"""Tests for enhanced synthetic data generation (noise, extended sources, cal errors)."""

import numpy as np
import pytest

from dsa110_contimg.simulation.visibility_models import (
    add_calibration_errors,
    add_thermal_noise,
    calculate_thermal_noise_rms,
    disk_source_visibility,
    gaussian_source_visibility,
)


def test_thermal_noise_calculation():
    """Test thermal noise RMS calculation."""
    rms = calculate_thermal_noise_rms(
        integration_time_sec=12.0,
        channel_width_hz=1e6,
        system_temperature_k=50.0,
        efficiency=0.7,
    )

    # Should be positive and reasonable (typically 0.01-0.1 Jy for DSA-110)
    assert rms > 0
    assert rms < 1.0  # Should be less than 1 Jy for typical parameters


def test_add_thermal_noise():
    """Test adding thermal noise to visibilities."""
    # Create simple visibility array
    vis = np.ones((10, 1, 64, 2), dtype=np.complex64) * (1.0 + 0j)

    # Add noise
    vis_noisy = add_thermal_noise(
        vis,
        integration_time_sec=12.0,
        channel_width_hz=1e6,
        system_temperature_k=50.0,
        rng=np.random.default_rng(42),  # Fixed seed for reproducibility
    )

    # Should have same shape
    assert vis_noisy.shape == vis.shape

    # Should have different values (noise added)
    assert not np.allclose(vis_noisy, vis, atol=1e-6)

    # Should be complex
    assert np.iscomplexobj(vis_noisy)


def test_gaussian_source_visibility():
    """Test Gaussian extended source visibility calculation."""
    # Create simple u, v coordinates
    u_lambda = np.array([0.0, 100.0, 1000.0])
    v_lambda = np.array([0.0, 0.0, 0.0])

    # Calculate visibility for 10 arcsec Gaussian
    vis = gaussian_source_visibility(
        u_lambda, v_lambda, flux_jy=1.0, major_axis_arcsec=10.0, minor_axis_arcsec=10.0
    )

    # Should have correct shape
    assert vis.shape == (3,)

    # At u=0, v=0, visibility should equal flux
    assert np.isclose(vis[0], 1.0, rtol=0.01)

    # At larger u, visibility should decrease
    assert abs(vis[2]) < abs(vis[0])


def test_disk_source_visibility():
    """Test uniform disk source visibility calculation."""
    try:
        # Create simple u, v coordinates
        u_lambda = np.array([0.0, 100.0, 1000.0])
        v_lambda = np.array([0.0, 0.0, 0.0])

        # Calculate visibility for 5 arcsec radius disk
        vis = disk_source_visibility(u_lambda, v_lambda, flux_jy=1.0, radius_arcsec=5.0)

        # Should have correct shape
        assert vis.shape == (3,)

        # At u=0, v=0, visibility should equal flux
        assert np.isclose(vis[0], 1.0, rtol=0.01)

        # At larger u, visibility should decrease
        assert abs(vis[2]) < abs(vis[0])
    except ImportError:
        pytest.skip("scipy not available, skipping disk source test")


def test_calibration_errors():
    """Test calibration error generation."""
    # Create simple visibility array
    vis = np.ones((10, 1, 64, 2), dtype=np.complex64) * (1.0 + 0j)
    nants = 10

    # Generate calibration errors
    vis_corr, gains, phases = add_calibration_errors(
        vis, nants, gain_std=0.1, phase_std_deg=10.0, rng=np.random.default_rng(42)
    )

    # Gains should have correct shape
    assert gains.shape == (nants, 64, 2)

    # Phases should have correct shape
    assert phases.shape == (nants, 64, 2)

    # Gains should be complex
    assert np.iscomplexobj(gains)

    # Phases should be real (radians)
    assert not np.iscomplexobj(phases)


def test_enhanced_generation_integration(tmp_path):
    """Test that enhanced features work in full generation."""
    # This would require running the full generation script
    # For now, just verify the functions can be imported and called
    from dsa110_contimg.simulation.visibility_models import (
        add_calibration_errors,
        add_thermal_noise,
    )

    # Create test data
    vis = np.ones((100, 1, 64, 2), dtype=np.complex64) * (1.0 + 0j)

    # Test noise addition
    vis_noisy = add_thermal_noise(vis, 12.0, 1e6, rng=np.random.default_rng(42))
    assert not np.allclose(vis_noisy, vis)

    # Test calibration errors
    _, gains, _ = add_calibration_errors(vis, 10, rng=np.random.default_rng(42))
    assert gains.shape == (10, 64, 2)


def test_noise_reproducibility():
    """Test that noise generation is reproducible with same seed."""
    vis = np.ones((10, 1, 64, 2), dtype=np.complex64) * (1.0 + 0j)

    # Generate noise with same seed
    rng1 = np.random.default_rng(42)
    vis1 = add_thermal_noise(vis, 12.0, 1e6, rng=rng1)

    rng2 = np.random.default_rng(42)
    vis2 = add_thermal_noise(vis, 12.0, 1e6, rng=rng2)

    # Should be identical
    assert np.allclose(vis1, vis2)


def test_cal_errors_reproducibility():
    """Test that calibration errors are reproducible with same seed."""
    vis = np.ones((10, 1, 64, 2), dtype=np.complex64) * (1.0 + 0j)

    # Generate cal errors with same seed
    rng1 = np.random.default_rng(42)
    _, gains1, phases1 = add_calibration_errors(vis, 10, rng=rng1)

    rng2 = np.random.default_rng(42)
    _, gains2, phases2 = add_calibration_errors(vis, 10, rng=rng2)

    # Should be identical
    assert np.allclose(gains1, gains2)
    assert np.allclose(phases1, phases2)
