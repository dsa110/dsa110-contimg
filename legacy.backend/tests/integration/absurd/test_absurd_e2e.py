#!/usr/bin/env python
"""
End-to-End Tests for Absurd Pipeline Integration

This test suite validates the complete Absurd workflow:
1. Synthetic data generation
2. Task spawning
3. Worker execution
4. Result validation
5. Fault tolerance
6. Performance benchmarking
"""

import asyncio
import os
import shutil
import tempfile
import time
from pathlib import Path

import pytest
import pytest_asyncio


# Check if PostgreSQL is available before running tests
def _check_postgres_available():
    """Check if PostgreSQL is reachable for absurd tests."""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 5432))
        sock.close()
        return result == 0
    except Exception:
        return False


POSTGRES_AVAILABLE = _check_postgres_available()

# Skip all tests in this module if PostgreSQL is not available
pytestmark = pytest.mark.skipif(
    not POSTGRES_AVAILABLE,
    reason="PostgreSQL not available on localhost:5432"
)

# Set up environment before imports
os.environ["ABSURD_DATABASE_URL"] = "postgresql://user:password@localhost/dsa110_absurd"
os.environ["ABSURD_QUEUE_NAME"] = "dsa110-pipeline-test"

from dsa110_contimg.absurd.client import AbsurdClient  # noqa: E402
from dsa110_contimg.absurd.config import AbsurdConfig  # noqa: E402


@pytest.fixture
def test_config():
    """Create test configuration."""
    return AbsurdConfig(
        enabled=True,
        database_url="postgresql://user:password@localhost/dsa110_absurd",
        queue_name="dsa110-pipeline-test",
        worker_poll_interval_sec=0.5,  # Faster polling for tests
        task_timeout_sec=300,  # 5 minute timeout for tests
    )


@pytest_asyncio.fixture
async def absurd_client(test_config):
    """Create and connect Absurd client."""
    client = AbsurdClient(test_config.database_url)
    await client.connect()

    # Ensure test queue exists
    try:
        await client._pool.execute(
            "INSERT INTO absurd.queues (queue_name, description) VALUES ($1, $2) ON CONFLICT (queue_name) DO NOTHING",
            test_config.queue_name,
            "Test queue for E2E tests",
        )
    except Exception as e:
        print(f"Queue creation warning: {e}")

    yield client
    await client.close()


@pytest.fixture
def temp_dirs():
    """Create temporary directories for test data."""
    base = tempfile.mkdtemp(prefix="absurd_test_")
    dirs = {
        "input": Path(base) / "incoming",
        "output": Path(base) / "stage",
        "ms": Path(base) / "stage" / "raw" / "ms",
        "images": Path(base) / "stage" / "images",
        "mosaics": Path(base) / "stage" / "mosaics",
    }

    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)

    yield dirs

    # Cleanup
    shutil.rmtree(base, ignore_errors=True)


