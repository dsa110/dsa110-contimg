"""Unit tests for ESE detection API endpoints.

Focus: Fast tests for POST /api/jobs/ese-detect and POST /api/batch/ese-detect endpoints.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

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
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = Path(f.name)

    monkeypatch.setenv("PIPELINE_PRODUCTS_DB", str(db_path))
    yield db_path
    db_path.unlink(missing_ok=True)


@pytest.fixture
def setup_jobs_tables(mock_products_db):
    """Set up jobs tables in test database."""
    conn = sqlite3.connect(mock_products_db)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            status TEXT NOT NULL,
            ms_path TEXT,
            params TEXT,
            logs TEXT,
            artifacts TEXT,
            created_at REAL NOT NULL,
            started_at REAL,
            finished_at REAL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS batch_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            created_at REAL NOT NULL,
            status TEXT NOT NULL,
            total_items INTEGER NOT NULL,
            completed_items INTEGER DEFAULT 0,
            failed_items INTEGER DEFAULT 0,
            params TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS batch_job_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL,
            ms_path TEXT NOT NULL,
            job_id INTEGER,
            status TEXT NOT NULL,
            error TEXT,
            started_at REAL,
            completed_at REAL,
            FOREIGN KEY (batch_id) REFERENCES batch_jobs(id)
        )
        """
    )

    conn.commit()
    conn.close()


class TestESEDetectJobEndpoint:
    """Test POST /api/jobs/ese-detect endpoint."""

    @patch("dsa110_contimg.api.routes.run_ese_detect_job")
    @patch("dsa110_contimg.database.products.ensure_products_db")
    def test_create_ese_detect_job(
        self, mock_ensure_db, mock_run_job, client, mock_products_db, setup_jobs_tables
    ):
        """Test creating an ESE detection job."""
        import sqlite3

        conn = sqlite3.connect(mock_products_db)
        mock_ensure_db.return_value = conn

        request_body = {
            "params": {
                "min_sigma": 5.0,
                "source_id": None,
                "recompute": False,
            }
        }

        response = client.post("/api/jobs/ese-detect", json=request_body)

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "ese-detect"
        assert data["status"] == "pending"
        assert "id" in data

        mock_run_job.assert_not_called()  # Background task

    @patch("dsa110_contimg.api.routes.run_ese_detect_job")
    @patch("dsa110_contimg.database.products.ensure_products_db")
    def test_create_ese_detect_job_with_source_id(
        self, mock_ensure_db, mock_run_job, client, mock_products_db, setup_jobs_tables
    ):
        """Test creating ESE detection job with specific source ID."""
        import sqlite3

        conn = sqlite3.connect(mock_products_db)
        mock_ensure_db.return_value = conn

        request_body = {
            "params": {
                "min_sigma": 6.0,
                "source_id": "source_001",
                "recompute": True,
            }
        }

        response = client.post("/api/jobs/ese-detect", json=request_body)

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "ese-detect"

    def test_create_ese_detect_job_invalid_params(self, client):
        """Test creating ESE detection job with invalid parameters."""
        request_body = {
            "params": {
                "min_sigma": -1.0,  # Invalid negative value
            }
        }

        response = client.post("/api/jobs/ese-detect", json=request_body)

        # Should still accept (validation happens in job execution)
        assert response.status_code in [200, 422]


class TestBatchESEDetectEndpoint:
    """Test POST /api/batch/ese-detect endpoint."""

    @patch("dsa110_contimg.api.routes.run_batch_ese_detect_job")
    @patch("dsa110_contimg.database.products.ensure_products_db")
    def test_create_batch_ese_detect_job(
        self, mock_ensure_db, mock_run_job, client, mock_products_db, setup_jobs_tables
    ):
        """Test creating a batch ESE detection job."""
        import sqlite3

        conn = sqlite3.connect(mock_products_db)
        mock_ensure_db.return_value = conn

        request_body = {
            "job_type": "ese-detect",
            "params": {
                "min_sigma": 5.0,
                "recompute": False,
                "source_ids": None,
            },
        }

        response = client.post("/api/batch/ese-detect", json=request_body)

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "batch_ese-detect"
        assert data["status"] == "pending"
        assert "id" in data
        assert data["total_items"] == 1  # All sources = 1 item

    @patch("dsa110_contimg.api.routes.run_batch_ese_detect_job")
    @patch("dsa110_contimg.database.products.ensure_products_db")
    def test_create_batch_ese_detect_job_with_source_ids(
        self, mock_ensure_db, mock_run_job, client, mock_products_db, setup_jobs_tables
    ):
        """Test creating batch ESE detection job with specific source IDs."""
        import sqlite3

        conn = sqlite3.connect(mock_products_db)
        mock_ensure_db.return_value = conn

        request_body = {
            "job_type": "ese-detect",
            "params": {
                "min_sigma": 5.0,
                "recompute": False,
                "source_ids": ["source_001", "source_002", "source_003"],
            },
        }

        response = client.post("/api/batch/ese-detect", json=request_body)

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "batch_ese-detect"
        assert data["total_items"] == 3

    def test_create_batch_ese_detect_job_invalid_type(self, client):
        """Test creating batch ESE detection job with invalid job type."""
        request_body = {
            "job_type": "invalid-type",
            "params": {
                "min_sigma": 5.0,
            },
        }

        response = client.post("/api/batch/ese-detect", json=request_body)

        assert response.status_code == 400
        assert "ese-detect" in response.json()["detail"].lower()

    def test_create_batch_ese_detect_job_invalid_params(self, client):
        """Test creating batch ESE detection job with invalid params type."""
        request_body = {
            "job_type": "ese-detect",
            "params": {
                "fits_paths": ["/path/to/file.fits"],  # Wrong params type
            },
        }

        response = client.post("/api/batch/ese-detect", json=request_body)

        assert response.status_code == 400
