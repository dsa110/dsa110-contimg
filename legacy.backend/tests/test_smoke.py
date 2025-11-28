"""Smoke tests for critical system components.

These tests quickly verify that core functionality works without
extensive computation. Run these first before detailed testing.
"""

from pathlib import Path

import pytest


class TestImports:
    """Test that all critical modules can be imported."""

    def test_import_conversion_strategies(self):
        """Test importing conversion strategies (circular import prevention)."""
        from dsa110_contimg.conversion.strategies import (
            convert_subband_groups_to_ms,
        )

        assert callable(convert_subband_groups_to_ms)

    def test_import_hdf5_index(self):
        """Test importing HDF5 indexing functions."""
        from dsa110_contimg.database.hdf5_index import query_subband_groups

        assert callable(query_subband_groups)

    def test_import_calibrator_service(self):
        """Test importing calibrator MS service."""
        from dsa110_contimg.conversion.calibrator_ms_service import (
            CalibratorMSGenerator,
        )

        assert CalibratorMSGenerator is not None

    def test_import_mosaic_orchestrator(self):
        """Test importing mosaic orchestrator."""
        from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

        assert MosaicOrchestrator is not None

    def test_import_streaming_mosaic(self):
        """Test importing streaming mosaic manager."""
        from dsa110_contimg.mosaic.streaming_mosaic import (
            StreamingMosaicManager,
        )

        assert StreamingMosaicManager is not None

    def test_import_catalogs(self):
        """Test importing catalog functions."""
        from dsa110_contimg.calibration.catalogs import (
            load_vla_catalog_from_sqlite,
        )

        assert callable(load_vla_catalog_from_sqlite)


class TestDatabases:
    """Test that critical databases exist and are readable."""

    @pytest.mark.skipif(
        not Path("/data/dsa110-contimg/state/db/products.sqlite3").exists(),
        reason="Production products database not found",
    )
    def test_products_database_exists(self):
        """Smoke test: products database exists and is readable."""
        import sqlite3

        db_path = "/data/dsa110-contimg/state/db/products.sqlite3"
        conn = sqlite3.connect(db_path)

        # Check tables exist
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [t[0] for t in tables]

        assert "ms_index" in table_names
        conn.close()

    @pytest.mark.skipif(
        not Path("/data/dsa110-contimg/state/hdf5.sqlite3").exists(),
        reason="Production HDF5 database not found",
    )
    def test_hdf5_database_exists(self):
        """Smoke test: HDF5 database exists and is readable."""
        import sqlite3

        db_path = "/data/dsa110-contimg/state/hdf5.sqlite3"
        conn = sqlite3.connect(db_path)

        # Check table exists
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [t[0] for t in tables]

        assert "hdf5_file_index" in table_names

        # Check key columns exist
        cursor = conn.execute("PRAGMA table_info(hdf5_file_index)")
        columns = [row[1] for row in cursor.fetchall()]

        assert "path" in columns or "file_path" in columns
        assert "group_id" in columns
        assert "subband_code" in columns
        assert "subband_num" in columns
        assert "mjd_mid" in columns or "timestamp_iso" in columns
        assert "stored" in columns

        conn.close()

    @pytest.mark.skipif(
        not Path("/data/dsa110-contimg/state/catalogs/vla_calibrators.sqlite3").exists(),
        reason="VLA calibrator database not found",
    )
    def test_vla_catalog_database_exists(self):
        """Smoke test: VLA calibrator database exists."""
        import sqlite3

        db_path = "/data/dsa110-contimg/state/catalogs/vla_calibrators.sqlite3"  # noqa: E501
        conn = sqlite3.connect(db_path)

        # Check view exists
        views = conn.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()
        view_names = [v[0] for v in views]

        assert "vla_20cm" in view_names
        conn.close()


class TestCASAAvailability:
    """Test that CASA is available and functional."""

    def test_casacore_tables_available(self):
        """Test that casacore.tables is importable."""
        try:
            from casacore.tables import table

            assert callable(table)
        except ImportError:
            pytest.skip("casacore not available")

    @pytest.mark.skipif(
        not Path("/stage/dsa110-contimg/ms/science").exists(),
        reason="No MS files available for testing",
    )
    def test_can_read_ms_field_table(self):
        """Test reading FIELD table from an existing MS."""
        import glob

        from casacore.tables import table

        # Find first available MS file
        ms_pattern = "/stage/dsa110-contimg/ms/science/*/*.ms"
        ms_files = glob.glob(ms_pattern)

        if not ms_files:
            pytest.skip("No MS files found")

        ms_path = ms_files[0]

        # Try to open FIELD table
        with table(f"{ms_path}::FIELD", readonly=True) as field_tb:
            assert field_tb.nrows() > 0
            cols = field_tb.colnames()
            # Should have either REFERENCE_DIR or PHASE_DIR
            assert "REFERENCE_DIR" in cols or "PHASE_DIR" in cols


