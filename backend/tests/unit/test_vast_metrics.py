"""
Unit tests for VAST-style QA metrics modules.

Tests for:
- image_qa.py: Image-level RMS statistics
- source_metrics.py: Source-level metrics (compactness, island ratios, etc.)
- condon_errors.py: Condon (1997) error calculations
- multi_epoch.py: Multi-epoch aggregate statistics
"""

import numpy as np
import pytest


# =============================================================================
# Image QA Tests
# =============================================================================


class TestImageRMSMetrics:
    """Tests for ImageRMSMetrics and get_rms_noise_image_values."""

    def test_basic_rms_stats(self):
        """Test basic RMS statistics calculation."""
        from dsa110_contimg.photometry.image_qa import get_rms_noise_image_values

        # Create simple noise map
        noise_map = np.array([
            [0.001, 0.002, 0.003],
            [0.001, 0.002, 0.003],
            [0.001, 0.002, 0.003],
        ])

        result = get_rms_noise_image_values(noise_map)

        assert result.rms_min == pytest.approx(0.001)
        assert result.rms_max == pytest.approx(0.003)
        assert result.rms_median == pytest.approx(0.002)
        assert result.n_valid_pixels == 9
        assert result.coverage_fraction == 1.0

    def test_rms_with_nan(self):
        """Test RMS calculation with NaN values."""
        from dsa110_contimg.photometry.image_qa import get_rms_noise_image_values

        noise_map = np.array([
            [0.001, np.nan, 0.003],
            [0.002, 0.002, np.nan],
            [0.001, 0.002, 0.003],
        ])

        result = get_rms_noise_image_values(noise_map)

        assert result.n_valid_pixels == 7
        assert result.coverage_fraction == pytest.approx(7 / 9)
        assert result.rms_min == pytest.approx(0.001)
        assert result.rms_max == pytest.approx(0.003)

    def test_rms_with_mask(self):
        """Test RMS calculation with explicit mask."""
        from dsa110_contimg.photometry.image_qa import get_rms_noise_image_values

        noise_map = np.full((3, 3), 0.002)
        mask = np.array([
            [True, True, False],
            [True, True, False],
            [False, False, False],
        ])

        result = get_rms_noise_image_values(noise_map, mask=mask)

        assert result.n_valid_pixels == 4
        assert result.rms_median == pytest.approx(0.002)

    def test_rms_all_invalid_raises(self):
        """Test that all-NaN noise map raises ValueError."""
        from dsa110_contimg.photometry.image_qa import get_rms_noise_image_values

        noise_map = np.full((3, 3), np.nan)

        with pytest.raises(ValueError, match="No valid pixels"):
            get_rms_noise_image_values(noise_map)

    def test_image_rms_to_dict(self):
        """Test ImageRMSMetrics.to_dict serialization."""
        from dsa110_contimg.photometry.image_qa import ImageRMSMetrics

        metrics = ImageRMSMetrics(
            rms_median=0.002,
            rms_min=0.001,
            rms_max=0.003,
            rms_mean=0.002,
            rms_std=0.001,
            n_valid_pixels=100,
            coverage_fraction=0.95,
        )

        d = metrics.to_dict()
        assert d["rms_median"] == 0.002
        assert d["n_valid_pixels"] == 100


class TestImageQAMetrics:
    """Tests for compute_image_qa_metrics."""

    def test_image_qa_nonexistent_file(self):
        """Test QA metrics for non-existent file."""
        from dsa110_contimg.photometry.image_qa import compute_image_qa_metrics

        result = compute_image_qa_metrics("/nonexistent/image.fits")

        assert not result.passed
        assert "not found" in result.warnings[0]

    def test_image_qa_to_dict(self):
        """Test ImageQAMetrics.to_dict serialization."""
        from dsa110_contimg.photometry.image_qa import ImageQAMetrics, ImageRMSMetrics

        rms = ImageRMSMetrics(0.002, 0.001, 0.003, 0.002, 0.001, 100, 0.95)
        metrics = ImageQAMetrics(
            image_path="/test/image.fits",
            rms=rms,
            dynamic_range=1000.0,
            peak_flux=2.0,
        )

        d = metrics.to_dict()
        assert d["image_path"] == "/test/image.fits"
        assert d["rms"]["rms_median"] == 0.002
        assert d["dynamic_range"] == 1000.0


