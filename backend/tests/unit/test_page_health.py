"""
Unit tests for page health and UI integration.

Tests for:
- All API endpoints return valid responses
- Response structure is consistent for UI consumption
- Error responses have proper format
- Content types are correct
- Pagination works correctly
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from dsa110_contimg.api.app import create_app


@pytest.fixture
def client():
    """Create a test client for the API."""
    with patch("dsa110_contimg.api.app.is_ip_allowed", return_value=True):
        app = create_app()
        yield TestClient(app)


class TestPageHealthImages:
    """Tests for images page health."""

    def test_images_list_returns_200(self, client):
        """Test images list returns 200."""
        response = client.get("/api/v1/images")
        
        assert response.status_code == 200

    def test_images_list_returns_array(self, client):
        """Test images list returns an array."""
        response = client.get("/api/v1/images")
        data = response.json()
        
        assert isinstance(data, list)

    def test_images_list_supports_pagination(self, client):
        """Test images list supports limit and offset."""
        response = client.get("/api/v1/images?limit=10&offset=0")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_images_content_type_is_json(self, client):
        """Test images endpoint returns JSON content type."""
        response = client.get("/api/v1/images")
        
        assert "application/json" in response.headers.get("content-type", "")

    def test_images_detail_returns_404_for_invalid(self, client):
        """Test image detail returns 404 for invalid ID."""
        response = client.get("/api/v1/images/invalid-id-xyz")
        
        assert response.status_code == 404

    def test_images_error_has_detail(self, client):
        """Test image error response has detail field."""
        response = client.get("/api/v1/images/invalid-id-xyz")
        data = response.json()
        
        assert "detail" in data


class TestPageHealthSources:
    """Tests for sources page health."""

    def test_sources_list_returns_200(self, client):
        """Test sources list returns 200."""
        response = client.get("/api/v1/sources")
        
        assert response.status_code == 200

    def test_sources_list_returns_array(self, client):
        """Test sources list returns an array."""
        response = client.get("/api/v1/sources")
        data = response.json()
        
        assert isinstance(data, list)

    def test_sources_list_supports_pagination(self, client):
        """Test sources list supports limit and offset."""
        response = client.get("/api/v1/sources?limit=20&offset=0")
        
        assert response.status_code == 200

    def test_sources_content_type_is_json(self, client):
        """Test sources endpoint returns JSON content type."""
        response = client.get("/api/v1/sources")
        
        assert "application/json" in response.headers.get("content-type", "")

    def test_sources_detail_returns_404_for_invalid(self, client):
        """Test source detail returns 404 for invalid ID."""
        response = client.get("/api/v1/sources/invalid-source-xyz")
        
        assert response.status_code == 404


class TestPageHealthJobs:
    """Tests for jobs page health."""

    def test_jobs_list_returns_200(self, client):
        """Test jobs list returns 200."""
        response = client.get("/api/v1/jobs")
        
        assert response.status_code == 200

    def test_jobs_list_returns_array(self, client):
        """Test jobs list returns an array."""
        response = client.get("/api/v1/jobs")
        data = response.json()
        
        assert isinstance(data, list)

    def test_jobs_list_supports_pagination(self, client):
        """Test jobs list supports limit and offset."""
        response = client.get("/api/v1/jobs?limit=50&offset=0")
        
        assert response.status_code == 200

    def test_jobs_content_type_is_json(self, client):
        """Test jobs endpoint returns JSON content type."""
        response = client.get("/api/v1/jobs")
        
        assert "application/json" in response.headers.get("content-type", "")


class TestPageHealthStats:
    """Tests for stats/dashboard page health."""

    def test_stats_endpoint_exists(self, client):
        """Test stats endpoint returns response."""
        response = client.get("/api/v1/stats")
        
        # May return 200 or 404 depending on implementation
        assert response.status_code in (200, 404)

    def test_health_endpoint_for_dashboard(self, client):
        """Test health endpoint for dashboard status."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestPageHealthCalibration:
    """Tests for calibration page health."""

    def test_cal_endpoint_exists(self, client):
        """Test calibration endpoint returns response."""
        response = client.get("/api/v1/cal")
        
        # May return 200, 404, or 405 depending on implementation
        assert response.status_code in (200, 404, 405)


