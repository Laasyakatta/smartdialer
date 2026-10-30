"""
Call Pydantic Schemas
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class TriggerDialRequest(BaseModel):
    campaign_id: str = Field(min_length=1, max_length=50)
    provider_name: Literal["mock_a", "mock_b"] = "mock_a"
    batch_size: int = Field(default=10, ge=1, le=100)
    answer_probability: float = Field(default=0.20, ge=0.0, le=1.0)
    talk_time_sec: int = Field(default=60, ge=1, le=3600)


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
