"""
Account Data Models
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, ForeignKey, Index
from backend.app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Account(Base):
    __tablename__ = "accounts"

    account_id = Column(String(50), primary_key=True, index=True)
    borrower_id = Column(String(50), index=True, nullable=True)  # Indexed soft reference to allow orphaned records
    loan_type = Column(String(50), nullable=True)
    principal_amount = Column(Float, default=0.0)
    outstanding_amount = Column(Float, default=0.0)
    dpd = Column(Integer, default=0, index=True)
    risk_segment = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, index=True)
    opened_at = Column(DateTime, nullable=True)
    timezone = Column(String(50), nullable=True)
    schema_version = Column(String(20), nullable=True)
    is_orphaned = Column(Boolean, default=False, nullable=False, index=True)

class AccountStatusHistory(Base):
    __tablename__ = "account_status_history"

    history_id = Column(String(50), primary_key=True)
    account_id = Column(String(50), ForeignKey("accounts.account_id"), index=True, nullable=False)
    borrower_id = Column(String(50), nullable=True, index=True)
    event_at = Column(DateTime, nullable=False)
    status = Column(String(50), nullable=False)
    changed_by = Column(String(50), nullable=True)
    source = Column(String(50), nullable=True)
    recorded_at = Column(DateTime, default=utc_now, nullable=False)
