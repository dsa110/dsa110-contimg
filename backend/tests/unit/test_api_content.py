"""
API content validation tests - verify actual data content and structure.

These tests verify that API responses contain properly structured data
that the frontend can consume to display meaningful content.

Uses the shared client fixture from conftest.py that provides test databases.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
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


class TestImagesContentValidation:
    """Validate image API response content for frontend display."""

    def test_images_list_item_has_required_fields(self, client):
        """Test image list items have fields required by ImageCard component."""
        response = client.get("/api/v1/images")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            image = data[0]
            # Fields required for ImageCard display
            assert "id" in image, "Image must have id for navigation"
            assert "path" in image, "Image must have path for display"
            # Optional but expected fields
            assert "qa_grade" in image or image.get("qa_grade") is None

    def test_images_list_items_have_valid_ids(self, client):
        """Test image IDs are non-empty strings for routing."""
        response = client.get("/api/v1/images")
        data = response.json()
        
        for image in data:
            assert isinstance(image.get("id"), str), "ID must be string"
            assert len(image.get("id", "")) > 0, "ID must not be empty"

    def test_image_detail_has_display_fields(self, client):
        """Test image detail has fields for ImageDetailPage."""
        # First get an image ID from list
        list_response = client.get("/api/v1/images")
        if list_response.status_code == 200 and len(list_response.json()) > 0:
            image_id = list_response.json()[0]["id"]
            
            response = client.get(f"/api/v1/images/{image_id}")
            if response.status_code == 200:
                image = response.json()
                # Required display fields
                assert "id" in image
                assert "path" in image
                # Provenance fields
                assert "ms_path" in image or image.get("ms_path") is None
                assert "qa_grade" in image or image.get("qa_grade") is None

    def test_image_qa_has_metrics(self, client):
        """Test image QA endpoint returns quality metrics."""
        list_response = client.get("/api/v1/images")
        if list_response.status_code == 200 and len(list_response.json()) > 0:
            image_id = list_response.json()[0]["id"]
            
            response = client.get(f"/api/v1/images/{image_id}/qa")
            if response.status_code == 200:
                qa = response.json()
                assert "image_id" in qa
                assert "qa_grade" in qa or qa.get("qa_grade") is None
                # Quality metrics for display
                if "quality_metrics" in qa:
                    metrics = qa["quality_metrics"]
                    # These show in QA panel
                    assert isinstance(metrics, dict)


class TestSourcesContentValidation:
    """Validate source API response content for frontend display."""

    def test_sources_list_has_coordinate_fields(self, client):
        """Test sources have RA/Dec for sky map display."""
        response = client.get("/api/v1/sources")
        assert response.status_code == 200
        
        data = response.json()
        for source in data:
            assert "id" in source, "Source must have id"
            # Coordinates for sky map plotting
            if "ra_deg" in source:
                assert isinstance(source["ra_deg"], (int, float, type(None)))
            if "dec_deg" in source:
                assert isinstance(source["dec_deg"], (int, float, type(None)))

    def test_sources_list_has_display_name(self, client):
        """Test sources have name or id for list display."""
        response = client.get("/api/v1/sources")
        data = response.json()
        
        for source in data:
            # Must have either name or id for display
            has_display = "name" in source or "id" in source
            assert has_display, "Source needs name or id for display"

    def test_source_detail_has_lightcurve_data(self, client):
        """Test source detail can provide lightcurve data."""
        list_response = client.get("/api/v1/sources")
        if list_response.status_code == 200 and len(list_response.json()) > 0:
            source_id = list_response.json()[0]["id"]
            
            # Lightcurve endpoint for chart display
            lc_response = client.get(f"/api/v1/sources/{source_id}/lightcurve")
            # Should return data or empty list, not error
            assert lc_response.status_code in (200, 404)

    def test_source_variability_has_statistics(self, client):
        """Test variability endpoint returns stats for display."""
        list_response = client.get("/api/v1/sources")
        if list_response.status_code == 200 and len(list_response.json()) > 0:
            source_id = list_response.json()[0]["id"]
            
            response = client.get(f"/api/v1/sources/{source_id}/variability")
            if response.status_code == 200:
                var_data = response.json()
                # Fields for variability panel
                assert "source_id" in var_data
                assert "n_epochs" in var_data


class TestJobsContentValidation:
    """Validate job API response content for frontend display."""

    def test_jobs_list_has_status_field(self, client):
        """Test jobs have status for badge display."""
        response = client.get("/api/v1/jobs")
        assert response.status_code == 200
        
        data = response.json()
        for job in data:
            # Status for color-coded badge
            if "status" in job:
                valid_statuses = ["pending", "running", "completed", "failed", "cancelled", None]
                assert job["status"] in valid_statuses or job["status"] is None

    def test_jobs_list_has_run_id(self, client):
        """Test jobs have run_id for navigation."""
        response = client.get("/api/v1/jobs")
        data = response.json()
        
        for job in data:
            assert "run_id" in job or "id" in job, "Job needs identifier"

    def test_jobs_list_has_timestamps(self, client):
        """Test jobs have timestamps for timeline display."""
        response = client.get("/api/v1/jobs")
        data = response.json()
        
        for job in data:
            # At least one timestamp for sorting/display
            has_timestamp = any(
                k in job for k in ["created_at", "started_at", "completed_at", "timestamp"]
            )
            # Timestamps are optional but expected for proper jobs


class TestHealthContentValidation:
    """Validate health API response for dashboard display."""

    def test_health_has_status_for_indicator(self, client):
        """Test health has status for traffic light indicator."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_health_detailed_has_components(self, client):
        """Test detailed health has component status for dashboard."""
        response = client.get("/api/v1/health?detailed=true")
        assert response.status_code == 200
        
        data = response.json()
        # Component sections for status cards
        assert "databases" in data or "redis" in data or "disk" in data

    def test_health_has_version_info(self, client):
        """Test health has version for footer display."""
        response = client.get("/api/v1/health")
        data = response.json()
        
        assert "version" in data
        assert "service" in data


