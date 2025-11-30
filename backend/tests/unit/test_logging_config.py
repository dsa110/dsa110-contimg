"""
Unit tests for the structured logging module.
"""

import json
import logging
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestContextVariables:
    """Tests for request context variables."""
    
    def test_get_request_id_default(self):
        """Should return None when not set."""
        from dsa110_contimg.api.logging_config import get_request_id
        
        # Clear any existing value
        from dsa110_contimg.api.logging_config import request_id_var
        request_id_var.set(None)
        
        assert get_request_id() is None
    
    def test_set_and_get_request_id(self):
        """Should set and retrieve request ID."""
        from dsa110_contimg.api.logging_config import (
            get_request_id, set_request_id, request_id_var
        )
        
        set_request_id("test-request-123")
        assert get_request_id() == "test-request-123"
        
        # Clean up
        request_id_var.set(None)
    
    def test_set_and_get_user_id(self):
        """Should set and retrieve user ID."""
        from dsa110_contimg.api.logging_config import (
            get_user_id, set_user_id, user_id_var
        )
        
        set_user_id("user-456")
        assert get_user_id() == "user-456"
        
        # Clean up
        user_id_var.set(None)


class TestJSONFormatter:
    """Tests for the JSON log formatter."""
    
    def test_format_basic_log(self):
        """Should format log as JSON with basic fields."""
        from dsa110_contimg.api.logging_config import JSONFormatter
        
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        log_obj = json.loads(output)
        
        assert log_obj["level"] == "INFO"
        assert log_obj["logger"] == "test.logger"
        assert log_obj["message"] == "Test message"
        assert "timestamp" in log_obj
    
    def test_format_includes_request_id(self):
        """Should include request ID when set."""
        from dsa110_contimg.api.logging_config import (
            JSONFormatter, set_request_id, request_id_var
        )
        
        set_request_id("req-abc123")
        
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        log_obj = json.loads(output)
        
        assert log_obj["request_id"] == "req-abc123"
        
        # Clean up
        request_id_var.set(None)
    
    def test_format_error_includes_location(self):
        """Should include location for error logs."""
        from dsa110_contimg.api.logging_config import JSONFormatter
        
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"
        
        output = formatter.format(record)
        log_obj = json.loads(output)
        
        assert "location" in log_obj
        assert log_obj["location"]["line"] == 42
    
    def test_format_extra_fields(self):
        """Should include extra fields."""
        from dsa110_contimg.api.logging_config import JSONFormatter
        
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.custom_field = "custom_value"
        
        output = formatter.format(record)
        log_obj = json.loads(output)
        
        assert "extra" in log_obj
        assert log_obj["extra"]["custom_field"] == "custom_value"
    
    def test_format_without_timestamp(self):
        """Should omit timestamp when disabled."""
        from dsa110_contimg.api.logging_config import JSONFormatter
        
        formatter = JSONFormatter(include_timestamp=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        log_obj = json.loads(output)
        
        assert "timestamp" not in log_obj


class TestColoredFormatter:
    """Tests for the colored console formatter."""
    
    def test_format_includes_level(self):
        """Should include log level."""
        from dsa110_contimg.api.logging_config import ColoredFormatter
        
        formatter = ColoredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        
        assert "INFO" in output
        assert "Test message" in output
    
    def test_format_includes_request_id(self):
        """Should include truncated request ID."""
        from dsa110_contimg.api.logging_config import (
            ColoredFormatter, set_request_id, request_id_var
        )
        
        set_request_id("12345678-full-request-id")
        
        formatter = ColoredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        
        assert "[12345678]" in output
        
        # Clean up
        request_id_var.set(None)


class TestConfigureLogging:
    """Tests for logging configuration."""
    
    def test_configure_with_json(self):
        """Should configure JSON formatter in production."""
        from dsa110_contimg.api.logging_config import configure_logging, JSONFormatter
        
        with patch.dict("os.environ", {"DSA110_LOG_JSON": "true"}):
            configure_logging(level="DEBUG", json_output=True)
        
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0
    
    def test_configure_with_color(self):
        """Should configure colored formatter in development."""
        from dsa110_contimg.api.logging_config import configure_logging
        
        with patch.dict("os.environ", {"DSA110_LOG_JSON": "false"}):
            configure_logging(level="DEBUG", json_output=False)
        
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0


class TestGetLogger:
    """Tests for get_logger function."""
    
    def test_returns_logger(self):
        """Should return a logger instance."""
        from dsa110_contimg.api.logging_config import get_logger
        
        logger = get_logger("test.module")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"


class TestAuditLogger:
    """Tests for the audit logger."""
    
    def test_log_auth_success(self):
        """Should log authentication success."""
        from dsa110_contimg.api.logging_config import AuditLogger
        
        audit = AuditLogger()
        
        with patch.object(audit.logger, "info") as mock_info:
            audit.log_auth_attempt(
                success=True,
                method="api_key",
                user="test_user",
            )
        
        mock_info.assert_called_once()
        call_args = mock_info.call_args
        assert "success" in call_args[0][0]
    
    def test_log_auth_failure(self):
        """Should log authentication failure."""
        from dsa110_contimg.api.logging_config import AuditLogger
        
        audit = AuditLogger()
        
        with patch.object(audit.logger, "info") as mock_info:
            audit.log_auth_attempt(
                success=False,
                method="jwt",
                reason="Invalid token",
            )
        
        mock_info.assert_called_once()
        call_args = mock_info.call_args
        assert "failure" in call_args[0][0]
    
    def test_log_access_granted(self):
        """Should log access granted."""
        from dsa110_contimg.api.logging_config import AuditLogger
        
        audit = AuditLogger()
        
        with patch.object(audit.logger, "log") as mock_log:
            audit.log_access(
                resource="images",
                action="read",
                granted=True,
            )
        
        mock_log.assert_called_once()
        assert mock_log.call_args[0][0] == logging.INFO
    
    def test_log_access_denied(self):
        """Should log access denied as warning."""
        from dsa110_contimg.api.logging_config import AuditLogger
        
        audit = AuditLogger()
        
        with patch.object(audit.logger, "log") as mock_log:
            audit.log_access(
                resource="admin",
                action="delete",
                granted=False,
            )
        
        mock_log.assert_called_once()
        assert mock_log.call_args[0][0] == logging.WARNING
    
    def test_log_data_change(self):
        """Should log data changes."""
        from dsa110_contimg.api.logging_config import AuditLogger
        
        audit = AuditLogger()
        
        with patch.object(audit.logger, "info") as mock_info:
            audit.log_data_change(
                entity="job",
                entity_id="123",
                action="rerun",
                user="admin",
            )
        
        mock_info.assert_called_once()
        call_args = mock_info.call_args
        assert "Data change" in call_args[0][0]


class TestPerformanceLogger:
    """Tests for the performance logger."""
    
    def test_log_timing(self):
        """Should log operation timing."""
        from dsa110_contimg.api.logging_config import PerformanceLogger
        
        perf = PerformanceLogger()
        
        with patch.object(perf.logger, "info") as mock_info:
            perf.log_timing(
                operation="database_query",
                duration_ms=150.5,
            )
        
        mock_info.assert_called_once()
        call_args = mock_info.call_args
        assert "150.50ms" in call_args[0][0]
    
    def test_log_slow_query_below_threshold(self):
        """Should not log queries below threshold."""
        from dsa110_contimg.api.logging_config import PerformanceLogger
        
        perf = PerformanceLogger()
        
        with patch.object(perf.logger, "warning") as mock_warning:
            perf.log_slow_query(
                query_type="SELECT",
                duration_ms=500,
                threshold_ms=1000,
            )
        
        mock_warning.assert_not_called()
    
    def test_log_slow_query_above_threshold(self):
        """Should log queries above threshold."""
        from dsa110_contimg.api.logging_config import PerformanceLogger
        
        perf = PerformanceLogger()
        
        with patch.object(perf.logger, "warning") as mock_warning:
            perf.log_slow_query(
                query_type="SELECT",
                duration_ms=2000,
                threshold_ms=1000,
            )
        
        mock_warning.assert_called_once()
        call_args = mock_warning.call_args
        assert "Slow query" in call_args[0][0]


class TestLogFunctionCallDecorator:
    """Tests for the log_function_call decorator."""
    
    def test_logs_sync_function(self):
        """Should log sync function entry/exit."""
        from dsa110_contimg.api.logging_config import log_function_call, get_logger
        
        logger = get_logger("test")
        
        @log_function_call(logger)
        def test_func(x):
            return x * 2
        
        with patch.object(logger, "debug") as mock_debug:
            result = test_func(5)
        
        assert result == 10
        assert mock_debug.call_count >= 2  # Entry and exit
    
    @pytest.mark.asyncio
    async def test_logs_async_function(self):
        """Should log async function entry/exit."""
        from dsa110_contimg.api.logging_config import log_function_call, get_logger
        
        logger = get_logger("test")
        
        @log_function_call(logger)
        async def test_async_func(x):
            return x * 2
        
        with patch.object(logger, "debug") as mock_debug:
            result = await test_async_func(5)
        
        assert result == 10
        assert mock_debug.call_count >= 2
    
    def test_logs_exception(self):
        """Should log exceptions."""
        from dsa110_contimg.api.logging_config import log_function_call, get_logger
        
        logger = get_logger("test")
        
        @log_function_call(logger)
        def failing_func():
            raise ValueError("Test error")
        
        with patch.object(logger, "debug"):
            with patch.object(logger, "error") as mock_error:
                with pytest.raises(ValueError):
                    failing_func()
        
        mock_error.assert_called_once()


class TestGlobalInstances:
    """Tests for global logger instances."""
    
    def test_audit_logger_exists(self):
        """Should have global audit logger."""
        from dsa110_contimg.api.logging_config import audit_logger, AuditLogger
        
        assert isinstance(audit_logger, AuditLogger)
    
    def test_perf_logger_exists(self):
        """Should have global performance logger."""
        from dsa110_contimg.api.logging_config import perf_logger, PerformanceLogger
        
        assert isinstance(perf_logger, PerformanceLogger)
