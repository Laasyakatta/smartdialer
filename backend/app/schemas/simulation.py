"""
Simulation Pydantic Schemas
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator


VALID_SCENARIOS = ["Scenario A", "Scenario B", "Scenario C", "Scenario D"]


class SimulationRunRequest(BaseModel):
    scenario: str = "Scenario A"
    dialing_mode: str = "PROGRESSIVE"
    agent_count: int = 30
    cycles: int = 4
    provider_name: str = "mock_a"
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

    @field_validator("agent_count")
    @classmethod
    def validate_agent_count(cls, v: int) -> int:
        if not 1 <= v <= 500:
            raise ValueError("agent_count must be between 1 and 500")
        return v

    @field_validator("cycles")
    @classmethod
    def validate_cycles(cls, v: int) -> int:
        if not 1 <= v <= 20:
            raise ValueError("cycles must be between 1 and 20")
        return v


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
