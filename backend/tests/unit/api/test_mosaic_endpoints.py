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


class TestMosaicListEndpoint:
    """Test GET /api/mosaics endpoint."""

    @patch("dsa110_contimg.api.routers.mosaics.fetch_mosaics_recent")
    def test_list_mosaics_success(self, mock_fetch, client):
        """Test successful mosaic listing."""
        mock_fetch.return_value = (
            [
                {
                    "id": 1,
                    "name": "test_mosaic",
                    "path": "/data/mosaics/test.fits",
                    "status": "completed",
                    "start_mjd": 60976.5,
                    "end_mjd": 60976.6,
                    "start_time": "2025-10-28T12:00:00",
                    "end_time": "2025-10-28T14:00:00",
                    "created_at": "2025-10-28T15:00:00",
                    "method": None,
                    "image_count": 10,
                    "noise_jy": 0.001,
                    "source_count": 150,
                    "center_ra_deg": None,
                    "center_dec_deg": None,
                    "thumbnail_path": None,
                }
            ],
            1,
        )

        response = client.get("/api/mosaics")
        assert response.status_code == 200
        data = response.json()
        assert "mosaics" in data
        assert len(data["mosaics"]) == 1
        assert data["total"] == 1
        assert data["mosaics"][0]["name"] == "test_mosaic"

    @patch("dsa110_contimg.api.routers.mosaics.fetch_mosaics_recent")
    def test_list_mosaics_empty(self, mock_fetch, client):
        """Test mosaic listing with no results."""
        mock_fetch.return_value = ([], 0)

        response = client.get("/api/mosaics")
        assert response.status_code == 200
        data = response.json()
        assert data["mosaics"] == []
        assert data["total"] == 0

    @patch("dsa110_contimg.api.routers.mosaics.fetch_mosaics_recent")
    def test_list_mosaics_with_limit(self, mock_fetch, client):
        """Test mosaic listing with custom limit."""
        mock_fetch.return_value = ([], 0)

        response = client.get("/api/mosaics?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 5
        mock_fetch.assert_called_once()
        # Verify limit was passed to function
        call_args = mock_fetch.call_args
        assert call_args[1]["limit"] == 5


class TestMosaicCreateEndpoint:
    """Test POST /api/mosaics/create endpoint."""

    @patch("dsa110_contimg.api.routers.mosaics.run_mosaic_create_job")
    @patch("dsa110_contimg.api.routers.mosaics.create_job")
    @patch("dsa110_contimg.api.routers.mosaics.get_job")
    @patch("dsa110_contimg.api.routers.mosaics.ensure_products_db")
    def test_create_mosaic_calibrator_centered(
        self,
        mock_ensure_db,
        mock_get_job,
        mock_create_job,
        mock_run_job,
        client,
        mock_products_db,
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
        self,
        mock_ensure_db,
        mock_get_job,
        mock_create_job,
        mock_run_job,
        client,
        mock_products_db,
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
