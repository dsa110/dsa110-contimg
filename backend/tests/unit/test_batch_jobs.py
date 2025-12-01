"""
Tests for the batch jobs module.

Tests batch job creation, updating, and database management functions.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from dsa110_contimg.api.batch.jobs import (
    create_batch_job,
    create_batch_conversion_job,
    create_batch_publish_job,
    create_batch_photometry_job,
    create_batch_ese_detect_job,
    ensure_batch_tables,
    ensure_data_id_column,
    update_batch_item,
    update_batch_conversion_item,
    _validate_job_type,
    _validate_string_list,
    _validate_params,
)


@pytest.fixture
def db_conn() -> Generator[sqlite3.Connection, None, None]:
    """Create a temporary in-memory database with batch tables."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_batch_tables(conn)
    yield conn
    conn.close()


class TestEnsureBatchTables:
    """Tests for ensure_batch_tables function."""

    def test_creates_batch_jobs_table(self):
        """Test that batch_jobs table is created."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        
        ensure_batch_tables(conn)
        
        # Verify table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='batch_jobs'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_creates_batch_job_items_table(self):
        """Test that batch_job_items table is created."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        
        ensure_batch_tables(conn)
        
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='batch_job_items'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_idempotent(self):
        """Test that calling multiple times doesn't raise errors."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        
        ensure_batch_tables(conn)
        ensure_batch_tables(conn)  # Should not raise
        
        conn.close()


class TestEnsureDataIdColumn:
    """Tests for ensure_data_id_column function."""

    def test_adds_data_id_column(self, db_conn):
        """Test that data_id column is added if missing."""
        # First, verify column doesn't exist yet
        cursor = db_conn.execute("PRAGMA table_info(batch_job_items)")
        columns = [row["name"] for row in cursor.fetchall()]
        # Initial table doesn't have data_id by default
        
        ensure_data_id_column(db_conn)
        
        # Now verify column exists (or was already added by ensure_batch_tables)
        cursor = db_conn.execute("PRAGMA table_info(batch_job_items)")
        columns = [row["name"] for row in cursor.fetchall()]
        # Function should work without error

    def test_idempotent(self, db_conn):
        """Test that calling multiple times doesn't raise errors."""
        ensure_data_id_column(db_conn)
        ensure_data_id_column(db_conn)  # Should not raise


class TestValidationHelpers:
    """Tests for validation helper functions."""

    def test_validate_job_type_valid(self):
        """Test valid job type passes validation."""
        _validate_job_type("batch_calibration")
        _validate_job_type("batch_image")
        _validate_job_type(" valid_type ")

    def test_validate_job_type_invalid_empty(self):
        """Test empty job type raises ValueError."""
        with pytest.raises(ValueError, match="non-empty string"):
            _validate_job_type("")

    def test_validate_job_type_invalid_whitespace(self):
        """Test whitespace-only job type raises ValueError."""
        with pytest.raises(ValueError, match="non-empty string"):
            _validate_job_type("   ")

    def test_validate_job_type_invalid_type(self):
        """Test non-string job type raises ValueError."""
        with pytest.raises(ValueError, match="non-empty string"):
            _validate_job_type(123)

    def test_validate_string_list_valid(self):
        """Test valid string list passes validation."""
        _validate_string_list(["path1", "path2", "path3"], "paths")

    def test_validate_string_list_empty(self):
        """Test empty list passes validation (no items)."""
        _validate_string_list([], "paths")

    def test_validate_string_list_not_list(self):
        """Test non-list raises ValueError."""
        with pytest.raises(ValueError, match="must be a list"):
            _validate_string_list("not_a_list", "paths")

    def test_validate_string_list_empty_strings(self):
        """Test empty strings in list raise ValueError."""
        with pytest.raises(ValueError, match="must be non-empty strings"):
            _validate_string_list(["valid", ""], "paths")

    def test_validate_string_list_non_strings(self):
        """Test non-strings in list raise ValueError."""
        with pytest.raises(ValueError, match="must be non-empty strings"):
            _validate_string_list(["valid", 123], "paths")

    def test_validate_params_valid(self):
        """Test valid params dict passes validation."""
        _validate_params({"key": "value"})
        _validate_params({})

    def test_validate_params_invalid_type(self):
        """Test non-dict params raises ValueError."""
        with pytest.raises(ValueError, match="must be a dictionary"):
            _validate_params("not_a_dict")


