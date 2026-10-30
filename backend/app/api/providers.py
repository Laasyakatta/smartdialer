"""
Telecom Providers & Outage Injection API Router
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.app.providers import (
    get_all_provider_statuses,
    set_provider_outage,
    get_circuit_breaker
)

router = APIRouter(prefix="/providers", tags=["providers"])

class OutageToggleRequest(BaseModel):
    is_outage: bool

@router.get("")
def list_providers():
    return get_all_provider_statuses()

@router.post("/{provider_name}/outage")
def toggle_outage(provider_name: str, payload: OutageToggleRequest):
    if provider_name not in ("mock_a", "mock_b"):
        raise HTTPException(status_code=404, detail="Provider not found")
    set_provider_outage(provider_name, payload.is_outage)
    action = "triggered OUTAGE on" if payload.is_outage else "RESTORED"
    return {
        "provider": provider_name,
        "is_outage": payload.is_outage,
        "message": f"Successfully {action} {provider_name}"
    }

@router.post("/{provider_name}/reset-circuit")
def reset_circuit(provider_name: str):
    if provider_name not in ("mock_a", "mock_b"):
        raise HTTPException(status_code=404, detail="Provider not found")
    cb = get_circuit_breaker(provider_name)
    cb.reset()
    return {"provider": provider_name, "circuit_state": cb.state.value}
