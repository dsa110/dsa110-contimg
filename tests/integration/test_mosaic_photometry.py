"""Integration tests for mosaic orchestrator photometry automation."""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator


class TestMosaicPhotometryIntegration:
    """Integration tests for photometry automation in mosaic orchestrator."""

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
    def mock_mosaic_path(self, tmp_path):
        """Create a mock mosaic FITS file."""
        mosaic_path = tmp_path / "mosaic.fits"
        mosaic_path.touch()
        return mosaic_path

    @pytest.fixture
    def orchestrator_with_photometry(self, temp_products_db):
        """Create orchestrator with photometry enabled."""
        return MosaicOrchestrator(
            products_db_path=temp_products_db,
            enable_photometry=True,
            photometry_config={
                "catalog": "nvss",
                "radius_deg": 1.0,
                "normalize": False,
                "max_sources": None,
            },
        )

    @patch("dsa110_contimg.mosaic.orchestrator.query_sources_for_mosaic")
    @patch("dsa110_contimg.api.batch_jobs.create_batch_photometry_job")
    def test_photometry_triggered_after_mosaic(
        self,
        mock_create_job,
        mock_query_sources,
        orchestrator_with_photometry,
        mock_mosaic_path,
        temp_products_db,
    ):
        """Test that photometry is triggered after mosaic creation."""
        # Setup mocks
        mock_query_sources.return_value = [
            {"ra": 180.0, "dec": 45.0, "flux_mjy": 10.0},
            {"ra": 180.1, "dec": 45.1, "flux_mjy": 20.0},
            {"ra": 180.2, "dec": 45.2, "flux_mjy": 30.0},
        ]
        mock_create_job.return_value = 456

        # Trigger photometry
        job_id = orchestrator_with_photometry._trigger_photometry_for_mosaic(
            mosaic_path=mock_mosaic_path,
            group_id="test_group",
        )

        # Verify photometry was triggered
        assert job_id == 456
        mock_query_sources.assert_called_once()
        mock_create_job.assert_called_once()
        call_args = mock_create_job.call_args
        assert call_args[1]["fits_paths"] == [str(mock_mosaic_path)]
        assert len(call_args[1]["coordinates"]) == 3
        assert call_args[1]["data_id"] == mock_mosaic_path.stem

    @patch("dsa110_contimg.mosaic.orchestrator.query_sources_for_mosaic")
    def test_no_photometry_when_no_sources(
        self,
        mock_query_sources,
        orchestrator_with_photometry,
        mock_mosaic_path,
    ):
        """Test that photometry is not triggered when no sources found."""
        mock_query_sources.return_value = []

        job_id = orchestrator_with_photometry._trigger_photometry_for_mosaic(
            mosaic_path=mock_mosaic_path,
            group_id="test_group",
        )

        assert job_id is None
        mock_query_sources.assert_called_once()

    def test_photometry_disabled_by_default(self, temp_products_db):
        """Test that photometry is disabled by default."""
        orchestrator = MosaicOrchestrator(products_db_path=temp_products_db)
        assert orchestrator.enable_photometry is False

    def test_photometry_config_defaults(self, temp_products_db):
        """Test that photometry config has correct defaults."""
        orchestrator = MosaicOrchestrator(products_db_path=temp_products_db, enable_photometry=True)
        assert orchestrator.photometry_config["catalog"] == "nvss"
        assert orchestrator.photometry_config["radius_deg"] == 1.0
        assert orchestrator.photometry_config["normalize"] is False
        assert orchestrator.photometry_config["max_sources"] is None
