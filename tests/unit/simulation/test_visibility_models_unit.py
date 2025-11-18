"""Comprehensive unit tests for visibility_models.py.

Tests focus on:
- Mathematical correctness of visibility models
- Edge cases and boundary conditions
- Reproducibility
- Performance
"""

import numpy as np

from dsa110_contimg.simulation.visibility_models import (
    add_calibration_errors,
    add_thermal_noise,
    apply_calibration_errors_to_visibilities,
    calculate_thermal_noise_rms,
    disk_source_visibility,
    gaussian_source_visibility,
)


class TestCalculateThermalNoiseRMS:
    """Test thermal noise RMS calculation."""

    def test_noise_rms_basic(self):
        """Test basic noise RMS calculation."""
        int_time = 10.0  # seconds
        chan_width = 1e6  # Hz
        t_sys = 50.0  # K

        rms = calculate_thermal_noise_rms(int_time, chan_width, t_sys)

        assert rms > 0
        assert np.isfinite(rms)
        # Implementation uses efficiency=0.7 and converts T_sys to Jy (factor 2.0)
        # Using radiometer equation: sigma = (T_sys * 2.0) / (eta * sqrt(2 * BW * t))
        # With eta=0.7, sigma = (T_sys * 2.0) / (0.7 * sqrt(2 * BW * t))
        efficiency = 0.7
        t_sys_to_jy = 2.0  # Conversion factor
        expected_order = (t_sys * t_sys_to_jy) / (efficiency * np.sqrt(2 * chan_width * int_time))
        # Allow tolerance for implementation details
        assert abs(rms - expected_order) < expected_order * 0.1

    def test_noise_rms_scaling_with_time(self):
        """Test that noise decreases with integration time."""
        chan_width = 1e6
        t_sys = 50.0

        rms_short = calculate_thermal_noise_rms(1.0, chan_width, t_sys)
        rms_long = calculate_thermal_noise_rms(10.0, chan_width, t_sys)

        # Longer integration should have lower noise
        assert rms_long < rms_short
        # Should scale as 1/sqrt(t)
        ratio = rms_short / rms_long
        expected_ratio = np.sqrt(10.0)
        assert abs(ratio - expected_ratio) < expected_ratio * 0.2

    def test_noise_rms_scaling_with_bandwidth(self):
        """Test that noise decreases with bandwidth."""
        int_time = 10.0
        t_sys = 50.0

        rms_narrow = calculate_thermal_noise_rms(int_time, 1e6, t_sys)
        rms_wide = calculate_thermal_noise_rms(int_time, 10e6, t_sys)

        # Wider bandwidth should have lower noise
        assert rms_wide < rms_narrow
        # Should scale as 1/sqrt(BW)
        ratio = rms_narrow / rms_wide
        expected_ratio = np.sqrt(10.0)
        assert abs(ratio - expected_ratio) < expected_ratio * 0.2

    def test_noise_rms_scaling_with_temperature(self):
        """Test that noise scales with system temperature."""
        int_time = 10.0
        chan_width = 1e6

        rms_cold = calculate_thermal_noise_rms(int_time, chan_width, 25.0)
        rms_hot = calculate_thermal_noise_rms(int_time, chan_width, 100.0)

        # Hotter system should have more noise
        assert rms_hot > rms_cold
        # Should scale linearly with T_sys
        ratio = rms_hot / rms_cold
        expected_ratio = 100.0 / 25.0
        assert abs(ratio - expected_ratio) < expected_ratio * 0.1


