"""
CASA Logging Utilities for DSA-110 Pipeline

This module provides utilities for configuring CASA log files to be saved
in the designated casalogs directory.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def setup_casa_logging(casa_log_dir: str, log_prefix: str = "casa") -> Optional[str]:
    """
    Set up CASA logging to save log files in the specified directory.
    
    This function forces CASA to use the specified directory by:
    1. Setting the CASA log file explicitly
    2. Changing the current working directory temporarily if needed
    3. Ensuring the log file is created in the correct location
    
    Args:
        casa_log_dir: Directory to save CASA log files
        log_prefix: Prefix for log file names (default: "casa")
        
    Returns:
        Path to the CASA log file if successful, None if failed
    """
    try:
        # Ensure the CASA log directory exists
        casa_log_path = Path(casa_log_dir)
        casa_log_path.mkdir(parents=True, exist_ok=True)
        
        # Generate log file name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_filename = f"{log_prefix}-{timestamp}.log"
        log_file_path = casa_log_path / log_filename
        
        # Import CASA logging module
        try:
            from casatasks import casalog
            
            # Force CASA to use the specified log file
            # Use absolute path to ensure it goes to the right place
            absolute_log_path = str(log_file_path.absolute())
            casalog.setlogfile(absolute_log_path)
            
            # Also set the CASA log file environment variable as backup
            os.environ['CASA_LOG_FILE'] = absolute_log_path
            
            logger.info(f"CASA logging configured. Log file: {absolute_log_path}")
            return absolute_log_path
            
        except ImportError:
            logger.warning("casatasks not available. CASA logging not configured.")
            return None
            
    except Exception as e:
        logger.error(f"Failed to set up CASA logging: {e}")
        return None


def get_casa_log_directory(config: dict) -> str:
    """
    Get the CASA log directory from configuration.
    
    Args:
        config: Pipeline configuration dictionary
        
    Returns:
        Absolute path to CASA log directory
    """
    paths_config = config.get('paths', {})
    casa_log_dir = paths_config.get('casa_log_dir', 'casalogs')
    
    # If relative path, make it relative to project root
    if not os.path.isabs(casa_log_dir):
        # Assuming we're in the project root
        project_root = Path(__file__).parent.parent.parent
        casa_log_dir = project_root / casa_log_dir
    
    return str(casa_log_dir)


def ensure_casa_log_directory(config: dict) -> bool:
    """
    Ensure the CASA log directory exists.
    
    Args:
        config: Pipeline configuration dictionary
        
    Returns:
        True if directory exists or was created successfully, False otherwise
    """
    try:
        casa_log_dir = get_casa_log_directory(config)
        Path(casa_log_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"CASA log directory ensured: {casa_log_dir}")
        return True
    except Exception as e:
        logger.error(f"Failed to ensure CASA log directory: {e}")
        return False


def force_casa_logging_to_directory(casa_log_dir: str) -> bool:
    """
    Force CASA to use the specified directory for all log files.
    
    This function should be called early in the pipeline initialization
    to override any existing CASA logging configuration.
    
    Args:
        casa_log_dir: Directory to save CASA log files
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure the directory exists
        casa_log_path = Path(casa_log_dir)
        casa_log_path.mkdir(parents=True, exist_ok=True)
        
        # Set environment variable to force CASA to use this directory
        os.environ['CASA_LOG_DIR'] = str(casa_log_path.absolute())
        
        # Try to import and configure CASA logging
        try:
            from casatasks import casalog
            
            # Generate a default log file name
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            default_log_file = casa_log_path / f"casa-{timestamp}.log"
            
            # Set the CASA log file
            casalog.setlogfile(str(default_log_file.absolute()))
            
            logger.info(f"CASA logging forced to directory: {casa_log_path}")
            return True
            
        except ImportError:
            logger.warning("casatasks not available. CASA logging not configured.")
            return False
            
    except Exception as e:
        logger.error(f"Failed to force CASA logging to directory: {e}")
        return False
