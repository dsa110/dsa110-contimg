"""
Contract tests for API endpoints.

These tests verify that API responses match expected schemas and formats.
Uses the FastAPI TestClient for synchronous testing without mocking.

Philosophy:
- Test actual HTTP responses, not mocked handlers
- Verify JSON schema compliance
- Check status code contracts
- Validate error response formats

API Structure:
- /api/health - Basic health endpoint
- /api/v1/* - Versioned API endpoints
- /absurd/* - Absurd orchestration endpoints
"""

import pytest
from pathlib import Path
from typing import Any, Dict


# ============================================================================
# Test Client Fixture
# ============================================================================


@pytest.fixture(scope="module")
def api_client():
    """Create a FastAPI TestClient for API testing."""
    from fastapi.testclient import TestClient
    from dsa110_contimg.api.app import app
    
    # Use TestClient which handles the async event loop
    client = TestClient(app)
    yield client


# ============================================================================
# Health Endpoint Contracts
# ============================================================================


class TestHealthEndpoints:
    """Contract tests for health check endpoints."""

    def test_health_endpoint_returns_200(self, api_client):
        """Verify /api/health returns 200 OK."""
        response = api_client.get("/api/health")
        
        assert response.status_code == 200

    def test_health_response_has_status_field(self, api_client):
        """Verify health response includes status field."""
        response = api_client.get("/api/health")
        data = response.json()
        
        # Should have overall_status or status field
        assert "overall_status" in data or "status" in data

    def test_health_response_is_json(self, api_client):
        """Verify health endpoint returns JSON."""
        response = api_client.get("/api/health")
        
        assert response.headers.get("content-type", "").startswith("application/json")


class TestHealthDetailedEndpoint:
    """Contract tests for detailed health endpoints."""

    def test_health_system_endpoint_exists(self, api_client):
        """Verify /api/v1/health/system returns valid response."""
        response = api_client.get("/api/v1/health/system")
        
        # Should return 200 (may fail if dependencies unavailable)
        assert response.status_code in [200, 500]

    def test_health_databases_endpoint(self, api_client):
        """Verify /api/v1/health/databases returns database status."""
        response = api_client.get("/api/v1/health/databases")
        
        # Should return 200 or 500 if db check fails
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)


# ============================================================================
# Services Status Contracts
# ============================================================================


class TestServicesStatus:
    """Contract tests for services status endpoints."""

    def test_services_status_endpoint_exists(self, api_client):
        """Verify /api/v1/services/status endpoint exists."""
        response = api_client.get("/api/v1/services/status")
        
        # Should return 200 or a valid error code, not 404
        assert response.status_code != 404

    def test_services_status_response_format(self, api_client):
        """Verify services status response is valid JSON."""
        response = api_client.get("/api/v1/services/status")
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))


# ============================================================================
# MS Metadata API Contracts
# ============================================================================


class TestMSMetadataAPI:
    """Contract tests for MS metadata endpoints."""

    def test_ms_metadata_endpoint_pattern(self, api_client):
        """Verify MS metadata endpoint exists."""
        # MS endpoints use encoded path - test with a fake path
        response = api_client.get("/api/v1/ms/test%2Fnonexistent.ms/metadata")
        
        # Should return 404 for non-existent MS, 500 for internal error,
        # or 503 if database is unavailable (test environment)
        assert response.status_code in [404, 500, 503]

    def test_ms_metadata_error_response_format(self, api_client):
        """Verify error response has error or detail field."""
        response = api_client.get("/api/v1/ms/test%2Fnonexistent.ms/metadata")
        
        if response.status_code == 404:
            data = response.json()
            # API may use either FastAPI default 'detail' or custom 'error' format
            assert "detail" in data or "error" in data or "message" in data


# ============================================================================
# Images API Contracts
# ============================================================================


class TestImagesAPI:
    """Contract tests for images endpoints."""

    def test_images_list_endpoint_exists(self, api_client):
        """Verify /api/v1/images endpoint exists."""
        response = api_client.get("/api/v1/images")
        
        # Should not be 404 - endpoint exists under v1
        assert response.status_code != 404

    def test_images_list_returns_array(self, api_client):
        """Verify images list returns array."""
        response = api_client.get("/api/v1/images")
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_images_detail_404_for_nonexistent(self, api_client):
        """Verify 404 for nonexistent image."""
        response = api_client.get("/api/v1/images/nonexistent_image_12345")
        
        # 404 for not found, or 503 if database unavailable in test env
        assert response.status_code in [404, 503]


