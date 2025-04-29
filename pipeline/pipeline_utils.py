# pipeline/pipeline_utils.py

import logging
import sys
import os
from datetime import datetime

# Define CASA log file path globally or pass via config if needed
# This might need refinement depending on how CASA logs are handled in CASA runtime
# For now, assume we might redirect CASA logs externally if running within CASA env
_CASA_LOG_FILE = None

def setup_logging(log_dir, config_name="pipeline"):
    """Sets up pipeline logging to file and console."""

    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_dir, f"{config_name}_{timestamp}.log")

    # Configure root logger
    log_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-5.5s] [%(threadName)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO) # Set default level (can be overridden)

    # File Handler
    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

    # --- CASA Log Handling ---
    # Option 1: Try setting CASA log file if casalog is available
    try:
        from casatasks import casalog
        global _CASA_LOG_FILE
        _CASA_LOG_FILE = os.path.join(log_dir, f"casa_{timestamp}.log")
        casalog.setlogfile(_CASA_LOG_FILE)
        root_logger.info(f"CASA log file set to: {_CASA_LOG_FILE}")
    except ImportError:
        root_logger.warning("casatasks not found. CASA logging not configured by pipeline.")
    except Exception as e:
        root_logger.error(f"Failed to set CASA log file: {e}")

    root_logger.info(f"Pipeline logging configured. Log file: {log_filename}")
    return root_logger

def get_logger(name):
    """Gets a logger instance for a specific module."""
    return logging.getLogger(name)

# --- Add other common utilities below ---
# E.g., functions for file path management, running external commands, etc.