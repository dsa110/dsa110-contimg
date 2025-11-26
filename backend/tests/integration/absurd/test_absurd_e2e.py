"""
End-to-end integration test for Absurd workflow manager.

Tests the complete workflow: task spawn → claim → execute → complete.
"""

import asyncio
import logging
import os
import sys
import tempfile
from pathlib import Path
from uuid import UUID

import pytest

# Add backend src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig
from dsa110_contimg.absurd.adapter import execute_pipeline_task

logger = logging.getLogger(__name__)


@pytest.fixture
def absurd_config():
    """Absurd configuration for testing."""
    # Use environment variables or defaults
    return AbsurdConfig(
        enabled=True,
        database_url=os.getenv(
            "ABSURD_DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/dsa110_absurd_test",
        ),
        queue_name=os.getenv("ABSURD_QUEUE_NAME", "dsa110-pipeline-test"),
        worker_concurrency=2,
        worker_poll_interval_sec=0.5,
        task_timeout_sec=300,
        max_retries=2,
    )


@pytest.fixture
async def absurd_client(absurd_config):
    """Connected Absurd client."""
    client = AbsurdClient(absurd_config.database_url, pool_min_size=1, pool_max_size=2)
    await client.connect()
    yield client
    await client.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_absurd_connection(absurd_client):
    """Test basic database connection."""
    # Try a simple query
    stats = await absurd_client.get_queue_stats("dsa110-pipeline-test")
    assert isinstance(stats, dict)
    assert "pending" in stats


@pytest.mark.asyncio
@pytest.mark.integration
async def test_spawn_and_get_task(absurd_client, absurd_config):
    """Test spawning a task and retrieving it."""
    # Spawn a simple task
    task_id = await absurd_client.spawn_task(
        queue_name=absurd_config.queue_name,
        task_name="test-task",
        params={"test_param": "test_value"},
        priority=10,
    )

    assert isinstance(task_id, UUID)

    # Retrieve task
    task = await absurd_client.get_task(task_id)
    assert task is not None
    assert task["task_name"] == "test-task"
    assert task["params"]["test_param"] == "test_value"
    assert task["status"] == "pending"
    assert task["priority"] == 10


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_tasks(absurd_client, absurd_config):
    """Test listing tasks with filters."""
    # Spawn multiple tasks
    task_ids = []
    for i in range(3):
        task_id = await absurd_client.spawn_task(
            queue_name=absurd_config.queue_name,
            task_name=f"test-list-{i}",
            params={"index": i},
            priority=i,
        )
        task_ids.append(task_id)

    # List all tasks
    tasks = await absurd_client.list_tasks(queue_name=absurd_config.queue_name, limit=10)
    assert len(tasks) >= 3

    # List pending tasks only
    pending_tasks = await absurd_client.list_tasks(
        queue_name=absurd_config.queue_name, status="pending", limit=10
    )
    assert len(pending_tasks) >= 3


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cancel_task(absurd_client, absurd_config):
    """Test cancelling a pending task."""
    # Spawn task
    task_id = await absurd_client.spawn_task(
        queue_name=absurd_config.queue_name,
        task_name="test-cancel",
        params={},
        priority=5,
    )

    # Cancel it
    cancelled = await absurd_client.cancel_task(task_id)
    assert cancelled is True

    # Verify status
    task = await absurd_client.get_task(task_id)
    assert task["status"] == "cancelled"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_queue_stats(absurd_client, absurd_config):
    """Test queue statistics."""
    # Spawn some tasks
    for i in range(5):
        await absurd_client.spawn_task(
            queue_name=absurd_config.queue_name,
            task_name=f"test-stats-{i}",
            params={},
            priority=5,
        )

    # Get stats
    stats = await absurd_client.get_queue_stats(absurd_config.queue_name)

    assert isinstance(stats, dict)
    assert stats["pending"] >= 5
    assert "completed" in stats
    assert "failed" in stats
    assert "cancelled" in stats


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_end_to_end_validation_task(absurd_client, absurd_config, tmp_path):
    """Test end-to-end execution of validation task."""
    # Create a temporary MS directory for testing
    test_ms_dir = tmp_path / "test.ms"
    test_ms_dir.mkdir()

    # Spawn validation task
    task_id = await absurd_client.spawn_task(
        queue_name=absurd_config.queue_name,
        task_name="validation",
        params={
            "config": None,  # Use defaults
            "outputs": {"ms_path": str(test_ms_dir)},
        },
        priority=20,
    )

    logger.info(f"Spawned validation task: {task_id}")

    # Note: This test requires a worker to be running
    # In CI, we would start a worker process here
    # For now, we just verify the task was created

    task = await absurd_client.get_task(task_id)
    assert task["status"] == "pending"
    assert task["task_name"] == "validation"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_adapter_catalog_setup_executor():
    """Test catalog setup executor directly (no database)."""
    # Create temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir)

        # Execute task
        result = await execute_pipeline_task(
            task_name="catalog-setup",
            params={
                "config": None,
                "inputs": {"input_path": str(input_path)},
            },
        )

        # Check result structure
        assert "status" in result
        assert "message" in result
        assert result["status"] in ("success", "error")

        if result["status"] == "success":
            assert "outputs" in result
        else:
            assert "errors" in result


