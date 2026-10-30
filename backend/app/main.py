"""
SmartDialer FastAPI Main Application
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.database import SessionLocal, engine, Base
import backend.app.models
from backend.app.services.recovery_service import RecoveryService

# Import API Routers
from backend.app.api.kpis import router as kpis_router
from backend.app.api.agents import router as agents_router
from backend.app.api.borrowers import router as borrowers_router
from backend.app.api.campaigns import router as campaigns_router
from backend.app.api.calls import router as calls_router
from backend.app.api.providers import router as providers_router
from backend.app.api.safety import router as safety_router
from backend.app.api.simulation import router as simulation_router
from backend.app.api.analytics import router as analytics_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("smartdialer.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing SmartDialer Application...")
    Base.metadata.create_all(bind=engine)
    
    # Startup reconciliation: Clean up any stale reservations from prior abnormal termination
    db = SessionLocal()
    try:
        reconciled = RecoveryService.reconcile_stale_reservations(db, timeout_seconds=10)
        logger.info(f"Startup crash recovery complete: {reconciled}")
    except Exception as ex:
        logger.error(f"Startup recovery encountered issue: {ex}")
    finally:
        db.close()
        
    yield
    logger.info("Shutting down SmartDialer Application...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Autonomous SmartDialer Engine with Progressive & Predictive Pacing and Independent Safety Controller",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
api_prefix = settings.API_V1_STR
app.include_router(kpis_router, prefix=api_prefix)
app.include_router(agents_router, prefix=api_prefix)
app.include_router(borrowers_router, prefix=api_prefix)
app.include_router(campaigns_router, prefix=api_prefix)
app.include_router(calls_router, prefix=api_prefix)
app.include_router(providers_router, prefix=api_prefix)
app.include_router(safety_router, prefix=api_prefix)
app.include_router(simulation_router, prefix=api_prefix)
app.include_router(analytics_router, prefix=api_prefix)

@app.get("/health")
def healthcheck():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "database": "sqlite_wal_connected"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
