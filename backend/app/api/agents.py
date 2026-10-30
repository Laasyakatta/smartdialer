"""
Agent Management API Router
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, update
from pydantic import BaseModel
from datetime import datetime, timezone

from backend.app.core.database import get_db
from backend.app.models.agent import Agent
from backend.app.models.enums import AgentState
from backend.app.services.agent_state_machine import AgentStateMachine

router = APIRouter(prefix="/agents", tags=["agents"])

class AgentStatusUpdate(BaseModel):
    status: str

class DisconnectBatchRequest(BaseModel):
    count: int = 20

@router.get("")
def list_agents(
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = select(Agent)
    if status:
        query = query.where(Agent.status == status.upper())
    
    total = db.scalar(select(func.count(Agent.agent_id)).where(Agent.status == status.upper() if status else True)) or 0
    agents = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "agent_id": a.agent_id,
                "agent_name": a.agent_name,
                "employee_code": a.employee_code,
                "vendor_id": a.vendor_id,
                "team": a.team,
                "status": a.status,
                "current_call_id": a.current_call_id,
                "reserved_at": a.reserved_at.isoformat() if a.reserved_at else None,
                "updated_at": a.updated_at.isoformat() if a.updated_at else None
            }
            for a in agents
        ]
    }

@router.post("/{agent_id}/status")
def update_agent_status(agent_id: str, payload: AgentStatusUpdate, db: Session = Depends(get_db)):
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    try:
        updated = AgentStateMachine.transition(db, agent, payload.status.upper())
        return {
            "agent_id": updated.agent_id,
            "status": updated.status,
            "message": f"Agent status updated to {updated.status}"
        }
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))

@router.post("/disconnect-batch")
def simulate_agent_disconnection(payload: DisconnectBatchRequest, db: Session = Depends(get_db)):
    """
    Simulates sudden agent drop: drops N available agents to OFFLINE to test safety reaction.
    """
    agents = db.scalars(
        select(Agent).where(Agent.status == AgentState.AVAILABLE.value).limit(payload.count)
    ).all()

    dropped = 0
    now = datetime.now(timezone.utc)
    for ag in agents:
        ag.status = AgentState.OFFLINE.value
        ag.last_status_change = now
        dropped += 1
    db.commit()

    return {
        "requested_drop": payload.count,
        "actual_dropped": dropped,
        "message": f"Successfully simulated sudden disconnect of {dropped} agents."
    }