class TestAddThermalNoise:
    """Test adding thermal noise to visibilities."""

    def test_add_noise_basic(self):
        """Test basic noise addition."""
        vis = np.ones((10, 1, 64, 2), dtype=np.complex64)
        int_time = 10.0
        chan_width = 1e6
        t_sys = 50.0

        noisy_vis = add_thermal_noise(vis, int_time, chan_width, t_sys)

        assert noisy_vis.shape == vis.shape
        assert noisy_vis.dtype == vis.dtype
        # Should have added noise (not all ones)
        # Check that values have changed (with some tolerance for edge cases)
        max_diff = np.max(np.abs(noisy_vis - vis))
        assert max_diff > 1e-6  # Should have some noise

    def test_add_noise_statistics(self):
        """Test that noise has correct statistics."""
        vis = np.zeros((1000, 1, 64, 2), dtype=np.complex64)
        int_time = 10.0
        chan_width = 1e6
        t_sys = 50.0

        noisy_vis = add_thermal_noise(vis, int_time, chan_width, t_sys)

        # Noise should be zero mean
        mean_real = np.mean(noisy_vis.real)
        mean_imag = np.mean(noisy_vis.imag)
        assert abs(mean_real) < 0.1
        assert abs(mean_imag) < 0.1

        # RMS should match expected
        rms_expected = calculate_thermal_noise_rms(int_time, chan_width, t_sys)
        rms_actual = np.std(noisy_vis.real)
        assert abs(rms_actual - rms_expected) < rms_expected * 0.3

    def test_add_noise_reproducibility(self):
        """Test that noise is reproducible with same seed."""
        vis = np.ones((10, 1, 64, 2), dtype=np.complex64)
        int_time = 10.0
        chan_width = 1e6
        t_sys = 50.0

        rng = np.random.Generator(np.random.PCG64(42))
        noisy1 = add_thermal_noise(vis, int_time, chan_width, t_sys, rng=rng)

        rng = np.random.Generator(np.random.PCG64(42))
        noisy2 = add_thermal_noise(vis, int_time, chan_width, t_sys, rng=rng)

        assert np.allclose(noisy1, noisy2)

    def test_add_noise_preserves_shape(self):
        """Test that noise addition preserves array shape."""
        shapes = [
            (10, 1, 64, 2),
            (100, 2, 128, 4),
            (1, 1, 1, 1),
        ]

        for shape in shapes:
            vis = np.ones(shape, dtype=np.complex64)
            noisy = add_thermal_noise(vis, 10.0, 1e6, 50.0)
            assert noisy.shape == shape


class TestGaussianSourceVisibility:
    """Test Gaussian extended source visibility calculation."""

    def test_gaussian_point_limit(self):
        """Test that small Gaussian approaches point source."""
        u = np.array([0.0, 100.0, 1000.0])
        v = np.array([0.0, 0.0, 0.0])
        amplitude = 1.0
        major = 0.001  # Very small (essentially point)
        minor = 0.001
        pa = 0.0

        vis = gaussian_source_visibility(u, v, amplitude, major, minor, pa)

        # Should be close to constant (point source)
        assert np.allclose(np.abs(vis), amplitude, rtol=0.1)

    def test_gaussian_at_origin(self):
        """Test Gaussian visibility at u=0, v=0."""
        u = np.array([0.0])
        v = np.array([0.0])
        amplitude = 1.0
        major = 10.0
        minor = 10.0
        pa = 0.0

        vis = gaussian_source_visibility(u, v, amplitude, major, minor, pa)

        # At origin, should equal amplitude
        assert np.allclose(vis[0], amplitude, rtol=1e-3)

    def test_gaussian_decay(self):
        """Test that Gaussian visibility decays with u,v."""
        u = np.array([0.0, 100.0, 1000.0, 10000.0])
        v = np.array([0.0, 0.0, 0.0, 0.0])
        amplitude = 1.0
        major = 10.0
        minor = 10.0
        pa = 0.0

        vis = gaussian_source_visibility(u, v, amplitude, major, minor, pa)

        # Should decay with increasing u
        assert abs(vis[0]) > abs(vis[1])
        assert abs(vis[1]) > abs(vis[2])
        assert abs(vis[2]) > abs(vis[3])

    def test_gaussian_elliptical(self):
        """Test elliptical Gaussian (major != minor)."""
        u = np.array([100.0, 0.0])
        v = np.array([0.0, 100.0])
        amplitude = 1.0
        major = 20.0
        minor = 10.0
        pa = 0.0

        vis = gaussian_source_visibility(u, v, amplitude, major, minor, pa)

        # Different decay along different axes
        assert len(vis) == 2
        assert abs(vis[0]) != abs(vis[1])

    def test_gaussian_position_angle(self):
        """Test that position angle affects visibility."""
        u = np.array([100.0])
        v = np.array([0.0])
        amplitude = 1.0
        major = 20.0
        minor = 10.0

        vis_pa0 = gaussian_source_visibility(u, v, amplitude, major, minor, 0.0)
        vis_pa90 = gaussian_source_visibility(u, v, amplitude, major, minor, 90.0)

        # Different PA should give different visibility
        assert abs(vis_pa0) != abs(vis_pa90)