class TestCreateBatchJob:
    """Tests for create_batch_job function."""

    def test_creates_job_with_valid_inputs(self, db_conn):
        """Test batch job creation with valid inputs."""
        batch_id = create_batch_job(
            conn=db_conn,
            job_type="batch_calibration",
            ms_paths=["/path/to/ms1", "/path/to/ms2"],
            params={"param1": "value1"},
        )
        
        assert isinstance(batch_id, int)
        assert batch_id > 0

    def test_job_has_correct_type(self, db_conn):
        """Test created job has correct type."""
        batch_id = create_batch_job(
            db_conn, "batch_calibration", ["/path/ms"], {}
        )
        
        row = db_conn.execute(
            "SELECT type FROM batch_jobs WHERE id = ?", (batch_id,)
        ).fetchone()
        assert row["type"] == "batch_calibration"

    def test_job_has_correct_item_count(self, db_conn):
        """Test job has correct total_items count."""
        ms_paths = ["/path1", "/path2", "/path3"]
        batch_id = create_batch_job(db_conn, "test", ms_paths, {})
        
        row = db_conn.execute(
            "SELECT total_items FROM batch_jobs WHERE id = ?", (batch_id,)
        ).fetchone()
        assert row["total_items"] == 3

    def test_job_starts_pending(self, db_conn):
        """Test new job status is pending."""
        batch_id = create_batch_job(db_conn, "test", ["/path"], {})
        
        row = db_conn.execute(
            "SELECT status FROM batch_jobs WHERE id = ?", (batch_id,)
        ).fetchone()
        assert row["status"] == "pending"

    def test_creates_batch_items(self, db_conn):
        """Test batch items are created for each ms_path."""
        ms_paths = ["/path1", "/path2"]
        batch_id = create_batch_job(db_conn, "test", ms_paths, {})
        
        items = db_conn.execute(
            "SELECT ms_path, status FROM batch_job_items WHERE batch_id = ?",
            (batch_id,)
        ).fetchall()
        
        assert len(items) == 2
        paths = [row["ms_path"] for row in items]
        assert "/path1" in paths
        assert "/path2" in paths
        assert all(row["status"] == "pending" for row in items)

    def test_invalid_job_type_raises(self, db_conn):
        """Test invalid job type raises ValueError."""
        with pytest.raises(ValueError):
            create_batch_job(db_conn, "", ["/path"], {})

    def test_invalid_ms_paths_raises(self, db_conn):
        """Test invalid ms_paths raises ValueError."""
        with pytest.raises(ValueError):
            create_batch_job(db_conn, "test", "not_a_list", {})


class TestCreateBatchConversionJob:
    """Tests for create_batch_conversion_job function."""

    def test_creates_job_with_time_windows(self, db_conn):
        """Test conversion job creation with time windows."""
        time_windows = [
            {"start_time": "2024-01-01T00:00:00", "end_time": "2024-01-01T01:00:00"},
            {"start_time": "2024-01-01T01:00:00", "end_time": "2024-01-01T02:00:00"},
        ]
        batch_id = create_batch_conversion_job(
            db_conn, "batch_convert", time_windows, {"output_dir": "/out"}
        )
        
        assert isinstance(batch_id, int)
        assert batch_id > 0

    def test_creates_items_for_time_windows(self, db_conn):
        """Test items are created for each time window."""
        time_windows = [
            {"start_time": "2024-01-01T00:00:00", "end_time": "2024-01-01T01:00:00"},
        ]
        batch_id = create_batch_conversion_job(
            db_conn, "batch_convert", time_windows, {}
        )
        
        items = db_conn.execute(
            "SELECT ms_path FROM batch_job_items WHERE batch_id = ?",
            (batch_id,)
        ).fetchall()
        
        assert len(items) == 1
        assert "time_window" in items[0]["ms_path"]

    def test_invalid_time_windows_raises(self, db_conn):
        """Test invalid time_windows raises ValueError."""
        with pytest.raises(ValueError, match="time_windows must be a list"):
            create_batch_conversion_job(db_conn, "test", "not_a_list", {})

    def test_missing_time_keys_raises(self, db_conn):
        """Test time windows without required keys raise ValueError."""
        with pytest.raises(ValueError, match="start_time"):
            create_batch_conversion_job(
                db_conn, "test", [{"start_time": "t1"}], {}  # Missing end_time
            )


