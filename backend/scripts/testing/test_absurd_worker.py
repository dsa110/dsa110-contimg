#!/usr/bin/env python3
"""
Test script for ABSURD worker functionality.

Usage:
    conda activate casa6
    python scripts/testing/test_absurd_worker.py
"""

import asyncio
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("absurd_test")


async def simple_executor(task_name: str, params: dict) -> dict:
    """Simple test executor that echoes the task params."""
    logger.info(f"Executing task: {task_name} with params: {params}")
    
    # Simulate some work
    await asyncio.sleep(0.5)
    
    # Return success with results
    return {
        "status": "success",
        "task_name": task_name,
        "input_params": params,
        "processed_at": datetime.utcnow().isoformat() + "Z",
        "message": f"Successfully processed {task_name}",
    }


async def main():
    """Test the ABSURD worker by spawning and processing a task."""
    from dsa110_contimg.absurd.client import AbsurdClient
    from dsa110_contimg.absurd.config import AbsurdConfig
    from dsa110_contimg.absurd.worker import AbsurdWorker
    
    # Load config from environment
    config = AbsurdConfig.from_env()
    logger.info(f"Using database: {config.database_url}")
    logger.info(f"Queue name: {config.queue_name}")
    
    # Create client and spawn a test task
    client = AbsurdClient(config.database_url)
    
    async with client:
        # Check initial queue stats
        stats = await client.get_queue_stats(config.queue_name)
        logger.info(f"Initial queue stats: {stats}")
        
        # Spawn a test task
        test_params = {
            "test_id": "worker-test-001",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": "echo",
        }
        
        task_id = await client.spawn_task(
            queue_name=config.queue_name,
            task_name="worker-test",
            params=test_params,
            priority=10,
        )
        logger.info(f"Spawned test task: {task_id}")
        
        # Verify task exists and is pending
        task = await client.get_task(task_id)
        assert task is not None, "Task should exist"
        assert task["status"] == "pending", f"Task should be pending, got {task['status']}"
        logger.info(f"Task status: {task['status']}")
        
        # Create worker with our test executor
        worker = AbsurdWorker(config, simple_executor)
        
        # Run worker in background
        logger.info("Starting worker...")
        worker_task = asyncio.create_task(worker.start())
        
        # Wait for task to be processed (with timeout)
        max_wait = 10.0
        poll_interval = 0.5
        elapsed = 0.0
        
        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            
            task = await client.get_task(task_id)
            if task and task["status"] in ("completed", "failed"):
                break
        
        # Stop the worker
        await worker.stop()
        try:
            await asyncio.wait_for(worker_task, timeout=2.0)
        except asyncio.TimeoutError:
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
        
        # Verify final state
        task = await client.get_task(task_id)
        logger.info(f"Final task status: {task['status']}")
        
        if task["status"] == "completed":
            logger.info(f"Task result: {task.get('result', {})}")
            logger.info("✅ Worker test PASSED!")
            
            # Clean up the test task
            await client._execute(
                "DELETE FROM absurd.tasks WHERE task_id = $1",
                task_id
            )
            logger.info(f"Cleaned up test task {task_id}")
            return 0
        else:
            logger.error(f"Task failed or timed out: {task}")
            logger.error("❌ Worker test FAILED!")
            return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