# =============================================================================
# Source Metrics Tests
# =============================================================================


class TestCompactness:
    """Tests for compactness calculation."""

    def test_point_source_compactness(self):
        """Test compactness for point source (ratio ~1)."""
        from dsa110_contimg.photometry.source_metrics import calculate_compactness

        # Point source: integrated ≈ peak
        result = calculate_compactness(flux_int=1.0, flux_peak=1.0)
        assert result == pytest.approx(1.0)

    def test_extended_source_compactness(self):
        """Test compactness for extended source (ratio >1)."""
        from dsa110_contimg.photometry.source_metrics import calculate_compactness

        # Extended source: integrated > peak
        result = calculate_compactness(flux_int=2.0, flux_peak=1.0)
        assert result == pytest.approx(2.0)

    def test_compactness_zero_peak_raises(self):
        """Test that zero peak flux raises ValueError."""
        from dsa110_contimg.photometry.source_metrics import calculate_compactness

        with pytest.raises(ValueError, match="Peak flux must be positive"):
            calculate_compactness(flux_int=1.0, flux_peak=0.0)


class TestSNR:
    """Tests for SNR calculation."""

    def test_snr_calculation(self):
        """Test basic SNR calculation."""
        from dsa110_contimg.photometry.source_metrics import calculate_snr

        result = calculate_snr(flux_peak=0.01, local_rms=0.001)
        assert result == pytest.approx(10.0)

    def test_snr_zero_rms_raises(self):
        """Test that zero RMS raises ValueError."""
        from dsa110_contimg.photometry.source_metrics import calculate_snr

        with pytest.raises(ValueError, match="Local RMS must be positive"):
            calculate_snr(flux_peak=1.0, local_rms=0.0)


class TestIslandMetrics:
    """Tests for island flux ratios."""

    def test_single_component_island(self):
        """Test metrics for single-component island."""
        from dsa110_contimg.photometry.source_metrics import compute_island_metrics

        components = [{"flux_int": 1.0, "flux_peak": 0.8}]
        result = compute_island_metrics(
            component_flux_int=1.0,
            component_flux_peak=0.8,
            island_components=components,
        )

        assert result.flux_int_isl_ratio == pytest.approx(1.0)
        assert result.flux_peak_isl_ratio == pytest.approx(1.0)
        assert result.has_siblings is False
        assert result.n_siblings == 0

    def test_multi_component_island(self):
        """Test metrics for multi-component island."""
        from dsa110_contimg.photometry.source_metrics import compute_island_metrics

        components = [
            {"flux_int": 0.6, "flux_peak": 0.5},
            {"flux_int": 0.4, "flux_peak": 0.3},
        ]
        result = compute_island_metrics(
            component_flux_int=0.6,
            component_flux_peak=0.5,
            island_components=components,
        )

        assert result.flux_int_isl_ratio == pytest.approx(0.6)  # 0.6 / 1.0
        assert result.flux_peak_isl_ratio == pytest.approx(1.0)  # 0.5 / 0.5
        assert result.has_siblings is True
        assert result.n_siblings == 1


class TestSpatialMetrics:
    """Tests for spatial metrics calculations."""

    def test_nearest_neighbor_distance(self):
        """Test nearest neighbor distance calculation."""
        from dsa110_contimg.photometry.source_metrics import (
            compute_nearest_neighbor_distance,
        )

        # Two sources 1 degree apart
        all_ra = np.array([0.0, 1.0])
        all_dec = np.array([0.0, 0.0])

        dist = compute_nearest_neighbor_distance(0.0, 0.0, all_ra, all_dec)
        assert dist == pytest.approx(1.0, rel=0.01)

    def test_isolated_source(self):
        """Test spatial metrics for isolated source."""
        from dsa110_contimg.photometry.source_metrics import compute_spatial_metrics

        # Single source (infinite neighbor distance)
        result = compute_spatial_metrics(
            ra_deg=0.0,
            dec_deg=0.0,
            all_ra_deg=np.array([0.0]),
            all_dec_deg=np.array([0.0]),
        )

        assert result.is_isolated is True
        assert result.n_neighbour_dist == float("inf")


