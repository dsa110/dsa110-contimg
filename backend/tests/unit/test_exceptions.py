"""
Unit tests for custom exception classes.

Tests the exception hierarchy, context propagation, and helper functions
defined in dsa110_contimg.utils.exceptions.
"""

import pytest
from datetime import datetime

from dsa110_contimg.utils.exceptions import (
    # Base exception
    PipelineError,
    # Subband errors
    SubbandGroupingError,
    IncompleteSubbandGroupError,
    # Conversion errors
    ConversionError,
    UVH5ReadError,
    MSWriteError,
    # Database errors
    DatabaseError,
    DatabaseMigrationError,
    DatabaseConnectionError,
    DatabaseLockError,
    # Queue errors
    QueueError,
    QueueStateTransitionError,
    # Calibration errors
    CalibrationError,
    CalibrationTableNotFoundError,
    CalibratorNotFoundError,
    # Imaging errors
    ImagingError,
    ImageNotFoundError,
    # Validation errors
    ValidationError,
    MissingParameterError,
    InvalidPathError,
    # Helpers
    wrap_exception,
    is_recoverable,
)


class TestPipelineError:
    """Tests for base PipelineError class."""
    
    def test_creates_with_message(self):
        """Test basic exception creation."""
        err = PipelineError("Test error message")
        assert str(err) == "Test error message"
        assert err.message == "Test error message"
    
    def test_includes_context_in_repr(self):
        """Test context is included in string representation."""
        err = PipelineError(
            "Error",
            group_id="2025-01-15T12:30:00",
            pipeline_stage="conversion",
        )
        assert "group_id=2025-01-15T12:30:00" in str(err)
        assert "stage=conversion" in str(err)
    
    def test_context_property_includes_metadata(self):
        """Test context dict includes error metadata."""
        err = PipelineError(
            "Test error",
            pipeline_stage="test_stage",
            custom_key="custom_value",
        )
        
        ctx = err.context
        assert ctx["error_type"] == "PipelineError"
        assert ctx["message"] == "Test error"
        assert ctx["pipeline_stage"] == "test_stage"
        assert ctx["custom_key"] == "custom_value"
        assert "timestamp" in ctx
    
    def test_captures_original_exception(self):
        """Test original exception is captured."""
        original = ValueError("Original error")
        err = PipelineError(
            "Wrapped error",
            original_exception=original,
        )
        
        assert err.original_exception is original
        assert "original_error" in err.context
        assert "ValueError" in err.context["original_type"]
        assert "traceback" in err.context
    
    def test_recoverable_flag(self):
        """Test recoverable flag."""
        recoverable = PipelineError("Error", recoverable=True)
        not_recoverable = PipelineError("Error", recoverable=False)
        
        assert recoverable.recoverable is True
        assert not_recoverable.recoverable is False


class TestSubbandGroupingError:
    """Tests for subband grouping errors."""
    
    def test_creates_with_group_context(self):
        """Test subband error includes group context."""
        err = SubbandGroupingError(
            "Incomplete group",
            group_id="2025-01-15T12:30:00",
            expected_count=16,
            actual_count=14,
            missing_subbands=["sb03", "sb07"],
        )
        
        assert err.context["group_id"] == "2025-01-15T12:30:00"
        assert err.context["expected_count"] == 16
        assert err.context["actual_count"] == 14
        assert "sb03" in err.context["missing_subbands"]
        assert err.context["pipeline_stage"] == "subband_grouping"
    
    def test_incomplete_subband_group_error(self):
        """Test IncompleteSubbandGroupError factory."""
        err = IncompleteSubbandGroupError(
            group_id="2025-01-15T12:30:00",
            expected_count=16,
            actual_count=14,
            missing_subbands=["sb03", "sb07"],
        )
        
        assert "expected 16 subbands" in err.message
        assert "found 14" in err.message
        assert err.recoverable is True  # Can skip incomplete groups


