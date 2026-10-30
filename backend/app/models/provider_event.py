"""
Telecom Provider Events Model
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from backend.app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class ProviderEvent(Base):
    __tablename__ = "provider_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_event_id = Column(String(100), unique=True, index=True, nullable=False)
    provider_name = Column(String(50), nullable=False)
    call_id = Column(String(50), index=True, nullable=False)
    event_type = Column(String(50), nullable=False)
    payload = Column(Text, nullable=True)
    received_at = Column(DateTime, default=utc_now, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="RECEIVED", nullable=False, index=True)
    processing_error = Column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_event_call_status", "call_id", "status"),
    )