class TestSourceQAMetrics:
    """Tests for complete source QA metrics."""

    def test_compute_source_qa_basic(self):
        """Test basic source QA metrics computation."""
        from dsa110_contimg.photometry.source_metrics import compute_source_qa_metrics

        result = compute_source_qa_metrics(
            source_id="test_source",
            ra_deg=180.0,
            dec_deg=37.0,
            flux_peak=0.01,
            flux_int=0.012,
            local_rms=0.001,
        )

        assert result.snr == pytest.approx(10.0)
        assert result.morphology.compactness == pytest.approx(1.2)
        assert result.morphology.is_resolved is False  # 1.2 < 1.2 threshold

    def test_batch_compute_source_metrics(self):
        """Test batch source metrics computation."""
        from dsa110_contimg.photometry.source_metrics import (
            batch_compute_source_metrics,
        )

        sources = [
            {"source_id": "s1", "ra_deg": 0.0, "dec_deg": 0.0,
             "flux_peak": 0.01, "flux_int": 0.01, "local_rms": 0.001},
            {"source_id": "s2", "ra_deg": 0.1, "dec_deg": 0.0,
             "flux_peak": 0.02, "flux_int": 0.02, "local_rms": 0.001},
        ]

        results = batch_compute_source_metrics(sources)

        assert len(results) == 2
        assert results[0].source_id == "s1"
        assert results[1].source_id == "s2"
        # Both should have spatial metrics (neighbors)
        assert results[0].spatial is not None


# =============================================================================
# Condon Error Tests
# =============================================================================


class TestCondonFluxErrors:
    """Tests for Condon (1997) flux error calculations."""

    def test_point_source_errors(self):
        """Test flux errors for point source."""
        from dsa110_contimg.photometry.condon_errors import calc_condon_flux_errors

        result = calc_condon_flux_errors(
            flux_peak=0.01,
            flux_int=0.01,
            snr=10.0,
            local_rms=0.001,
            major_arcsec=30.0,
            minor_arcsec=25.0,
            pa_deg=45.0,
            beam_major_arcsec=30.0,
            beam_minor_arcsec=25.0,
        )

        # For point source (size = beam), errors scale as flux/SNR
        assert result.flux_peak_err > 0
        assert result.flux_int_err > 0
        assert result.major_err_arcsec > 0
        assert result.minor_err_arcsec > 0

    def test_resolved_source_larger_errors(self):
        """Test that resolved sources have larger flux errors."""
        from dsa110_contimg.photometry.condon_errors import calc_condon_flux_errors

        # Point source
        point = calc_condon_flux_errors(
            flux_peak=0.01, flux_int=0.01, snr=10.0, local_rms=0.001,
            major_arcsec=30.0, minor_arcsec=25.0, pa_deg=45.0,
            beam_major_arcsec=30.0, beam_minor_arcsec=25.0,
        )

        # Resolved source (larger than beam)
        resolved = calc_condon_flux_errors(
            flux_peak=0.01, flux_int=0.02, snr=10.0, local_rms=0.001,
            major_arcsec=60.0, minor_arcsec=50.0, pa_deg=45.0,
            beam_major_arcsec=30.0, beam_minor_arcsec=25.0,
        )

        # Resolved source should have larger integrated flux error
        assert resolved.flux_int_err > point.flux_int_err

    def test_invalid_snr_raises(self):
        """Test that invalid SNR raises ValueError."""
        from dsa110_contimg.photometry.condon_errors import calc_condon_flux_errors

        with pytest.raises(ValueError, match="SNR must be positive"):
            calc_condon_flux_errors(
                flux_peak=0.01, flux_int=0.01, snr=0.0, local_rms=0.001,
                major_arcsec=30.0, minor_arcsec=25.0, pa_deg=45.0,
                beam_major_arcsec=30.0, beam_minor_arcsec=25.0,
            )


