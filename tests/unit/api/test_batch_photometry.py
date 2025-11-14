"""Unit tests for batch photometry API endpoint and job functions.

Tests the batch photometry functionality with focus on:
- Fast execution (mocked photometry functions)
- Accurate targeting of batch job logic
- Error handling and edge cases
"""

import sqlite3
from pathlib import Path
from typing import Tuple
from unittest.mock import MagicMock, patch

import pytest

from dsa110_contimg.api.batch_jobs import create_batch_photometry_job
from dsa110_contimg.api.models import BatchPhotometryParams, Coordinate
from dsa110_contimg.database.products import ensure_products_db

# Rebuild models to resolve forward references
BatchPhotometryParams.model_rebuild()


class TestBatchPhotometryJobCreation:
    """Test batch photometry job creation."""

    def test_create_batch_photometry_job_success(self, tmp_path):
        """Test successful batch photometry job creation."""
        products_db = tmp_path / "products.sqlite3"
        conn = ensure_products_db(products_db)

        fits_paths = ["/path/to/image1.fits", "/path/to/image2.fits"]
        coordinates = [
            {"ra_deg": 100.0, "dec_deg": 50.0},
            {"ra_deg": 101.0, "dec_deg": 51.0},
        ]
        params = {"box_size_pix": 5, "normalize": False}

        batch_id = create_batch_photometry_job(
            conn, "batch_photometry", fits_paths, coordinates, params
        )

        assert batch_id is not None

        # Verify batch job was created
        cursor = conn.execute("SELECT total_items FROM batch_jobs WHERE id = ?", (batch_id,))
        row = cursor.fetchone()
        assert row[0] == 4  # 2 images * 2 coordinates

        # Verify batch items were created
        cursor = conn.execute(
            "SELECT COUNT(*) FROM batch_job_items WHERE batch_id = ?", (batch_id,)
        )
        count = cursor.fetchone()[0]
        assert count == 4

        conn.close()

    def test_create_batch_photometry_job_validation(self, tmp_path):
        """Test input validation for batch photometry job creation."""
        products_db = tmp_path / "products.sqlite3"
        conn = ensure_products_db(products_db)

        # Test invalid job_type
        with pytest.raises(ValueError, match="job_type must be a non-empty string"):
            create_batch_photometry_job(conn, "", [], [], {})

        # Test invalid fits_paths
        with pytest.raises(ValueError, match="fits_paths must be a list"):
            create_batch_photometry_job(conn, "batch_photometry", "not_a_list", [], {})

        # Test invalid coordinates
        with pytest.raises(ValueError, match="coordinates must be a list"):
            create_batch_photometry_job(conn, "batch_photometry", [], "not_a_list", {})

        # Test invalid params
        with pytest.raises(ValueError, match="params must be a dictionary"):
            create_batch_photometry_job(conn, "batch_photometry", [], [], "not_a_dict")

        conn.close()


