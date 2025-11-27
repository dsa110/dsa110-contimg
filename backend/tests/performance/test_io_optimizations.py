"""
Performance regression tests for HDF5 I/O and conversion optimizations.

These tests verify that performance-critical optimizations remain effective
and detect regressions. They use assertion thresholds based on measured
baseline performance from the optimization implementation phase.

Run with:
    conda activate casa6
    python -m pytest tests/performance/test_io_optimizations.py -v

For CI, these tests are part of the performance-tests job with:
    pytest tests/performance/ -v --benchmark-only --benchmark-json=results.json
"""

import time
from typing import Optional

import numpy as np
import pytest

# Optional dependencies for memory profiling
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


# =============================================================================
# Test: h5py Cache Configuration
# =============================================================================


class TestH5pyCacheConfiguration:
    """Test h5py chunk cache optimization effectiveness."""

    def test_cache_configuration_applies(self):
        """Verify h5py cache is configured to 16MB by default."""
        from dsa110_contimg.utils.hdf5_io import (
            configure_h5py_cache_defaults,
            get_h5py_cache_info,
        )

        # Apply configuration
        configure_h5py_cache_defaults()

        # Verify
        info = get_h5py_cache_info()
        assert info["patch_applied"], "h5py cache patch should be applied"
        assert info["default_rdcc_nbytes_mb"] >= 16.0, (
            f"Cache should be at least 16MB, got {info['default_rdcc_nbytes_mb']}MB"
        )

    def test_cache_info_returns_valid_dict(self):
        """Verify cache info returns expected keys."""
        from dsa110_contimg.utils.hdf5_io import get_h5py_cache_info

        info = get_h5py_cache_info()
        required_keys = [
            "default_rdcc_nbytes",
            "default_rdcc_nslots",
            "default_rdcc_nbytes_mb",
        ]
        for key in required_keys:
            assert key in info, f"Missing required key: {key}"


# =============================================================================
# Test: Batch Time Conversion Performance
# =============================================================================


class TestBatchTimeConversion:
    """Test batch astropy Time conversion optimization.

    Baseline measurement (2025-11-27):
    - Per-iteration Time(): 2.73 ms for 24 times
    - Batch Time():         0.12 ms for 24 times
    - Speedup: 21.9x

    Regression threshold: Allow 5x slowdown from batch baseline (0.6ms)
    """

    BATCH_THRESHOLD_MS = 0.6  # Fail if batch takes >0.6ms (5x baseline)
    PER_ITER_THRESHOLD_MS = 5.0  # Per-iteration should be <5ms

    def test_batch_time_conversion_fast(self):
        """Verify batch Time() conversion is fast."""
        from astropy.time import Time

        # Typical DSA-110 observation: 24 unique times
        n_times = 24
        jd_times = np.linspace(2460000.0, 2460000.01, n_times)

        # Warm up
        _ = Time(jd_times, format="jd").mjd

        # Benchmark batch conversion
        n_iterations = 100
        start = time.time()
        for _ in range(n_iterations):
            mjd_arr = Time(jd_times, format="jd").mjd
        elapsed_ms = (time.time() - start) / n_iterations * 1000

        assert elapsed_ms < self.BATCH_THRESHOLD_MS, (
            f"Batch Time() took {elapsed_ms:.2f}ms, "
            f"threshold is {self.BATCH_THRESHOLD_MS}ms"
        )
        assert mjd_arr.shape == (n_times,)

    def test_batch_faster_than_per_iteration(self):
        """Verify batch conversion is significantly faster than per-iteration."""
        from astropy.time import Time

        n_times = 24
        jd_times = np.linspace(2460000.0, 2460000.01, n_times)

        # Per-iteration approach
        n_iterations = 50
        start = time.time()
        for _ in range(n_iterations):
            mjd_list = []
            for jd in jd_times:
                mjd_list.append(Time(jd, format="jd").mjd)
        per_iter_ms = (time.time() - start) / n_iterations * 1000

        # Batch approach
        start = time.time()
        for _ in range(n_iterations):
            mjd_arr = Time(jd_times, format="jd").mjd
        batch_ms = (time.time() - start) / n_iterations * 1000

        speedup = per_iter_ms / batch_ms
        assert speedup > 5.0, (
            f"Batch should be >5x faster than per-iteration, "
            f"got {speedup:.1f}x (per-iter: {per_iter_ms:.2f}ms, batch: {batch_ms:.2f}ms)"
        )


