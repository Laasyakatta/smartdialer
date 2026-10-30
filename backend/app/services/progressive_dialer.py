"""
Progressive Dialer Service

Core Tenet:
  1 available agent -> 1 outbound call.
  Never exceeds available agent capacity.
  Every call is checked with the Safety Controller.
"""
from dataclasses import dataclass, field
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from backend.app.models.enums import DialingMode, SafetyDecisionType, AgentState
from backend.app.models.agent import Agent
from backend.app.models.call import Call
from backend.app.services.agent_state_machine import AgentStateMachine
from backend.app.services.eligibility_service import EligibilityService
from backend.app.services.safety_controller import SafetyController, SafetyEvaluationResult
from backend.app.services.call_allocator import CallAllocator
from backend.app.providers import get_telecom_provider
from backend.app.services.event_processor import EventProcessor

logger = logging.getLogger("smartdialer.progressive_dialer")

@dataclass
class DialingCycleResult:
    campaign_id: str
    dialing_mode: str
    available_agents: int
    requested_calls: int
    approved_calls: int
    calls_initiated: int
    safety_decision: str
    safety_reason: str
    call_ids: list[str] = field(default_factory=list)

class ProgressiveDialerService:
    @staticmethod
    def execute_progressive_cycle(
        db: Session,
        campaign_id: str,
        provider_name: str = "mock_a",
        max_batch_size: int = 25,
        is_simulation: bool = False,
        simulation_id: str | None = None,
        simulated_answer_prob: float = 0.20,
        simulated_talk_sec: int = 60
    ) -> DialingCycleResult:
        """
        Executes one full progressive dialing cycle:
        1. Find available agents count.
        2. Find eligible borrowers.
        3. Consult Safety Controller.
        4. Reserve agents & allocate approved calls.
        5. Trigger provider lifecycle events.
        """
        # Step 1: Query available agent count
        available_agent_count = db.scalar(
            select(func.count(Agent.agent_id))
            .where(Agent.status == AgentState.AVAILABLE.value)
        ) or 0

        if available_agent_count <= 0:
            logger.info("Progressive Dialer: Zero available agents to dial.")
            return DialingCycleResult(
                campaign_id=campaign_id,
                dialing_mode="PROGRESSIVE",
                available_agents=0,
                requested_calls=0,
                approved_calls=0,
                calls_initiated=0,
                safety_decision="REJECT",
                safety_reason="Zero available agents"
            )

        batch_target = min(available_agent_count, max_batch_size)

        # Step 2: Query candidate borrowers
        candidates = EligibilityService.get_candidate_borrowers_for_campaign(
            db, campaign_id, limit=batch_target * 2
        )

        if not candidates:
            return DialingCycleResult(
                campaign_id=campaign_id,
                dialing_mode="PROGRESSIVE",
                available_agents=available_agent_count,
                requested_calls=batch_target,
                approved_calls=0,
                calls_initiated=0,
                safety_decision="REJECT",
                safety_reason="No eligible borrowers found in target queue"
            )

        candidate_bids = [b_id for b_id, _ in candidates]
        account_map = {b_id: acc_id for b_id, acc_id in candidates}

        # Step 3: Consult Safety Controller BEFORE reserving agents
        safety_eval: SafetyEvaluationResult = SafetyController.evaluate_proposal(
            db=db,
            campaign_id=campaign_id,
            requested_count=batch_target,
            candidate_borrower_ids=candidate_bids,
            provider_name=provider_name,
            dialing_mode=DialingMode.PROGRESSIVE
        )

        if safety_eval.approved_count <= 0:
            return DialingCycleResult(
                campaign_id=campaign_id,
                dialing_mode="PROGRESSIVE",
                available_agents=available_agent_count,
                requested_calls=batch_target,
                approved_calls=0,
                calls_initiated=0,
                safety_decision=safety_eval.decision.value,
                safety_reason=safety_eval.reason
            )

        # Step 4: Atomically reserve agents up to approved_count
        reserved_agents = AgentStateMachine.find_and_reserve_available_agents(
            db, limit=safety_eval.approved_count, campaign_id=campaign_id
        )

        if not reserved_agents:
            return DialingCycleResult(
                campaign_id=campaign_id,
                dialing_mode="PROGRESSIVE",
                available_agents=available_agent_count,
                requested_calls=batch_target,
                approved_calls=safety_eval.approved_count,
                calls_initiated=0,
                safety_decision="REJECT",
                safety_reason="Could not reserve agents (race or dropped availability)"
            )

        # Step 5: Allocate and Initiate approved calls
        initiated_calls = []
        for i, b_id in enumerate(safety_eval.valid_borrower_ids):
            if i >= len(reserved_agents):
                break
            agent = reserved_agents[i]
            acc_id = account_map.get(b_id, "ACC_DEFAULT")
            call = CallAllocator.allocate_and_initiate(
                db=db,
                campaign_id=campaign_id,
                borrower_id=b_id,
                account_id=acc_id,
                agent=agent,
                provider_name=provider_name,
                is_simulation=is_simulation,
                simulation_id=simulation_id
            )
            if call:
                initiated_calls.append(call)

        # Release any unallocated agents
        if len(initiated_calls) < len(reserved_agents):
            for unused in reserved_agents[len(initiated_calls):]:
                AgentStateMachine.release_agent(db, unused.agent_id)

        # Step 6: Deliver mock provider events
        provider = get_telecom_provider(provider_name)
        for call in initiated_calls:
            events = provider.generate_call_lifecycle_events(
                call_id=call.call_id,
                answer_probability=simulated_answer_prob,
                talk_time_sec=simulated_talk_sec
            )
            for evt in events:
                EventProcessor.process_incoming_event(
                    db=db,
                    provider_event_id=evt["provider_event_id"],
                    provider_name=evt["provider_name"],
                    call_id=evt["call_id"],
                    event_type=evt["event_type"],
                    duration_sec=evt.get("duration_sec"),
                    terminal_reason=evt.get("terminal_reason")
                )

        return DialingCycleResult(
            campaign_id=campaign_id,
            dialing_mode="PROGRESSIVE",
            available_agents=available_agent_count,
            requested_calls=batch_target,
            approved_calls=safety_eval.approved_count,
            calls_initiated=len(initiated_calls),
            safety_decision=safety_eval.decision.value,
            safety_reason=safety_eval.reason,
            call_ids=[c.call_id for c in initiated_calls]
        )
