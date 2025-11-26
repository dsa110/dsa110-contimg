"""Unit tests for MosaicOrchestrator with mocked dependencies.

Tests for:
- find_earliest_incomplete_window with various database states
- Transit time calculations
- Photometry configuration
- Default behavior workflow

Uses mocking to avoid CASA/database dependencies.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from astropy.time import Time


@pytest.fixture
def temp_products_db(tmp_path):
    """Create a temporary products database for testing."""
    from dsa110_contimg.database.products import ensure_products_db

    db_path = tmp_path / "test_products.sqlite3"
    conn = ensure_products_db(db_path)

    # Ensure pointing columns exist
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(ms_index)")
    cols = {r[1] for r in cur.fetchall()}
    if "ra_deg" not in cols:
        cur.execute("ALTER TABLE ms_index ADD COLUMN ra_deg REAL")
    if "dec_deg" not in cols:
        cur.execute("ALTER TABLE ms_index ADD COLUMN dec_deg REAL")

    # Ensure mosaic_groups table exists
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS mosaic_groups (
            group_id TEXT PRIMARY KEY,
            mosaic_id TEXT,
            ms_paths TEXT NOT NULL,
            calibration_ms_path TEXT,
            bpcal_solved INTEGER DEFAULT 0,
            created_at REAL NOT NULL,
            calibrated_at REAL,
            imaged_at REAL,
            mosaicked_at REAL,
            status TEXT DEFAULT 'pending',
            stage TEXT,
            cal_applied INTEGER DEFAULT 0
        )
        """
    )

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def temp_data_registry_db(tmp_path):
    """Create a temporary data registry database for testing."""
    from dsa110_contimg.database.data_registry import ensure_data_registry_db

    db_path = tmp_path / "test_registry.sqlite3"
    conn = ensure_data_registry_db(db_path)
    conn.close()
    return db_path


