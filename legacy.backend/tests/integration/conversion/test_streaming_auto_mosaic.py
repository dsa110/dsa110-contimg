"""Integration tests for automatic mosaic triggering in streaming converter.

Tests the sliding window overlap pattern and mosaic queue tracking.
Issue #45: Streaming Converter Lacks Automatic Mosaic Triggering
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest


class TestMosaicTrackingTables:
    """Test mosaic tracking table creation and management."""

    def test_ensure_mosaic_tracking_table_creates_tables(self, tmp_path: Path):
        """Test that _ensure_mosaic_tracking_table creates required tables."""
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            _ensure_mosaic_tracking_table,
        )

        db_path = tmp_path / "test_products.sqlite3"
        conn = sqlite3.connect(str(db_path))

        _ensure_mosaic_tracking_table(conn)

        # Check mosaic_groups table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='mosaic_groups'"
        )
        assert cursor.fetchone() is not None

        # Check mosaic_ms_membership table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='mosaic_ms_membership'"
        )
        assert cursor.fetchone() is not None

        conn.close()

    def test_ensure_mosaic_tracking_table_idempotent(self, tmp_path: Path):
        """Test that _ensure_mosaic_tracking_table is idempotent."""
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            _ensure_mosaic_tracking_table,
        )

        db_path = tmp_path / "test_products.sqlite3"
        conn = sqlite3.connect(str(db_path))

        # Call twice - should not error
        _ensure_mosaic_tracking_table(conn)
        _ensure_mosaic_tracking_table(conn)

        conn.close()


class TestMosaicGroupRegistration:
    """Test mosaic group registration functionality."""

    def test_register_mosaic_group_inserts_group(self, tmp_path: Path):
        """Test registering a new mosaic group."""
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            _ensure_mosaic_tracking_table,
            register_mosaic_group,
        )

        db_path = tmp_path / "test_products.sqlite3"

        # Pre-create tables
        conn = sqlite3.connect(str(db_path))
        _ensure_mosaic_tracking_table(conn)
        conn.close()

        # Register group
        ms_paths = [f"/data/ms/test_{i}.ms" for i in range(10)]
        register_mosaic_group(db_path, "test_group_1", ms_paths, status="pending")

        # Verify
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT group_id, status FROM mosaic_groups WHERE group_id = ?", 
                              ("test_group_1",))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "test_group_1"
        assert row[1] == "pending"

        # Verify membership
        cursor = conn.execute(
            "SELECT COUNT(*) FROM mosaic_ms_membership WHERE mosaic_group_id = ?",
            ("test_group_1",)
        )
        assert cursor.fetchone()[0] == 10

        conn.close()

    def test_register_mosaic_group_tracks_position(self, tmp_path: Path):
        """Test that MS paths are tracked with correct position in group."""
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            _ensure_mosaic_tracking_table,
            register_mosaic_group,
        )

        db_path = tmp_path / "test_products.sqlite3"

        conn = sqlite3.connect(str(db_path))
        _ensure_mosaic_tracking_table(conn)
        conn.close()

        ms_paths = [f"/data/ms/test_{i:02d}.ms" for i in range(10)]
        register_mosaic_group(db_path, "test_group_1", ms_paths)

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT ms_path, position_in_group FROM mosaic_ms_membership "
            "WHERE mosaic_group_id = ? ORDER BY position_in_group",
            ("test_group_1",)
        )
        rows = cursor.fetchall()
        assert len(rows) == 10
        for i, row in enumerate(rows):
            assert row[0] == ms_paths[i]
            assert row[1] == i
        conn.close()


class TestMosaicGroupStatusUpdate:
    """Test mosaic group status update functionality."""

    def test_update_mosaic_group_status_to_completed(self, tmp_path: Path):
        """Test updating mosaic group status to completed."""
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            _ensure_mosaic_tracking_table,
            register_mosaic_group,
            update_mosaic_group_status,
        )

        db_path = tmp_path / "test_products.sqlite3"

        conn = sqlite3.connect(str(db_path))
        _ensure_mosaic_tracking_table(conn)
        conn.close()

        ms_paths = [f"/data/ms/test_{i}.ms" for i in range(10)]
        register_mosaic_group(db_path, "test_group_1", ms_paths, status="pending")
        update_mosaic_group_status(
            db_path, "test_group_1", "completed", 
            mosaic_path="/data/mosaics/test_group_1.fits"
        )

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT status, mosaic_path FROM mosaic_groups WHERE group_id = ?",
            ("test_group_1",)
        )
        row = cursor.fetchone()
        assert row[0] == "completed"
        assert row[1] == "/data/mosaics/test_group_1.fits"
        conn.close()

    def test_update_mosaic_group_status_to_failed(self, tmp_path: Path):
        """Test updating mosaic group status to failed with error."""
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            _ensure_mosaic_tracking_table,
            register_mosaic_group,
            update_mosaic_group_status,
        )

        db_path = tmp_path / "test_products.sqlite3"

        conn = sqlite3.connect(str(db_path))
        _ensure_mosaic_tracking_table(conn)
        conn.close()

        ms_paths = [f"/data/ms/test_{i}.ms" for i in range(10)]
        register_mosaic_group(db_path, "test_group_1", ms_paths, status="in_progress")
        update_mosaic_group_status(
            db_path, "test_group_1", "failed", 
            error="Mosaic creation failed: disk full"
        )

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT status, error FROM mosaic_groups WHERE group_id = ?",
            ("test_group_1",)
        )
        row = cursor.fetchone()
        assert row[0] == "failed"
        assert "disk full" in row[1]
        conn.close()


class TestMosaicQueueStatus:
    """Test mosaic queue status API function."""

    def _setup_products_db(self, db_path: Path) -> sqlite3.Connection:
        """Set up a minimal products database with ms_index table."""
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ms_index (
                path TEXT PRIMARY KEY,
                mid_mjd REAL,
                stage TEXT,
                status TEXT
            )
        """)
        conn.commit()
        return conn

    def test_get_mosaic_queue_status_empty(self, tmp_path: Path):
        """Test getting queue status with empty database."""
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            _ensure_mosaic_tracking_table,
            get_mosaic_queue_status,
        )

        db_path = tmp_path / "test_products.sqlite3"
        conn = self._setup_products_db(db_path)
        _ensure_mosaic_tracking_table(conn)
        conn.close()

        status = get_mosaic_queue_status(db_path)

        assert status["pending_count"] == 0
        assert status["in_progress_count"] == 0
        assert status["completed_count"] == 0
        assert status["failed_count"] == 0
        assert status["available_ms_count"] == 0
        assert status["ms_until_next_mosaic"] == 8  # Need 8 new MS files

    def test_get_mosaic_queue_status_with_pending_groups(self, tmp_path: Path):
        """Test getting queue status with pending mosaic groups."""
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            _ensure_mosaic_tracking_table,
            get_mosaic_queue_status,
            register_mosaic_group,
        )

        db_path = tmp_path / "test_products.sqlite3"
        conn = self._setup_products_db(db_path)
        _ensure_mosaic_tracking_table(conn)
        conn.close()

        # Register some groups with different statuses
        for i in range(3):
            ms_paths = [f"/data/ms/group{i}_test_{j}.ms" for j in range(10)]
            register_mosaic_group(db_path, f"group_{i}", ms_paths, status="pending")

        status = get_mosaic_queue_status(db_path)
        assert status["pending_count"] == 3

    def test_get_mosaic_queue_status_counts_available_ms(self, tmp_path: Path):
        """Test that available_ms_count excludes already-mosaicked files."""
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            _ensure_mosaic_tracking_table,
            get_mosaic_queue_status,
            register_mosaic_group,
        )

        db_path = tmp_path / "test_products.sqlite3"
        conn = self._setup_products_db(db_path)
        _ensure_mosaic_tracking_table(conn)

        # Add some imaged MS files
        for i in range(15):
            conn.execute(
                "INSERT INTO ms_index (path, mid_mjd, stage, status) VALUES (?, ?, ?, ?)",
                (f"/data/ms/test_{i}.ms", 60000.0 + i * 0.01, "imaged", "done")
            )
        conn.commit()
        conn.close()

        # Register first 10 as mosaicked
        ms_paths = [f"/data/ms/test_{i}.ms" for i in range(10)]
        register_mosaic_group(db_path, "group_1", ms_paths, status="completed")

        status = get_mosaic_queue_status(db_path)
        # 15 total - 10 mosaicked = 5 available
        assert status["available_ms_count"] == 5
        # Need 8 new, have 5, so need 3 more
        assert status["ms_until_next_mosaic"] == 3


