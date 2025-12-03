"""
Unit tests for GPU calibration module.

Tests the GPU-accelerated gain application and solving functionality.
"""

import numpy as np
import pytest

from dsa110_contimg.calibration.gpu_calibration import (
    CalibrationConfig,
    GainSolutionResult,
    ApplyCalResult,
    apply_gains_cpu,
    apply_gains,
    solve_per_antenna_gains_cpu,
    solve_per_antenna_gains,
    estimate_applycal_memory_gb,
    estimate_solve_memory_gb,
    CUPY_AVAILABLE,
)


class TestCalibrationConfig:
    """Test CalibrationConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CalibrationConfig()
        assert config.gpu_id == 0
        assert config.chunk_size == 5_000_000
        assert config.n_antennas == 110
        assert config.n_channels == 1024
        assert config.n_polarizations == 4
        assert config.interpolation == "nearest"

    def test_custom_config(self):
        """Test custom configuration."""
        config = CalibrationConfig(
            gpu_id=1,
            n_antennas=64,
            n_channels=512,
        )
        assert config.gpu_id == 1
        assert config.n_antennas == 64
        assert config.n_channels == 512


class TestGainSolutionResult:
    """Test GainSolutionResult dataclass."""

    def test_success_property_true(self):
        """Test success property when gains are provided."""
        result = GainSolutionResult(
            gains=np.ones((10, 1, 1), dtype=np.complex128),
            converged=True,
        )
        assert result.success is True

    def test_success_property_false_no_gains(self):
        """Test success property when gains are None."""
        result = GainSolutionResult(gains=None)
        assert result.success is False

    def test_success_property_false_error(self):
        """Test success property when error is set."""
        result = GainSolutionResult(
            gains=np.ones((10, 1, 1)),
            error="Test error",
        )
        assert result.success is False


class TestApplyCalResult:
    """Test ApplyCalResult dataclass."""

    def test_success_property(self):
        """Test success property."""
        result = ApplyCalResult(n_vis_processed=100)
        assert result.success is True

        result_err = ApplyCalResult(error="Test error")
        assert result_err.success is False


class TestMemoryEstimation:
    """Test memory estimation functions."""

    def test_applycal_memory_estimation(self):
        """Test applycal memory estimation."""
        gpu_gb, sys_gb = estimate_applycal_memory_gb(
            n_vis=1_000_000,
            n_channels=1024,
            n_pols=4,
            n_antennas=110,
        )
        # Should be reasonable estimates
        assert gpu_gb > 0
        assert gpu_gb < 10  # Should be under 10 GB
        assert sys_gb > gpu_gb

    def test_solve_memory_estimation(self):
        """Test solve memory estimation."""
        gpu_gb, sys_gb = estimate_solve_memory_gb(
            n_vis=1_000_000,
            n_antennas=110,
        )
        assert gpu_gb > 0
        assert sys_gb > gpu_gb


class TestApplyGainsCPU:
    """Test CPU gain application."""

    def test_unit_gains(self):
        """Test that unit gains don't change visibilities."""
        rng = np.random.default_rng(42)
        n_vis = 100
        n_ant = 10

        vis = (rng.standard_normal(n_vis) + 1j * rng.standard_normal(n_vis))
        gains = np.ones(n_ant, dtype=np.complex128)
        ant1 = rng.integers(0, n_ant, n_vis)
        ant2 = rng.integers(0, n_ant, n_vis)

        corrected, n_flagged = apply_gains_cpu(vis.copy(), gains, ant1, ant2)

        np.testing.assert_allclose(corrected.squeeze(), vis, rtol=1e-10)
        assert n_flagged == 0

    def test_constant_gains(self):
        """Test gain application with constant gains."""
        n_vis = 50
        n_ant = 5

        vis = np.ones(n_vis, dtype=np.complex128)
        gains = np.full(n_ant, 2.0 + 0j, dtype=np.complex128)
        ant1 = np.zeros(n_vis, dtype=int)
        ant2 = np.ones(n_vis, dtype=int)

        corrected, n_flagged = apply_gains_cpu(vis.copy(), gains, ant1, ant2)

        # V_corr = V / (g1 * conj(g2)) = 1 / (2 * 2) = 0.25
        np.testing.assert_allclose(corrected.squeeze(), 0.25, rtol=1e-10)
        assert n_flagged == 0

    def test_zero_gains_flagged(self):
        """Test that zero gains are handled by flagging."""
        n_vis = 10

        vis = np.ones(n_vis, dtype=np.complex128)
        gains = np.array([0.0, 1.0, 1.0], dtype=np.complex128)
        ant1 = np.zeros(n_vis, dtype=int)  # All use antenna 0 (gain=0)
        ant2 = np.ones(n_vis, dtype=int)

        corrected, n_flagged = apply_gains_cpu(vis.copy(), gains, ant1, ant2)

        # All should be flagged (NaN) due to zero gain
        assert n_flagged == n_vis
        assert np.all(np.isnan(corrected))


