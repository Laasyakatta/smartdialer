"""
Unit Tests for Telecom Providers & Circuit Breaker
"""
import time
from backend.app.providers import get_telecom_provider, get_circuit_breaker, set_provider_outage
from backend.app.providers.circuit_breaker import TelecomCircuitBreaker, CircuitState

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
