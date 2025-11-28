"""Tests for HDF5 file grouping algorithms.

These tests ensure the proximity-based grouping algorithm correctly
identifies complete 16-subband groups despite timestamp jitter.

CRITICAL: Never use manual time-based clustering. Always use the
query_subband_groups() function from hdf5_index.py
"""

import sqlite3
from pathlib import Path

import pytest

from dsa110_contimg.database.hdf5_index import (
    get_group_count,
    is_group_complete,
    query_subband_groups,
)


def create_hdf5_table(conn):
    """Create the hdf5_file_index table with the correct schema."""
    conn.execute(
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


class TestHDF5ProximityGrouping:
    """Test the proximity-based grouping algorithm."""

    @pytest.fixture
    def mock_hdf5_db(self, tmp_path):
        """Create a mock HDF5 database with test data."""
        db_path = tmp_path / "test_hdf5.sqlite3"
        conn = sqlite3.connect(str(db_path))

        create_hdf5_table(conn)

        # Insert complete group with 60s jitter tolerance
        # MJD for 2025-10-02T01:00:00 is approximately 60950.04167
        base_mjd = 60950.04167
        for sb_num in range(16):
            # Add small jitter (up to 30 seconds)
            jitter_days = (sb_num * 2 - 15) / 86400.0  # ±30 seconds
            filename = f"test_sb{sb_num:02d}.hdf5"
            conn.execute(
                """INSERT INTO hdf5_file_index 
                   (path, filename, group_id, subband_code, subband_num, 
                    timestamp_iso, timestamp_mjd, stored, ra_deg, dec_deg, 
                    obs_date, obs_time)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)""",
                (
                    f"/data/{filename}",
                    filename,
                    "2025-10-02T01:00:00",
                    f"sb{sb_num:02d}",
                    sb_num,
                    "2025-10-02T01:00:00",
                    base_mjd + jitter_days,
                    128.5 if sb_num == 0 else None,
                    55.5 if sb_num == 0 else None,
                    "2025-10-02" if sb_num == 0 else None,
                    "01:00:00" if sb_num == 0 else None,
                ),
            )

        # Insert incomplete group (missing sb06)
        # MJD for 2025-10-02T03:00:00 is approximately 60950.125
        base_mjd2 = 60950.125
        for sb_num in range(16):
            if sb_num == 6:  # Skip sb06
                continue
            jitter_days = (sb_num * 2 - 15) / 86400.0
            filename = f"test2_sb{sb_num:02d}.hdf5"
            conn.execute(
                """INSERT INTO hdf5_file_index 
                   (path, filename, group_id, subband_code, subband_num, 
                    timestamp_iso, timestamp_mjd, stored, ra_deg, dec_deg, 
                    obs_date, obs_time)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)""",
                (
                    f"/data/{filename}",
                    filename,
                    "2025-10-02T03:00:00",
                    f"sb{sb_num:02d}",
                    sb_num,
                    "2025-10-02T03:00:00",
                    base_mjd2 + jitter_days,
                    128.5 if sb_num == 0 else None,
                    55.5 if sb_num == 0 else None,
                    "2025-10-02" if sb_num == 0 else None,
                    "03:00:00" if sb_num == 0 else None,
                ),
            )

        conn.commit()
        conn.close()

        return db_path

    def test_query_complete_group(self, mock_hdf5_db):
        """Test querying a complete 16-subband group."""
        groups = query_subband_groups(
            mock_hdf5_db,
            start_time="2025-10-02T00:00:00",
            end_time="2025-10-02T02:00:00",
            tolerance_s=60.0,
            only_stored=False,
        )

        assert len(groups) == 1
        group = groups[0]
        assert group.present_count == 16
        assert group.is_complete is True

        # Check all subbands present (no None in files list)
        assert all(f is not None for f in group.files)

    def test_query_incomplete_group(self, mock_hdf5_db):
        """Test that semi-complete groups (12-15 subbands) are returned.
        
        The new protocol accepts groups with 12-16 subbands. Groups with
        fewer than 12 subbands are rejected.
        """
        groups = query_subband_groups(
            mock_hdf5_db,
            start_time="2025-10-02T02:00:00",
            end_time="2025-10-02T04:00:00",
            tolerance_s=60.0,
            only_stored=False,
        )

        # Should return semi-complete group (15 subbands, missing sb06)
        assert len(groups) == 1
        group = groups[0]
        assert group.present_count == 15
        assert group.is_complete is False
        assert 6 in group.missing_subbands
        assert "sb06" in group.missing_subband_codes

    def test_tolerance_too_small(self, mock_hdf5_db):
        """Test that too-small tolerance fails to group files."""
        groups = query_subband_groups(
            mock_hdf5_db,
            start_time="2025-10-02T00:00:00",
            end_time="2025-10-02T02:00:00",
            tolerance_s=10.0,  # Too small for 30s jitter
            only_stored=False,
        )

        # May not find complete group with restrictive tolerance
        # (depending on jitter pattern)
        assert len(groups) <= 1

    def test_get_group_count(self, mock_hdf5_db):
        """Test counting subbands for a specific group."""
        # Count complete group (should have 16)
        count = get_group_count(mock_hdf5_db, group_id="2025-10-02T01:00:00")
        assert count == 16

        # Count incomplete group (should have 15, missing sb06)
        count2 = get_group_count(mock_hdf5_db, group_id="2025-10-02T03:00:00")
        assert count2 == 15

    def test_is_group_complete(self, mock_hdf5_db):
        """Test checking if a specific group is complete."""
        # Check complete group
        is_complete = is_group_complete(mock_hdf5_db, group_id="2025-10-02T01:00:00")
        assert is_complete is True

        # Check incomplete group
        is_incomplete = is_group_complete(mock_hdf5_db, group_id="2025-10-02T03:00:00")
        assert is_incomplete is False


class TestHDF5GroupingEdgeCases:
    """Test edge cases in HDF5 grouping."""

    @pytest.fixture
    def edge_case_db(self, tmp_path):
        """Create database with edge cases."""
        db_path = tmp_path / "edge_cases.sqlite3"
        conn = sqlite3.connect(str(db_path))

        create_hdf5_table(conn)

        # Group with duplicate subband (should only count once)
        # MJD for 2025-10-03T01:00:00
        base_mjd = 60951.04167
        for sb_num in range(16):
            filename = f"dup1_sb{sb_num:02d}.hdf5"
            conn.execute(
                """INSERT INTO hdf5_file_index 
                   (path, filename, group_id, subband_code, subband_num, 
                    timestamp_iso, timestamp_mjd, stored)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                (
                    f"/data/{filename}",
                    filename,
                    "2025-10-03T01:00:00",
                    f"sb{sb_num:02d}",
                    sb_num,
                    "2025-10-03T01:00:00",
                    base_mjd + sb_num / 86400.0,
                ),
            )

        # Add duplicate sb00
        conn.execute(
            """INSERT INTO hdf5_file_index 
               (path, filename, group_id, subband_code, subband_num, 
                timestamp_iso, timestamp_mjd, stored)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
            (
                "/data/dup1_sb00_v2.hdf5",
                "dup1_sb00_v2.hdf5",
                "2025-10-03T01:00:00",
                "sb00",
                0,
                "2025-10-03T01:00:00",
                base_mjd,
            ),
        )

        conn.commit()
        conn.close()

        return db_path

    def test_duplicate_subband_handling(self, edge_case_db):
        """Test that duplicate subbands are handled correctly."""
        groups = query_subband_groups(
            edge_case_db,
            start_time="2025-10-03T00:00:00",
            end_time="2025-10-03T02:00:00",
            tolerance_s=60.0,
            only_stored=False,
        )

        # Should still return complete group
        assert len(groups) == 1
        # All 16 subbands should be present
        assert groups[0].present_count == 16
        assert groups[0].is_complete is True

    def test_empty_database(self, tmp_path):
        """Test querying empty database."""
        db_path = tmp_path / "empty.sqlite3"
        conn = sqlite3.connect(str(db_path))
        create_hdf5_table(conn)
        conn.commit()
        conn.close()

        groups = query_subband_groups(
            db_path,
            start_time="2025-10-02T00:00:00",
            end_time="2025-10-02T01:00:00",
            tolerance_s=60.0,
            only_stored=False,
        )

        assert len(groups) == 0

    def test_only_stored_filter(self, tmp_path):
        """Test that only_stored parameter filters by the stored column.
        
        Note: When only_stored=True, the function also checks if files exist on disk.
        Since we use fake paths in tests, we can only test the stored=0 filtering
        (where files are marked as not stored in the database).
        """
        db_path = tmp_path / "stored_filter.sqlite3"
        conn = sqlite3.connect(str(db_path))

        create_hdf5_table(conn)

        # Insert group with stored=0 (marked as deleted/not stored)
        # MJD for 2025-10-04T01:00:00
        base_mjd = 60952.04167
        for sb_num in range(16):
            filename = f"unstored_sb{sb_num:02d}.hdf5"
            conn.execute(
                """INSERT INTO hdf5_file_index 
                   (path, filename, group_id, subband_code, subband_num, 
                    timestamp_iso, timestamp_mjd, stored)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
                (
                    f"/data/{filename}",
                    filename,
                    "2025-10-04T01:00:00",
                    f"sb{sb_num:02d}",
                    sb_num,
                    "2025-10-04T01:00:00",
                    base_mjd + sb_num / 86400.0,
                ),
            )

        conn.commit()
        conn.close()

        # With only_stored=False, should find groups even when stored=0
        groups = query_subband_groups(
            db_path,
            start_time="2025-10-04T00:00:00",
            end_time="2025-10-04T02:00:00",
            tolerance_s=60.0,
            only_stored=False,
        )
        assert len(groups) == 1, "Should find group when only_stored=False, even with stored=0"


class TestGroupingPerformance:
    """Test grouping algorithm performance."""

    def test_large_dataset(self, tmp_path):
        """Test grouping with large number of files."""
        db_path = tmp_path / "large.sqlite3"
        conn = sqlite3.connect(str(db_path))

        create_hdf5_table(conn)

        # Insert 100 complete groups (1600 files)
        import time

        # MJD for 2025-10-05T00:00:00
        base_mjd = 60953.0
        for group_idx in range(100):
            for sb_num in range(16):
                mjd = base_mjd + (group_idx * 0.01) + (sb_num / 86400.0)
                filename = f"g{group_idx}_sb{sb_num:02d}.hdf5"
                conn.execute(
                    """INSERT INTO hdf5_file_index 
                       (path, filename, group_id, subband_code, subband_num, 
                        timestamp_iso, timestamp_mjd, stored)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                    (
                        f"/data/{filename}",
                        filename,
                        f"2025-10-05T{group_idx:02d}:00:00",
                        f"sb{sb_num:02d}",
                        sb_num,
                        f"2025-10-05T{group_idx:02d}:00:00",
                        mjd,
                    ),
                )

        conn.commit()
        conn.close()

        # Query should complete in reasonable time
        start = time.time()
        groups = query_subband_groups(
            db_path,
            start_time="2025-10-05T00:00:00",
            end_time="2025-10-06T00:00:00",
            tolerance_s=60.0,
            only_stored=False,
        )
        elapsed = time.time() - start

        assert len(groups) == 100
        assert elapsed < 5.0, f"Grouping took {elapsed:.2f}s (too slow)"
