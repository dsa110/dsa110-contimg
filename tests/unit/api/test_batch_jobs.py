"""Unit tests for batch job creation functions.

Focus: Fast tests for batch job database operations with mocked dependencies.
"""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from dsa110_contimg.api.batch_jobs import (
    create_batch_conversion_job,
    create_batch_publish_job,
    update_batch_conversion_item,
)


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = Path(f.name)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create batch_jobs table
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

    # Create batch_job_items table
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
            completed_at REAL,
            FOREIGN KEY (batch_id) REFERENCES batch_jobs(id)
        )
        """
    )

    conn.commit()
    yield conn, db_path
    conn.close()
    db_path.unlink()


class TestCreateBatchConversionJob:
    """Test create_batch_conversion_job function."""

    def test_create_batch_conversion_job(self, temp_db):
        """Test creating a batch conversion job."""
        conn, db_path = temp_db

        time_windows = [
            {"start_time": "2025-11-12T10:00:00", "end_time": "2025-11-12T10:50:00"},
            {"start_time": "2025-11-12T11:00:00", "end_time": "2025-11-12T11:50:00"},
        ]
        params = {"output_dir": "/stage/ms"}

        batch_id = create_batch_conversion_job(conn, "batch_convert", time_windows, params)

        assert batch_id is not None
        assert batch_id > 0

        # Verify batch job
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM batch_jobs WHERE id = ?", (batch_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row[1] == "batch_convert"  # type
        assert row[4] == 2  # total_items

        # Verify batch items
        cursor.execute("SELECT COUNT(*) FROM batch_job_items WHERE batch_id = ?", (batch_id,))
        count = cursor.fetchone()[0]
        assert count == 2

    def test_create_batch_conversion_job_empty_windows(self, temp_db):
        """Test creating batch conversion job with empty time_windows."""
        conn, db_path = temp_db

        batch_id = create_batch_conversion_job(conn, "batch_convert", [], {})

        cursor = conn.cursor()
        cursor.execute("SELECT total_items FROM batch_jobs WHERE id = ?", (batch_id,))
        total_items = cursor.fetchone()[0]
        assert total_items == 0

    def test_create_batch_conversion_job_invalid_input(self, temp_db):
        """Test create_batch_conversion_job with invalid input."""
        conn, db_path = temp_db

        with pytest.raises(ValueError, match="job_type must be a non-empty string"):
            create_batch_conversion_job(conn, "", [], {})

        with pytest.raises(ValueError, match="time_windows must be a list"):
            create_batch_conversion_job(conn, "batch_convert", "not_a_list", {})

        with pytest.raises(ValueError, match="params must be a dictionary"):
            create_batch_conversion_job(conn, "batch_convert", [], "not_a_dict")


class TestCreateBatchPublishJob:
    """Test create_batch_publish_job function."""

    def test_create_batch_publish_job(self, temp_db):
        """Test creating a batch publish job."""
        conn, db_path = temp_db

        data_ids = ["mosaic_001", "mosaic_002", "mosaic_003"]
        params = {"products_base": "/data/products"}

        batch_id = create_batch_publish_job(conn, "batch_publish", data_ids, params)

        assert batch_id is not None
        assert batch_id > 0

        # Verify batch job
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM batch_jobs WHERE id = ?", (batch_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row[1] == "batch_publish"  # type
        assert row[4] == 3  # total_items

        # Verify batch items
        cursor.execute(
            "SELECT ms_path FROM batch_job_items WHERE batch_id = ? ORDER BY ms_path",
            (batch_id,),
        )
        items = [row[0] for row in cursor.fetchall()]
        assert items == ["mosaic_001", "mosaic_002", "mosaic_003"]

    def test_create_batch_publish_job_empty_ids(self, temp_db):
        """Test creating batch publish job with empty data_ids."""
        conn, db_path = temp_db

        batch_id = create_batch_publish_job(conn, "batch_publish", [], {})

        cursor = conn.cursor()
        cursor.execute("SELECT total_items FROM batch_jobs WHERE id = ?", (batch_id,))
        total_items = cursor.fetchone()[0]
        assert total_items == 0

    def test_create_batch_publish_job_invalid_input(self, temp_db):
        """Test create_batch_publish_job with invalid input."""
        conn, db_path = temp_db

        with pytest.raises(ValueError, match="job_type must be a non-empty string"):
            create_batch_publish_job(conn, "", [], {})

        with pytest.raises(ValueError, match="data_ids must be a list"):
            create_batch_publish_job(conn, "batch_publish", "not_a_list", {})

        with pytest.raises(ValueError, match="All data_ids must be non-empty strings"):
            create_batch_publish_job(conn, "batch_publish", [""], {})


class TestUpdateBatchConversionItem:
    """Test update_batch_conversion_item function."""

    def test_update_batch_conversion_item(self, temp_db):
        """Test updating a batch conversion item."""
        conn, db_path = temp_db

        # Create a batch job first
        time_windows = [{"start_time": "2025-11-12T10:00:00", "end_time": "2025-11-12T10:50:00"}]
        batch_id = create_batch_conversion_job(conn, "batch_convert", time_windows, {})

        time_window_id = "time_window_2025-11-12T10:00:00_2025-11-12T10:50:00"

        # Update item status
        update_batch_conversion_item(conn, batch_id, time_window_id, 123, "running")

        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT job_id, status FROM batch_job_items
            WHERE batch_id = ? AND ms_path = ?
            """,
            (batch_id, time_window_id),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 123  # job_id
        assert row[1] == "running"  # status

        # Update to done
        update_batch_conversion_item(conn, batch_id, time_window_id, 123, "done")

        cursor.execute(
            "SELECT status FROM batch_job_items WHERE batch_id = ? AND ms_path = ?",
            (batch_id, time_window_id),
        )
        status = cursor.fetchone()[0]
        assert status == "done"