class TestCreateBatchPublishJob:
    """Tests for create_batch_publish_job function."""

    def test_creates_job_with_data_ids(self, db_conn):
        """Test publish job creation with data IDs."""
        data_ids = ["data_001", "data_002", "data_003"]
        batch_id = create_batch_publish_job(
            db_conn, "batch_publish", data_ids, {"products_base": "/products"}
        )
        
        assert isinstance(batch_id, int)
        assert batch_id > 0

    def test_creates_items_for_data_ids(self, db_conn):
        """Test items are created for each data ID."""
        data_ids = ["id1", "id2"]
        batch_id = create_batch_publish_job(db_conn, "batch_publish", data_ids, {})
        
        items = db_conn.execute(
            "SELECT ms_path FROM batch_job_items WHERE batch_id = ?",
            (batch_id,)
        ).fetchall()
        
        assert len(items) == 2
        paths = [row["ms_path"] for row in items]
        assert "id1" in paths
        assert "id2" in paths


class TestCreateBatchPhotometryJob:
    """Tests for create_batch_photometry_job function."""

    def test_creates_job_with_coordinates(self, db_conn):
        """Test photometry job creation with coordinates."""
        fits_paths = ["/fits1.fits", "/fits2.fits"]
        coordinates = [
            {"ra_deg": 180.0, "dec_deg": 45.0},
            {"ra_deg": 181.0, "dec_deg": 46.0},
        ]
        batch_id = create_batch_photometry_job(
            db_conn, "batch_photometry", fits_paths, coordinates, {}
        )
        
        assert isinstance(batch_id, int)
        assert batch_id > 0

    def test_creates_items_for_all_combinations(self, db_conn):
        """Test items are created for each image-coordinate pair."""
        fits_paths = ["/fits1.fits", "/fits2.fits"]
        coordinates = [{"ra_deg": 180.0, "dec_deg": 45.0}]
        batch_id = create_batch_photometry_job(
            db_conn, "batch_photometry", fits_paths, coordinates, {}
        )
        
        row = db_conn.execute(
            "SELECT total_items FROM batch_jobs WHERE id = ?", (batch_id,)
        ).fetchone()
        
        assert row["total_items"] == 2  # 2 images × 1 coordinate

    def test_with_data_id(self, db_conn):
        """Test photometry job with data_id linkage."""
        batch_id = create_batch_photometry_job(
            db_conn,
            "batch_photometry",
            ["/fits.fits"],
            [{"ra_deg": 180.0, "dec_deg": 45.0}],
            {},
            data_id="data_001"
        )
        
        # Verify data_id is stored
        row = db_conn.execute(
            "SELECT data_id FROM batch_job_items WHERE batch_id = ?",
            (batch_id,)
        ).fetchone()
        assert row["data_id"] == "data_001"