class TestConversionError:
    """Tests for conversion errors."""
    
    def test_includes_io_paths(self):
        """Test conversion error includes input/output paths."""
        err = ConversionError(
            "Conversion failed",
            input_path="/data/incoming/obs.hdf5",
            output_path="/stage/output.ms",
            group_id="2025-01-15T12:30:00",
        )
        
        assert err.context["input_path"] == "/data/incoming/obs.hdf5"
        assert err.context["output_path"] == "/stage/output.ms"
        assert err.context["pipeline_stage"] == "conversion"
    
    def test_uvh5_read_error(self):
        """Test UVH5ReadError specifics."""
        err = UVH5ReadError(
            file_path="/data/incoming/corrupt.hdf5",
            reason="Invalid HDF5 structure",
        )
        
        assert "corrupt.hdf5" in err.message
        assert "Invalid HDF5 structure" in err.message
        assert err.context["input_path"] == "/data/incoming/corrupt.hdf5"
    
    def test_ms_write_error(self):
        """Test MSWriteError specifics."""
        err = MSWriteError(
            output_path="/stage/output.ms",
            reason="Disk full",
        )
        
        assert "output.ms" in err.message
        assert "Disk full" in err.message
        assert err.recoverable is False


class TestDatabaseError:
    """Tests for database errors."""
    
    def test_includes_db_context(self):
        """Test database error includes database context."""
        err = DatabaseError(
            "Query failed",
            db_name="products",
            db_path="/data/state/db/products.sqlite3",
            operation="insert",
            table_name="images",
        )
        
        assert err.context["db_name"] == "products"
        assert err.context["operation"] == "insert"
        assert err.context["table_name"] == "images"
        assert err.context["pipeline_stage"] == "database"
    
    def test_migration_error(self):
        """Test DatabaseMigrationError specifics."""
        err = DatabaseMigrationError(
            db_name="products",
            migration_version="v2.0",
            reason="Column type mismatch",
        )
        
        assert "products" in err.message
        assert "v2.0" in err.message
        assert "Column type mismatch" in err.message
        assert err.recoverable is False
    
    def test_connection_error(self):
        """Test DatabaseConnectionError specifics."""
        err = DatabaseConnectionError(
            db_name="ingest",
            db_path="/data/state/db/ingest.sqlite3",
            reason="Permission denied",
        )
        
        assert "ingest" in err.message
        assert "Permission denied" in err.message
    
    def test_lock_error_is_recoverable(self):
        """Test DatabaseLockError is marked recoverable."""
        err = DatabaseLockError(
            db_name="products",
            timeout_seconds=30.0,
        )
        
        assert err.recoverable is True
        assert "30.0" in err.message


class TestQueueError:
    """Tests for queue errors."""
    
    def test_state_transition_error(self):
        """Test QueueStateTransitionError."""
        err = QueueStateTransitionError(
            group_id="2025-01-15T12:30:00",
            current_state="completed",
            target_state="in_progress",
            reason="Cannot restart completed jobs",
        )
        
        assert "completed" in err.message
        assert "in_progress" in err.message
        assert err.context["group_id"] == "2025-01-15T12:30:00"


class TestCalibrationError:
    """Tests for calibration errors."""
    
    def test_cal_table_not_found(self):
        """Test CalibrationTableNotFoundError."""
        err = CalibrationTableNotFoundError(
            ms_path="/stage/obs.ms",
            cal_table="/stage/obs.bcal",
        )
        
        assert "obs.bcal" in err.message
        assert "obs.ms" in err.message
        assert err.context["pipeline_stage"] == "calibration"
    
    def test_calibrator_not_found(self):
        """Test CalibratorNotFoundError."""
        err = CalibratorNotFoundError(
            calibrator="3C999",
            catalog="VLA",
        )
        
        assert "3C999" in err.message
        assert "VLA" in err.message


