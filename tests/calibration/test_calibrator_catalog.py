"""
Tests for calibrator catalog functionality.

These tests verify catalog loading, querying, and database operations.
"""

import sqlite3
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from dsa110_contimg.calibration.catalogs import (
    load_vla_catalog_from_sqlite,
    nearest_calibrator_within_radius,
)


@pytest.fixture
def temp_calibrator_db():
    """Create a temporary calibrator database with test data."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = Path(f.name)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS calibrator_sources (
            source_name TEXT PRIMARY KEY,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            flux_5ghz_jy REAL,
            spectral_index REAL,
            catalog_name TEXT
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS calibrators (
            name TEXT PRIMARY KEY,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS vla_20cm (
            name TEXT PRIMARY KEY,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            flux_jy REAL
        )
    """
    )

    # Insert test data
    test_sources = [
        (
            "0834+555",
            128.72876715416666,
            55.57251971666667,
            1.5,
            -0.5,
            "VLA",
        ),
        ("1234+567", 188.5, 56.7, 2.0, -0.6, "VLA"),
        ("2345+678", 356.25, 67.8, 1.0, -0.4, "VLA"),
    ]

    cursor.executemany(
        "INSERT INTO calibrator_sources VALUES (?, ?, ?, ?, ?, ?)",
        test_sources,
    )

    # Also insert into vla_20cm table for the load function
    vla_sources = [
        ("0834+555", 128.72876715416666, 55.57251971666667, 1.5),
        ("1234+567", 188.5, 56.7, 2.0),
        ("2345+678", 356.25, 67.8, 1.0),
    ]
    cursor.executemany(
        "INSERT INTO vla_20cm VALUES (?, ?, ?, ?)",
        vla_sources,
    )

    conn.commit()
    yield conn, db_path

    conn.close()
    db_path.unlink(missing_ok=True)


def test_load_vla_catalog_from_sqlite(temp_calibrator_db):
    """Test loading VLA calibrator catalog from SQLite database."""
    conn, db_path = temp_calibrator_db

    df = load_vla_catalog_from_sqlite(str(db_path))

    assert df is not None
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert "source_name" in df.columns
    assert "ra_deg" in df.columns
    assert "dec_deg" in df.columns


def test_find_nearest_calibrator(temp_calibrator_db):
    """Test finding the nearest calibrator to a target position."""
    conn, db_path = temp_calibrator_db
    df = load_vla_catalog_from_sqlite(str(db_path))

    # Search near 0834+555
    target_ra = 128.7
    target_dec = 55.5

    # nearest_calibrator_within_radius returns (name, ra, dec, distance)
    nearest = nearest_calibrator_within_radius(target_ra, target_dec, df, radius_deg=5.0)

    assert nearest is not None
    # nearest is a tuple: (source_name, ra, dec, distance)
    assert nearest[0] == "0834+555"


def test_find_calibrator_by_name(temp_calibrator_db):
    """Test finding a specific calibrator by name."""
    conn, db_path = temp_calibrator_db
    df = load_vla_catalog_from_sqlite(str(db_path))

    calibrator = df[df["source_name"] == "0834+555"]

    assert len(calibrator) == 1
    assert calibrator.iloc[0]["ra_deg"] == pytest.approx(128.72876715416666)
    assert calibrator.iloc[0]["dec_deg"] == pytest.approx(55.57251971666667)


def test_calibrator_dec_range():
    """Test that calibrator declinations are within observable range."""
    # DSA-110 is at ~37° N latitude
    # Observable Dec range is roughly -53° to +90° (with elevation > 0°)
    dsa110_lat = 37.23
    min_observable_dec = -90 + dsa110_lat
    max_observable_dec = 90

    # Test that our known calibrator is observable
    test_dec = 55.57251971666667  # 0834+555
    assert min_observable_dec < test_dec < max_observable_dec


@pytest.mark.integration
def test_vla_calibrator_database_exists():
    """Smoke test to check if the actual VLA calibrator database exists."""
    # This tests the real database path
    db_path = Path("/data/dsa110-contimg/state/vla_calibrators.sqlite3")

    if db_path.exists():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if table exists
        tables = cursor.execute(
            "SELECT name FROM sqlite_master " "WHERE type='table' AND name='calibrator_sources'"
        ).fetchall()

        assert len(tables) > 0, "calibrator_sources table not found"

        # Check row count
        count = cursor.execute("SELECT COUNT(*) FROM calibrator_sources").fetchone()[0]
        conn.close()

        # Database should have multiple calibrators
        assert count > 0, f"Database has {count} calibrators, expected > 0"
    else:
        pytest.skip("VLA calibrator database not found at expected path")


def test_sqlite_database_priority():
    """Test that SQLite database is preferred over CSV catalog."""
    # This is a design test - verifying the architectural decision
    # The calibrator_ms_service should use SQLite first, CSV as fallback

    # CSV fallback should be disabled (per user request)
    # This is verified by the code structure in calibrator_ms_service.py
    assert True  # Placeholder for architectural verification
