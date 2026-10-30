"""
Call Allocator Service: Pairs Approved Borrowers with Agents and Telecom Execution
"""
import uuid
from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session

from backend.app.models.enums import CallState, AgentState
from backend.app.models.call import Call, CallAllocation
from backend.app.models.agent import Agent
from backend.app.models.borrower import Borrower
from backend.app.providers import get_telecom_provider, get_circuit_breaker
from backend.app.services.call_state_machine import CallStateMachine
from backend.app.services.agent_state_machine import AgentStateMachine
from backend.app.services.eligibility_service import EligibilityService
from backend.app.services.event_processor import EventProcessor

logger = logging.getLogger("smartdialer.call_allocator")

class CallAllocator:
    @staticmethod
    def allocate_and_initiate(
        db: Session,
        campaign_id: str,
        borrower_id: str,
        account_id: str,
        agent: Agent,
        provider_name: str = "mock_a",
        is_simulation: bool = False,
        simulation_id: str | None = None
    ) -> Call | None:
        """
        Pairs a reserved agent with an eligible borrower, creates the Call record,
        and initiates telecom routing.
        """
        call_id = f"CALL-{uuid.uuid4().hex[:12].upper()}"
        now = datetime.now(timezone.utc)

        # 1. Atomically lock borrower
        if not EligibilityService.reserve_borrower_atomic(db, borrower_id, call_id):
            logger.warning(f"Could not reserve borrower {borrower_id}: already in flight")
            AgentStateMachine.release_agent(db, agent.agent_id)
            return None

        # 2. Update agent association
        agent.current_call_id = call_id
        db.commit()

        # 3. Create Call record in RESERVED state
        call = Call(
            call_id=call_id,
            campaign_id=campaign_id,
            account_id=account_id,
            borrower_id=borrower_id,
            agent_id=agent.agent_id,
            provider_name=provider_name,
            direction="OUTBOUND",
            state=CallState.RESERVED.value,
            queued_at=now,
            reserved_at=now,
            is_simulation=is_simulation,
            simulation_id=simulation_id
        )
        db.add(call)
        
        allocation = CallAllocation(
            call_id=call_id,
            agent_id=agent.agent_id,
            borrower_id=borrower_id,
            allocated_at=now,
            status="ACTIVE"
        )
        db.add(allocation)
        db.commit()
        db.refresh(call)

        # 4. Initiate Call via Telecom Provider
        provider = get_telecom_provider(provider_name)
        cb = get_circuit_breaker(provider_name)

        borrower = db.get(Borrower, borrower_id)
        phone = borrower.phone if borrower else "9999999999"

        try:
            telecom_resp = provider.initiate_call(call_id, phone)
        except Exception as ex:
            logger.error(
                "Provider initiation raised for call %s (%s)",
                call_id,
                type(ex).__name__
            )
            telecom_resp = {"success": False, "error": "PROVIDER_INITIATION_ERROR"}

        if not telecom_resp.get("success", False):
            # Provider initiation failed!
            cb.record_failure()
            error_reason = str(telecom_resp.get("error") or "PROVIDER_INITIATION_ERROR")[:100]
            logger.error("Telecom carrier failed initiation for call %s (%s)", call_id, error_reason)
            
            CallStateMachine.transition(db, call, CallState.FAILED, reason=error_reason)
            AgentStateMachine.release_agent(db, agent.agent_id)
            EligibilityService.release_borrower(db, borrower_id)
            allocation.status = "FAILED"
            allocation.released_at = datetime.now(timezone.utc)
            db.commit()
            return call

        cb.record_success()

        # 5. Transition Call to INITIATED & Agent to DIALING
        CallStateMachine.transition(db, call, CallState.INITIATED)
        AgentStateMachine.transition(db, agent, AgentState.DIALING, call_id=call_id)
        
        return call
