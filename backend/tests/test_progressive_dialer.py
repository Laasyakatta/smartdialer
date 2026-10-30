"""
Integration Test for Progressive Dialer Service
"""
import pytest
from datetime import datetime, timezone
from backend.app.models.agent import Agent
from backend.app.models.borrower import Borrower
from backend.app.models.account import Account
from backend.app.models.campaign import Campaign, DailyTargeting
from backend.app.models.enums import AgentState
from backend.app.services.progressive_dialer import ProgressiveDialerService

def test_progressive_dialer_execution_cycle(test_db):
    """
    Creates available agents, campaign, eligible borrowers, and executes cycle.
    """
    # 1. Agents
    for i in range(3):
        test_db.add(Agent(
            agent_id=f"AGT_PROG_{i}",
            agent_name=f"Progressive Agent {i}",
            status=AgentState.AVAILABLE.value,
            last_status_change=datetime.now(timezone.utc)
        ))

    # 2. Campaign
    camp = Campaign(
        campaign_id="CMP_PROG_1",
        campaign_name="Prog Dial Campaign",
        max_concurrent_calls=50,
        is_active=True
    )
    test_db.add(camp)

    # 3. Borrowers & Accounts & Targeting
    for i in range(5):
        bid = f"BRW_PROG_{i}"
        acc_id = f"ACC_PROG_{i}"
        test_db.add(Borrower(
            borrower_id=bid,
            name=f"Borrower {i}",
            phone=f"987654321{i}",
            is_eligible=True
        ))
        test_db.add(Account(
            account_id=acc_id,
            borrower_id=bid,
            status="ACTIVE"
        ))
        test_db.add(DailyTargeting(
            target_id=f"TGT_PROG_{i}",
            account_id=acc_id,
            campaign_id="CMP_PROG_1",
            target_date=datetime.now(timezone.utc),
            priority=i + 1,
            status="QUEUED"
        ))
    test_db.commit()

    # Execute Progressive cycle
    res = ProgressiveDialerService.execute_progressive_cycle(
        db=test_db,
        campaign_id="CMP_PROG_1",
        provider_name="mock_a",
        max_batch_size=3,
        simulated_answer_prob=0.33,
        simulated_talk_sec=45
    )

    assert res.calls_initiated == 3
    assert res.approved_calls == 3
    assert res.safety_decision == "APPROVE"
    assert len(res.call_ids) == 3
