#!/usr/bin/env python3
"""
Test script to verify all implementations work as intended (direct imports).
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_performance_metrics():
    """Test performance metrics module."""
    print("=" * 70)
    print("Testing: Performance Metrics Module")
    print("=" * 70)

    # Import directly to avoid __init__.py issues
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "performance", Path("src/dsa110_contimg/utils/performance.py")
    )
    performance = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(performance)

    import time

    # Test decorator
    @performance.track_performance("test_operation")
    def test_function(x):
        time.sleep(0.01)
        return x * 2

    # Clear any existing metrics
    performance.clear_performance_metrics()

    # Run function multiple times
    for i in range(5):
        result = test_function(i)
        assert result == i * 2, f"Expected {i * 2}, got {result}"

    # Get stats
    stats = performance.get_performance_stats("test_operation")
    assert "test_operation" in stats, "Stats should include test_operation"
    assert (
        stats["test_operation"]["count"] == 5
    ), f"Expected 5 calls, got {stats['test_operation']['count']}"
    assert stats["test_operation"]["mean"] > 0, "Mean time should be positive"

    # Test summary
    summary = performance.get_performance_summary()
    assert "test_operation" in summary, "Summary should include test_operation"

    print(":check_mark: Performance metrics module works correctly")
    print()


def test_error_context():
    """Test error context module."""
    print("=" * 70)
    print("Testing: Error Context Module")
    print("=" * 70)

    # Import directly
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "error_context", Path("src/dsa110_contimg/utils/error_context.py")
    )
    error_context = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(error_context)

    # Test basic error formatting
    error = ValueError("Test error message")
    context = {"operation": "test_operation", "suggestion": "This is a test suggestion"}
    result = error_context.format_error_with_context(error, context)
    assert "Error: Test error message" in result, "Error message should be included"
    assert "Operation: test_operation" in result, "Operation should be included"
    assert "Suggestion:" in result, "Suggestion should be included"

    # Test MS error formatting
    ms_error = FileNotFoundError("MS not found")
    suggestions = ["Check MS path", "Verify file exists"]
    result = error_context.format_ms_error_with_suggestions(
        ms_error, "/path/to/ms", "validation", suggestions
    )
    assert "MS not found" in result, "Error message should be included"
    assert "Check MS path" in result, "First suggestion should be included"

    print(":check_mark: Error context module works correctly")
    print()


def test_cache_stats():
    """Test cache statistics function."""
    print("=" * 70)
    print("Testing: Cache Statistics Function")
    print("=" * 70)

    # Import directly
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "ms_helpers", Path("src/dsa110_contimg/utils/ms_helpers.py")
    )
    ms_helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ms_helpers)

    # Clear caches first
    ms_helpers.clear_ms_metadata_cache()
    ms_helpers.clear_flag_validation_cache()

    # Get initial stats
    initial_stats = ms_helpers.get_cache_stats()
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
    assert ms_stats["maxsize"] == 128, f"Expected maxsize=128, got {ms_stats['maxsize']}"
    assert flag_stats["maxsize"] == 64, f"Expected maxsize=64, got {flag_stats['maxsize']}"

    print(":check_mark: Cache statistics function works correctly")
    print(f"  MS metadata cache: maxsize={ms_stats['maxsize']}, currsize={ms_stats['currsize']}")
    print(
        f"  Flag validation cache: maxsize={flag_stats['maxsize']}, currsize={flag_stats['currsize']}"
    )
    print()


def test_parallel_processing():
    """Test parallel processing utilities."""
    print("=" * 70)
    print("Testing: Parallel Processing Module")
    print("=" * 70)

    # Import directly
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "parallel", Path("src/dsa110_contimg/utils/parallel.py")
    )
    parallel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parallel)

    def square(x):
        return x * x

    # Test basic parallel processing
    items = [1, 2, 3, 4, 5]
    results = parallel.process_parallel(items, square, max_workers=2, show_progress=False)
    assert len(results) == 5, f"Expected 5 results, got {len(results)}"
    assert results == [1, 4, 9, 16, 25], f"Expected [1,4,9,16,25], got {results}"

    # Test empty list
    results_empty = parallel.process_parallel([], square, show_progress=False)
    assert results_empty == [], "Empty list should return empty results"

    print(":check_mark: Parallel processing module works correctly")
    print()


def test_type_annotations():
    """Verify type annotations are present."""
    print("=" * 70)
    print("Testing: Type Annotations")
    print("=" * 70)

    import importlib.util
    import inspect

    spec = importlib.util.spec_from_file_location(
        "ms_helpers", Path("src/dsa110_contimg/utils/ms_helpers.py")
    )
    ms_helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ms_helpers)

    # Check return type annotations
    sig1 = inspect.signature(ms_helpers.clear_ms_metadata_cache)
    assert (
        sig1.return_annotation != inspect.Signature.empty
    ), "clear_ms_metadata_cache should have return annotation"
    # None type annotation can be None or NoneType
    assert sig1.return_annotation in (
        type(None),
        None,
    ), f"Expected None type, got {sig1.return_annotation}"

    sig2 = inspect.signature(ms_helpers.clear_flag_validation_cache)
    assert (
        sig2.return_annotation != inspect.Signature.empty
    ), "clear_flag_validation_cache should have return annotation"
    assert sig2.return_annotation in (
        type(None),
        None,
    ), f"Expected None type, got {sig2.return_annotation}"

    print(":check_mark: Type annotations present and correct")
    print()


def test_duplicate_function_fix():
    """Verify duplicate function fix."""
    print("=" * 70)
    print("Testing: Duplicate Function Fix")
    print("=" * 70)

    import re

    # Read the file
    file_path = Path("src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py")
    content = file_path.read_text()

    # Count occurrences of "def sort_key(" and "def sort_key_files("
    len(re.findall(r"\bdef sort_key\(", content))
    sort_key_files_count = len(re.findall(r"\bdef sort_key_files\(", content))

    # There should be one sort_key (the original) and one sort_key_files (the renamed one)
    # Actually, let me check the actual usage
    lines = content.split("\n")
    sort_key_lines = [i + 1 for i, line in enumerate(lines) if re.search(r"\bdef sort_key\(", line)]
    sort_key_files_lines = [
        i + 1 for i, line in enumerate(lines) if re.search(r"\bdef sort_key_files\(", line)
    ]

    print(f"  Found sort_key at lines: {sort_key_lines}")
    print(f"  Found sort_key_files at lines: {sort_key_files_lines}")

    # Verify sort_key_files is used where it should be
    assert (
        sort_key_files_count == 1
    ), f"Expected 1 sort_key_files function, found {sort_key_files_count}"

    # Verify the file compiles
    try:
        compile(content, str(file_path), "exec")
        print(":check_mark: File compiles successfully")
    except SyntaxError as e:
        print(f":ballot_x: Syntax error: {e}")
        return False

    # Verify sort_key_files is used in the sorted() call
    assert "key=sort_key_files" in content, "sorted() should use sort_key_files"

    print(":check_mark: Duplicate function fix verified")
    print()


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("COMPREHENSIVE IMPLEMENTATION TEST (Direct Imports)")
    print("=" * 70 + "\n")

    tests = [
        ("Performance Metrics", test_performance_metrics),
        ("Error Context", test_error_context),
        ("Cache Statistics", test_cache_stats),
        ("Parallel Processing", test_parallel_processing),
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
            print(f"\n:ballot_x: {name} TEST FAILED: {e}")
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
