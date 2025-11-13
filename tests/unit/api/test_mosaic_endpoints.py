"""Unit tests for mosaic creation API endpoint.

Focus: Fast tests for mosaic creation endpoint with mocked dependencies.
"""

from __future__ import annotations
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from dsa110_contimg.api.routes import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_products_db(monkeypatch):
    """Mock products database path."""
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = Path(f.name)

    monkeypatch.setenv("PIPELINE_PRODUCTS_DB", str(db_path))
    yield db_path
    db_path.unlink(missing_ok=True)


class TestMosaicCreateEndpoint:
    """Test POST /api/mosaics/create endpoint."""

    @patch("dsa110_contimg.api.routers.mosaics.run_mosaic_create_job")
    @patch("dsa110_contimg.api.routers.mosaics.create_job")
    @patch("dsa110_contimg.api.routers.mosaics.get_job")
    @patch("dsa110_contimg.api.routers.mosaics.ensure_products_db")
    def test_create_mosaic_calibrator_centered(
        self, mock_ensure_db, mock_get_job, mock_create_job, mock_run_job, client, mock_products_db
    ):
        """Test creating mosaic centered on calibrator."""
        mock_conn = MagicMock()
        mock_ensure_db.return_value = mock_conn

        mock_create_job.return_value = 1

        mock_get_job.return_value = {
            "id": 1,
            "status": "pending",
            "params": {},
        }

        request_body = {
            "calibrator_name": "0834+555",
            "timespan_minutes": 50,
            "wait_for_published": False,
        }

        response = client.post("/api/mosaics/create", json=request_body)

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == 1
        assert data["status"] == "pending"
        assert "message" in data

        mock_create_job.assert_called_once()
        mock_run_job.assert_called_once()

    @patch("dsa110_contimg.api.routers.mosaics.run_mosaic_create_job")
    @patch("dsa110_contimg.api.routers.mosaics.create_job")
    @patch("dsa110_contimg.api.routers.mosaics.get_job")
    @patch("dsa110_contimg.api.routers.mosaics.ensure_products_db")
    def test_create_mosaic_time_window(
        self, mock_ensure_db, mock_get_job, mock_create_job, mock_run_job, client, mock_products_db
    ):
        """Test creating mosaic for time window."""
        mock_conn = MagicMock()
        mock_ensure_db.return_value = mock_conn

        mock_create_job.return_value = 1

        mock_get_job.return_value = {
            "id": 1,
            "status": "pending",
            "params": {},
        }

        request_body = {
            "start_time": "2025-11-12T10:00:00",
            "end_time": "2025-11-12T10:50:00",
            "wait_for_published": False,
        }

        response = client.post("/api/mosaics/create", json=request_body)

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == 1
        assert data["status"] == "pending"

        mock_create_job.assert_called_once()
        mock_run_job.assert_called_once()

    def test_create_mosaic_missing_params(self, client):
        """Test creating mosaic without required parameters."""
        request_body = {}

        response = client.post("/api/mosaics/create", json=request_body)
        assert response.status_code == 400

    def test_create_mosaic_invalid_params(self, client):
        """Test creating mosaic with invalid parameters (neither calibrator nor time window)."""
        request_body = {
            "timespan_minutes": 50,
        }

        response = client.post("/api/mosaics/create", json=request_body)
        assert response.status_code == 400

