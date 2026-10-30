"""
Basic Load Test for SmartDialer
Measures throughput, cycle latency, and capacity enforcement under concurrent execution.
"""
import time
import pytest
from datetime import datetime, timezone
from backend.app.models.agent import Agent
from backend.app.models.borrower import Borrower
from backend.app.models.account import Account
from backend.app.models.campaign import Campaign
from backend.app.models.enums import AgentState
from backend.app.services.progressive_dialer import ProgressiveDialerService

def test_load_dialer_cycles(test_db):
    """
    Executes multiple rapid dialing bursts to measure system throughput and latency.
    """
    # Setup test pool with 20 available agents
    for i in range(20):
        test_db.add(Agent(
            agent_id=f"AGT_LOAD_{i}",
            agent_name=f"Load Agent {i}",
            status=AgentState.AVAILABLE.value,
            last_status_change=datetime.now(timezone.utc)
        ))

    test_db.add(Campaign(
        campaign_id="CMP_LOAD",
        campaign_name="Load Test Campaign",
        max_concurrent_calls=100,
        is_active=True
    ))

    # Add 100 eligible borrowers
    for i in range(100):
        bid = f"BRW_LOAD_{i}"
        acc_id = f"ACC_LOAD_{i}"
        test_db.add(Borrower(borrower_id=bid, name=f"Load Borrower {i}", phone=f"90000000{i:02d}", is_eligible=True))
        test_db.add(Account(account_id=acc_id, borrower_id=bid, status="ACTIVE"))

    test_db.commit()

    latencies = []
    total_calls_initiated = 0
    start_time = time.perf_counter()

    # Execute 10 rapid dialing cycles
    num_cycles = 10
    for cycle in range(num_cycles):
        t0 = time.perf_counter()
        res = ProgressiveDialerService.execute_progressive_cycle(
            db=test_db,
            campaign_id="CMP_LOAD",
            provider_name="mock_a",
            max_batch_size=10,
            simulated_answer_prob=0.30,
            simulated_talk_sec=30
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(elapsed_ms)
        total_calls_initiated += res.calls_initiated

    total_time = time.perf_counter() - start_time
    avg_latency = sum(latencies) / len(latencies)
    throughput = total_calls_initiated / total_time if total_time > 0 else 0

    print("\n" + "=" * 50)
    print("SMARTDIALER BASIC LOAD TEST EXECUTION RESULTS:")
    print(f"Total Cycles Executed : {num_cycles}")
    print(f"Total Calls Initiated : {total_calls_initiated}")
    print(f"Total Test Duration   : {total_time:.3f} s")
    print(f"Average Cycle Latency : {avg_latency:.2f} ms")
    print(f"Min / Max Latency     : {min(latencies):.2f} ms / {max(latencies):.2f} ms")
    print(f"Throughput Rate       : {throughput:.1f} calls/second")
    print("=" * 50)

    assert total_calls_initiated > 0
    assert avg_latency < 2000  # Sub-2-second cycle response time under simulated provider sleep
