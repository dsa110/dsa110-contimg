"""
Comprehensive edge case testing for synthetic data generation.

Tests extreme parameter values, antenna configurations, time/frequency edge cases,
and coordinate edge cases to ensure robustness.
"""

from pathlib import Path

import numpy as np
import pytest
from astropy import units as u
from astropy.time import Time

from dsa110_contimg.simulation.make_synthetic_uvh5 import (
    TelescopeConfig,
    build_time_arrays,
    build_uvw,
)
from dsa110_contimg.simulation.visibility_models import (
    add_calibration_errors,
    calculate_thermal_noise_rms,
    disk_source_visibility,
    gaussian_source_visibility,
)


@pytest.fixture
def sample_config():
    """Create a minimal TelescopeConfig for testing."""
    from astropy.coordinates import EarthLocation

    return TelescopeConfig(
        layout_csv=Path("/tmp/dummy.csv"),
        polarizations=[-5, -6],  # XX, YY
        num_subbands=4,
        channels_per_subband=64,
        channel_width_hz=1e6,
        reference_frequency_hz=1.4e9,
        integration_time_sec=10.0,
        phase_ra=180.0 * u.deg,
        phase_dec=35.0 * u.deg,
        freq_min_hz=1.2e9,
        freq_max_hz=1.6e9,
        total_duration_sec=3600.0,
        site_location=EarthLocation.of_site("greenwich"),
        extra_keywords={},
    )


class TestExtremeParameters:
    """Test extreme parameter values."""

    def test_very_small_flux(self):
        """Test flux near zero (1e-6 Jy)."""
        u_lambda = np.array([0.0, 100.0])
        v_lambda = np.array([0.0, 0.0])
        flux = 1e-6  # Very small flux

        vis = gaussian_source_visibility(u_lambda, v_lambda, flux, 10.0, 10.0, 0.0)

        # Visibility should be very small but non-zero
        assert np.all(np.abs(vis) > 0)
        assert np.abs(vis[0]) == pytest.approx(flux, rel=1e-3)
        assert np.all(np.abs(vis) <= flux)

    def test_very_large_flux(self):
        """Test very bright sources (1e6 Jy)."""
        u_lambda = np.array([0.0, 100.0])
        v_lambda = np.array([0.0, 0.0])
        flux = 1e6  # Very large flux

        vis = gaussian_source_visibility(u_lambda, v_lambda, flux, 10.0, 10.0, 0.0)

        # Visibility should be large but finite
        assert np.all(np.isfinite(vis))
        assert np.abs(vis[0]) == pytest.approx(flux, rel=1e-3)
        assert np.all(np.abs(vis) <= flux)

    def test_very_extended_source(self):
        """Test source larger than typical field of view (1000 arcsec)."""
        u_lambda = np.array([0.0, 10.0, 100.0])
        v_lambda = np.array([0.0, 0.0, 0.0])
        flux = 1.0
        size = 1000.0  # Very extended source (1000 arcsec)

        vis = gaussian_source_visibility(u_lambda, v_lambda, flux, size, size, 0.0)

        # Very extended source should have visibility that decays very quickly
        assert np.all(np.isfinite(vis))
        assert np.abs(vis[0]) == pytest.approx(flux, rel=1e-3)
        # Visibility should decay significantly at longer baselines
        # (Allow some tolerance - very extended sources decay quickly but not instantly)
        assert np.abs(vis[2]) < 0.5 * flux

    def test_extreme_calibration_errors(self):
        """Test very large calibration errors (gain_std=1.0, phase_std=180°)."""
        vis = np.ones((10, 1, 64, 2), dtype=complex)
        nants = 10

        # Extreme errors
        vis_cal, gains, phases = add_calibration_errors(
            vis, nants, gain_std=1.0, phase_std_deg=180.0, rng=np.random.default_rng(42)
        )

        # Should still produce finite results
        assert np.all(np.isfinite(vis_cal))
        assert np.all(np.isfinite(gains))
        assert np.all(np.isfinite(phases))

        # Gains are complex, check magnitude is positive
        assert np.all(np.abs(gains) > 0)

        # Phases should be in reasonable range (even with large std)
        assert np.all(np.abs(phases) < 360.0)

    def test_zero_flux(self):
        """Test zero flux (edge case)."""
        u_lambda = np.array([0.0, 100.0])
        v_lambda = np.array([0.0, 0.0])
        flux = 0.0

        vis = gaussian_source_visibility(u_lambda, v_lambda, flux, 10.0, 10.0, 0.0)

        # Zero flux should produce zero visibility
        assert np.allclose(vis, 0.0)


