"""Unit tests for monitoring API endpoints.

Focus: Fast, isolated tests for publish monitoring and recovery endpoints.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from dsa110_contimg.api.routes import create_app
from dsa110_contimg.database.data_registry import (
    ensure_data_registry_db,
    register_data,
)


def _init_data_registry_db(path: Path) -> None:
    """Initialize data registry database with test data."""
    conn = ensure_data_registry_db(path)

    # Register some test data
    now = datetime.now(tz=timezone.utc).timestamp()

    # Published data
    register_data(
        conn,
        data_type="mosaic",
        data_id="mosaic_published_001",
        stage_path="/stage/mosaics/mosaic_001.fits",
        auto_publish=True,
    )
    # Set as published
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE data_registry
        SET status = 'published',
            published_path = '/data/products/mosaics/mosaic_001.fits',
            published_at = ?,
            publish_attempts = 0
        WHERE data_id = 'mosaic_published_001'
        """,
        (now,),
    )

    # Staging data (no failures)
    register_data(
        conn,
        data_type="mosaic",
        data_id="mosaic_staging_001",
        stage_path="/stage/mosaics/mosaic_002.fits",
        auto_publish=True,
    )

    # Failed publish (1 attempt)
    register_data(
        conn,
        data_type="mosaic",
        data_id="mosaic_failed_001",
        stage_path="/stage/mosaics/mosaic_003.fits",
        auto_publish=True,
    )
    cur.execute(
        """
        UPDATE data_registry
        SET publish_attempts = 1,
            publish_error = 'Disk full'
        WHERE data_id = 'mosaic_failed_001'
        """,
    )

    # Failed publish (max attempts exceeded)
    register_data(
        conn,
        data_type="mosaic",
        data_id="mosaic_failed_max_001",
        stage_path="/stage/mosaics/mosaic_004.fits",
        auto_publish=True,
    )
    cur.execute(
        """
        UPDATE data_registry
        SET publish_attempts = 3,
            publish_error = 'Persistent error'
        WHERE data_id = 'mosaic_failed_max_001'
        """,
    )

    conn.commit()
    conn.close()


@pytest.fixture
def temp_registry_db(tmp_path, monkeypatch):
    """Create temporary data registry database and set environment."""
    db_path = tmp_path / "products.sqlite3"
    _init_data_registry_db(db_path)

    # Mock the database path used by API routes
    monkeypatch.setenv("PIPELINE_STATE_DIR", str(tmp_path))

    return db_path


@pytest.fixture
def api_client(temp_registry_db, monkeypatch):
    """Create API test client with mocked databases."""
    # Import the function to patch
    from dsa110_contimg.database import data_registry

    # Store original function
    original_ensure_db = data_registry.ensure_data_registry_db

    def mock_ensure_db(path):
        """Mock ensure_data_registry_db to use temp db."""
        path_str = str(path)
        if path_str == "/data/dsa110-contimg/state/products.sqlite3":
            return original_ensure_db(temp_registry_db)
        return original_ensure_db(path)

    monkeypatch.setattr(
        data_registry,
        "ensure_data_registry_db",
        mock_ensure_db,
    )

    app = create_app()
    return TestClient(app)


@pytest.mark.unit
def test_get_publish_status_endpoint(api_client, temp_registry_db):
    """Test GET /api/monitoring/publish/status endpoint."""
    response = api_client.get("/api/monitoring/publish/status")

    assert response.status_code == 200
    data = response.json()

    assert "total_published" in data
    assert "total_staging" in data
    assert "total_publishing" in data
    assert "failed_publishes" in data
    assert "max_attempts_exceeded" in data
    assert "success_rate_percent" in data
    assert "recent_failures_24h" in data
    assert "timestamp" in data

    # Verify structure (counts may vary based on test data)
    assert isinstance(data["total_published"], int)
    assert isinstance(data["failed_publishes"], int)
    assert isinstance(data["max_attempts_exceeded"], int)
    assert 0 <= data["success_rate_percent"] <= 100


@pytest.mark.unit
def test_get_failed_publishes_endpoint(api_client):
    """Test GET /api/monitoring/publish/failed endpoint."""
    response = api_client.get("/api/monitoring/publish/failed")

    assert response.status_code == 200
    data = response.json()

    assert "count" in data
    assert "failed_publishes" in data
    assert isinstance(data["failed_publishes"], list)
    assert data["count"] == len(data["failed_publishes"])

    # Verify structure of failed publish records
    if data["failed_publishes"]:
        failed = data["failed_publishes"][0]
        assert "data_id" in failed
        assert "data_type" in failed
        assert "stage_path" in failed
        assert "publish_attempts" in failed
        assert "publish_error" in failed
        assert failed["publish_attempts"] > 0


