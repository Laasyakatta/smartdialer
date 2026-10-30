"""
Historical Collections Analytics Service
Calculates empirical KPIs from the imported dataset.
"""
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, case

from backend.app.models.call import Call, CallAttempt
from backend.app.models.agent import Agent, AgentSession
from backend.app.models.borrower import Borrower
from backend.app.models.account import Account
from backend.app.models.campaign import Campaign

class AnalyticsService:
    @staticmethod
    def get_overview_kpis(db: Session) -> dict:
        """
        Global operational & historical KPIs.
        """
        total_calls = db.scalar(select(func.count(Call.call_id))) or 0
        answered_calls = db.scalar(
            select(func.count(Call.call_id)).where(Call.answered_at.isnot(None))
        ) or 0
        failed_calls = db.scalar(
            select(func.count(Call.call_id)).where(Call.terminal_reason == "PROVIDER_FAILED")
        ) or 0
        no_answer_calls = db.scalar(
            select(func.count(Call.call_id)).where(Call.terminal_reason == "NO_ANSWER")
        ) or 0
        busy_calls = db.scalar(
            select(func.count(Call.call_id)).where(Call.terminal_reason == "BUSY")
        ) or 0
        voicemail_calls = db.scalar(
            select(func.count(Call.call_id)).where(Call.terminal_reason == "VOICEMAIL")
        ) or 0

        avg_duration = db.scalar(
            select(func.avg(Call.duration_sec)).where(Call.answered_at.isnot(None))
        ) or 0.0

        total_borrowers = db.scalar(select(func.count(Borrower.borrower_id))) or 0
        eligible_borrowers = db.scalar(
            select(func.count(Borrower.borrower_id)).where(Borrower.is_eligible.is_(True))
        ) or 0

        total_agents = db.scalar(select(func.count(Agent.agent_id))) or 0
        available_agents = db.scalar(
            select(func.count(Agent.agent_id)).where(Agent.status == "AVAILABLE")
        ) or 0
        offline_agents = db.scalar(
            select(func.count(Agent.agent_id)).where(Agent.status == "OFFLINE")
        ) or 0

        total_accounts = db.scalar(select(func.count(Account.account_id))) or 0
        total_campaigns = db.scalar(select(func.count(Campaign.campaign_id))) or 0

        total_attempts = db.scalar(select(func.count(CallAttempt.attempt_id))) or 0
        attempts_per_borrower = round(total_attempts / total_borrowers, 2) if total_borrowers > 0 else 0.0

        return {
            "total_calls": total_calls,
            "answered_calls": answered_calls,
            "overall_answer_rate": round((answered_calls / total_calls) * 100, 2) if total_calls > 0 else 0.0,
            "failure_rate": round((failed_calls / total_calls) * 100, 2) if total_calls > 0 else 0.0,
            "no_answer_rate": round((no_answer_calls / total_calls) * 100, 2) if total_calls > 0 else 0.0,
            "busy_rate": round((busy_calls / total_calls) * 100, 2) if total_calls > 0 else 0.0,
            "voicemail_rate": round((voicemail_calls / total_calls) * 100, 2) if total_calls > 0 else 0.0,
            "avg_talk_duration_sec": round(avg_duration, 1),
            "total_borrowers": total_borrowers,
            "eligible_borrowers": eligible_borrowers,
            "total_agents": total_agents,
            "available_agents": available_agents,
            "offline_agents": offline_agents,
            "total_accounts": total_accounts,
            "total_campaigns": total_campaigns,
            "attempts_per_borrower": attempts_per_borrower,
        }

    @staticmethod
    def get_campaign_performance(db: Session, limit: int = 15) -> list[dict]:
        """
        Campaign-wise performance metrics.
        """
        query = (
            select(
                Call.campaign_id,
                Campaign.campaign_name,
                func.count(Call.call_id).label("total_calls"),
                func.sum(case((Call.answered_at.isnot(None), 1), else_=0)).label("answered_calls"),
                func.avg(Call.duration_sec).label("avg_duration")
            )
            .outerjoin(Campaign, Call.campaign_id == Campaign.campaign_id)
            .where(Call.campaign_id.isnot(None))
            .group_by(Call.campaign_id, Campaign.campaign_name)
            .order_by(desc("total_calls"))
            .limit(limit)
        )
        results = db.execute(query).all()
        data = []
        for row in results:
            tot = row.total_calls or 0
            ans = row.answered_calls or 0
            rate = round((ans / tot) * 100, 2) if tot > 0 else 0.0
            data.append({
                "campaign_id": row.campaign_id,
                "campaign_name": row.campaign_name or row.campaign_id,
                "total_calls": tot,
                "answered_calls": ans,
                "answer_rate": rate,
                "avg_duration_sec": round(row.avg_duration or 0.0, 1)
            })
        return data

    @staticmethod
    def get_vendor_performance(db: Session) -> list[dict]:
        """
        Telephony vendor performance metrics.
        """
        query = (
            select(
                Call.vendor_id,
                func.count(Call.call_id).label("total_calls"),
                func.sum(case((Call.answered_at.isnot(None), 1), else_=0)).label("answered_calls"),
                func.sum(case((Call.terminal_reason == "PROVIDER_FAILED", 1), else_=0)).label("failed_calls")
            )
            .where(Call.vendor_id.isnot(None))
            .group_by(Call.vendor_id)
            .order_by(desc("total_calls"))
        )
        results = db.execute(query).all()
        data = []
        for row in results:
            tot = row.total_calls or 0
            ans = row.answered_calls or 0
            fail = row.failed_calls or 0
            data.append({
                "vendor_id": row.vendor_id,
                "total_calls": tot,
                "answered_calls": ans,
                "answer_rate": round((ans / tot) * 100, 2) if tot > 0 else 0.0,
                "failure_rate": round((fail / tot) * 100, 2) if tot > 0 else 0.0
            })
        return data

    @staticmethod
    def get_call_disposition_breakdown(db: Session) -> list[dict]:
        """
        Aggregated outcomes distribution.
        """
        query = (
            select(Call.terminal_reason, func.count(Call.call_id).label("count"))
            .group_by(Call.terminal_reason)
            .order_by(desc("count"))
        )
        res = db.execute(query).all()
        return [{"status": r.terminal_reason or "UNKNOWN", "count": r.count} for r in res]
