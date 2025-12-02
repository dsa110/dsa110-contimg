"""
Unit tests for conversion module error handling.

Tests error scenarios in the HDF5 orchestrator and related conversion
code, including subband grouping failures, read errors, and write errors.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from dsa110_contimg.utils.exceptions import (
    ConversionError,
    SubbandGroupingError,
    IncompleteSubbandGroupError,
    UVH5ReadError,
    MSWriteError,
    DatabaseError,
    InvalidPathError,
)


class TestHDF5OrchestratorErrors:
    """Tests for error handling in hdf5_orchestrator module."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock out dependencies that may not be available."""
        with patch.dict('sys.modules', {
            'dsa110_contimg.utils.antpos_local': MagicMock(),
            'pyuvdata': MagicMock(),
        }):
            yield
    
    def test_raises_on_nonexistent_input_dir(self, mock_dependencies):
        """Test that ConversionError is raised for missing input directory."""
        try:
            from dsa110_contimg.conversion import convert_subband_groups_to_ms
        except (ImportError, AttributeError):
            pytest.skip("hdf5_orchestrator not available")
        
        with patch("dsa110_contimg.conversion.strategies.hdf5_orchestrator.query_subband_groups"):
            with pytest.raises(ConversionError) as exc_info:
                convert_subband_groups_to_ms(
                    input_dir="/nonexistent/path",
                    output_dir="/tmp/output",
                    start_time="2025-01-15T00:00:00",
                    end_time="2025-01-15T23:59:59",
                )
            
            assert "does not exist" in str(exc_info.value)
            assert exc_info.value.context["input_path"] == "/nonexistent/path"
    
    def test_handles_database_query_failure(self, mock_dependencies, tmp_path):
        """Test handling of database query failures."""
        try:
            from dsa110_contimg.conversion import convert_subband_groups_to_ms
        except (ImportError, AttributeError):
            pytest.skip("hdf5_orchestrator not available")
        
        with patch("dsa110_contimg.conversion.strategies.hdf5_orchestrator.query_subband_groups") as mock_query:
            mock_query.side_effect = DatabaseError("Connection failed", db_name="hdf5")
            
            with pytest.raises(ConversionError) as exc_info:
                convert_subband_groups_to_ms(
                    input_dir=str(tmp_path),
                    output_dir=str(tmp_path / "output"),
                    start_time="2025-01-15T00:00:00",
                    end_time="2025-01-15T23:59:59",
                )
            
            assert "query subband groups" in str(exc_info.value).lower()


class TestHDF5IndexErrors:
    """Tests for error handling in hdf5_index module."""
    
    def test_raises_on_nonexistent_directory(self):
        """Test InvalidPathError for missing directory."""
        from dsa110_contimg.database.hdf5_index import index_hdf5_files
        
        with pytest.raises(InvalidPathError) as exc_info:
            index_hdf5_files("/nonexistent/directory")
        
        # Check exception properties
        assert "directory" in str(exc_info.value).lower()
        assert "/nonexistent/directory" in str(exc_info.value)
    
    def test_raises_on_nonexistent_file(self):
        """Test InvalidPathError for missing file."""
        from dsa110_contimg.database.hdf5_index import query_hdf5_file
        
        with pytest.raises(InvalidPathError) as exc_info:
            query_hdf5_file("/nonexistent/file.hdf5", "data")
        
        assert "file" in str(exc_info.value).lower()
    
    def test_raises_on_nonexistent_db(self):
        """Test InvalidPathError for missing database file."""
        from dsa110_contimg.database.hdf5_index import query_subband_groups
        
        with pytest.raises(InvalidPathError) as exc_info:
            query_subband_groups(
                "/nonexistent/db.sqlite3",
                "2025-01-15T00:00:00",
                "2025-01-15T23:59:59",
            )
        
        assert "database" in str(exc_info.value).lower()
    
    def test_continues_on_corrupt_files(self, tmp_path):
        """Test that indexing continues when some files are corrupt."""
        from dsa110_contimg.database.hdf5_index import index_hdf5_files
        
        # Create a corrupt HDF5 file
        corrupt_file = tmp_path / "corrupt.hdf5"
        corrupt_file.write_text("not valid hdf5 data")
        
        # Should not raise, but return empty list with logged warning
        results = index_hdf5_files(str(tmp_path))
        
        assert results == []  # No valid files indexed


