"""
Safety Controller Pydantic Schemas
"""
from __future__ import annotations
from typing import List, Dict, Any
from pydantic import BaseModel


class AgentCapacity(BaseModel):
    available: int
    reserved: int
    dialing: int
    connected: int
    usable_slots_headroom: int


class CallCapacity(BaseModel):
    in_flight_pre_connect: int
    connected_talkers: int


class ProviderHealth(BaseModel):
    name: str
    is_outage: bool
    circuit_state: str
    failures: int
    can_execute: bool


class SafetyStatusResponse(BaseModel):
    safety_guard_active: bool
    bypass_allowed: bool
    agent_capacity: AgentCapacity
    call_capacity: CallCapacity
    providers_health: List[ProviderHealth]
    system_ready_to_dial: bool
