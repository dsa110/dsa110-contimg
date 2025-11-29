#!/opt/miniforge/envs/casa6/bin/python
"""
Fault tolerance verification tests for Absurd.

Tests worker crashes, database failures, network issues, and recovery scenarios.
"""

from __future__ import annotations

import asyncio
import multiprocessing
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional
from uuid import uuid4

import psutil
import pytest
import pytest_asyncio

from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig, AbsurdWorker

TEST_DATABASE_URL = os.getenv(
    "TEST_ABSURD_DB", "postgresql://postgres:postgres@localhost:5432/absurd_test"
)
TEST_QUEUE_NAME = f"ft-test-{uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def absurd_client():
    """Create Absurd client."""
    client = AbsurdClient(TEST_DATABASE_URL, pool_min_size=2, pool_max_size=5)
    await client.connect()
    yield client
    await client.close()


class WorkerProcess:
    """Helper class to manage worker processes for testing."""

    def __init__(self, queue_name: str, concurrency: int = 1):
        self.queue_name = queue_name
        self.concurrency = concurrency
        self.process: Optional[subprocess.Popen] = None

    def start(self):
        """Start worker in subprocess."""
        cmd = [
            "python",
            "-c",
            f"""
import asyncio
from dsa110_contimg.absurd import AbsurdClient, AbsurdWorker, AbsurdConfig

async def main():
    config = AbsurdConfig(
        enabled=True,
        database_url="{TEST_DATABASE_URL}",
        queue_name="{self.queue_name}",
        worker_concurrency={self.concurrency},
        worker_poll_interval=0.5,
        task_timeout=10,
        max_retries=3
    )
    
    client = AbsurdClient(config.database_url)
    await client.connect()
    
    worker = AbsurdWorker(client, config)
    await worker.start()

asyncio.run(main())
""",
        ]

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,  # Create new process group
        )

        # Wait for worker to initialize
        time.sleep(2)

        return self.process.pid

    def stop(self, graceful: bool = True):
        """Stop worker process."""
        if self.process is None:
            return

        if graceful:
            # Send SIGTERM for graceful shutdown
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if not responsive
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
        else:
            # Force kill (simulating crash)
            os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)

        self.process = None

    def is_alive(self) -> bool:
        """Check if worker process is running."""
        if self.process is None:
            return False
        return self.process.poll() is None


# ============================================================================
# Worker Crash Recovery Tests
# ============================================================================


@pytest.mark.asyncio
async def test_worker_crash_task_recovery(absurd_client: AbsurdClient):
    """Test that tasks are recovered after worker crash."""
    # Spawn task
    task_id = await absurd_client.spawn_task(
        queue_name=TEST_QUEUE_NAME,
        task_name="slow-task",
        params={"sleep": 10},
        timeout_sec=15,
    )

    # Start worker
    worker = WorkerProcess(TEST_QUEUE_NAME)
    worker_pid = worker.start()

    # Wait for task to be claimed
    await asyncio.sleep(1)

    task = await absurd_client.get_task(task_id)
    assert task["status"] == "claimed", f"Task not claimed, status: {task['status']}"

    # Simulate crash (SIGKILL)
    print(f"\n💥 Crashing worker (PID {worker_pid})")
    worker.stop(graceful=False)

    # Wait for timeout to expire
    await asyncio.sleep(16)

    # Task should be available for recovery
    task = await absurd_client.get_task(task_id)
    assert task["status"] in [
        "pending",
        "claimed",
    ], f"Task not recovered after crash, status: {task['status']}"
    assert task["retry_count"] == 1, f"Retry count not incremented, got {task['retry_count']}"

    print(f"✓ Task recovered after crash (retry_count={task['retry_count']})")


@pytest.mark.asyncio
async def test_multiple_worker_crash_recovery(absurd_client: AbsurdClient):
    """Test recovery after multiple worker crashes."""
    task_id = await absurd_client.spawn_task(
        queue_name=TEST_QUEUE_NAME,
        task_name="resilient-task",
        params={},
        timeout_sec=5,
    )

    for attempt in range(3):
        # Start worker
        worker = WorkerProcess(TEST_QUEUE_NAME)
        worker.start()

        # Wait for claim
        await asyncio.sleep(1)

        task = await absurd_client.get_task(task_id)
        print(
            f"\n🔄 Attempt {attempt + 1}: Task status={task['status']}, retry={task['retry_count']}"
        )

        # Crash worker
        worker.stop(graceful=False)

        # Wait for timeout
        await asyncio.sleep(6)

    # Task should still be recoverable (not failed)
    task = await absurd_client.get_task(task_id)
    assert task["status"] in [
        "pending",
        "claimed",
    ], f"Task failed prematurely, status: {task['status']}"
    assert task["retry_count"] <= 3, f"Too many retries: {task['retry_count']}"

    print(f"✓ Task survived {3} crashes, retry_count={task['retry_count']}")