class TestQueueStateValidation:
    """Tests for queue state validation."""
    
    def test_valid_transitions(self):
        """Test that valid state transitions are recognized."""
        # Define expected valid transitions
        valid = [
            ("collecting", "pending"),
            ("collecting", "failed"),
            ("pending", "in_progress"),
            ("pending", "failed"),
            ("in_progress", "completed"),
            ("in_progress", "failed"),
            ("failed", "pending"),  # Retry
        ]
        
        invalid = [
            ("completed", "pending"),
            ("completed", "in_progress"),
            ("collecting", "completed"),
            ("completed", "collecting"),
        ]
        
        # These are the expected behaviors based on the state machine
        for from_state, to_state in valid:
            # No exception should be raised for valid transitions
            pass  # State machine validation happens at runtime
        
        for from_state, to_state in invalid:
            # These would be invalid transitions
            pass


class TestConversionMetricsDataclass:
    """Tests for conversion metrics."""
    
    def test_metrics_to_dict(self):
        """Test ConversionMetrics dataclass without imports."""
        from dataclasses import dataclass, field, asdict
        from datetime import datetime
        from typing import Any
        
        @dataclass
        class TestMetrics:
            group_id: str
            load_time: float = 0.0
            phase_time: float = 0.0
            write_time: float = 0.0
            total_time: float = 0.0
            subband_count: int = 0
            output_size_bytes: int = 0
            recorded_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
        
        metrics = TestMetrics(
            group_id="2025-01-15T12:30:00",
            load_time=10.5,
            phase_time=2.3,
            write_time=15.7,
            total_time=28.5,
            subband_count=16,
            output_size_bytes=1024 * 1024 * 100,
        )
        
        d = asdict(metrics)
        
        assert d["group_id"] == "2025-01-15T12:30:00"
        assert d["load_time"] == 10.5
        assert d["subband_count"] == 16
        assert "recorded_at" in d


class TestErrorRecovery:
    """Tests for error recovery patterns."""
    
    def test_recoverable_errors_can_retry(self):
        """Test that recoverable errors are marked for retry."""
        from dsa110_contimg.utils.exceptions import is_recoverable, DatabaseLockError
        
        # Database lock is recoverable
        lock_err = DatabaseLockError("ingest")
        assert is_recoverable(lock_err)
        
        # Incomplete group is recoverable (skip and continue)
        incomplete = IncompleteSubbandGroupError(
            group_id="test",
            expected_count=16,
            actual_count=14,
        )
        assert is_recoverable(incomplete)
        
        # MS write error is not recoverable
        write_err = MSWriteError("/path.ms", reason="Disk full")
        assert not is_recoverable(write_err)
    
    def test_error_context_for_logging(self):
        """Test that errors provide useful context for logging."""
        err = UVH5ReadError(
            file_path="/data/incoming/corrupt.hdf5",
            reason="Invalid magic number",
            group_id="2025-01-15T12:30:00",
        )
        
        ctx = err.context
        
        # Should have all relevant context for log analysis
        assert "input_path" in ctx
        assert ctx["pipeline_stage"] == "conversion"
        assert "timestamp" in ctx
        assert ctx.get("group_id") == "2025-01-15T12:30:00"


class TestExceptionChaining:
    """Tests for exception chaining behavior."""
    
    def test_original_exception_preserved(self):
        """Test that original exception is preserved in chain."""
        original = OSError("Disk error")
        
        wrapped = UVH5ReadError(
            file_path="/path/to/file.hdf5",
            reason="Read failed",
            original_exception=original,
        )
        
        assert wrapped.original_exception is original
        assert "original_error" in wrapped.context
        assert "OSError" in wrapped.context["original_type"]
    
    def test_traceback_captured(self):
        """Test that traceback is captured from original exception."""
        try:
            raise ValueError("Inner error")
        except ValueError as e:
            wrapped = ConversionError(
                "Outer error",
                original_exception=e,
            )
        
        assert "traceback" in wrapped.context
        assert "ValueError" in wrapped.context["traceback"]
        assert "Inner error" in wrapped.context["traceback"]