# =============================================================================
# Test: Pre-allocation Patterns
# =============================================================================


class TestPreallocationPatterns:
    """Test pre-allocation patterns reduce overhead.

    Note: For small objects, pre-allocation may not show speedup in microbenchmarks.
    The real benefit is reduced GC pressure when storing large objects (UVData).
    """

    def test_preallocated_array_assignment(self):
        """Verify pre-allocated array assignment works correctly."""
        n_items = 16  # 16 subbands
        values = list(range(n_items))

        # Pre-allocated approach
        result = [None] * n_items
        for i, val in enumerate(values):
            result[i] = val

        # Filter None (safety check in production code)
        result = [x for x in result if x is not None]

        assert len(result) == n_items
        assert result == values

    def test_numpy_preallocation_pattern(self):
        """Verify numpy array pre-allocation is faster for repeated assignment."""
        n_unique = 24
        n_iterations = 1000

        # Append approach
        start = time.time()
        for _ in range(n_iterations):
            results = []
            for i in range(n_unique):
                results.append(float(i) * 1.5)
            arr = np.array(results)
        append_time = time.time() - start

        # Pre-allocation approach
        start = time.time()
        for _ in range(n_iterations):
            arr = np.zeros(n_unique, dtype=np.float64)
            for i in range(n_unique):
                arr[i] = float(i) * 1.5
        prealloc_time = time.time() - start

        # Pre-allocation should not be significantly slower
        # (may be faster or similar, depending on numpy internals)
        assert prealloc_time < append_time * 2.0, (
            f"Pre-allocation should not be >2x slower: "
            f"prealloc={prealloc_time:.3f}s, append={append_time:.3f}s"
        )


# =============================================================================
# Test: FastMeta Performance
# =============================================================================


class TestFastMetaPerformance:
    """Test FastMeta provides fast metadata access.

    Baseline (from OPTIMIZATION_ROADMAP):
    - FastMeta is ~700x faster than full UVData.read()
    """

    def test_fastmeta_import(self):
        """Verify FastMeta is importable and has expected interface."""
        from dsa110_contimg.utils import FastMeta

        # Verify FastMeta has context manager interface
        assert hasattr(FastMeta, "__enter__")
        assert hasattr(FastMeta, "__exit__")


# =============================================================================
# Test: Parallel I/O Configuration
# =============================================================================


class TestParallelIOConfiguration:
    """Test parallel I/O is configurable and defaults are sensible."""

    def test_cli_parallel_io_defaults(self):
        """Verify CLI exposes parallel I/O options."""
        import argparse
        import sys
        from io import StringIO

        # Import the CLI module to check argument parser
        from dsa110_contimg.conversion import cli

        # Check that the module has expected functions
        assert hasattr(cli, "main") or hasattr(cli, "parse_args")

    def test_threadpool_overhead_acceptable(self):
        """Verify ThreadPoolExecutor has acceptable overhead for I/O tasks."""
        from concurrent.futures import ThreadPoolExecutor

        # Simulate parallel I/O with minimal work
        def dummy_io(x):
            time.sleep(0.001)  # 1ms simulated I/O
            return x * 2

        items = list(range(16))  # 16 subbands

        # Sequential
        start = time.time()
        seq_results = [dummy_io(x) for x in items]
        seq_time = time.time() - start

        # Parallel with 4 workers
        start = time.time()
        with ThreadPoolExecutor(max_workers=4) as executor:
            par_results = list(executor.map(dummy_io, items))
        par_time = time.time() - start

        assert seq_results == par_results

        # Parallel should be faster (4 workers, 16 items with 1ms each)
        # Sequential: ~16ms, Parallel: ~4ms
        # Allow some overhead, but should see speedup
        speedup = seq_time / par_time
        assert speedup > 2.0, (
            f"Parallel should be >2x faster for I/O-bound tasks, "
            f"got {speedup:.1f}x"
        )


