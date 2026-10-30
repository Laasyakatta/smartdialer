"""
Campaign Pydantic Schemas
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator

from backend.app.models.enums import DialingMode


class DialingModeUpdateRequest(BaseModel):
    mode: str

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        v_up = v.upper()
        valid = [m.value for m in DialingMode]
        if v_up not in valid:
            raise ValueError(f"mode must be one of {valid}")
        return v_up


class CampaignResponse(BaseModel):
    campaign_id: str
    campaign_name: str
    channel: Optional[str] = None
    strategy_version: Optional[str] = None
    dialing_mode: str
    is_active: bool
    max_concurrent_calls: int
    target_answer_rate: float
    safety_margin: float

    model_config = {"from_attributes": True}


class CampaignListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[CampaignResponse]


class CampaignPerformanceResponse(BaseModel):
    campaign_id: Optional[str] = None
    campaign_name: str
    total_calls: int
    answered_calls: int
    answer_rate: float
    avg_duration_sec: float
