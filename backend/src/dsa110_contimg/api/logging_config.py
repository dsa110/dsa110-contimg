"""
Structured logging module for the DSA-110 API.

Provides JSON-formatted logging with correlation IDs for request tracing,
performance metrics, and consistent log formatting across the application.
"""

import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


# Context variables for request-scoped data
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


def get_request_id() -> Optional[str]:
    """Get the current request ID from context."""
    return request_id_var.get()


def get_user_id() -> Optional[str]:
    """Get the current user ID from context."""
    return user_id_var.get()


def set_request_id(request_id: str) -> None:
    """Set the request ID in context."""
    request_id_var.set(request_id)


def set_user_id(user_id: str) -> None:
    """Set the user ID in context."""
    user_id_var.set(user_id)


# ============================================================================
# JSON Formatter
# ============================================================================

class JSONFormatter(logging.Formatter):
    """
    Custom JSON log formatter for structured logging.
    
    Outputs logs as JSON objects with standardized fields:
    - timestamp: ISO 8601 format
    - level: Log level name
    - message: Log message
    - logger: Logger name
    - request_id: Correlation ID (if available)
    - user_id: User identifier (if available)
    - extra: Additional context data
    """
    
    # Fields to exclude from extra data
    RESERVED_FIELDS = {
        "name", "msg", "args", "created", "filename", "funcName",
        "levelname", "levelno", "lineno", "module", "msecs",
        "pathname", "process", "processName", "relativeCreated",
        "stack_info", "exc_info", "exc_text", "thread", "threadName",
        "message", "asctime",
    }
    
    def __init__(
        self,
        include_timestamp: bool = True,
        include_hostname: bool = False,
    ):
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_hostname = include_hostname
        self._hostname = None
        if include_hostname:
            import socket
            self._hostname = socket.gethostname()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Build base log object
        log_obj: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add timestamp
        if self.include_timestamp:
            log_obj["timestamp"] = datetime.utcfromtimestamp(
                record.created
            ).isoformat() + "Z"
        
        # Add hostname if configured
        if self.include_hostname and self._hostname:
            log_obj["hostname"] = self._hostname
        
        # Add request context
        request_id = get_request_id()
        if request_id:
            log_obj["request_id"] = request_id
        
        user_id = get_user_id()
        if user_id:
            log_obj["user_id"] = user_id
        
        # Add source location for errors
        if record.levelno >= logging.ERROR:
            log_obj["location"] = {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName,
            }
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        extra = {}
        for key, value in record.__dict__.items():
            if key not in self.RESERVED_FIELDS:
                try:
                    # Ensure value is JSON serializable
                    json.dumps(value)
                    extra[key] = value
                except (TypeError, ValueError):
                    extra[key] = str(value)
        
        if extra:
            log_obj["extra"] = extra
        
        return json.dumps(log_obj, default=str)


# ============================================================================
# Console Formatter (for development)
# ============================================================================

class ColoredFormatter(logging.Formatter):
    """
    Colored console formatter for development.
    """
    
    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        
        # Add request ID if available
        request_id = get_request_id()
        request_str = f"[{request_id[:8]}] " if request_id else ""
        
        message = f"{color}{record.levelname:8}{self.RESET} {request_str}{record.getMessage()}"
        
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)
        
        return message


# ============================================================================
# Logger Configuration
# ============================================================================

def configure_logging(
    level: str = "INFO",
    json_output: bool = True,
    include_hostname: bool = False,
) -> None:
    """
    Configure application logging.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: Use JSON format (True for production, False for dev)
        include_hostname: Include hostname in logs
    """
    # Get log level from environment or parameter
    log_level = os.getenv("DSA110_LOG_LEVEL", level).upper()
    use_json = os.getenv("DSA110_LOG_JSON", str(json_output)).lower() == "true"
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Choose formatter based on environment
    if use_json:
        handler.setFormatter(JSONFormatter(include_hostname=include_hostname))
    else:
        handler.setFormatter(ColoredFormatter())
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    root_logger.handlers = [handler]
    
    # Configure specific loggers
    for name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        logger = logging.getLogger(name)
        logger.handlers = [handler]
        logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.
    
    Returns a logger that will include request context when available.
    """
    return logging.getLogger(name)


# ============================================================================
# Logging Middleware
# ============================================================================

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request logging with correlation IDs.
    
    Features:
    - Generates unique request ID for each request
    - Logs request start/end with timing
    - Captures user ID from auth headers
    - Adds request ID to response headers
    """
    
    def __init__(self, app, logger_name: str = "dsa110.api"):
        super().__init__(app)
        self.logger = get_logger(logger_name)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract request ID
        request_id = (
            request.headers.get("X-Request-ID") or
            request.headers.get("X-Correlation-ID") or
            str(uuid.uuid4())
        )
        set_request_id(request_id)
        
        # Extract user ID if present
        if hasattr(request.state, "user_id"):
            set_user_id(request.state.user_id)
        
        # Log request start
        start_time = time.perf_counter()
        self.logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "client_ip": self._get_client_ip(request),
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Log request completion
            self.logger.info(
                f"Request completed: {request.method} {request.url.path} -> {response.status_code}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.logger.error(
                f"Request failed: {request.method} {request.url.path}",
                exc_info=True,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                }
            )
            raise
        finally:
            # Clear context
            set_request_id(None)
            user_id_var.set(None)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


