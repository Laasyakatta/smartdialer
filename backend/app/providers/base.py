"""
Base Telecom Provider Interface
"""
from abc import ABC, abstractmethod
from typing import Any
import uuid

class BaseTelecomProvider(ABC):
    def __init__(self, name: str):
        self.name = name
        self.is_outage = False

    @abstractmethod
    def initiate_call(self, call_id: str, phone: str) -> dict[str, Any]:
        """
        Initiate an outbound call to the telecom carrier.
        Returns a dictionary with status, provider_call_id, and latency_ms.
        """
        pass

    @abstractmethod
    def generate_call_lifecycle_events(
        self,
        call_id: str,
        answer_probability: float = 0.20,
        talk_time_sec: int = 60
    ) -> list[dict[str, Any]]:
        """
        Generates simulated telephony webhook events for a call.
        Each event contains:
          - provider_event_id: str
          - provider_name: str
          - call_id: str
          - event_type: str ('INITIATED', 'RINGING', 'ANSWERED', 'COMPLETED', 'FAILED')
          - duration_sec: int
          - timestamp: iso datetime string
        """
        pass

    def set_outage(self, in_outage: bool):
        self.is_outage = in_outage

    def is_healthy(self) -> bool:
        return not self.is_outage
