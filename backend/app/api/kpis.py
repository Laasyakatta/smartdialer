"""
Global KPIs API Router
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/kpis", tags=["kpis"])

@router.get("")
def get_kpis(db: Session = Depends(get_db)):
    return AnalyticsService.get_overview_kpis(db)
