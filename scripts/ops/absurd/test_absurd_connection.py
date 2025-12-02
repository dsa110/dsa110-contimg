#!/opt/miniforge/envs/casa6/bin/python
"""
Test script for Absurd database connection.

Verifies that the Absurd client can connect and perform basic operations.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend/src to path
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig


async def main():
    """Test Absurd connection and basic operations."""
    print("=== Absurd Connection Test ===\n")

    # Load configuration
    config = AbsurdConfig.from_env()
    print(f"Configuration:")
    print(f"  Enabled: {config.enabled}")
    print(f"  Database URL: {config.database_url}")
    print(f"  Queue Name: {config.queue_name}")
    print()

    # Create client
    client = AbsurdClient(config.database_url)

    try:
        # Connect
        print("Connecting to Absurd database...")
        await client.connect()
        print(":check: Connected\n")

        # Spawn a test task
        print("Spawning test task...")
        task_id = await client.spawn_task(
            queue_name=config.queue_name,
            task_name="test-connection",
            params={"message": "Hello from Absurd!", "timestamp": "now"},
            priority=0,
        )
        print(f":check: Task spawned: {task_id}\n")

        # Get task details
        print("Fetching task details...")
        task = await client.get_task(task_id)
        if task:
            print(f":check: Task retrieved:")
            print(f"  ID: {task['task_id']}")
            print(f"  Name: {task['task_name']}")
            print(f"  Status: {task['status']}")
            print(f"  Params: {task['params']}")
            print()
        else:
            print(":cross: Task not found\n")

        # List tasks
        print("Listing recent tasks...")
        tasks = await client.list_tasks(queue_name=config.queue_name, limit=5)
        print(f":check: Found {len(tasks)} tasks")
        for task in tasks:
            print(
                f"  - {task['task_name']} " f"[{task['status']}] " f"(ID: {task['task_id'][:8]}...)"
            )
        print()

        # Get queue stats
        print("Getting queue statistics...")
        stats = await client.get_queue_stats(config.queue_name)
        print(f":check: Queue stats:")
        for status, count in stats.items():
            print(f"  {status}: {count}")
        print()

        print("=== All Tests Passed ===")
        return 0

    except Exception as e:
        print(f"\n:cross: Error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        await client.close()
        print("\nDisconnected from database")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
