"""
Unit Tests for Predictive Pacing Engine & Mathematical Model
"""
import pytest
from backend.app.models.agent import Agent
from backend.app.models.campaign import Campaign
from backend.app.models.enums import AgentState
from backend.app.services.predictive_engine import PredictivePacingEngine

def test_predictive_pacing_calculation_with_agents(test_db):
    # Add 10 available agents
    for i in range(10):
        test_db.add(Agent(
            agent_id=f"AGT_PRED_{i}",
            agent_name=f"Agent {i}",
            status=AgentState.AVAILABLE.value
        ))
    test_db.add(Campaign(
        campaign_id="CMP_PRED_1",
        campaign_name="Predictive Test",
        target_answer_rate=0.20,
        safety_margin=0.15
    ))
    test_db.commit()

    engine = PredictivePacingEngine(default_historical_answer_rate=0.20)
    proposal = engine.generate_proposal(test_db, "CMP_PRED_1")

    # With 10 agents, R_eff ~ 0.20, R_adj ~ 0.23 -> Overdial ~ 4.3x
    # Net capacity = 10 -> proposed ~ floor(10 / 0.23) ~ 43 bounded by 3x available agents (30)
    assert proposal.available_agents == 10
    assert proposal.proposed_calls > 10  # Must propose more than 10 due to overdialing
    assert proposal.effective_answer_rate == 0.20

def test_predictive_pacing_zero_agents_proposes_zero(test_db):
    test_db.add(Campaign(
        campaign_id="CMP_PRED_2",
        campaign_name="Zero Agent Test",
        target_answer_rate=0.20,
        safety_margin=0.15
    ))
    test_db.commit()

    engine = PredictivePacingEngine()
    proposal = engine.generate_proposal(test_db, "CMP_PRED_2")

    assert proposal.available_agents == 0
    assert proposal.proposed_calls == 0