class TestSolveGainsCPU:
    """Test CPU gain solving."""

    def test_solve_known_gains(self):
        """Test solving for known gains."""
        rng = np.random.default_rng(42)
        n_vis = 1000
        n_ant = 10

        # Generate true gains
        true_gains = (
            rng.uniform(0.9, 1.1, n_ant) +
            1j * rng.uniform(-0.05, 0.05, n_ant)
        ).astype(np.complex128)

        # Reference antenna
        refant = 0
        true_gains[refant] = 1.0 + 0j

        # Generate baselines
        ant1 = rng.integers(0, n_ant, n_vis)
        ant2 = rng.integers(0, n_ant, n_vis)

        # Model (assume point source at phase center)
        model = np.ones(n_vis, dtype=np.complex128)

        # Observed = g1 * M * conj(g2)
        vis = model * true_gains[ant1] * np.conj(true_gains[ant2])

        weights = np.ones(n_vis)

        result = solve_per_antenna_gains_cpu(
            vis, model, ant1, ant2, weights, n_ant,
            refant=refant, max_iter=100, tol=1e-8
        )

        assert result.converged
        assert result.n_iterations < 50

        # Check gains match (up to a global phase)
        # Normalize by reference antenna
        solved = result.gains.squeeze()

        for ant in range(n_ant):
            if ant == refant:
                continue
            np.testing.assert_allclose(
                np.abs(solved[ant]),
                np.abs(true_gains[ant]),
                rtol=0.1,  # Within 10%
            )

    def test_solve_with_noise(self):
        """Test solving with noisy data."""
        rng = np.random.default_rng(123)
        n_vis = 2000
        n_ant = 8

        true_gains = np.ones(n_ant, dtype=np.complex128)
        true_gains[1:] = (
            rng.uniform(0.95, 1.05, n_ant - 1) +
            1j * rng.uniform(-0.02, 0.02, n_ant - 1)
        )

        ant1 = rng.integers(0, n_ant, n_vis)
        ant2 = rng.integers(0, n_ant, n_vis)

        model = np.ones(n_vis, dtype=np.complex128)
        vis = model * true_gains[ant1] * np.conj(true_gains[ant2])

        # Add noise
        noise_level = 0.01
        noise = noise_level * (
            rng.standard_normal(n_vis) + 1j * rng.standard_normal(n_vis)
        )
        vis_noisy = vis + noise

        weights = np.ones(n_vis)

        result = solve_per_antenna_gains_cpu(
            vis_noisy, model, ant1, ant2, weights, n_ant,
            refant=0, max_iter=100,
        )

        # Should still converge with small noise
        assert result.success


class TestApplyGainsDispatch:
    """Test automatic GPU/CPU dispatch."""

    def test_cpu_fallback(self):
        """Test that CPU fallback works."""
        rng = np.random.default_rng(42)
        n_vis = 100
        n_ant = 5

        vis = rng.standard_normal(n_vis) + 1j * rng.standard_normal(n_vis)
        gains = np.ones(n_ant, dtype=np.complex128)
        ant1 = rng.integers(0, n_ant, n_vis)
        ant2 = rng.integers(0, n_ant, n_vis)

        result = apply_gains(vis.copy(), gains, ant1, ant2, use_gpu=False)
        assert result.success
        assert result.n_vis_processed == n_vis

    @pytest.mark.skipif(not CUPY_AVAILABLE, reason="CuPy not available")
    def test_gpu_path(self):
        """Test GPU path when available."""
        rng = np.random.default_rng(42)
        n_vis = 100
        n_ant = 5

        vis = rng.standard_normal(n_vis) + 1j * rng.standard_normal(n_vis)
        vis = vis.astype(np.complex128)
        gains = np.ones(n_ant, dtype=np.complex128)
        ant1 = rng.integers(0, n_ant, n_vis).astype(np.int32)
        ant2 = rng.integers(0, n_ant, n_vis).astype(np.int32)

        result = apply_gains(vis.copy(), gains, ant1, ant2, use_gpu=True)
        assert result.success


class TestSolveGainsDispatch:
    """Test automatic GPU/CPU dispatch for solving."""

    def test_cpu_fallback(self):
        """Test CPU fallback for solving."""
        rng = np.random.default_rng(42)
        n_vis = 500
        n_ant = 5

        vis = np.ones(n_vis, dtype=np.complex128)
        model = np.ones(n_vis, dtype=np.complex128)
        ant1 = rng.integers(0, n_ant, n_vis)
        ant2 = rng.integers(0, n_ant, n_vis)
        weights = np.ones(n_vis)

        result = solve_per_antenna_gains(
            vis, model, ant1, ant2, weights, n_ant, use_gpu=False
        )
        assert result.success

    @pytest.mark.skipif(not CUPY_AVAILABLE, reason="CuPy not available")
    def test_gpu_path(self):
        """Test GPU path for solving when available."""
        rng = np.random.default_rng(42)
        n_vis = 500
        n_ant = 5

        vis = np.ones(n_vis, dtype=np.complex128)
        model = np.ones(n_vis, dtype=np.complex128)
        ant1 = rng.integers(0, n_ant, n_vis)
        ant2 = rng.integers(0, n_ant, n_vis)
        weights = np.ones(n_vis)

        result = solve_per_antenna_gains(
            vis, model, ant1, ant2, weights, n_ant, use_gpu=True
        )
        assert result.success


class TestCupyAvailability:
    """Test CuPy availability detection."""

    def test_cupy_available_flag(self):
        """Test that CUPY_AVAILABLE is a boolean."""
        assert isinstance(CUPY_AVAILABLE, bool)

    @pytest.mark.skipif(not CUPY_AVAILABLE, reason="CuPy not available")
    def test_cupy_import(self):
        """Test CuPy can be imported when available."""
        import cupy as cp
        assert cp is not None