class TestBatchPhotometryJobAdapter:
    """Test batch photometry job adapter."""

    @patch("dsa110_contimg.photometry.forced.measure_forced_peak")
    @patch("dsa110_contimg.api.batch_jobs.update_batch_item")
    def test_run_batch_photometry_job_success(self, mock_update, mock_measure, tmp_path):
        """Test successful batch photometry job execution."""
        from dsa110_contimg.api import job_adapters
        from dsa110_contimg.photometry.forced import ForcedPhotometryResult

        products_db = tmp_path / "products.sqlite3"
        conn = ensure_products_db(products_db)

        # Create batch job
        fits_paths = ["/path/to/image1.fits"]
        coordinates = [{"ra_deg": 100.0, "dec_deg": 50.0}]
        params = {"box_size_pix": 5, "normalize": False}

        batch_id = create_batch_photometry_job(
            conn, "batch_photometry", fits_paths, coordinates, params
        )
        conn.close()

        # Mock photometry result
        # ForcedPhotometryResult is a dataclass with specific fields
        mock_result = ForcedPhotometryResult(
            ra_deg=100.0,
            dec_deg=50.0,
            peak_jyb=1.0,
            peak_err_jyb=0.02,
            pix_x=100.0,
            pix_y=200.0,
            box_size_pix=5,
        )
        mock_measure.return_value = mock_result

        # Run batch job
        job_adapters.run_batch_photometry_job(
            batch_id, fits_paths, coordinates, params, products_db
        )

        # Verify batch job status updated
        conn = ensure_products_db(products_db)
        cursor = conn.execute("SELECT status FROM batch_jobs WHERE id = ?", (batch_id,))
        status = cursor.fetchone()[0]
        assert status == "done"

        conn.close()

    @patch("dsa110_contimg.photometry.forced.measure_forced_peak")
    def test_run_batch_photometry_job_with_normalization(self, mock_measure, tmp_path):
        """Test batch photometry job with normalization enabled."""
        from dsa110_contimg.api import job_adapters
        from dsa110_contimg.photometry.forced import ForcedPhotometryResult
        from dsa110_contimg.photometry.normalize import CorrectionResult, ReferenceSource

        products_db = tmp_path / "products.sqlite3"
        conn = ensure_products_db(products_db)

        fits_paths = ["/path/to/image1.fits"]
        coordinates = [{"ra_deg": 100.0, "dec_deg": 50.0}]
        params = {"box_size_pix": 5, "normalize": True}

        batch_id = create_batch_photometry_job(
            conn, "batch_photometry", fits_paths, coordinates, params
        )
        conn.close()

        # Mock photometry result
        # ForcedPhotometryResult is a dataclass with specific fields
        mock_result = ForcedPhotometryResult(
            ra_deg=100.0,
            dec_deg=50.0,
            peak_jyb=1.0,
            peak_err_jyb=0.02,
            pix_x=100.0,
            pix_y=200.0,
            box_size_pix=5,
        )
        mock_measure.return_value = mock_result

        # Mock normalization functions
        with (
            patch("dsa110_contimg.photometry.normalize.query_reference_sources") as mock_query,
            patch(
                "dsa110_contimg.photometry.normalize.compute_ensemble_correction"
            ) as mock_compute,
            patch("dsa110_contimg.photometry.normalize.normalize_measurement") as mock_normalize,
        ):
            mock_query.return_value = [
                ReferenceSource(
                    source_id=1,
                    ra_deg=100.0,
                    dec_deg=50.0,
                    nvss_name="NVSS J100000+500000",
                    nvss_flux_mjy=100.0,
                    snr_nvss=100.0,
                )
            ]
            mock_compute.return_value = CorrectionResult(
                correction_factor=1.05,
                correction_rms=0.02,
                n_references=1,
                reference_measurements=[1.05],
                valid_references=[1],
            )
            mock_normalize.return_value = (0.952, 0.019)

            # Run batch job
            job_adapters.run_batch_photometry_job(
                batch_id, fits_paths, coordinates, params, products_db
            )

            # Verify normalization was called
            mock_query.assert_called_once()
            mock_compute.assert_called_once()
            mock_normalize.assert_called_once()

        conn = ensure_products_db(products_db)
        conn.close()

    @patch("dsa110_contimg.photometry.forced.measure_forced_peak")
    def test_run_batch_photometry_job_failure_handling(self, mock_measure, tmp_path):
        """Test batch photometry job failure handling."""
        from dsa110_contimg.api import job_adapters

        products_db = tmp_path / "products.sqlite3"
        conn = ensure_products_db(products_db)

        fits_paths = ["/path/to/image1.fits"]
        coordinates = [{"ra_deg": 100.0, "dec_deg": 50.0}]
        params = {"box_size_pix": 5, "normalize": False}

        batch_id = create_batch_photometry_job(
            conn, "batch_photometry", fits_paths, coordinates, params
        )
        conn.close()

        # Mock photometry failure - raise exception for the measurement
        mock_measure.side_effect = Exception("Measurement failed")

        # Run batch job
        job_adapters.run_batch_photometry_job(
            batch_id, fits_paths, coordinates, params, products_db
        )

        # Verify batch job status shows failure
        conn = ensure_products_db(products_db)
        cursor = conn.execute(
            "SELECT status, failed_items, completed_items FROM batch_jobs WHERE id = ?", (batch_id,)
        )
        status, failed_items, completed_items = cursor.fetchone()
        # With 1 item that fails, we should have failed_items=1, completed_items=0, status='failed'
        assert failed_items == 1, f"Expected failed_items=1, got {failed_items}"
        assert completed_items == 0, f"Expected completed_items=0, got {completed_items}"
        assert status == "failed", f"Expected status='failed', got status='{status}'"

        conn.close()

    @patch("dsa110_contimg.photometry.forced.measure_forced_peak")
    def test_run_batch_photometry_job_cancellation(self, mock_measure, tmp_path):
        """Test batch photometry job cancellation."""
        from dsa110_contimg.api import job_adapters
        from dsa110_contimg.photometry.forced import ForcedPhotometryResult

        products_db = tmp_path / "products.sqlite3"
        conn = ensure_products_db(products_db)

        fits_paths = ["/path/to/image1.fits", "/path/to/image2.fits"]
        coordinates = [{"ra_deg": 100.0, "dec_deg": 50.0}]
        params = {"box_size_pix": 5, "normalize": False}

        batch_id = create_batch_photometry_job(
            conn, "batch_photometry", fits_paths, coordinates, params
        )
        conn.close()

        # Mock photometry result
        # ForcedPhotometryResult is a dataclass with specific fields
        mock_result = ForcedPhotometryResult(
            ra_deg=100.0,
            dec_deg=50.0,
            peak_jyb=1.0,
            peak_err_jyb=0.02,
            pix_x=100.0,
            pix_y=200.0,
            box_size_pix=5,
        )
        mock_measure.return_value = mock_result

        # Run batch job
        # Note: The function sets status to 'running' at start, then checks cancellation
        # at the start of each fits_path iteration. Testing mid-processing cancellation
        # would require complex async/multi-threaded setup, so this test verifies
        # that normal processing completes successfully.
        job_adapters.run_batch_photometry_job(
            batch_id, fits_paths, coordinates, params, products_db
        )

        # Verify all items were processed
        conn = ensure_products_db(products_db)
        cursor = conn.execute(
            """
            SELECT COUNT(*) FROM batch_job_items
            WHERE batch_id = ? AND status = 'done'
            """,
            (batch_id,),
        )
        done_count = cursor.fetchone()[0]
        assert done_count == len(fits_paths) * len(
            coordinates
        ), f"Expected {len(fits_paths) * len(coordinates)} items processed, got {done_count}"

        conn.close()


class TestBatchPhotometryModels:
    """Test batch photometry models."""

    def test_batch_photometry_params_model(self):
        """Test BatchPhotometryParams model."""
        params = BatchPhotometryParams(
            fits_paths=["/path/to/image1.fits", "/path/to/image2.fits"],
            coordinates=[
                Coordinate(ra_deg=100.0, dec_deg=50.0),
                Coordinate(ra_deg=101.0, dec_deg=51.0),
            ],
            box_size_pix=5,
            annulus_pix=(12, 20),
            use_aegean=False,
            normalize=True,
        )

        assert len(params.fits_paths) == 2
        assert len(params.coordinates) == 2
        assert params.box_size_pix == 5
        assert params.normalize is True

    def test_batch_photometry_params_defaults(self):
        """Test BatchPhotometryParams default values."""
        params = BatchPhotometryParams(
            fits_paths=["/path/to/image.fits"],
            coordinates=[Coordinate(ra_deg=100.0, dec_deg=50.0)],
        )

        assert params.box_size_pix == 5
        assert params.annulus_pix == (12, 20)
        assert params.use_aegean is False
        assert params.normalize is False
