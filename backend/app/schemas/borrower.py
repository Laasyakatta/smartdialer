"""
Borrower Pydantic Schemas
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class BorrowerResponse(BaseModel):
    borrower_id: str
    name: str
    phone_masked: Optional[str] = None
    email_masked: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    is_eligible: bool
    ineligibility_reason: Optional[str] = None
    current_active_call_id: Optional[str] = None

    model_config = {"from_attributes": True}


class BorrowerListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[BorrowerResponse]
