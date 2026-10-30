"""
Predictive Pacing Engine

Mathematical Formulation:
  1. Effective Answer Rate (Exponential Smoothing):
       R_eff = alpha * R_recent + (1 - alpha) * R_hist
  2. Conservative Safety Margin Adjustment:
       R_adj = min(1.0, max(0.05, R_eff * (1.0 + safety_margin)))
  3. Capacity Headroom:
       Expected completions over lookahead window Delta_t:
         E_free = (C_connected * Delta_t) / max(30, T_talk)
       Net available target slots:
         A_target = max(0, A_available + E_free - C_ringing)
  4. Proposed Launch Batch:
       N_proposed = floor(A_target / R_adj)

Mandate:
  The Predictive Engine proposes dialing volume based on empirical performance,
  but NEVER initiates calls directly. All proposals are dispatched to the Safety Controller.
"""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import math
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select, func, case

from backend.app.models.enums import AgentState, CallState
from backend.app.models.agent import Agent
from backend.app.models.call import Call
from backend.app.models.campaign import Campaign

logger = logging.getLogger("smartdialer.predictive_engine")

@dataclass
class PacingProposal:
    campaign_id: str
    proposed_calls: int
    effective_answer_rate: float
    rolling_answer_rate: float
    historical_answer_rate: float
    available_agents: int
    connected_calls: int
    ringing_calls: int
    avg_duration_sec: float
    reason: str

class PredictivePacingEngine:
    def __init__(
        self,
        alpha_smoothing: float = 0.3,
        lookahead_window_sec: float = 15.0,
        default_historical_answer_rate: float = 0.20
    ):
        self.alpha_smoothing = alpha_smoothing
        self.lookahead_window_sec = lookahead_window_sec
        self.default_historical_answer_rate = default_historical_answer_rate

    def calculate_rolling_answer_rate(
        self,
        db: Session,
        campaign_id: str | None = None,
        lookback_minutes: int = 15
    ) -> float:
        """
        Calculates recent rolling answer rate over the last lookback_minutes.
        """
        since = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
        query = select(Call).where(Call.completed_at >= since)
        if campaign_id:
            query = query.where(Call.campaign_id == campaign_id)

        completed_calls = db.scalars(query).all()
        if not completed_calls or len(completed_calls) < 5:
            return self.default_historical_answer_rate

        answered = sum(1 for c in completed_calls if c.terminal_reason in ("NORMAL_HANGUP", "ANSWERED_NORMAL", "ANSWERED"))
        return round(answered / len(completed_calls), 4)

    def calculate_historical_answer_rate(
        self,
        db: Session,
        campaign_id: str | None = None
    ) -> float:
        """
        Calculates baseline historical answer rate from completed records.
        """
        query = select(
            func.count(Call.call_id).label("total"),
            func.sum(
                case((Call.answered_at.isnot(None), 1), else_=0)
            ).label("answered")
        )
        if campaign_id:
            query = query.where(Call.campaign_id == campaign_id)

        row = db.execute(query).one_or_none()
        if row and row.total and row.total > 0:
            answered_cnt = row.answered or 0
            return round(answered_cnt / row.total, 4)
        return self.default_historical_answer_rate

    def calculate_avg_talk_duration(
        self,
        db: Session,
        campaign_id: str | None = None
    ) -> float:
        query = select(func.avg(Call.duration_sec)).where(
            Call.answered_at.isnot(None),
            Call.duration_sec > 0
        )
        if campaign_id:
            query = query.where(Call.campaign_id == campaign_id)
        avg_dur = db.scalar(query)
        return float(avg_dur) if avg_dur else 120.0

    def generate_proposal(
        self,
        db: Session,
        campaign_id: str
    ) -> PacingProposal:
        """
        Calculates optimal proposed calls using the rule-based pacing model.
        """
        campaign = db.get(Campaign, campaign_id)
        safety_margin = campaign.safety_margin if campaign else 0.15

        # 1. Metric aggregation
        available_agents = db.scalar(
            select(func.count(Agent.agent_id))
            .where(Agent.status == AgentState.AVAILABLE.value)
        ) or 0

        connected_calls = db.scalar(
            select(func.count(Call.call_id))
            .where(Call.state == CallState.CONNECTED.value)
        ) or 0

        ringing_calls = db.scalar(
            select(func.count(Call.call_id))
            .where(Call.state.in_([CallState.INITIATED.value, CallState.RINGING.value, CallState.RESERVED.value]))
        ) or 0

        r_hist = self.calculate_historical_answer_rate(db, campaign_id)
        r_recent = self.calculate_rolling_answer_rate(db, campaign_id)
        avg_talk_time = self.calculate_avg_talk_duration(db, campaign_id)

        # 2. Mathematical calculation
        # Smoothed answer rate
        r_eff = (self.alpha_smoothing * r_recent) + ((1.0 - self.alpha_smoothing) * r_hist)
        # Apply conservative safety margin (reduces over-dialing risk)
        r_adj = min(1.0, max(0.05, r_eff * (1.0 + safety_margin)))

        # Expected agents freeing up over lookahead window
        expected_free_agents = (connected_calls * self.lookahead_window_sec) / max(30.0, avg_talk_time)
        net_capacity = max(0.0, available_agents + expected_free_agents - ringing_calls)

        # Propose pacing batch
        if net_capacity <= 0 or available_agents <= 0:
            proposed = 0
            reason = f"No capacity: Available={available_agents}, Ringing={ringing_calls}"
        else:
            # Overdial factor = 1.0 / r_adj
            proposed = math.floor(net_capacity / r_adj)
            # Bound proposal to sensible operational limit
            proposed = min(proposed, available_agents * 3)
            reason = (
                f"Pacing calculation: net_cap={net_capacity:.1f}, "
                f"R_eff={r_eff:.2%}, R_adj={r_adj:.2%}, Overdial={1.0/r_adj:.2f}x"
            )

        proposal = PacingProposal(
            campaign_id=campaign_id,
            proposed_calls=proposed,
            effective_answer_rate=round(r_eff, 4),
            rolling_answer_rate=round(r_recent, 4),
            historical_answer_rate=round(r_hist, 4),
            available_agents=available_agents,
            connected_calls=connected_calls,
            ringing_calls=ringing_calls,
            avg_duration_sec=round(avg_talk_time, 1),
            reason=reason
        )

        logger.info(f"Predictive Engine Proposal for {campaign_id}: {proposed} calls. ({reason})")
        return proposal
