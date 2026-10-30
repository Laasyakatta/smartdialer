"""
Failure Recovery & System Reconciliation Service

Handles:
1. Worker crashes after agent reservation.
2. Worker crashes after borrower reservation.
3. Worker crashes after call initiation.
4. Worker crashes after ANSWERED (preserves agent-borrower bond; never abandons answered borrower).
5. Stale reservation reaping.
"""
from datetime import datetime, timezone, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select, update, and_

from backend.app.models.enums import AgentState, CallState
from backend.app.models.agent import Agent
from backend.app.models.borrower import Borrower
from backend.app.models.call import Call
from backend.app.services.agent_state_machine import AgentStateMachine
from backend.app.services.call_state_machine import CallStateMachine
from backend.app.services.eligibility_service import EligibilityService
from backend.app.core.config import settings

logger = logging.getLogger("smartdialer.recovery")

class RecoveryService:
    @staticmethod
    def reconcile_stale_reservations(
        db: Session,
        timeout_seconds: int = 45
    ) -> dict[str, int]:
        """
        Reconciles orphaned agent/borrower reservations caused by worker crashes.
        """
        now = datetime.now(timezone.utc)
        stale_threshold = now - timedelta(seconds=timeout_seconds)
        
        reconciled_agents = 0
        reconciled_borrowers = 0
        reconciled_calls = 0

        # 1. Stale Agent Reservations: Agent is RESERVED, but no active in-flight call exists
        stale_agents = db.scalars(
            select(Agent).where(
                Agent.status == AgentState.RESERVED.value,
                Agent.reserved_at < stale_threshold
            )
        ).all()

        for ag in stale_agents:
            # Check if there is an active call attached
            has_active_call = False
            if ag.current_call_id:
                call = db.get(Call, ag.current_call_id)
                if call and not CallStateMachine.is_terminal(call.state):
                    has_active_call = True

            if not has_active_call:
                logger.warning(f"Reconciling stale agent reservation: {ag.agent_id}")
                AgentStateMachine.release_agent(db, ag.agent_id)
                reconciled_agents += 1

        # 2. Stale Borrower Reservations: Borrower has current_active_call_id but call is missing or terminal
        stale_borrowers = db.scalars(
            select(Borrower).where(
                Borrower.current_active_call_id.isnot(None),
                Borrower.reserved_at < stale_threshold
            )
        ).all()

        for b in stale_borrowers:
            call = db.get(Call, b.current_active_call_id) if b.current_active_call_id else None
            if not call or CallStateMachine.is_terminal(call.state):
                logger.warning(f"Reconciling stale borrower lock: {b.borrower_id}")
                EligibilityService.release_borrower(db, b.borrower_id)
                reconciled_borrowers += 1

        # 3. Hanging Initiated Calls: Call stuck in INITIATED / RINGING for > timeout
        hanging_calls = db.scalars(
            select(Call).where(
                Call.state.in_([CallState.RESERVED.value, CallState.INITIATED.value, CallState.RINGING.value]),
                Call.queued_at < stale_threshold
            )
        ).all()

        for c in hanging_calls:
            logger.warning(f"Reconciling hanging call: {c.call_id} (State: {c.state})")
            CallStateMachine.transition(
                db, c, CallState.FAILED, reason="WORKER_CRASH_OR_INITIATION_TIMEOUT"
            )
            if c.agent_id:
                AgentStateMachine.release_agent(db, c.agent_id)
            if c.borrower_id:
                EligibilityService.release_borrower(db, c.borrower_id)
            reconciled_calls += 1

        return {
            "reconciled_agents": reconciled_agents,
            "reconciled_borrowers": reconciled_borrowers,
            "reconciled_hanging_calls": reconciled_calls
        }

    @staticmethod
    def reconcile_connected_call_after_crash(
        db: Session,
        call_id: str
    ) -> bool:
        """
        Scenario 4: Worker crash immediately after ANSWERED.
        Invariant: Never release an agent in a way that leaves an answered borrower abandoned!
        If agent and call are connected, lock is verified and preserved until telecom terminates.
        """
        call = db.get(Call, call_id)
        if not call:
            return False

        if call.state in (CallState.ANSWERED.value, CallState.CONNECTED.value):
            if call.agent_id:
                agent = db.get(Agent, call.agent_id)
                if agent and agent.status != AgentState.CONNECTED.value:
                    agent.status = AgentState.CONNECTED.value
                    agent.current_call_id = call.call_id
                    db.commit()
                    logger.info(f"Reconciled connected bond for agent {agent.agent_id} and call {call_id}")
            return True
        return False