class TestValidationError:
    """Tests for validation errors."""
    
    def test_missing_parameter(self):
        """Test MissingParameterError."""
        err = MissingParameterError(parameter="input_dir")
        
        assert "input_dir" in err.message
        assert err.context["field"] == "input_dir"
        assert err.recoverable is True
    
    def test_invalid_path_error(self):
        """Test InvalidPathError."""
        err = InvalidPathError(
            path="/nonexistent/path",
            path_type="directory",
            reason="Path does not exist",
        )
        
        assert "directory" in err.message
        assert "/nonexistent/path" in err.message
        assert err.context["value"] == "/nonexistent/path"


class TestWrapException:
    """Tests for wrap_exception helper."""
    
    def test_wraps_standard_exception(self):
        """Test wrapping a standard Python exception."""
        original = FileNotFoundError("File not found: /data/test.hdf5")
        
        # Use ConversionError which has compatible signature
        wrapped = wrap_exception(
            original,
            ConversionError,
            input_path="/data/test.hdf5",
        )
        
        assert isinstance(wrapped, ConversionError)
        assert wrapped.original_exception is original
        assert "File not found" in str(wrapped)
    
    def test_falls_back_to_pipeline_error(self):
        """Test fallback to PipelineError for incompatible signatures."""
        original = FileNotFoundError("File not found")
        
        # UVH5ReadError has specific required args, so fallback is used
        wrapped = wrap_exception(
            original,
            UVH5ReadError,
            file_path="/data/test.hdf5",
        )
        
        # Falls back to PipelineError due to signature mismatch
        assert isinstance(wrapped, PipelineError)
        assert wrapped.original_exception is original
    
    def test_preserves_traceback(self):
        """Test that traceback is preserved."""
        try:
            raise ValueError("Inner error")
        except ValueError as e:
            wrapped = wrap_exception(e, ConversionError)
            assert "traceback" in wrapped.context
            assert "ValueError" in wrapped.context["traceback"]


class TestIsRecoverable:
    """Tests for is_recoverable helper."""
    
    def test_pipeline_error_recoverable(self):
        """Test checking PipelineError recoverable flag."""
        recoverable = SubbandGroupingError("Error", recoverable=True)
        not_recoverable = MSWriteError("/path.ms")
        
        assert is_recoverable(recoverable) is True
        assert is_recoverable(not_recoverable) is False
    
    def test_standard_exceptions(self):
        """Test standard exceptions considered recoverable."""
        assert is_recoverable(FileNotFoundError()) is True
        assert is_recoverable(PermissionError()) is True
        assert is_recoverable(TimeoutError()) is True
        assert is_recoverable(ValueError()) is False


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""
    
    def test_all_inherit_from_pipeline_error(self):
        """Test all custom exceptions inherit from PipelineError."""
        exception_classes = [
            SubbandGroupingError,
            IncompleteSubbandGroupError,
            ConversionError,
            UVH5ReadError,
            MSWriteError,
            DatabaseError,
            DatabaseMigrationError,
            DatabaseConnectionError,
            DatabaseLockError,
            QueueError,
            QueueStateTransitionError,
            CalibrationError,
            CalibrationTableNotFoundError,
            CalibratorNotFoundError,
            ImagingError,
            ImageNotFoundError,
            ValidationError,
            MissingParameterError,
            InvalidPathError,
        ]
        
        for cls in exception_classes:
            assert issubclass(cls, PipelineError)
            assert issubclass(cls, Exception)
    
    def test_subclass_relationships(self):
        """Test specific subclass relationships."""
        assert issubclass(IncompleteSubbandGroupError, SubbandGroupingError)
        assert issubclass(UVH5ReadError, ConversionError)
        assert issubclass(MSWriteError, ConversionError)
        assert issubclass(DatabaseMigrationError, DatabaseError)
        assert issubclass(DatabaseConnectionError, DatabaseError)
        assert issubclass(DatabaseLockError, DatabaseError)
        assert issubclass(QueueStateTransitionError, QueueError)
        assert issubclass(CalibrationTableNotFoundError, CalibrationError)
        assert issubclass(CalibratorNotFoundError, CalibrationError)
        assert issubclass(ImageNotFoundError, ImagingError)
        assert issubclass(MissingParameterError, ValidationError)
        assert issubclass(InvalidPathError, ValidationError)
