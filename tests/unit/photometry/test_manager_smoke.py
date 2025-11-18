"""Smoke tests for PhotometryManager.

Quick validation that all components work together end-to-end.
Focus: Fast execution, minimal setup, core functionality.
"""

from unittest.mock import patch

import numpy as np
import pytest
from astropy.io import fits

from dsa110_contimg.photometry.manager import (
    PhotometryConfig,
    PhotometryManager,
)


@pytest.fixture
def smoke_fits_file(tmp_path):
    """Create minimal FITS file for smoke tests."""
    fits_path = tmp_path / "smoke_test.fits"

    hdr = fits.Header()
    hdr["NAXIS"] = 2
    hdr["NAXIS1"] = 100
    hdr["NAXIS2"] = 100
    hdr["CRVAL1"] = 180.0
    hdr["CRVAL2"] = 35.0
    hdr["CRPIX1"] = 50.0
    hdr["CRPIX2"] = 50.0
    hdr["CDELT1"] = -0.001
    hdr["CDELT2"] = 0.001
    hdr["CTYPE1"] = "RA---SIN"
    hdr["CTYPE2"] = "DEC--SIN"

    data = np.zeros((100, 100))
    hdu = fits.PrimaryHDU(data=data, header=hdr)
    hdu.writeto(fits_path, overwrite=True)

    return fits_path


@pytest.mark.smoke
@pytest.mark.unit
class TestPhotometryManagerSmoke:
    """Smoke tests for PhotometryManager."""

    def test_manager_initialization(self, tmp_path):
        """Smoke test: Manager can be initialized."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")
        assert manager is not None
        assert manager.default_config.catalog == "nvss"

    @patch("dsa110_contimg.photometry.manager.query_sources_for_fits")
    def test_measure_for_fits_smoke(self, mock_query_sources, tmp_path, smoke_fits_file):
        """Smoke test: measure_for_fits completes without errors."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")

        mock_query_sources.return_value = [
            {"ra_deg": 180.0, "dec_deg": 35.0},
        ]

        result = manager.measure_for_fits(
            fits_path=smoke_fits_file,
            dry_run=True,  # Use dry-run for speed
        )

        assert result is not None
        assert result.sources_queried == 1

    @patch("dsa110_contimg.photometry.manager.query_sources_for_mosaic")
    def test_measure_for_mosaic_smoke(self, mock_query_sources, tmp_path, smoke_fits_file):
        """Smoke test: measure_for_mosaic completes without errors."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")

        mock_query_sources.return_value = [
            {"ra_deg": 180.0, "dec_deg": 35.0},
        ]

        result = manager.measure_for_mosaic(
            mosaic_path=smoke_fits_file,
            dry_run=True,
        )

        assert result is not None
        assert result.sources_queried == 1

    def test_config_creation_smoke(self):
        """Smoke test: Config can be created and converted."""
        config = PhotometryConfig(catalog="nvss", radius_deg=0.5)
        assert config.catalog == "nvss"

        config_dict = config.to_dict()
        assert config_dict["catalog"] == "nvss"

        config2 = PhotometryConfig.from_dict(config_dict)
        assert config2.catalog == "nvss"

    def test_extent_computation_smoke(self, tmp_path, smoke_fits_file):
        """Smoke test: Extent computation works."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")

        config = PhotometryConfig(auto_compute_extent=True)
        ra_radius, dec_radius = manager._get_search_radii(smoke_fits_file, config)

        assert ra_radius > 0
        assert dec_radius > 0

    @patch("dsa110_contimg.photometry.manager.query_sources_for_fits")
    def test_dry_run_smoke(self, mock_query_sources, tmp_path, smoke_fits_file):
        """Smoke test: Dry-run mode works correctly."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")

        mock_query_sources.return_value = [
            {"ra_deg": 180.0, "dec_deg": 35.0},
            {"ra_deg": 180.1, "dec_deg": 35.1},
        ]

        result = manager.measure_for_fits(
            fits_path=smoke_fits_file,
            dry_run=True,
        )

        assert result is not None
        assert result.batch_job_id is None  # No job created in dry-run
        assert result.sources_queried == 2
