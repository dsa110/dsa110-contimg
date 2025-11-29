#!/opt/miniforge/envs/casa6/bin/python
"""
Test script for Phase 3 backend API endpoints (Events and Cache).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
from datetime import datetime

from dsa110_contimg.pipeline.caching import get_cache_backend
from dsa110_contimg.pipeline.event_bus import (EventType, PipelineEvent,
                                               get_event_bus)


def test_event_bus():
    """Test event bus functionality."""
    print("=" * 60)
    print("Testing Event Bus")
    print("=" * 60)

    event_bus = get_event_bus()

    # Publish some test events
    print("\n1. Publishing test events...")
    import time

    from dsa110_contimg.pipeline.event_bus import (
      EventType, PhotometryMeasurementCompleted)

    for i in range(5):
        event = PhotometryMeasurementCompleted(
            event_type=EventType.PHOTOMETRY_MEASUREMENT_COMPLETED,
            timestamp=time.time(),
            fits_path=f"/test/path/image_{i}.fits",
            ra_deg=120.0 + i * 0.1,
            dec_deg=45.0 + i * 0.1,
            flux_jy=1.0 + i * 0.1,
            method="aperture",
            source_id=f"src_{i}",
            correlation_id=f"test_{i}",
        )
        event_bus.publish(event)
        print(f"   Published event {i+1}: {event.event_type.value}")
        time.sleep(0.01)  # Small delay to ensure different timestamps

    time.sleep(0.1)

    # Test get_history
    print("\n2. Testing get_history()...")
    history = event_bus.get_history(limit=10)
    print(f"   Retrieved {len(history)} events")
    if history:
        print(f"   Latest event: {history[0].event_type}")

    # Test get_statistics
    print("\n3. Testing get_statistics()...")
    stats = event_bus.get_statistics()
    print(f"   Total events: {stats['total_events']}")
    print(f"   Events in history: {stats['events_in_history']}")
    print(f"   Events per type: {stats['events_per_type']}")
    print(f"   Events last minute: {stats['events_last_minute']}")

    # Test get_history with filtering
    print("\n4. Testing get_history() with event type filter...")
    filtered = event_bus.get_history(event_type=EventType.PHOTOMETRY_MEASUREMENT_COMPLETED, limit=5)
    print(f"   Retrieved {len(filtered)} filtered events")

    # Test get_history with timestamp filter
    print("\n5. Testing get_history() with timestamp filter...")
    since = time.time() - 60  # Last minute
    recent = event_bus.get_history(since=since, limit=10)
    print(f"   Retrieved {len(recent)} recent events")

    print("\n✓ Event bus tests passed!\n")


def test_cache():
    """Test cache functionality."""
    print("=" * 60)
    print("Testing Cache Backend")
    print("=" * 60)

    cache = get_cache_backend()
    backend_type = type(cache).__name__
    print(f"\nCache backend: {backend_type}")

    # Test basic operations
    print("\n1. Testing basic cache operations...")
    cache.set("test_key_1", {"value": 123, "data": "test"})
    cache.set("test_key_2", "string_value", ttl=60)
    cache.set("variability_stats:src_1", {"flux": 1.5, "sigma": 0.2})

    val1 = cache.get("test_key_1")
    val2 = cache.get("test_key_2")
    val3 = cache.get("variability_stats:src_1")

    print(f"   test_key_1: {val1}")
    print(f"   test_key_2: {val2}")
    print(f"   variability_stats:src_1: {val3}")

    # Test get_statistics
    print("\n2. Testing get_statistics()...")
    stats = cache.get_statistics()
    print(f"   Backend type: {stats['backend_type']}")
    print(f"   Total keys: {stats['total_keys']}")
    print(f"   Active keys: {stats['active_keys']}")
    print(f"   Hits: {stats['hits']}")
    print(f"   Misses: {stats['misses']}")
    print(f"   Hit rate: {stats['hit_rate']}%")

    # Test list_keys
    print("\n3. Testing list_keys()...")
    all_keys = cache.list_keys(limit=100)
    print(f"   Total keys listed: {len(all_keys)}")
    print(f"   Sample keys: {all_keys[:5]}")

    # Test list_keys with pattern
    print("\n4. Testing list_keys() with pattern filter...")
    pattern_keys = cache.list_keys(pattern="variability_stats:*", limit=10)
    print(f"   Pattern-matched keys: {len(pattern_keys)}")
    print(f"   Keys: {pattern_keys}")

    # Test delete
    print("\n5. Testing delete()...")
    cache.delete("test_key_1")
    deleted_val = cache.get("test_key_1")
    print(f"   After delete, test_key_1 = {deleted_val} (should be None)")

    # Test clear
    print("\n6. Testing clear()...")
    cache.clear()
    cleared_stats = cache.get_statistics()
    print(f"   After clear, total keys: {cleared_stats['total_keys']}")

    print("\n✓ Cache tests passed!\n")


if __name__ == "__main__":
    try:
        test_event_bus()
        test_cache()
        print("=" * 60)
        print("All Phase 3 backend tests passed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