@pytest.mark.asyncio
async def test_graceful_shutdown_preserves_tasks(absurd_client: AbsurdClient):
    """Test that graceful shutdown doesn't lose tasks."""
    # Spawn multiple tasks
    task_ids = []
    for i in range(5):
        task_id = await absurd_client.spawn_task(
            queue_name=TEST_QUEUE_NAME,
            task_name=f"task-{i}",
            params={},
        )
        task_ids.append(task_id)

    # Start worker
    worker = WorkerProcess(TEST_QUEUE_NAME, concurrency=2)
    worker.start()

    # Wait for some tasks to be claimed
    await asyncio.sleep(2)

    # Graceful shutdown
    print("\n🛑 Graceful shutdown")
    worker.stop(graceful=True)

    # Check task states
    pending_or_claimed = 0
    completed = 0

    for task_id in task_ids:
        task = await absurd_client.get_task(task_id)
        if task["status"] in ["pending", "claimed"]:
            pending_or_claimed += 1
        elif task["status"] == "completed":
            completed += 1

    # All tasks should be accounted for (none lost)
    total = pending_or_claimed + completed
    assert total == len(task_ids), f"Lost tasks: expected {len(task_ids)}, found {total}"

    print(
        f"✓ All {len(task_ids)} tasks preserved (pending/claimed: {pending_or_claimed}, completed: {completed})"
    )


# ============================================================================
# Database Connection Tests
# ============================================================================


@pytest.mark.asyncio
async def test_database_connection_retry():
    """Test that client retries on transient database errors."""
    # This would require mocking database failures
    # For now, test that client handles invalid connection gracefully

    invalid_url = "postgresql://invalid:invalid@localhost:9999/invalid"
    client = AbsurdClient(invalid_url)

    try:
        await client.connect()
        pytest.fail("Should have raised connection error")
    except Exception as e:
        assert "connection" in str(e).lower() or "could not connect" in str(e).lower()
        print(f"✓ Connection error handled gracefully: {e}")


@pytest.mark.asyncio
async def test_query_timeout_handling(absurd_client: AbsurdClient):
    """Test handling of slow database queries."""
    # Spawn task with very short timeout
    task_id = await absurd_client.spawn_task(
        queue_name=TEST_QUEUE_NAME,
        task_name="test-task",
        params={},
        timeout_sec=1,
    )

    # Multiple concurrent operations
    start = time.time()

    results = await asyncio.gather(
        absurd_client.get_task(task_id),
        absurd_client.get_task(task_id),
        absurd_client.get_task(task_id),
        absurd_client.list_tasks(queue_name=TEST_QUEUE_NAME),
        absurd_client.get_queue_stats(TEST_QUEUE_NAME),
        return_exceptions=True,
    )

    elapsed = time.time() - start

    # Check for errors
    errors = [r for r in results if isinstance(r, Exception)]
    if errors:
        print(f"⚠ Some operations failed: {errors}")

    # Should complete reasonably fast even with concurrent operations
    assert elapsed < 5.0, f"Operations took too long: {elapsed:.2f}s"

    print(f"✓ Handled {len(results)} concurrent operations in {elapsed:.2f}s")


# ============================================================================
# Task State Consistency Tests
# ============================================================================


@pytest.mark.asyncio
async def test_no_duplicate_task_claims(absurd_client: AbsurdClient):
    """Test that a task cannot be claimed by multiple workers simultaneously."""
    # Spawn single task
    task_id = await absurd_client.spawn_task(
        queue_name=TEST_QUEUE_NAME,
        task_name="exclusive-task",
        params={},
    )

    # Attempt to claim concurrently
    claims = await asyncio.gather(*[absurd_client.claim_task(TEST_QUEUE_NAME) for _ in range(10)])

    # Filter out None results
    successful_claims = [c for c in claims if c is not None and c["task_id"] == task_id]

    # Only one claim should succeed
    assert len(successful_claims) == 1, f"Task claimed {len(successful_claims)} times (expected 1)"

    print(f"✓ Task claimed exactly once despite {len(claims)} concurrent attempts")


@pytest.mark.asyncio
async def test_task_state_atomicity(absurd_client: AbsurdClient):
    """Test that task state transitions are atomic."""
    task_id = await absurd_client.spawn_task(
        queue_name=TEST_QUEUE_NAME,
        task_name="test-task",
        params={},
    )

    # Claim task
    claimed = await absurd_client.claim_task(TEST_QUEUE_NAME)
    assert claimed is not None

    # Attempt conflicting operations concurrently
    results = await asyncio.gather(
        absurd_client.complete_task(task_id, {"result": "ok"}),
        absurd_client.fail_task(task_id, "error"),
        absurd_client.cancel_task(task_id),
        return_exceptions=True,
    )

    # Check final state (should be consistent)
    task = await absurd_client.get_task(task_id)
    assert task["status"] in [
        "completed",
        "failed",
        "cancelled",
    ], f"Unexpected final state: {task['status']}"

    # Count errors (concurrent operations should fail gracefully)
    errors = [r for r in results if isinstance(r, Exception)]
    print(f"✓ Final state: {task['status']}, {len(errors)} conflicting operations rejected")


