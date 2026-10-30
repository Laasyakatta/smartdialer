"""
Call Pydantic Schemas
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator


class TriggerDialRequest(BaseModel):
    campaign_id: str
    provider_name: str = "mock_a"
    batch_size: int = 10
    answer_probability: float = 0.20
    talk_time_sec: int = 60

    @field_validator("provider_name")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        if v not in ("mock_a", "mock_b"):
            raise ValueError("provider_name must be 'mock_a' or 'mock_b'")
        return v

    @field_validator("answer_probability")
    @classmethod
    def validate_probability(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("answer_probability must be between 0.0 and 1.0")
        return v


class CallResponse(BaseModel):
    call_id: str
    campaign_id: Optional[str] = None
    account_id: str
    borrower_id: str
    agent_id: Optional[str] = None
    provider_name: str
    direction: str
    state: str
    terminal_reason: Optional[str] = None
    duration_sec: int
    queued_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    is_simulation: bool

    model_config = {"from_attributes": True}


class CallListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[CallResponse]
