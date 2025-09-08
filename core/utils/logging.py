# core/utils/logging.py
"""
Enhanced logging utilities for DSA-110 pipeline.

This module provides structured logging capabilities with context-aware
logging and better integration with monitoring systems.
"""

import logging
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any
import json


def setup_logging(log_dir: str, config_name: str = "pipeline", 
                 log_level: int = logging.INFO) -> logging.Logger:
    """
    Set up structured logging for the pipeline.
    
    Args:
        log_dir: Directory to store log files
        config_name: Name for the log file
        log_level: Logging level
        
    Returns:
        Configured logger instance
    """
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_dir, f"{config_name}_{timestamp}.log")
    
    # Configure root logger
    log_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-5.5s] [%(threadName)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # File Handler
    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)
    
    root_logger.info(f"Pipeline logging configured. Log file: {log_filename}")
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class StructuredLogger:
    """
    Context-aware structured logger that adds metadata to log messages.
    """
    
    def __init__(self, name: str, context: Optional[Dict[str, Any]] = None):
        self.logger = logging.getLogger(name)
        self.context = context or {}
    
    def _format_message(self, message: str, extra_context: Optional[Dict[str, Any]] = None) -> str:
        """Format message with context."""
        context = {**self.context, **(extra_context or {})}
        if context:
            context_str = json.dumps(context, default=str)
            return f"{message} | Context: {context_str}"
        return message
    
    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self.logger.info(self._format_message(message, kwargs))
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self.logger.warning(self._format_message(message, kwargs))
    
    def error(self, message: str, **kwargs):
        """Log error message with context."""
        self.logger.error(self._format_message(message, kwargs))
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self.logger.debug(self._format_message(message, kwargs))
    
    def critical(self, message: str, **kwargs):
        """Log critical message with context."""
        self.logger.critical(self._format_message(message, kwargs))
    
    def with_context(self, **context) -> 'StructuredLogger':
        """Create a new logger with additional context."""
        new_context = {**self.context, **context}
        return StructuredLogger(self.logger.name, new_context)
