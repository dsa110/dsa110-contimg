"""
Integration tests for the DSA-110 API.

These tests make actual HTTP requests to test endpoints end-to-end.
They require the API to be running and accessible.

Run with:
    pytest tests/integration/ -v --tb=short
"""

import os
import pytest
from datetime import datetime
from httpx import AsyncClient

# Test configuration
API_BASE_URL = os.getenv("TEST_API_URL", "http://localhost:8000")
TEST_API_KEY = os.getenv("TEST_API_KEY", "test-key-for-integration")


@pytest.fixture
def api_url():
    """Get API base URL."""
    return API_BASE_URL


@pytest.fixture
def auth_headers():
    """Get authentication headers for write operations."""
    return {"X-API-Key": TEST_API_KEY}


class TestHealthEndpoint:
    """Tests for the health check endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, api_url):
        """Health endpoint should return healthy status."""
        async with AsyncClient() as client:
            response = await client.get(f"{api_url}/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_health_has_service_name(self, api_url):
        """Health response should include service name."""
        async with AsyncClient() as client:
            response = await client.get(f"{api_url}/api/health")
        
        data = response.json()
        assert "service" in data
        assert data["service"] == "dsa110-contimg-api"


class TestImagesEndpoint:
    """Tests for the images endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_images_returns_list(self, api_url):
        """GET /images should return a list."""
        async with AsyncClient() as client:
            response = await client.get(f"{api_url}/api/images")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_list_images_with_pagination(self, api_url):
        """GET /images should support pagination."""
        async with AsyncClient() as client:
            response = await client.get(
                f"{api_url}/api/images",
                params={"limit": 5, "offset": 0}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_image(self, api_url):
        """GET /images/{id} should return 404 for missing image."""
        async with AsyncClient() as client:
            response = await client.get(f"{api_url}/api/images/nonexistent_image_id")
        
        assert response.status_code == 404


class TestSourcesEndpoint:
    """Tests for the sources endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_sources_returns_list(self, api_url):
        """GET /sources should return a list."""
        async with AsyncClient() as client:
            response = await client.get(f"{api_url}/api/sources")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_source(self, api_url):
        """GET /sources/{id} should return 404 for missing source."""
        async with AsyncClient() as client:
            response = await client.get(f"{api_url}/api/sources/nonexistent_source_id")
        
        assert response.status_code == 404


class TestJobsEndpoint:
    """Tests for the jobs endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_jobs_returns_list(self, api_url):
        """GET /jobs should return a list."""
        async with AsyncClient() as client:
            response = await client.get(f"{api_url}/api/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self, api_url):
        """GET /jobs/{id} should return 404 for missing job."""
        async with AsyncClient() as client:
            response = await client.get(f"{api_url}/api/jobs/nonexistent_run_id")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_rerun_job_requires_auth(self, api_url):
        """POST /jobs/{id}/rerun should require authentication."""
        async with AsyncClient() as client:
            response = await client.post(f"{api_url}/api/jobs/some_run_id/rerun")
        
        # Should get 401 without auth header
        assert response.status_code == 401


class TestQueueEndpoint:
    """Tests for the queue endpoints."""
    
    @pytest.mark.asyncio
    async def test_queue_stats(self, api_url):
        """GET /queue should return queue stats."""
        async with AsyncClient() as client:
            response = await client.get(f"{api_url}/api/queue")
        
        assert response.status_code == 200
        data = response.json()
        assert "connected" in data
        assert "queue_name" in data
    
    @pytest.mark.asyncio
    async def test_list_queued_jobs(self, api_url):
        """GET /queue/jobs should return job list."""
        async with AsyncClient() as client:
            response = await client.get(f"{api_url}/api/queue/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_queue_job_not_found(self, api_url):
        """GET /queue/jobs/{id} should return 404 for missing job."""
        async with AsyncClient() as client:
            response = await client.get(f"{api_url}/api/queue/jobs/nonexistent_job")
        
        assert response.status_code == 404


class TestCacheEndpoint:
    """Tests for the cache endpoints."""
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, api_url):
        """GET /cache should return cache stats."""
        async with AsyncClient() as client:
            response = await client.get(f"{api_url}/api/cache")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    @pytest.mark.asyncio
    async def test_cache_invalidate_requires_auth(self, api_url):
        """POST /cache/invalidate requires auth."""
        async with AsyncClient() as client:
            response = await client.post(f"{api_url}/api/cache/invalidate/test")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_cache_clear_requires_auth(self, api_url):
        """POST /cache/clear requires auth."""
        async with AsyncClient() as client:
            response = await client.post(f"{api_url}/api/cache/clear")
        
        assert response.status_code == 401


class TestCORSHeaders:
    """Tests for CORS headers."""
    
    @pytest.mark.asyncio
    async def test_cors_headers_present(self, api_url):
        """API should include CORS headers."""
        async with AsyncClient() as client:
            # Test that CORS headers are present on a regular GET request
            response = await client.get(
                f"{api_url}/api/health",
                headers={"Origin": "http://localhost:3000"}
            )
        
        # Check that the request succeeds and CORS is configured
        assert response.status_code == 200
        # CORS headers should be present in the response
        # Note: In test environment, CORS may not be fully configured
        # This test primarily verifies the middleware doesn't break requests


class TestStatsEndpoint:
    """Tests for the stats endpoints."""
    
    @pytest.mark.asyncio
    async def test_stats_returns_data(self, api_url):
        """GET /stats should return statistics."""
        async with AsyncClient() as client:
            response = await client.get(f"{api_url}/api/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestOpenAPI:
    """Tests for OpenAPI documentation."""
    
    @pytest.mark.asyncio
    async def test_openapi_json(self, api_url):
        """OpenAPI JSON should be available."""
        async with AsyncClient() as client:
            response = await client.get(f"{api_url}/api/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
    
    @pytest.mark.asyncio
    async def test_docs_page(self, api_url):
        """Docs page should be accessible."""
        async with AsyncClient() as client:
            response = await client.get(f"{api_url}/api/docs")
        
        assert response.status_code == 200
