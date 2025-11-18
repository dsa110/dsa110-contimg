"""Integration tests for PhotometryManager.

Tests the complete workflow with real database operations and mocked FITS files.
"""

import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest
from astropy.io import fits

from dsa110_contimg.photometry.manager import (
    PhotometryConfig,
    PhotometryManager,
)


@pytest.fixture
def temp_products_db(tmp_path):
    """Create temporary products database with schema."""
    db_path = tmp_path / "products.sqlite3"
    conn = sqlite3.connect(db_path)

    # Create batch_jobs table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS batch_jobs (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            created_at REAL NOT NULL,
            status TEXT NOT NULL,
            total_items INTEGER NOT NULL,
            completed_items INTEGER DEFAULT 0,
            failed_items INTEGER DEFAULT 0,
            params TEXT,
            data_id TEXT
        )
        """
    )

    # Create batch_job_items table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS batch_job_items (
            id INTEGER PRIMARY KEY,
            batch_id INTEGER NOT NULL,
            fits_path TEXT NOT NULL,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            status TEXT NOT NULL,
            job_id INTEGER,
            error TEXT,
            started_at REAL,
            completed_at REAL,
            FOREIGN KEY (batch_id) REFERENCES batch_jobs(id)
        )
        """
    )

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def temp_data_registry_db(tmp_path):
    """Create temporary data registry database."""
    db_path = tmp_path / "data_registry.sqlite3"
    conn = sqlite3.connect(db_path)

    # Create data_products table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS data_products (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            path TEXT NOT NULL,
            created_at REAL NOT NULL,
            photometry_status TEXT,
            photometry_job_id TEXT
        )
        """
    )

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def sample_fits_file(tmp_path):
    """Create a sample FITS file with valid WCS."""
    fits_path = tmp_path / "test_image.fits"

    # Create minimal FITS header with WCS
    hdr = fits.Header()
    hdr["NAXIS"] = 2
    hdr["NAXIS1"] = 512
    hdr["NAXIS2"] = 512
    hdr["CRVAL1"] = 180.0  # RA center
    hdr["CRVAL2"] = 35.0  # Dec center
    hdr["CRPIX1"] = 256.0
    hdr["CRPIX2"] = 256.0
    hdr["CDELT1"] = -0.001  # degrees per pixel
    hdr["CDELT2"] = 0.001
    hdr["CTYPE1"] = "RA---SIN"
    hdr["CTYPE2"] = "DEC--SIN"

    # Create dummy data
    data = np.zeros((512, 512))

    hdu = fits.PrimaryHDU(data=data, header=hdr)
    hdu.writeto(fits_path, overwrite=True)

    return fits_path


@pytest.fixture
def elongated_mosaic_fits(tmp_path):
    """Create an elongated mosaic FITS file (2° RA × 0.5° Dec)."""
    fits_path = tmp_path / "elongated_mosaic.fits"

    hdr = fits.Header()
    hdr["NAXIS"] = 2
    hdr["NAXIS1"] = 2000  # Long in RA
    hdr["NAXIS2"] = 500  # Short in Dec
    hdr["CRVAL1"] = 180.0
    hdr["CRVAL2"] = 35.0
    hdr["CRPIX1"] = 1000.0
    hdr["CRPIX2"] = 250.0
    hdr["CDELT1"] = -0.001
    hdr["CDELT2"] = 0.001
    hdr["CTYPE1"] = "RA---SIN"
    hdr["CTYPE2"] = "DEC--SIN"

    data = np.zeros((500, 2000))
    hdu = fits.PrimaryHDU(data=data, header=hdr)
    hdu.writeto(fits_path, overwrite=True)

    return fits_path


@pytest.mark.integration
class TestPhotometryManagerIntegration:
    """Integration tests for PhotometryManager workflow."""

    @patch("dsa110_contimg.photometry.manager.query_sources_for_fits")
    @patch("dsa110_contimg.photometry.manager.create_batch_photometry_job")
    def test_complete_workflow_batch_job(
        self,
        mock_create_job,
        mock_query_sources,
        temp_products_db,
        sample_fits_file,
    ):
        """Test complete workflow with batch job creation."""
        manager = PhotometryManager(
            products_db_path=temp_products_db,
        )

        # Mock sources
        mock_query_sources.return_value = [
            {"ra_deg": 180.0, "dec_deg": 35.0, "flux_mjy": 50.0},
            {"ra_deg": 180.1, "dec_deg": 35.1, "flux_mjy": 30.0},
        ]

        mock_create_job.return_value = 123

        result = manager.measure_for_fits(
            fits_path=sample_fits_file,
            create_batch_job=True,
            data_id="test_image",
        )

        assert result is not None
        assert result.batch_job_id == 123
        assert result.sources_queried == 2
        assert result.measurements_total == 2
        mock_create_job.assert_called_once()

    @patch("dsa110_contimg.photometry.manager.query_sources_for_fits")
    @patch("dsa110_contimg.photometry.manager.measure_many")
    def test_complete_workflow_synchronous(
        self,
        mock_measure_many,
        mock_query_sources,
        temp_products_db,
        sample_fits_file,
    ):
        """Test complete workflow with synchronous execution."""
        manager = PhotometryManager(
            products_db_path=temp_products_db,
        )

        mock_query_sources.return_value = [
            {"ra_deg": 180.0, "dec_deg": 35.0},
        ]

        # Mock measurement results
        mock_result = Mock()
        mock_result.success = True
        mock_result.ra_deg = 180.0
        mock_result.dec_deg = 35.0
        mock_result.peak_jyb = 0.05
        mock_measure_many.return_value = [mock_result]

        result = manager.measure_for_fits(
            fits_path=sample_fits_file,
            create_batch_job=False,
        )

        assert result is not None
        assert result.measurements_successful == 1
        assert result.results is not None
        mock_measure_many.assert_called_once()

    @patch("dsa110_contimg.photometry.manager.query_sources_for_mosaic")
    @patch("dsa110_contimg.photometry.manager.create_batch_photometry_job")
    def test_mosaic_workflow_with_data_registry(
        self,
        mock_create_job,
        mock_query_sources,
        temp_products_db,
        temp_data_registry_db,
        sample_fits_file,
    ):
        """Test mosaic workflow with data registry linking."""
        manager = PhotometryManager(
            products_db_path=temp_products_db,
            data_registry_db_path=temp_data_registry_db,
        )

        # Insert test data into registry
        conn = sqlite3.connect(temp_data_registry_db)
        conn.execute(
            """
            INSERT INTO data_products (id, type, path, created_at)
            VALUES (?, ?, ?, ?)
            """,
            ("test_mosaic", "mosaic", str(sample_fits_file), 1234567890.0),
        )
        conn.commit()
        conn.close()

        mock_query_sources.return_value = [
            {"ra_deg": 180.0, "dec_deg": 35.0},
        ]
        mock_create_job.return_value = 456

        result = manager.measure_for_mosaic(
            mosaic_path=sample_fits_file,
            create_batch_job=True,
            data_id="test_mosaic",
        )

        assert result is not None
        assert result.batch_job_id == 456

    def test_auto_compute_extent_elongated_mosaic(
        self,
        temp_products_db,
        elongated_mosaic_fits,
    ):
        """Test automatic extent computation for elongated mosaic."""
        manager = PhotometryManager(
            products_db_path=temp_products_db,
        )

        config = PhotometryConfig(auto_compute_extent=True)

        # Should compute extent from FITS header
        ra_radius, dec_radius = manager._get_search_radii(elongated_mosaic_fits, config)

        # For 2° × 0.5° mosaic: extent/2 * 1.1
        # RA: 2.0° / 2 * 1.1 = 1.1°
        # Dec: 0.5° / 2 * 1.1 = 0.275°
        # Allow some tolerance for WCS computation
        assert abs(ra_radius - 1.1) < 0.3  # More lenient for WCS edge effects
        assert abs(dec_radius - 0.275) < 0.1
        assert ra_radius > dec_radius  # Should be elongated (key requirement)

    @patch("dsa110_contimg.photometry.manager.query_sources_for_fits")
    def test_dry_run_integration(
        self,
        mock_query_sources,
        temp_products_db,
        sample_fits_file,
    ):
        """Test dry-run mode in integration context."""
        manager = PhotometryManager(
            products_db_path=temp_products_db,
        )

        mock_query_sources.return_value = [
            {"ra_deg": 180.0, "dec_deg": 35.0},
            {"ra_deg": 180.1, "dec_deg": 35.1},
        ]

        result = manager.measure_for_fits(
            fits_path=sample_fits_file,
            dry_run=True,
        )

        assert result is not None
        assert result.sources_queried == 2
        assert result.batch_job_id is None
        # Should query sources but not create jobs
        mock_query_sources.assert_called_once()

    def test_error_handling_missing_file(self, temp_products_db):
        """Test error handling for missing FITS file."""
        manager = PhotometryManager(
            products_db_path=temp_products_db,
        )

        result = manager.measure_for_fits(
            fits_path=Path("/nonexistent/file.fits"),
        )

        assert result is None
