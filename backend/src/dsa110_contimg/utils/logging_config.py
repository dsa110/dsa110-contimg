"""
Centralized logging configuration for the DSA-110 Continuum Imaging Pipeline.

This module provides:
- Structured JSON logging for production environments
- Human-readable console logging for development
- Automatic log file rotation to /data/dsa110-contimg/state/logs/
- Context-aware logging with pipeline stage and group ID tracking

Usage:
    # Basic setup at application entry point
    from dsa110_contimg.utils.logging_config import setup_logging
    
    setup_logging()  # Uses defaults from environment
    
    # Or with explicit configuration
    setup_logging(
        log_level="DEBUG",
        log_dir="/custom/log/path",
        json_format=True,
    )
    
    # Module-level logger usage
    import logging
    logger = logging.getLogger(__name__)
    
    # Simple logging
    logger.info("Processing started")
    
    # Logging with extra context
    logger.error(
        "Conversion failed",
        extra={
            "group_id": "2025-01-15T12:30:00",
            "file_path": "/data/incoming/obs.hdf5",
            "pipeline_stage": "conversion",
        }
    )
    
    # Using context manager for automatic context injection
    from dsa110_contimg.utils.logging_config import log_context
    
    with log_context(group_id="2025-01-15T12:30:00", pipeline_stage="conversion"):
        logger.info("Starting conversion")  # Automatically includes context
        process_files()
        logger.info("Conversion complete")

Environment Variables:
    PIPELINE_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
    PIPELINE_LOG_DIR: Log directory path
    PIPELINE_LOG_FORMAT: Log format (json, text)
    PIPELINE_LOG_MAX_SIZE: Max log file size in MB
    PIPELINE_LOG_BACKUP_COUNT: Number of backup files to keep
"""

from __future__ import annotations

import os
import sys
import json
import logging
import logging.handlers
import threading
from pathlib import Path
from typing import Any, Optional, Generator
from datetime import datetime
from contextlib import contextmanager
from contextvars import ContextVar

# Context variables for automatic context injection
_log_context: ContextVar[dict[str, Any]] = ContextVar("log_context", default={})

# Default configuration
DEFAULT_LOG_DIR = "/data/dsa110-contimg/state/logs"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "text"
DEFAULT_MAX_SIZE_MB = 50
DEFAULT_BACKUP_COUNT = 10

# Log file names by category
LOG_FILES = {
    "main": "pipeline.log",
    "conversion": "conversion.log",
    "streaming": "streaming.log",
    "calibration": "calibration.log",
    "imaging": "imaging.log",
    "api": "api.log",
    "database": "database.log",
    "error": "error.log",  # All errors across all categories
}


class ContextFilter(logging.Filter):
    """
    Logging filter that injects context variables into log records.
    
    Adds context from the current context variable to every log record,
    enabling automatic context propagation through async/threaded code.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Get current context
        context = _log_context.get()
        
        # Add context attributes to record
        for key, value in context.items():
            if not hasattr(record, key):
                setattr(record, key, value)
        
        # Ensure standard context attributes exist
        for attr in ["group_id", "pipeline_stage", "file_path", "ms_path"]:
            if not hasattr(record, attr):
                setattr(record, attr, "")
        
        return True


class JsonFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.
    
    Outputs logs in JSON format suitable for log aggregation systems.
    Includes all extra context and exception information.
    """
    
    STANDARD_FIELDS = {
        "name", "msg", "args", "created", "filename", "funcName",
        "levelname", "levelno", "lineno", "module", "pathname",
        "process", "processName", "thread", "threadName",
        "exc_info", "exc_text", "stack_info", "message",
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # Build base log entry
        log_entry = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields (context)
        for key, value in record.__dict__.items():
            if key not in self.STANDARD_FIELDS and not key.startswith("_"):
                # Handle non-serializable values
                try:
                    json.dumps(value)
                    log_entry[key] = value
                except (TypeError, ValueError):
                    log_entry[key] = str(value)
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)