# ============================================================================
# Logging Decorators
# ============================================================================

def log_function_call(logger: Optional[logging.Logger] = None):
    """
    Decorator to log function entry/exit with timing.
    
    Usage:
        @log_function_call()
        def my_function(arg1, arg2):
            ...
    """
    def decorator(func: Callable) -> Callable:
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            logger.debug(f"Entering {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.debug(
                    f"Exiting {func.__name__}",
                    extra={"duration_ms": round(duration_ms, 2)}
                )
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"Error in {func.__name__}: {e}",
                    exc_info=True,
                    extra={"duration_ms": round(duration_ms, 2)}
                )
                raise
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            logger.debug(f"Entering {func.__name__}")
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.debug(
                    f"Exiting {func.__name__}",
                    extra={"duration_ms": round(duration_ms, 2)}
                )
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"Error in {func.__name__}: {e}",
                    exc_info=True,
                    extra={"duration_ms": round(duration_ms, 2)}
                )
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator


# ============================================================================
# Audit Logging
# ============================================================================

class AuditLogger:
    """
    Specialized logger for audit events.
    
    Records security-relevant events like:
    - Authentication attempts
    - Authorization decisions
    - Data access
    - Configuration changes
    """
    
    def __init__(self, logger_name: str = "dsa110.audit"):
        self.logger = get_logger(logger_name)
    
    def log_auth_attempt(
        self,
        success: bool,
        method: str,
        user: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Log authentication attempt."""
        self.logger.info(
            f"Auth {'success' if success else 'failure'}: {method}",
            extra={
                "event_type": "auth_attempt",
                "success": success,
                "method": method,
                "user": user,
                "reason": reason,
            }
        )
    
    def log_access(
        self,
        resource: str,
        action: str,
        user: Optional[str] = None,
        granted: bool = True,
    ) -> None:
        """Log resource access."""
        level = logging.INFO if granted else logging.WARNING
        self.logger.log(
            level,
            f"Access {'granted' if granted else 'denied'}: {action} on {resource}",
            extra={
                "event_type": "access",
                "resource": resource,
                "action": action,
                "user": user,
                "granted": granted,
            }
        )
    
    def log_data_change(
        self,
        entity: str,
        entity_id: str,
        action: str,
        user: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        """Log data modification."""
        self.logger.info(
            f"Data change: {action} {entity}:{entity_id}",
            extra={
                "event_type": "data_change",
                "entity": entity,
                "entity_id": entity_id,
                "action": action,
                "user": user,
                "details": details or {},
            }
        )


# Global audit logger instance
audit_logger = AuditLogger()


# ============================================================================
# Performance Logging
# ============================================================================

class PerformanceLogger:
    """
    Logger for performance metrics.
    """
    
    def __init__(self, logger_name: str = "dsa110.performance"):
        self.logger = get_logger(logger_name)
    
    def log_timing(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        details: Optional[dict] = None,
    ) -> None:
        """Log operation timing."""
        self.logger.info(
            f"Timing: {operation} took {duration_ms:.2f}ms",
            extra={
                "event_type": "timing",
                "operation": operation,
                "duration_ms": duration_ms,
                "success": success,
                **(details or {}),
            }
        )
    
    def log_slow_query(
        self,
        query_type: str,
        duration_ms: float,
        threshold_ms: float = 1000,
        details: Optional[dict] = None,
    ) -> None:
        """Log slow database query."""
        if duration_ms >= threshold_ms:
            self.logger.warning(
                f"Slow query: {query_type} took {duration_ms:.2f}ms",
                extra={
                    "event_type": "slow_query",
                    "query_type": query_type,
                    "duration_ms": duration_ms,
                    "threshold_ms": threshold_ms,
                    **(details or {}),
                }
            )


# Global performance logger instance
perf_logger = PerformanceLogger()
