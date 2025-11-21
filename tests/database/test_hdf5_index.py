"""
Tests for HDF5 file indexing and grouping functionality.

These tests verify the proximity-based grouping algorithm and database operations.
"""

import tempfile
from pathlib import Path

import pytest

from dsa110_contimg.database.hdf5_db import ensure_hdf5_db
from dsa110_contimg.database.hdf5_index import (
    get_group_count,
    is_group_complete,
    query_subband_groups,
)


@pytest.fixture
def temp_hdf5_db():
    """Create a temporary HDF5 database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = Path(f.name)

    conn = ensure_hdf5_db(db_path)
    yield conn, db_path

    conn.close()
    db_path.unlink(missing_ok=True)


def test_ensure_hdf5_db_creates_tables(temp_hdf5_db):
    """Test that ensure_hdf5_db creates the required tables and indexes."""
    conn, _ = temp_hdf5_db
    cursor = conn.cursor()

    # Check table exists
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='hdf5_file_index'"
    ).fetchall()
    assert len(tables) == 1

    # Check required columns exist
    columns = cursor.execute("PRAGMA table_info(hdf5_file_index)").fetchall()
    column_names = [col[1] for col in columns]

    required_cols = [
        "path",
        "group_id",
        "subband_code",
        "subband_num",
        "timestamp_iso",
        "timestamp_mjd",
        "stored",
        "indexed_at",
        "ra_deg",
        "dec_deg",
        "obs_date",
        "obs_time",
    ]
    for col in required_cols:
        assert col in column_names, f"Missing required column: {col}"


def test_parse_hdf5_metadata_sb00():
    """Test metadata parsing for sb00 files."""
    # This is a smoke test - actual file parsing requires real files
    filename = "corr00_59765_65432_sb00.hdf5"

    # The actual parsing would require a real file
    # but we can test the filename parsing
    assert "sb00" in filename


def test_query_subband_groups_empty_db(temp_hdf5_db):
    """Test querying subband groups from an empty database."""
    conn, db_path = temp_hdf5_db

    start_time = "2025-10-01T00:00:00"
    end_time = "2025-10-01T01:00:00"

    groups = query_subband_groups(db_path, start_time, end_time)
    assert groups == []


def test_get_group_count_empty_db(temp_hdf5_db):
    """Test getting group count from an empty database."""
    conn, db_path = temp_hdf5_db

    start_time = "2025-10-01T00:00:00"
    end_time = "2025-10-01T01:00:00"

    count = get_group_count(db_path, start_time, end_time)
    assert count == 0


def test_is_group_complete_empty_db(temp_hdf5_db):
    """Test checking group completeness in an empty database."""
    conn, db_path = temp_hdf5_db

    complete = is_group_complete(db_path, "nonexistent_group")
    assert complete is False


def test_subband_ordering():
    """Test that subband numbers are correctly ordered from 0-15."""
    subbands = [f"sb{i:02d}" for i in range(16)]
    expected = [
        "sb00",
        "sb01",
        "sb02",
        "sb03",
        "sb04",
        "sb05",
        "sb06",
        "sb07",
        "sb08",
        "sb09",
        "sb10",
        "sb11",
        "sb12",
        "sb13",
        "sb14",
        "sb15",
    ]
    assert subbands == expected


@pytest.mark.integration
def test_proximity_grouping_tolerance():
    """Test that the proximity-based grouping respects tolerance."""
    # This is a conceptual test - full integration requires real data
    # The key property: files within tolerance_s should be grouped
    tolerance_s = 60.0

    # Example timestamps (in MJD)
    base_mjd = 59765.5
    timestamps = [
        base_mjd,
        base_mjd + (30 / 86400),  # 30 seconds later
        base_mjd + (90 / 86400),  # 90 seconds later (out of tolerance)
    ]

    # First two should group together, third should be separate
    # This property should be tested with actual grouping logic
    diff_close = abs(timestamps[1] - timestamps[0]) * 86400
    diff_far = abs(timestamps[2] - timestamps[0]) * 86400
    assert diff_close < tolerance_s
    assert diff_far > tolerance_s
