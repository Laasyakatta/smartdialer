"""
Agent State Machine with Atomic Concurrency Guarantees

Valid States:
  OFFLINE, AVAILABLE, RESERVED, DIALING, CONNECTED, WRAP_UP, PAUSED

Concurrency Guarantee:
  Conditional atomic updates ensure two workers can NEVER reserve the same agent simultaneously.
"""
from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session
from sqlalchemy import update, select
from backend.app.models.enums import AgentState
from backend.app.models.agent import Agent

logger = logging.getLogger("smartdialer.agent_state_machine")

# Formal valid transition map
VALID_TRANSITIONS: dict[AgentState, set[AgentState]] = {
    AgentState.OFFLINE: {AgentState.AVAILABLE, AgentState.PAUSED},
    AgentState.AVAILABLE: {AgentState.RESERVED, AgentState.PAUSED, AgentState.OFFLINE},
    AgentState.RESERVED: {AgentState.DIALING, AgentState.AVAILABLE, AgentState.OFFLINE},
    AgentState.DIALING: {AgentState.CONNECTED, AgentState.WRAP_UP, AgentState.AVAILABLE, AgentState.OFFLINE},
    AgentState.CONNECTED: {AgentState.WRAP_UP, AgentState.AVAILABLE, AgentState.OFFLINE},
    AgentState.WRAP_UP: {AgentState.AVAILABLE, AgentState.PAUSED, AgentState.OFFLINE},
    AgentState.PAUSED: {AgentState.AVAILABLE, AgentState.OFFLINE},
}

class InvalidAgentStateTransition(Exception):
    pass

class AgentStateMachine:
    @staticmethod
    def is_transition_valid(current_state: AgentState | str, target_state: AgentState | str) -> bool:
        curr = AgentState(current_state) if isinstance(current_state, str) else current_state
        tgt = AgentState(target_state) if isinstance(target_state, str) else target_state
        return tgt in VALID_TRANSITIONS.get(curr, set())

    @staticmethod
    def transition(
        db: Session,
        agent: Agent,
        target_state: AgentState | str,
        call_id: str | None = None
    ) -> Agent:
        """
        Transitions an agent to target_state if valid.
        Raises InvalidAgentStateTransition on illegal transition.
        """
        curr = AgentState(agent.status)
        tgt = AgentState(target_state) if isinstance(target_state, str) else target_state

        if curr == tgt:
            return agent

        if not AgentStateMachine.is_transition_valid(curr, tgt):
            msg = f"Invalid agent transition from {curr.value} to {tgt.value} for agent {agent.agent_id}"
            logger.warning(msg)
            raise InvalidAgentStateTransition(msg)

        now = datetime.now(timezone.utc)
        agent.status = tgt.value
        agent.last_status_change = now

        if tgt == AgentState.RESERVED:
            agent.reserved_at = now
            if call_id:
                agent.current_call_id = call_id
        elif tgt in (AgentState.AVAILABLE, AgentState.OFFLINE, AgentState.PAUSED):
            agent.reserved_at = None
            agent.current_call_id = None
        elif tgt == AgentState.CONNECTED and call_id:
            agent.current_call_id = call_id

        db.commit()
        db.refresh(agent)
        logger.info(f"Agent {agent.agent_id} transitioned: {curr.value} -> {tgt.value}")
        return agent

    @staticmethod
    def reserve_agent_atomic(
        db: Session,
        agent_id: str,
        call_id: str | None = None
    ) -> bool:
        """
        Atomically reserve an available agent using a conditional update.
        Prevents race condition: Two concurrent workers cannot reserve the same agent.
        Returns True if reservation was successful, False if already claimed or unavailable.
        """
        now = datetime.now(timezone.utc)
        
        stmt = (
            update(Agent)
            .where(Agent.agent_id == agent_id, Agent.status == AgentState.AVAILABLE.value)
            .values(
                status=AgentState.RESERVED.value,
                reserved_at=now,
                last_status_change=now,
                current_call_id=call_id
            )
        )
        
        result = db.execute(stmt)
        db.commit()
        
        # In SQLAlchemy / SQLite, rowcount indicates how many rows matched the WHERE clause
        success = (result.rowcount > 0)
        if success:
            logger.info(f"Successfully atomically reserved agent {agent_id} for call {call_id}")
        else:
            logger.debug(f"Failed to reserve agent {agent_id}: already claimed or not AVAILABLE")
            
        return success

    @staticmethod
    def find_and_reserve_available_agents(
        db: Session,
        limit: int = 1,
        campaign_id: str | None = None
    ) -> list[Agent]:
        """
        Finds candidate available agents and atomically reserves up to `limit` agents.
        In SQLite, candidate IDs are queried, then individually reserved via conditional update.
        In PostgreSQL production, this would use:
          SELECT agent_id FROM agents WHERE status = 'AVAILABLE' FOR UPDATE SKIP LOCKED LIMIT :limit
        """
        candidates = db.execute(
            select(Agent.agent_id)
            .where(Agent.status == AgentState.AVAILABLE.value)
            .limit(limit * 2)  # sample a slightly larger pool to absorb race conditions
        ).scalars().all()

        reserved_agents = []
        for aid in candidates:
            if len(reserved_agents) >= limit:
                break
            if AgentStateMachine.reserve_agent_atomic(db, aid):
                agent = db.get(Agent, aid)
                if agent:
                    reserved_agents.append(agent)

        return reserved_agents

    @staticmethod
    def release_agent(db: Session, agent_id: str) -> bool:
        """
        Safely releases an agent back to AVAILABLE if not OFFLINE or PAUSED.
        """
        agent = db.get(Agent, agent_id)
        if not agent:
            return False
            
        now = datetime.now(timezone.utc)
        if agent.status in (AgentState.RESERVED.value, AgentState.DIALING.value, AgentState.CONNECTED.value, AgentState.WRAP_UP.value):
            agent.status = AgentState.AVAILABLE.value
            agent.reserved_at = None
            agent.current_call_id = None
            agent.last_status_change = now
            db.commit()
            logger.info(f"Agent {agent_id} safely released to AVAILABLE")
            return True
        return False
