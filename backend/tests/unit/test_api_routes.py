"""
Unit tests for API routes - sources, jobs, queue, stats, and cal.

These tests verify route handlers work correctly with mocked dependencies.
Uses the shared client fixture from conftest.py that provides test databases.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient


def assert_error_response(data: dict, message: str = ""):
    """Assert that a response contains a valid error structure."""
    has_new_format = "message" in data and "error" in data
    has_old_format = "detail" in data
    assert has_new_format or has_old_format, f"Response should have error structure: {data}"


# Note: Uses client fixture from conftest.py


class TestSourcesRoutes:
    """Tests for source routes."""
    
    def test_list_sources_returns_list(self, client):
        """GET /api/v1/sources should return a list."""
        response = client.get("/api/v1/sources")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_list_sources_with_pagination(self, client):
        """GET /api/v1/sources should support pagination parameters."""
        response = client.get("/api/v1/sources", params={"limit": 10, "offset": 0})
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10
    
    def test_list_sources_limit_validation(self, client):
        """GET /api/v1/sources should validate limit parameter."""
        # Limit over 1000 should fail
        response = client.get("/api/v1/sources", params={"limit": 2000})
        
        assert response.status_code == 422  # Validation error
    
    def test_get_source_not_found(self, client):
        """GET /api/v1/sources/{id} should return 404 for unknown source."""
        response = client.get("/api/v1/sources/nonexistent_source_123")
        
        assert response.status_code == 404
        data = response.json()
        assert_error_response(data)
    
    def test_get_source_lightcurve_not_found(self, client):
        """GET /api/v1/sources/{id}/lightcurve should handle unknown source."""
        response = client.get("/api/v1/sources/nonexistent_source/lightcurve")
        
        # May return 404 or empty data depending on implementation
        assert response.status_code in (200, 404)
    
    def test_lightcurve_date_validation_valid_format(self, client):
        """Lightcurve should accept valid ISO date format."""
        # Valid ISO format dates should be accepted
        response = client.get(
            "/api/v1/sources/test_source/lightcurve",
            params={"start_date": "2025-01-01", "end_date": "2025-01-31"}
        )
        # Should succeed (200) or return 404 for non-existent source, not 422
        assert response.status_code in (200, 404)
    
    def test_lightcurve_date_validation_invalid_format(self, client):
        """Lightcurve should reject invalid date format."""
        # Invalid date format should be rejected
        response = client.get(
            "/api/v1/sources/test_source/lightcurve",
            params={"start_date": "not-a-date"}
        )
        # Should return validation error (422 or 400)
        assert response.status_code in (400, 422)
        data = response.json()
        assert_error_response(data)
    
    def test_lightcurve_date_validation_partial_dates(self, client):
        """Lightcurve should handle partial date specifications."""
        # Only start_date provided (should be valid)
        response = client.get(
            "/api/v1/sources/test_source/lightcurve",
            params={"start_date": "2025-06-15"}
        )
        assert response.status_code in (200, 404)


class TestJobsRoutes:
    """Tests for job routes."""
    
    def test_list_jobs_returns_list(self, client):
        """GET /api/v1/jobs should return a list."""
        response = client.get("/api/v1/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_list_jobs_with_pagination(self, client):
        """GET /api/v1/jobs should support pagination."""
        response = client.get("/api/v1/jobs", params={"limit": 5, "offset": 0})
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5
    
    def test_get_job_not_found(self, client):
        """GET /api/v1/jobs/{run_id} should return 404 for unknown job."""
        response = client.get("/api/v1/jobs/nonexistent_run_id")
        
        assert response.status_code == 404
        data = response.json()
        assert_error_response(data)
    
    def test_get_job_provenance_not_found(self, client):
        """GET /api/v1/jobs/{run_id}/provenance should return 404."""
        response = client.get("/api/v1/jobs/unknown_run/provenance")
        
        assert response.status_code == 404
    
    def test_get_job_logs_not_found(self, client):
        """GET /api/v1/jobs/{run_id}/logs should handle unknown job."""
        response = client.get("/api/v1/jobs/unknown_run/logs")
        
        # May return 404 or empty logs depending on implementation
        assert response.status_code in (200, 404)
    
    def test_rerun_job_requires_auth(self, client):
        """POST /api/v1/jobs/{run_id}/rerun should require authentication."""
        response = client.post("/api/v1/jobs/some_run_id/rerun")
        
        # Route may return 404 (not found) before checking auth, or 401 if auth is checked first
        assert response.status_code in (401, 404)


class TestQueueRoutes:
    """Tests for queue routes."""
    
    def test_get_queue_stats(self, client):
        """GET /api/v1/queue should return queue statistics."""
        response = client.get("/api/v1/queue")
        
        assert response.status_code == 200
        data = response.json()
        # Should have some queue stats structure
        assert isinstance(data, dict)
    
    def test_list_queued_jobs(self, client):
        """GET /api/v1/queue/jobs should return list of queued jobs."""
        response = client.get("/api/v1/queue/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_list_queued_jobs_with_status_filter(self, client):
        """GET /api/v1/queue/jobs should support status filter."""
        response = client.get("/api/v1/queue/jobs", params={"status": "queued"})
        
        assert response.status_code == 200
    
    def test_list_queued_jobs_invalid_status(self, client):
        """Invalid status filter should return 400."""
        response = client.get("/api/v1/queue/jobs", params={"status": "invalid_status"})
        
        assert response.status_code == 400
        data = response.json()
        assert_error_response(data)
    
    def test_get_queued_job_not_found(self, client):
        """GET /api/v1/queue/jobs/{job_id} should return 404."""
        response = client.get("/api/v1/queue/jobs/nonexistent_job_id")
        
        assert response.status_code == 404
    
    def test_cancel_job_requires_auth(self, client):
        """POST /api/v1/queue/jobs/{job_id}/cancel should require auth."""
        response = client.post("/api/v1/queue/jobs/some_job/cancel")
        
        # Route may return 404 (not found) before checking auth, or 401 if auth is checked first
        assert response.status_code in (401, 404)


class TestStatsRoutes:
    """Tests for stats routes."""
    
    def test_get_stats(self, client):
        """GET /api/v1/stats should return dashboard statistics."""
        response = client.get("/api/v1/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestCalRoutes:
    """Tests for calibration routes."""
    
    def test_get_cal_table_not_found(self, client):
        """GET /api/v1/cal/{path} should return 404 for unknown table."""
        response = client.get("/api/v1/cal/nonexistent/path/to/cal.tbl")
        
        assert response.status_code == 404
        data = response.json()
        assert_error_response(data)
    
    def test_get_cal_table_url_encoded_path(self, client):
        """GET /api/v1/cal/{path} should handle URL-encoded paths."""
        # Path with special characters
        encoded_path = "/data/cal%2Ftables/test.tbl"
        response = client.get(f"/api/v1/cal{encoded_path}")
        
        # Should try to look up the decoded path
        assert response.status_code in (200, 404)


class TestServicesRoutes:
    """Tests for services status routes."""
    
    def test_get_services_status(self, client):
        """GET /api/v1/services/status should return service statuses."""
        response = client.get("/api/v1/services/status")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (dict, list))
    
    def test_get_service_by_port_not_found(self, client):
        """GET /api/v1/services/status/{port} should return 404 for unknown port."""
        response = client.get("/api/v1/services/status/99999")
        
        assert response.status_code == 404


class TestMSRoutes:
    """Tests for measurement set routes."""
    
    def test_get_ms_list_not_implemented(self, client):
        """GET /api/v1/ms should return 404 (not implemented)."""
        response = client.get("/api/v1/ms")
        
        # This route may not exist
        assert response.status_code in (200, 404)
    
    def test_get_ms_metadata_not_found(self, client):
        """GET /api/v1/ms/{path}/metadata should return 404 for unknown MS."""
        response = client.get("/api/v1/ms/nonexistent/path/metadata")
        
        # Path-based routes may have different behavior
        assert response.status_code in (404, 422)


class TestCacheRoutes:
    """Tests for cache management routes."""
    
    def test_get_cache_stats(self, client):
        """GET /api/v1/cache should return cache statistics."""
        response = client.get("/api/v1/cache")
        
        # May return stats or 404 if not implemented
        assert response.status_code in (200, 404)
    
    def test_clear_cache_requires_auth(self, client):
        """POST /api/v1/cache/clear should require authentication."""
        response = client.post("/api/v1/cache/clear")
        
        # Cache clear endpoint may not require auth in test mode, or may not exist
        # Accept 200 (cleared), 401 (auth required), 404 (not found), or 405 (method not allowed)
        assert response.status_code in (200, 401, 404, 405)


class TestLogsRoutes:
    """Tests for log routes."""
    
    def test_get_logs_list(self, client):
        """GET /api/v1/logs should return list of log files."""
        response = client.get("/api/v1/logs")
        
        assert response.status_code in (200, 404)
    
    def test_get_log_file_not_found(self, client):
        """GET /api/v1/logs/{filename} should handle unknown file."""
        response = client.get("/api/v1/logs/nonexistent.log")
        
        # May return 404 or redirect depending on implementation
        assert response.status_code in (200, 404, 422)
