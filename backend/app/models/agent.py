"""
Agent Data Models
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Integer, Index
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.enums import AgentState

def utc_now():
    return datetime.now(timezone.utc)

class Agent(Base):
    __tablename__ = "agents"

    agent_id = Column(String(50), primary_key=True, index=True)
    employee_code = Column(String(50), index=True, nullable=True)
    agent_name = Column(String(100), nullable=False)
    vendor_id = Column(String(50), index=True, nullable=True)
    team = Column(String(50), nullable=True)
    status = Column(String(20), default=AgentState.AVAILABLE.value, nullable=False, index=True)
    current_call_id = Column(String(50), nullable=True)
    reserved_at = Column(DateTime, nullable=True)
    last_status_change = Column(DateTime, default=utc_now, nullable=False)
    joined_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    is_simulation = Column(Boolean, default=False, nullable=False, index=True)
    simulation_id = Column(String(50), nullable=True, index=True)

    __table_args__ = (
        Index("ix_agent_status_sim", "status", "is_simulation"),
    )

class AgentSession(Base):
    __tablename__ = "agent_sessions"

    session_id = Column(String(50), primary_key=True)
    agent_id = Column(String(50), ForeignKey("agents.agent_id"), index=True, nullable=False)
    login_at = Column(DateTime, nullable=False)
    logout_at = Column(DateTime, nullable=True)
    channel = Column(String(50), nullable=True)
    device_id = Column(String(100), nullable=True)
    timezone = Column(String(50), nullable=True)

class AgentAuditHistory(Base):
    __tablename__ = "agent_audit_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(50), index=True, nullable=False)
    employee_code = Column(String(50), nullable=True)
    agent_name = Column(String(100), nullable=True)
    vendor_id = Column(String(50), nullable=True)
    team = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False)
    joined_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False)