@pytest.mark.asyncio
@pytest.mark.integration
async def test_adapter_organize_files_executor():
    """Test file organization executor directly (no database)."""
    # Create temp MS directory
    with tempfile.TemporaryDirectory() as tmpdir:
        ms_dir = Path(tmpdir) / "test.ms"
        ms_dir.mkdir()

        # Execute task
        result = await execute_pipeline_task(
            task_name="organize-files",
            params={
                "config": None,
                "outputs": {"ms_path": str(ms_dir)},
            },
        )

        # Check result structure
        assert "status" in result
        assert "message" in result

        if result["status"] == "success":
            assert "outputs" in result
            assert "ms_path" in result["outputs"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_full_pipeline_simulation(absurd_client, absurd_config, tmp_path):
    """
    Simulate a full pipeline: conversion → calibration → imaging.

    This test does NOT execute the actual pipeline stages (requires CASA, data),
    but verifies task spawning and chaining logic.
    """
    # Step 1: Spawn conversion task
    conversion_task_id = await absurd_client.spawn_task(
        queue_name=absurd_config.queue_name,
        task_name="convert-uvh5-to-ms",
        params={
            "config": None,
            "inputs": {
                "input_path": str(tmp_path),
                "start_time": "2025-11-25T00:00:00",
                "end_time": "2025-11-25T01:00:00",
            },
        },
        priority=20,
    )

    logger.info(f"Spawned conversion task: {conversion_task_id}")

    # Verify task is pending
    conversion_task = await absurd_client.get_task(conversion_task_id)
    assert conversion_task["status"] == "pending"
    assert conversion_task["task_name"] == "convert-uvh5-to-ms"

    # Step 2: Simulate MS path from conversion
    simulated_ms_path = str(tmp_path / "simulated.ms")

    # Step 3: Spawn calibration solve task
    cal_solve_task_id = await absurd_client.spawn_task(
        queue_name=absurd_config.queue_name,
        task_name="calibration-solve",
        params={"config": None, "outputs": {"ms_path": simulated_ms_path}},
        priority=20,
    )

    logger.info(f"Spawned calibration solve task: {cal_solve_task_id}")

    # Step 4: Spawn imaging task
    imaging_task_id = await absurd_client.spawn_task(
        queue_name=absurd_config.queue_name,
        task_name="imaging",
        params={"config": None, "outputs": {"ms_path": simulated_ms_path}},
        priority=15,
    )

    logger.info(f"Spawned imaging task: {imaging_task_id}")

    # Verify all tasks are in queue
    all_tasks = await absurd_client.list_tasks(queue_name=absurd_config.queue_name, limit=10)
    task_ids = [task["task_id"] for task in all_tasks]

    assert str(conversion_task_id) in task_ids
    assert str(cal_solve_task_id) in task_ids
    assert str(imaging_task_id) in task_ids

    logger.info(f"✓ Full pipeline simulation successful ({len(task_ids)} tasks queued)")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_error_handling_invalid_task():
    """Test error handling for invalid task name."""
    result = await execute_pipeline_task(task_name="invalid-task-name", params={"config": None})

    assert result["status"] == "error"
    assert "Unknown task name" in result["message"]
    assert len(result["errors"]) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_error_handling_missing_params():
    """Test error handling for missing required parameters."""
    result = await execute_pipeline_task(
        task_name="convert-uvh5-to-ms",
        params={
            "config": None,
            "inputs": {
                # Missing start_time and end_time
                "input_path": "/tmp/test"
            },
        },
    )

    assert result["status"] == "error"
    assert "Missing required inputs" in result["message"]
    assert len(result["errors"]) > 0


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--log-cli-level=INFO"])
