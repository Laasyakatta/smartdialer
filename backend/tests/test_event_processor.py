"""
Unit Tests for Event Processor & Idempotency
"""
import pytest
from datetime import datetime, timezone
from backend.app.models.call import Call
from backend.app.models.agent import Agent
from backend.app.models.borrower import Borrower
from backend.app.models.provider_event import ProviderEvent
from backend.app.models.enums import CallState, AgentState, ProviderEventType
from backend.app.services.event_processor import EventProcessor

def test_duplicate_event_idempotency(test_db):
    """
    Submitting the same provider_event_id twice must drop the second event
    and cause NO state corruption.
    """
    agent = Agent(agent_id="AGT_EVT_1", agent_name="Evt Agent", status=AgentState.RESERVED.value)
    call = Call(
        call_id="CALL_EVT_1",
        account_id="ACC_1",
        borrower_id="BRW_1",
        agent_id="AGT_EVT_1",
        state=CallState.INITIATED.value
    )
    test_db.add(agent)
    test_db.add(call)
    test_db.commit()

    event_id = "EVT_UNIQUE_001"

    # First event: RINGING
    res1 = EventProcessor.process_incoming_event(
        db=test_db,
        provider_event_id=event_id,
        provider_name="mock_a",
        call_id="CALL_EVT_1",
        event_type=ProviderEventType.RINGING.value
    )
    assert res1["status"] == "PROCESSED"
    assert call.state == CallState.RINGING.value

    # Second arrival of EXACT SAME event ID:
    res2 = EventProcessor.process_incoming_event(
        db=test_db,
        provider_event_id=event_id,
        provider_name="mock_a",
        call_id="CALL_EVT_1",
        event_type=ProviderEventType.RINGING.value
    )
    assert res2["status"] == "DROPPED_DUPLICATE"

    # Verify DB only has 1 event record for this event_id
    records = test_db.query(ProviderEvent).filter_by(provider_event_id=event_id).all()
    assert len(records) == 1

def test_out_of_order_event_ignored_for_completed_call(test_db):
    """
    Provider B sends COMPLETED before late ANSWERED/RINGING event.
    The late event must be dropped.
    """
    call = Call(
        call_id="CALL_EVT_2",
        account_id="ACC_2",
        borrower_id="BRW_2",
        state=CallState.COMPLETED.value,
        terminal_reason="NORMAL_HANGUP",
        duration_sec=110
    )
    test_db.add(call)
    test_db.commit()

    # Late ANSWERED arrives
    res = EventProcessor.process_incoming_event(
        db=test_db,
        provider_event_id="EVT_LATE_002",
        provider_name="mock_b",
        call_id="CALL_EVT_2",
        event_type=ProviderEventType.ANSWERED.value
    )
    assert res["status"] == "OUT_OF_ORDER_IGNORED"
    assert call.state == CallState.COMPLETED.value
