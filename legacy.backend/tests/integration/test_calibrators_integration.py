"""
Integration tests for calibrators.sqlite3 migration and pipeline integration.

Tests the full workflow:
1. Register bandpass calibrators
2. Query calibrators from pipeline code
3. Create skymodels
4. Verify end-to-end functionality
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from dsa110_contimg.database.calibrators import (
    ensure_calibrators_db,
    get_bandpass_calibrators,
    register_bandpass_calibrator,
)
from dsa110_contimg.database.catalog_query import (
    find_calibrators_for_field,
    query_unified_catalog,
)
from dsa110_contimg.database.skymodel_storage import (
    create_skymodel,
    get_skymodel_for_field,
)


@pytest.fixture
def temp_calibrators_db():
    """Create a temporary calibrators database."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = Path(f.name)

    ensure_calibrators_db(db_path)
    yield db_path

    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def temp_skymodel_dir():
    """Create a temporary directory for skymodels."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_register_and_query_bandpass_calibrator(temp_calibrators_db):
    """Test registering and querying a bandpass calibrator."""
    # Register a known calibrator (3C286)
    cal_id = register_bandpass_calibrator(
        calibrator_name="3C286",
        ra_deg=202.7845,
        dec_deg=30.5092,
        dec_range_min=25.0,
        dec_range_max=35.0,
        source_catalog="VLA",
        flux_jy=14.9,
        registered_by="integration_test",
        calibrators_db=temp_calibrators_db,
    )

    assert cal_id is not None

    # Query by declination
    calibrators = get_bandpass_calibrators(dec_deg=30.0, calibrators_db=temp_calibrators_db)
    assert len(calibrators) >= 1
    assert any(cal["calibrator_name"] == "3C286" for cal in calibrators)


def test_find_calibrators_for_field(temp_calibrators_db, monkeypatch):
    """Test finding calibrators for a field using the unified interface."""
    # Mock the calibrators database path for this test
    from dsa110_contimg.database import calibrators

    original_get_path = calibrators.get_calibrators_db_path

    def mock_get_path():
        return temp_calibrators_db

    monkeypatch.setattr(calibrators, "get_calibrators_db_path", mock_get_path)

    # Register a bandpass calibrator
    register_bandpass_calibrator(
        calibrator_name="3C286",
        ra_deg=202.7845,
        dec_deg=30.5092,
        dec_range_min=25.0,
        dec_range_max=35.0,
        flux_jy=14.9,
        calibrators_db=temp_calibrators_db,
    )

    # Find calibrators for a field
    bp_cal, gain_cals = find_calibrators_for_field(
        ra_deg=202.7845,
        dec_deg=30.5092,
        radius_deg=0.1,
        min_flux_jy=1.0,
    )

    assert bp_cal is not None
    assert bp_cal["name"] == "3C286"
    assert isinstance(gain_cals, list)


def test_skymodel_creation_and_retrieval(temp_calibrators_db, temp_skymodel_dir):
    """Test creating and retrieving a skymodel."""
    sources = [
        {
            "source_name": "NVSS_J202784+305092",
            "ra_deg": 202.7845,
            "dec_deg": 30.5092,
            "flux_jy": 14.9,
            "catalog_source": "NVSS",
        },
        {
            "source_name": "NVSS_J202785+305093",
            "ra_deg": 202.7850,
            "dec_deg": 30.5093,
            "flux_jy": 5.0,
            "catalog_source": "NVSS",
        },
    ]

    skymodel_path = create_skymodel(
        field_id="test_field_integration",
        sources=sources,
        output_path=temp_skymodel_dir / "test_field.skymodel",
        created_by="integration_test",
        calibrators_db=temp_calibrators_db,
    )

    assert skymodel_path.exists()

    # Retrieve skymodel
    skymodel_info = get_skymodel_for_field(
        "test_field_integration", calibrators_db=temp_calibrators_db
    )
    assert skymodel_info is not None
    assert skymodel_info["field_id"] == "test_field_integration"
    assert skymodel_info["n_sources"] == 2


def test_pipeline_code_compatibility(temp_calibrators_db):
    """Test that pipeline code can use the new database."""
    # Register calibrator
    register_bandpass_calibrator(
        calibrator_name="0834+555",
        ra_deg=129.2758,
        dec_deg=55.2456,
        dec_range_min=50.0,
        dec_range_max=60.0,
        flux_jy=2.5,
        calibrators_db=temp_calibrators_db,
    )

    # Simulate pipeline code query (like streaming_mosaic.py)
    from dsa110_contimg.database.calibrators import get_bandpass_calibrators

    calibrators = get_bandpass_calibrators(
        dec_deg=55.0, status="active", calibrators_db=temp_calibrators_db
    )

    assert len(calibrators) >= 1
    assert any(cal["calibrator_name"] == "0834+555" for cal in calibrators)

    # Format like streaming_mosaic.py expects
    if calibrators:
        calibrators.sort(key=lambda x: x.get("registered_at", 0), reverse=True)
        cal = calibrators[0]
        result = {
            "name": cal["calibrator_name"],
            "ra_deg": cal["ra_deg"],
            "dec_deg": cal["dec_deg"],
            "dec_range_min": cal.get("dec_range_min"),
            "dec_range_max": cal.get("dec_range_max"),
            "registered_at": cal.get("registered_at"),
            "notes": cal.get("notes"),
        }

        assert result["name"] == "0834+555"
        assert result["ra_deg"] == 129.2758


def test_multiple_calibrators_same_dec_range(temp_calibrators_db):
    """Test handling multiple calibrators in the same declination range."""
    # Register two calibrators with overlapping ranges
    register_bandpass_calibrator(
        calibrator_name="3C286",
        ra_deg=202.7845,
        dec_deg=30.5092,
        dec_range_min=25.0,
        dec_range_max=35.0,
        status="active",
        calibrators_db=temp_calibrators_db,
    )

    register_bandpass_calibrator(
        calibrator_name="3C48",
        ra_deg=24.4221,
        dec_deg=33.1597,
        dec_range_min=28.0,
        dec_range_max=38.0,
        status="active",
        calibrators_db=temp_calibrators_db,
    )

    # Query for declination in overlap region
    calibrators = get_bandpass_calibrators(dec_deg=33.0, calibrators_db=temp_calibrators_db)
    assert len(calibrators) == 2

    # Verify both are returned
    names = {cal["calibrator_name"] for cal in calibrators}
    assert "3C286" in names
    assert "3C48" in names
