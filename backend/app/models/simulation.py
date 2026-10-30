"""
Simulation Run Data Model
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, Text
from backend.app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    simulation_id = Column(String(50), primary_key=True, index=True)
    scenario_name = Column(String(100), nullable=False)
    status = Column(String(30), default="PENDING", nullable=False)
    dialing_mode = Column(String(30), default="PROGRESSIVE", nullable=False)
    
    # Input parameters
    agent_count = Column(Integer, default=50, nullable=False)
    borrower_pool_size = Column(Integer, default=200, nullable=False)
    simulated_answer_rate = Column(Float, default=0.20, nullable=False)
    simulated_avg_talk_time = Column(Integer, default=120, nullable=False)
    provider_name = Column(String(50), default="mock_a", nullable=False)
    
    # Output metrics
    calls_initiated = Column(Integer, default=0, nullable=False)
    calls_answered = Column(Integer, default=0, nullable=False)
    calls_connected = Column(Integer, default=0, nullable=False)
    calls_completed = Column(Integer, default=0, nullable=False)
    calls_failed = Column(Integer, default=0, nullable=False)
    calls_abandoned = Column(Integer, default=0, nullable=False)
    
    agent_utilization = Column(Float, default=0.0, nullable=False)
    avg_wait_time_sec = Column(Float, default=0.0, nullable=False)
    
    safety_approvals = Column(Integer, default=0, nullable=False)
    safety_reductions = Column(Integer, default=0, nullable=False)
    safety_rejections = Column(Integer, default=0, nullable=False)
    max_concurrent_calls = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    metrics_json = Column(Text, nullable=True)