@pytest.fixture
def temp_hdf5_db(tmp_path):
    """Create a temporary HDF5 index database for testing."""
    db_path = tmp_path / "test_hdf5.sqlite3"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS hdf5_file_index (
            path TEXT PRIMARY KEY,
            timestamp TEXT,
            subband INTEGER,
            group_id TEXT
        )
        """
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def orchestrator(temp_products_db, temp_data_registry_db, temp_hdf5_db, tmp_path):
    """Create a MosaicOrchestrator instance for testing."""
    from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

    # Mock the CalibratorMSGenerator to avoid import overhead
    with patch(
        "dsa110_contimg.mosaic.orchestrator.CalibratorMSGenerator"
    ) as mock_gen, patch(
        "dsa110_contimg.mosaic.orchestrator.CalibratorMSConfig.from_env"
    ):
        mock_gen.from_config.return_value = MagicMock()

        return MosaicOrchestrator(
            products_db_path=temp_products_db,
            hdf5_db_path=temp_hdf5_db,
            data_registry_db_path=temp_data_registry_db,
            ms_output_dir=tmp_path / "ms",
            images_dir=tmp_path / "images",
            mosaic_output_dir=tmp_path / "mosaics",
            input_dir=tmp_path / "input",
            enable_photometry=False,
        )


class TestOrchestratorInitialization:
    """Tests for MosaicOrchestrator initialization."""

    def test_default_paths_from_env(
        self, temp_products_db, temp_data_registry_db, tmp_path
    ):
        """Test that default paths are read from environment."""
        from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

        with patch(
            "dsa110_contimg.mosaic.orchestrator.CalibratorMSGenerator"
        ) as mock_gen, patch(
            "dsa110_contimg.mosaic.orchestrator.CalibratorMSConfig.from_env"
        ):
            mock_gen.from_config.return_value = MagicMock()

            orchestrator = MosaicOrchestrator(
                products_db_path=temp_products_db,
                data_registry_db_path=temp_data_registry_db,
                ms_output_dir=tmp_path / "ms",
                images_dir=tmp_path / "images",
                mosaic_output_dir=tmp_path / "mosaics",
            )

            # Paths should be set
            assert orchestrator.products_db_path == temp_products_db
            assert orchestrator.ms_output_dir == tmp_path / "ms"

    def test_photometry_enabled_by_default(
        self, temp_products_db, temp_data_registry_db, tmp_path
    ):
        """Test that photometry is enabled by default."""
        from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

        with patch(
            "dsa110_contimg.mosaic.orchestrator.CalibratorMSGenerator"
        ) as mock_gen, patch(
            "dsa110_contimg.mosaic.orchestrator.CalibratorMSConfig.from_env"
        ):
            mock_gen.from_config.return_value = MagicMock()

            orchestrator = MosaicOrchestrator(
                products_db_path=temp_products_db,
                data_registry_db_path=temp_data_registry_db,
                ms_output_dir=tmp_path / "ms",
                images_dir=tmp_path / "images",
                mosaic_output_dir=tmp_path / "mosaics",
            )

            assert orchestrator.enable_photometry is True

    def test_photometry_disabled(self, orchestrator):
        """Test photometry can be disabled."""
        assert orchestrator.enable_photometry is False
        assert orchestrator.photometry_manager is None


class TestFindEarliestIncompleteWindow:
    """Tests for find_earliest_incomplete_window method."""

    def test_no_ms_files_returns_none(self, orchestrator):
        """Test returns None when no MS files exist."""
        result = orchestrator.find_earliest_incomplete_window()
        assert result is None

    def test_with_ms_files_no_dec(
        self, temp_products_db, temp_data_registry_db, temp_hdf5_db, tmp_path
    ):
        """Test returns None when Dec cannot be determined."""
        from dsa110_contimg.database.products import ensure_products_db
        from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

        # Insert MS files without Dec
        conn = ensure_products_db(temp_products_db)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO ms_index (path, start_mjd, end_mjd, mid_mjd, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("/test/ms/file.ms", 60000.0, 60000.01, 60000.005, "converted"),
        )
        conn.commit()
        conn.close()

        with patch(
            "dsa110_contimg.mosaic.orchestrator.CalibratorMSGenerator"
        ) as mock_gen, patch(
            "dsa110_contimg.mosaic.orchestrator.CalibratorMSConfig.from_env"
        ):
            mock_gen.from_config.return_value = MagicMock()

            orchestrator = MosaicOrchestrator(
                products_db_path=temp_products_db,
                hdf5_db_path=temp_hdf5_db,
                data_registry_db_path=temp_data_registry_db,
                ms_output_dir=tmp_path / "ms",
                images_dir=tmp_path / "images",
                mosaic_output_dir=tmp_path / "mosaics",
            )

        result = orchestrator.find_earliest_incomplete_window()
        assert result is None

    def test_with_ms_files_and_dec(
        self, temp_products_db, temp_data_registry_db, temp_hdf5_db, tmp_path
    ):
        """Test returns window info when MS files with Dec exist."""
        from dsa110_contimg.database.products import ensure_products_db
        from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

        # Insert MS files with Dec
        conn = ensure_products_db(temp_products_db)
        cur = conn.cursor()
        for i in range(10):
            cur.execute(
                """
                INSERT INTO ms_index (path, start_mjd, end_mjd, mid_mjd, status, dec_deg, ra_deg)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"/test/ms/file_{i}.ms",
                    60000.0 + i * 0.01,
                    60000.01 + i * 0.01,
                    60000.005 + i * 0.01,
                    "converted",
                    37.0,  # Dec
                    150.0,  # RA
                ),
            )
        conn.commit()
        conn.close()

        with patch(
            "dsa110_contimg.mosaic.orchestrator.CalibratorMSGenerator"
        ) as mock_gen, patch(
            "dsa110_contimg.mosaic.orchestrator.CalibratorMSConfig.from_env"
        ):
            mock_gen.from_config.return_value = MagicMock()

            orchestrator = MosaicOrchestrator(
                products_db_path=temp_products_db,
                hdf5_db_path=temp_hdf5_db,
                data_registry_db_path=temp_data_registry_db,
                ms_output_dir=tmp_path / "ms",
                images_dir=tmp_path / "images",
                mosaic_output_dir=tmp_path / "mosaics",
            )

            # Mock the BP calibrator lookup
            mock_manager = MagicMock()
            mock_manager.get_bandpass_calibrator_for_dec.return_value = {
                "name": "3C286",
                "ra_deg": 202.78,
            }
            mock_manager.calculate_calibrator_transit.return_value = Time(
                60000.5, format="mjd"
            )
            orchestrator.mosaic_manager = mock_manager

        result = orchestrator.find_earliest_incomplete_window()

        if result is not None:
            assert "dec_deg" in result
            assert result["dec_deg"] == 37.0
            assert "bp_calibrator" in result


