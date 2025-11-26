#!/usr/bin/env python
"""Submit a test task to Absurd queue.

This script demonstrates how to submit tasks to the Absurd workflow manager
using the REST API.

Usage:
    python scripts/absurd/submit_test_task.py
"""

import json
import sys
from pathlib import Path

import requests

# Configuration
API_URL = "http://localhost:8000/api/absurd"


def submit_task(task_name: str, params: dict, priority: int = 10):
    """Submit a task via the API."""
    print(f"\n📤 Submitting task: {task_name}")
    print(f"   Priority: {priority}")

    response = requests.post(
        f"{API_URL}/tasks", json={"task_name": task_name, "params": params, "priority": priority}
    )

    if response.status_code == 200:
        task = response.json()
        print(f"✅ Task submitted successfully!")
        print(f"   Task ID: {task['task_id']}")
        print(f"   Status: {task['status']}")
        return task["task_id"]
    else:
        print(f"❌ Failed to submit task: {response.status_code}")
        print(f"   Error: {response.text}")
        return None


def check_task(task_id: str):
    """Check task status via the API."""
    print(f"\n🔍 Checking task status: {task_id}")

    response = requests.get(f"{API_URL}/tasks/{task_id}")

    if response.status_code == 200:
        task = response.json()
        print(f"   Status: {task['status']}")
        if task.get("result"):
            print(f"   Result: {json.dumps(task['result'], indent=2)[:200]}...")
        return task
    else:
        print(f"❌ Failed to get task: {response.status_code}")
        return None


def list_tasks(limit: int = 5):
    """List recent tasks."""
    print(f"\n📋 Listing recent tasks (limit={limit})...")

    response = requests.get(f"{API_URL}/tasks?limit={limit}")

    if response.status_code == 200:
        tasks = response.json()
        print(f"   Found {len(tasks)} tasks:")
        for task in tasks:
            print(f"   - {task['task_id'][:8]}... | {task['task_name']:20} | {task['status']}")
        return tasks
    else:
        print(f"❌ Failed to list tasks: {response.status_code}")
        return None


def get_queue_stats(queue_name: str = "dsa110-pipeline"):
    """Get queue statistics."""
    print(f"\n📊 Queue statistics for: {queue_name}")

    response = requests.get(f"{API_URL}/queues/{queue_name}/stats")

    if response.status_code == 200:
        stats = response.json()
        print(f"   Pending: {stats.get('pending', 0)}")
        print(f"   Running: {stats.get('running', 0)}")
        print(f"   Completed: {stats.get('completed', 0)}")
        print(f"   Failed: {stats.get('failed', 0)}")
        return stats
    else:
        print(f"❌ Failed to get queue stats: {response.status_code}")
        return None


def main():
    """Main function - submit a test task and check its status."""
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║          Absurd Test Task Submission                          ║")
    print("╚════════════════════════════════════════════════════════════════╝")

    # Check API is reachable
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code != 200:
            print(f"\n❌ API not reachable at {API_URL}")
            print("   Make sure the FastAPI server is running:")
            print("   uvicorn src.dsa110_contimg.api.routes:app --port 8000")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to API at {API_URL}")
        print("   Make sure the FastAPI server is running:")
        print("   uvicorn src.dsa110_contimg.api.routes:app --port 8000")
        sys.exit(1)

    print("\n✅ API server is reachable")

    # Get current queue stats
    get_queue_stats()

    # Example 1: Submit a simple test task (catalog setup)
    print("\n" + "=" * 70)
    print("Example 1: Catalog Setup Task")
    print("=" * 70)

    task_id = submit_task(
        "catalog-setup",
        {
            "config": {
                "paths": {
                    "incoming": "/data/incoming",
                    "staging": "/stage/dsa110-contimg",
                    "products": "/data/dsa110-contimg/products",
                }
            },
            "inputs": {"input_path": "/data/incoming/test_observation.hdf5"},
        },
        priority=10,
    )

    if task_id:
        # Wait a moment and check status
        import time

        time.sleep(2)
        check_task(task_id)

    # Example 2: List all recent tasks
    print("\n" + "=" * 70)
    print("Example 2: Recent Tasks")
    print("=" * 70)
    list_tasks(limit=10)

    # Final queue stats
    print("\n" + "=" * 70)
    print("Final Queue Statistics")
    print("=" * 70)
    get_queue_stats()

    print("\n" + "╔════════════════════════════════════════════════════════════════╗")
    print("║                    ✅ Test Complete                            ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print("\nNext steps:")
    print("  - Check worker logs to see task execution")
    print("  - Monitor queue statistics")
    print("  - Submit more tasks via API or Python client")
    print("")
    print("For full pipeline example, see:")
    print("  docs/how-to/operating_absurd_pipeline.md")
    print("")


if __name__ == "__main__":
    main()