class TestCondonPositionErrors:
    """Tests for Condon (1997) positional error calculations."""

    def test_position_errors_scale_with_snr(self):
        """Test that position errors decrease with SNR."""
        from dsa110_contimg.photometry.condon_errors import calc_condon_position_errors

        low_snr = calc_condon_position_errors(
            snr=5.0,
            major_arcsec=30.0, minor_arcsec=25.0, pa_deg=0.0,
            beam_major_arcsec=30.0, beam_minor_arcsec=25.0,
        )

        high_snr = calc_condon_position_errors(
            snr=50.0,
            major_arcsec=30.0, minor_arcsec=25.0, pa_deg=0.0,
            beam_major_arcsec=30.0, beam_minor_arcsec=25.0,
        )

        # Higher SNR should give smaller errors
        assert high_snr.ra_err_arcsec < low_snr.ra_err_arcsec
        assert high_snr.dec_err_arcsec < low_snr.dec_err_arcsec

    def test_systematic_errors_added(self):
        """Test that systematic errors are added in quadrature."""
        from dsa110_contimg.photometry.condon_errors import calc_condon_position_errors

        no_sys = calc_condon_position_errors(
            snr=10.0,
            major_arcsec=30.0, minor_arcsec=25.0, pa_deg=0.0,
            beam_major_arcsec=30.0, beam_minor_arcsec=25.0,
        )

        with_sys = calc_condon_position_errors(
            snr=10.0,
            major_arcsec=30.0, minor_arcsec=25.0, pa_deg=0.0,
            beam_major_arcsec=30.0, beam_minor_arcsec=25.0,
            systematic_ra_arcsec=1.0,
            systematic_dec_arcsec=1.0,
        )

        # Systematic errors should increase total
        assert with_sys.ra_err_arcsec > no_sys.ra_err_arcsec
        assert with_sys.dec_err_arcsec > no_sys.dec_err_arcsec


class TestCondonErrorsCombined:
    """Tests for complete Condon error calculation."""

    def test_calc_condon_errors(self):
        """Test complete Condon error calculation."""
        from dsa110_contimg.photometry.condon_errors import calc_condon_errors

        result = calc_condon_errors(
            flux_peak=0.01,
            flux_int=0.012,
            snr=10.0,
            local_rms=0.001,
            major_arcsec=35.0,
            minor_arcsec=28.0,
            pa_deg=30.0,
            beam_major_arcsec=30.0,
            beam_minor_arcsec=25.0,
        )

        assert result.flux.flux_peak_err > 0
        assert result.position.ra_err_arcsec > 0
        assert result.position.error_radius_arcsec > 0

    def test_simple_position_error(self):
        """Test simple position error estimate."""
        from dsa110_contimg.photometry.condon_errors import simple_position_error

        # beam / (2 * SNR) = 30 / 20 = 1.5 arcsec
        result = simple_position_error(beam_arcsec=30.0, snr=10.0)
        assert result == pytest.approx(1.5)


# =============================================================================
# Multi-Epoch Tests
# =============================================================================


class TestWeightedPosition:
    """Tests for weighted average position calculation."""

    def test_weighted_average_position(self):
        """Test weighted average position calculation."""
        from dsa110_contimg.photometry.multi_epoch import calc_weighted_average_position

        # Two measurements with different uncertainties
        ra = np.array([180.0, 180.01])
        dec = np.array([37.0, 37.0])
        ra_err = np.array([0.001, 0.002])  # First has smaller error
        dec_err = np.array([0.001, 0.001])

        result = calc_weighted_average_position(ra, dec, ra_err, dec_err)

        # Weighted average should be closer to first measurement
        assert result.wavg_ra < 180.005  # Closer to 180.0
        assert result.n_measurements == 2

    def test_weighted_position_with_invalid(self):
        """Test weighted position with some invalid measurements."""
        from dsa110_contimg.photometry.multi_epoch import calc_weighted_average_position

        ra = np.array([180.0, np.nan, 180.01])
        dec = np.array([37.0, 37.0, 37.0])
        ra_err = np.array([0.001, 0.001, 0.001])
        dec_err = np.array([0.001, 0.001, 0.001])

        result = calc_weighted_average_position(ra, dec, ra_err, dec_err)

        assert result.n_measurements == 2  # NaN excluded


