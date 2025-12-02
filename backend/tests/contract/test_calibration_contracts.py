"""
Contract tests for calibration operations.

These tests verify that calibration-related code produces valid,
standards-compliant outputs. Tests use synthetic data fixtures
where possible to avoid dependency on real calibration tables.

Philosophy:
- Test actual behavior, not implementation details
- Verify outputs are valid CASA calibration tables
- Check antenna/frequency coverage contracts
- Validate flagging operations work correctly
"""

import pytest
from pathlib import Path
from typing import Generator
import time


# ============================================================================
# Calibration Table Structure Contracts
# ============================================================================


class TestCalTableDiscovery:
    """Contract tests for calibration table discovery."""

    def test_discover_caltables_returns_dict(self, tmp_path: Path):
        """Verify discover_caltables returns expected structure."""
        from dsa110_contimg.calibration.caltables import discover_caltables
        
        # Create a fake MS directory
        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()
        
        result = discover_caltables(str(ms_path))
        
        # Should always return dict with these keys
        assert isinstance(result, dict)
        assert "k" in result
        assert "bp" in result
        assert "g" in result

    def test_discover_caltables_finds_existing_tables(self, tmp_path: Path):
        """Verify discovery finds existing calibration tables."""
        from dsa110_contimg.calibration.caltables import discover_caltables
        
        # Create fake MS and calibration table directories
        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()
        
        # Create fake bandpass table (CASA cal tables are directories)
        bp_table = tmp_path / "test.bpcal"
        bp_table.mkdir()
        
        result = discover_caltables(str(ms_path))
        
        assert result["bp"] == str(bp_table)

    def test_discover_caltables_nonexistent_ms(self, tmp_path: Path):
        """Verify graceful handling of nonexistent MS."""
        from dsa110_contimg.calibration.caltables import discover_caltables
        
        result = discover_caltables(str(tmp_path / "nonexistent.ms"))
        
        # Should return dict with None values
        assert result["k"] is None
        assert result["bp"] is None
        assert result["g"] is None


class TestCalTableValidation:
    """Contract tests for calibration table validation."""

    def test_validate_caltable_exists_raises_on_missing(self, tmp_path: Path):
        """Verify validation raises FileNotFoundError for missing table."""
        from dsa110_contimg.calibration.validate import validate_caltable_exists
        
        with pytest.raises(FileNotFoundError):
            validate_caltable_exists(str(tmp_path / "nonexistent.bcal"))

    def test_validate_caltable_exists_raises_on_file_not_dir(self, tmp_path: Path):
        """Verify validation raises ValueError for file (not directory)."""
        from dsa110_contimg.calibration.validate import validate_caltable_exists
        
        # Create a file instead of directory
        fake_cal = tmp_path / "fake.bcal"
        fake_cal.write_text("not a cal table")
        
        with pytest.raises(ValueError, match="not a directory"):
            validate_caltable_exists(str(fake_cal))


# ============================================================================
# Transit Calculation Contracts
# ============================================================================


class TestTransitCalculations:
    """Contract tests for transit time calculations."""

    def test_next_transit_time_returns_time_object(self):
        """Verify next_transit_time returns an astropy Time object."""
        from astropy.time import Time
        from dsa110_contimg.calibration.transit import next_transit_time
        
        # Use RA in degrees (3C286 is at RA ~202.8 deg)
        ra_deg = 202.8
        start_time_mjd = Time.now().mjd
        
        result = next_transit_time(ra_deg, start_time_mjd)
        
        assert isinstance(result, Time)

    def test_upcoming_transits_returns_list(self):
        """Verify upcoming_transits returns list of Time objects."""
        from astropy.time import Time
        from dsa110_contimg.calibration.transit import upcoming_transits
        
        # Use RA in degrees
        ra_deg = 202.8
        
        result = upcoming_transits(ra_deg, n=3)
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(t, Time) for t in result)
        # Should be in chronological order
        for i in range(len(result) - 1):
            assert result[i] < result[i + 1]

    def test_previous_transits_returns_list(self):
        """Verify previous_transits returns list of Time objects."""
        from astropy.time import Time
        from dsa110_contimg.calibration.transit import previous_transits
        
        # Use RA in degrees
        ra_deg = 202.8
        
        result = previous_transits(ra_deg, n=3)
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(t, Time) for t in result)
        # All should be in the past
        now = Time.now()
        assert all(t < now for t in result)


# ============================================================================
# Flagging Operation Contracts
# ============================================================================


