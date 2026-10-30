"""
Unit Tests for Call State Machine & Monotonicity
"""
import pytest
from datetime import datetime, timezone
from backend.app.models.call import Call
from backend.app.models.campaign import Campaign
from backend.app.models.account import Account
from backend.app.models.enums import CallState
from backend.app.services.call_state_machine import CallStateMachine, InvalidCallStateTransition

def test_valid_call_lifecycle(test_db):
    call = Call(
        call_id="CALL_TEST_1",
        account_id="ACC_1",
        borrower_id="BRW_1",
        state=CallState.QUEUED.value
    )
    test_db.add(call)
    test_db.commit()

    # QUEUED -> RESERVED
    CallStateMachine.transition(test_db, call, CallState.RESERVED)
    assert call.state == CallState.RESERVED.value

    # RESERVED -> INITIATED
    CallStateMachine.transition(test_db, call, CallState.INITIATED)
    assert call.state == CallState.INITIATED.value

    # INITIATED -> RINGING
    CallStateMachine.transition(test_db, call, CallState.RINGING)
    assert call.state == CallState.RINGING.value

    # RINGING -> ANSWERED
    CallStateMachine.transition(test_db, call, CallState.ANSWERED)
    assert call.state == CallState.ANSWERED.value

    # ANSWERED -> CONNECTED
    CallStateMachine.transition(test_db, call, CallState.CONNECTED)
    assert call.state == CallState.CONNECTED.value

    # CONNECTED -> COMPLETED
    CallStateMachine.transition(test_db, call, CallState.COMPLETED, duration_sec=140, reason="NORMAL_HANGUP")
    assert call.state == CallState.COMPLETED.value
    assert call.duration_sec == 140
    assert call.terminal_reason == "NORMAL_HANGUP"

def test_terminal_state_protection_against_delayed_events(test_db):
    call = Call(
        call_id="CALL_TEST_2",
        account_id="ACC_2",
        borrower_id="BRW_2",
        state=CallState.COMPLETED.value,
        terminal_reason="NORMAL_HANGUP",
        duration_sec=95
    )
    test_db.add(call)
    test_db.commit()

    # Late-arriving RINGING or ANSWERED event arriving after COMPLETED
    call_res, applied = CallStateMachine.transition(test_db, call, CallState.ANSWERED)
    # Must NOT apply transition; terminal state remains COMPLETED!
    assert applied is False
    assert call_res.state == CallState.COMPLETED.value

    call_res2, applied2 = CallStateMachine.transition(test_db, call, CallState.RINGING)
    assert applied2 is False
    assert call_res2.state == CallState.COMPLETED.value
