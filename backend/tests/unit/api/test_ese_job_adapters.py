"""Unit tests for ESE detection job adapters.

Focus: Fast tests for run_ese_detect_job and run_batch_ese_detect_job functions.
"""

from __future__ import annotations

import sqlite3
import time
from unittest.mock import patch

import pytest

from dsa110_contimg.api.job_adapters import run_batch_ese_detect_job, run_ese_detect_job
from dsa110_contimg.database.products import ensure_products_db


@pytest.fixture
def temp_products_db(tmp_path):
    """Create temporary products database with jobs tables."""
    db_path = tmp_path / "products.sqlite3"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE jobs (
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
            completed_at REAL,
            FOREIGN KEY (batch_id) REFERENCES batch_jobs(id)
        )
        """
    )

    conn.commit()
    conn.close()
    return db_path


class TestRunESEDetectJob:
    """Test run_ese_detect_job function."""

    @patch("dsa110_contimg.photometry.ese_detection.detect_ese_candidates")
    def test_run_ese_detect_job_success(self, mock_detect, temp_products_db):
        """Test successful ESE detection job execution."""
        mock_detect.return_value = [
            {
                "source_id": "source_001",
                "significance": 6.5,
            }
        ]

        conn = ensure_products_db(temp_products_db)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO jobs (type, status, ms_path, params, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("ese-detect", "pending", "", '{"min_sigma": 5.0}', time.time()),
        )
        job_id = cursor.lastrowid
        conn.commit()
        conn.close()

        params = {"min_sigma": 5.0, "source_id": None, "recompute": False}
        run_ese_detect_job(job_id, params, temp_products_db)

        # Verify job status updated
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        status = cursor.fetchone()[0]
        assert status == "done"
        conn.close()

        mock_detect.assert_called_once_with(
            products_db=temp_products_db,
            min_sigma=5.0,
            source_id=None,
            recompute=False,
            use_composite_scoring=False,
            scoring_weights=None,
        )

    @patch("dsa110_contimg.photometry.ese_detection.detect_ese_candidates")
    def test_run_ese_detect_job_failure(self, mock_detect, temp_products_db):
        """Test ESE detection job failure handling."""
        mock_detect.side_effect = Exception("Test error")

        conn = ensure_products_db(temp_products_db)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO jobs (type, status, ms_path, params, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("ese-detect", "pending", "", '{"min_sigma": 5.0}', time.time()),
        )
        job_id = cursor.lastrowid
        conn.commit()
        conn.close()

        params = {"min_sigma": 5.0}
        with pytest.raises(Exception):
            run_ese_detect_job(job_id, params, temp_products_db)

        # Verify job status updated to failed
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        status = cursor.fetchone()[0]
        assert status == "failed"
        conn.close()


class TestRunBatchESEDetectJob:
    """Test run_batch_ese_detect_job function."""

    @patch("dsa110_contimg.photometry.ese_detection.detect_ese_candidates")
    def test_run_batch_ese_detect_job_all_sources(self, mock_detect, temp_products_db):
        """Test batch ESE detection for all sources."""
        mock_detect.return_value = [
            {"source_id": "source_001", "significance": 6.5},
            {"source_id": "source_002", "significance": 7.2},
        ]

        conn = ensure_products_db(temp_products_db)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO batch_jobs (type, created_at, status, total_items, params)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("batch_ese-detect", time.time(), "pending", 1, '{"min_sigma": 5.0}'),
        )
        batch_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO batch_job_items (batch_id, ms_path, status)
            VALUES (?, ?, ?)
            """,
            (batch_id, "all_sources", "pending"),
        )
        conn.commit()
        conn.close()

        params = {"min_sigma": 5.0, "recompute": False, "source_ids": None}
        run_batch_ese_detect_job(batch_id, params, temp_products_db)

        # Verify batch job status
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM batch_jobs WHERE id = ?", (batch_id,))
        status = cursor.fetchone()[0]
        assert status == "done"
        conn.close()

    @patch("dsa110_contimg.photometry.ese_detection.detect_ese_candidates")
    def test_run_batch_ese_detect_job_specific_sources(self, mock_detect, temp_products_db):
        """Test batch ESE detection for specific source IDs."""
        mock_detect.return_value = [{"source_id": "source_001", "significance": 6.5}]

        conn = ensure_products_db(temp_products_db)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO batch_jobs (type, created_at, status, total_items, params)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("batch_ese-detect", time.time(), "pending", 2, '{"min_sigma": 5.0}'),
        )
        batch_id = cursor.lastrowid
        for source_id in ["source_001", "source_002"]:
            cursor.execute(
                """
                INSERT INTO batch_job_items (batch_id, ms_path, status)
                VALUES (?, ?, ?)
                """,
                (batch_id, source_id, "pending"),
            )
        conn.commit()
        conn.close()

        params = {
            "min_sigma": 5.0,
            "recompute": False,
            "source_ids": ["source_001", "source_002"],
        }
        run_batch_ese_detect_job(batch_id, params, temp_products_db)

        # Verify batch job status
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM batch_jobs WHERE id = ?", (batch_id,))
        status = cursor.fetchone()[0]
        assert status == "done"
        conn.close()

    @patch("dsa110_contimg.photometry.ese_detection.detect_ese_candidates")
    def test_run_batch_ese_detect_job_partial_failure(self, mock_detect, temp_products_db):
        """Test batch ESE detection with partial failures."""

        def side_effect(products_db, min_sigma, source_id, recompute):
            if source_id == "source_001":
                return [{"source_id": "source_001", "significance": 6.5}]
            else:
                raise Exception("Test error")

        mock_detect.side_effect = side_effect

        conn = ensure_products_db(temp_products_db)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO batch_jobs (type, created_at, status, total_items, params)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("batch_ese-detect", time.time(), "pending", 2, '{"min_sigma": 5.0}'),
        )
        batch_id = cursor.lastrowid
        for source_id in ["source_001", "source_002"]:
            cursor.execute(
                """
                INSERT INTO batch_job_items (batch_id, ms_path, status)
                VALUES (?, ?, ?)
                """,
                (batch_id, source_id, "pending"),
            )
        conn.commit()
        conn.close()

        params = {
            "min_sigma": 5.0,
            "source_ids": ["source_001", "source_002"],
        }
        run_batch_ese_detect_job(batch_id, params, temp_products_db)

        # Verify batch job status is partial
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status, completed_items, failed_items FROM batch_jobs WHERE id = ?",
            (batch_id,),
        )
        row = cursor.fetchone()
        # When all items fail in source_ids batch (no completed), status is 'failed'
        assert row[0] == "failed"
        assert row[1] == 0
        assert row[2] == 2
        conn.close()
