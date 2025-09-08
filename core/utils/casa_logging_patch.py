"""
CASA Logging Monkey Patch

This module patches CASA logging to force all log files to go to the casalogs directory.
It should be imported early in the pipeline to override any subsequent casalog.setlogfile() calls.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Store the original casalog module reference
_original_casalog = None
_casa_log_dir = None

def patch_casa_logging(casa_log_dir: str):
    """
    Patch CASA logging to force all log files to go to the specified directory.
    
    This function should be called early in the pipeline initialization,
    before any CASA modules are imported.
    
    Args:
        casa_log_dir: Directory to save CASA log files
    """
    global _casa_log_dir
    _casa_log_dir = casa_log_dir
    
    # Ensure the directory exists
    Path(casa_log_dir).mkdir(parents=True, exist_ok=True)
    
    # Set environment variable
    os.environ['CASA_LOG_DIR'] = str(Path(casa_log_dir).absolute())
    
    print(f"CASA logging patched to use directory: {casa_log_dir}")


def _patched_setlogfile(logfile_path: str):
    """
    Patched version of casalog.setlogfile that forces log files to casalogs directory.
    """
    global _casa_log_dir, _original_casalog
    
    if _casa_log_dir is None or _original_casalog is None:
        # If no directory is set or original function is not available, do nothing
        return
    
    # Extract the filename from the original path
    original_filename = Path(logfile_path).name
    
    # If it's already in the casalogs directory, use it as-is
    if str(_casa_log_dir) in str(logfile_path):
        return _original_casalog.setlogfile(logfile_path)
    
    # Generate a new log file path in the casalogs directory
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    
    # If the original filename follows the casa-{timestamp}.log pattern, keep it
    if original_filename.startswith('casa-') and original_filename.endswith('.log'):
        new_filename = original_filename
    else:
        # Generate a new filename
        new_filename = f"casa-{timestamp}.log"
    
    new_logfile_path = Path(_casa_log_dir) / new_filename
    
    print(f"CASA logging redirected: {logfile_path} -> {new_logfile_path}")
    
    # Call the original function with the new path
    return _original_casalog(str(new_logfile_path))


def apply_casa_logging_patch():
    """
    Apply the CASA logging patch.
    
    This function patches the casalog.setlogfile method to redirect all log files
    to the casalogs directory.
    """
    global _original_casalog
    
    try:
        # Import casalog
        from casatasks import casalog
        
        # Store the original function reference
        _original_casalog = casalog.setlogfile
        
        # Patch the setlogfile method
        casalog.setlogfile = _patched_setlogfile
        
        print("CASA logging patch applied successfully")
        return True
        
    except ImportError:
        print("casatasks not available. CASA logging patch not applied.")
        return False
    except Exception as e:
        print(f"Failed to apply CASA logging patch: {e}")
        return False


def remove_casa_logging_patch():
    """
    Remove the CASA logging patch and restore original behavior.
    """
    global _original_casalog
    
    if _original_casalog is not None:
        try:
            from casatasks import casalog
            casalog.setlogfile = _original_casalog.setlogfile
            print("CASA logging patch removed")
            return True
        except Exception as e:
            print(f"Failed to remove CASA logging patch: {e}")
            return False
    
    return False
