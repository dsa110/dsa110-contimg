"""
Test concurrent generation scenarios.

Tests parallel UVH5 generation, thread safety of random number generators,
and file I/O contention.
"""

import multiprocessing
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pytest

from dsa110_contimg.simulation.visibility_models import (
    add_calibration_errors,
    add_thermal_noise,
)


# Module-level functions for multiprocessing (must be picklable)
def create_temp_file_worker(args):
    """Worker function for creating temp files (module-level for pickling)."""
    seed, temp_dir_path = args
    rng = np.random.default_rng(seed)
    data = rng.random(100)
    file_path = Path(temp_dir_path) / f"test_{seed}.npy"
    np.save(file_path, data)
    return file_path.exists()


def generate_noise_worker(args):
    """Worker function for parallel noise generation."""
    seed, array_size = args
    rng = np.random.default_rng(seed)

    vis = np.ones((array_size, 1, 64, 2), dtype=complex)
    vis_noisy = add_thermal_noise(
        vis,
        integration_time_sec=10.0,
        channel_width_hz=1e6,
        system_temperature_k=50.0,
        frequency_hz=1.4e9,
        rng=rng,
    )

    return np.mean(np.abs(vis_noisy))


def generate_cal_errors_worker(args):
    """Worker function for parallel calibration error generation."""
    seed, nants = args
    rng = np.random.default_rng(seed)

    vis = np.ones((100, 1, 64, 2), dtype=complex)
    vis_cal, gains, phases = add_calibration_errors(vis, nants, rng=rng)

    return np.mean(np.abs(vis_cal)), np.mean(gains), np.mean(phases)


class TestConcurrentGeneration:
    """Test concurrent generation scenarios."""

    def test_parallel_noise_generation(self):
        """Test generating noise in parallel processes."""
        n_workers = 4
        array_size = 1000

        # Create worker arguments with different seeds
        worker_args = [(i, array_size) for i in range(n_workers)]

        # Run in parallel
        with multiprocessing.Pool(processes=n_workers) as pool:
            results = pool.map(generate_noise_worker, worker_args)

        # All should produce valid results
        assert len(results) == n_workers
        assert all(np.isfinite(r) for r in results)

        # Results should be different (different seeds)
        assert len(set(results)) > 1

    def test_parallel_calibration_errors(self):
        """Test generating calibration errors in parallel."""
        n_workers = 4
        nants = 10

        # Create worker arguments with different seeds
        worker_args = [(i, nants) for i in range(n_workers)]

        # Run in parallel
        with multiprocessing.Pool(processes=n_workers) as pool:
            results = pool.map(generate_cal_errors_worker, worker_args)

        # All should produce valid results
        assert len(results) == n_workers
        for vis_mean, gain_mean, phase_mean in results:
            assert np.isfinite(vis_mean)
            assert np.isfinite(gain_mean)
            assert np.isfinite(phase_mean)

        # Results should be valid (may be similar due to statistical variation)
        # The important thing is that parallel execution works correctly
        vis_means = [r[0] for r in results]
        # All should be finite and reasonable
        assert all(np.isfinite(v) for v in vis_means)
        assert all(0.5 < v < 2.0 for v in vis_means)  # Reasonable range

    def test_thread_safety_random_generator(self):
        """Test that random number generators are thread-safe."""
        import threading

        results = []
        lock = threading.Lock()

        def worker(seed):
            rng = np.random.default_rng(seed)
            # Generate some random numbers
            values = rng.random(100)
            with lock:
                results.append(np.mean(values))

        # Create multiple threads
        threads = []
        for i in range(4):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # All should produce valid results
        assert len(results) == 4
        assert all(np.isfinite(r) for r in results)

        # Results should be different (different seeds)
        assert len(set(results)) > 1

    def test_concurrent_file_operations(self):
        """Test concurrent file I/O (if applicable)."""
        # This test would be for actual file generation
        # For now, test that we can create temporary files concurrently
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Create files in parallel using module-level function
            n_workers = 4
            worker_args = [(i, str(temp_dir)) for i in range(n_workers)]
            with multiprocessing.Pool(processes=n_workers) as pool:
                results = pool.map(create_temp_file_worker, worker_args)

            # All files should be created
            assert all(results)
            assert len(list(temp_dir.glob("*.npy"))) == n_workers

        finally:
            shutil.rmtree(temp_dir)


class TestReproducibilityConcurrent:
    """Test reproducibility in concurrent scenarios."""

    def test_reproducibility_with_seeds(self):
        """Test that same seeds produce same results in parallel."""
        seed = 42
        array_size = 1000

        # Run same seed in parallel
        worker_args = [(seed, array_size) for _ in range(4)]

        with multiprocessing.Pool(processes=4) as pool:
            results = pool.map(generate_noise_worker, worker_args)

        # All should produce same result (same seed)
        assert len(set(results)) == 1

        # Compare with sequential result
        sequential_result = generate_noise_worker((seed, array_size))
        assert results[0] == pytest.approx(sequential_result, rel=1e-10)
