"""
Safety Controller Tests: Proof that Safety Cannot Be Bypassed
"""
import pytest
from datetime import datetime, timezone
from backend.app.models.agent import Agent
from backend.app.models.borrower import Borrower
from backend.app.models.campaign import Campaign
from backend.app.models.call import Call
from backend.app.models.enums import AgentState, CallState, DialingMode, SafetyDecisionType
from backend.app.services.safety_controller import SafetyController
from backend.app.providers import set_provider_outage, get_circuit_breaker

def test_safety_controller_enforces_agent_capacity_slot_limit(test_db):
    """
    Scenario: Pacing engine proposes 15 calls.
    Only 4 agents are available.
    Safety Controller MUST reduce the request to 4.
    """
    # Create 4 available agents
    for i in range(4):
        test_db.add(Agent(
            agent_id=f"AGT_SAFE_{i}",
            agent_name=f"Agent {i}",
            status=AgentState.AVAILABLE.value,
            last_status_change=datetime.now(timezone.utc)
        ))
    
    # Create campaign
    test_db.add(Campaign(
        campaign_id="CMP_SAFE_1",
        campaign_name="Safety Test Campaign",
        max_concurrent_calls=50
    ))
    test_db.commit()

    candidates = [f"BRW_SAFE_{i}" for i in range(20)]

    result = SafetyController.evaluate_proposal(
        db=test_db,
        campaign_id="CMP_SAFE_1",
        requested_count=15,
        candidate_borrower_ids=candidates,
        provider_name="mock_a",
        dialing_mode=DialingMode.PREDICTIVE
    )

    # Invariant: Must NOT approve 15 calls. Must REDUCE to available slots (4)
    assert result.approved_count == 4
    assert result.decision in (SafetyDecisionType.REDUCE, getattr(SafetyDecisionType, 'REDUCED', SafetyDecisionType.REDUCE))
    assert len(result.valid_borrower_ids) == 4

def test_safety_controller_zero_capacity_rejection(test_db):
    """
    Zero available agents -> Safety Controller MUST REJECT.
    """
    test_db.add(Campaign(campaign_id="CMP_SAFE_2", campaign_name="Zero Cap Campaign", max_concurrent_calls=50))
    test_db.commit()

    result = SafetyController.evaluate_proposal(
        db=test_db,
        campaign_id="CMP_SAFE_2",
        requested_count=5,
        candidate_borrower_ids=["BRW_1", "BRW_2"],
        provider_name="mock_a",
        dialing_mode=DialingMode.PROGRESSIVE
    )

    assert result.decision == SafetyDecisionType.REJECT
    assert result.approved_count == 0

def test_safety_controller_does_not_double_count_reserved_agent_calls(test_db):
    """
    Calls already attached to reserved agents must not reduce the remaining
    AVAILABLE agent capacity a second time.
    """
    for i in range(2):
        test_db.add(Agent(
            agent_id=f"AGT_BUSY_{i}",
            agent_name=f"Busy Agent {i}",
            status=AgentState.RESERVED.value
        ))
    for i in range(4):
        test_db.add(Agent(
            agent_id=f"AGT_FREE_{i}",
            agent_name=f"Free Agent {i}",
            status=AgentState.AVAILABLE.value
        ))
    test_db.add(Campaign(
        campaign_id="CMP_SAFE_RESERVED",
        campaign_name="Reserved Capacity Test",
        max_concurrent_calls=50
    ))
    for i in range(2):
        test_db.add(Call(
            call_id=f"CALL_BUSY_{i}",
            account_id=f"ACC_BUSY_{i}",
            borrower_id=f"BRW_BUSY_{i}",
            agent_id=f"AGT_BUSY_{i}",
            campaign_id="CMP_SAFE_RESERVED",
            state=CallState.RINGING.value
        ))
    test_db.commit()

    result = SafetyController.evaluate_proposal(
        db=test_db,
        campaign_id="CMP_SAFE_RESERVED",
        requested_count=4,
        candidate_borrower_ids=[f"BRW_NEW_{i}" for i in range(4)],
        provider_name="mock_a",
        dialing_mode=DialingMode.PREDICTIVE
    )

    assert result.approved_count == 4
    assert result.diagnostics["usable_agent_slots"] == 4

def test_safety_controller_borrower_deduplication(test_db):
    """
    Candidate borrower already has a call IN_FLIGHT -> must be filtered out!
    """
    test_db.add(Agent(agent_id="AGT_AVAIL_1", agent_name="Agent 1", status=AgentState.AVAILABLE.value))
    test_db.add(Agent(agent_id="AGT_AVAIL_2", agent_name="Agent 2", status=AgentState.AVAILABLE.value))
    test_db.add(Campaign(campaign_id="CMP_SAFE_3", campaign_name="Dedup Test", max_concurrent_calls=50))
    # Existing active call on BRW_DUPLICATE
    test_db.add(Call(
        call_id="CALL_EXISTING_1",
        account_id="ACC_1",
        borrower_id="BRW_DUPLICATE",
        state=CallState.RINGING.value
    ))
    test_db.commit()

    result = SafetyController.evaluate_proposal(
        db=test_db,
        campaign_id="CMP_SAFE_3",
        requested_count=2,
        candidate_borrower_ids=["BRW_DUPLICATE", "BRW_FRESH"],
        provider_name="mock_a",
        dialing_mode=DialingMode.PROGRESSIVE
    )

    # BRW_DUPLICATE must be filtered out. Only BRW_FRESH approved!
    assert result.approved_count == 1
    assert "BRW_DUPLICATE" not in result.valid_borrower_ids
    assert "BRW_FRESH" in result.valid_borrower_ids

def test_safety_controller_provider_outage_rejection(test_db):
    """
    Provider in outage -> Safety Controller triggers REJECT / FALLBACK.
    """
    test_db.add(Agent(agent_id="AGT_AVAIL_2", agent_name="Agent 2", status=AgentState.AVAILABLE.value))
    test_db.add(Campaign(campaign_id="CMP_SAFE_4", campaign_name="Outage Campaign", max_concurrent_calls=50))
    test_db.commit()

    set_provider_outage("mock_a", True)

    try:
        result = SafetyController.evaluate_proposal(
            db=test_db,
            campaign_id="CMP_SAFE_4",
            requested_count=1,
            candidate_borrower_ids=["BRW_99"],
            provider_name="mock_a",
            dialing_mode=DialingMode.PROGRESSIVE
        )
        assert result.decision == SafetyDecisionType.REJECT
        assert result.approved_count == 0
    finally:
        set_provider_outage("mock_a", False)
        get_circuit_breaker("mock_a").reset()
