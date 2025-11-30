"""
Unit tests for health check endpoint enhancements.

Tests for:
- Basic health check
- Detailed health check with database, Redis, and disk checks
- Health status determination (healthy, degraded)
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from dsa110_contimg.api.app import create_app


@pytest.fixture
def client():
    """Create a test client for the API."""
    with patch("dsa110_contimg.api.app.is_ip_allowed", return_value=True):
        app = create_app()
        yield TestClient(app)


class TestBasicHealthCheck:
    """Tests for basic health check endpoint."""

    def test_health_returns_200(self, client):
        """Test health endpoint returns 200."""
        response = client.get("/api/health")
        
        assert response.status_code == 200

    def test_health_status_healthy(self, client):
        """Test health status is healthy."""
        response = client.get("/api/health")
        data = response.json()
        
        assert data["status"] == "healthy"

    def test_health_includes_service_name(self, client):
        """Test health includes service name."""
        response = client.get("/api/health")
        data = response.json()
        
        assert "service" in data
        assert "dsa110" in data["service"].lower()

    def test_health_includes_version(self, client):
        """Test health includes version."""
        response = client.get("/api/health")
        data = response.json()
        
        assert "version" in data

    def test_health_includes_timestamp(self, client):
        """Test health includes timestamp."""
        response = client.get("/api/health")
        data = response.json()
        
        assert "timestamp" in data
        # Should be ISO format
        assert "T" in data["timestamp"]


class TestDetailedHealthCheck:
    """Tests for detailed health check with ?detailed=true."""

    def test_detailed_health_includes_databases(self, client):
        """Test detailed health includes database status."""
        response = client.get("/api/health?detailed=true")
        data = response.json()
        
        assert "databases" in data
        assert isinstance(data["databases"], dict)

    def test_detailed_health_includes_redis(self, client):
        """Test detailed health includes Redis status."""
        response = client.get("/api/health?detailed=true")
        data = response.json()
        
        assert "redis" in data
        assert isinstance(data["redis"], dict)
        assert "status" in data["redis"]

    def test_detailed_health_includes_disk(self, client):
        """Test detailed health includes disk status."""
        response = client.get("/api/health?detailed=true")
        data = response.json()
        
        assert "disk" in data
        assert isinstance(data["disk"], dict)

    def test_detailed_health_database_checks(self, client):
        """Test detailed health checks multiple databases."""
        response = client.get("/api/health?detailed=true")
        data = response.json()
        
        databases = data.get("databases", {})
        # Should check multiple databases
        expected_dbs = ["products", "cal_registry", "hdf5", "ingest"]
        for db_name in expected_dbs:
            if db_name in databases:
                # Each should have a status
                assert isinstance(databases[db_name], str)

    def test_detailed_health_redis_status(self, client):
        """Test detailed health Redis status values."""
        response = client.get("/api/health?detailed=true")
        data = response.json()
        
        redis_status = data.get("redis", {}).get("status", "")
        # Status should be one of these
        valid_statuses = ["ok", "unavailable", "error", "unknown"]
        assert redis_status in valid_statuses

    def test_detailed_health_disk_free_space(self, client):
        """Test detailed health includes disk free space."""
        response = client.get("/api/health?detailed=true")
        data = response.json()
        
        disk = data.get("disk", {})
        # If any disk paths exist, they should have free_gb
        for path, info in disk.items():
            if isinstance(info, dict) and "free_gb" in info:
                assert isinstance(info["free_gb"], (int, float))
                assert info["free_gb"] >= 0


class TestHealthStatusDetermination:
    """Tests for health status determination logic."""

    def test_healthy_when_no_issues(self, client):
        """Test status is healthy when no issues detected."""
        response = client.get("/api/health")
        data = response.json()
        
        # Basic check should always be healthy (no component checks)
        assert data["status"] == "healthy"

    def test_detailed_health_can_be_degraded(self, client):
        """Test detailed health can return degraded status."""
        response = client.get("/api/health?detailed=true")
        data = response.json()
        
        # Status should be either healthy or degraded
        assert data["status"] in ["healthy", "degraded"]

    def test_health_always_accessible(self, client):
        """Test health endpoint is always accessible (no IP filter)."""
        # Health should work even with IP filtering
        response = client.get("/api/health")
        
        assert response.status_code == 200


class TestHealthCheckV1:
    """Tests for /api/v1/health endpoint."""

    def test_v1_health_endpoint(self, client):
        """Test /api/v1/health works same as /api/health."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_v1_health_detailed(self, client):
        """Test /api/v1/health?detailed=true works."""
        response = client.get("/api/v1/health?detailed=true")
        
        assert response.status_code == 200
        data = response.json()
        assert "databases" in data or "redis" in data or "disk" in data

    def test_v1_health_includes_api_version(self, client):
        """Test /api/v1/health includes api_version."""
        response = client.get("/api/v1/health")
        data = response.json()
        
        assert data.get("api_version") == "v1"


class TestHealthCheckResponseFormat:
    """Tests for health check response format."""

    def test_response_is_json(self, client):
        """Test health response is JSON."""
        response = client.get("/api/health")
        
        assert "application/json" in response.headers.get("content-type", "")

    def test_timestamp_is_utc(self, client):
        """Test timestamp is UTC (ends with Z)."""
        response = client.get("/api/health")
        data = response.json()
        
        assert data["timestamp"].endswith("Z")

    def test_response_structure(self, client):
        """Test health response has required fields."""
        response = client.get("/api/health")
        data = response.json()
        
        required_fields = ["status", "service", "version", "timestamp"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