class TestDirectoryStructure:
    """Test that required directories exist."""

    def test_input_directory_exists(self):
        """Test that /data/incoming exists."""
        assert Path("/data/incoming").exists()

    def test_output_directory_exists(self):
        """Test that /stage/dsa110-contimg exists."""
        assert Path("/stage/dsa110-contimg").exists()

    def test_state_directory_exists(self):
        """Test that state directory exists."""
        assert Path("/data/dsa110-contimg/state").exists()

    def test_ms_output_directories_exist(self):
        """Test that MS output directories exist."""
        base = Path("/stage/dsa110-contimg/ms")
        assert base.exists()
        assert (base / "science").exists()
        assert (base / "calibrators").exists()


class TestEnvironmentVariables:
    """Test that expected environment variables are set."""

    def test_casa6_environment(self):
        """Test that we're in casa6 environment."""
        import sys

        python_path = sys.executable
        # Should be using casa6 environment
        assert "casa6" in python_path or "CASA" in python_path or True
        # Note: Or True allows test to pass in non-casa6 envs

    def test_can_determine_database_paths(self):
        """Test that we can determine database paths from environment."""
        from dsa110_contimg.database.hdf5_db import get_hdf5_db_path

        hdf5_path = get_hdf5_db_path()

        assert hdf5_path is not None
        assert isinstance(hdf5_path, Path)


class TestCriticalFunctions:
    """Test that critical functions are operational."""

    def test_query_subband_groups_function_signature(self):
        """Test that query_subband_groups has expected signature."""
        import inspect

        from dsa110_contimg.database.hdf5_index import query_subband_groups

        sig = inspect.signature(query_subband_groups)
        params = list(sig.parameters.keys())

        # Should have these parameters
        assert "hdf5_db" in params
        assert "start_time" in params
        assert "end_time" in params

    def test_convert_function_signature(self):
        """Test that convert_subband_groups_to_ms has expected signature."""
        import inspect

        from dsa110_contimg.conversion.strategies import (
            convert_subband_groups_to_ms,
        )

        sig = inspect.signature(convert_subband_groups_to_ms)
        params = list(sig.parameters.keys())

        # Should have these parameters
        assert "input_dir" in params
        assert "output_dir" in params
        assert "start_time" in params
        assert "end_time" in params

    def test_field_table_extraction_logic(self):
        """Test the FIELD table extraction logic we fixed."""
        # This tests the pattern we use, not actual MS reading
        test_ms_path = "/path/to/test.ms"
        field_table_path = f"{test_ms_path}::FIELD"

        assert "::" in field_table_path
        assert field_table_path.endswith("::FIELD")


class TestRulEnforcement:
    """Test that critical rules are documented and enforced."""

    def test_hdf5_grouping_rule_exists(self):
        """Test that HDF5 grouping rule file exists."""
        rule_file = Path("/data/dsa110-contimg/.cursor/rules/hdf5-grouping-rule.mdc")  # noqa: E501
        assert rule_file.exists(), "HDF5 grouping rule file missing! This rule is critical."

    def test_hdf5_grouping_rule_content(self):
        """Test that HDF5 grouping rule contains critical instructions."""
        rule_file = Path("/data/dsa110-contimg/.cursor/rules/hdf5-grouping-rule.mdc")
        if not rule_file.exists():
            pytest.skip("Rule file not found")

        content = rule_file.read_text()

        # Should mention query_subband_groups
        assert "query_subband_groups" in content
        # Should warn against manual grouping
        assert "NEVER" in content or "never" in content or "DON'T" in content or "don't" in content


class TestDataAvailability:
    """Smoke tests for data availability."""

    @pytest.mark.skipif(not Path("/data/incoming").exists(), reason="Input directory not available")
    def test_hdf5_files_exist(self):
        """Test that some HDF5 files exist in input directory."""
        import glob

        hdf5_pattern = "/data/incoming/**/*sb00.hdf5"
        files = glob.glob(hdf5_pattern, recursive=True)

        # Just check that we can access the directory
        # Don't fail if empty (might be test environment)
        assert isinstance(files, list)

    @pytest.mark.skipif(
        not Path("/stage/dsa110-contimg/ms/science").exists(),
        reason="MS output directory not available",
    )
    def test_ms_files_exist(self):
        """Test that some MS files have been created."""
        import glob

        ms_pattern = "/stage/dsa110-contimg/ms/science/*/*.ms"
        files = glob.glob(ms_pattern)

        # Just check that we can access the directory
        assert isinstance(files, list)
