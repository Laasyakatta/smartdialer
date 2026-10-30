"""
Telecom Event Processor with Ingestion-Before-Processing & Idempotency

Architectural Invariants:
1. Events are persisted to DB (ProviderEvent) BEFORE mutating call/agent states.
2. Duplicate event IDs are dropped idempotently with zero redundant state transitions.
3. Out-of-order events cannot overwrite terminal states (COMPLETED, FAILED, CANCELLED).
4. Terminal states release resources cleanly (agent -> AVAILABLE, borrower lock released).
"""
import json
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.models.enums import (
    CallState,
    AgentState,
    ProviderEventType,
    ProviderEventStatus
)
from backend.app.models.call import Call, CallAttempt
from backend.app.models.agent import Agent
from backend.app.models.borrower import Borrower
from backend.app.models.provider_event import ProviderEvent
from backend.app.services.call_state_machine import CallStateMachine
from backend.app.services.agent_state_machine import AgentStateMachine

logger = logging.getLogger("smartdialer.event_processor")

class EventProcessor:
    @staticmethod
    def process_incoming_event(
        db: Session,
        provider_event_id: str,
        provider_name: str,
        call_id: str,
        event_type: str,
        payload: dict | None = None,
        duration_sec: int | None = None,
        terminal_reason: str | None = None
    ) -> dict:
        """
        Idempotent entrypoint for telecom provider events.
        """
        now = datetime.now(timezone.utc)
        payload_str = json.dumps(payload) if payload else "{}"

        # 1. Step 1: Idempotency Check & Event Persistence BEFORE State Mutation
        existing_event = db.scalar(
            select(ProviderEvent)
            .where(ProviderEvent.provider_event_id == provider_event_id)
        )

        if existing_event:
            logger.info(f"Duplicate event {provider_event_id} for call {call_id} detected. Dropping idempotently.")
            return {
                "status": "DROPPED_DUPLICATE",
                "call_id": call_id,
                "event_type": event_type,
                "message": "Duplicate event ID ignored"
            }

        # Persist raw event first (Crash-durability requirement)
        event_record = ProviderEvent(
            provider_event_id=provider_event_id,
            provider_name=provider_name,
            call_id=call_id,
            event_type=event_type,
            payload=payload_str,
            received_at=now,
            status=ProviderEventStatus.RECEIVED.value
        )
        db.add(event_record)
        db.commit()
        db.refresh(event_record)

        # 2. Step 2: Retrieve Call entity
        call = db.get(Call, call_id)
        if not call:
            event_record.status = ProviderEventStatus.ERROR.value
            event_record.processing_error = f"Call {call_id} not found"
            db.commit()
            return {"status": "ERROR", "message": f"Call {call_id} not found"}

        # 3. Step 3: Out-of-order & Terminal State Guard
        if CallStateMachine.is_terminal(call.state):
            event_record.status = ProviderEventStatus.OUT_OF_ORDER_IGNORED.value
            event_record.processed_at = now
            event_record.processing_error = f"Call already terminal ({call.state})"
            db.commit()
            logger.warning(
                f"Out-of-order event {event_type} ignored because Call {call_id} is already in terminal state {call.state}"
            )
            return {
                "status": "OUT_OF_ORDER_IGNORED",
                "call_id": call_id,
                "current_call_state": call.state
            }

        # 4. Step 4: Dispatch Event Transition
        try:
            ev = ProviderEventType(event_type)
            if ev == ProviderEventType.INITIATED:
                CallStateMachine.transition(db, call, CallState.INITIATED)
                if call.agent_id:
                    agent = db.get(Agent, call.agent_id)
                    if agent and agent.status == AgentState.RESERVED.value:
                        AgentStateMachine.transition(db, agent, AgentState.DIALING, call_id=call.call_id)

            elif ev == ProviderEventType.RINGING:
                CallStateMachine.transition(db, call, CallState.RINGING)

            elif ev == ProviderEventType.ANSWERED:
                CallStateMachine.transition(db, call, CallState.ANSWERED)
                # Transition to CONNECTED
                CallStateMachine.transition(db, call, CallState.CONNECTED)
                if call.agent_id:
                    agent = db.get(Agent, call.agent_id)
                    if agent:
                        AgentStateMachine.transition(db, agent, AgentState.CONNECTED, call_id=call.call_id)

            elif ev == ProviderEventType.COMPLETED:
                reason = terminal_reason or "COMPLETED_NORMAL"
                CallStateMachine.transition(db, call, CallState.COMPLETED, reason=reason, duration_sec=duration_sec)
                # Cleanup agent & borrower
                EventProcessor._release_resources(db, call)

            elif ev == ProviderEventType.FAILED:
                reason = terminal_reason or "PROVIDER_FAILURE"
                CallStateMachine.transition(db, call, CallState.FAILED, reason=reason)
                # Cleanup agent & borrower
                EventProcessor._release_resources(db, call)

            event_record.status = ProviderEventStatus.PROCESSED.value
            event_record.processed_at = datetime.now(timezone.utc)
            db.commit()

            return {
                "status": "PROCESSED",
                "call_id": call_id,
                "new_state": call.state
            }

        except Exception as ex:
            db.rollback()
            event_record.status = ProviderEventStatus.ERROR.value
            event_record.processing_error = str(ex)
            db.commit()
            logger.error(f"Error processing event {provider_event_id}: {ex}")
            raise

    @staticmethod
    def _release_resources(db: Session, call: Call):
        """
        Releases agent and borrower when call enters a terminal state.
        Ensures agent transitions: CONNECTED -> WRAP_UP -> AVAILABLE or directly to AVAILABLE.
        """
        # 1. Release Agent
        if call.agent_id:
            agent = db.get(Agent, call.agent_id)
            if agent:
                if agent.status == AgentState.CONNECTED.value:
                    try:
                        AgentStateMachine.transition(db, agent, AgentState.WRAP_UP)
                        AgentStateMachine.transition(db, agent, AgentState.AVAILABLE)
                    except Exception:
                        AgentStateMachine.release_agent(db, agent.agent_id)
                else:
                    AgentStateMachine.release_agent(db, agent.agent_id)

        # 2. Release Borrower
        if call.borrower_id:
            borrower = db.get(Borrower, call.borrower_id)
            if borrower:
                borrower.current_active_call_id = None
                borrower.reserved_at = None
                db.commit()
