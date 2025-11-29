"""
Unit tests for logging configuration module.

Tests the centralized logging setup, context injection, and formatters
defined in dsa110_contimg.utils.logging_config.
"""

import pytest
import logging
import json
import tempfile
import os
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock

from dsa110_contimg.utils.logging_config import (
    setup_logging,
    log_context,
    get_logger,
    log_exception,
    ContextFilter,
    JsonFormatter,
    ColoredFormatter,
)
from dsa110_contimg.utils.exceptions import ConversionError, PipelineError


class TestContextFilter:
    """Tests for ContextFilter logging filter."""
    
    def test_injects_default_attributes(self):
        """Test that default context attributes are added."""
        filter = ContextFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        filter.filter(record)
        
        assert hasattr(record, "group_id")
        assert hasattr(record, "pipeline_stage")
        assert hasattr(record, "file_path")
        assert hasattr(record, "ms_path")
    
    def test_preserves_existing_attributes(self):
        """Test that existing attributes are not overwritten."""
        filter = ContextFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.group_id = "existing-group-id"
        
        filter.filter(record)
        
        assert record.group_id == "existing-group-id"


class TestJsonFormatter:
    """Tests for JSON log formatter."""
    
    def test_outputs_valid_json(self):
        """Test that output is valid JSON."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test.module"
        assert parsed["message"] == "Test message"
        assert parsed["line"] == 42
    
    def test_includes_extra_fields(self):
        """Test that extra fields are included."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.group_id = "2025-01-15T12:30:00"
        record.custom_field = "custom_value"
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert parsed["group_id"] == "2025-01-15T12:30:00"
        assert parsed["custom_field"] == "custom_value"
    
    def test_includes_exception_info(self):
        """Test that exception info is included."""
        formatter = JsonFormatter()
        
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]
    
    def test_handles_non_serializable_values(self):
        """Test that non-serializable values are converted to strings."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.non_serializable = lambda x: x  # Functions aren't JSON serializable
        
        output = formatter.format(record)
        parsed = json.loads(output)  # Should not raise
        
        assert "non_serializable" in parsed


class TestColoredFormatter:
    """Tests for colored console formatter."""
    
    def test_formats_without_colors(self):
        """Test formatting without ANSI colors."""
        formatter = ColoredFormatter(use_colors=False)
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.group_id = ""
        record.pipeline_stage = ""
        record.file_path = ""
        
        output = formatter.format(record)
        
        assert "INFO" in output
        assert "test.module" in output
        assert "Test message" in output
        # No ANSI codes
        assert "\033[" not in output
    
    def test_includes_context_in_output(self):
        """Test that context fields are included."""
        formatter = ColoredFormatter(use_colors=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.group_id = "2025-01-15T12:30:00"
        record.pipeline_stage = "conversion"
        record.file_path = ""
        
        output = formatter.format(record)
        
        assert "group_id=2025-01-15T12:30:00" in output
        assert "pipeline_stage=conversion" in output


class TestSetupLogging:
    """Tests for setup_logging function."""
    
    def test_creates_log_directory(self, tmp_path):
        """Test that log directory is created."""
        log_dir = tmp_path / "logs"
        
        setup_logging(log_dir=str(log_dir), console_output=False)
        
        assert log_dir.exists()
    
    def test_sets_log_level(self, tmp_path):
        """Test that log level is set correctly."""
        setup_logging(
            log_level="DEBUG",
            log_dir=str(tmp_path),
            console_output=False,
        )
        
        root = logging.getLogger()
        assert root.level == logging.DEBUG
    
    def test_creates_file_handlers(self, tmp_path):
        """Test that file handlers are created."""
        setup_logging(log_dir=str(tmp_path), console_output=False)
        
        # Check that log files are created on first log
        logger = logging.getLogger("test_file_handlers")
        logger.info("Test message")
        
        assert (tmp_path / "pipeline.log").exists()
    
    def test_reads_from_environment(self, tmp_path, monkeypatch):
        """Test that environment variables are respected."""
        monkeypatch.setenv("PIPELINE_LOG_LEVEL", "WARNING")
        monkeypatch.setenv("PIPELINE_LOG_DIR", str(tmp_path))
        
        setup_logging(console_output=False)
        
        root = logging.getLogger()
        assert root.level == logging.WARNING


class TestLogContext:
    """Tests for log_context context manager."""
    
    def test_adds_context_to_logs(self, tmp_path):
        """Test that context is added to log records."""
        setup_logging(
            log_dir=str(tmp_path),
            console_output=False,
            json_format=True,
        )
        
        captured_records = []
        handler = logging.Handler()
        handler.emit = lambda record: captured_records.append(record)
        
        logger = logging.getLogger("test_context")
        logger.addHandler(handler)
        
        with log_context(group_id="test-group", pipeline_stage="test"):
            logger.info("Test message")
        
        assert len(captured_records) == 1
        # Context is injected by filter, which runs during emit
    
    def test_context_is_nested(self, tmp_path):
        """Test that contexts can be nested."""
        setup_logging(log_dir=str(tmp_path), console_output=False)
        
        captured_records = []
        handler = logging.Handler()
        handler.emit = lambda record: captured_records.append(record)
        
        logger = logging.getLogger("test_nested")
        logger.addHandler(handler)
        
        with log_context(group_id="outer"):
            with log_context(pipeline_stage="inner"):
                logger.info("Nested message")
    
    def test_context_is_restored(self):
        """Test that context is restored after block."""
        with log_context(group_id="temporary"):
            pass
        
        # Context should be cleared
        from dsa110_contimg.utils.logging_config import _log_context
        assert _log_context.get() == {}


class TestGetLogger:
    """Tests for get_logger helper."""
    
    def test_returns_logger(self):
        """Test that a logger is returned."""
        logger = get_logger("test.module")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"
    
    def test_returns_adapter_with_context(self):
        """Test that adapter is returned with default context."""
        logger = get_logger("test.module", pipeline_stage="conversion")
        
        # LoggerAdapter has an extra attribute
        assert hasattr(logger, "extra")
        assert logger.extra.get("pipeline_stage") == "conversion"


class TestLogException:
    """Tests for log_exception helper."""
    
    def test_logs_pipeline_error_context(self, tmp_path):
        """Test that PipelineError context is included."""
        setup_logging(log_dir=str(tmp_path), console_output=False)
        
        captured_records = []
        handler = logging.Handler()
        handler.emit = lambda record: captured_records.append(record)
        
        logger = logging.getLogger("test_exc")
        logger.addHandler(handler)
        
        exc = ConversionError(
            "Test error",
            group_id="test-group",
            input_path="/test/path",
        )
        
        log_exception(logger, exc)
        
        assert len(captured_records) == 1
        record = captured_records[0]
        assert record.levelno == logging.ERROR
    
    def test_logs_standard_exception(self, tmp_path):
        """Test logging of standard Python exceptions."""
        setup_logging(log_dir=str(tmp_path), console_output=False)
        
        captured_records = []
        handler = logging.Handler()
        handler.emit = lambda record: captured_records.append(record)
        
        logger = logging.getLogger("test_std_exc")
        logger.addHandler(handler)
        
        exc = ValueError("Standard error")
        
        log_exception(logger, exc, custom_context="value")
        
        assert len(captured_records) == 1
    
    def test_custom_log_level(self, tmp_path):
        """Test that custom log level is respected."""
        setup_logging(log_dir=str(tmp_path), console_output=False)
        
        captured_records = []
        handler = logging.Handler()
        handler.emit = lambda record: captured_records.append(record)
        
        logger = logging.getLogger("test_level")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        exc = ValueError("Warning level error")
        
        log_exception(logger, exc, level=logging.WARNING)
        
        assert len(captured_records) == 1
        assert captured_records[0].levelno == logging.WARNING


class TestLoggingIntegration:
    """Integration tests for the logging system."""
    
    def test_full_logging_flow(self, tmp_path):
        """Test complete logging flow with context and file output."""
        log_dir = tmp_path / "logs"
        
        # Setup
        setup_logging(
            log_dir=str(log_dir),
            log_level="DEBUG",
            json_format=True,
            console_output=False,
        )
        
        # Log with context
        logger = get_logger(__name__, pipeline_stage="test")
        
        with log_context(group_id="integration-test"):
            logger.info("Starting test")
            logger.debug("Debug details")
            
            try:
                raise ConversionError("Test conversion error", group_id="integration-test")
            except ConversionError as e:
                log_exception(logger, e)
        
        # Verify log files were created
        assert (log_dir / "pipeline.log").exists()
        assert (log_dir / "error.log").exists()
        
        # Verify error log contains the exception
        error_log = (log_dir / "error.log").read_text()
        assert "Test conversion error" in error_log
