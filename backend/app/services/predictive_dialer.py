"""
Predictive Dialer Workflow Service

Coordinates:
  Pacing Engine -> Safety Controller -> Call Allocator -> Provider Events
"""
import logging
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from backend.app.models.enums import DialingMode, SafetyDecisionType
from backend.app.services.predictive_engine import PredictivePacingEngine, PacingProposal
from backend.app.services.safety_controller import SafetyController, SafetyEvaluationResult
from backend.app.services.agent_state_machine import AgentStateMachine
from backend.app.services.eligibility_service import EligibilityService
from backend.app.services.call_allocator import CallAllocator
from backend.app.services.progressive_dialer import ProgressiveDialerService, DialingCycleResult
from backend.app.providers import get_telecom_provider
from backend.app.services.event_processor import EventProcessor

logger = logging.getLogger("smartdialer.predictive_dialer")

class PredictiveDialerService:
    @staticmethod
    def execute_predictive_cycle(
        db: Session,
        campaign_id: str,
        provider_name: str = "mock_a",
        is_simulation: bool = False,
        simulation_id: str | None = None,
        simulated_answer_prob: float = 0.20,
        simulated_talk_sec: int = 60
    ) -> DialingCycleResult:
        """
        Executes one predictive dialing cycle according to the strict architecture:
        Campaign -> Pacing Engine -> Safety Controller -> Call Allocator -> Provider
        """
        pacing_engine = PredictivePacingEngine()
        proposal: PacingProposal = pacing_engine.generate_proposal(db, campaign_id)

        if proposal.proposed_calls <= 0:
            return DialingCycleResult(
                campaign_id=campaign_id,
                dialing_mode="PREDICTIVE",
                available_agents=proposal.available_agents,
                requested_calls=0,
                approved_calls=0,
                calls_initiated=0,
                safety_decision="REJECT",
                safety_reason=f"Predictive engine proposed 0 calls ({proposal.reason})"
            )

        # Retrieve candidate borrowers for proposal
        candidates = EligibilityService.get_candidate_borrowers_for_campaign(
            db, campaign_id, limit=proposal.proposed_calls * 2
        )

        if not candidates:
            return DialingCycleResult(
                campaign_id=campaign_id,
                dialing_mode="PREDICTIVE",
                available_agents=proposal.available_agents,
                requested_calls=proposal.proposed_calls,
                approved_calls=0,
                calls_initiated=0,
                safety_decision="REJECT",
                safety_reason="No eligible borrowers found in target pool"
            )

        candidate_bids = [b_id for b_id, _ in candidates]
        account_map = {b_id: acc_id for b_id, acc_id in candidates}

        # Send proposal to Independent Safety Controller (Mandatory boundary)
        safety_eval: SafetyEvaluationResult = SafetyController.evaluate_proposal(
            db=db,
            campaign_id=campaign_id,
            requested_count=proposal.proposed_calls,
            candidate_borrower_ids=candidate_bids,
            provider_name=provider_name,
            dialing_mode=DialingMode.PREDICTIVE
        )

        if safety_eval.decision == SafetyDecisionType.FALLBACK_TO_PROGRESSIVE:
            logger.warning("Safety Controller triggered FALLBACK_TO_PROGRESSIVE")
            return ProgressiveDialerService.execute_progressive_cycle(
                db=db,
                campaign_id=campaign_id,
                provider_name=provider_name,
                is_simulation=is_simulation,
                simulation_id=simulation_id,
                simulated_answer_prob=simulated_answer_prob,
                simulated_talk_sec=simulated_talk_sec
            )

        if safety_eval.approved_count <= 0:
            return DialingCycleResult(
                campaign_id=campaign_id,
                dialing_mode="PREDICTIVE",
                available_agents=proposal.available_agents,
                requested_calls=proposal.proposed_calls,
                approved_calls=0,
                calls_initiated=0,
                safety_decision=safety_eval.decision.value,
                safety_reason=safety_eval.reason
            )

        # Reserve agents up to approved count
        agents = AgentStateMachine.find_and_reserve_available_agents(
            db, limit=safety_eval.approved_count, campaign_id=campaign_id
        )

        if not agents:
            return DialingCycleResult(
                campaign_id=campaign_id,
                dialing_mode="PREDICTIVE",
                available_agents=0,
                requested_calls=proposal.proposed_calls,
                approved_calls=safety_eval.approved_count,
                calls_initiated=0,
                safety_decision="REJECT",
                safety_reason="Could not atomically reserve agents (race or dropped availability)"
            )

        # Allocate approved calls
        initiated_calls = []
        for i, b_id in enumerate(safety_eval.valid_borrower_ids):
            if i >= len(agents):
                break
            agent = agents[i]
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

        # Release any unallocated agents if candidate borrowers were insufficient
        if len(initiated_calls) < len(agents):
            for unused_agent in agents[len(initiated_calls):]:
                AgentStateMachine.release_agent(db, unused_agent.agent_id)

        # Deliver provider lifecycle events
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
            dialing_mode="PREDICTIVE",
            available_agents=proposal.available_agents,
            requested_calls=proposal.proposed_calls,
            approved_calls=safety_eval.approved_count,
            calls_initiated=len(initiated_calls),
            safety_decision=safety_eval.decision.value,
            safety_reason=safety_eval.reason,
            call_ids=[c.call_id for c in initiated_calls]
        )
