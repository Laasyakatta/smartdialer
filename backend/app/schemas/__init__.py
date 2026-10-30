"""
Pydantic Schemas for SmartDialer API
"""
from backend.app.schemas.agent import (
    AgentResponse, AgentListResponse, AgentStatusUpdateRequest,
    AgentSessionResponse, DisconnectBatchRequest
)
from backend.app.schemas.borrower import BorrowerResponse, BorrowerListResponse
from backend.app.schemas.campaign import (
    CampaignResponse, CampaignListResponse,
    DialingModeUpdateRequest, CampaignPerformanceResponse
)
from backend.app.schemas.call import (
    CallResponse, CallListResponse, TriggerDialRequest
)
from backend.app.schemas.simulation import (
    SimulationRunRequest, SimulationRunResponse, SimulationHistoryItem,
    ScenarioInfo
)
from backend.app.schemas.analytics import (
    OverviewKPIsResponse, VendorPerformanceResponse,
    CallDispositionResponse, CampaignAnalyticsResponse
)
from backend.app.schemas.safety import SafetyStatusResponse
from backend.app.schemas.provider import ProviderStatusResponse, OutageToggleRequest

__all__ = [
    "AgentResponse", "AgentListResponse", "AgentStatusUpdateRequest",
    "AgentSessionResponse", "DisconnectBatchRequest",
    "BorrowerResponse", "BorrowerListResponse",
    "CampaignResponse", "CampaignListResponse", "DialingModeUpdateRequest",
    "CampaignPerformanceResponse",
    "CallResponse", "CallListResponse", "TriggerDialRequest",
    "SimulationRunRequest", "SimulationRunResponse", "SimulationHistoryItem",
    "ScenarioInfo",
    "OverviewKPIsResponse", "VendorPerformanceResponse",
    "CallDispositionResponse", "CampaignAnalyticsResponse",
    "SafetyStatusResponse",
    "ProviderStatusResponse", "OutageToggleRequest",
]
