"""
Unit Tests for Agent State Machine & Transitions
"""
import pytest
from datetime import datetime, timezone
from backend.app.models.agent import Agent
from backend.app.models.enums import AgentState
from backend.app.services.agent_state_machine import AgentStateMachine, InvalidAgentStateTransition

def test_valid_agent_transitions(test_db):
    agent = Agent(
        agent_id="AGT_TEST_1",
        agent_name="Alice Smith",
        status=AgentState.AVAILABLE.value,
        last_status_change=datetime.now(timezone.utc)
    )
    test_db.add(agent)
    test_db.commit()

    # AVAILABLE -> RESERVED
    AgentStateMachine.transition(test_db, agent, AgentState.RESERVED, call_id="CALL_1")
    assert agent.status == AgentState.RESERVED.value
    assert agent.current_call_id == "CALL_1"
    assert agent.reserved_at is not None

    # RESERVED -> DIALING
    AgentStateMachine.transition(test_db, agent, AgentState.DIALING, call_id="CALL_1")
    assert agent.status == AgentState.DIALING.value

    # DIALING -> CONNECTED
    AgentStateMachine.transition(test_db, agent, AgentState.CONNECTED, call_id="CALL_1")
    assert agent.status == AgentState.CONNECTED.value

    # CONNECTED -> WRAP_UP
    AgentStateMachine.transition(test_db, agent, AgentState.WRAP_UP)
    assert agent.status == AgentState.WRAP_UP.value

    # WRAP_UP -> AVAILABLE
    AgentStateMachine.transition(test_db, agent, AgentState.AVAILABLE)
    assert agent.status == AgentState.AVAILABLE.value
    assert agent.reserved_at is None
    assert agent.current_call_id is None

def test_invalid_agent_transitions_rejected(test_db):
    agent = Agent(
        agent_id="AGT_TEST_2",
        agent_name="Bob Jones",
        status=AgentState.AVAILABLE.value,
        last_status_change=datetime.now(timezone.utc)
    )
    test_db.add(agent)
    test_db.commit()

    # AVAILABLE cannot jump directly to CONNECTED without reservation/dialing
    with pytest.raises(InvalidAgentStateTransition):
        AgentStateMachine.transition(test_db, agent, AgentState.CONNECTED)

    # AVAILABLE cannot jump directly to WRAP_UP
    with pytest.raises(InvalidAgentStateTransition):
        AgentStateMachine.transition(test_db, agent, AgentState.WRAP_UP)

def test_atomic_agent_reservation(test_db):
    agent = Agent(
        agent_id="AGT_TEST_3",
        agent_name="Charlie Brown",
        status=AgentState.AVAILABLE.value,
        last_status_change=datetime.now(timezone.utc)
    )
    test_db.add(agent)
    test_db.commit()

    # First reservation succeeds
    success1 = AgentStateMachine.reserve_agent_atomic(test_db, "AGT_TEST_3", call_id="CALL_X")
    assert success1 is True

    # Second concurrent reservation attempt must fail because status is now RESERVED
    success2 = AgentStateMachine.reserve_agent_atomic(test_db, "AGT_TEST_3", call_id="CALL_Y")
    assert success2 is False
