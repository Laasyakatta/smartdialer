"""
Borrower Data Models
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Index
from backend.app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Borrower(Base):
    __tablename__ = "borrowers"

    borrower_id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=True, index=True)
    email = Column(String(120), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    is_eligible = Column(Boolean, default=True, nullable=False, index=True)
    ineligibility_reason = Column(String(200), nullable=True)
    current_active_call_id = Column(String(50), nullable=True, index=True)
    reserved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    is_simulation = Column(Boolean, default=False, nullable=False, index=True)

    __table_args__ = (
        Index("ix_borrower_eligible_active", "is_eligible", "current_active_call_id"),
    )

class BorrowerAuditHistory(Base):
    __tablename__ = "borrower_audit_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    borrower_id = Column(String(50), index=True, nullable=False)
    name = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(120), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
