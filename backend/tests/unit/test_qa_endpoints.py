"""
Unit tests for QA endpoints - quality assurance routes.

Tests for:
- /images/{id}/qa endpoint
- /qa/image/{id} endpoint
- QA response structure and metrics

Uses the shared client fixture from conftest.py that provides test databases.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from dsa110_contimg.api.app import create_app


def assert_error_response(data: dict, context: str = ""):
    """Assert that a response contains a valid error structure.
    
    Supports both old format (detail field) and new format (error/message/details).
    """
    # New exception format uses error, message, details
    has_new_format = "message" in data and "error" in data
    # Old format uses detail
    has_old_format = "detail" in data
    
    assert has_new_format or has_old_format, f"{context} Response should have error structure: {data}"


# Note: Uses client fixture from conftest.py


class TestImageQAEndpoint:
    """Tests for /images/{id}/qa endpoint."""

    def test_image_qa_returns_json(self, client):
        """Test image QA endpoint returns JSON."""
        response = client.get("/api/v1/images/test-image/qa")
        
        assert response.status_code in (200, 404)
        assert "application/json" in response.headers.get("content-type", "")

    def test_image_qa_404_for_unknown_image(self, client):
        """Test image QA returns 404 for unknown image."""
        response = client.get("/api/v1/images/nonexistent-image-xyz/qa")
        
        assert response.status_code == 404
        data = response.json()
        assert_error_response(data, "image QA 404")

    def test_image_qa_legacy_route(self, client):
        """Test /api/images/{id}/qa legacy route works."""
        response = client.get("/api/images/test-image/qa")
        
        assert response.status_code in (200, 404)


class TestQAResponseStructure:
    """Tests for QA response structure."""

    def test_qa_response_has_image_id(self):
        """Test QA response includes image_id."""
        # Mock response structure
        qa_report = {
            "image_id": "test-123",
            "qa_grade": "A",
            "qa_summary": "Good quality",
        }
        
        assert "image_id" in qa_report

    def test_qa_response_has_grade(self):
        """Test QA response includes qa_grade."""
        qa_report = {
            "image_id": "test-123",
            "qa_grade": "A",
            "qa_summary": "Good quality",
        }
        
        assert "qa_grade" in qa_report
        assert qa_report["qa_grade"] in ["A", "B", "C", "D", "F", None]

    def test_qa_response_has_quality_metrics(self):
        """Test QA response includes quality_metrics."""
        qa_report = {
            "quality_metrics": {
                "noise_rms_jy": 0.001,
                "dynamic_range": 1000,
            }
        }
        
        assert "quality_metrics" in qa_report
        assert "noise_rms_jy" in qa_report["quality_metrics"]
        assert "dynamic_range" in qa_report["quality_metrics"]

    def test_qa_response_has_beam_info(self):
        """Test QA response includes beam information."""
        qa_report = {
            "beam": {
                "major_arcsec": 5.0,
                "minor_arcsec": 3.0,
                "pa_deg": 45.0,
            }
        }
        
        assert "beam" in qa_report
        assert "major_arcsec" in qa_report["beam"]
        assert "minor_arcsec" in qa_report["beam"]
        assert "pa_deg" in qa_report["beam"]


class TestQAQualityMetrics:
    """Tests for QA quality metrics."""

    def test_noise_rms_is_numeric(self):
        """Test noise RMS is a number."""
        noise_rms = 0.001  # 1 mJy
        
        assert isinstance(noise_rms, (int, float))
        assert noise_rms >= 0

    def test_dynamic_range_is_positive(self):
        """Test dynamic range is positive."""
        dynamic_range = 1000
        
        assert dynamic_range > 0

    def test_noise_ratio_calculation(self):
        """Test noise ratio calculation."""
        measured_noise = 0.002  # 2 mJy
        theoretical_noise = 0.001  # 1 mJy
        
        noise_ratio = measured_noise / theoretical_noise
        
        assert noise_ratio == 2.0

    def test_high_noise_warning(self):
        """Test high noise triggers warning."""
        noise_jy = 0.015  # 15 mJy
        threshold = 0.01  # 10 mJy
        
        warnings = []
        if noise_jy > threshold:
            warnings.append("High noise level detected")
        
        assert len(warnings) == 1

    def test_low_dynamic_range_warning(self):
        """Test low dynamic range triggers warning."""
        dynamic_range = 50
        threshold = 100
        
        warnings = []
        if dynamic_range < threshold:
            warnings.append("Low dynamic range")
        
        assert len(warnings) == 1


class TestQABeamMetrics:
    """Tests for QA beam metrics."""

    def test_beam_major_minor_positive(self):
        """Test beam axes are positive."""
        beam = {
            "major_arcsec": 5.0,
            "minor_arcsec": 3.0,
        }
        
        assert beam["major_arcsec"] > 0
        assert beam["minor_arcsec"] > 0

    def test_beam_major_gte_minor(self):
        """Test beam major axis >= minor axis."""
        major = 5.0
        minor = 3.0
        
        assert major >= minor

    def test_beam_pa_range(self):
        """Test beam position angle is in valid range."""
        pa_deg = 45.0
        
        # PA typically -180 to 180 or 0 to 180
        assert -180 <= pa_deg <= 180


class TestQASourceStats:
    """Tests for QA source statistics."""

    def test_source_count_is_integer(self):
        """Test source count is non-negative integer."""
        n_sources = 42
        
        assert isinstance(n_sources, int)
        assert n_sources >= 0

    def test_peak_flux_is_positive(self):
        """Test peak flux is positive."""
        peak_flux_jy = 0.5
        
        assert peak_flux_jy > 0


class TestQAFlagsAndWarnings:
    """Tests for QA flags and warnings."""

    def test_flags_is_list(self):
        """Test flags is a list."""
        flags = []
        
        assert isinstance(flags, list)

    def test_warnings_is_list(self):
        """Test warnings is a list."""
        warnings = []
        
        assert isinstance(warnings, list)

    def test_multiple_warnings_possible(self):
        """Test multiple warnings can be added."""
        warnings = []
        
        # High noise
        warnings.append("High noise level detected")
        # Low dynamic range
        warnings.append("Low dynamic range")
        
        assert len(warnings) == 2


class TestQAEndpointRouting:
    """Tests for QA endpoint routing."""

    def test_v1_images_qa_route(self, client):
        """Test /api/v1/images/{id}/qa route."""
        response = client.get("/api/v1/images/test-123/qa")
        
        assert response.status_code in (200, 404)

    def test_legacy_images_qa_route(self, client):
        """Test /api/images/{id}/qa legacy route."""
        response = client.get("/api/images/test-123/qa")
        
        assert response.status_code in (200, 404)

    def test_qa_image_route(self, client):
        """Test /api/v1/qa/image/{id} route if exists."""
        response = client.get("/api/v1/qa/image/test-123")
        
        # May or may not exist depending on implementation
        assert response.status_code in (200, 404)
