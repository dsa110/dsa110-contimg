"""Unit tests for batch API endpoints.

Focus: Fast tests for batch conversion and publishing endpoints with mocked dependencies.
"""

from __future__ import annotations

import tempfile
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


class TestBatchConvertEndpoint:
    """Test POST /api/batch/convert endpoint."""

    @patch("dsa110_contimg.api.batch_jobs.create_batch_conversion_job")
    @patch("dsa110_contimg.api.job_runner.run_batch_convert_job")
    @patch("dsa110_contimg.database.products.ensure_products_db")
    def test_create_batch_convert_job(
        self, mock_ensure_db, mock_run_job, mock_create_job, client, mock_products_db
    ):
        """Test creating a batch conversion job."""
        import sqlite3

        # Create real in-memory database
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        cursor = conn.cursor()

        # Create tables
        cursor.execute(
            """
            CREATE TABLE batch_jobs (
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
            CREATE TABLE batch_job_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                ms_path TEXT NOT NULL,
                job_id INTEGER,
                status TEXT NOT NULL,
                error TEXT,
                started_at REAL,
                completed_at REAL
            )
            """
        )

        # Insert test batch job
        cursor.execute(
            """
            INSERT INTO batch_jobs (type, created_at, status, total_items, completed_items, failed_items, params)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "batch_convert",
                1234567890.0,
                "pending",
                2,
                0,
                0,
                '{"output_dir": "/stage/ms"}',
            ),
        )
        batch_id = cursor.lastrowid

        # Insert test items
        cursor.execute(
            """
            INSERT INTO batch_job_items (batch_id, ms_path, status)
            VALUES (?, ?, ?)
            """,
            (
                batch_id,
                "time_window_2025-11-12T10:00:00_2025-11-12T10:50:00",
                "pending",
            ),
        )
        cursor.execute(
            """
            INSERT INTO batch_job_items (batch_id, ms_path, status)
            VALUES (?, ?, ?)
            """,
            (
                batch_id,
                "time_window_2025-11-12T11:00:00_2025-11-12T11:50:00",
                "pending",
            ),
        )
        conn.commit()

        mock_ensure_db.return_value = conn
        mock_create_job.return_value = batch_id

        request_body = {
            "job_type": "convert",
            "params": {
                "time_windows": [
                    {
                        "start_time": "2025-11-12T10:00:00",
                        "end_time": "2025-11-12T10:50:00",
                    },
                    {
                        "start_time": "2025-11-12T11:00:00",
                        "end_time": "2025-11-12T11:50:00",
                    },
                ],
                "params": {
                    "input_dir": "/data/incoming",
                    "output_dir": "/stage/ms",
                    "start_time": "2025-11-12T09:30:00",
                    "end_time": "2025-11-12T12:30:00",
                    "writer": "parallel-subband",
                    "stage_to_tmpfs": False,
                    "max_workers": 2,
                },
            },
        }

        response = client.post("/api/batch/convert", json=request_body)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["type"] == "batch_convert"
        assert data["total_items"] == 2

    def test_create_batch_convert_job_invalid_type(self, client):
        """Test creating batch convert job with invalid job_type."""
        request_body = {
            "job_type": "invalid",
            "params": {
                "time_windows": [],
                "params": {},
            },
        }

        response = client.post("/api/batch/convert", json=request_body)
        assert response.status_code == 400

    def test_create_batch_convert_job_invalid_params(self, client):
        """Test creating batch convert job with invalid params type."""
        request_body = {
            "job_type": "convert",
            "params": {"invalid": "params"},
        }

        response = client.post("/api/batch/convert", json=request_body)
        assert response.status_code == 400


class TestBatchPublishEndpoint:
    """Test POST /api/batch/publish endpoint."""

    @patch("dsa110_contimg.api.batch_jobs.create_batch_publish_job")
    @patch("dsa110_contimg.api.job_runner.run_batch_publish_job")
    @patch("dsa110_contimg.database.products.ensure_products_db")
    def test_create_batch_publish_job(
        self, mock_ensure_db, mock_run_job, mock_create_job, client, mock_products_db
    ):
        """Test creating a batch publish job."""
        import sqlite3

        conn = sqlite3.connect(":memory:", check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE batch_jobs (
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
            CREATE TABLE batch_job_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                ms_path TEXT NOT NULL,
                job_id INTEGER,
                status TEXT NOT NULL,
                error TEXT,
                started_at REAL,
                completed_at REAL
            )
            """
        )

        cursor.execute(
            """
            INSERT INTO batch_jobs (type, created_at, status, total_items, completed_items, failed_items, params)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "batch_publish",
                1234567890.0,
                "pending",
                2,
                0,
                0,
                '{"products_base": "/data/products"}',
            ),
        )
        batch_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO batch_job_items (batch_id, ms_path, status)
            VALUES (?, ?, ?)
            """,
            (batch_id, "mosaic_001", "pending"),
        )
        cursor.execute(
            """
            INSERT INTO batch_job_items (batch_id, ms_path, status)
            VALUES (?, ?, ?)
            """,
            (batch_id, "mosaic_002", "pending"),
        )
        conn.commit()

        mock_ensure_db.return_value = conn
        mock_create_job.return_value = batch_id

        request_body = {
            "job_type": "publish",
            "params": {
                "data_ids": ["mosaic_001", "mosaic_002"],
                "products_base": "/data/products",
            },
        }

        response = client.post("/api/batch/publish", json=request_body)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["type"] == "batch_publish"
        assert data["total_items"] == 2

    def test_create_batch_publish_job_invalid_type(self, client):
        """Test creating batch publish job with invalid job_type."""
        request_body = {
            "job_type": "invalid",
            "params": {
                "data_ids": ["mosaic_001"],
            },
        }

        response = client.post("/api/batch/publish", json=request_body)
        assert response.status_code == 400

    def test_create_batch_publish_job_invalid_params(self, client):
        """Test creating batch publish job with invalid params type."""
        request_body = {
            "job_type": "publish",
            "params": {"invalid": "params"},
        }

        response = client.post("/api/batch/publish", json=request_body)
        assert response.status_code == 400