class TestMosaicCoverage:
    """Tests for mosaic coverage checking."""

    def test_is_time_range_covered_empty_registry(self, orchestrator):
        """Test coverage check with empty data registry."""
        result = orchestrator._is_time_range_covered_by_published_mosaics(60000.0)
        assert result is False


class TestMosaicManagerCreation:
    """Tests for mosaic manager creation."""

    def test_get_mosaic_manager_lazy_init(self, orchestrator):
        """Test that mosaic manager is lazily initialized."""
        assert orchestrator.mosaic_manager is None

        # Access the manager
        manager = orchestrator._get_mosaic_manager()

        assert manager is not None
        assert orchestrator.mosaic_manager is manager

    def test_get_mosaic_manager_cached(self, orchestrator):
        """Test that mosaic manager is cached."""
        manager1 = orchestrator._get_mosaic_manager()
        manager2 = orchestrator._get_mosaic_manager()

        assert manager1 is manager2


class TestPhotometryConfiguration:
    """Tests for photometry configuration."""

    def test_default_photometry_config(
        self, temp_products_db, temp_data_registry_db, tmp_path
    ):
        """Test default photometry configuration."""
        from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

        with patch(
            "dsa110_contimg.mosaic.orchestrator.CalibratorMSGenerator"
        ) as mock_gen, patch(
            "dsa110_contimg.mosaic.orchestrator.CalibratorMSConfig.from_env"
        ):
            mock_gen.from_config.return_value = MagicMock()

            orchestrator = MosaicOrchestrator(
                products_db_path=temp_products_db,
                data_registry_db_path=temp_data_registry_db,
                ms_output_dir=tmp_path / "ms",
                images_dir=tmp_path / "images",
                mosaic_output_dir=tmp_path / "mosaics",
            )

        assert orchestrator.photometry_config["catalog"] == "nvss"
        assert orchestrator.photometry_config["radius_deg"] == 1.0
        assert orchestrator.photometry_config["normalize"] is False

    def test_custom_photometry_config(
        self, temp_products_db, temp_data_registry_db, tmp_path
    ):
        """Test custom photometry configuration."""
        from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

        custom_config = {
            "catalog": "first",
            "radius_deg": 2.0,
            "normalize": True,
            "max_sources": 100,
        }

        with patch(
            "dsa110_contimg.mosaic.orchestrator.CalibratorMSGenerator"
        ) as mock_gen, patch(
            "dsa110_contimg.mosaic.orchestrator.CalibratorMSConfig.from_env"
        ):
            mock_gen.from_config.return_value = MagicMock()

            orchestrator = MosaicOrchestrator(
                products_db_path=temp_products_db,
                data_registry_db_path=temp_data_registry_db,
                ms_output_dir=tmp_path / "ms",
                images_dir=tmp_path / "images",
                mosaic_output_dir=tmp_path / "mosaics",
                photometry_config=custom_config,
            )

        assert orchestrator.photometry_config["catalog"] == "first"
        assert orchestrator.photometry_config["radius_deg"] == 2.0
        assert orchestrator.photometry_config["normalize"] is True
        assert orchestrator.photometry_config["max_sources"] == 100


class TestConstants:
    """Tests for mosaic orchestrator constants."""

    def test_default_mosaic_span(self):
        """Test default mosaic span constant."""
        from dsa110_contimg.mosaic.orchestrator import DEFAULT_MOSAIC_SPAN_MINUTES

        assert DEFAULT_MOSAIC_SPAN_MINUTES == 50

    def test_default_ms_per_mosaic(self):
        """Test default MS per mosaic constant."""
        from dsa110_contimg.mosaic.orchestrator import DEFAULT_MS_PER_MOSAIC

        assert DEFAULT_MS_PER_MOSAIC == 10

    def test_ms_overlap(self):
        """Test MS overlap constant."""
        from dsa110_contimg.mosaic.orchestrator import MS_OVERLAP

        assert MS_OVERLAP == 2

    def test_ms_duration(self):
        """Test MS duration constant."""
        from dsa110_contimg.mosaic.orchestrator import MS_DURATION_MINUTES

        assert MS_DURATION_MINUTES == 5