class TestFluxAggregates:
    """Tests for flux aggregate statistics."""

    def test_flux_aggregates_basic(self):
        """Test basic flux aggregate calculation."""
        from dsa110_contimg.photometry.multi_epoch import calc_flux_aggregates

        flux_int = np.array([1.0, 2.0, 3.0])
        flux_peak = np.array([0.8, 1.5, 2.5])

        result = calc_flux_aggregates(flux_int, flux_peak)

        assert result.avg_flux_int == pytest.approx(2.0)
        assert result.min_flux_int == pytest.approx(1.0)
        assert result.max_flux_int == pytest.approx(3.0)
        assert result.n_detections == 3

    def test_flux_aggregates_with_forced(self):
        """Test flux aggregates distinguishing forced photometry."""
        from dsa110_contimg.photometry.multi_epoch import calc_flux_aggregates

        flux_int = np.array([1.0, 2.0, 3.0])
        flux_peak = np.array([0.8, 1.5, 2.5])
        is_forced = np.array([False, True, False])

        result = calc_flux_aggregates(flux_int, flux_peak, is_forced)

        assert result.n_detections == 2
        assert result.n_forced == 1


class TestNewSourceSignificance:
    """Tests for new source significance calculation."""

    def test_genuinely_new_source(self):
        """Test metrics for a genuinely new source."""
        from dsa110_contimg.photometry.multi_epoch import calc_new_source_significance

        # Source flux is 0.01 Jy, previous RMS values are 0.003 Jy (3.3σ)
        result = calc_new_source_significance(
            source_flux_peak=0.01,
            previous_rms_values=np.array([0.003, 0.003, 0.003]),
        )

        # At 3.3σ in previous images, below 5σ threshold -> new
        assert result.is_new is True
        assert result.new_high_sigma == pytest.approx(3.33, rel=0.1)

    def test_not_new_source(self):
        """Test metrics for source that should have been detected before."""
        from dsa110_contimg.photometry.multi_epoch import calc_new_source_significance

        # Source flux 0.01 Jy, previous RMS 0.001 Jy (10σ)
        result = calc_new_source_significance(
            source_flux_peak=0.01,
            previous_rms_values=np.array([0.001, 0.001]),
        )

        # At 10σ in previous images, above 5σ threshold -> not new
        assert result.is_new is False
        assert result.new_high_sigma == pytest.approx(10.0)


class TestMultiEpochStats:
    """Tests for complete multi-epoch statistics."""

    def test_compute_multi_epoch_stats(self):
        """Test complete multi-epoch statistics computation."""
        from dsa110_contimg.photometry.multi_epoch import compute_multi_epoch_stats

        measurements = [
            {"ra_deg": 180.0, "dec_deg": 37.0, "flux_int": 0.01, "flux_peak": 0.008,
             "local_rms": 0.001, "mjd": 60000.0},
            {"ra_deg": 180.001, "dec_deg": 37.0, "flux_int": 0.012, "flux_peak": 0.010,
             "local_rms": 0.001, "mjd": 60001.0},
            {"ra_deg": 180.0, "dec_deg": 37.001, "flux_int": 0.011, "flux_peak": 0.009,
             "local_rms": 0.001, "mjd": 60002.0},
        ]

        result = compute_multi_epoch_stats("test_source", measurements)

        assert result.source_id == "test_source"
        assert result.n_measurements == 3
        assert result.flux.n_detections == 3
        assert result.snr.min_snr > 0


