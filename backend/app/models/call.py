"""
Call & Allocation Data Models
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Index
from backend.app.core.database import Base
from backend.app.models.enums import CallState

def utc_now():
    return datetime.now(timezone.utc)

class Call(Base):
    __tablename__ = "calls"

    call_id = Column(String(50), primary_key=True, index=True)
    campaign_id = Column(String(50), index=True, nullable=True)
    account_id = Column(String(50), index=True, nullable=False)
    borrower_id = Column(String(50), index=True, nullable=False)
    agent_id = Column(String(50), index=True, nullable=True)
    vendor_id = Column(String(50), nullable=True)
    provider_name = Column(String(50), default="mock_a", nullable=False)
    direction = Column(String(20), default="OUTBOUND", nullable=False)
    state = Column(String(30), default=CallState.QUEUED.value, nullable=False, index=True)
    terminal_reason = Column(String(100), nullable=True)
    duration_sec = Column(Integer, default=0, nullable=False)
    
    # Lifecycle Timestamps
    queued_at = Column(DateTime, default=utc_now, nullable=False)
    reserved_at = Column(DateTime, nullable=True)
    initiated_at = Column(DateTime, nullable=True)
    ringing_at = Column(DateTime, nullable=True)
    answered_at = Column(DateTime, nullable=True)
    connected_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Metadata
    timezone = Column(String(50), nullable=True)
    is_simulation = Column(Boolean, default=False, nullable=False, index=True)
    simulation_id = Column(String(50), nullable=True, index=True)

    __table_args__ = (
        Index("ix_call_state_sim", "state", "is_simulation"),
        Index("ix_call_campaign_state", "campaign_id", "state"),
    )

class CallAttempt(Base):
    __tablename__ = "call_attempts"

    attempt_id = Column(String(50), primary_key=True, index=True)
    call_id = Column(String(50), index=True, nullable=False)
    account_id = Column(String(50), nullable=False)
    borrower_id = Column(String(50), nullable=False)
    agent_id = Column(String(50), nullable=True)
    attempt_no = Column(Integer, default=1, nullable=False)
    vendor_id = Column(String(50), nullable=True)
    attempt_status = Column(String(50), nullable=False)
    event_at = Column(DateTime, default=utc_now, nullable=False)

class CallDisposition(Base):
    __tablename__ = "call_dispositions"

    disposition_id = Column(String(50), primary_key=True, index=True)
    call_id = Column(String(50), index=True, nullable=False)
    account_id = Column(String(50), nullable=False)
    borrower_id = Column(String(50), nullable=False)
    agent_id = Column(String(50), nullable=True)
    disposition_code = Column(String(50), nullable=False, index=True)
    raw_disposition_code = Column(String(50), nullable=True)
    disposition_version = Column(String(20), nullable=True)
    event_at = Column(DateTime, default=utc_now, nullable=False)

class CallAllocation(Base):
    __tablename__ = "call_allocations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_id = Column(String(50), index=True, nullable=False)
    agent_id = Column(String(50), index=True, nullable=False)
    borrower_id = Column(String(50), index=True, nullable=False)
    allocated_at = Column(DateTime, default=utc_now, nullable=False)
    released_at = Column(DateTime, nullable=True)
    status = Column(String(30), default="ACTIVE", nullable=False)