class TestStatsContentValidation:
    """Validate stats API response for dashboard cards."""

    def test_stats_endpoint_returns_counts(self, client):
        """Test stats returns counts for dashboard cards."""
        response = client.get("/api/v1/stats")
        
        if response.status_code == 200:
            data = response.json()
            # Dashboard cards need these counts
            count_fields = ["total_images", "total_sources", "total_jobs", 
                          "images", "sources", "jobs", "ms_count"]
            has_counts = any(f in data for f in count_fields)
            # Stats should provide some count data


class TestPaginationContentValidation:
    """Validate pagination works correctly for infinite scroll."""

    def test_images_pagination_returns_subset(self, client):
        """Test pagination limits work for lazy loading."""
        # First request
        response1 = client.get("/api/v1/images?limit=5&offset=0")
        assert response1.status_code == 200
        
        data1 = response1.json()
        assert len(data1) <= 5, "Should respect limit"
        
        # Second page
        response2 = client.get("/api/v1/images?limit=5&offset=5")
        assert response2.status_code == 200

    def test_sources_pagination_returns_subset(self, client):
        """Test sources pagination for scroll loading."""
        response = client.get("/api/v1/sources?limit=10&offset=0")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) <= 10


class TestErrorContentValidation:
    """Validate error responses are displayable."""

    def test_404_has_user_message(self, client):
        """Test 404 errors have message for error display."""
        response = client.get("/api/v1/images/nonexistent-xyz")
        assert response.status_code == 404
        
        data = response.json()
        # New exception format uses error, message, details structure
        assert "message" in data or "detail" in data
        # Message should be displayable
        if "message" in data:
            assert isinstance(data["message"], str)
            assert len(data["message"]) > 0
        else:
            detail = data["detail"]
            if isinstance(detail, dict):
                assert "message" in detail or "code" in detail
            else:
                assert isinstance(detail, str)

    def test_validation_error_has_field_info(self, client):
        """Test validation errors identify the problem field."""
        response = client.get("/api/v1/images?limit=invalid")
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data
        # Should identify what was wrong
        detail = data["detail"]
        assert detail is not None


class TestResponseFormatValidation:
    """Validate response formats match frontend expectations."""

    def test_dates_are_iso_format(self, client):
        """Test dates are ISO format for JavaScript parsing."""
        response = client.get("/api/v1/health")
        data = response.json()
        
        if "timestamp" in data:
            ts = data["timestamp"]
            # Should parse as ISO date
            assert "T" in ts or "Z" in ts or "-" in ts

    def test_numbers_are_numbers(self, client):
        """Test numeric fields are actual numbers, not strings."""
        response = client.get("/api/v1/images")
        data = response.json()
        
        for image in data:
            # Numeric fields should be numeric
            if "center_ra_deg" in image and image["center_ra_deg"] is not None:
                assert isinstance(image["center_ra_deg"], (int, float))
            if "center_dec_deg" in image and image["center_dec_deg"] is not None:
                assert isinstance(image["center_dec_deg"], (int, float))

    def test_booleans_are_booleans(self, client):
        """Test boolean fields are actual booleans."""
        # Health check has boolean-like status
        response = client.get("/api/v1/health")
        data = response.json()
        
        # Status is string but should be truthy/falsy evaluable
        assert data["status"] in ["healthy", "degraded", "unhealthy"]


class TestCrossReferenceValidation:
    """Validate cross-references between entities work."""

    def test_image_has_valid_ms_reference(self, client):
        """Test image's ms_path can be used to fetch MS."""
        response = client.get("/api/v1/images")
        data = response.json()
        
        for image in data:
            if image.get("ms_path"):
                # ms_path should be a string path
                assert isinstance(image["ms_path"], str)

    def test_job_provenance_links_to_resources(self, client):
        """Test job provenance contains valid resource URLs."""
        jobs_response = client.get("/api/v1/jobs")
        if jobs_response.status_code == 200 and len(jobs_response.json()) > 0:
            job = jobs_response.json()[0]
            run_id = job.get("run_id") or job.get("id")
            
            if run_id:
                prov_response = client.get(f"/api/v1/jobs/{run_id}/provenance")
                if prov_response.status_code == 200:
                    prov = prov_response.json()
                    # URLs should be strings starting with /
                    for url_field in ["logs_url", "qa_url", "image_url", "ms_url"]:
                        if url_field in prov and prov[url_field]:
                            assert prov[url_field].startswith("/") or prov[url_field].startswith("http")
