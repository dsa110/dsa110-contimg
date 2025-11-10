#!/usr/bin/env python3
"""
Test script to verify all implementations work as intended.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_performance_metrics():
    """Test performance metrics module."""
    print("=" * 70)
    print("Testing: Performance Metrics Module")
    print("=" * 70)

    from dsa110_contimg.utils.performance import (
        track_performance,
        get_performance_stats,
        clear_performance_metrics,
        get_performance_summary,
    )
    import time

    # Test decorator
    @track_performance("test_operation")
    def test_function(x):
        time.sleep(0.01)  # Small delay
        return x * 2

    # Clear any existing metrics
    clear_performance_metrics()

    # Run function multiple times
    for i in range(5):
        result = test_function(i)
        assert result == i * 2, f"Expected {i*2}, got {result}"

    # Get stats
    stats = get_performance_stats("test_operation")
    assert "test_operation" in stats, "Stats should include test_operation"
    assert (
        stats["test_operation"]["count"] == 5
    ), f"Expected 5 calls, got {stats['test_operation']['count']}"
    assert stats["test_operation"]["mean"] > 0, "Mean time should be positive"

    # Test summary
    summary = get_performance_summary()
    assert "test_operation" in summary, "Summary should include test_operation"

    # Test clearing
    clear_performance_metrics("test_operation")
    stats_after_clear = get_performance_stats("test_operation")
    assert "test_operation" not in stats_after_clear, "Stats should be cleared"

    print("✓ Performance metrics module works correctly")
    print()


def test_error_context():
    """Test error context module."""
    print("=" * 70)
    print("Testing: Error Context Module")
    print("=" * 70)

    from dsa110_contimg.utils.error_context import (
        format_error_with_context,
        format_ms_error_with_suggestions,
        format_file_error_with_suggestions,
    )
    import tempfile

    # Test basic error formatting
    error = ValueError("Test error message")
    context = {"operation": "test_operation", "suggestion": "This is a test suggestion"}
    result = format_error_with_context(error, context)
    assert "Error: Test error message" in result, "Error message should be included"
    assert "Operation: test_operation" in result, "Operation should be included"
    assert "Suggestion:" in result, "Suggestion should be included"

    # Test MS error formatting
    ms_error = FileNotFoundError("MS not found")
    suggestions = ["Check MS path", "Verify file exists"]
    result = format_ms_error_with_suggestions(
        ms_error, "/path/to/ms", "validation", suggestions
    )
    assert "MS not found" in result, "Error message should be included"
    assert "Check MS path" in result, "First suggestion should be included"

    # Test file error formatting
    file_error = PermissionError("Permission denied")
    result = format_file_error_with_suggestions(
        file_error, "/path/to/file", "read", ["Check permissions"]
    )
    assert "Permission denied" in result, "Error message should be included"
    assert "Check permissions" in result, "Suggestion should be included"

    print("✓ Error context module works correctly")
    print()


def test_cache_stats():
    """Test cache statistics function."""
    print("=" * 70)
    print("Testing: Cache Statistics Function")
    print("=" * 70)

    from dsa110_contimg.utils.ms_helpers import (
        get_cache_stats,
        get_ms_metadata,
        validate_ms_unflagged_fraction,
        clear_ms_metadata_cache,
        clear_flag_validation_cache,
    )
    import tempfile

    # Clear caches first
    clear_ms_metadata_cache()
    clear_flag_validation_cache()

    # Get initial stats
    initial_stats = get_cache_stats()
    assert "ms_metadata" in initial_stats, "Should have ms_metadata stats"
    assert "flag_validation" in initial_stats, "Should have flag_validation stats"

    # Verify stats structure
    ms_stats = initial_stats["ms_metadata"]
    assert "hits" in ms_stats, "Should have hits"
    assert "misses" in ms_stats, "Should have misses"
    assert "maxsize" in ms_stats, "Should have maxsize"
    assert "currsize" in ms_stats, "Should have currsize"
    assert "hit_rate" in ms_stats, "Should have hit_rate"

    flag_stats = initial_stats["flag_validation"]
    assert "hits" in flag_stats, "Should have hits"
    assert "misses" in flag_stats, "Should have misses"

    # Verify maxsize matches expected values
    assert (
        ms_stats["maxsize"] == 128
    ), f"Expected maxsize=128, got {ms_stats['maxsize']}"
    assert (
        flag_stats["maxsize"] == 64
    ), f"Expected maxsize=64, got {flag_stats['maxsize']}"

    print("✓ Cache statistics function works correctly")
    print(
        f"  MS metadata cache: maxsize={ms_stats['maxsize']}, currsize={ms_stats['currsize']}"
    )
    print(
        f"  Flag validation cache: maxsize={flag_stats['maxsize']}, currsize={flag_stats['currsize']}"
    )
    print()


def test_parallel_processing():
    """Test parallel processing utilities."""
    print("=" * 70)
    print("Testing: Parallel Processing Module")
    print("=" * 70)

    from dsa110_contimg.utils.parallel import process_parallel

    def square(x):
        return x * x

    # Test basic parallel processing
    items = [1, 2, 3, 4, 5]
    results = process_parallel(items, square, max_workers=2, show_progress=False)
    assert len(results) == 5, f"Expected 5 results, got {len(results)}"
    assert results == [1, 4, 9, 16, 25], f"Expected [1,4,9,16,25], got {results}"

    # Test empty list
    results_empty = process_parallel([], square, show_progress=False)
    assert results_empty == [], "Empty list should return empty results"

    # Test single item
    results_single = process_parallel([10], square, show_progress=False)
    assert results_single == [100], "Single item should work"

    print("✓ Parallel processing module works correctly")
    print()


def test_ms_helpers_optimizations():
    """Test MS helpers optimizations."""
    print("=" * 70)
    print("Testing: MS Helpers Optimizations")
    print("=" * 70)

    from dsa110_contimg.utils.ms_helpers import (
        clear_ms_metadata_cache,
        clear_flag_validation_cache,
        get_cache_stats,
    )

    # Test that cache clearing functions exist and work
    try:
        clear_ms_metadata_cache()
        clear_flag_validation_cache()
        print("✓ Cache clearing functions work")
    except Exception as e:
        print(f"✗ Cache clearing failed: {e}")
        return False

    # Test cache stats
    try:
        stats = get_cache_stats()
        assert isinstance(stats, dict), "Stats should be a dictionary"
        assert "ms_metadata" in stats, "Should have ms_metadata"
        assert "flag_validation" in stats, "Should have flag_validation"
        print("✓ Cache stats function works")
    except Exception as e:
        print(f"✗ Cache stats failed: {e}")
        return False

    print()


def test_type_annotations():
    """Verify type annotations are present."""
    print("=" * 70)
    print("Testing: Type Annotations")
    print("=" * 70)

    import inspect
    from dsa110_contimg.utils.ms_helpers import (
        clear_ms_metadata_cache,
        clear_flag_validation_cache,
    )

    # Check return type annotations
    sig1 = inspect.signature(clear_ms_metadata_cache)
    assert (
        sig1.return_annotation != inspect.Signature.empty
    ), "clear_ms_metadata_cache should have return annotation"
    assert sig1.return_annotation == type(
        None
    ), f"Expected None, got {sig1.return_annotation}"

    sig2 = inspect.signature(clear_flag_validation_cache)
    assert (
        sig2.return_annotation != inspect.Signature.empty
    ), "clear_flag_validation_cache should have return annotation"
    assert sig2.return_annotation == type(
        None
    ), f"Expected None, got {sig2.return_annotation}"

    print("✓ Type annotations present and correct")
    print()


def test_duplicate_function_fix():
    """Verify duplicate function fix."""
    print("=" * 70)
    print("Testing: Duplicate Function Fix")
    print("=" * 70)

    import ast
    import re

    # Read the file
    file_path = Path("src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py")
    content = file_path.read_text()

    # Count occurrences of "def sort_key(" and "def sort_key_files("
    sort_key_count = len(re.findall(r"\bdef sort_key\(", content))
    sort_key_files_count = len(re.findall(r"\bdef sort_key_files\(", content))

    # Verify only one sort_key exists (the one at line 1264)
    # and one sort_key_files exists (the one we renamed)
    # The original sort_key should still exist once, and sort_key_files should exist once
    assert sort_key_count == 1, f"Expected 1 sort_key function, found {sort_key_count}"
    assert (
        sort_key_files_count == 1
    ), f"Expected 1 sort_key_files function, found {sort_key_files_count}"

    # Verify the file compiles
    try:
        compile(content, str(file_path), "exec")
        print("✓ File compiles successfully")
    except SyntaxError as e:
        print(f"✗ Syntax error: {e}")
        return False

    print("✓ Duplicate function fix verified")
    print()


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("COMPREHENSIVE IMPLEMENTATION TEST")
    print("=" * 70 + "\n")

    tests = [
        ("Performance Metrics", test_performance_metrics),
        ("Error Context", test_error_context),
        ("Cache Statistics", test_cache_stats),
        ("Parallel Processing", test_parallel_processing),
        ("MS Helpers Optimizations", test_ms_helpers_optimizations),
        ("Type Annotations", test_type_annotations),
        ("Duplicate Function Fix", test_duplicate_function_fix),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n✗ {name} TEST FAILED: {e}")
            import traceback

            traceback.print_exc()
            failed += 1
            print()

    print("=" * 70)
    print(f"TEST SUMMARY: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
