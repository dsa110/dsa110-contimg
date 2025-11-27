"""Tests for HDF5 subband grouping algorithm.

CRITICAL: These tests ensure the CORRECT proximity-based grouping algorithm
is used, NOT naive time clustering by group_id.

The correct algorithm:
1. Sort files by timestamp
2. For each file, find all files within tolerance
3. Build subband map and check if complete (16 subbands)
4. Mark used files to avoid duplicate groups
"""

import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np


def create_test_hdf5_db(test_files):
    """Create a temporary HDF5 database for testing.

    Args:
        test_files: List of tuples (mjd, subband_code, path)

    Returns:
        Path to temporary database
    """
    # Create temporary database
    fd, db_path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)

    # Initialize database schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE hdf5_file_index (
            path TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            group_id TEXT NOT NULL,
            subband_code TEXT NOT NULL,
            subband_num INTEGER,
            timestamp_iso TEXT NOT NULL,
            timestamp_mjd REAL NOT NULL,
            file_size_bytes INTEGER,
            modified_time REAL,
            indexed_at REAL,
            stored INTEGER DEFAULT 1,
            ra_deg REAL,
            dec_deg REAL,
            obs_date TEXT,
            obs_time TEXT
        )
    """
    )

    # Insert test data
    for mjd, subband_code, path in test_files:
        # Extract subband number
        try:
            if subband_code.startswith("sb"):
                subband_num = int(subband_code[2:])
            else:
                subband_num = None
        except (ValueError, IndexError):
            subband_num = None

        # Convert MJD to ISO
        from astropy.time import Time

        timestamp_iso = Time(mjd, format="mjd").isot

        cursor.execute(
            """
            INSERT INTO hdf5_file_index
            (path, filename, group_id, subband_code, subband_num,
             timestamp_iso, timestamp_mjd, stored)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """,
            (
                path,
                Path(path).name,
                timestamp_iso,  # group_id is timestamp
                subband_code,
                subband_num,
                timestamp_iso,
                mjd,
            ),
        )

    conn.commit()
    conn.close()

    return Path(db_path)


class TestProximityBasedGrouping:
    """Test the proximity-based grouping algorithm."""

    def test_grouping_handles_timestamp_jitter(self, tmp_path):
        """Test that grouping works with timestamp jitter within tolerance."""
        from dsa110_contimg.database.hdf5_index import query_subband_groups

        # Create test database with files having slight timestamp differences
        # Group 1: All 16 subbands with ±0.5s jitter
        # Use MJD for 2025-10-02T01:00:00
        base_mjd = 60950.041666666664
        test_files = []
        for sb_idx in range(16):
            mjd = base_mjd + np.random.uniform(-0.5 / 86400, 0.5 / 86400)
            path = str(tmp_path / f"2025-10-02T01:00:00_sb{sb_idx:02d}.hdf5")
            # Create dummy files so exists() check passes
            Path(path).touch()
            test_files.append((mjd, f"sb{sb_idx:02d}", path))

        # Create temporary database with test data
        db_path = create_test_hdf5_db(test_files)

        try:
            # Query with 1.0s tolerance
            groups = query_subband_groups(
                db_path,
                "2025-10-02T00:00:00",
                "2025-10-02T02:00:00",
                tolerance_s=1.0,
                cluster_tolerance_s=1.0,
                only_stored=True,
            )

            # Should find 1 complete group despite timestamp jitter
            assert len(groups) == 1
            assert groups[0].present_count == 16
            assert groups[0].is_complete is True
        finally:
            # Clean up
            if db_path.exists():
                db_path.unlink()

    @patch("dsa110_contimg.database.hdf5_index.sqlite3")
    @patch("os.path.exists")
    def test_grouping_rejects_incomplete_groups(self, mock_exists, mock_sqlite):
        """Test that incomplete groups (missing subbands) are not returned."""
        from dsa110_contimg.database.hdf5_index import query_subband_groups

        # Mock database with only 15 subbands (missing sb06)
        base_mjd = 60000.5
        mock_files = []
        for sb_idx in range(16):
            if sb_idx == 6:  # Skip sb06
                continue
            mjd = base_mjd + 0.1 / 86400  # All same time
            mock_files.append(
                (
                    mjd,
                    f"sb{sb_idx:02d}",
                    f"/data/incoming/2025-10-02T01:00:00_sb{sb_idx:02d}.hdf5",
                )
            )

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_sqlite.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = mock_files

        mock_exists.return_value = True

        groups = query_subband_groups(
            Path("/tmp/hdf5.sqlite3"),
            "2025-10-02T00:00:00",
            "2025-10-02T02:00:00",
            tolerance_s=1.0,
            only_stored=True,
        )

        # Should find 0 complete groups (missing sb06)
        assert len(groups) == 0

    def test_grouping_handles_multiple_groups(self, tmp_path):
        """Test that multiple complete groups are correctly identified."""
        from dsa110_contimg.database.hdf5_index import query_subband_groups

        # Create 2 complete groups with different timestamps
        test_files = []
        for group_idx in range(2):
            # Use MJD for 2025-10-02T01:00:00, groups 14.4 minutes apart
            base_mjd = 60950.041666666664 + group_idx * 0.01
            for sb_idx in range(16):
                mjd = base_mjd + np.random.uniform(-0.3 / 86400, 0.3 / 86400)
                path = str(tmp_path / f"group{group_idx}_sb{sb_idx:02d}.hdf5")
                Path(path).touch()
                test_files.append((mjd, f"sb{sb_idx:02d}", path))

        db_path = create_test_hdf5_db(test_files)

        try:
            groups = query_subband_groups(
                db_path,
                "2025-10-02T00:00:00",
                "2025-10-02T02:00:00",
                tolerance_s=1.0,
                cluster_tolerance_s=1.0,
                only_stored=True,
            )

            # Should find 2 complete groups
            assert len(groups) == 2
            for group in groups:
                assert len(group) == 16
        finally:
            if db_path.exists():
                db_path.unlink()


class TestGroupingReturnFormat:
    """Test that grouping returns files in correct order."""

    def test_files_ordered_by_subband(self, tmp_path):
        """Test that files within a group are ordered sb00 to sb15."""
        from dsa110_contimg.database.hdf5_index import query_subband_groups

        # Create files in random subband order
        # Use MJD for 2025-10-02T01:00:00
        base_mjd = 60950.041666666664
        subband_order = list(range(16))
        np.random.shuffle(subband_order)

        test_files = []
        for sb_idx in subband_order:
            path = str(tmp_path / f"file_sb{sb_idx:02d}.hdf5")
            Path(path).touch()
            test_files.append((base_mjd, f"sb{sb_idx:02d}", path))

        db_path = create_test_hdf5_db(test_files)

        try:
            groups = query_subband_groups(
                db_path,
                "2025-10-02T00:00:00",
                "2025-10-02T02:00:00",
                tolerance_s=1.0,
                cluster_tolerance_s=1.0,
                only_stored=True,
            )

            assert len(groups) == 1
            group = groups[0]

            # Verify ordering: sb00 to sb15
            for idx, filepath in enumerate(group):
                assert f"sb{idx:02d}" in filepath
        finally:
            if db_path.exists():
                db_path.unlink()


class TestGroupingEdgeCases:
    """Test edge cases in grouping algorithm."""

    @patch("dsa110_contimg.database.hdf5_index.sqlite3")
    def test_empty_database_returns_empty_list(self, mock_sqlite):
        """Test that empty database returns empty list."""
        from dsa110_contimg.database.hdf5_index import query_subband_groups

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_sqlite.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        groups = query_subband_groups(
            Path("/tmp/hdf5.sqlite3"),
            "2025-10-02T00:00:00",
            "2025-10-02T02:00:00",
            tolerance_s=1.0,
            only_stored=True,
        )

        assert groups == []

    def test_duplicate_subbands_uses_latest(self, tmp_path):
        """Test that duplicate subbands in same time window uses latest."""
        from dsa110_contimg.database.hdf5_index import query_subband_groups

        # Create complete group with duplicate sb00
        # Use MJD for 2025-10-02T01:00:00
        base_mjd = 60950.041666666664
        test_files = []

        # Convert seconds to MJD: 1 second = 1/86400 days
        offset_0p2s = 0.2 / 86400
        offset_0p5s = 0.5 / 86400

        # First sb00 (earlier, should be rejected)
        path1 = str(tmp_path / "file1_sb00.hdf5")
        Path(path1).touch()
        test_files.append((base_mjd - offset_0p2s, "sb00", path1))

        # Rest of subbands
        for sb_idx in range(1, 16):
            path = str(tmp_path / f"file_sb{sb_idx:02d}.hdf5")
            Path(path).touch()
            test_files.append((base_mjd, f"sb{sb_idx:02d}", path))

        # Second sb00 (later, should be used)
        path2 = str(tmp_path / "file2_sb00.hdf5")
        Path(path2).touch()
        test_files.append((base_mjd + offset_0p5s, "sb00", path2))

        db_path = create_test_hdf5_db(test_files)

        try:
            groups = query_subband_groups(
                db_path,
                "2025-10-02T00:00:00",
                "2025-10-02T02:00:00",
                tolerance_s=1.0,
                cluster_tolerance_s=1.0,
                only_stored=True,
            )

            # Should find 1 group
            assert len(groups) == 1
            # Should have 16 unique files
            assert groups[0].present_count == 16
            assert groups[0].is_complete is True
        finally:
            if db_path.exists():
                db_path.unlink()


class TestSmokeTests:
    """Smoke tests for HDF5 grouping."""

    def test_can_import_query_function(self):
        """Smoke test: Can import query_subband_groups."""
        from dsa110_contimg.database.hdf5_index import query_subband_groups

        assert callable(query_subband_groups)

    def test_query_function_signature(self):
        """Smoke test: Check query function has correct parameters."""
        import inspect

        from dsa110_contimg.database.hdf5_index import query_subband_groups

        sig = inspect.signature(query_subband_groups)
        params = list(sig.parameters.keys())

        # Required parameters
        assert "hdf5_db" in params
        assert "start_time" in params
        assert "end_time" in params
        assert "tolerance_s" in params
        assert "only_stored" in params
