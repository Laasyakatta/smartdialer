"""
Analytics & Chart Data API Router
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/campaigns")
def get_campaigns_analytics(limit: int = 10, db: Session = Depends(get_db)):
    return AnalyticsService.get_campaign_performance(db, limit=limit)

@router.get("/vendors")
def get_vendors_analytics(db: Session = Depends(get_db)):
    return AnalyticsService.get_vendor_performance(db)

@router.get("/dispositions")
def get_dispositions_breakdown(db: Session = Depends(get_db)):
    return AnalyticsService.get_call_disposition_breakdown(db)