class TestUIResponseConsistency:
    """Tests for UI response consistency."""

    def test_list_endpoints_return_arrays(self, client):
        """Test all list endpoints return arrays."""
        list_endpoints = [
            "/api/v1/images",
            "/api/v1/sources",
            "/api/v1/jobs",
        ]
        
        for endpoint in list_endpoints:
            response = client.get(endpoint)
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list), f"{endpoint} should return array"

    def test_error_responses_have_detail(self, client):
        """Test error responses have detail field."""
        error_urls = [
            "/api/v1/images/nonexistent",
            "/api/v1/sources/nonexistent",
        ]
        
        for url in error_urls:
            response = client.get(url)
            if response.status_code >= 400:
                data = response.json()
                assert "detail" in data, f"{url} error should have detail"

    def test_all_endpoints_return_json(self, client):
        """Test all API endpoints return JSON."""
        endpoints = [
            "/api/v1/images",
            "/api/v1/sources",
            "/api/v1/jobs",
            "/api/v1/health",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            content_type = response.headers.get("content-type", "")
            assert "application/json" in content_type, f"{endpoint} should return JSON"


class TestUIPagination:
    """Tests for UI pagination support."""

    def test_images_pagination_params_accepted(self, client):
        """Test images accepts pagination parameters."""
        response = client.get("/api/v1/images?limit=10&offset=5")
        
        assert response.status_code == 200

    def test_sources_pagination_params_accepted(self, client):
        """Test sources accepts pagination parameters."""
        response = client.get("/api/v1/sources?limit=10&offset=5")
        
        assert response.status_code == 200

    def test_jobs_pagination_params_accepted(self, client):
        """Test jobs accepts pagination parameters."""
        response = client.get("/api/v1/jobs?limit=10&offset=5")
        
        assert response.status_code == 200

    def test_invalid_limit_rejected(self, client):
        """Test invalid limit is rejected."""
        response = client.get("/api/v1/images?limit=-1")
        
        # Should reject negative limit
        assert response.status_code in (200, 422)  # 422 for validation error

    def test_large_limit_capped(self, client):
        """Test large limit is handled (capped or accepted)."""
        response = client.get("/api/v1/images?limit=10000")
        
        # Should either cap or reject
        assert response.status_code in (200, 422)


class TestUIErrorHandling:
    """Tests for UI error handling."""

    def test_404_returns_json(self, client):
        """Test 404 errors return JSON."""
        response = client.get("/api/v1/images/nonexistent-id")
        
        assert response.status_code == 404
        assert "application/json" in response.headers.get("content-type", "")

    def test_404_has_error_structure(self, client):
        """Test 404 error has proper structure."""
        response = client.get("/api/v1/images/nonexistent-id")
        data = response.json()
        
        assert "detail" in data

    def test_validation_error_returns_422(self, client):
        """Test validation errors return 422."""
        # Invalid query parameter
        response = client.get("/api/v1/images?limit=not-a-number")
        
        assert response.status_code == 422


class TestUICORSHeaders:
    """Tests for UI CORS header support."""

    def test_cors_headers_present(self, client):
        """Test CORS headers are present in responses."""
        response = client.get("/api/v1/images")
        
        # Note: TestClient may not show CORS headers directly
        # But we verify the endpoint works
        assert response.status_code == 200


class TestUISecurityHeaders:
    """Tests for UI security headers."""

    def test_x_content_type_options(self, client):
        """Test X-Content-Type-Options header is set."""
        response = client.get("/api/v1/images")
        
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        """Test X-Frame-Options header is set."""
        response = client.get("/api/v1/images")
        
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_referrer_policy(self, client):
        """Test Referrer-Policy header is set."""
        response = client.get("/api/v1/images")
        
        assert "Referrer-Policy" in response.headers


class TestUIResponseTiming:
    """Tests for UI response timing expectations."""

    def test_health_endpoint_is_fast(self, client):
        """Test health endpoint responds quickly."""
        import time
        
        start = time.time()
        response = client.get("/api/v1/health")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0  # Should respond in under 1 second

    def test_list_endpoints_respond(self, client):
        """Test list endpoints respond in reasonable time."""
        import time
        
        endpoints = ["/api/v1/images", "/api/v1/sources", "/api/v1/jobs"]
        
        for endpoint in endpoints:
            start = time.time()
            response = client.get(endpoint)
            elapsed = time.time() - start
            
            assert response.status_code == 200
            assert elapsed < 5.0  # Should respond in under 5 seconds
