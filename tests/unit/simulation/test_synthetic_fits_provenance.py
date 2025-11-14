"""Tests for synthetic FITS image provenance marking."""

from pathlib import Path

import pytest
from astropy.io import fits

from dsa110_contimg.simulation.synthetic_fits import create_synthetic_fits


def test_synthetic_fits_provenance_marking(tmp_path):
    """Test that synthetic FITS files are properly marked."""
    output_path = tmp_path / "test_synthetic.fits"

    create_synthetic_fits(
        output_path,
        ra_deg=180.0,
        dec_deg=35.0,
        mark_synthetic=True,
    )

    # Verify provenance marking
    with fits.open(output_path) as hdul:
        header = hdul[0].header
        assert header.get("SYNTHETIC") is True
        assert "Synthetic Test Image" in header.get("OBJECT", "")
        assert "synthetic" in str(header.get("COMMENT", "")).lower()


def test_synthetic_fits_no_marking(tmp_path):
    """Test that marking can be disabled."""
    output_path = tmp_path / "test_non_synthetic.fits"

    create_synthetic_fits(
        output_path,
        ra_deg=180.0,
        dec_deg=35.0,
        mark_synthetic=False,
    )

    # Verify no synthetic marking
    with fits.open(output_path) as hdul:
        header = hdul[0].header
        assert header.get("SYNTHETIC") is None
        assert "Synthetic" not in header.get("OBJECT", "")


def test_synthetic_fits_with_sources(tmp_path):
    """Test creating FITS with specific source list."""
    output_path = tmp_path / "test_with_sources.fits"

    sources = [
        {"ra_deg": 180.0, "dec_deg": 35.0, "flux_jy": 1.0, "name": "source1"},
        {"ra_deg": 180.01, "dec_deg": 35.01, "flux_jy": 0.5, "name": "source2"},
    ]

    create_synthetic_fits(
        output_path,
        ra_deg=180.0,
        dec_deg=35.0,
        sources=sources,
        mark_synthetic=True,
    )

    # Verify file was created
    assert output_path.exists()

    # Verify provenance
    with fits.open(output_path) as hdul:
        header = hdul[0].header
        assert header.get("SYNTHETIC") is True