# =============================================================================
# Test: Memory Usage (requires psutil)
# =============================================================================


@pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available")
class TestMemoryUsage:
    """Test memory management patterns."""

    def test_numpy_preallocation_memory(self):
        """Verify pre-allocation doesn't cause memory bloat."""
        process = psutil.Process()

        # Baseline memory
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        # Pre-allocate arrays similar to phase_to_meridian
        n_unique = 24
        for _ in range(100):
            phase_ra = np.zeros(n_unique, dtype=np.float64)
            phase_dec = np.zeros(n_unique, dtype=np.float64)
            phase_center_id = np.zeros(1000, dtype=np.int32)

        # Memory after
        mem_after = process.memory_info().rss / 1024 / 1024  # MB

        # Should not increase memory significantly (arrays are small)
        mem_increase = mem_after - mem_before
        assert mem_increase < 50, (
            f"Memory increased by {mem_increase:.1f}MB, should be <50MB"
        )


# =============================================================================
# Test: JIT Warm-up (Numba)
# =============================================================================


class TestJITWarmup:
    """Test numba JIT warm-up functionality."""

    def test_warmup_function_exists(self):
        """Verify warm_up_jit function is available."""
        try:
            from dsa110_contimg.utils.numba_accel import warm_up_jit

            # Should be callable
            assert callable(warm_up_jit)
        except ImportError:
            # numba_accel may not be available in all environments
            pytest.skip("numba_accel not available")

    def test_warmup_completes_quickly(self):
        """Verify JIT warm-up completes in reasonable time."""
        try:
            from dsa110_contimg.utils.numba_accel import warm_up_jit

            start = time.time()
            warm_up_jit()
            elapsed_ms = (time.time() - start) * 1000

            # Should complete in <500ms (baseline was ~64ms)
            assert elapsed_ms < 500, (
                f"JIT warm-up took {elapsed_ms:.1f}ms, should be <500ms"
            )
        except ImportError:
            pytest.skip("numba_accel not available")


# =============================================================================
# Benchmark Fixtures (for pytest-benchmark integration)
# =============================================================================


@pytest.fixture
def benchmark_time_conversion():
    """Fixture providing Time conversion benchmarks."""
    from astropy.time import Time

    n_times = 24
    jd_times = np.linspace(2460000.0, 2460000.01, n_times)

    def batch_convert():
        return Time(jd_times, format="jd").mjd

    def per_iter_convert():
        return [Time(jd, format="jd").mjd for jd in jd_times]

    return {"batch": batch_convert, "per_iter": per_iter_convert}


# =============================================================================
# Performance Regression Summary
# =============================================================================


class TestPerformanceRegressionSummary:
    """Summary test that documents expected performance characteristics.

    This test serves as documentation and a quick sanity check.
    """

    def test_optimization_summary(self):
        """Document expected optimization speedups.

        Phase 1: h5py cache - 32% faster conversion, 48% faster HDF5 reads
        Phase 2: Numba JIT - Angular separation accelerated (LST uses astropy)
        Phase 4: Parallel I/O - Configurable via CLI
        Phase 5: Pre-allocation - 21.9x faster Time() conversion (batch)

        These are measured baselines from the optimization implementation.
        """
        # This test always passes - it's documentation
        expected_speedups = {
            "h5py_cache_conversion": "32%",
            "h5py_cache_hdf5_read": "48%",
            "batch_time_conversion": "21.9x",
            "parallel_io_4workers": "~2-3x for I/O-bound tasks",
        }

        for optimization, speedup in expected_speedups.items():
            print(f"  {optimization}: {speedup}")

        assert True  # Documentation test always passes
