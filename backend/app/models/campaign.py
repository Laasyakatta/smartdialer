"""
Campaign & Targeting Data Models
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, ForeignKey, Index
from backend.app.core.database import Base
from backend.app.models.enums import DialingMode

def utc_now():
    return datetime.now(timezone.utc)

class Campaign(Base):
    __tablename__ = "campaigns"

    campaign_id = Column(String(50), primary_key=True, index=True)
    campaign_name = Column(String(150), nullable=False)
    channel = Column(String(50), nullable=True)
    strategy_version = Column(String(50), nullable=True)
    dialing_mode = Column(String(20), default=DialingMode.PROGRESSIVE.value, nullable=False)
    target_definition = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    start_at = Column(DateTime, nullable=True)
    end_at = Column(DateTime, nullable=True)
    max_concurrent_calls = Column(Integer, default=50, nullable=False)
    target_answer_rate = Column(Float, default=0.20, nullable=False)
    safety_margin = Column(Float, default=0.15, nullable=False)
    is_simulation = Column(Boolean, default=False, nullable=False)

class DailyTargeting(Base):
    __tablename__ = "daily_targeting"

    target_id = Column(String(50), primary_key=True, index=True)
    account_id = Column(String(50), ForeignKey("accounts.account_id"), index=True, nullable=False)
    campaign_id = Column(String(50), ForeignKey("campaigns.campaign_id"), index=True, nullable=False)
    target_date = Column(DateTime, nullable=False, index=True)
    priority = Column(Integer, default=1, index=True)
    recommended_channel = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, index=True)
