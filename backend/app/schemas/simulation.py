"""
Simulation Pydantic Schemas
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator


VALID_SCENARIOS = ["Scenario A", "Scenario B", "Scenario C", "Scenario D"]


class SimulationRunRequest(BaseModel):
    scenario: str = "Scenario A"
    dialing_mode: str = "PROGRESSIVE"
    agent_count: int = Field(default=30, ge=1, le=500)
    cycles: int = Field(default=4, ge=1, le=20)
    provider_name: Literal["mock_a", "mock_b"] = "mock_a"
    seed: int = 42

    @field_validator("scenario")
    @classmethod
    def validate_scenario(cls, v: str) -> str:
        if v not in VALID_SCENARIOS:
            raise ValueError(f"scenario must be one of {VALID_SCENARIOS}")
        return v

    @field_validator("dialing_mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        v_up = v.upper()
        if v_up not in ("PROGRESSIVE", "PREDICTIVE"):
            raise ValueError("dialing_mode must be 'PROGRESSIVE' or 'PREDICTIVE'")
        return v_up


class SimulationRunResponse(BaseModel):
    simulation_id: str
    scenario: str
    dialing_mode: str
    calls_initiated: int
    calls_answered: int
    calls_completed: int
    calls_failed: int
    calls_abandoned: int
    agent_utilization: float
    avg_wait_time_sec: float
    safety_approvals: int
    safety_reductions: int
    safety_rejections: int
    max_concurrent_calls: int
    status: str


class SimulationHistoryItem(BaseModel):
    simulation_id: str
    scenario: str
    dialing_mode: str
    calls_initiated: int
    calls_answered: int
    agent_utilization: float
    safety_approvals: int
    safety_reductions: int
    safety_rejections: int
    status: str
    created_at: Optional[datetime] = None


class ScenarioInfo(BaseModel):
    name: str
    description: str
    base_answer_rate: float
    base_talk_time: int
