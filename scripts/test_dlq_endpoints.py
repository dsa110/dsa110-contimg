#!/usr/bin/env python3
"""
Test script for Dead Letter Queue endpoints.
Creates test DLQ items and verifies API endpoints.
"""

import sys
import json
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Import directly to avoid __init__.py import issues
try:
    from dsa110_contimg.pipeline.dead_letter_queue import get_dlq
except ImportError as e:
    # Fallback: import module directly
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "dead_letter_queue",
        project_root / "src" / "dsa110_contimg" / "pipeline" / "dead_letter_queue.py"
    )
    dlq_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dlq_module)
    get_dlq = dlq_module.get_dlq


def create_test_dlq_items():
    """Create test DLQ items for testing."""
    dlq = get_dlq()

    test_items = [
        {
            "component": "ese_detection",
            "operation": "detect_candidates",
            "error": RuntimeError("Test error: ESE detection failed"),
            "context": {
                "min_sigma": 5.0,
                "source_id": "test_source_001",
                "image_id": "test_image_001",
            }
        },
        {
            "component": "calibration_solve",
            "operation": "solve_gain",
            "error": ValueError("Test error: Calibration solve failed"),
            "context": {
                "ms_path": "/test/path/to/ms",
                "cal_type": "K",
            }
        },
        {
            "component": "photometry",
            "operation": "measure_flux",
            "error": KeyError("Test error: Source not found"),
            "context": {
                "source_id": "test_source_002",
                "image_id": "test_image_002",
            }
        },
    ]

    created_items = []
    for item_data in test_items:
        try:
            item_id = dlq.add(
                component=item_data["component"],
                operation=item_data["operation"],
                error=item_data["error"],
                context=item_data["context"]
            )
            created_items.append({
                "id": item_id,
                "component": item_data["component"],
                "operation": item_data["operation"],
            })
            print(
                f"Created DLQ item {item_id}: {item_data['component']}.{item_data['operation']}")
        except Exception as e:
            print(f"Failed to create DLQ item: {e}")

    return created_items


def get_dlq_stats():
    """Get DLQ statistics."""
    dlq = get_dlq()
    stats = dlq.get_stats()
    return stats


def main():
    """Main test function."""
    print("=" * 60)
    print("DLQ Test Data Creation Script")
    print("=" * 60)

    # Get initial stats
    print("\nInitial DLQ Stats:")
    initial_stats = get_dlq_stats()
    print(json.dumps(initial_stats, indent=2))

    # Create test items
    print("\nCreating test DLQ items...")
    created_items = create_test_dlq_items()

    # Wait a moment for database writes
    time.sleep(0.5)

    # Get final stats
    print("\nFinal DLQ Stats:")
    final_stats = get_dlq_stats()
    print(json.dumps(final_stats, indent=2))

    # Print created items
    print("\nCreated Items:")
    print(json.dumps(created_items, indent=2))

    print("\n" + "=" * 60)
    print("Test data creation complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Test API endpoints using curl commands")
    print("2. Verify items appear in frontend")
    print("3. Test retry/resolve actions")


if __name__ == "__main__":
    main()