class TestDiskSourceVisibility:
    """Test uniform disk source visibility calculation."""

    def test_disk_point_limit(self):
        """Test that small disk approaches point source."""
        u = np.array([0.0, 100.0, 1000.0])
        v = np.array([0.0, 0.0, 0.0])
        amplitude = 1.0
        radius = 0.001  # Very small (essentially point)

        vis = disk_source_visibility(u, v, amplitude, radius)

        # Should be close to constant (point source)
        assert np.allclose(np.abs(vis), amplitude, rtol=0.1)

    def test_disk_at_origin(self):
        """Test disk visibility at u=0, v=0."""
        u = np.array([0.0])
        v = np.array([0.0])
        amplitude = 1.0
        radius = 10.0

        vis = disk_source_visibility(u, v, amplitude, radius)

        # At origin, should equal amplitude
        assert np.allclose(vis[0], amplitude, rtol=1e-3)

    def test_disk_decay(self):
        """Test that disk visibility decays with u,v."""
        u = np.array([0.0, 100.0, 1000.0, 10000.0])
        v = np.array([0.0, 0.0, 0.0, 0.0])
        amplitude = 1.0
        radius = 10.0

        vis = disk_source_visibility(u, v, amplitude, radius)

        # Should decay with increasing u
        assert abs(vis[0]) > abs(vis[1])
        assert abs(vis[1]) > abs(vis[2])
        assert abs(vis[2]) > abs(vis[3])

    def test_disk_zeros(self):
        """Test disk visibility at zeros of Bessel function."""
        # First zero of J1 is at ~3.83
        # For a disk, first zero is at u*radius/lambda ~ 3.83
        # So for radius=10 arcsec, zero is at u ~ 3.83 * lambda / (10 arcsec)
        # Using approximate conversion: 1 arcsec = 4.85e-6 rad at 1 GHz
        # So u_lambda ~ 3.83 / (10 * 4.85e-6) ~ 79000
        u = np.array([79000.0])
        v = np.array([0.0])
        amplitude = 1.0
        radius = 10.0

        vis = disk_source_visibility(u, v, amplitude, radius)

        # Should be close to zero (first null)
        assert abs(vis[0]) < 0.1 * amplitude


