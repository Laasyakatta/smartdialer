"""
Unit Tests for Telecom Providers & Circuit Breaker
"""
import time
from backend.app.models.agent import Agent
from backend.app.models.borrower import Borrower
from backend.app.models.enums import AgentState, CallState
from backend.app.providers import get_telecom_provider, get_circuit_breaker, set_provider_outage
from backend.app.providers.circuit_breaker import TelecomCircuitBreaker, CircuitState
from backend.app.services.call_allocator import CallAllocator

def test_circuit_breaker_tripping_and_recovery():
    cb = TelecomCircuitBreaker(failure_threshold=3, recovery_timeout_sec=0.2)
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # Record 3 failures
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED

    cb.record_failure()
    # Breaker trips OPEN!
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False

    # Wait for recovery timeout
    time.sleep(0.25)
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN

    # 3 consecutive successes reset breaker to CLOSED
    cb.record_success()
    cb.record_success()
    cb.record_success()
    assert cb.state == CircuitState.CLOSED

def test_provider_outage_simulation():
    prov = get_telecom_provider("mock_a")
    cb = get_circuit_breaker("mock_a")
    
    set_provider_outage("mock_a", True)
    assert prov.is_outage is True
    res = prov.initiate_call("CALL_OUTAGE_1", "9999999999")
    assert res["success"] is False
    assert res["error"] == "PROVIDER_OUTAGE"

    # Restore
    set_provider_outage("mock_a", False)
    cb.reset()
    assert prov.is_outage is False


def test_provider_exception_fails_call_and_releases_reservations(test_db, monkeypatch):
    agent = Agent(
        agent_id="AGT_PROVIDER_ERROR",
        agent_name="Provider Error Agent",
        status=AgentState.RESERVED.value
    )
    borrower = Borrower(
        borrower_id="BRW_PROVIDER_ERROR",
        name="Provider Error Borrower",
        phone="5550100"
    )
    test_db.add_all([agent, borrower])
    test_db.commit()

    class RaisingProvider:
        def initiate_call(self, call_id, phone):
            raise RuntimeError("provider failure")

    monkeypatch.setattr(
        "backend.app.services.call_allocator.get_telecom_provider",
        lambda provider_name: RaisingProvider()
    )
    circuit = get_circuit_breaker("mock_a")
    circuit.reset()

    try:
        call = CallAllocator.allocate_and_initiate(
            db=test_db,
            campaign_id="CMP_PROVIDER_ERROR",
            borrower_id=borrower.borrower_id,
            account_id="ACC_PROVIDER_ERROR",
            agent=agent
        )

        assert call is not None
        assert call.state == CallState.FAILED.value
        test_db.refresh(agent)
        test_db.refresh(borrower)
        assert agent.status == AgentState.AVAILABLE.value
        assert borrower.current_active_call_id is None
        assert circuit.failure_count == 1
    finally:
        circuit.reset()
