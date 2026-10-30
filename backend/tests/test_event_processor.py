"""
Unit Tests for Event Processor & Idempotency
"""
import concurrent.futures
import threading

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
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


def test_concurrent_duplicate_provider_event_is_processed_once(tmp_path):
    database_path = (tmp_path / "duplicate-events.db").as_posix()
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False, "timeout": 15}
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    initial_db = session_factory()
    initial_db.add(Call(
        call_id="CALL_CONCURRENT_EVT",
        account_id="ACC_EVT",
        borrower_id="BRW_EVT",
        state=CallState.INITIATED.value
    ))
    initial_db.commit()
    initial_db.close()
    start = threading.Barrier(2)

    def process_event():
        db = session_factory()
        try:
            start.wait(timeout=5)
            return EventProcessor.process_incoming_event(
                db=db,
                provider_event_id="EVT_CONCURRENT_DUPLICATE",
                provider_name="mock_a",
                call_id="CALL_CONCURRENT_EVT",
                event_type=ProviderEventType.RINGING.value
            )
        finally:
            db.close()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: process_event(), range(2)))

        assert sorted(result["status"] for result in results) == [
            "DROPPED_DUPLICATE",
            "PROCESSED"
        ]
        verify_db = session_factory()
        assert verify_db.scalar(
            select(ProviderEvent).where(
                ProviderEvent.provider_event_id == "EVT_CONCURRENT_DUPLICATE"
            )
        ) is not None
        assert verify_db.get(Call, "CALL_CONCURRENT_EVT").state == CallState.RINGING.value
        verify_db.close()
    finally:
        engine.dispose()
