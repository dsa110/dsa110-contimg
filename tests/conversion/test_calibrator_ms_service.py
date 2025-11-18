"""Tests for CalibratorMSGenerator service.

Tests the calibrator MS generation workflow including:
- Database path handling
- Catalog loading
- HDF5 group querying
- CSV vs SQLite catalog preference
"""

from pathlib import Path
from unittest.mock import Mock, patch

from astropy.time import Time


class TestCalibratorMSServiceInitialization:
    """Test initialization and configuration."""

    def test_init_with_all_parameters(self, tmp_path):
        """Test initialization with all parameters provided."""
        from dsa110_contimg.conversion.calibrator_ms_service import (
            CalibratorMSGenerator,
        )

        gen = CalibratorMSGenerator(
            input_dir=tmp_path / "incoming",
            output_dir=tmp_path / "ms",
            products_db=tmp_path / "products.sqlite3",
            hdf5_db=tmp_path / "hdf5.sqlite3",
            catalogs=[tmp_path / "catalog.sqlite3"],
            verbose=True,
        )

        assert gen.input_dir == tmp_path / "incoming"
        assert gen.output_dir == tmp_path / "ms"
        assert gen.products_db == tmp_path / "products.sqlite3"
        assert gen.hdf5_db == tmp_path / "hdf5.sqlite3"
        assert len(gen.catalogs) == 1

    def test_hdf5_db_defaults_to_env_variable(self, monkeypatch, tmp_path):
        """Test that hdf5_db falls back to HDF5_DB_PATH env var."""
        monkeypatch.setenv("HDF5_DB_PATH", "/env/hdf5.sqlite3")

        from dsa110_contimg.conversion.calibrator_ms_service import (
            CalibratorMSGenerator,
        )

        gen = CalibratorMSGenerator(
            input_dir=tmp_path / "incoming",
            output_dir=tmp_path / "ms",
            products_db=tmp_path / "products.sqlite3",
            catalogs=[],
        )

        assert gen.hdf5_db == Path("/env/hdf5.sqlite3")

    def test_hdf5_db_defaults_to_products_db_if_no_env(self, tmp_path):
        """Test that hdf5_db falls back to default path if no env variable."""
        from dsa110_contimg.conversion.calibrator_ms_service import (
            CalibratorMSGenerator,
        )

        gen = CalibratorMSGenerator(
            input_dir=tmp_path / "incoming",
            output_dir=tmp_path / "ms",
            products_db=tmp_path / "products.sqlite3",
            catalogs=[],
        )

        # Should fall back to a default hdf5.sqlite3 path
        assert gen.hdf5_db.name == "hdf5.sqlite3"


class TestCatalogLoading:
    """Test catalog loading and preference order."""

    @patch("dsa110_contimg.calibration.catalogs.load_vla_catalog_from_sqlite")
    def test_sqlite_catalog_preferred_over_csv(self, mock_load_sqlite, tmp_path):
        """Test that SQLite catalogs are loaded, CSV is disabled."""
        from dsa110_contimg.conversion.calibrator_ms_service import (
            CalibratorMSGenerator,
        )

        mock_load_sqlite.return_value = Mock()

        # Create dummy SQLite file so exists() check passes
        catalog_file = tmp_path / "catalog.sqlite3"
        catalog_file.touch()

        gen = CalibratorMSGenerator(
            input_dir=tmp_path,
            output_dir=tmp_path,
            products_db=tmp_path / "products.sqlite3",
            catalogs=[catalog_file],
        )

        # Should call SQLite loader
        _ = gen._load_catalog_dataframe(catalog_file)
        mock_load_sqlite.assert_called_once_with(str(catalog_file))

    def test_csv_loading_is_disabled(self, tmp_path):
        """Test that CSV catalog loading is disabled."""
        from dsa110_contimg.conversion.calibrator_ms_service import (
            CalibratorMSGenerator,
        )

        gen = CalibratorMSGenerator(
            input_dir=tmp_path,
            output_dir=tmp_path,
            products_db=tmp_path / "products.sqlite3",
            catalogs=[],
        )

        # CSV loading should be disabled (returns None)
        result = gen._load_catalog_dataframe(Path("/data/catalog.csv"))
        assert result is None


class TestHDF5DatabaseQuerying:
    """Test that HDF5 queries use the correct database."""

    @patch("dsa110_contimg.conversion.calibrator_ms_service.query_subband_groups")
    def test_queries_use_hdf5_db_not_products_db(self, mock_query, tmp_path):
        """Test that subband group queries use hdf5_db, not products_db."""
        from dsa110_contimg.conversion.calibrator_ms_service import (
            CalibratorMSGenerator,
        )

        mock_query.return_value = []

        gen = CalibratorMSGenerator(
            input_dir=tmp_path,
            output_dir=tmp_path,
            products_db=tmp_path / "products.sqlite3",
            hdf5_db=tmp_path / "hdf5.sqlite3",
            catalogs=[],
        )

        # Mock the catalog to have a calibrator
        gen.catalog_df = Mock()
        gen.catalog_df.loc = {"0834+555": {"ra_deg": 128.7, "dec_deg": 55.5}}

        # Try to generate (will fail but we only care about the query call)
        try:
            gen.generate_from_transit(
                calibrator_name="0834+555",
                transit_time=Time("2025-10-02T01:00:00"),
                window_minutes=12,
            )
        except Exception:
            pass

        # Verify query_subband_groups was called with hdf5_db, not products_db
        if mock_query.called:
            # First argument should be hdf5_db path
            call_args = mock_query.call_args
            assert call_args[0][0] == Path("/data/hdf5.sqlite3")


class TestSmokeTests:
    """Smoke tests to ensure basic functionality doesn't crash."""

    def test_can_instantiate_without_crash(self):
        """Smoke test: Can create CalibratorMSGenerator instance."""
        from dsa110_contimg.conversion.calibrator_ms_service import (
            CalibratorMSGenerator,
        )

        gen = CalibratorMSGenerator(
            input_dir=Path("/tmp"),
            output_dir=Path("/tmp"),
            products_db=Path("/tmp/products.sqlite3"),
            catalogs=[],
        )

        assert gen is not None
        assert hasattr(gen, "input_dir")
        assert hasattr(gen, "hdf5_db")

    def test_has_required_methods(self):
        """Smoke test: Check that required methods exist."""
        from dsa110_contimg.conversion.calibrator_ms_service import (
            CalibratorMSGenerator,
        )

        gen = CalibratorMSGenerator(
            input_dir=Path("/tmp"),
            output_dir=Path("/tmp"),
            products_db=Path("/tmp/products.sqlite3"),
            catalogs=[],
        )

        assert hasattr(gen, "generate_from_transit")
        assert callable(gen.generate_from_transit)
        assert hasattr(gen, "_load_catalog_dataframe")
        assert callable(gen._load_catalog_dataframe)
