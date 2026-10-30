"""
Independent Safety Controller Service

Architectural Mandate:
  The Predictive Pacing Engine must NEVER directly initiate calls.
  The Safety Controller sits as an impassable gatekeeper between the Pacing Engine
  and Call Allocation / Telecom initiation.

Decisions:
  APPROVE, REDUCE, REJECT, FALLBACK_TO_PROGRESSIVE
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_

from backend.app.models.enums import AgentState, CallState, DialingMode, SafetyDecisionType
from backend.app.models.agent import Agent
from backend.app.models.call import Call
from backend.app.models.campaign import Campaign
from backend.app.models.borrower import Borrower
from backend.app.providers import get_telecom_provider, get_circuit_breaker
from backend.app.core.config import settings

logger = logging.getLogger("smartdialer.safety_controller")

ACTIVE_CALL_STATES = {
    CallState.QUEUED.value,
    CallState.RESERVED.value,
    CallState.INITIATED.value,
    CallState.RINGING.value,
    CallState.ANSWERED.value,
    CallState.CONNECTED.value,
}

OUTSTANDING_PRE_CONNECT_STATES = {
    CallState.RESERVED.value,
    CallState.INITIATED.value,
    CallState.RINGING.value,
}

@dataclass
class SafetyEvaluationResult:
    decision: SafetyDecisionType
    approved_count: int
    requested_count: int
    reason: str
    valid_borrower_ids: list[str] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)

class SafetyController:
    @staticmethod
    def evaluate_proposal(
        db: Session,
        campaign_id: str,
        requested_count: int,
        candidate_borrower_ids: list[str],
        provider_name: str = "mock_a",
        dialing_mode: DialingMode = DialingMode.PROGRESSIVE
    ) -> SafetyEvaluationResult:
        """
        Validates proposed dialing batch against deterministic capacity, health,
        concurrency, and deduplication rules.
        """
        # Diagnostic tracking
        diagnostics = {
            "campaign_id": campaign_id,
            "provider_name": provider_name,
            "dialing_mode": dialing_mode.value,
            "requested_count": requested_count
        }

        # 1. Provider Health Verification
        provider = get_telecom_provider(provider_name)
        cb = get_circuit_breaker(provider_name)

        if provider.is_outage or not cb.can_execute():
            reason = f"Provider '{provider_name}' unhealthy or circuit breaker OPEN"
            logger.warning(f"Safety Gate REJECT: {reason}")
            if dialing_mode == DialingMode.PREDICTIVE:
                return SafetyEvaluationResult(
                    decision=SafetyDecisionType.FALLBACK_TO_PROGRESSIVE,
                    approved_count=0,
                    requested_count=requested_count,
                    reason=reason + " -> Fallback to Progressive Dialing",
                    diagnostics=diagnostics
                )
            return SafetyEvaluationResult(
                decision=SafetyDecisionType.REJECT,
                approved_count=0,
                requested_count=requested_count,
                reason=reason,
                diagnostics=diagnostics
            )

        # 2. Campaign & Global Concurrency Check
        campaign = db.get(Campaign, campaign_id)
        max_campaign_calls = campaign.max_concurrent_calls if campaign else 50

        campaign_active_calls = db.scalar(
            select(func.count(Call.call_id))
            .where(
                Call.campaign_id == campaign_id,
                Call.state.in_(ACTIVE_CALL_STATES)
            )
        ) or 0

        system_active_calls = db.scalar(
            select(func.count(Call.call_id))
            .where(Call.state.in_(ACTIVE_CALL_STATES))
        ) or 0

        campaign_room = max(0, max_campaign_calls - campaign_active_calls)
        system_room = max(0, settings.MAX_SYSTEM_CONCURRENT_CALLS - system_active_calls)
        concurrency_headroom = min(campaign_room, system_room)

        diagnostics["campaign_active_calls"] = campaign_active_calls
        diagnostics["system_active_calls"] = system_active_calls
        diagnostics["concurrency_headroom"] = concurrency_headroom

        if concurrency_headroom <= 0:
            return SafetyEvaluationResult(
                decision=SafetyDecisionType.REJECT,
                approved_count=0,
                requested_count=requested_count,
                reason="Max concurrent call limits reached for campaign or system",
                diagnostics=diagnostics
            )

        # 3. Deterministic Hard Agent Capacity Slot Enforcement
        # Available agents = in AVAILABLE state
        available_agents = db.scalar(
            select(func.count(Agent.agent_id))
            .where(
                Agent.status == AgentState.AVAILABLE.value,
                ~Agent.agent_id.in_(
                    select(Call.agent_id).where(
                        Call.agent_id.isnot(None),
                        Call.state.in_(ACTIVE_CALL_STATES)
                    )
                )
            )
        ) or 0

        # Outstanding pre-connected calls already launched and consuming capacity slots
        outstanding_calls = db.scalar(
            select(func.count(Call.call_id))
            .where(Call.state.in_(OUTSTANDING_PRE_CONNECT_STATES))
        ) or 0

        # A call without an assigned agent still consumes one of the free slots.
        unassigned_outstanding_calls = db.scalar(
            select(func.count(Call.call_id))
            .where(
                Call.state.in_(OUTSTANDING_PRE_CONNECT_STATES),
                Call.agent_id.is_(None)
            )
        ) or 0

        connected_calls = db.scalar(
            select(func.count(Call.call_id))
            .where(Call.state == CallState.CONNECTED.value)
        ) or 0

        diagnostics["available_agents"] = available_agents
        diagnostics["outstanding_pre_connect_calls"] = outstanding_calls
        diagnostics["unassigned_outstanding_calls"] = unassigned_outstanding_calls
        diagnostics["connected_calls"] = connected_calls

        # Calls with reserved agents already reduce AVAILABLE; only unassigned calls
        # need to be deducted from the remaining agent capacity.
        usable_agent_slots = max(0, available_agents - unassigned_outstanding_calls)
        diagnostics["usable_agent_slots"] = usable_agent_slots

        if usable_agent_slots <= 0:
            logger.info("Safety Gate REJECT: Zero available agent slots remaining")
            return SafetyEvaluationResult(
                decision=SafetyDecisionType.REJECT,
                approved_count=0,
                requested_count=requested_count,
                reason=f"Zero unreserved agent slots (Available: {available_agents}, Outstanding: {outstanding_calls})",
                diagnostics=diagnostics
            )

        # 4. Borrower Deduplication & Uniqueness
        # Ensure no candidate borrower currently has an active call
        deduped_borrowers = []
        seen_batch_borrowers = set()
        
        for bid in candidate_borrower_ids:
            if bid in seen_batch_borrowers:
                continue
            seen_batch_borrowers.add(bid)

            # Check DB for active call on borrower
            active_call_count = db.scalar(
                select(func.count(Call.call_id))
                .where(
                    Call.borrower_id == bid,
                    Call.state.in_(ACTIVE_CALL_STATES)
                )
            ) or 0

            if active_call_count == 0:
                deduped_borrowers.append(bid)

        diagnostics["deduped_eligible_borrowers"] = len(deduped_borrowers)

        if not deduped_borrowers:
            return SafetyEvaluationResult(
                decision=SafetyDecisionType.REJECT,
                approved_count=0,
                requested_count=requested_count,
                reason="All candidate borrowers already have active calls or are invalid",
                diagnostics=diagnostics
            )

        # 5. Determine Approved Volume
        # Hard limits ceiling: min(requested_count, concurrency_headroom, usable_agent_slots, len(deduped_borrowers))
        approved_count = min(
            requested_count,
            concurrency_headroom,
            usable_agent_slots,
            len(deduped_borrowers)
        )

        final_borrowers = deduped_borrowers[:approved_count]

        if approved_count == requested_count and approved_count > 0:
            return SafetyEvaluationResult(
                decision=SafetyDecisionType.APPROVE,
                approved_count=approved_count,
                requested_count=requested_count,
                reason="Proposal verified and approved within hard capacity boundaries",
                valid_borrower_ids=final_borrowers,
                diagnostics=diagnostics
            )
        elif approved_count > 0:
            return SafetyEvaluationResult(
                decision=SafetyDecisionType.REDUCED if hasattr(SafetyDecisionType, 'REDUCED') else SafetyDecisionType.REDUCE,
                approved_count=approved_count,
                requested_count=requested_count,
                reason=f"Reduced from {requested_count} to {approved_count} to enforce strict agent slot headroom ({usable_agent_slots} slots)",
                valid_borrower_ids=final_borrowers,
                diagnostics=diagnostics
            )
        else:
            return SafetyEvaluationResult(
                decision=SafetyDecisionType.REJECT,
                approved_count=0,
                requested_count=requested_count,
                reason="Capacity constraints or headroom prevent starting calls",
                diagnostics=diagnostics
            )
