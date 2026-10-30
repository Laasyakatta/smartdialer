"""
Campaign Management API Router
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.models.campaign import Campaign
from backend.app.models.enums import DialingMode

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

class DialingModeUpdate(BaseModel):
    mode: str

@router.get("")
def list_campaigns(
    active_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = select(Campaign)
    if active_only:
        query = query.where(Campaign.is_active.is_(True))

    total = db.scalar(
        select(func.count(Campaign.campaign_id))
        .where(Campaign.is_active.is_(True) if active_only else True)
    ) or 0

    campaigns = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "campaign_id": c.campaign_id,
                "campaign_name": c.campaign_name,
                "channel": c.channel,
                "strategy_version": c.strategy_version,
                "dialing_mode": c.dialing_mode,
                "is_active": c.is_active,
                "max_concurrent_calls": c.max_concurrent_calls,
                "target_answer_rate": c.target_answer_rate,
                "safety_margin": c.safety_margin
            }
            for c in campaigns
        ]
    }

@router.post("/{campaign_id}/start")
def start_campaign(campaign_id: str, db: Session = Depends(get_db)):
    c = db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    c.is_active = True
    db.commit()
    return {"campaign_id": c.campaign_id, "is_active": True, "message": "Campaign started"}

@router.post("/{campaign_id}/pause")
def pause_campaign(campaign_id: str, db: Session = Depends(get_db)):
    c = db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    c.is_active = False
    db.commit()
    return {"campaign_id": c.campaign_id, "is_active": False, "message": "Campaign paused"}

@router.post("/{campaign_id}/mode")
def update_campaign_mode(campaign_id: str, payload: DialingModeUpdate, db: Session = Depends(get_db)):
    c = db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    new_mode = payload.mode.upper()
    if new_mode not in ("PROGRESSIVE", "PREDICTIVE"):
        raise HTTPException(status_code=400, detail="Mode must be PROGRESSIVE or PREDICTIVE")
    
    c.dialing_mode = new_mode
    db.commit()
    return {"campaign_id": c.campaign_id, "dialing_mode": c.dialing_mode, "message": f"Mode changed to {new_mode}"}