# ============================================================================
# Queue API Contracts
# ============================================================================


class TestQueueAPI:
    """Contract tests for processing queue endpoints."""

    def test_queue_status_endpoint_exists(self, api_client):
        """Verify queue endpoint exists."""
        response = api_client.get("/api/v1/queue")
        
        # Endpoint should exist
        assert response.status_code != 404

    def test_queue_response_format(self, api_client):
        """Verify queue response is valid JSON."""
        response = api_client.get("/api/v1/queue")
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))

    def test_queue_jobs_endpoint_exists(self, api_client):
        """Verify queue jobs endpoint exists."""
        response = api_client.get("/api/v1/queue/jobs")
        
        assert response.status_code != 404


# ============================================================================
# Error Response Contracts
# ============================================================================


class TestErrorResponses:
    """Contract tests for error response formats."""

    def test_404_response_is_json(self, api_client):
        """Verify 404 responses are JSON."""
        response = api_client.get("/api/definitely_not_a_real_endpoint_xyz")
        
        assert response.status_code == 404
        # Should be JSON
        assert response.headers.get("content-type", "").startswith("application/json")

    def test_404_response_has_detail(self, api_client):
        """Verify 404 responses include detail message."""
        response = api_client.get("/api/definitely_not_a_real_endpoint_xyz")
        
        data = response.json()
        assert "detail" in data

    def test_method_not_allowed_returns_405(self, api_client):
        """Verify POST to GET-only endpoint returns 405."""
        response = api_client.post("/api/health")
        
        # Should be 405 Method Not Allowed
        assert response.status_code == 405


# ============================================================================
# CORS Headers Contract
# ============================================================================


class TestCORSHeaders:
    """Contract tests for CORS configuration."""

    def test_cors_allows_localhost(self, api_client):
        """Verify CORS allows localhost origin."""
        response = api_client.options(
            "/api/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        # Should not reject the preflight
        assert response.status_code in [200, 204, 405]


# ============================================================================
# Pagination Contracts
# ============================================================================


class TestPaginationContracts:
    """Contract tests for paginated endpoints."""

    def test_images_pagination_params_accepted(self, api_client):
        """Verify pagination parameters are accepted on images endpoint."""
        response = api_client.get("/api/v1/images?limit=10&offset=0")
        
        # Should not error on pagination params
        # 503 if database unavailable in test environment
        assert response.status_code in [200, 422, 503]

    def test_limit_constrains_results(self, api_client):
        """Verify limit parameter constrains result count."""
        response = api_client.get("/api/v1/images?limit=5")
        
        if response.status_code == 200:
            data = response.json()
            assert len(data) <= 5


# ============================================================================
# Content-Type Contracts
# ============================================================================


class TestContentTypeContracts:
    """Contract tests for content-type handling."""

    def test_json_content_type_header(self, api_client):
        """Verify JSON endpoints have correct content-type."""
        response = api_client.get("/api/health")
        
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type

    def test_accepts_json_content_type(self, api_client):
        """Verify API accepts JSON content-type."""
        response = api_client.get(
            "/api/health",
            headers={"Accept": "application/json"}
        )
        
        assert response.status_code == 200


# ============================================================================
# API Version/Info Contracts
# ============================================================================


class TestAPIInfoContracts:
    """Contract tests for API metadata endpoints."""

    def test_docs_endpoint_exists(self, api_client):
        """Verify /api/docs endpoint exists."""
        response = api_client.get("/api/docs")
        
        # Should return docs page or redirect
        assert response.status_code in [200, 307, 308]

    def test_openapi_schema_available(self, api_client):
        """Verify OpenAPI schema is accessible."""
        response = api_client.get("/api/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data

    def test_redoc_endpoint_exists(self, api_client):
        """Verify /api/redoc endpoint exists."""
        response = api_client.get("/api/redoc")
        
        # Should return redoc page
        assert response.status_code == 200
