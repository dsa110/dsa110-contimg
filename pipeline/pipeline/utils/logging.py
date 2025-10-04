"""
Logging utilities for DSA-110 continuum imaging pipeline.

Simplified adapter for dsautils.dsa_syslog
"""

import logging
import sys


class DsaSyslogger:
    """
    Simplified logger for DSA-110 continuum imaging pipeline.
    
    This is a lightweight adapter that provides a compatible interface
    with dsautils.dsa_syslog.DsaSyslogger but uses standard Python logging.
    
    Parameters
    ----------
    proj_name : str
        Project name (default: 'dsa110-contimg')
    subsystem_name : str
        Subsystem name (default: 'conversion')
    log_level : int
        Logging level (default: logging.INFO)
    logger_name : str
        Logger name (default: __name__)
    log_stream : file-like, optional
        Output stream (default: sys.stdout)
    """
    
    def __init__(self,
                 proj_name='dsa110-contimg',
                 subsystem_name='conversion',
                 log_level=logging.INFO,
                 logger_name=__name__,
                 log_stream=None):
        
        self.proj_name = proj_name
        self.subsystem_name = subsystem_name
        self._log_level = log_level
        
        # Create logger
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(log_level)
        
        # Add handler if not already present
        if not self.logger.handlers:
            if log_stream is None:
                log_stream = sys.stdout
            
            handler = logging.StreamHandler(log_stream)
            handler.setLevel(log_level)
            
            # Create formatter
            formatter = logging.Formatter(
                f'%(asctime)s - {proj_name}/{subsystem_name} - '
                '%(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def subsystem(self, name):
        """Set the subsystem name."""
        self.subsystem_name = name
    
    def level(self, level):
        """Set the logging level."""
        self._log_level = level
        self.logger.setLevel(level)
    
    def debug(self, event):
        """Log a debug message."""
        self.logger.debug(event)
    
    def info(self, event):
        """Log an info message."""
        self.logger.info(event)
    
    def warning(self, event):
        """Log a warning message."""
        self.logger.warning(event)
    
    def error(self, event):
        """Log an error message."""
        self.logger.error(event)
    
    def critical(self, event):
        """Log a critical message."""
        self.logger.critical(event)


def exception_logger(logger, task, exception, throw):
    """
    Log an exception and optionally re-raise it.
    
    Parameters
    ----------
    logger : DsaSyslogger or logging.Logger
        Logger instance
    task : str
        Description of the task that failed
    exception : Exception
        The exception that occurred
    throw : bool
        Whether to re-raise the exception
    """
    error_msg = f"{task} failed with exception: {type(exception).__name__}: {str(exception)}"
    
    if hasattr(logger, 'error'):
        logger.error(error_msg)
    else:
        logging.error(error_msg)
    
    if throw:
        raise exception


def warning_logger(logger, message):
    """
    Log a warning message.
    
    Parameters
    ----------
    logger : DsaSyslogger or logging.Logger
        Logger instance
    message : str
        Warning message
    """
    if hasattr(logger, 'warning'):
        logger.warning(message)
    else:
        logging.warning(message)

