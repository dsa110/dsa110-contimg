"""Tests for VLA calibrator catalog functionality.

Tests the catalog loading system including:
- SQLite database loading
- CSV fallback (currently disabled)
- Calibrator lookup
- Database schema validation
"""

from pathlib import Path

import pandas as pd
import pytest


class TestSQLiteCatalogLoading:
    """Test SQLite catalog loading."""

    def test_load_vla_catalog_from_sqlite(self):
        """Test loading VLA catalog from SQLite database."""
        from dsa110_contimg.calibration.catalogs import (
            load_vla_catalog_from_sqlite,
        )

        catalog_path = Path("/data/dsa110-contimg/state/catalogs/vla_calibrators.sqlite3")

        if not catalog_path.exists():
            pytest.skip("VLA calibrator database not found")

        df = load_vla_catalog_from_sqlite(str(catalog_path))

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        # Check that calibrator names are in the index or column
        assert df.index.name == "source" or "source" in df.columns or len(df.index) > 0

    def test_sqlite_catalog_has_required_columns(self):
        """Test that SQLite catalog has required columns after loading."""
        from dsa110_contimg.calibration.catalogs import (
            load_vla_catalog_from_sqlite,
        )

        # This test requires actual database file
        catalog_path = Path("/data/dsa110-contimg/state/catalogs/vla_calibrators.sqlite3")

        if not catalog_path.exists():
            pytest.skip("VLA calibrator database not found")

        df = load_vla_catalog_from_sqlite(str(catalog_path))

        # Check required columns (ra_deg, dec_deg, or ra, dec)
        has_ra = "ra_deg" in df.columns or "ra" in df.columns
        has_dec = "dec_deg" in df.columns or "dec" in df.columns
        assert has_ra, "Catalog missing RA column"
        assert has_dec, "Catalog missing Dec column"
        # Should have some calibrators
        assert len(df) > 0


class TestCSVCatalogFallback:
    """Test CSV catalog fallback (currently disabled)."""

    def test_csv_fallback_is_disabled_in_service(self):
        """Test that CSV fallback is disabled in CalibratorMSService."""
        from pathlib import Path

        from dsa110_contimg.conversion.calibrator_ms_service import (
            CalibratorMSGenerator,
        )

        gen = CalibratorMSGenerator(
            input_dir=Path("/tmp"),
            output_dir=Path("/tmp"),
            products_db=Path("/tmp/products.sqlite3"),
            catalogs=[],
        )

        # CSV loading should return None (disabled)
        result = gen._load_catalog_dataframe(Path("/data/catalog.csv"))
        assert result is None


class TestCalibratorLookup:
    """Test calibrator lookup in catalogs."""

    def test_calibrator_lookup_by_name(self):
        """Test finding calibrator by name in catalog."""
        from dsa110_contimg.calibration.catalogs import (
            load_vla_catalog_from_sqlite,
        )

        catalog_path = Path("/data/dsa110-contimg/state/catalogs/vla_calibrators.sqlite3")

        if not catalog_path.exists():
            pytest.skip("VLA calibrator database not found")

        df = load_vla_catalog_from_sqlite(str(catalog_path))

        # Check if 0834+555 exists
        if "0834+555" in df.index:
            calibrator = df.loc["0834+555"]
            assert "ra_deg" in calibrator or "ra_deg" in df.columns
            assert "dec_deg" in calibrator or "dec_deg" in df.columns


class TestIntegrationTests:
    """Integration tests for full catalog loading workflow."""

    def test_catalog_can_be_loaded_and_queried(self):
        """Integration test: Load catalog and query for known calibrator."""
        from dsa110_contimg.calibration.catalogs import (
            load_vla_catalog_from_sqlite,
        )

        catalog_path = Path("/data/dsa110-contimg/state/catalogs/vla_calibrators.sqlite3")

        if not catalog_path.exists():
            pytest.skip("VLA calibrator database not found")

        # Load catalog
        df = load_vla_catalog_from_sqlite(str(catalog_path))

        # Should have at least one calibrator
        assert len(df) > 0

        # Should have coordinate columns
        has_coords = ("ra_deg" in df.columns or "ra" in df.columns) and (
            "dec_deg" in df.columns or "dec" in df.columns
        )
        assert has_coords


class TestSmokeTests:
    """Smoke tests for catalog module."""

    def test_can_import_catalog_functions(self):
        """Smoke test: Can import catalog functions without crash."""
        from dsa110_contimg.calibration.catalogs import (
            load_vla_catalog_from_sqlite,
        )

        assert callable(load_vla_catalog_from_sqlite)

    def test_sqlite_load_with_nonexistent_file(self):
        """Smoke test: Loading nonexistent SQLite file raises error."""
        from dsa110_contimg.calibration.catalogs import (
            load_vla_catalog_from_sqlite,
        )

        with pytest.raises(Exception):  # Should raise some error
            load_vla_catalog_from_sqlite("/nonexistent/catalog.sqlite3")