class ColoredFormatter(logging.Formatter):
    """
    Colored console formatter for human-readable output.
    
    Adds ANSI color codes based on log level and highlights context.
    """
    
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors and sys.stderr.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        # Build timestamp
        timestamp = datetime.utcfromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        
        # Get level with optional color
        level = record.levelname
        if self.use_colors:
            color = self.COLORS.get(level, "")
            level = f"{color}{level:8}{self.RESET}"
        else:
            level = f"{level:8}"
        
        # Build message
        message = record.getMessage()
        
        # Add context if present
        context_parts = []
        for attr in ["group_id", "pipeline_stage", "file_path"]:
            value = getattr(record, attr, "")
            if value:
                if self.use_colors:
                    context_parts.append(f"{self.DIM}{attr}={value}{self.RESET}")
                else:
                    context_parts.append(f"{attr}={value}")
        
        # Format output
        parts = [f"{timestamp} {level} [{record.name}] {message}"]
        if context_parts:
            parts.append(" | " + " ".join(context_parts))
        
        output = "".join(parts)
        
        # Add exception if present
        if record.exc_info:
            output += "\n" + self.formatException(record.exc_info)
        
        return output


def setup_logging(
    log_level: Optional[str] = None,
    log_dir: Optional[str] = None,
    json_format: Optional[bool] = None,
    max_size_mb: Optional[int] = None,
    backup_count: Optional[int] = None,
    console_output: bool = True,
) -> None:
    """
    Configure logging for the pipeline.
    
    Should be called once at application startup. Configures:
    - Root logger level
    - Console handler (colored text or JSON)
    - File handlers for each category
    - Error file handler (all errors)
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files
        json_format: Use JSON format for file logs
        max_size_mb: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        console_output: Enable console output
    """
    # Read from environment with fallbacks
    log_level = log_level or os.environ.get("PIPELINE_LOG_LEVEL", DEFAULT_LOG_LEVEL)
    log_dir = log_dir or os.environ.get("PIPELINE_LOG_DIR", DEFAULT_LOG_DIR)
    
    json_format_env = os.environ.get("PIPELINE_LOG_FORMAT", DEFAULT_LOG_FORMAT)
    if json_format is None:
        json_format = json_format_env.lower() == "json"
    
    max_size_mb = max_size_mb or int(
        os.environ.get("PIPELINE_LOG_MAX_SIZE", DEFAULT_MAX_SIZE_MB)
    )
    backup_count = backup_count or int(
        os.environ.get("PIPELINE_LOG_BACKUP_COUNT", DEFAULT_BACKUP_COUNT)
    )
    
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Add context filter to root
    context_filter = ContextFilter()
    root_logger.addFilter(context_filter)
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(ColoredFormatter(use_colors=True))
        root_logger.addHandler(console_handler)
    
    # File handlers
    file_formatter = JsonFormatter() if json_format else logging.Formatter(
        "%(asctime)s %(levelname)-8s [%(name)s] %(message)s "
        "[group_id=%(group_id)s] [stage=%(pipeline_stage)s]"
    )
    
    # Main log file
    main_handler = logging.handlers.RotatingFileHandler(
        log_path / LOG_FILES["main"],
        maxBytes=max_size_mb * 1024 * 1024,
        backupCount=backup_count,
    )
    main_handler.setLevel(logging.DEBUG)
    main_handler.setFormatter(file_formatter)
    root_logger.addHandler(main_handler)
    
    # Error log file (ERROR and above only)
    error_handler = logging.handlers.RotatingFileHandler(
        log_path / LOG_FILES["error"],
        maxBytes=max_size_mb * 1024 * 1024,
        backupCount=backup_count,
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)
    
    # Category-specific loggers
    _setup_category_loggers(log_path, file_formatter, max_size_mb, backup_count)
    
    # Log startup
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: level={log_level}, dir={log_dir}, json={json_format}"
    )


