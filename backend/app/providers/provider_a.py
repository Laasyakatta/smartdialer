"""
Mock Telecom Provider A: High Reliability, Low Latency, Standard Ordering
"""
import random
import uuid
import time
from datetime import datetime, timezone
from typing import Any
from backend.app.providers.base import BaseTelecomProvider
from backend.app.models.enums import ProviderEventType

class ProviderA(BaseTelecomProvider):
    def __init__(self, failure_rate: float = 0.02):
        super().__init__(name="mock_a")
        self.failure_rate = failure_rate

    def initiate_call(self, call_id: str, phone: str) -> dict[str, Any]:
        if self.is_outage:
            return {
                "success": False,
                "error": "PROVIDER_OUTAGE",
                "latency_ms": 10,
                "provider_call_id": None
            }

        # Simulated slight network latency
        latency_ms = random.randint(15, 60)
        time.sleep(latency_ms / 1000.0)

        # Failure injection
        if random.random() < self.failure_rate:
            return {
                "success": False,
                "error": "NETWORK_CONGESTION",
                "latency_ms": latency_ms,
                "provider_call_id": None
            }

        provider_call_id = f"TEL-A-{uuid.uuid4().hex[:12].upper()}"
        return {
            "success": True,
            "provider_call_id": provider_call_id,
            "latency_ms": latency_ms,
            "error": None
        }

    def generate_call_lifecycle_events(
        self,
        call_id: str,
        answer_probability: float = 0.20,
        talk_time_sec: int = 60
    ) -> list[dict[str, Any]]:
        """
        Provider A sends strictly ordered events:
        INITIATED -> RINGING -> (ANSWERED -> COMPLETED) or FAILED
        """
        now = datetime.now(timezone.utc)
        events = []

        # Event 1: INITIATED
        events.append({
            "provider_event_id": f"EVT-A-{uuid.uuid4().hex[:16]}",
            "provider_name": self.name,
            "call_id": call_id,
            "event_type": ProviderEventType.INITIATED.value,
            "duration_sec": 0,
            "terminal_reason": None,
            "timestamp": now.isoformat()
        })

        if self.is_outage:
            events.append({
                "provider_event_id": f"EVT-A-{uuid.uuid4().hex[:16]}",
                "provider_name": self.name,
                "call_id": call_id,
                "event_type": ProviderEventType.FAILED.value,
                "duration_sec": 0,
                "terminal_reason": "PROVIDER_OUTAGE",
                "timestamp": now.isoformat()
            })
            return events

        # Event 2: RINGING
        events.append({
            "provider_event_id": f"EVT-A-{uuid.uuid4().hex[:16]}",
            "provider_name": self.name,
            "call_id": call_id,
            "event_type": ProviderEventType.RINGING.value,
            "duration_sec": 0,
            "terminal_reason": None,
            "timestamp": now.isoformat()
        })

        is_answered = random.random() < answer_probability

        if is_answered:
            # Event 3: ANSWERED
            events.append({
                "provider_event_id": f"EVT-A-{uuid.uuid4().hex[:16]}",
                "provider_name": self.name,
                "call_id": call_id,
                "event_type": ProviderEventType.ANSWERED.value,
                "duration_sec": 0,
                "terminal_reason": None,
                "timestamp": now.isoformat()
            })
            # Event 4: COMPLETED
            events.append({
                "provider_event_id": f"EVT-A-{uuid.uuid4().hex[:16]}",
                "provider_name": self.name,
                "call_id": call_id,
                "event_type": ProviderEventType.COMPLETED.value,
                "duration_sec": talk_time_sec,
                "terminal_reason": "NORMAL_HANGUP",
                "timestamp": now.isoformat()
            })
        else:
            # Non-answered outcome
            outcome = random.choice(["NO_ANSWER", "BUSY", "VOICEMAIL"])
            events.append({
                "provider_event_id": f"EVT-A-{uuid.uuid4().hex[:16]}",
                "provider_name": self.name,
                "call_id": call_id,
                "event_type": ProviderEventType.COMPLETED.value,
                "duration_sec": random.randint(15, 30),
                "terminal_reason": outcome,
                "timestamp": now.isoformat()
            })

        return events
