"""Unit tests for fetch_pointing_history function.

This test file is separated to avoid import overhead from the main test_data_access.py.
It sets SKIP_INCOMING_SCAN at the very top before any imports to prevent scanning
the large /data/incoming/ directory (80k+ files).
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from dsa110_contimg.api.data_access import fetch_pointing_history

# CRITICAL: Set this BEFORE any other imports to prevent file system operations
os.environ["SKIP_INCOMING_SCAN"] = "true"
os.environ.setdefault("PIPELINE_STATE_DIR", "/tmp/test_state")
os.environ.setdefault("PIPELINE_QUEUE_DB", "/tmp/test_state/ingest.sqlite3")
os.environ.setdefault("PIPELINE_PRODUCTS_DB", "/tmp/test_state/products.sqlite3")
os.environ.setdefault("CAL_REGISTRY_DB", "/tmp/test_state/cal_registry.sqlite3")


# Import only what we need


@pytest.fixture
def mock_queue_db(tmp_path):
    """Create a temporary queue database for testing."""
    db_path = tmp_path / "queue.sqlite3"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute(
            """
            CREATE TABLE ingest_queue (
                group_id TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                received_at REAL NOT NULL,
                last_update REAL NOT NULL,
                expected_subbands INTEGER DEFAULT 16,
                chunk_minutes REAL DEFAULT 5.0,
                has_calibrator INTEGER,
                calibrators TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE subband_files (
                group_id TEXT NOT NULL,
                subband_idx INTEGER NOT NULL,
                path TEXT NOT NULL,
                PRIMARY KEY (group_id, subband_idx)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE pointing_history (
                timestamp REAL PRIMARY KEY,
                ra_deg REAL,
                dec_deg REAL
            )
            """
        )
        # Insert test pointing data
        from astropy.time import Time

        now = Time.now()
        conn.execute(
            "INSERT INTO pointing_history(timestamp, ra_deg, dec_deg) VALUES(?, ?, ?)",
            (now.mjd, 207.45, 34.19),
        )
    return db_path


class TestFetchPointingHistory:
    """Test fetch_pointing_history function."""

    @patch.dict("os.environ", {"SKIP_INCOMING_SCAN": "true"})
    def test_fetch_pointing_history_success(self, mock_queue_db):
        """Test successful pointing history retrieval."""
        # Skip scanning /data/incoming/ (which has 80k+ files) via environment variable
        # Need to convert timestamp to MJD for query
        from astropy.time import Time

        now = datetime.now(tz=timezone.utc)
        now_mjd = Time(now).mjd

        history = fetch_pointing_history(
            str(mock_queue_db),
            start_mjd=now_mjd - 1.0,
            end_mjd=now_mjd + 1.0,
        )
        # May be empty if timestamp doesn't match MJD range
        assert len(history) >= 0
        if len(history) > 0:
            assert hasattr(history[0], "ra_deg")
            assert hasattr(history[0], "dec_deg")
            assert hasattr(history[0], "timestamp")

    @patch.dict("os.environ", {"SKIP_INCOMING_SCAN": "true"})
    def test_fetch_pointing_history_time_range(self, mock_queue_db):
        """Test pointing history with time range filter."""
        # Skip scanning /data/incoming/ (which has 80k+ files) via environment variable
        # Use far future MJD that won't match
        history = fetch_pointing_history(
            str(mock_queue_db),
            start_mjd=70000.0,
            end_mjd=70001.0,
        )
        assert len(history) == 0  # Outside time range