def _setup_category_loggers(
    log_path: Path,
    formatter: logging.Formatter,
    max_size_mb: int,
    backup_count: int,
) -> None:
    """Set up category-specific loggers with their own files."""
    
    # Mapping of logger name prefix to log file
    category_mapping = {
        "dsa110_contimg.conversion": "conversion",
        "dsa110_contimg.streaming": "streaming",
        "dsa110_contimg.calibration": "calibration",
        "dsa110_contimg.imaging": "imaging",
        "dsa110_contimg.api": "api",
        "dsa110_contimg.database": "database",
    }
    
    for logger_prefix, category in category_mapping.items():
        logger = logging.getLogger(logger_prefix)
        
        # Create rotating file handler for this category
        handler = logging.handlers.RotatingFileHandler(
            log_path / LOG_FILES[category],
            maxBytes=max_size_mb * 1024 * 1024,
            backupCount=backup_count,
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)


@contextmanager
def log_context(**context: Any) -> Generator[None, None, None]:
    """
    Context manager for adding context to all logs within a block.
    
    Automatically injects context into every log message within the block,
    even in called functions and async code.
    
    Args:
        **context: Key-value pairs to add to log records
    
    Example:
        with log_context(group_id="2025-01-15T12:30:00", pipeline_stage="conversion"):
            logger.info("Starting conversion")  # Includes group_id and pipeline_stage
            process_group(files)
            logger.info("Conversion complete")  # Same context
    """
    # Get current context and merge with new context
    current = _log_context.get()
    merged = {**current, **context}
    
    # Set new context
    token = _log_context.set(merged)
    
    try:
        yield
    finally:
        # Reset to previous context
        _log_context.reset(token)


def get_logger(name: str, **default_context: Any) -> logging.Logger:
    """
    Get a logger with optional default context.
    
    Convenience function for getting a configured logger.
    
    Args:
        name: Logger name (usually __name__)
        **default_context: Default context to include in every log
    
    Returns:
        Configured logger instance
    
    Example:
        logger = get_logger(__name__, pipeline_stage="conversion")
        logger.info("Message")  # Always includes pipeline_stage
    """
    logger = logging.getLogger(name)
    
    if default_context:
        # Create an adapter that includes default context
        class ContextAdapter(logging.LoggerAdapter):
            def process(self, msg, kwargs):
                extra = kwargs.get("extra", {})
                extra = {**self.extra, **extra}
                kwargs["extra"] = extra
                return msg, kwargs
        
        return ContextAdapter(logger, default_context)
    
    return logger


def log_exception(
    logger: logging.Logger,
    exc: BaseException,
    message: Optional[str] = None,
    level: int = logging.ERROR,
    **extra_context: Any,
) -> None:
    """
    Log an exception with full context.
    
    Convenience function for logging exceptions with consistent formatting.
    Automatically extracts context from PipelineError exceptions.
    
    Args:
        logger: Logger instance to use
        exc: Exception to log
        message: Optional message (defaults to str(exc))
        level: Log level (defaults to ERROR)
        **extra_context: Additional context to include
    
    Example:
        try:
            process_file(path)
        except ConversionError as e:
            log_exception(logger, e, file_path=path)
            raise
    """
    from dsa110_contimg.utils.exceptions import PipelineError
    
    # Reserved LogRecord attribute names that cannot be used in extra
    RESERVED_KEYS = {
        "name", "msg", "args", "created", "filename", "funcName",
        "levelname", "levelno", "lineno", "module", "pathname",
        "process", "processName", "thread", "threadName",
        "exc_info", "exc_text", "stack_info", "message",
    }
    
    # Build context from exception if it's a PipelineError
    if isinstance(exc, PipelineError):
        raw_context = {**exc.context, **extra_context}
    else:
        raw_context = {
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            **extra_context,
        }
    
    # Filter out reserved keys to avoid LogRecord conflicts
    context = {k: v for k, v in raw_context.items() if k not in RESERVED_KEYS}
    
    # Log with exception info
    logger.log(
        level,
        message or str(exc),
        exc_info=True,
        extra=context,
    )