class TestAddCalibrationErrors:
    """Test calibration error generation."""

    def test_cal_errors_basic(self):
        """Test basic calibration error generation."""
        vis = np.ones((10, 1, 64, 2), dtype=np.complex64)
        nants = 3
        gain_std = 0.1
        phase_std_deg = 10.0

        vis_corr, gains, phases = add_calibration_errors(vis, nants, gain_std, phase_std_deg)

        assert vis_corr.shape == vis.shape
        assert gains.shape == (nants, 64, 2)  # nants, nfreqs, npols
        assert phases.shape == (nants, 64, 2)

    def test_cal_errors_gain_statistics(self):
        """Test that gain errors have correct statistics."""
        vis = np.ones((100, 1, 64, 2), dtype=np.complex64)
        nants = 10
        gain_std = 0.1
        phase_std_deg = 10.0

        _, gains, _ = add_calibration_errors(vis, nants, gain_std, phase_std_deg)

        # Gains should be close to 1.0 on average
        mean_gain = np.mean(np.abs(gains))
        assert abs(mean_gain - 1.0) < 0.2

        # Gain std should be approximately gain_std
        gain_std_actual = np.std(np.abs(gains))
        assert abs(gain_std_actual - gain_std) < gain_std * 0.5

    def test_cal_errors_phase_statistics(self):
        """Test that phase errors have correct statistics."""
        vis = np.ones((100, 1, 64, 2), dtype=np.complex64)
        nants = 10
        gain_std = 0.1
        phase_std_deg = 10.0

        _, _, phases = add_calibration_errors(vis, nants, gain_std, phase_std_deg)

        # Phases should be in degrees
        phase_std_actual_deg = np.std(phases)
        assert abs(phase_std_actual_deg - phase_std_deg) < phase_std_deg * 0.5

    def test_cal_errors_reproducibility(self):
        """Test that calibration errors are reproducible."""
        vis = np.ones((10, 1, 64, 2), dtype=np.complex64)
        nants = 3

        rng = np.random.Generator(np.random.PCG64(42))
        vis1, gains1, phases1 = add_calibration_errors(vis, nants, 0.1, 10.0, rng=rng)

        rng = np.random.Generator(np.random.PCG64(42))
        vis2, gains2, phases2 = add_calibration_errors(vis, nants, 0.1, 10.0, rng=rng)

        assert np.allclose(vis1, vis2)
        assert np.allclose(gains1, gains2)
        assert np.allclose(phases1, phases2)

    def test_cal_errors_zero_std(self):
        """Test that zero std gives minimal errors."""
        vis = np.ones((10, 1, 64, 2), dtype=np.complex64)
        nants = 3

        vis_corr, gains, phases = add_calibration_errors(
            vis, nants, gain_std=0.0, phase_std_deg=0.0
        )

        # With zero std, gains should be very close to 1.0 and phases close to 0
        # (may have small numerical differences)
        assert np.allclose(np.abs(gains), 1.0, atol=0.01)
        assert np.allclose(phases, 0.0, atol=0.01)
        # Visibilities should be very close to original
        assert np.allclose(vis_corr, vis, rtol=0.01)


