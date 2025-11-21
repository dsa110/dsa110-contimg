"""
Performance testing for synthetic data generation.

Tests generation performance with realistic data volumes, memory usage,
and scaling characteristics.
"""

import time

import numpy as np
import pytest

# Skip performance tests if psutil not available
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from dsa110_contimg.simulation.visibility_models import (
    add_calibration_errors,
    add_thermal_noise,
    calculate_thermal_noise_rms,
    gaussian_source_visibility,
)


@pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available")
class TestGenerationPerformance:
    """Test generation performance with realistic data volumes."""

    def test_large_visibility_array(self):
        """Test visibility generation with large arrays."""
        # Simulate large dataset: 1000 baselines, 100 integrations, 64 channels
        nbls = 1000
        ntimes = 100
        nblts = nbls * ntimes

        u_lambda = np.random.randn(nblts) * 1000.0
        v_lambda = np.random.randn(nblts) * 1000.0
        flux = 1.0

        start_time = time.time()
        vis = gaussian_source_visibility(u_lambda, v_lambda, flux, 10.0, 10.0, 0.0)
        elapsed = time.time() - start_time

        # Should complete in reasonable time (< 1 second for this size)
        assert elapsed < 1.0
        assert vis.shape == (nblts,)
        assert np.all(np.isfinite(vis))

    def test_memory_usage_large_array(self):
        """Profile memory usage for large arrays."""
        process = psutil.Process()
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        # Create large visibility array
        nblts = 10000
        nspws = 1
        nfreqs = 64
        npols = 2

        vis = np.ones((nblts, nspws, nfreqs, npols), dtype=complex)

        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_used = mem_after - mem_before

        # Should use reasonable memory (< 100 MB for this array)
        # Complex float64: 8 bytes * 2 (real+imag) = 16 bytes per element
        expected_mb = (nblts * nspws * nfreqs * npols * 16) / 1024 / 1024
        assert mem_used < expected_mb * 2  # Allow some overhead

        del vis

    def test_noise_generation_scaling(self):
        """Test how noise generation time scales with data volume."""
        sizes = [
            (100, 1, 64, 2),
            (1000, 1, 64, 2),
            (10000, 1, 64, 2),
        ]

        times = []
        for size in sizes:
            nblts, nspws, nfreqs, npols = size
            vis = np.ones((nblts, nspws, nfreqs, npols), dtype=complex)

            start_time = time.time()
            vis_noisy = add_thermal_noise(
                vis,
                integration_time_sec=10.0,
                channel_width_hz=1e6,
                system_temperature_k=50.0,
                frequency_hz=1.4e9,
                rng=np.random.default_rng(42),
            )
            elapsed = time.time() - start_time
            times.append(elapsed)

            assert np.all(np.isfinite(vis_noisy))

        # Time should scale roughly linearly with array size
        # (may have some overhead, so allow 2x)
        ratio_1 = times[1] / times[0] if times[0] > 0 else 1.0
        ratio_2 = times[2] / times[1] if times[1] > 0 else 1.0

        # Should scale roughly with size ratio (10x size = ~10x time)
        # Allow 2x overhead
        assert ratio_1 < 20.0  # 10x size, allow 2x overhead
        assert ratio_2 < 20.0

    def test_calibration_errors_scaling(self):
        """Test calibration error application scaling."""
        sizes = [
            (100, 1, 64, 2, 10),
            (1000, 1, 64, 2, 10),
            (10000, 1, 64, 2, 10),
        ]

        times = []
        for size in sizes:
            nblts, nspws, nfreqs, npols, nants = size
            vis = np.ones((nblts, nspws, nfreqs, npols), dtype=complex)

            start_time = time.time()
            vis_cal, gains, phases = add_calibration_errors(
                vis, nants, rng=np.random.default_rng(42)
            )
            elapsed = time.time() - start_time
            times.append(elapsed)

            assert np.all(np.isfinite(vis_cal))

        # Should scale roughly linearly
        if len(times) > 1 and times[0] > 0:
            ratio = times[1] / times[0]
            assert ratio < 20.0  # Allow overhead


class TestPerformanceBenchmarks:
    """Benchmark performance characteristics."""

    def test_visibility_generation_benchmark(self):
        """Benchmark visibility generation speed."""
        nblts = 1000
        u_lambda = np.random.randn(nblts) * 100.0
        v_lambda = np.random.randn(nblts) * 100.0

        # Point source
        start = time.time()
        vis_point = gaussian_source_visibility(u_lambda, v_lambda, 1.0, 0.0, 0.0, 0.0)
        time_point = time.time() - start

        # Gaussian source
        start = time.time()
        vis_gauss = gaussian_source_visibility(u_lambda, v_lambda, 1.0, 10.0, 10.0, 0.0)
        time_gauss = time.time() - start

        # Disk source
        from dsa110_contimg.simulation.visibility_models import (
            disk_source_visibility,
        )

        start = time.time()
        vis_disk = disk_source_visibility(u_lambda, v_lambda, 1.0, 5.0)
        time_disk = time.time() - start

        # All should complete quickly (disk is slower due to Bessel function)
        assert time_point < 0.1
        assert time_gauss < 0.1
        assert time_disk < 0.5  # Disk source uses Bessel function, slower

        # Results should be valid
        assert np.all(np.isfinite(vis_point))
        assert np.all(np.isfinite(vis_gauss))
        assert np.all(np.isfinite(vis_disk))

    def test_noise_calculation_benchmark(self):
        """Benchmark noise calculation speed."""
        # Single calculation
        start = time.time()
        rms = calculate_thermal_noise_rms(
            integration_time_sec=10.0,
            channel_width_hz=1e6,
            system_temperature_k=50.0,
            frequency_hz=1.4e9,
        )
        time_single = time.time() - start

        # Many calculations
        start = time.time()
        for _ in range(1000):
            rms = calculate_thermal_noise_rms(
                integration_time_sec=10.0,
                channel_width_hz=1e6,
                system_temperature_k=50.0,
                frequency_hz=1.4e9,
            )
        time_many = time.time() - start

        # Should be very fast
        assert time_single < 0.001
        assert time_many < 0.1  # 1000 calculations in < 100ms
        assert np.isfinite(rms)


@pytest.mark.slow
class TestLargeDatasetPerformance:
    """Performance tests for very large datasets (marked as slow)."""

    def test_very_large_visibility_generation(self):
        """Test with very large visibility arrays."""
        # Simulate very large dataset
        nblts = 100000
        u_lambda = np.random.randn(nblts) * 1000.0
        v_lambda = np.random.randn(nblts) * 1000.0

        start_time = time.time()
        vis = gaussian_source_visibility(u_lambda, v_lambda, 1.0, 10.0, 10.0, 0.0)
        elapsed = time.time() - start_time

        # Should complete in reasonable time (< 5 seconds)
        assert elapsed < 5.0
        assert vis.shape == (nblts,)
        assert np.all(np.isfinite(vis))
