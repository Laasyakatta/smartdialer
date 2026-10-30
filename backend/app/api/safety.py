"""
Independent Safety Controller Monitoring API Router
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from backend.app.core.database import get_db
from backend.app.models.agent import Agent
from backend.app.models.call import Call
from backend.app.models.enums import AgentState, CallState
from backend.app.providers import get_all_provider_statuses

router = APIRouter(prefix="/safety", tags=["safety"])

@router.get("/status")
def get_safety_status(db: Session = Depends(get_db)):
    """
    Returns real-time capacity and health checks tracked by the Safety Controller.
    """
    available_agents = db.scalar(
        select(func.count(Agent.agent_id)).where(Agent.status == AgentState.AVAILABLE.value)
    ) or 0

    reserved_agents = db.scalar(
        select(func.count(Agent.agent_id)).where(Agent.status == AgentState.RESERVED.value)
    ) or 0

    dialing_agents = db.scalar(
        select(func.count(Agent.agent_id)).where(Agent.status == AgentState.DIALING.value)
    ) or 0

    connected_agents = db.scalar(
        select(func.count(Agent.agent_id)).where(Agent.status == AgentState.CONNECTED.value)
    ) or 0

    # In-flight calls
    in_flight_calls = db.scalar(
        select(func.count(Call.call_id))
        .where(Call.state.in_([CallState.RESERVED.value, CallState.INITIATED.value, CallState.RINGING.value]))
    ) or 0

    active_connected_calls = db.scalar(
        select(func.count(Call.call_id)).where(Call.state == CallState.CONNECTED.value)
    ) or 0

    # Hard capacity formula: Usable agent slots
    usable_slots = max(0, available_agents - in_flight_calls)

    providers = get_all_provider_statuses()
    is_any_provider_healthy = any(p["can_execute"] and not p["is_outage"] for p in providers)

    return {
        "safety_guard_active": True,
        "bypass_allowed": False,  # Architectural invariant: Cannot be disabled
        "agent_capacity": {
            "available": available_agents,
            "reserved": reserved_agents,
            "dialing": dialing_agents,
            "connected": connected_agents,
            "usable_slots_headroom": usable_slots
        },
        "call_capacity": {
            "in_flight_pre_connect": in_flight_calls,
            "connected_talkers": active_connected_calls
        },
        "providers_health": providers,
        "system_ready_to_dial": is_any_provider_healthy and usable_slots > 0
    }
