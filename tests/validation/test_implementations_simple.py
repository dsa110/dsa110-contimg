#!/usr/bin/env python3
"""
Simple test to verify implementations are syntactically correct and work as intended.
"""

import sys
import ast
import importlib.util
from pathlib import Path


def test_syntax(file_path):
    """Test that file compiles."""
    try:
        with open(file_path, "r") as f:
            code = f.read()
        compile(code, file_path, "exec")
        return True
    except SyntaxError as e:
        print(f"✗ Syntax error in {file_path}: {e}")
        return False


def test_performance_direct():
    """Test performance module directly."""
    print("Testing: Performance Metrics Module")
    file_path = Path("src/dsa110_contimg/utils/performance.py")

    if not test_syntax(file_path):
        return False

    # Import directly
    spec = importlib.util.spec_from_file_location("performance", file_path)
    perf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(perf)

    # Test decorator
    import time

    @perf.track_performance("test")
    def test_func(x):
        time.sleep(0.001)
        return x * 2

    perf.clear_performance_metrics()
    result = test_func(5)
    assert result == 10, f"Expected 10, got {result}"

    stats = perf.get_performance_stats("test")
    assert "test" in stats and stats["test"]["count"] == 1

    print("✓ Performance metrics work correctly")
    return True


def test_error_context_direct():
    """Test error context module directly."""
    print("Testing: Error Context Module")
    file_path = Path("src/dsa110_contimg/utils/error_context.py")

    if not test_syntax(file_path):
        return False

    # Import directly
    spec = importlib.util.spec_from_file_location("error_context", file_path)
    ec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ec)

    # Test without MS metadata (to avoid import issues)
    error = ValueError("Test")
    context = {"operation": "test", "suggestion": "Test suggestion"}
    result = ec.format_error_with_context(error, context, include_metadata=False)

    assert "Error: Test" in result
    assert "Operation: test" in result
    assert "Suggestion:" in result

    print("✓ Error context works correctly (without metadata)")
    return True


def test_cache_stats():
    """Test cache stats."""
    print("Testing: Cache Statistics")
    file_path = Path("src/dsa110_contimg/utils/ms_helpers.py")

    if not test_syntax(file_path):
        return False

    spec = importlib.util.spec_from_file_location("ms_helpers", file_path)
    ms = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ms)

    # Test cache stats function exists
    assert hasattr(ms, "get_cache_stats"), "get_cache_stats function should exist"
    stats = ms.get_cache_stats()
    assert "ms_metadata" in stats
    assert "flag_validation" in stats
    assert stats["ms_metadata"]["maxsize"] == 128
    assert stats["flag_validation"]["maxsize"] == 64

    print("✓ Cache statistics work correctly")
    return True


def test_parallel_direct():
    """Test parallel module directly."""
    print("Testing: Parallel Processing Module")
    file_path = Path("src/dsa110_contimg/utils/parallel.py")

    if not test_syntax(file_path):
        return False

    spec = importlib.util.spec_from_file_location("parallel", file_path)
    par = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(par)

    def square(x):
        return x * x

    # Test without progress bar (to avoid import issues)
    results = par.process_parallel(
        [1, 2, 3], square, max_workers=2, show_progress=False
    )
    assert results == [1, 4, 9], f"Expected [1,4,9], got {results}"

    print("✓ Parallel processing works correctly")
    return True


def test_type_annotations():
    """Test type annotations."""
    print("Testing: Type Annotations")
    file_path = Path("src/dsa110_contimg/utils/ms_helpers.py")

    spec = importlib.util.spec_from_file_location("ms_helpers", file_path)
    ms = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ms)

    import inspect

    sig1 = inspect.signature(ms.clear_ms_metadata_cache)
    sig2 = inspect.signature(ms.clear_flag_validation_cache)

    assert sig1.return_annotation != inspect.Signature.empty
    assert sig2.return_annotation != inspect.Signature.empty

    print("✓ Type annotations present")
    return True


def test_duplicate_function():
    """Test duplicate function fix."""
    print("Testing: Duplicate Function Fix")
    file_path = Path("src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py")

    if not test_syntax(file_path):
        return False

    content = file_path.read_text()

    # Verify sort_key_files exists and is used
    assert "def sort_key_files(" in content
    assert "key=sort_key_files" in content

    # Verify file compiles
    compile(content, str(file_path), "exec")

    print("✓ Duplicate function fix verified")
    return True


def main():
    print("=" * 70)
    print("IMPLEMENTATION VERIFICATION TEST")
    print("=" * 70 + "\n")

    tests = [
        ("Performance Metrics", test_performance_direct),
        ("Error Context", test_error_context_direct),
        ("Cache Statistics", test_cache_stats),
        ("Parallel Processing", test_parallel_direct),
        ("Type Annotations", test_type_annotations),
        ("Duplicate Function Fix", test_duplicate_function),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {name} FAILED: {e}\n")
            failed += 1

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
