"""
Simulation API Router
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.models.simulation import SimulationRun
from backend.app.services.simulation_engine import SimulationEngine, SCENARIO_CONFIGS

router = APIRouter(prefix="/simulation", tags=["simulation"])

class RunSimulationRequest(BaseModel):
    scenario: str = "Scenario A"
    dialing_mode: str = "PROGRESSIVE"
    agent_count: int = 30
    cycles: int = 4
    provider_name: str = "mock_a"
    seed: int = 42

@router.get("/scenarios")
def list_available_scenarios():
    return [
        {"name": k, "description": v["description"], "base_answer_rate": v["answer_rate"], "base_talk_time": v["avg_talk_time"]}
        for k, v in SCENARIO_CONFIGS.items()
    ]

@router.post("/run")
def run_simulation(payload: RunSimulationRequest, db: Session = Depends(get_db)):
    try:
        run = SimulationEngine.run_simulation(
            db=db,
            scenario_key=payload.scenario,
            dialing_mode=payload.dialing_mode,
            agent_count=payload.agent_count,
            cycles=payload.cycles,
            provider_name=payload.provider_name,
            random_seed=payload.seed
        )
        return {
            "simulation_id": run.simulation_id,
            "scenario": run.scenario_name,
            "dialing_mode": run.dialing_mode,
            "calls_initiated": run.calls_initiated,
            "calls_answered": run.calls_answered,
            "calls_completed": run.calls_completed,
            "calls_failed": run.calls_failed,
            "calls_abandoned": run.calls_abandoned,
            "agent_utilization": run.agent_utilization,
            "avg_wait_time_sec": run.avg_wait_time_sec,
            "safety_approvals": run.safety_approvals,
            "safety_reductions": run.safety_reductions,
            "safety_rejections": run.safety_rejections,
            "max_concurrent_calls": run.max_concurrent_calls,
            "status": run.status
        }
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))

@router.get("/history")
def list_simulations(limit: int = 10, db: Session = Depends(get_db)):
    runs = db.scalars(
        select(SimulationRun).order_by(desc(SimulationRun.created_at)).limit(limit)
    ).all()
    return [
        {
            "simulation_id": r.simulation_id,
            "scenario": r.scenario_name,
            "dialing_mode": r.dialing_mode,
            "calls_initiated": r.calls_initiated,
            "calls_answered": r.calls_answered,
            "agent_utilization": r.agent_utilization,
            "safety_approvals": r.safety_approvals,
            "safety_reductions": r.safety_reductions,
            "safety_rejections": r.safety_rejections,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in runs
    ]