class TestAbsurdE2E:
    """End-to-end tests for Absurd pipeline."""

    @pytest.mark.asyncio
    async def test_task_spawning_and_claiming(self, absurd_client, test_config):
        """Test basic task lifecycle: spawn -> claim -> complete."""
        # Spawn a test task
        task_id = await absurd_client.spawn_task(
            queue_name=test_config.queue_name,
            task_name="test-task",
            params={"test_param": "test_value"},
            priority=10,
            timeout_sec=300,
        )

        assert task_id is not None
        print(f":check_mark: Task spawned: {task_id}")

        # Claim the task
        task = await absurd_client.claim_task(test_config.queue_name, "test-worker-1")
        assert task is not None
        assert task["task_id"] == task_id
        assert task["status"] == "claimed"
        print(f":check_mark: Task claimed: {task_id}")

        # Complete the task
        await absurd_client.complete_task(task_id, {"result": "success"})

        # Verify completion
        completed_task = await absurd_client.get_task(task_id)
        assert completed_task["status"] == "completed"
        assert completed_task["result"]["result"] == "success"
        print(f":check_mark: Task completed: {task_id}")

    @pytest.mark.asyncio
    async def test_task_failure_handling(self, absurd_client, test_config):
        """Test task failure and error recording."""
        task_id = await absurd_client.spawn_task(
            queue_name=test_config.queue_name,
            task_name="test-failing-task",
            params={"should_fail": True},
            timeout_sec=300,
        )

        # Claim and fail the task
        task = await absurd_client.claim_task(test_config.queue_name, "test-worker-2")
        await absurd_client.fail_task(task_id, "Intentional test failure")

        # Verify failure
        failed_task = await absurd_client.get_task(task_id)
        assert failed_task["status"] == "failed"
        assert "Intentional test failure" in failed_task["error"]
        print(f":check_mark: Task failure handled correctly: {task_id}")

    @pytest.mark.asyncio
    async def test_heartbeat_mechanism(self, absurd_client, test_config):
        """Test task heartbeat updates."""
        task_id = await absurd_client.spawn_task(
            queue_name=test_config.queue_name,
            task_name="test-heartbeat-task",
            params={},
            timeout_sec=300,
        )

        task = await absurd_client.claim_task(test_config.queue_name, "test-worker-3")

        # Record initial heartbeat time
        initial_task = await absurd_client.get_task(task_id)
        initial_heartbeat = initial_task["last_heartbeat"]

        # Wait and send heartbeat
        await asyncio.sleep(1)
        await absurd_client.heartbeat_task(task_id)

        # Verify heartbeat updated
        updated_task = await absurd_client.get_task(task_id)
        assert updated_task["last_heartbeat"] > initial_heartbeat
        print(f":check_mark: Heartbeat mechanism working: {task_id}")

        # Complete task
        await absurd_client.complete_task(task_id, {"result": "heartbeat_test_passed"})

    @pytest.mark.asyncio
    async def test_multiple_workers_parallel_execution(self, absurd_client, test_config):
        """Test multiple workers executing tasks in parallel."""
        num_tasks = 10
        task_ids = []

        # Spawn multiple tasks
        for i in range(num_tasks):
            task_id = await absurd_client.spawn_task(
                queue_name=test_config.queue_name,
                task_name=f"parallel-task-{i}",
                params={"task_index": i},
                priority=5,
                timeout_sec=300,
            )
            task_ids.append(task_id)

        print(f":check_mark: Spawned {num_tasks} tasks")

        # Simulate multiple workers claiming tasks
        claimed_tasks = []
        for worker_id in range(3):  # 3 workers
            for _ in range(num_tasks // 3 + 1):
                task = await absurd_client.claim_task(
                    test_config.queue_name, f"test-worker-parallel-{worker_id}"
                )
                if task:
                    claimed_tasks.append(task)

        print(f":check_mark: Claimed {len(claimed_tasks)} tasks across 3 workers")

        # Complete all claimed tasks
        for task in claimed_tasks:
            await absurd_client.complete_task(
                task["task_id"], {"worker": task["worker_id"], "status": "done"}
            )

        # Verify all tasks completed
        completed_count = 0
        for task_id in task_ids:
            task = await absurd_client.get_task(task_id)
            if task["status"] == "completed":
                completed_count += 1

        assert completed_count == num_tasks
        print(f":check_mark: All {num_tasks} tasks completed successfully")

    @pytest.mark.asyncio
    async def test_task_retry_on_failure(self, absurd_client, test_config):
        """Test that failed tasks can be retried."""
        task_id = await absurd_client.spawn_task(
            queue_name=test_config.queue_name,
            task_name="test-retry-task",
            params={"attempt": 1},
            max_retries=3,
            timeout_sec=300,
        )

        # First attempt: claim and fail
        task = await absurd_client.claim_task(test_config.queue_name, "test-worker-retry")
        await absurd_client.fail_task(task_id, "First attempt failed")

        failed_task = await absurd_client.get_task(task_id)
        assert failed_task["status"] == "failed"
        assert failed_task["retry_count"] == 0
        print(f":check_mark: Task failed on first attempt: {task_id}")

        # Note: Automatic retry logic would need to be implemented in the worker
        # For now, we just verify the retry_count field is tracked

    @pytest.mark.asyncio
    async def test_worker_crash_recovery(self, absurd_client, test_config):
        """Test that tasks are recovered after worker crash (timeout)."""
        task_id = await absurd_client.spawn_task(
            queue_name=test_config.queue_name,
            task_name="test-crash-recovery",
            params={},
            timeout_sec=5,  # Short timeout for testing
        )

        # Claim task but don't complete it (simulate crash)
        task = await absurd_client.claim_task(test_config.queue_name, "test-worker-crash")
        assert task is not None
        print(f":check_mark: Task claimed by worker (simulating crash): {task_id}")

        # In production, timeout handler would mark this as failed
        # and make it available for retry
        # For this test, we just verify the task is in claimed state
        claimed_task = await absurd_client.get_task(task_id)
        assert claimed_task["status"] == "claimed"
        print(f":check_mark: Task in claimed state (would timeout and be retried): {task_id}")


class TestAbsurdPerformance:
    """Performance and benchmarking tests."""

    @pytest.mark.asyncio
    async def test_throughput_benchmark(self, absurd_client, test_config):
        """Benchmark task spawning and claiming throughput."""
        num_tasks = 100

        # Benchmark spawning
        start_time = time.time()
        task_ids = []
        for i in range(num_tasks):
            task_id = await absurd_client.spawn_task(
                queue_name=test_config.queue_name,
                task_name=f"benchmark-task-{i}",
                params={"index": i},
                timeout_sec=300,
            )
            task_ids.append(task_id)
        spawn_time = time.time() - start_time
        spawn_rate = num_tasks / spawn_time

        print(f":check_mark: Spawn rate: {spawn_rate:.2f} tasks/sec ({spawn_time:.2f}s for {num_tasks} tasks)")

        # Benchmark claiming
        start_time = time.time()
        claimed_count = 0
        for _ in range(num_tasks):
            task = await absurd_client.claim_task(test_config.queue_name, "benchmark-worker")
            if task:
                claimed_count += 1
                # Complete immediately to free up
                await absurd_client.complete_task(task["task_id"], {})
        claim_time = time.time() - start_time
        claim_rate = claimed_count / claim_time

        print(
            f":check_mark: Claim+complete rate: {claim_rate:.2f} tasks/sec ({claim_time:.2f}s for {claimed_count} tasks)"
        )

        # Performance assertions
        assert spawn_rate > 10, "Spawn rate should be > 10 tasks/sec"
        assert claim_rate > 5, "Claim+complete rate should be > 5 tasks/sec"

    @pytest.mark.asyncio
    async def test_database_connection_pool(self, test_config):
        """Test connection pool behavior under load."""
        clients = []
        try:
            # Create multiple clients
            for i in range(5):
                client = AbsurdClient(test_config.database_url, pool_min_size=2, pool_max_size=10)
                await client.connect()
                clients.append(client)

            print(f":check_mark: Created {len(clients)} concurrent clients")

            # Execute concurrent operations
            tasks = []
            for client in clients:
                for i in range(10):
                    tasks.append(
                        client.spawn_task(
                            test_config.queue_name, f"pool-test-task", {}, timeout_sec=300
                        )
                    )

            results = await asyncio.gather(*tasks)
            print(f":check_mark: Executed {len(results)} concurrent operations")

        finally:
            # Cleanup
            for client in clients:
                await client.close()


class TestAbsurdFaultTolerance:
    """Fault tolerance and edge case tests."""

    @pytest.mark.asyncio
    async def test_duplicate_claim_prevention(self, absurd_client, test_config):
        """Test that a task cannot be claimed by multiple workers."""
        task_id = await absurd_client.spawn_task(
            queue_name=test_config.queue_name,
            task_name="test-duplicate-claim",
            params={},
            timeout_sec=300,
        )

        # First worker claims
        task1 = await absurd_client.claim_task(test_config.queue_name, "worker-1")
        assert task1 is not None
        assert task1["task_id"] == task_id

        # Second worker tries to claim same task
        task2 = await absurd_client.claim_task(test_config.queue_name, "worker-2")

        # Should get None or a different task
        if task2:
            assert task2["task_id"] != task_id

        print(f":check_mark: Duplicate claim prevention working")

        # Cleanup
        await absurd_client.complete_task(task_id, {})

    @pytest.mark.asyncio
    async def test_empty_queue_handling(self, absurd_client, test_config):
        """Test claiming from empty queue returns None gracefully."""
        # Try to claim from empty queue
        task = await absurd_client.claim_task(test_config.queue_name, "worker-empty")
        assert task is None
        print(f":check_mark: Empty queue handling works correctly")

    @pytest.mark.asyncio
    async def test_invalid_task_id_handling(self, absurd_client):
        """Test handling of invalid task IDs."""
        import uuid

        fake_task_id = str(uuid.uuid4())

        # Try to get non-existent task
        task = await absurd_client.get_task(fake_task_id)
        assert task is None
        print(f":check_mark: Invalid task ID handled gracefully")


# Pytest configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    # Run tests with pytest
    import sys

    sys.exit(pytest.main([__file__, "-v", "-s"]))