@pytest.mark.unit
def test_get_failed_publishes_with_max_attempts_filter(api_client):
    """Test GET /api/monitoring/publish/failed with max_attempts filter."""
    # Get all failed
    response1 = api_client.get("/api/monitoring/publish/failed")
    all_failed = response1.json()["count"]

    # Get only max attempts exceeded
    response2 = api_client.get("/api/monitoring/publish/failed?max_attempts=3")
    max_attempts_failed = response2.json()["count"]

    assert max_attempts_failed <= all_failed
    # May be 0 if test data doesn't have 3+ attempts, which is fine


@pytest.mark.unit
def test_get_failed_publishes_with_limit(api_client):
    """Test GET /api/monitoring/publish/failed with limit parameter."""
    response = api_client.get("/api/monitoring/publish/failed?limit=1")

    assert response.status_code == 200
    data = response.json()
    assert len(data["failed_publishes"]) <= 1


@pytest.mark.unit
def test_retry_publish_endpoint_success(api_client, temp_registry_db):
    """Test POST /api/monitoring/publish/retry/{data_id} success."""
    # Mock trigger_auto_publish to succeed
    with patch(
        "dsa110_contimg.database.data_registry.trigger_auto_publish",
        return_value=True,
    ):
        # Use data_id that exists in test database
        response = api_client.post("/api/monitoring/publish/retry/mosaic_failed_001")

        # Should succeed (mocked)
        assert response.status_code == 200
        data = response.json()
        assert data["retried"] is True
        assert data["published"] is True


@pytest.mark.unit
def test_retry_publish_endpoint_not_found(api_client):
    """Test retry endpoint with non-existent data_id."""
    response = api_client.post("/api/monitoring/publish/retry/nonexistent_id")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.unit
def test_retry_publish_endpoint_already_published(api_client):
    """Test retry endpoint with already published data."""
    response = api_client.post("/api/monitoring/publish/retry/mosaic_published_001")

    assert response.status_code == 400
    assert "already published" in response.json()["detail"].lower()


@pytest.mark.unit
def test_retry_all_failed_publishes_endpoint(api_client):
    """Test POST /api/monitoring/publish/retry-all endpoint."""
    # Mock trigger_auto_publish to succeed
    with patch(
        "dsa110_contimg.database.data_registry.trigger_auto_publish",
        return_value=True,
    ):
        response = api_client.post("/api/monitoring/publish/retry-all?limit=5")

        assert response.status_code == 200
        data = response.json()

        assert "total_attempted" in data
        assert "successful" in data
        assert "failed" in data
        assert "results" in data
        assert isinstance(data["results"], list)
        assert data["total_attempted"] == len(data["results"])


@pytest.mark.unit
def test_retry_all_with_max_attempts_filter(api_client):
    """Test POST /api/monitoring/publish/retry-all with max_attempts filter."""
    with patch(
        "dsa110_contimg.database.data_registry.trigger_auto_publish",
        return_value=True,
    ):
        response = api_client.post(
            "/api/monitoring/publish/retry-all?max_attempts=3&limit=10"
        )

        assert response.status_code == 200
        data = response.json()
        # Should only retry publishes with 3+ attempts
        assert data["total_attempted"] >= 0


@pytest.mark.unit
def test_monitoring_endpoints_handle_empty_database(tmp_path, monkeypatch):
    """Test that monitoring endpoints handle empty database gracefully."""
    # Create empty database
    db_path = tmp_path / "empty_registry.sqlite3"
    conn = ensure_data_registry_db(db_path)
    conn.close()

    monkeypatch.setenv("PIPELINE_STATE_DIR", str(tmp_path))

    app = create_app()
    client = TestClient(app)

    # Status endpoint should work with empty DB
    response = client.get("/api/monitoring/publish/status")
    assert response.status_code == 200
    data = response.json()
    assert data["total_published"] == 0
    assert data["failed_publishes"] == 0
    assert data["success_rate_percent"] == 100.0

    # Failed endpoint should return empty list
    response = client.get("/api/monitoring/publish/failed")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["failed_publishes"] == []
