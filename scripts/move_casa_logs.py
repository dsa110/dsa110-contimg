#!/usr/bin/env python3
"""
Move CASA log files from root directory to casalogs directory.

This script can be run periodically or as a cron job to move any CASA log files
that are created in the root directory to the casalogs directory.
"""

import os
import shutil
from pathlib import Path
import glob

def move_casa_logs():
    """Move CASA log files from root to casalogs directory."""
    
    # Get project root
    project_root = Path(__file__).parent.parent
    casalogs_dir = project_root / "casalogs"
    
    # Ensure casalogs directory exists
    casalogs_dir.mkdir(exist_ok=True)
    
    # Find all CASA log files in root directory
    casa_log_pattern = project_root / "casa-*.log"
    casa_log_files = glob.glob(str(casa_log_pattern))
    
    if not casa_log_files:
        print("No CASA log files found in root directory")
        return
    
    print(f"Found {len(casa_log_files)} CASA log files in root directory")
    
    # Move each file
    moved_count = 0
    for log_file_path in casa_log_files:
        log_file = Path(log_file_path)
        destination = casalogs_dir / log_file.name
        
        try:
            # Move the file
            shutil.move(str(log_file), str(destination))
            print(f"Moved: {log_file.name} -> casalogs/")
            moved_count += 1
        except Exception as e:
            print(f"Failed to move {log_file.name}: {e}")
    
    print(f"Successfully moved {moved_count} CASA log files to casalogs directory")

if __name__ == "__main__":
    move_casa_logs()
