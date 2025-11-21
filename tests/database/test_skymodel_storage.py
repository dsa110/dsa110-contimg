"""
Tests for skymodel storage system.
"""

import tempfile
from pathlib import Path

import pytest

from dsa110_contimg.database.skymodel_storage import (
    create_skymodel,
    delete_skymodel,
    get_skymodel_for_field,
    get_sources_for_skymodel,
    list_skymodels,
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


@pytest.fixture
def temp_skymodel_dir():
    """Create a temporary directory for skymodels."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_create_skymodel(temp_db, temp_skymodel_dir):
    """Test creating a skymodel."""
    sources = [
        {
            "source_name": "NVSS_J123456+123456",
            "ra_deg": 123.456,
            "dec_deg": 12.3456,
            "flux_jy": 5.0,
            "catalog_source": "NVSS",
        },
        {
            "source_name": "NVSS_J123457+123457",
            "ra_deg": 123.457,
            "dec_deg": 12.3457,
            "flux_jy": 3.0,
            "catalog_source": "NVSS",
        },
    ]

    output_path = temp_skymodel_dir / "test_field.skymodel"

    skymodel_path = create_skymodel(
        field_id="test_field_001",
        sources=sources,
        output_path=output_path,
        created_by="test",
        calibrators_db=temp_db,
    )

    assert skymodel_path.exists()
    assert skymodel_path == output_path

    # Verify file contents
    content = skymodel_path.read_text()
    assert "test_field_001" in content
    assert "NVSS_J123456+123456" in content


def test_get_skymodel_for_field(temp_db, temp_skymodel_dir):
    """Test retrieving skymodel for a field."""
    sources = [
        {
            "source_name": "source_1",
            "ra_deg": 100.0,
            "dec_deg": 10.0,
            "flux_jy": 5.0,
        },
    ]

    create_skymodel(
        field_id="test_field_002",
        sources=sources,
        calibrators_db=temp_db,
    )

    skymodel_info = get_skymodel_for_field("test_field_002", calibrators_db=temp_db)

    assert skymodel_info is not None
    assert skymodel_info["field_id"] == "test_field_002"
    assert skymodel_info["n_sources"] == 1
    assert skymodel_info["total_flux_jy"] == 5.0


def test_list_skymodels(temp_db, temp_skymodel_dir):
    """Test listing all skymodels."""
    # Create multiple skymodels
    for i in range(3):
        create_skymodel(
            field_id=f"field_{i:03d}",
            sources=[
                {
                    "source_name": f"source_{i}",
                    "ra_deg": 100.0 + i,
                    "dec_deg": 10.0 + i,
                    "flux_jy": 1.0,
                }
            ],
            calibrators_db=temp_db,
        )

    skymodels = list_skymodels(calibrators_db=temp_db)
    assert len(skymodels) == 3


def test_get_sources_for_skymodel(temp_db, temp_skymodel_dir):
    """Test getting sources for a skymodel."""
    sources = [
        {
            "source_name": "source_1",
            "ra_deg": 100.0,
            "dec_deg": 10.0,
            "flux_jy": 5.0,
        },
        {
            "source_name": "source_2",
            "ra_deg": 100.1,
            "dec_deg": 10.1,
            "flux_jy": 3.0,
        },
    ]

    create_skymodel(
        field_id="test_field_003",
        sources=sources,
        calibrators_db=temp_db,
    )

    skymodel_sources = get_sources_for_skymodel("test_field_003", calibrators_db=temp_db)
    assert len(skymodel_sources) == 2
