"""
CASA Import Hook

This module provides an import hook that sets up CASA logging before CASA is imported.
It should be imported before any CASA modules to ensure proper log file placement.
"""

import os
import sys
from pathlib import Path

# Set up CASA logging environment before any CASA imports
def setup_casa_logging_environment():
    """Set up CASA logging environment variables."""
    
    # Get project root (assuming this file is in core/utils/)
    project_root = Path(__file__).parent.parent.parent
    casalogs_dir = project_root / "casalogs"
    
    # Ensure casalogs directory exists
    casalogs_dir.mkdir(exist_ok=True)
    
    # Set CASA environment variables
    os.environ['CASA_LOG_DIR'] = str(casalogs_dir.absolute())
    os.environ['CASA_LOG_FILE'] = str(casalogs_dir / "casa.log")
    
    # Set CASA configuration directory
    casa_config_dir = project_root / ".casa"
    casa_config_dir.mkdir(exist_ok=True)
    
    # Create CASA configuration file
    casa_config_file = casa_config_dir / "rc"
    with open(casa_config_file, 'w') as f:
        f.write(f"# CASA configuration for DSA-110 pipeline\n")
        f.write(f"# Log directory: {casalogs_dir}\n")
        f.write(f"logfile = '{casalogs_dir}/casa.log'\n")
        f.write(f"logdir = '{casalogs_dir}'\n")
    
    return str(casalogs_dir)

# Set up the environment immediately when this module is imported
_casa_log_dir = setup_casa_logging_environment()

# Monkey patch the current working directory to be the casalogs directory
# This ensures CASA creates log files in the right place
_original_cwd = os.getcwd()
os.chdir(_casa_log_dir)

# Restore original working directory after a short delay
import threading
import time

def restore_cwd():
    """Restore the original working directory."""
    time.sleep(0.1)  # Give CASA time to create its log file
    os.chdir(_original_cwd)

# Start a thread to restore the working directory
restore_thread = threading.Thread(target=restore_cwd, daemon=True)
restore_thread.start()

print(f"CASA logging environment configured: {_casa_log_dir}")