class TestCheckForCompleteGroup:
    """Test the check_for_complete_group function with sliding window."""

    def _setup_full_db(self, db_path: Path, n_ms: int = 20) -> None:
        """Set up database with ms_index entries and tracking tables."""
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            _ensure_mosaic_tracking_table,
        )

        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ms_index (
                path TEXT PRIMARY KEY,
                mid_mjd REAL,
                stage TEXT,
                status TEXT
            )
        """)
        
        # Add imaged MS files
        base_mjd = 60000.0
        for i in range(n_ms):
            conn.execute(
                "INSERT INTO ms_index (path, mid_mjd, stage, status) VALUES (?, ?, ?, ?)",
                (f"/data/ms/test_{i:02d}.ms", base_mjd + i * 0.005, "imaged", "done")
            )
        
        _ensure_mosaic_tracking_table(conn)
        conn.commit()
        conn.close()

    def test_check_for_complete_group_returns_none_if_insufficient(self, tmp_path: Path):
        """Test that check_for_complete_group returns None if not enough MS files."""
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            check_for_complete_group,
        )

        db_path = tmp_path / "test_products.sqlite3"
        # Only 5 MS files - not enough for a mosaic of 10
        self._setup_full_db(db_path, n_ms=5)

        result = check_for_complete_group(
            "/data/ms/test_03.ms", 
            db_path,
            time_window_minutes=120.0
        )
        assert result is None

    def test_check_for_complete_group_returns_first_10(self, tmp_path: Path):
        """Test that first mosaic trigger returns 10 new MS files."""
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            check_for_complete_group,
        )

        db_path = tmp_path / "test_products.sqlite3"
        self._setup_full_db(db_path, n_ms=15)

        # Trigger from file 10 - should find 10 consecutive MS files in window
        result = check_for_complete_group(
            "/data/ms/test_10.ms",
            db_path,
            time_window_minutes=120.0
        )

        assert result is not None
        assert len(result) == 10
        # Should return 10 consecutive MS files (the function returns oldest 10 new files)
        # Since all files are new (not in any mosaic), should be first 10 chronologically
        # that fall within the time window centered on test_10.ms
        # Verify all paths are unique and from our test set
        for path in result:
            assert path.startswith("/data/ms/test_")
            assert path.endswith(".ms")

    def test_check_for_complete_group_sliding_window_overlap(self, tmp_path: Path):
        """Test sliding window overlap pattern after first mosaic."""
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            check_for_complete_group,
            register_mosaic_group,
        )

        db_path = tmp_path / "test_products.sqlite3"
        self._setup_full_db(db_path, n_ms=20)

        # First mosaic: files 0-9
        first_group = [f"/data/ms/test_{i:02d}.ms" for i in range(10)]
        register_mosaic_group(db_path, "mosaic_1", first_group, status="completed")

        # Now we have 10 new files (10-19) and need 8 new + 2 overlap
        # Check from file 17 (which should trigger second mosaic)
        result = check_for_complete_group(
            "/data/ms/test_17.ms",
            db_path,
            time_window_minutes=120.0
        )

        assert result is not None
        assert len(result) == 10
        # Should include 2 overlap files from first mosaic (files 8, 9)
        # and 8 new files (files 10-17)
        assert "/data/ms/test_08.ms" in result
        assert "/data/ms/test_09.ms" in result
        for i in range(10, 18):
            assert f"/data/ms/test_{i:02d}.ms" in result

    def test_check_for_complete_group_prevents_duplicates(self, tmp_path: Path):
        """Test that same MS files aren't returned for new mosaics."""
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            check_for_complete_group,
            register_mosaic_group,
        )

        db_path = tmp_path / "test_products.sqlite3"
        self._setup_full_db(db_path, n_ms=12)

        # Register first mosaic with files 0-9
        first_group = [f"/data/ms/test_{i:02d}.ms" for i in range(10)]
        register_mosaic_group(db_path, "mosaic_1", first_group, status="completed")

        # Only 2 new files (10, 11) - not enough for next mosaic (need 8 new)
        result = check_for_complete_group(
            "/data/ms/test_11.ms",
            db_path,
            time_window_minutes=120.0
        )

        # Should return None - only 2 new files, need 8
        assert result is None


