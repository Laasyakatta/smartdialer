"""
Telecom Provider Pydantic Schemas
"""
from __future__ import annotations
from pydantic import BaseModel


class ProviderStatusResponse(BaseModel):
    name: str
    is_outage: bool
    circuit_state: str
    failures: int
    can_execute: bool


class OutageToggleRequest(BaseModel):
    is_outage: bool
