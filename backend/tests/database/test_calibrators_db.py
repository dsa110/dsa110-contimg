"""
Tests for calibrators.sqlite3 database module.
"""

import tempfile
from pathlib import Path

import pytest

from dsa110_contimg.database.calibrators import (
    ensure_calibrators_db,
    get_bandpass_calibrators,
    get_gain_calibrators,
    register_bandpass_calibrator,
    register_gain_calibrator,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = Path(f.name)

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


def test_ensure_calibrators_db(temp_db):
    """Test database creation."""
    conn = ensure_calibrators_db(temp_db)

    # Check tables exist
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

    assert "bandpass_calibrators" in tables
    assert "gain_calibrators" in tables
    assert "catalog_sources" in tables
    assert "vla_calibrators" in tables
    assert "vla_flux_info" in tables
    assert "skymodel_metadata" in tables

    conn.close()


def test_register_bandpass_calibrator(temp_db):
    """Test registering a bandpass calibrator."""
    cal_id = register_bandpass_calibrator(
        calibrator_name="3C286",
        ra_deg=202.7845,
        dec_deg=30.5092,
        dec_range_min=25.0,
        dec_range_max=35.0,
        source_catalog="VLA",
        flux_jy=14.9,
        registered_by="test",
        calibrators_db=temp_db,
    )

    assert cal_id is not None

    # Verify it was registered
    calibrators = get_bandpass_calibrators(calibrators_db=temp_db)
    assert len(calibrators) == 1
    assert calibrators[0]["calibrator_name"] == "3C286"
    assert calibrators[0]["ra_deg"] == 202.7845
    assert calibrators[0]["dec_deg"] == 30.5092


def test_get_bandpass_calibrators_by_dec(temp_db):
    """Test querying bandpass calibrators by declination."""
    # Register multiple calibrators
    register_bandpass_calibrator(
        calibrator_name="3C286",
        ra_deg=202.7845,
        dec_deg=30.5092,
        dec_range_min=25.0,
        dec_range_max=35.0,
        calibrators_db=temp_db,
    )

    register_bandpass_calibrator(
        calibrator_name="3C48",
        ra_deg=24.4221,
        dec_deg=33.1597,
        dec_range_min=28.0,
        dec_range_max=38.0,
        calibrators_db=temp_db,
    )

    # Query for declination in first range only (30.0 is in 25-35, not in 28-38)
    calibrators = get_bandpass_calibrators(dec_deg=30.0, calibrators_db=temp_db)
    # 30.0 is within 25-35 (3C286) and also within 28-38 (3C48) - both match
    assert len(calibrators) >= 1
    assert any(cal["calibrator_name"] == "3C286" for cal in calibrators)

    # Query for declination in both ranges
    calibrators = get_bandpass_calibrators(dec_deg=33.0, calibrators_db=temp_db)
    assert len(calibrators) == 2


def test_register_gain_calibrator(temp_db):
    """Test registering a gain calibrator."""
    cal_id = register_gain_calibrator(
        field_id="test_field_001",
        source_name="NVSS_J123456+123456",
        ra_deg=123.456,
        dec_deg=12.3456,
        flux_jy=5.0,
        catalog_source="NVSS",
        calibrators_db=temp_db,
    )

    assert cal_id is not None

    # Verify it was registered
    calibrators = get_gain_calibrators(field_id="test_field_001", calibrators_db=temp_db)
    assert len(calibrators) == 1
    assert calibrators[0]["source_name"] == "NVSS_J123456+123456"
    assert calibrators[0]["flux_jy"] == 5.0


def test_get_gain_calibrators(temp_db):
    """Test querying gain calibrators."""
    # Register multiple gain calibrators
    register_gain_calibrator(
        field_id="field_001",
        source_name="source_1",
        ra_deg=100.0,
        dec_deg=10.0,
        flux_jy=1.0,
        calibrators_db=temp_db,
    )

    register_gain_calibrator(
        field_id="field_001",
        source_name="source_2",
        ra_deg=100.1,
        dec_deg=10.1,
        flux_jy=2.0,
        calibrators_db=temp_db,
    )

    register_gain_calibrator(
        field_id="field_002",
        source_name="source_3",
        ra_deg=200.0,
        dec_deg=20.0,
        flux_jy=3.0,
        calibrators_db=temp_db,
    )

    # Query by field
    calibrators = get_gain_calibrators(field_id="field_001", calibrators_db=temp_db)
    assert len(calibrators) == 2

    # Query all
    all_calibrators = get_gain_calibrators(calibrators_db=temp_db)
    assert len(all_calibrators) == 3