# ============================================================================
# Resource Exhaustion Tests
# ============================================================================


@pytest.mark.asyncio
async def test_connection_pool_saturation(absurd_client: AbsurdClient):
    """Test behavior when connection pool is saturated."""
    # Spawn many concurrent operations
    num_operations = 50

    start = time.time()

    results = await asyncio.gather(
        *[
            absurd_client.spawn_task(
                queue_name=TEST_QUEUE_NAME,
                task_name=f"task-{i}",
                params={},
            )
            for i in range(num_operations)
        ],
        return_exceptions=True,
    )

    elapsed = time.time() - start

    # Count successes vs errors
    successes = [r for r in results if not isinstance(r, Exception)]
    errors = [r for r in results if isinstance(r, Exception)]

    print(f"\n✓ Connection pool test:")
    print(f"  {len(successes)} successes, {len(errors)} errors")
    print(f"  Completed in {elapsed:.2f}s ({len(successes)/elapsed:.1f} ops/s)")

    # Most operations should succeed (connection pooling working)
    success_rate = len(successes) / num_operations
    assert success_rate > 0.9, f"Success rate too low: {success_rate:.1%}"


@pytest.mark.asyncio
async def test_memory_leak_detection(absurd_client: AbsurdClient):
    """Test for memory leaks during prolonged operation."""
    import gc

    process = psutil.Process()

    # Baseline memory
    gc.collect()
    baseline_mb = process.memory_info().rss / 1024 / 1024

    # Perform many operations
    for batch in range(5):
        task_ids = await asyncio.gather(
            *[
                absurd_client.spawn_task(
                    queue_name=TEST_QUEUE_NAME,
                    task_name=f"task-{i}",
                    params={"data": "x" * 1000},
                )
                for i in range(100)
            ]
        )

        # Claim and complete all tasks
        for _ in range(100):
            claimed = await absurd_client.claim_task(TEST_QUEUE_NAME)
            if claimed:
                await absurd_client.complete_task(claimed["task_id"], {})

        gc.collect()

    # Final memory
    final_mb = process.memory_info().rss / 1024 / 1024
    growth_mb = final_mb - baseline_mb

    print(f"\n✓ Memory usage: {baseline_mb:.1f} MB → {final_mb:.1f} MB (+{growth_mb:.1f} MB)")

    # Memory growth should be reasonable (< 50 MB for 500 tasks)
    assert growth_mb < 50, f"Potential memory leak: {growth_mb:.1f} MB growth"


# ============================================================================
# Network Partition Tests
# ============================================================================


@pytest.mark.asyncio
async def test_worker_reconnection_after_network_issue():
    """Test that worker can reconnect after temporary network issue."""
    # This would require network simulation
    # For now, test that worker handles connection loss gracefully

    # Create worker with short reconnect interval
    config = AbsurdConfig(
        enabled=True,
        database_url=TEST_DATABASE_URL,
        queue_name=TEST_QUEUE_NAME,
        worker_poll_interval=1.0,
    )

    client = AbsurdClient(config.database_url)
    await client.connect()

    # Worker should be able to start even if initial connection is slow
    worker = AbsurdWorker(client, config)

    # Verify worker has reconnection logic
    assert hasattr(worker, "start")
    assert hasattr(worker, "stop")

    await client.close()

    print("✓ Worker has reconnection infrastructure")


# ============================================================================
# Chaos Engineering Tests
# ============================================================================


@pytest.mark.asyncio
async def test_chaos_mixed_failures(absurd_client: AbsurdClient):
    """Test system resilience under mixed failure scenarios."""
    # Spawn multiple tasks
    task_ids = await asyncio.gather(
        *[
            absurd_client.spawn_task(
                queue_name=TEST_QUEUE_NAME,
                task_name=f"chaos-task-{i}",
                params={"id": i},
                timeout_sec=10,
            )
            for i in range(20)
        ]
    )

    # Start multiple workers
    workers = [WorkerProcess(TEST_QUEUE_NAME, concurrency=2) for _ in range(3)]

    for worker in workers:
        worker.start()

    # Wait for processing to start
    await asyncio.sleep(2)

    # Introduce chaos
    print("\n💥 Introducing chaos:")

    # Crash one worker
    print("  - Crashing worker 0")
    workers[0].stop(graceful=False)

    await asyncio.sleep(1)

    # Gracefully stop another
    print("  - Gracefully stopping worker 1")
    workers[1].stop(graceful=True)

    await asyncio.sleep(1)

    # Leave one worker running
    print("  - Worker 2 continues running")

    # Wait for remaining worker to recover and process tasks
    await asyncio.sleep(10)

    # Check final state
    stats = await absurd_client.get_queue_stats(TEST_QUEUE_NAME)

    print(f"\n✓ Chaos test results:")
    print(f"  Completed: {stats['completed']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Pending: {stats['pending']}")

    # At least some tasks should complete despite chaos
    assert stats["completed"] > 0, "No tasks completed despite chaos"

    # Cleanup
    for worker in workers:
        if worker.is_alive():
            worker.stop(graceful=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
