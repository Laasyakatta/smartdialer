"""
Call Monitoring & Trigger API Router
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
import logging

from backend.app.core.database import get_db
from backend.app.models.call import Call
from backend.app.services.progressive_dialer import ProgressiveDialerService
from backend.app.services.predictive_dialer import PredictiveDialerService
from backend.app.schemas.call import TriggerDialRequest

router = APIRouter(prefix="/calls", tags=["calls"])
logger = logging.getLogger("smartdialer.api.calls")

@router.get("")
def list_calls(
    state: str | None = None,
    is_simulation: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = select(Call).order_by(desc(Call.queued_at))
    if state:
        query = query.where(Call.state == state.upper())
    if is_simulation is not None:
        query = query.where(Call.is_simulation == is_simulation)

    count_query = select(func.count(Call.call_id))
    if state:
        count_query = count_query.where(Call.state == state.upper())
    if is_simulation is not None:
        count_query = count_query.where(Call.is_simulation == is_simulation)
    total = db.scalar(count_query) or 0

    calls = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "call_id": c.call_id,
                "campaign_id": c.campaign_id,
                "account_id": c.account_id,
                "borrower_id": c.borrower_id,
                "agent_id": c.agent_id,
                "provider_name": c.provider_name,
                "direction": c.direction,
                "state": c.state,
                "terminal_reason": c.terminal_reason,
                "duration_sec": c.duration_sec,
                "queued_at": c.queued_at.isoformat() if c.queued_at else None,
                "completed_at": c.completed_at.isoformat() if c.completed_at else None,
                "is_simulation": c.is_simulation
            }
            for c in calls
        ]
    }

@router.post("/dial/progressive")
def trigger_progressive_dial(payload: TriggerDialRequest, db: Session = Depends(get_db)):
    try:
        res = ProgressiveDialerService.execute_progressive_cycle(
            db=db,
            campaign_id=payload.campaign_id,
            provider_name=payload.provider_name,
            max_batch_size=payload.batch_size,
            simulated_answer_prob=payload.answer_probability,
            simulated_talk_sec=payload.talk_time_sec
        )
        return res
    except Exception as ex:
        logger.exception("Progressive dial cycle failed for campaign %s", payload.campaign_id)
        raise HTTPException(status_code=500, detail="Unable to complete progressive dial cycle") from ex

@router.post("/dial/predictive")
def trigger_predictive_dial(payload: TriggerDialRequest, db: Session = Depends(get_db)):
    try:
        res = PredictiveDialerService.execute_predictive_cycle(
            db=db,
            campaign_id=payload.campaign_id,
            provider_name=payload.provider_name,
            simulated_answer_prob=payload.answer_probability,
            simulated_talk_sec=payload.talk_time_sec
        )
        return res
    except Exception as ex:
        logger.exception("Predictive dial cycle failed for campaign %s", payload.campaign_id)
        raise HTTPException(status_code=500, detail="Unable to complete predictive dial cycle") from ex