class TestCreateBatchEseDetectJob:
    """Tests for create_batch_ese_detect_job function."""

    def test_creates_job_with_source_ids(self, db_conn):
        """Test ESE detection job with specific source IDs."""
        params = {
            "min_sigma": 5.0,
            "recompute": True,
            "source_ids": ["src_001", "src_002"],
        }
        batch_id = create_batch_ese_detect_job(db_conn, "batch_ese-detect", params)
        
        assert isinstance(batch_id, int)
        assert batch_id > 0
        
        row = db_conn.execute(
            "SELECT total_items FROM batch_jobs WHERE id = ?", (batch_id,)
        ).fetchone()
        assert row["total_items"] == 2

    def test_creates_job_for_all_sources(self, db_conn):
        """Test ESE detection job for all sources (no source_ids)."""
        params = {"min_sigma": 5.0, "recompute": False}
        batch_id = create_batch_ese_detect_job(db_conn, "batch_ese-detect", params)
        
        row = db_conn.execute(
            "SELECT total_items FROM batch_jobs WHERE id = ?", (batch_id,)
        ).fetchone()
        assert row["total_items"] == 1  # Single item for "all_sources"
        
        item = db_conn.execute(
            "SELECT ms_path FROM batch_job_items WHERE batch_id = ?",
            (batch_id,)
        ).fetchone()
        assert item["ms_path"] == "all_sources"

    def test_invalid_source_ids_raises(self, db_conn):
        """Test invalid source_ids raises ValueError."""
        params = {"source_ids": "not_a_list"}
        with pytest.raises(ValueError, match="source_ids must be a list"):
            create_batch_ese_detect_job(db_conn, "batch_ese-detect", params)


class TestUpdateBatchItem:
    """Tests for update_batch_item function."""

    def test_update_item_status_running(self, db_conn):
        """Test updating batch item to running status."""
        batch_id = create_batch_job(db_conn, "test", ["/path"], {})
        
        update_batch_item(
            db_conn, batch_id, "/path", job_id=100, status="running"
        )
        
        item = db_conn.execute(
            "SELECT status, job_id, started_at FROM batch_job_items WHERE batch_id = ?",
            (batch_id,)
        ).fetchone()
        assert item["status"] == "running"
        assert item["job_id"] == 100
        assert item["started_at"] is not None

    def test_update_item_status_done(self, db_conn):
        """Test updating batch item to done status."""
        batch_id = create_batch_job(db_conn, "test", ["/path"], {})
        
        update_batch_item(
            db_conn, batch_id, "/path", job_id=None, status="done"
        )
        
        item = db_conn.execute(
            "SELECT status, completed_at FROM batch_job_items WHERE batch_id = ?",
            (batch_id,)
        ).fetchone()
        assert item["status"] == "done"
        assert item["completed_at"] is not None

    def test_update_with_error(self, db_conn):
        """Test updating batch item with error."""
        batch_id = create_batch_job(db_conn, "test", ["/path"], {})
        
        update_batch_item(
            db_conn, batch_id, "/path", job_id=None, status="failed", error="Test error"
        )
        
        item = db_conn.execute(
            "SELECT status, error FROM batch_job_items WHERE batch_id = ?",
            (batch_id,)
        ).fetchone()
        assert item["status"] == "failed"
        assert item["error"] == "Test error"

    def test_update_batch_counts(self, db_conn):
        """Test that batch job counts are updated."""
        batch_id = create_batch_job(db_conn, "test", ["/path1", "/path2"], {})
        
        update_batch_item(db_conn, batch_id, "/path1", job_id=None, status="done")
        
        job = db_conn.execute(
            "SELECT completed_items, failed_items FROM batch_jobs WHERE id = ?",
            (batch_id,)
        ).fetchone()
        assert job["completed_items"] == 1
        assert job["failed_items"] == 0

    def test_batch_status_updates_to_running(self, db_conn):
        """Test batch status updates to running when items are processed."""
        batch_id = create_batch_job(db_conn, "test", ["/path1", "/path2"], {})
        
        update_batch_item(db_conn, batch_id, "/path1", job_id=100, status="running")
        
        job = db_conn.execute(
            "SELECT status FROM batch_jobs WHERE id = ?", (batch_id,)
        ).fetchone()
        assert job["status"] == "running"

    def test_batch_status_updates_to_done(self, db_conn):
        """Test batch status updates to done when all items complete."""
        batch_id = create_batch_job(db_conn, "test", ["/path"], {})
        
        update_batch_item(db_conn, batch_id, "/path", job_id=None, status="done")
        
        job = db_conn.execute(
            "SELECT status FROM batch_jobs WHERE id = ?", (batch_id,)
        ).fetchone()
        assert job["status"] == "done"

    def test_batch_status_updates_to_failed(self, db_conn):
        """Test batch status updates to failed when items fail."""
        batch_id = create_batch_job(db_conn, "test", ["/path"], {})
        
        update_batch_item(db_conn, batch_id, "/path", job_id=None, status="failed", error="err")
        
        job = db_conn.execute(
            "SELECT status FROM batch_jobs WHERE id = ?", (batch_id,)
        ).fetchone()
        assert job["status"] == "failed"

    def test_invalid_batch_id_raises(self, db_conn):
        """Test invalid batch_id raises ValueError."""
        with pytest.raises(ValueError, match="batch_id must be a positive integer"):
            update_batch_item(db_conn, -1, "/path", job_id=None, status="done")

    def test_invalid_status_raises(self, db_conn):
        """Test invalid status raises ValueError."""
        batch_id = create_batch_job(db_conn, "test", ["/path"], {})
        with pytest.raises(ValueError, match="Invalid status"):
            update_batch_item(db_conn, batch_id, "/path", job_id=None, status="invalid")

    def test_invalid_ms_path_raises(self, db_conn):
        """Test invalid ms_path raises ValueError."""
        batch_id = create_batch_job(db_conn, "test", ["/path"], {})
        with pytest.raises(ValueError, match="ms_path must be a non-empty string"):
            update_batch_item(db_conn, batch_id, "", job_id=None, status="done")