class TestTriggerGroupMosaicCreation:
    """Test the trigger_group_mosaic_creation function."""

    def _setup_db(self, db_path: Path) -> None:
        """Set up minimal database."""
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            _ensure_mosaic_tracking_table,
        )
        
        conn = sqlite3.connect(str(db_path))
        _ensure_mosaic_tracking_table(conn)
        conn.close()

    @patch("dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator")
    def test_trigger_registers_group_before_processing(
        self, mock_orchestrator_cls, tmp_path: Path
    ):
        """Test that trigger_group_mosaic_creation registers group first."""
        import argparse
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            trigger_group_mosaic_creation,
        )

        db_path = tmp_path / "test_products.sqlite3"
        self._setup_db(db_path)

        # Mock orchestrator
        mock_orchestrator = MagicMock()
        mock_orchestrator._form_group_from_ms_paths.return_value = True
        mock_orchestrator._process_group_workflow.return_value = "/data/mosaics/test.fits"
        mock_orchestrator_cls.return_value = mock_orchestrator

        args = argparse.Namespace()
        ms_paths = [f"/data/ms/2025-01-15T12:00:{i:02d}_test.ms" for i in range(10)]

        result = trigger_group_mosaic_creation(ms_paths, db_path, args)

        # Check group was registered
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT COUNT(*) FROM mosaic_groups")
        assert cursor.fetchone()[0] == 1
        conn.close()

        assert result == "/data/mosaics/test.fits"

    @patch("dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator")
    def test_trigger_updates_status_on_success(
        self, mock_orchestrator_cls, tmp_path: Path
    ):
        """Test that trigger updates status to completed on success."""
        import argparse
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            trigger_group_mosaic_creation,
        )

        db_path = tmp_path / "test_products.sqlite3"
        self._setup_db(db_path)

        mock_orchestrator = MagicMock()
        mock_orchestrator._form_group_from_ms_paths.return_value = True
        mock_orchestrator._process_group_workflow.return_value = "/data/mosaics/test.fits"
        mock_orchestrator_cls.return_value = mock_orchestrator

        args = argparse.Namespace()
        ms_paths = [f"/data/ms/2025-01-15T12:00:{i:02d}_test.ms" for i in range(10)]

        trigger_group_mosaic_creation(ms_paths, db_path, args)

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT status, mosaic_path FROM mosaic_groups")
        row = cursor.fetchone()
        assert row[0] == "completed"
        assert row[1] == "/data/mosaics/test.fits"
        conn.close()

    @patch("dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator")
    def test_trigger_updates_status_on_failure(
        self, mock_orchestrator_cls, tmp_path: Path
    ):
        """Test that trigger updates status to failed on failure."""
        import argparse
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            trigger_group_mosaic_creation,
        )

        db_path = tmp_path / "test_products.sqlite3"
        self._setup_db(db_path)

        mock_orchestrator = MagicMock()
        mock_orchestrator._form_group_from_ms_paths.return_value = True
        mock_orchestrator._process_group_workflow.return_value = None  # Failure
        mock_orchestrator_cls.return_value = mock_orchestrator

        args = argparse.Namespace()
        ms_paths = [f"/data/ms/2025-01-15T12:00:{i:02d}_test.ms" for i in range(10)]

        result = trigger_group_mosaic_creation(ms_paths, db_path, args)

        assert result is None

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT status, error FROM mosaic_groups")
        row = cursor.fetchone()
        assert row[0] == "failed"
        assert "Orchestrator returned None" in row[1]
        conn.close()

    @patch("dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator")
    def test_trigger_handles_form_group_failure(
        self, mock_orchestrator_cls, tmp_path: Path
    ):
        """Test that trigger handles group formation failure."""
        import argparse
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            trigger_group_mosaic_creation,
        )

        db_path = tmp_path / "test_products.sqlite3"
        self._setup_db(db_path)

        mock_orchestrator = MagicMock()
        mock_orchestrator._form_group_from_ms_paths.return_value = False
        mock_orchestrator_cls.return_value = mock_orchestrator

        args = argparse.Namespace()
        ms_paths = [f"/data/ms/2025-01-15T12:00:{i:02d}_test.ms" for i in range(10)]

        result = trigger_group_mosaic_creation(ms_paths, db_path, args)

        assert result is None

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT status, error FROM mosaic_groups")
        row = cursor.fetchone()
        assert row[0] == "failed"
        assert "Failed to form group" in row[1]
        conn.close()


class TestMosaicConstants:
    """Test that mosaic constants are properly defined."""

    def test_constants_defined(self):
        """Test that mosaic grouping constants are defined."""
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            MS_NEW_PER_TRIGGER,
            MS_OVERLAP,
            MS_PER_MOSAIC,
        )

        assert MS_PER_MOSAIC == 10
        assert MS_OVERLAP == 2
        assert MS_NEW_PER_TRIGGER == 8
        assert MS_NEW_PER_TRIGGER == MS_PER_MOSAIC - MS_OVERLAP
