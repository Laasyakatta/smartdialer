"""
Telecom Provider Registry & Factory
"""
from backend.app.providers.base import BaseTelecomProvider
from backend.app.providers.provider_a import ProviderA
from backend.app.providers.provider_b import ProviderB
from backend.app.providers.circuit_breaker import TelecomCircuitBreaker

_providers: dict[str, BaseTelecomProvider] = {
    "mock_a": ProviderA(),
    "mock_b": ProviderB()
}

_circuit_breakers: dict[str, TelecomCircuitBreaker] = {
    "mock_a": TelecomCircuitBreaker(),
    "mock_b": TelecomCircuitBreaker()
}

def get_telecom_provider(name: str = "mock_a") -> BaseTelecomProvider:
    if name not in _providers:
        name = "mock_a"
    return _providers[name]

def get_circuit_breaker(name: str = "mock_a") -> TelecomCircuitBreaker:
    if name not in _circuit_breakers:
        name = "mock_a"
    return _circuit_breakers[name]

def set_provider_outage(name: str, in_outage: bool):
    provider = get_telecom_provider(name)
    provider.set_outage(in_outage)
    cb = get_circuit_breaker(name)
    if in_outage:
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
    else:
        cb.reset()

def get_all_provider_statuses() -> list[dict]:
    res = []
    for name, prov in _providers.items():
        cb = _circuit_breakers[name]
        res.append({
            "name": name,
            "is_outage": prov.is_outage,
            "circuit_state": cb.state.value,
            "failures": cb.failure_count,
            "can_execute": cb.can_execute()
        })
    return res
