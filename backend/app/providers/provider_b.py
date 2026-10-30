"""
Mock Telecom Provider B: Degraded Network, Duplicate Events, Out-of-Order Delivery
"""
import random
import uuid
import time
from datetime import datetime, timezone
from typing import Any
from backend.app.providers.base import BaseTelecomProvider
from backend.app.models.enums import ProviderEventType

class ProviderB(BaseTelecomProvider):
    def __init__(
        self,
        failure_rate: float = 0.15,
        dup_rate: float = 0.15,
        out_of_order_rate: float = 0.20
    ):
        super().__init__(name="mock_b")
        self.failure_rate = failure_rate
        self.dup_rate = dup_rate
        self.out_of_order_rate = out_of_order_rate

    def initiate_call(self, call_id: str, phone: str) -> dict[str, Any]:
        if self.is_outage:
            return {
                "success": False,
                "error": "PROVIDER_OUTAGE",
                "latency_ms": 150,
                "provider_call_id": None
            }

        # Elevated latency
        latency_ms = random.randint(80, 250)
        time.sleep(latency_ms / 1000.0)

        # Timeout simulation
        if random.random() < 0.05:
            return {
                "success": False,
                "error": "GATEWAY_TIMEOUT",
                "latency_ms": latency_ms + 1000,
                "provider_call_id": None
            }

        # Failure injection
        if random.random() < self.failure_rate:
            return {
                "success": False,
                "error": "TRUNK_CIRCUIT_BUSY",
                "latency_ms": latency_ms,
                "provider_call_id": None
            }

        provider_call_id = f"TEL-B-{uuid.uuid4().hex[:12].upper()}"
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
        now = datetime.now(timezone.utc)
        events = []

        # Event 1: INITIATED
        init_evt = {
            "provider_event_id": f"EVT-B-{uuid.uuid4().hex[:16]}",
            "provider_name": self.name,
            "call_id": call_id,
            "event_type": ProviderEventType.INITIATED.value,
            "duration_sec": 0,
            "terminal_reason": None,
            "timestamp": now.isoformat()
        }
        events.append(init_evt)

        if self.is_outage or random.random() < self.failure_rate:
            fail_evt = {
                "provider_event_id": f"EVT-B-{uuid.uuid4().hex[:16]}",
                "provider_name": self.name,
                "call_id": call_id,
                "event_type": ProviderEventType.FAILED.value,
                "duration_sec": 0,
                "terminal_reason": "PROVIDER_CIRCUIT_FAILURE",
                "timestamp": now.isoformat()
            }
            events.append(fail_evt)
            return events

        # Event 2: RINGING
        ring_evt = {
            "provider_event_id": f"EVT-B-{uuid.uuid4().hex[:16]}",
            "provider_name": self.name,
            "call_id": call_id,
            "event_type": ProviderEventType.RINGING.value,
            "duration_sec": 0,
            "terminal_reason": None,
            "timestamp": now.isoformat()
        }
        events.append(ring_evt)

        is_answered = random.random() < answer_probability
        if is_answered:
            ans_evt = {
                "provider_event_id": f"EVT-B-{uuid.uuid4().hex[:16]}",
                "provider_name": self.name,
                "call_id": call_id,
                "event_type": ProviderEventType.ANSWERED.value,
                "duration_sec": 0,
                "terminal_reason": None,
                "timestamp": now.isoformat()
            }
            comp_evt = {
                "provider_event_id": f"EVT-B-{uuid.uuid4().hex[:16]}",
                "provider_name": self.name,
                "call_id": call_id,
                "event_type": ProviderEventType.COMPLETED.value,
                "duration_sec": talk_time_sec,
                "terminal_reason": "NORMAL_HANGUP",
                "timestamp": now.isoformat()
            }
            events.extend([ans_evt, comp_evt])
        else:
            outcome = random.choice(["NO_ANSWER", "BUSY", "VOICEMAIL"])
            comp_evt = {
                "provider_event_id": f"EVT-B-{uuid.uuid4().hex[:16]}",
                "provider_name": self.name,
                "call_id": call_id,
                "event_type": ProviderEventType.COMPLETED.value,
                "duration_sec": random.randint(10, 25),
                "terminal_reason": outcome,
                "timestamp": now.isoformat()
            }
            events.append(comp_evt)

        # Inject duplicates
        if random.random() < self.dup_rate and len(events) >= 2:
            target_evt = random.choice(events)
            # Create a duplicate event with identical provider_event_id!
            dup_evt = dict(target_evt)
            events.append(dup_evt)

        # Inject out-of-order anomalies
        if random.random() < self.out_of_order_rate and len(events) >= 3:
            # E.g. swap last two events or move COMPLETED ahead of ANSWERED/RINGING
            idx1 = random.randint(1, len(events) - 1)
            idx2 = random.randint(1, len(events) - 1)
            events[idx1], events[idx2] = events[idx2], events[idx1]

        return events
