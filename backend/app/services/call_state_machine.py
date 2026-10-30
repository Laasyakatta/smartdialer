"""
Call State Machine with Out-of-Order & Terminal State Protection

Valid States:
  QUEUED, RESERVED, INITIATED, RINGING, ANSWERED, CONNECTED, COMPLETED, FAILED, CANCELLED

Rules:
1. Terminal states (COMPLETED, FAILED, CANCELLED) are immutable and cannot be overwritten.
2. Monotonic forward progress prevents regression from delayed or out-of-order events.
"""
from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session
from backend.app.models.enums import CallState
from backend.app.models.call import Call

logger = logging.getLogger("smartdialer.call_state_machine")

TERMINAL_STATES = {CallState.COMPLETED, CallState.FAILED, CallState.CANCELLED}

VALID_CALL_TRANSITIONS: dict[CallState, set[CallState]] = {
    CallState.QUEUED: {CallState.RESERVED, CallState.CANCELLED, CallState.FAILED},
    CallState.RESERVED: {CallState.INITIATED, CallState.CANCELLED, CallState.FAILED},
    CallState.INITIATED: {CallState.RINGING, CallState.ANSWERED, CallState.COMPLETED, CallState.FAILED, CallState.CANCELLED},
    CallState.RINGING: {CallState.ANSWERED, CallState.COMPLETED, CallState.FAILED, CallState.CANCELLED},
    CallState.ANSWERED: {CallState.CONNECTED, CallState.COMPLETED, CallState.FAILED},
    CallState.CONNECTED: {CallState.COMPLETED, CallState.FAILED},
    CallState.COMPLETED: set(),  # Terminal
    CallState.FAILED: set(),     # Terminal
    CallState.CANCELLED: set(),  # Terminal
}

class InvalidCallStateTransition(Exception):
    pass

class CallStateMachine:
    @staticmethod
    def is_terminal(state: CallState | str) -> bool:
        curr = CallState(state) if isinstance(state, str) else state
        return curr in TERMINAL_STATES

    @staticmethod
    def transition(
        db: Session,
        call: Call,
        target_state: CallState | str,
        reason: str | None = None,
        duration_sec: int | None = None
    ) -> tuple[Call, bool]:
        """
        Transitions call to target_state.
        Returns: (Call, bool) where bool is True if transition was applied,
                 False if transition was ignored due to terminal state or duplicate.
        """
        curr = CallState(call.state)
        tgt = CallState(target_state) if isinstance(target_state, str) else target_state

        if curr == tgt:
            logger.debug(f"Call {call.call_id} already in state {curr.value} (idempotent)")
            return call, False

        # Rule 1: Terminal calls can never be altered
        if curr in TERMINAL_STATES:
            logger.warning(
                f"Ignoring delayed event {tgt.value} for Call {call.call_id} "
                f"which is already in terminal state {curr.value}"
            )
            return call, False

        # Rule 2: Check valid progression
        if tgt not in VALID_CALL_TRANSITIONS.get(curr, set()):
            msg = f"Illegal transition for call {call.call_id}: {curr.value} -> {tgt.value}"
            logger.error(msg)
            raise InvalidCallStateTransition(msg)

        now = datetime.now(timezone.utc)
        call.state = tgt.value
        
        if reason:
            call.terminal_reason = reason
        if duration_sec is not None:
            call.duration_sec = duration_sec

        # Update lifecycle timestamps
        if tgt == CallState.RESERVED:
            call.reserved_at = now
        elif tgt == CallState.INITIATED:
            call.initiated_at = now
        elif tgt == CallState.RINGING:
            call.ringing_at = now
        elif tgt == CallState.ANSWERED:
            call.answered_at = now
        elif tgt == CallState.CONNECTED:
            call.connected_at = now
        elif tgt in TERMINAL_STATES:
            call.completed_at = now

        db.commit()
        db.refresh(call)
        logger.info(f"Call {call.call_id} transitioned: {curr.value} -> {tgt.value}")
        return call, True
