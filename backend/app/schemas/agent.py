"""
Agent Pydantic Schemas
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator

from backend.app.models.enums import AgentState


class AgentStatusUpdateRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        v_up = v.upper()
        valid = [s.value for s in AgentState]
        if v_up not in valid:
            raise ValueError(f"status must be one of {valid}")
        return v_up


class DisconnectBatchRequest(BaseModel):
    count: int = 20


class AgentResponse(BaseModel):
    agent_id: str
    agent_name: str
    employee_code: Optional[str] = None
    vendor_id: Optional[str] = None
    team: Optional[str] = None
    status: str
    current_call_id: Optional[str] = None
    reserved_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[AgentResponse]


class AgentSessionResponse(BaseModel):
    session_id: str
    agent_id: str
    login_at: datetime
    logout_at: Optional[datetime] = None
    channel: Optional[str] = None

    model_config = {"from_attributes": True}