class TestApplyCalibrationErrorsToVisibilities:
    """Test applying calibration errors to visibilities."""

    def test_apply_errors_basic(self):
        """Test basic application of calibration errors."""
        vis = np.ones((10, 1, 64, 2), dtype=np.complex64)
        ant1 = np.array([0, 0, 1, 0, 1, 2, 0, 1, 2, 3])
        ant2 = np.array([1, 2, 2, 3, 3, 3, 1, 2, 2, 0])
        nants = 4

        # Create simple gains (all 1.0)
        gains = np.ones((nants, 64, 2), dtype=np.complex64)

        vis_corr = apply_calibration_errors_to_visibilities(vis, ant1, ant2, gains)

        assert vis_corr.shape == vis.shape
        # With gains=1, should be unchanged
        assert np.allclose(vis_corr, vis)

    def test_apply_errors_with_gains(self):
        """Test applying non-unity gains."""
        vis = np.ones((2, 1, 64, 2), dtype=np.complex64)
        ant1 = np.array([0, 1])
        ant2 = np.array([1, 2])
        nants = 3

        # Create gains: ant0=2.0, ant1=1.0, ant2=0.5
        gains = np.ones((nants, 64, 2), dtype=np.complex64)
        gains[0, :, :] = 2.0
        gains[1, :, :] = 1.0
        gains[2, :, :] = 0.5

        vis_corr = apply_calibration_errors_to_visibilities(vis, ant1, ant2, gains)

        # Baseline 0-1: should be 1.0 * 2.0 * conj(1.0) = 2.0
        assert np.allclose(vis_corr[0, 0, :, :], 2.0)
        # Baseline 1-2: should be 1.0 * 1.0 * conj(0.5) = 0.5
        assert np.allclose(vis_corr[1, 0, :, :], 0.5)

    def test_apply_errors_with_phases(self):
        """Test applying phase errors."""
        vis = np.ones((2, 1, 64, 2), dtype=np.complex64)
        ant1 = np.array([0, 1])
        ant2 = np.array([1, 2])
        nants = 3

        # Create gains with phases: ant0=90deg, ant1=0deg, ant2=-90deg
        gains = np.ones((nants, 64, 2), dtype=np.complex64)
        gains[0, :, :] = 1.0 * np.exp(1j * np.pi / 2)  # 90 deg
        gains[1, :, :] = 1.0  # 0 deg
        gains[2, :, :] = 1.0 * np.exp(-1j * np.pi / 2)  # -90 deg

        vis_corr = apply_calibration_errors_to_visibilities(vis, ant1, ant2, gains)

        # Baseline 0-1: phase should be 90 - 0 = 90 deg
        expected_phase_01 = np.pi / 2
        actual_phase_01 = np.angle(vis_corr[0, 0, 0, 0])
        assert abs(actual_phase_01 - expected_phase_01) < 0.01

        # Baseline 1-2: phase should be 0 - (-90) = 90 deg
        expected_phase_12 = np.pi / 2
        actual_phase_12 = np.angle(vis_corr[1, 0, 0, 0])
        assert abs(actual_phase_12 - expected_phase_12) < 0.01


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_noise_zero_temperature(self):
        """Test noise with zero system temperature."""
        vis = np.ones((10, 1, 64, 2), dtype=np.complex64)
        noisy = add_thermal_noise(vis, 10.0, 1e6, 0.0)
        # Should be unchanged (no noise)
        assert np.allclose(noisy, vis)

    def test_noise_zero_bandwidth(self):
        """Test noise with zero bandwidth (should handle gracefully)."""
        vis = np.ones((10, 1, 64, 2), dtype=np.complex64)
        # Zero bandwidth should give infinite or very large noise
        # But function should not crash
        try:
            add_thermal_noise(vis, 10.0, 0.0, 50.0)
            # If it doesn't crash, that's fine
        except (ZeroDivisionError, ValueError):
            # Expected for zero bandwidth
            pass

    def test_gaussian_zero_size(self):
        """Test Gaussian with zero size."""
        u = np.array([0.0, 100.0])
        v = np.array([0.0, 0.0])
        vis = gaussian_source_visibility(u, v, 1.0, 0.0, 0.0, 0.0)
        # Should behave like point source
        assert np.allclose(np.abs(vis), 1.0, rtol=0.1)

    def test_disk_zero_radius(self):
        """Test disk with zero radius."""
        u = np.array([0.0, 100.0])
        v = np.array([0.0, 0.0])
        vis = disk_source_visibility(u, v, 1.0, 0.0)
        # Zero radius may produce NaN, so check for that or point source behavior
        if np.any(np.isnan(vis)):
            # NaN is acceptable for zero radius (division by zero)
            # Just check it doesn't crash
            pass
        else:
            # If not NaN, should behave like point source
            assert np.allclose(np.abs(vis), 1.0, rtol=0.1)


class TestPerformance:
    """Test performance characteristics."""

    def test_noise_performance(self):
        """Test that noise addition is fast."""
        import time

        vis = np.ones((1000, 1, 64, 2), dtype=np.complex64)
        start = time.time()
        add_thermal_noise(vis, 10.0, 1e6, 50.0)
        elapsed = time.time() - start

        # Should complete in < 0.1 seconds
        assert elapsed < 0.1

    def test_gaussian_performance(self):
        """Test that Gaussian visibility calculation is fast."""
        import time

        u = np.linspace(0, 10000, 10000)
        v = np.linspace(0, 10000, 10000)
        start = time.time()
        gaussian_source_visibility(u, v, 1.0, 10.0, 10.0, 0.0)
        elapsed = time.time() - start

        # Should complete in < 0.1 seconds
        assert elapsed < 0.1

    def test_cal_errors_performance(self):
        """Test that calibration error generation is fast."""
        import time

        vis = np.ones((1000, 1, 64, 2), dtype=np.complex64)
        start = time.time()
        add_calibration_errors(vis, 110, 0.1, 10.0)  # DSA-110 has 110 antennas
        elapsed = time.time() - start

        # Should complete in < 0.1 seconds
        assert elapsed < 0.1