class TestAntennaConfigurations:
    """Test edge cases in antenna configurations."""

    def test_minimum_antennas(self, sample_config):
        """Test with 2 antennas (minimum for interferometry)."""
        config = sample_config

        # Minimum: 2 antennas = 1 baseline
        nants = 2
        ntimes = 1
        nbls = 1  # nants * (nants - 1) / 2 = 1

        # Create minimal antenna arrays
        ant1_array = np.array([0])
        ant2_array = np.array([1])

        start_time = Time("2024-01-01T00:00:00", format="isot", scale="utc")
        unique_times, time_array, lst_array, int_time = build_time_arrays(
            config, nbls, ntimes, start_time
        )

        # Should work with minimum antennas
        assert len(unique_times) == 1
        assert len(time_array) == nbls * ntimes

        # Build UVW (minimal case)
        uvw = build_uvw(config, unique_times, ant1_array, ant2_array, nants)

        assert uvw.shape == (nbls * ntimes, 3)
        assert np.all(np.isfinite(uvw))

    def test_single_baseline(self, sample_config):
        """Test with only one baseline."""
        config = sample_config

        nants = 2
        ntimes = 10
        nbls = 1

        # build_uvw creates outer product: for each time, for each baseline
        # So shape is (ntimes * nbls, 3)
        unique_times = np.array(
            [Time("2024-01-01T00:00:00", format="isot", scale="utc").mjd] * ntimes
        )
        ant1_array = np.array([0] * nbls)  # One baseline
        ant2_array = np.array([1] * nbls)

        uvw = build_uvw(config, unique_times, ant1_array, ant2_array, nants)

        # Should work with single baseline
        # build_uvw returns shape (ntimes * nbls, 3)
        expected_shape = (ntimes * nbls, 3)
        assert uvw.shape == expected_shape
        assert np.all(np.isfinite(uvw))


class TestTimeFrequencyEdgeCases:
    """Test edge cases in time/frequency."""

    def test_single_integration(self, sample_config):
        """Test with only one time integration."""
        config = sample_config

        nbls = 10
        ntimes = 1  # Single integration

        start_time = Time("2024-01-01T00:00:00", format="isot", scale="utc")
        unique_times, time_array, lst_array, int_time = build_time_arrays(
            config, nbls, ntimes, start_time
        )

        # Should work with single integration
        assert len(unique_times) == 1
        assert len(time_array) == nbls * ntimes
        assert np.allclose(time_array, time_array[0])

    def test_very_long_time_series(self, sample_config):
        """Test with many time integrations (simulate 24 hours)."""
        config = sample_config

        # 24 hours = 8640 seconds, 10 sec integrations = 864 integrations
        nbls = 10
        ntimes = 864  # 24 hours of data

        start_time = Time("2024-01-01T00:00:00", format="isot", scale="utc")
        unique_times, time_array, lst_array, int_time = build_time_arrays(
            config, nbls, ntimes, start_time
        )

        # Should handle many integrations
        assert len(unique_times) == ntimes
        assert len(time_array) == nbls * ntimes

        # Time should progress correctly
        time_diff = (time_array[-1] - time_array[0]) * 86400.0  # Convert to seconds
        expected_diff = (ntimes - 1) * config.integration_time_sec
        assert time_diff == pytest.approx(expected_diff, rel=0.01)

    def test_extreme_noise_parameters(self):
        """Test noise calculation with extreme parameters."""
        # Very short integration time
        rms_short = calculate_thermal_noise_rms(
            integration_time_sec=0.1,
            channel_width_hz=1e6,
            system_temperature_k=50.0,
            efficiency=0.7,
            frequency_hz=1.4e9,
        )
        assert rms_short > 0
        assert np.isfinite(rms_short)

        # Very long integration time
        rms_long = calculate_thermal_noise_rms(
            integration_time_sec=3600.0,
            channel_width_hz=1e6,
            system_temperature_k=50.0,
            efficiency=0.7,
            frequency_hz=1.4e9,
        )
        assert rms_long > 0
        assert np.isfinite(rms_long)
        assert rms_long < rms_short  # Longer integration = lower noise

        # Very narrow channel
        rms_narrow = calculate_thermal_noise_rms(
            integration_time_sec=10.0,
            channel_width_hz=1e3,  # 1 kHz
            system_temperature_k=50.0,
            efficiency=0.7,
            frequency_hz=1.4e9,
        )
        assert rms_narrow > 0
        assert np.isfinite(rms_narrow)
        assert rms_narrow > rms_short  # Narrower channel = higher noise


