"""Unit tests for Pydantic models validation.

Focus: Fast validation tests for all API models.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from dsa110_contimg.api.models import (
    AlertHistory,
    CalibrationSet,
    CalibratorMatch,
    ESECandidate,
    ImageInfo,
    ImageList,
    LightCurveData,
    Mosaic,
    PipelineStatus,
    ProductEntry,
    ProductList,
    QueueGroup,
    QueueStats,
    SourceDetail,
    SourceFluxPoint,
    SourceSearchResponse,
    SourceTimeseries,
    VariabilityMetrics,
)


class TestQueueStats:
    """Test QueueStats model."""

    def test_valid_queue_stats(self):
        """Test valid QueueStats creation."""
        stats = QueueStats(
            total=10,
            pending=2,
            in_progress=1,
            failed=0,
            completed=7,
            collecting=0,
        )
        assert stats.total == 10
        assert stats.pending == 2

    def test_queue_stats_defaults(self):
        """Test QueueStats with zero values."""
        stats = QueueStats(
            total=0,
            pending=0,
            in_progress=0,
            failed=0,
            completed=0,
            collecting=0,
        )
        assert stats.total == 0


class TestQueueGroup:
    """Test QueueGroup model."""

    def test_valid_queue_group(self):
        """Test valid QueueGroup creation."""
        now = datetime.now(tz=timezone.utc)
        group = QueueGroup(
            group_id="2025-10-07T00:00:00",
            state="pending",
            received_at=now,
            last_update=now,
            subbands_present=10,
            expected_subbands=16,
        )
        assert group.group_id == "2025-10-07T00:00:00"
        assert group.state == "pending"
        assert group.subbands_present == 10

    def test_queue_group_with_calibrator(self):
        """Test QueueGroup with calibrator matches."""
        now = datetime.now(tz=timezone.utc)
        match = CalibratorMatch(name="3C123", ra_deg=188.7, dec_deg=42.1, sep_deg=0.1)
        group = QueueGroup(
            group_id="2025-10-07T00:00:00",
            state="pending",
            received_at=now,
            last_update=now,
            subbands_present=10,
            expected_subbands=16,
            has_calibrator=True,
            matches=[match],
        )
        assert group.has_calibrator is True
        assert len(group.matches) == 1


class TestCalibrationSet:
    """Test CalibrationSet model."""

    def test_valid_calibration_set(self):
        """Test valid CalibrationSet creation."""
        cal_set = CalibrationSet(
            set_name="2025-10-06_J1234",
            tables=["/data/cal/cal.K", "/data/cal/cal.BP"],
            active=2,
            total=2,
        )
        assert cal_set.set_name == "2025-10-06_J1234"
        assert len(cal_set.tables) == 2
        assert cal_set.active == 2


class TestPipelineStatus:
    """Test PipelineStatus model."""

    def test_valid_pipeline_status(self):
        """Test valid PipelineStatus creation."""
        stats = QueueStats(
            total=10,
            pending=2,
            in_progress=1,
            failed=0,
            completed=7,
            collecting=0,
        )
        now = datetime.now(tz=timezone.utc)
        group = QueueGroup(
            group_id="2025-10-07T00:00:00",
            state="pending",
            received_at=now,
            last_update=now,
            subbands_present=10,
            expected_subbands=16,
        )
        cal_set = CalibrationSet(
            set_name="2025-10-06_J1234",
            tables=["/data/cal/cal.K"],
            active=1,
            total=1,
        )
        status = PipelineStatus(
            queue=stats,
            recent_groups=[group],
            calibration_sets=[cal_set],
            matched_recent=1,
        )
        assert status.queue.total == 10
        assert len(status.recent_groups) == 1
        assert len(status.calibration_sets) == 1


class TestProductEntry:
    """Test ProductEntry model."""

    def test_valid_product_entry(self):
        """Test valid ProductEntry creation."""
        now = datetime.now(tz=timezone.utc)
        product = ProductEntry(
            id=1,
            path="/data/images/test.fits",
            ms_path="/data/ms/test.ms",
            created_at=now,
            type="image",
            beam_major_arcsec=12.5,
            noise_jy=0.002,
            pbcor=True,
        )
        assert product.id == 1
        assert product.type == "image"
        assert product.pbcor is True

    def test_product_entry_optional_fields(self):
        """Test ProductEntry with optional fields."""
        now = datetime.now(tz=timezone.utc)
        product = ProductEntry(
            id=1,
            path="/data/images/test.fits",
            ms_path="/data/ms/test.ms",
            created_at=now,
            type="image",
        )
        assert product.beam_major_arcsec is None
        assert product.noise_jy is None
        assert product.pbcor is False


class TestImageInfo:
    """Test ImageInfo model."""

    def test_valid_image_info(self):
        """Test valid ImageInfo creation."""
        now = datetime.now(tz=timezone.utc)
        image = ImageInfo(
            id=1,
            path="/data/images/test.fits",
            ms_path="/data/ms/test.ms",
            created_at=now,
            type="image",
            beam_major_arcsec=12.5,
            noise_jy=0.002,
            pbcor=True,
            center_ra_deg=188.7,
            center_dec_deg=42.1,
        )
        assert image.id == 1
        assert image.type == "image"
        assert image.center_ra_deg == 188.7


class TestImageList:
    """Test ImageList model."""

    def test_valid_image_list(self):
        """Test valid ImageList creation."""
        now = datetime.now(tz=timezone.utc)
        image = ImageInfo(
            id=1,
            path="/data/images/test.fits",
            ms_path="/data/ms/test.ms",
            created_at=now,
            type="image",
        )
        image_list = ImageList(items=[image], total=1)
        assert len(image_list.items) == 1
        assert image_list.total == 1


class TestSourceFluxPoint:
    """Test SourceFluxPoint model."""

    def test_valid_source_flux_point(self):
        """Test valid SourceFluxPoint creation."""
        point = SourceFluxPoint(
            mjd=60238.5,
            time="2025-10-20T07:12:00",
            flux_jy=0.198,
            flux_err_jy=0.0052,
            image_id="/stage/.../image.fits",
        )
        assert point.mjd == 60238.5
        assert point.flux_jy == 0.198

    def test_source_flux_point_optional_error(self):
        """Test SourceFluxPoint with optional error."""
        point = SourceFluxPoint(
            mjd=60238.5,
            time="2025-10-20T07:12:00",
            flux_jy=0.198,
        )
        assert point.flux_err_jy is None


class TestSourceTimeseries:
    """Test SourceTimeseries model."""

    def test_valid_source_timeseries(self):
        """Test valid SourceTimeseries creation."""
        point = SourceFluxPoint(
            mjd=60238.5,
            time="2025-10-20T07:12:00",
            flux_jy=0.198,
        )
        timeseries = SourceTimeseries(
            source_id="NVSS J123456.7+420312",
            ra_deg=188.73625,
            dec_deg=42.05333,
            catalog="NVSS",
            flux_points=[point],
            mean_flux_jy=0.153,
            std_flux_jy=0.012,
            chi_sq_nu=8.3,
            is_variable=True,
        )
        assert timeseries.source_id == "NVSS J123456.7+420312"
        assert len(timeseries.flux_points) == 1
        assert timeseries.is_variable is True


class TestSourceSearchResponse:
    """Test SourceSearchResponse model."""

    def test_valid_source_search_response(self):
        """Test valid SourceSearchResponse creation."""
        point = SourceFluxPoint(
            mjd=60238.5,
            time="2025-10-20T07:12:00",
            flux_jy=0.198,
        )
        timeseries = SourceTimeseries(
            source_id="NVSS J123456.7+420312",
            ra_deg=188.73625,
            dec_deg=42.05333,
            catalog="NVSS",
            flux_points=[point],
            mean_flux_jy=0.153,
            std_flux_jy=0.012,
            chi_sq_nu=8.3,
            is_variable=True,
        )
        response = SourceSearchResponse(sources=[timeseries], total=1)
        assert len(response.sources) == 1
        assert response.total == 1


class TestSourceDetail:
    """Test SourceDetail model."""

    def test_valid_source_detail(self):
        """Test valid SourceDetail creation."""
        metrics = VariabilityMetrics(
            source_id="NVSS J123456.7+420312",
            v=0.25,
            eta=0.12,
            vs_mean=0.15,
            m_mean=0.10,
            n_epochs=142,
        )
        detail = SourceDetail(
            id="NVSS J123456.7+420312",
            name="NVSS J123456.7+420312",
            ra_deg=188.73625,
            dec_deg=42.05333,
            catalog="NVSS",
            n_meas=142,
            n_meas_forced=15,
            mean_flux_jy=0.153,
            std_flux_jy=0.012,
            max_snr=38.1,
            is_variable=True,
            ese_probability=0.75,
            variability_metrics=metrics,
        )
        assert detail.id == "NVSS J123456.7+420312"
        assert detail.n_meas == 142
        assert detail.variability_metrics is not None


class TestVariabilityMetrics:
    """Test VariabilityMetrics model."""

    def test_valid_variability_metrics(self):
        """Test valid VariabilityMetrics creation."""
        metrics = VariabilityMetrics(
            source_id="NVSS J123456.7+420312",
            v=0.25,
            eta=0.12,
            vs_mean=0.15,
            m_mean=0.10,
            n_epochs=142,
        )
        assert metrics.v == 0.25
        assert metrics.eta == 0.12
        assert metrics.n_epochs == 142
        # Note: VariabilityMetrics doesn't have is_variable field


class TestESECandidate:
    """Test ESECandidate model."""

    def test_valid_ese_candidate(self):
        """Test valid ESECandidate creation."""
        candidate = ESECandidate(
            id=1,
            source_id="NVSS J123456.7+420312",
            ra_deg=188.73625,
            dec_deg=42.05333,
            first_detection_at="2025-10-20T07:12:00",
            last_detection_at="2025-10-20T07:12:00",
            max_sigma_dev=7.8,
            current_flux_jy=0.153,
            baseline_flux_jy=0.145,
            status="active",
        )
        assert candidate.id == 1
        assert candidate.max_sigma_dev == 7.8
        assert candidate.status == "active"


class TestMosaic:
    """Test Mosaic model."""

    def test_valid_mosaic(self):
        """Test valid Mosaic creation."""
        mosaic = Mosaic(
            id=1,
            name="test_mosaic",
            path="/data/mosaics/test.fits",
            start_mjd=60238.5,
            end_mjd=60238.542,
            start_time="2025-10-20T07:12:00",
            end_time="2025-10-20T07:13:00",
            created_at="2025-10-20T07:15:00",
            status="completed",
            image_count=12,
            source_count=142,
            noise_jy=0.00085,
        )
        assert mosaic.id == 1
        assert mosaic.image_count == 12
        assert mosaic.source_count == 142


class TestLightCurveData:
    """Test LightCurveData model."""

    def test_valid_light_curve_data(self):
        """Test valid LightCurveData creation."""
        point = SourceFluxPoint(
            mjd=60238.5,
            time="2025-10-20T07:12:00",
            flux_jy=0.198,
        )
        lightcurve = LightCurveData(
            source_id="NVSS J123456.7+420312",
            ra_deg=188.73625,
            dec_deg=42.05333,
            flux_points=[point],
        )
        assert lightcurve.source_id == "NVSS J123456.7+420312"
        assert len(lightcurve.flux_points) == 1


class TestModelValidationErrors:
    """Test model validation error handling."""

    def test_queue_stats_missing_field(self):
        """Test QueueStats with missing required field."""
        with pytest.raises(ValidationError):
            QueueStats(
                total=10,
                pending=2,
                # Missing in_progress, failed, completed, collecting
            )

    def test_image_info_missing_required(self):
        """Test ImageInfo with missing required field."""
        with pytest.raises(ValidationError):
            ImageInfo(
                id=1,
                # Missing path, ms_path, type
            )

    def test_source_flux_point_invalid_mjd(self):
        """Test SourceFluxPoint with invalid MJD."""
        # Should accept any float, but test with negative value
        point = SourceFluxPoint(
            mjd=-1.0,  # Invalid but model accepts it
            time="2025-10-20T07:12:00",
            flux_jy=0.198,
        )
        assert point.mjd == -1.0  # Model doesn't validate range
