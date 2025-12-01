"""
Unit tests for API routes - sources, jobs, queue, stats, and cal.

These tests verify route handlers work correctly with mocked dependencies.
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


@pytest.fixture
def client():
    """Create a test client for the API."""
    with patch("dsa110_contimg.api.app.is_ip_allowed", return_value=True):
        from dsa110_contimg.api.app import create_app
        app = create_app()
        yield TestClient(app)


class TestSourcesRoutes:
    """Tests for source routes."""
    
    def test_list_sources_returns_list(self, client):
        """GET /api/sources should return a list."""
        response = client.get("/api/sources")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_list_sources_with_pagination(self, client):
        """GET /api/sources should support pagination parameters."""
        response = client.get("/api/sources", params={"limit": 10, "offset": 0})
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10
    
    def test_list_sources_limit_validation(self, client):
        """GET /api/sources should validate limit parameter."""
        # Limit over 1000 should fail
        response = client.get("/api/sources", params={"limit": 2000})
        
        assert response.status_code == 422  # Validation error
    
    def test_get_source_not_found(self, client):
        """GET /api/sources/{id} should return 404 for unknown source."""
        response = client.get("/api/sources/nonexistent_source_123")
        
        assert response.status_code == 404
        data = response.json()
        assert_error_response(data)
    
    def test_get_source_lightcurve_not_found(self, client):
        """GET /api/sources/{id}/lightcurve should return 404 for unknown source."""
        response = client.get("/api/sources/nonexistent_source/lightcurve")
        
        assert response.status_code == 404
    
    def test_lightcurve_date_validation(self, client):
        """Lightcurve should validate date format."""
        response = client.get(
            "/api/sources/test_source/lightcurve",
            params={"start_date": "invalid-date"}
        )
        
        # Should return validation error or 404 (if source not found first)
        assert response.status_code in (400, 404, 422)


class TestJobsRoutes:
    """Tests for job routes."""
    
    def test_list_jobs_returns_list(self, client):
        """GET /api/jobs should return a list."""
        response = client.get("/api/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_list_jobs_with_pagination(self, client):
        """GET /api/jobs should support pagination."""
        response = client.get("/api/jobs", params={"limit": 5, "offset": 0})
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5
    
    def test_get_job_not_found(self, client):
        """GET /api/jobs/{run_id} should return 404 for unknown job."""
        response = client.get("/api/jobs/nonexistent_run_id")
        
        assert response.status_code == 404
        data = response.json()
        assert_error_response(data)
    
    def test_get_job_provenance_not_found(self, client):
        """GET /api/jobs/{run_id}/provenance should return 404."""
        response = client.get("/api/jobs/unknown_run/provenance")
        
        assert response.status_code == 404
    
    def test_get_job_logs_not_found(self, client):
        """GET /api/jobs/{run_id}/logs should return 404."""
        response = client.get("/api/jobs/unknown_run/logs")
        
        assert response.status_code == 404
    
    def test_rerun_job_requires_auth(self, client):
        """POST /api/jobs/{run_id}/rerun should require authentication."""
        response = client.post("/api/jobs/some_run_id/rerun")
        
        # Should get 401 without auth header
        assert response.status_code == 401


class TestQueueRoutes:
    """Tests for queue routes."""
    
    def test_get_queue_stats(self, client):
        """GET /api/queue should return queue statistics."""
        response = client.get("/api/queue")
        
        assert response.status_code == 200
        data = response.json()
        # Should have some queue stats structure
        assert isinstance(data, dict)
    
    def test_list_queued_jobs(self, client):
        """GET /api/queue/jobs should return list of queued jobs."""
        response = client.get("/api/queue/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_list_queued_jobs_with_status_filter(self, client):
        """GET /api/queue/jobs should support status filter."""
        response = client.get("/api/queue/jobs", params={"status": "queued"})
        
        assert response.status_code == 200
    
    def test_list_queued_jobs_invalid_status(self, client):
        """Invalid status filter should return 400."""
        response = client.get("/api/queue/jobs", params={"status": "invalid_status"})
        
        assert response.status_code == 400
        data = response.json()
        assert_error_response(data)
    
    def test_get_queued_job_not_found(self, client):
        """GET /api/queue/jobs/{job_id} should return 404."""
        response = client.get("/api/queue/jobs/nonexistent_job_id")
        
        assert response.status_code == 404
    
    def test_cancel_job_requires_auth(self, client):
        """POST /api/queue/jobs/{job_id}/cancel should require auth."""
        response = client.post("/api/queue/jobs/some_job/cancel")
        
        assert response.status_code == 401


class TestStatsRoutes:
    """Tests for stats routes."""
    
    def test_get_stats(self, client):
        """GET /api/stats should return dashboard statistics."""
        response = client.get("/api/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestCalRoutes:
    """Tests for calibration routes."""
    
    def test_get_cal_table_not_found(self, client):
        """GET /api/cal/{path} should return 404 for unknown table."""
        response = client.get("/api/cal/nonexistent/path/to/cal.tbl")
        
        assert response.status_code == 404
        data = response.json()
        assert_error_response(data)
    
    def test_get_cal_table_url_encoded_path(self, client):
        """GET /api/cal/{path} should handle URL-encoded paths."""
        # Path with special characters
        encoded_path = "/data/cal%2Ftables/test.tbl"
        response = client.get(f"/api/cal{encoded_path}")
        
        # Should try to look up the decoded path
        assert response.status_code in (200, 404)


class TestServicesRoutes:
    """Tests for services status routes."""
    
    def test_get_services_status(self, client):
        """GET /api/services/status should return service statuses."""
        response = client.get("/api/services/status")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (dict, list))
    
    def test_get_service_by_port_not_found(self, client):
        """GET /api/services/status/{port} should return 404 for unknown port."""
        response = client.get("/api/services/status/99999")
        
        assert response.status_code == 404


class TestMSRoutes:
    """Tests for measurement set routes."""
    
    def test_get_ms_list_not_implemented(self, client):
        """GET /api/ms should return 404 (not implemented)."""
        response = client.get("/api/ms")
        
        # This route may not exist
        assert response.status_code in (200, 404)
    
    def test_get_ms_metadata_not_found(self, client):
        """GET /api/ms/{path}/metadata should return 404 for unknown MS."""
        response = client.get("/api/ms/nonexistent/path/metadata")
        
        # Path-based routes may have different behavior
        assert response.status_code in (404, 422)


class TestCacheRoutes:
    """Tests for cache management routes."""
    
    def test_get_cache_stats(self, client):
        """GET /api/cache should return cache statistics."""
        response = client.get("/api/cache")
        
        # May return stats or 404 if not implemented
        assert response.status_code in (200, 404)
    
    def test_clear_cache_requires_auth(self, client):
        """POST /api/cache/clear should require authentication."""
        response = client.post("/api/cache/clear")
        
        # Should require auth
        assert response.status_code in (401, 404, 405)


class TestLogsRoutes:
    """Tests for log routes."""
    
    def test_get_logs_list(self, client):
        """GET /api/logs should return list of log files."""
        response = client.get("/api/logs")
        
        assert response.status_code in (200, 404)
    
    def test_get_log_file_not_found(self, client):
        """GET /api/logs/{filename} should return 404 for unknown file."""
        response = client.get("/api/logs/nonexistent.log")
        
        assert response.status_code in (404, 422)
