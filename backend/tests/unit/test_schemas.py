"""
Unit tests for API Pydantic schemas.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError as PydanticValidationError

from dsa110_contimg.api.schemas import (
    ImageDetailResponse,
    ImageListResponse,
    MSDetailResponse,
    SourceDetailResponse,
    SourceListResponse,
    JobListResponse,
    ProvenanceResponse,
    CalibratorMatch,
    ContributingImage,
    QAMetrics,
    QAReportResponse,
    LightcurvePoint,
    LightcurveResponse,
    VariabilityResponse,
    DashboardStats,
)


class TestImageSchemas:
    """Tests for image-related schemas."""
    
    def test_image_detail_response_required_fields(self):
        """Test ImageDetailResponse requires id and path."""
        response = ImageDetailResponse(id="img-001", path="/data/images/img.fits")
        assert response.id == "img-001"
        assert response.path == "/data/images/img.fits"
    
    def test_image_detail_response_optional_fields(self):
        """Test ImageDetailResponse optional fields have defaults."""
        response = ImageDetailResponse(id="img-001", path="/data/images/img.fits")
        assert response.ms_path is None
        assert response.qa_grade is None
        assert response.run_id is None
    
    def test_image_detail_response_qa_grade_validation(self):
        """Test qa_grade accepts only valid values."""
        response = ImageDetailResponse(
            id="img-001", 
            path="/data/images/img.fits",
            qa_grade="good"
        )
        assert response.qa_grade == "good"
        
        response = ImageDetailResponse(
            id="img-001", 
            path="/data/images/img.fits",
            qa_grade="warn"
        )
        assert response.qa_grade == "warn"
    
    def test_image_list_response_fields(self):
        """Test ImageListResponse fields."""
        response = ImageListResponse(
            id="img-001",
            path="/data/images/img.fits",
            qa_grade="good",
            created_at=datetime(2025, 1, 15, 10, 30),
            run_id="job-123"
        )
        assert response.id == "img-001"
        assert response.qa_grade == "good"
        assert response.run_id == "job-123"


class TestMSSchemas:
    """Tests for Measurement Set schemas."""
    
    def test_ms_detail_response_required_fields(self):
        """Test MSDetailResponse requires path."""
        response = MSDetailResponse(path="/data/ms/obs.ms")
        assert response.path == "/data/ms/obs.ms"
    
    def test_calibrator_match_fields(self):
        """Test CalibratorMatch schema."""
        match = CalibratorMatch(cal_table="/data/cal/flux.tbl", type="flux")
        assert match.cal_table == "/data/cal/flux.tbl"
        assert match.type == "flux"
    
    def test_ms_detail_with_calibrators(self):
        """Test MSDetailResponse with calibrator matches."""
        response = MSDetailResponse(
            path="/data/ms/obs.ms",
            calibrator_matches=[
                CalibratorMatch(cal_table="/data/cal/flux.tbl", type="flux"),
                CalibratorMatch(cal_table="/data/cal/phase.tbl", type="phase"),
            ]
        )
        assert len(response.calibrator_matches) == 2


class TestSourceSchemas:
    """Tests for source catalog schemas."""
    
    def test_source_detail_required_fields(self):
        """Test SourceDetailResponse requires id and coordinates."""
        response = SourceDetailResponse(
            id="src-001",
            ra_deg=180.0,
            dec_deg=-30.0
        )
        assert response.id == "src-001"
        assert response.ra_deg == 180.0
        assert response.dec_deg == -30.0
    
    def test_source_list_response_defaults(self):
        """Test SourceListResponse default values."""
        response = SourceListResponse(
            id="src-001",
            ra_deg=180.0,
            dec_deg=-30.0
        )
        assert response.num_images == 0
        assert response.image_id is None
    
    def test_contributing_image_fields(self):
        """Test ContributingImage schema."""
        image = ContributingImage(
            image_id="img-001",
            path="/data/images/img.fits",
            qa_grade="good"
        )
        assert image.image_id == "img-001"
        assert image.qa_grade == "good"


class TestJobSchemas:
    """Tests for job-related schemas."""
    
    def test_job_list_response_required_fields(self):
        """Test JobListResponse requires run_id and status."""
        response = JobListResponse(run_id="job-123", status="completed")
        assert response.run_id == "job-123"
        assert response.status == "completed"
    
    def test_job_list_response_status_validation(self):
        """Test status accepts only valid values."""
        for status in ["pending", "running", "completed", "failed"]:
            response = JobListResponse(run_id="job-123", status=status)
            assert response.status == status


class TestProvenanceSchema:
    """Tests for provenance response schema."""
    
    def test_provenance_required_fields(self):
        """Test ProvenanceResponse requires run_id."""
        response = ProvenanceResponse(run_id="job-123")
        assert response.run_id == "job-123"
    
    def test_provenance_urls(self):
        """Test ProvenanceResponse URL fields."""
        response = ProvenanceResponse(
            run_id="job-123",
            logs_url="/api/logs/job-123",
            qa_url="/api/qa/job/job-123",
            ms_url="/api/ms/path/to/ms/metadata"
        )
        assert response.logs_url == "/api/logs/job-123"


class TestQASchemas:
    """Tests for QA-related schemas."""
    
    def test_qa_metrics_fields(self):
        """Test QAMetrics schema."""
        metrics = QAMetrics(
            noise_jy=0.00035,
            dynamic_range=1200.0,
            n_sources=42
        )
        assert metrics.noise_jy == 0.00035
        assert metrics.dynamic_range == 1200.0
        assert metrics.n_sources == 42
    
    def test_qa_report_response_fields(self):
        """Test QAReportResponse schema."""
        response = QAReportResponse(
            entity_id="img-001",
            entity_type="image",
            qa_grade="good",
            qa_summary="RMS 0.35 mJy",
            warnings=["High RFI in subband 5"]
        )
        assert response.entity_id == "img-001"
        assert response.entity_type == "image"
        assert len(response.warnings) == 1
    
    def test_qa_report_entity_type_validation(self):
        """Test entity_type accepts only valid values."""
        for entity_type in ["image", "ms", "job", "source"]:
            response = QAReportResponse(
                entity_id="test-001",
                entity_type=entity_type
            )
            assert response.entity_type == entity_type


class TestLightcurveSchemas:
    """Tests for lightcurve schemas."""
    
    def test_lightcurve_point_fields(self):
        """Test LightcurvePoint schema."""
        point = LightcurvePoint(
            mjd=60000.5,
            flux_jy=0.001,
            flux_err_jy=0.0001,
            image_id="img-001"
        )
        assert point.mjd == 60000.5
        assert point.flux_jy == 0.001
        assert point.flux_err_jy == 0.0001
    
    def test_lightcurve_response_fields(self):
        """Test LightcurveResponse schema."""
        response = LightcurveResponse(
            source_id="src-001",
            data_points=[
                LightcurvePoint(mjd=60000.5, flux_jy=0.001),
                LightcurvePoint(mjd=60001.5, flux_jy=0.0012),
            ]
        )
        assert response.source_id == "src-001"
        assert len(response.data_points) == 2


class TestVariabilitySchema:
    """Tests for variability response schema."""
    
    def test_variability_response_fields(self):
        """Test VariabilityResponse schema."""
        response = VariabilityResponse(
            source_id="src-001",
            n_epochs=10,
            mean_flux_jy=0.001,
            std_flux_jy=0.0002,
            variability_index=0.2,
            is_variable=True
        )
        assert response.source_id == "src-001"
        assert response.n_epochs == 10
        assert response.is_variable is True
    
    def test_variability_response_defaults(self):
        """Test VariabilityResponse default values."""
        response = VariabilityResponse(source_id="src-001", n_epochs=5)
        assert response.is_variable is False
        assert response.mean_flux_jy is None


class TestDashboardStatsSchema:
    """Tests for dashboard statistics schema."""
    
    def test_dashboard_stats_required_fields(self):
        """Test DashboardStats required fields."""
        stats = DashboardStats(
            total_images=1000,
            total_sources=5000,
            total_jobs=200,
            total_ms=150
        )
        assert stats.total_images == 1000
        assert stats.total_sources == 5000
    
    def test_dashboard_stats_defaults(self):
        """Test DashboardStats default values."""
        stats = DashboardStats(
            total_images=1000,
            total_sources=5000,
            total_jobs=200,
            total_ms=150
        )
        assert stats.recent_images == 0
        assert stats.recent_jobs == 0
        assert stats.qa_good == 0
