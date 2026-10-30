"""
Concurrency Test: Proves Two Workers Cannot Double-Reserve the Same Agent
"""
import concurrent.futures
import tempfile
import os
import time
from datetime import datetime, timezone
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from backend.app.core.database import Base
from backend.app.models.agent import Agent
from backend.app.models.enums import AgentState
from backend.app.services.agent_state_machine import AgentStateMachine

def test_concurrent_agent_reservation_race():
    """
    Spawns 10 threads trying to atomically reserve the exact same AVAILABLE agent
    at the exact same time. Exactly 1 thread must succeed; 9 must fail.
    """
    # Create temporary file db with WAL mode to simulate production SQLite concurrency
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_race.db")
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False, "timeout": 15}
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    # Insert single target agent
    init_db = Session()
    target_agent_id = "AGT_RACE_001"
    agent = Agent(
        agent_id=target_agent_id,
        agent_name="Concurrent Contender",
        status=AgentState.AVAILABLE.value,
        last_status_change=datetime.now(timezone.utc)
    )
    init_db.add(agent)
    init_db.commit()
    init_db.close()

    results = []

    def worker_attempt_reservation(worker_id: int):
        db = Session()
        try:
            call_id = f"CALL_WORKER_{worker_id}"
            # Retry on transient busy lock
            for attempt in range(5):
                try:
                    success = AgentStateMachine.reserve_agent_atomic(db, target_agent_id, call_id=call_id)
                    return (worker_id, success)
                except Exception as ex:
                    time.sleep(0.02 * (attempt + 1))
            return (worker_id, False)
        finally:
            db.close()

    # Launch 10 concurrent threads simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker_attempt_reservation, i) for i in range(10)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    success_count = sum(1 for wid, ok in results if ok)
    fail_count = sum(1 for wid, ok in results if not ok)

    # Assert strict invariant: EXACTLY ONE worker got the agent!
    assert success_count == 1, f"Expected 1 winner, but got {success_count}"
    assert fail_count == 9, f"Expected 9 losers, but got {fail_count}"

    # Verify final state in database
    verify_db = Session()
    final_agent = verify_db.get(Agent, target_agent_id)
    assert final_agent.status == AgentState.RESERVED.value
    assert final_agent.current_call_id is not None
    verify_db.close()
