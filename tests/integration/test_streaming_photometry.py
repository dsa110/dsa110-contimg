"""Integration tests for streaming converter photometry automation."""

import sqlite3
from unittest.mock import Mock, patch

import pytest

from dsa110_contimg.conversion.streaming.streaming_converter import (
    build_parser,
    trigger_photometry_for_image,
)


class TestStreamingPhotometryIntegration:
    """Integration tests for photometry automation in streaming converter."""

    @pytest.fixture
    def temp_products_db(self, tmp_path):
        """Create temporary products database."""
        db_path = tmp_path / "products.sqlite3"
        conn = sqlite3.connect(db_path)
        # Create minimal schema
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
                params TEXT
            )
        """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS batch_job_items (
                id INTEGER PRIMARY KEY,
                batch_id INTEGER NOT NULL,
                ms_path TEXT NOT NULL,
                job_id INTEGER,
                status TEXT NOT NULL,
                error TEXT,
                started_at REAL,
                completed_at REAL,
                data_id TEXT DEFAULT NULL,
                FOREIGN KEY (batch_id) REFERENCES batch_jobs(id)
            )
        """
        )
        conn.commit()
        conn.close()
        return db_path

    @pytest.fixture
    def mock_fits_image(self, tmp_path):
        """Create a mock FITS image file."""
        fits_path = tmp_path / "test_image.pbcor.fits"
        fits_path.touch()
        return fits_path

    @pytest.fixture
    def mock_args(self):
        """Create mock command-line arguments."""
        args = Mock()
        args.photometry_catalog = "nvss"
        args.photometry_radius = 0.5
        args.photometry_normalize = False
        args.photometry_max_sources = None
        return args

    @patch("dsa110_contimg.conversion.streaming.streaming_converter.query_sources_for_fits")
    @patch("dsa110_contimg.api.batch_jobs.create_batch_photometry_job")
    def test_photometry_triggered_after_imaging(
        self,
        mock_create_job,
        mock_query_sources,
        mock_fits_image,
        mock_args,
        temp_products_db,
    ):
        """Test that photometry is triggered after imaging completes."""
        # Setup mocks
        mock_query_sources.return_value = [
            {"ra": 180.0, "dec": 45.0, "flux_mjy": 10.0},
            {"ra": 180.1, "dec": 45.1, "flux_mjy": 20.0},
        ]
        mock_create_job.return_value = 123

        # Trigger photometry
        job_id = trigger_photometry_for_image(
            image_path=mock_fits_image,
            group_id="test_group",
            args=mock_args,
            products_db_path=temp_products_db,
        )

        # Verify photometry was triggered
        assert job_id == 123
        mock_query_sources.assert_called_once()
        mock_create_job.assert_called_once()
        call_args = mock_create_job.call_args
        assert call_args[1]["fits_paths"] == [str(mock_fits_image)]
        assert len(call_args[1]["coordinates"]) == 2
        assert call_args[1]["data_id"] == mock_fits_image.stem

    @patch("dsa110_contimg.conversion.streaming.streaming_converter.query_sources_for_fits")
    def test_no_photometry_when_no_sources(
        self, mock_query_sources, mock_fits_image, mock_args, temp_products_db
    ):
        """Test that photometry is not triggered when no sources found."""
        mock_query_sources.return_value = []

        job_id = trigger_photometry_for_image(
            image_path=mock_fits_image,
            group_id="test_group",
            args=mock_args,
            products_db_path=temp_products_db,
        )

        assert job_id is None
        mock_query_sources.assert_called_once()

    def test_command_line_flags_exist(self):
        """Test that photometry command-line flags exist."""
        parser = build_parser()
        args = parser.parse_args(
            [
                "--input-dir",
                "/tmp",
                "--output-dir",
                "/tmp",
                "--enable-photometry",
                "--photometry-catalog",
                "nvss",
                "--photometry-radius",
                "1.0",
                "--photometry-normalize",
                "--photometry-max-sources",
                "100",
            ]
        )

        assert args.enable_photometry is True
        assert args.photometry_catalog == "nvss"
        assert args.photometry_radius == 1.0
        assert args.photometry_normalize is True
        assert args.photometry_max_sources == 100