class TestTwoEpochMetrics:
    """Tests for two-epoch pair metrics."""

    def test_calc_two_epoch_pairs(self):
        """Test two-epoch pair metric calculation."""
        from dsa110_contimg.photometry.multi_epoch import calc_two_epoch_pair_metrics

        measurements = [
            {"flux_int": 1.0, "flux_peak": 0.8, "flux_err": 0.1},
            {"flux_int": 1.5, "flux_peak": 1.2, "flux_err": 0.1},
        ]

        pairs = calc_two_epoch_pair_metrics(measurements)

        assert len(pairs) == 1  # Only one pair for 2 measurements
        assert "vs_int" in pairs[0]
        assert "m_int" in pairs[0]

    def test_get_most_significant_pair(self):
        """Test finding most significant pair."""
        from dsa110_contimg.photometry.multi_epoch import (
            calc_two_epoch_pair_metrics,
            get_most_significant_pair,
        )

        # Create measurements with clear variability
        measurements = [
            {"flux_int": 1.0, "flux_peak": 0.8, "flux_err": 0.1},
            {"flux_int": 2.0, "flux_peak": 1.6, "flux_err": 0.1},  # Variable
            {"flux_int": 1.1, "flux_peak": 0.9, "flux_err": 0.1},
        ]

        pairs = calc_two_epoch_pair_metrics(measurements)
        significant = get_most_significant_pair(pairs, min_abs_vs=4.0)

        # The 0-1 or 1-2 pair should be most significant
        if significant:
            assert abs(significant["vs_int"]) >= 4.0 or abs(significant["vs_peak"]) >= 4.0


# =============================================================================
# Integration Tests
# =============================================================================


class TestMetricsIntegration:
    """Integration tests combining multiple metric modules."""

    def test_full_source_analysis(self):
        """Test complete source analysis workflow."""
        from dsa110_contimg.photometry.source_metrics import compute_source_qa_metrics
        from dsa110_contimg.photometry.condon_errors import calc_condon_errors

        # Step 1: Compute source QA metrics
        qa = compute_source_qa_metrics(
            source_id="integrated_test",
            ra_deg=180.0,
            dec_deg=37.0,
            flux_peak=0.015,
            flux_int=0.018,
            local_rms=0.001,
            major_arcsec=35.0,
            minor_arcsec=28.0,
            beam_major_arcsec=30.0,
            beam_minor_arcsec=25.0,
        )

        # Step 2: Compute Condon errors
        errors = calc_condon_errors(
            flux_peak=qa.flux_peak,
            flux_int=qa.flux_int,
            snr=qa.snr,
            local_rms=qa.local_rms,
            major_arcsec=35.0,
            minor_arcsec=28.0,
            pa_deg=45.0,
            beam_major_arcsec=30.0,
            beam_minor_arcsec=25.0,
        )

        # Verify integration
        assert qa.snr == pytest.approx(15.0)
        assert qa.morphology.compactness == pytest.approx(1.2)
        assert errors.flux.flux_peak_err > 0
        assert errors.position.ra_err_arcsec > 0

    def test_serialization_roundtrip(self):
        """Test that all metrics can be serialized to dict."""
        from dsa110_contimg.photometry.source_metrics import compute_source_qa_metrics
        from dsa110_contimg.photometry.condon_errors import calc_condon_errors
        from dsa110_contimg.photometry.multi_epoch import compute_multi_epoch_stats

        # Source QA
        qa = compute_source_qa_metrics(
            source_id="test", ra_deg=0.0, dec_deg=0.0,
            flux_peak=0.01, flux_int=0.01, local_rms=0.001,
        )
        qa_dict = qa.to_dict()
        assert isinstance(qa_dict, dict)
        assert "source_id" in qa_dict

        # Condon errors
        errors = calc_condon_errors(
            flux_peak=0.01, flux_int=0.01, snr=10.0, local_rms=0.001,
            major_arcsec=30.0, minor_arcsec=25.0, pa_deg=0.0,
            beam_major_arcsec=30.0, beam_minor_arcsec=25.0,
        )
        err_dict = errors.to_dict()
        assert isinstance(err_dict, dict)
        assert "flux" in err_dict

        # Multi-epoch
        measurements = [
            {"ra_deg": 0.0, "dec_deg": 0.0, "flux_int": 0.01,
             "flux_peak": 0.01, "local_rms": 0.001},
        ]
        multi = compute_multi_epoch_stats("test", measurements)
        multi_dict = multi.to_dict()
        assert isinstance(multi_dict, dict)
        assert "position" in multi_dict
