"""
Failure Recovery Tests
"""
from datetime import datetime, timezone, timedelta
from backend.app.models.agent import Agent
from backend.app.models.borrower import Borrower
from backend.app.models.call import Call
from backend.app.models.enums import AgentState, CallState
from backend.app.services.recovery_service import RecoveryService

def test_stale_agent_reservation_recovery(test_db):
    """
    Worker crashed after reserving an agent.
    Reservation timestamp is 60 seconds old.
    Reconciler must reset agent to AVAILABLE.
    """
    past_time = datetime.now(timezone.utc) - timedelta(seconds=60)
    agent = Agent(
        agent_id="AGT_CRASH_1",
        agent_name="Crashed Agent",
        status=AgentState.RESERVED.value,
        reserved_at=past_time,
        last_status_change=past_time
    )
    test_db.add(agent)
    test_db.commit()

    report = RecoveryService.reconcile_stale_reservations(test_db, timeout_seconds=30)
    assert report["reconciled_agents"] == 1

    test_db.refresh(agent)
    assert agent.status == AgentState.AVAILABLE.value
    assert agent.reserved_at is None

def test_stale_borrower_lock_recovery(test_db):
    """
    Worker crashed after locking borrower.
    Reconciler must clear borrower active call lock.
    """
    past_time = datetime.now(timezone.utc) - timedelta(seconds=60)
    borrower = Borrower(
        borrower_id="BRW_CRASH_1",
        name="Locked Borrower",
        phone="9988776655",
        current_active_call_id="CALL_NON_EXISTENT",
        reserved_at=past_time
    )
    test_db.add(borrower)
    test_db.commit()

    report = RecoveryService.reconcile_stale_reservations(test_db, timeout_seconds=30)
    assert report["reconciled_borrowers"] == 1

    test_db.refresh(borrower)
    assert borrower.current_active_call_id is None
    assert borrower.reserved_at is None

def test_worker_crash_after_answered_preserves_agent(test_db):
    """
    Invariant: Never release an agent in a way that could leave an answered borrower without an agent!
    """
    call = Call(
        call_id="CALL_ANS_1",
        account_id="ACC_1",
        borrower_id="BRW_1",
        agent_id="AGT_CONNECTED_1",
        state=CallState.ANSWERED.value
    )
    agent = Agent(
        agent_id="AGT_CONNECTED_1",
        agent_name="Connected Agent",
        status=AgentState.DIALING.value  # Worker crashed before finishing agent update
    )
    test_db.add(call)
    test_db.add(agent)
    test_db.commit()

    reconciled = RecoveryService.reconcile_connected_call_after_crash(test_db, "CALL_ANS_1")
    assert reconciled is True

    test_db.refresh(agent)
    assert agent.status == AgentState.CONNECTED.value
    assert agent.current_call_id == "CALL_ANS_1"