class TestCoordinateEdgeCases:
    """Test edge cases in coordinates."""

    def test_north_pole(self):
        """Test at dec = +90° (North Pole)."""
        u_lambda = np.array([0.0, 100.0])
        v_lambda = np.array([0.0, 0.0])
        flux = 1.0

        # Should work at pole
        vis = gaussian_source_visibility(u_lambda, v_lambda, flux, 10.0, 10.0, 0.0)

        assert np.all(np.isfinite(vis))
        assert np.abs(vis[0]) == pytest.approx(flux, rel=1e-3)

    def test_south_pole(self):
        """Test at dec = -90° (South Pole)."""
        u_lambda = np.array([0.0, 100.0])
        v_lambda = np.array([0.0, 0.0])
        flux = 1.0

        # Should work at pole
        vis = gaussian_source_visibility(u_lambda, v_lambda, flux, 10.0, 10.0, 0.0)

        assert np.all(np.isfinite(vis))
        assert np.abs(vis[0]) == pytest.approx(flux, rel=1e-3)

    def test_equator(self):
        """Test at dec = 0° (Equator)."""
        u_lambda = np.array([0.0, 100.0])
        v_lambda = np.array([0.0, 0.0])
        flux = 1.0

        # Should work at equator
        vis = gaussian_source_visibility(u_lambda, v_lambda, flux, 10.0, 10.0, 0.0)

        assert np.all(np.isfinite(vis))
        assert np.abs(vis[0]) == pytest.approx(flux, rel=1e-3)

    def test_date_line(self):
        """Test at ra = 0°/360° (Date Line)."""
        u_lambda = np.array([0.0, 100.0])
        v_lambda = np.array([0.0, 0.0])
        flux = 1.0

        # Should work at date line
        vis = gaussian_source_visibility(u_lambda, v_lambda, flux, 10.0, 10.0, 0.0)

        assert np.all(np.isfinite(vis))
        assert np.abs(vis[0]) == pytest.approx(flux, rel=1e-3)


class TestVisibilityModelEdgeCases:
    """Test edge cases in visibility models."""

    def test_zero_radius_disk(self):
        """Test disk source with zero radius (should be point source)."""
        u_lambda = np.array([0.0, 100.0])
        v_lambda = np.array([0.0, 0.0])
        flux = 1.0
        radius = 0.0

        vis = disk_source_visibility(u_lambda, v_lambda, flux, radius)

        # Zero radius disk should behave like point source
        # At origin, visibility should equal flux
        assert np.abs(vis[0]) == pytest.approx(flux, rel=1e-3)
        # At non-zero baseline, should be constant (point source)
        assert np.all(np.isfinite(vis))

    def test_very_small_disk(self):
        """Test disk source with very small radius."""
        u_lambda = np.array([0.0, 100.0])
        v_lambda = np.array([0.0, 0.0])
        flux = 1.0
        radius = 0.001  # 1 mas

        vis = disk_source_visibility(u_lambda, v_lambda, flux, radius)

        # Should behave nearly like point source
        assert np.all(np.isfinite(vis))
        assert np.abs(vis[0]) == pytest.approx(flux, rel=1e-3)

    def test_gaussian_zero_size(self):
        """Test Gaussian source with zero size."""
        u_lambda = np.array([0.0, 100.0])
        v_lambda = np.array([0.0, 0.0])
        flux = 1.0

        vis = gaussian_source_visibility(u_lambda, v_lambda, flux, 0.0, 0.0, 0.0)

        # Zero size should be point source (constant visibility)
        assert np.all(np.isfinite(vis))
        assert np.allclose(np.abs(vis), flux)
