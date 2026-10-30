"""
Collections Extended Domain Models & Ingestion Audit Log
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, Index
from backend.app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(String(50), primary_key=True, index=True)
    account_id = Column(String(50), index=True, nullable=False)
    borrower_id = Column(String(50), index=True, nullable=False)
    event_at = Column(DateTime, nullable=False)
    payment_reference = Column(String(100), nullable=True)
    amount = Column(Float, default=0.0)
    payment_status = Column(String(50), nullable=False)
    payment_method = Column(String(50), nullable=True)
    provider_id = Column(String(50), nullable=True)

class PromiseToPay(Base):
    __tablename__ = "promises_to_pay"

    ptp_id = Column(String(50), primary_key=True, index=True)
    account_id = Column(String(50), index=True, nullable=False)
    borrower_id = Column(String(50), index=True, nullable=False)
    event_at = Column(DateTime, nullable=False)
    agent_id = Column(String(50), nullable=True)
    promised_amount = Column(Float, default=0.0)
    promised_date = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False)
    source = Column(String(50), nullable=True)

class Complaint(Base):
    __tablename__ = "complaints"

    complaint_id = Column(String(50), primary_key=True, index=True)
    account_id = Column(String(50), index=True, nullable=False)
    borrower_id = Column(String(50), index=True, nullable=False)
    event_at = Column(DateTime, default=utc_now, nullable=True)
    complaint_type = Column(String(50), nullable=False)
    severity = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    source = Column(String(50), nullable=True)
    resolution_at = Column(DateTime, nullable=True)

class FieldVisit(Base):
    __tablename__ = "field_visits"

    visit_id = Column(String(50), primary_key=True, index=True)
    account_id = Column(String(50), index=True, nullable=False)
    borrower_id = Column(String(50), index=True, nullable=False)
    event_at = Column(DateTime, nullable=False)
    agent_id = Column(String(50), nullable=True)
    visit_type = Column(String(50), nullable=False)
    outcome = Column(String(50), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    scheduled_at = Column(DateTime, nullable=True)

class SmsEvent(Base):
    __tablename__ = "sms_events"

    sms_event_id = Column(String(50), primary_key=True, index=True)
    account_id = Column(String(50), index=True, nullable=False)
    borrower_id = Column(String(50), index=True, nullable=False)
    event_at = Column(DateTime, nullable=False)
    message_id = Column(String(100), nullable=True)
    event_type = Column(String(50), nullable=False)
    template_code = Column(String(50), nullable=True)
    provider_id = Column(String(50), nullable=True)

class WhatsappEvent(Base):
    __tablename__ = "whatsapp_events"

    whatsapp_event_id = Column(String(50), primary_key=True, index=True)
    account_id = Column(String(50), index=True, nullable=False)
    borrower_id = Column(String(50), index=True, nullable=False)
    event_at = Column(DateTime, nullable=False)
    message_id = Column(String(100), nullable=True)
    event_type = Column(String(50), nullable=False)
    template_code = Column(String(50), nullable=True)
    provider_id = Column(String(50), nullable=True)

class VendorTelephony(Base):
    __tablename__ = "vendor_telephony"

    vendor_id = Column(String(50), primary_key=True, index=True)
    vendor_name = Column(String(100), nullable=False)
    vendor_account_id = Column(String(100), nullable=True)
    timezone = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False)
    schema_version = Column(String(50), nullable=True)

class IngestionAuditLog(Base):
    __tablename__ = "ingestion_audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(50), index=True, nullable=False)
    row_identifier = Column(String(100), index=True, nullable=True)
    issue_type = Column(String(50), nullable=False)
    details = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
