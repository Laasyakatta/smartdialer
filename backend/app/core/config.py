"""
Application Configuration
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartDialer"
    API_V1_STR: str = "/api"
    
    # Database
    DATABASE_PATH: Path = BASE_DIR / "data" / "smartdialer.db"
    DATABASE_URL: str = f"sqlite:///{DATABASE_PATH.as_posix()}"
    
    # Telephony Provider Defaults
    PROVIDER_A_TIMEOUT_SEC: float = 3.0
    PROVIDER_A_FAILURE_RATE: float = 0.02
    PROVIDER_B_TIMEOUT_SEC: float = 8.0
    PROVIDER_B_FAILURE_RATE: float = 0.15
    PROVIDER_B_DUP_RATE: float = 0.10
    PROVIDER_B_OUT_OF_ORDER_RATE: float = 0.10
    
    # Safety Controller Constraints
    STALE_RESERVATION_TIMEOUT_SEC: int = 45
    MAX_SYSTEM_CONCURRENT_CALLS: int = 500
    DEFAULT_SAFETY_MARGIN: float = 0.15
    
    # Circuit Breaker
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIME_SEC: int = 15
    
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

settings = Settings()
