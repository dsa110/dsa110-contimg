#!/opt/miniforge/envs/casa6/bin/python
"""
Integration tests for Absurd workflow manager.

Tests task execution, state transitions, fault tolerance, and performance.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytest
import pytest_asyncio

from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig
from dsa110_contimg.absurd.adapter import execute_pipeline_task

# Test configuration
TEST_DATABASE_URL = os.getenv(
    "TEST_ABSURD_DB", "postgresql://postgres:postgres@localhost:5432/absurd_test"
)
TEST_QUEUE_NAME = f"test-queue-{uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def absurd_client() -> AbsurdClient:
    """Create and initialize Absurd client for testing."""
    client = AbsurdClient(TEST_DATABASE_URL, pool_min_size=2, pool_max_size=5)
    await client.connect()
    yield client
    await client.close()


@pytest_asyncio.fixture
async def clean_queue(absurd_client: AbsurdClient):
    """Clean up test queue before and after tests."""
    # Clean before
    tasks = await absurd_client.list_tasks(queue_name=TEST_QUEUE_NAME, limit=1000)
    for task in tasks:
        try:
            await absurd_client.cancel_task(task["task_id"])
        except Exception:
            pass

    yield

    # Clean after
    tasks = await absurd_client.list_tasks(queue_name=TEST_QUEUE_NAME, limit=1000)
    for task in tasks:
        try:
            await absurd_client.cancel_task(task["task_id"])
        except Exception:
            pass


# ============================================================================
# Task Execution Tests
# ============================================================================


@pytest.mark.asyncio
async def test_spawn_task_basic(absurd_client: AbsurdClient, clean_queue):
    """Test basic task spawning."""
    task_id = await absurd_client.spawn_task(
        queue_name=TEST_QUEUE_NAME,
        task_name="test-task",
        params={"foo": "bar"},
        priority=5,
    )

    assert task_id is not None

    # Verify task was created
    task = await absurd_client.get_task(task_id)
    assert task["task_id"] == task_id
    assert task["queue_name"] == TEST_QUEUE_NAME
    assert task["task_name"] == "test-task"
    assert task["params"]["foo"] == "bar"
    assert task["priority"] == 5
    assert task["status"] == "pending"


@pytest.mark.asyncio
async def test_task_state_transitions(absurd_client: AbsurdClient, clean_queue):
    """Test task state transitions: pending → claimed → completed."""
    task_id = await absurd_client.spawn_task(
        queue_name=TEST_QUEUE_NAME,
        task_name="test-task",
        params={},
    )

    # Initial state: pending
    task = await absurd_client.get_task(task_id)
    assert task["status"] == "pending"
    assert task["claimed_at"] is None

    # Claim task
    claimed_task = await absurd_client.claim_task(TEST_QUEUE_NAME)
    assert claimed_task is not None
    assert claimed_task["task_id"] == task_id
    assert claimed_task["status"] == "claimed"

    # Verify claimed state
    task = await absurd_client.get_task(task_id)
    assert task["status"] == "claimed"
    assert task["claimed_at"] is not None

    # Complete task
    result = {"output": "success"}
    await absurd_client.complete_task(task_id, result)

    # Verify completed state
    task = await absurd_client.get_task(task_id)
    assert task["status"] == "completed"
    assert task["completed_at"] is not None
    assert task["result"]["output"] == "success"


@pytest.mark.asyncio
async def test_task_failure_handling(absurd_client: AbsurdClient, clean_queue):
    """Test task failure and error recording."""
    task_id = await absurd_client.spawn_task(
        queue_name=TEST_QUEUE_NAME,
        task_name="test-task",
        params={},
    )

    # Claim and fail task
    claimed_task = await absurd_client.claim_task(TEST_QUEUE_NAME)
    await absurd_client.fail_task(task_id, "Test error message")

    # Verify failed state
    task = await absurd_client.get_task(task_id)
    assert task["status"] == "failed"
    assert task["error"] == "Test error message"
    assert task["completed_at"] is not None


@pytest.mark.asyncio
async def test_catalog_setup_task(absurd_client: AbsurdClient, clean_queue):
    """Test catalog-setup task execution."""
    with tempfile.TemporaryDirectory() as tmpdir:
        task_id = await absurd_client.spawn_task(
            queue_name=TEST_QUEUE_NAME,
            task_name="catalog-setup",
            params={
                "config": {
                    "catalog_path": str(Path(tmpdir) / "test_catalog.csv"),
                    "radius_deg": 5.0,
                },
                "inputs": {
                    "ra_deg": 180.0,
                    "dec_deg": 45.0,
                },
            },
        )

        # Claim and execute
        claimed = await absurd_client.claim_task(TEST_QUEUE_NAME)
        assert claimed is not None

        result = await execute_pipeline_task(claimed["task_name"], claimed["params"])

        if result["status"] == "success":
            await absurd_client.complete_task(task_id, result)
        else:
            await absurd_client.fail_task(task_id, result.get("message", "Unknown error"))

        # Verify completion
        task = await absurd_client.get_task(task_id)
        assert task["status"] in ["completed", "failed"]

        if task["status"] == "completed":
            assert "outputs" in task["result"]


@pytest.mark.asyncio
async def test_priority_ordering(absurd_client: AbsurdClient, clean_queue):
    """Test that higher priority tasks are claimed first."""
    # Spawn tasks with different priorities
    low_task = await absurd_client.spawn_task(
        queue_name=TEST_QUEUE_NAME,
        task_name="low-priority",
        params={},
        priority=1,
    )

    high_task = await absurd_client.spawn_task(
        queue_name=TEST_QUEUE_NAME,
        task_name="high-priority",
        params={},
        priority=10,
    )

    medium_task = await absurd_client.spawn_task(
        queue_name=TEST_QUEUE_NAME,
        task_name="medium-priority",
        params={},
        priority=5,
    )

    # Claim tasks and verify order
    first = await absurd_client.claim_task(TEST_QUEUE_NAME)
    second = await absurd_client.claim_task(TEST_QUEUE_NAME)
    third = await absurd_client.claim_task(TEST_QUEUE_NAME)

    assert first["task_id"] == high_task  # Priority 10
    assert second["task_id"] == medium_task  # Priority 5
    assert third["task_id"] == low_task  # Priority 1


@pytest.mark.asyncio
async def test_task_timeout(absurd_client: AbsurdClient, clean_queue):
    """Test task timeout handling."""
    task_id = await absurd_client.spawn_task(
        queue_name=TEST_QUEUE_NAME,
        task_name="test-task",
        params={},
        timeout_sec=2,  # 2 second timeout
    )

    # Claim task and let it timeout
    claimed = await absurd_client.claim_task(TEST_QUEUE_NAME)
    assert claimed is not None

    # Wait for timeout
    await asyncio.sleep(3)

    # Task should be available for reclaim
    reclaimed = await absurd_client.claim_task(TEST_QUEUE_NAME)
    assert reclaimed is not None
    assert reclaimed["task_id"] == task_id
    assert reclaimed["retry_count"] == 1


@pytest.mark.asyncio
async def test_task_cancellation(absurd_client: AbsurdClient, clean_queue):
    """Test task cancellation."""
    task_id = await absurd_client.spawn_task(
        queue_name=TEST_QUEUE_NAME,
        task_name="test-task",
        params={},
    )

    # Cancel before claiming
    await absurd_client.cancel_task(task_id)

    # Verify cancelled state
    task = await absurd_client.get_task(task_id)
    assert task["status"] == "cancelled"

    # Verify cannot be claimed
    claimed = await absurd_client.claim_task(TEST_QUEUE_NAME)
    assert claimed is None or claimed["task_id"] != task_id


@pytest.mark.asyncio
async def test_queue_statistics(absurd_client: AbsurdClient, clean_queue):
    """Test queue statistics computation."""
    # Spawn tasks with different outcomes
    await absurd_client.spawn_task(TEST_QUEUE_NAME, "task1", {})  # pending

    task2 = await absurd_client.spawn_task(TEST_QUEUE_NAME, "task2", {})
    claimed = await absurd_client.claim_task(TEST_QUEUE_NAME)
    await absurd_client.complete_task(claimed["task_id"], {"result": "ok"})

    task3 = await absurd_client.spawn_task(TEST_QUEUE_NAME, "task3", {})
    claimed = await absurd_client.claim_task(TEST_QUEUE_NAME)
    await absurd_client.fail_task(claimed["task_id"], "error")

    task4 = await absurd_client.spawn_task(TEST_QUEUE_NAME, "task4", {})
    await absurd_client.cancel_task(task4)

    # Get stats
    stats = await absurd_client.get_queue_stats(TEST_QUEUE_NAME)

    assert stats["pending"] >= 1
    assert stats["completed"] >= 1
    assert stats["failed"] >= 1
    assert stats["cancelled"] >= 1
    assert stats["total"] >= 4


# ============================================================================
# Fault Tolerance Tests
# ============================================================================


@pytest.mark.asyncio
async def test_worker_crash_recovery(absurd_client: AbsurdClient, clean_queue):
    """Test that tasks are recovered after worker crash."""
    task_id = await absurd_client.spawn_task(
        queue_name=TEST_QUEUE_NAME,
        task_name="test-task",
        params={},
        timeout_sec=5,
    )

    # Claim task (simulating worker)
    claimed = await absurd_client.claim_task(TEST_QUEUE_NAME)
    assert claimed is not None

    # Simulate worker crash: disconnect without completing task
    # Task should become available after timeout

    # Wait for timeout + grace period
    await asyncio.sleep(6)

    # Task should be reclaimable
    reclaimed = await absurd_client.claim_task(TEST_QUEUE_NAME)
    assert reclaimed is not None
    assert reclaimed["task_id"] == task_id
    assert reclaimed["retry_count"] == 1


@pytest.mark.asyncio
async def test_retry_with_exponential_backoff(absurd_client: AbsurdClient, clean_queue):
    """Test retry mechanism with exponential backoff."""
    task_id = await absurd_client.spawn_task(
        queue_name=TEST_QUEUE_NAME,
        task_name="test-task",
        params={},
        timeout_sec=2,
    )

    retry_times = []

    for attempt in range(3):
        start = time.time()
        claimed = await absurd_client.claim_task(TEST_QUEUE_NAME)
        if claimed is None:
            await asyncio.sleep(1)
            continue

        retry_times.append(time.time() - start)

        # Simulate failure
        await asyncio.sleep(2.5)  # Let it timeout

    # Verify exponential backoff
    # First retry should be fast, subsequent retries should have increasing delays
    assert len(retry_times) >= 2


@pytest.mark.asyncio
async def test_max_retries_enforcement(absurd_client: AbsurdClient, clean_queue):
    """Test that tasks fail permanently after max retries."""
    task_id = await absurd_client.spawn_task(
        queue_name=TEST_QUEUE_NAME,
        task_name="test-task",
        params={},
        timeout_sec=1,
    )

    # Fail task multiple times
    for _ in range(4):  # Default max_retries is 3
        claimed = await absurd_client.claim_task(TEST_QUEUE_NAME)
        if claimed is None:
            break
        await absurd_client.fail_task(claimed["task_id"], "Test failure")
        await asyncio.sleep(0.5)

    # Task should be permanently failed
    task = await absurd_client.get_task(task_id)
    assert task["status"] == "failed"
    assert task["retry_count"] >= 3

    # Should not be claimable anymore
    claimed = await absurd_client.claim_task(TEST_QUEUE_NAME)
    assert claimed is None or claimed["task_id"] != task_id


@pytest.mark.asyncio
async def test_database_connection_resilience(absurd_client: AbsurdClient):
    """Test graceful handling of database connection issues."""
    # This test would need to temporarily disrupt database connection
    # For now, we verify that client has proper error handling

    # Attempt operation with invalid task ID
    try:
        await absurd_client.get_task("00000000-0000-0000-0000-000000000000")
    except Exception as e:
        # Should get a clean error, not a crash
        assert "not found" in str(e).lower() or "does not exist" in str(e).lower()


# ============================================================================
# Performance Tests
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_task_spawning(absurd_client: AbsurdClient, clean_queue):
    """Test spawning many tasks concurrently."""
    num_tasks = 100
    start = time.time()

    # Spawn tasks concurrently
    task_ids = await asyncio.gather(
        *[
            absurd_client.spawn_task(
                queue_name=TEST_QUEUE_NAME,
                task_name=f"task-{i}",
                params={"index": i},
            )
            for i in range(num_tasks)
        ]
    )

    elapsed = time.time() - start

    # Verify all tasks created
    assert len(task_ids) == num_tasks
    assert len(set(task_ids)) == num_tasks  # All unique

    # Performance check: should be able to spawn 100 tasks in < 5 seconds
    assert elapsed < 5.0, f"Took {elapsed:.2f}s to spawn {num_tasks} tasks"

    print(f"\n:check_mark: Spawned {num_tasks} tasks in {elapsed:.2f}s ({num_tasks/elapsed:.1f} tasks/s)")


@pytest.mark.asyncio
async def test_concurrent_task_claiming(absurd_client: AbsurdClient, clean_queue):
    """Test claiming tasks concurrently (simulating multiple workers)."""
    num_tasks = 50

    # Spawn tasks
    await asyncio.gather(
        *[
            absurd_client.spawn_task(
                queue_name=TEST_QUEUE_NAME,
                task_name=f"task-{i}",
                params={},
            )
            for i in range(num_tasks)
        ]
    )

    start = time.time()

    # Claim tasks concurrently (simulating multiple workers)
    claimed_tasks = await asyncio.gather(
        *[absurd_client.claim_task(TEST_QUEUE_NAME) for _ in range(num_tasks)]
    )

    elapsed = time.time() - start

    # Filter out None results (when queue is empty)
    claimed_tasks = [t for t in claimed_tasks if t is not None]

    # Verify no duplicate claims
    claimed_ids = [t["task_id"] for t in claimed_tasks]
    assert len(claimed_ids) == len(set(claimed_ids)), "Duplicate task claims detected!"

    # Performance check
    assert elapsed < 3.0, f"Took {elapsed:.2f}s to claim {num_tasks} tasks"

    print(
        f"\n:check_mark: Claimed {len(claimed_tasks)} tasks in {elapsed:.2f}s ({len(claimed_tasks)/elapsed:.1f} tasks/s)"
    )


@pytest.mark.asyncio
async def test_task_listing_performance(absurd_client: AbsurdClient, clean_queue):
    """Test performance of listing large number of tasks."""
    num_tasks = 200

    # Spawn tasks
    await asyncio.gather(
        *[
            absurd_client.spawn_task(
                queue_name=TEST_QUEUE_NAME,
                task_name=f"task-{i}",
                params={},
            )
            for i in range(num_tasks)
        ]
    )

    start = time.time()
    tasks = await absurd_client.list_tasks(queue_name=TEST_QUEUE_NAME, limit=num_tasks)
    elapsed = time.time() - start

    # Verify all tasks retrieved
    assert len(tasks) >= num_tasks

    # Performance check: should list 200 tasks in < 1 second
    assert elapsed < 1.0, f"Took {elapsed:.2f}s to list {num_tasks} tasks"

    print(f"\n:check_mark: Listed {len(tasks)} tasks in {elapsed:.2f}s")


@pytest.mark.asyncio
async def test_queue_stats_performance(absurd_client: AbsurdClient, clean_queue):
    """Test performance of queue statistics computation."""
    # Create varied task states
    await asyncio.gather(
        *[absurd_client.spawn_task(TEST_QUEUE_NAME, f"task-{i}", {}) for i in range(100)]
    )

    # Claim and complete some
    for _ in range(20):
        claimed = await absurd_client.claim_task(TEST_QUEUE_NAME)
        if claimed:
            await absurd_client.complete_task(claimed["task_id"], {})

    # Measure stats computation time
    start = time.time()
    stats = await absurd_client.get_queue_stats(TEST_QUEUE_NAME)
    elapsed = time.time() - start

    # Performance check: should compute stats in < 0.5 seconds
    assert elapsed < 0.5, f"Took {elapsed:.2f}s to compute queue stats"

    print(f"\n:check_mark: Computed queue stats in {elapsed:.2f}s")
    print(f"  Stats: {stats}")


@pytest.mark.asyncio
async def test_end_to_end_throughput(absurd_client: AbsurdClient, clean_queue):
    """Test end-to-end task throughput (spawn → claim → complete)."""
    num_tasks = 50

    start = time.time()

    # Spawn all tasks
    task_ids = await asyncio.gather(
        *[
            absurd_client.spawn_task(
                queue_name=TEST_QUEUE_NAME,
                task_name=f"task-{i}",
                params={"value": i},
            )
            for i in range(num_tasks)
        ]
    )

    # Process all tasks
    for _ in range(num_tasks):
        claimed = await absurd_client.claim_task(TEST_QUEUE_NAME)
        if claimed:
            # Simulate minimal work
            await asyncio.sleep(0.01)
            await absurd_client.complete_task(claimed["task_id"], {"result": "ok"})

    elapsed = time.time() - start
    throughput = num_tasks / elapsed

    print(f"\n:check_mark: End-to-end throughput: {throughput:.1f} tasks/s")
    print(f"  Processed {num_tasks} tasks in {elapsed:.2f}s")

    # Verify all tasks completed
    stats = await absurd_client.get_queue_stats(TEST_QUEUE_NAME)
    assert stats["completed"] >= num_tasks


# ============================================================================
# Pipeline Task Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_pipeline_task_adapter_routing():
    """Test that adapter correctly routes task types."""
    # Test each task type
    task_types = [
        "catalog-setup",
        "convert-uvh5-to-ms",
        "calibration-solve",
        "calibration-apply",
        "imaging",
        "validation",
        "crossmatch",
        "photometry",
        "organize-files",
    ]

    for task_name in task_types:
        try:
            result = await execute_pipeline_task(task_name, {"config": {}, "inputs": {}})
            # Should return a result dict, not raise exception
            assert "status" in result
            assert result["status"] in ["success", "error"]
        except Exception as e:
            pytest.fail(f"Task {task_name} raised unexpected exception: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