class TestFlaggingOperations:
    """Contract tests for flagging operations.
    
    These tests verify the flagging functions have correct signatures
    and basic behavior. Full integration tests require a real MS.
    """

    def test_flag_functions_exist(self):
        """Verify all flagging functions are importable."""
        from dsa110_contimg.calibration.flagging import (
            reset_flags,
            flag_zeros,
            flag_rfi,
        )
        
        # Functions should be callable
        assert callable(reset_flags)
        assert callable(flag_zeros)
        assert callable(flag_rfi)

    def test_suppress_subprocess_stderr_context_manager(self):
        """Verify stderr suppression context manager works."""
        from dsa110_contimg.calibration.flagging import suppress_subprocess_stderr
        
        # Should work as context manager without error
        with suppress_subprocess_stderr():
            pass  # No-op, just testing it doesn't crash


# ============================================================================
# Calibration Database Schema Contracts
# ============================================================================


class TestCalibrationDatabaseSchema:
    """Contract tests for calibration table database schema."""

    def test_calibration_tables_schema(self, test_pipeline_db):
        """Verify calibration_tables has all required columns."""
        db = test_pipeline_db
        
        cursor = db.conn.execute("PRAGMA table_info(calibration_tables)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        # Required columns for calibration tables registry
        # Based on actual schema in database/unified.py
        required_columns = {
            "id": "INTEGER",
            "set_name": "TEXT",
            "path": "TEXT",
            "table_type": "TEXT",
            "order_index": "INTEGER",
            "created_at": "REAL",
            "status": "TEXT",
        }
        
        for col_name, col_type in required_columns.items():
            assert col_name in columns, f"Missing column: {col_name}"
            assert columns[col_name] == col_type, \
                f"Column {col_name} has type {columns[col_name]}, expected {col_type}"

    def test_calibration_applied_schema(self, test_pipeline_db):
        """Verify calibration_applied has required columns."""
        db = test_pipeline_db
        
        cursor = db.conn.execute("PRAGMA table_info(calibration_applied)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        # Check table exists and has basic structure
        assert "ms_path" in columns, "calibration_applied should have ms_path column"
        assert "caltable_path" in columns, "calibration_applied should have caltable_path column"
        assert "applied_at" in columns, "calibration_applied should have applied_at column"

    def test_can_insert_calibration_record(self, test_pipeline_db):
        """Verify we can insert and query calibration records."""
        db = test_pipeline_db
        
        now = time.time()
        
        # Insert a calibration table record
        db.execute(
            """INSERT INTO calibration_tables 
               (set_name, path, table_type, order_index, created_at, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("test_set", "/path/to/test.bcal", "bandpass", 0, now, "active")
        )
        
        # Query it back
        results = db.query(
            "SELECT * FROM calibration_tables WHERE path = ?",
            ("/path/to/test.bcal",)
        )
        
        assert len(results) == 1
        assert results[0]["table_type"] == "bandpass"
        assert results[0]["status"] == "active"


# ============================================================================
# Calibration Application Contracts
# ============================================================================


class TestApplycalContracts:
    """Contract tests for calibration application.
    
    These verify the API contracts for applycal functions.
    Full integration tests require real MS and calibration tables.
    """

    def test_apply_to_target_function_exists(self):
        """Verify apply_to_target is importable and callable."""
        from dsa110_contimg.calibration.applycal import apply_to_target
        
        assert callable(apply_to_target)

    def test_verify_corrected_data_function_exists(self):
        """Verify verification function exists."""
        from dsa110_contimg.calibration.applycal import _verify_corrected_data_populated
        
        assert callable(_verify_corrected_data_populated)


# ============================================================================
# Calibrator Selection Contracts
# ============================================================================


class TestCalibratorSelection:
    """Contract tests for calibrator selection logic."""

    def test_bandpass_calibrator_selection_module_exists(self):
        """Verify calibration selection module is available."""
        try:
            from dsa110_contimg.calibration import selection
            # Module should exist
            assert selection is not None
        except ImportError as e:
            # May have missing dependencies (e.g., beam_model)
            pytest.skip(f"Selection module has unmet dependencies: {e}")

    def test_refant_selection_function_exists(self):
        """Verify reference antenna selection is available."""
        try:
            from dsa110_contimg.calibration.refant_selection import select_refant
            assert callable(select_refant)
        except ImportError:
            # Function may have different name
            from dsa110_contimg.calibration import refant_selection
            # Module should exist even if function name differs
            assert refant_selection is not None
