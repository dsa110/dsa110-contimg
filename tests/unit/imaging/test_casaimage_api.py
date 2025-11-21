"""Unit test for casaimage API issues in post-validation and metrics generation.

Tests the specific API calls that are failing:
1. img.close() - AttributeError
2. img.coordsys() - AttributeError
"""

import os
from pathlib import Path

import pytest

# Set CASAPATH before importing CASA
if "CASAPATH" not in os.environ:
    casa_share = "/opt/miniforge/envs/casa6/share/casa"
    if os.path.exists(casa_share):
        os.environ["CASAPATH"] = casa_share

try:
    from casacore.images import image as casaimage

    HAVE_CASACORE = True
except ImportError:
    HAVE_CASACORE = False
    casaimage = None

pytestmark = pytest.mark.skipif(not HAVE_CASACORE, reason="casacore not available")


@pytest.fixture
def mosaic_path():
    """Path to test mosaic."""
    path = Path("/stage/dsa110-contimg/mosaics/2025-10-28_science_mosaic")
    if not path.exists():
        pytest.skip(f"Mosaic not found: {path}")
    return str(path)


def test_casaimage_open(mosaic_path):
    """Test that casaimage can open the mosaic."""
    img = casaimage(mosaic_path)
    assert img is not None

    # Test getdata works
    data = img.getdata()
    assert data is not None
    assert data.size > 0


def test_casaimage_coordsys_method(mosaic_path):
    """Test coordsys() vs coordinates() method availability."""
    img = casaimage(mosaic_path)

    # Check which method exists
    has_coordsys = hasattr(img, "coordsys")
    has_coordinates = hasattr(img, "coordinates")

    assert has_coordsys or has_coordinates, "Neither coordsys() nor coordinates() available"

    # Try to call the available method
    if has_coordsys:
        cs = img.coordsys()
        assert cs is not None
    elif has_coordinates:
        cs = img.coordinates()
        assert cs is not None


def test_casaimage_close_method(mosaic_path):
    """Test close() method availability."""
    img = casaimage(mosaic_path)

    has_close = hasattr(img, "close")
    has_context_manager = hasattr(img, "__enter__") and hasattr(img, "__exit__")

    # At least one cleanup method should exist
    assert has_close or has_context_manager, "No cleanup method available"

    # Test the available method
    if has_close:
        img.close()  # Should not raise
    elif has_context_manager:
        # Test context manager
        with casaimage(mosaic_path) as img2:
            data = img2.getdata()
            assert data is not None


def test_casaimage_context_manager(mosaic_path):
    """Test if casaimage supports context manager."""
    if hasattr(casaimage(mosaic_path), "__enter__"):
        with casaimage(mosaic_path) as img:
            data = img.getdata()
            assert data is not None
    else:
        # If no context manager, test that del works
        img = casaimage(mosaic_path)
        data = img.getdata()
        assert data is not None
        del img  # Should not raise
