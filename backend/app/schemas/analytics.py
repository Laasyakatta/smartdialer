"""
Analytics Pydantic Schemas
"""
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel


class OverviewKPIsResponse(BaseModel):
    total_calls: int
    answered_calls: int
    overall_answer_rate: float
    failure_rate: float
    no_answer_rate: float
    busy_rate: float
    voicemail_rate: float
    avg_talk_duration_sec: float
    total_borrowers: int
    eligible_borrowers: int
    total_agents: int
    available_agents: int
    offline_agents: int
    total_accounts: int
    total_campaigns: int
    attempts_per_borrower: float


class VendorPerformanceResponse(BaseModel):
    vendor_id: Optional[str] = None
    total_calls: int
    answered_calls: int
    answer_rate: float
    failure_rate: float


class CallDispositionResponse(BaseModel):
    status: str
    count: int


class CampaignAnalyticsResponse(BaseModel):
    campaign_id: Optional[str] = None
    campaign_name: str
    total_calls: int
    answered_calls: int
    answer_rate: float
    avg_duration_sec: float