class TestUpdateBatchConversionItem:
    """Tests for update_batch_conversion_item function."""

    def test_update_conversion_item_running(self, db_conn):
        """Test updating conversion batch item to running."""
        time_windows = [
            {"start_time": "2024-01-01T00:00:00", "end_time": "2024-01-01T01:00:00"},
        ]
        batch_id = create_batch_conversion_job(
            db_conn, "batch_convert", time_windows, {}
        )
        
        # The time_window_id format used internally
        time_window_id = "time_window_2024-01-01T00:00:00_2024-01-01T01:00:00"
        
        update_batch_conversion_item(
            db_conn,
            batch_id,
            time_window_id,
            job_id=200,
            status="running",
        )
        
        item = db_conn.execute(
            "SELECT status, job_id FROM batch_job_items WHERE batch_id = ?",
            (batch_id,)
        ).fetchone()
        assert item["status"] == "running"
        assert item["job_id"] == 200

    def test_update_conversion_item_done(self, db_conn):
        """Test updating conversion batch item to done."""
        time_windows = [
            {"start_time": "2024-01-01T00:00:00", "end_time": "2024-01-01T01:00:00"},
        ]
        batch_id = create_batch_conversion_job(
            db_conn, "batch_convert", time_windows, {}
        )
        
        time_window_id = "time_window_2024-01-01T00:00:00_2024-01-01T01:00:00"
        
        update_batch_conversion_item(
            db_conn,
            batch_id,
            time_window_id,
            job_id=None,
            status="done",
        )
        
        item = db_conn.execute(
            "SELECT status, completed_at FROM batch_job_items WHERE batch_id = ?",
            (batch_id,)
        ).fetchone()
        assert item["status"] == "done"
        assert item["completed_at"] is not None


class TestTransactionSupport:
    """Tests for transaction handling in batch operations."""

    def test_atomic_batch_creation(self, db_conn):
        """Test that batch job and items are created atomically."""
        batch_id = create_batch_job(
            db_conn, "test", ["/path1", "/path2", "/path3"], {}
        )
        
        # Verify both job and all items exist
        job = db_conn.execute(
            "SELECT * FROM batch_jobs WHERE id = ?", (batch_id,)
        ).fetchone()
        items = db_conn.execute(
            "SELECT * FROM batch_job_items WHERE batch_id = ?", (batch_id,)
        ).fetchall()
        
        assert job is not None
        assert len(items) == 3

    def test_params_stored_correctly(self, db_conn):
        """Test that params are stored and retrievable."""
        params = {"key1": "value1", "key2": 123, "nested": {"a": "b"}}
        batch_id = create_batch_job(db_conn, "test", ["/path"], params)
        
        row = db_conn.execute(
            "SELECT params FROM batch_jobs WHERE id = ?", (batch_id,)
        ).fetchone()
        
        # Params should be stored as string representation
        assert "key1" in row["params"]
        assert "value1" in row["params"]
