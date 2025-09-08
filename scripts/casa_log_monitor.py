#!/usr/bin/env python3
"""
CASA Log Monitor

This script monitors for CASA log files in the root directory and moves them
to the casalogs directory. It can be run as a daemon or cron job.
"""

import os
import time
import shutil
from pathlib import Path
import glob
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CASALogMonitor:
    """Monitor and manage CASA log files."""
    
    def __init__(self, project_root: str = None):
        """Initialize the CASA log monitor."""
        if project_root is None:
            project_root = Path(__file__).parent.parent
        else:
            project_root = Path(project_root)
        
        self.project_root = project_root
        self.casalogs_dir = project_root / "casalogs"
        
        # Ensure casalogs directory exists
        self.casalogs_dir.mkdir(exist_ok=True)
        
        logger.info(f"CASA log monitor initialized for: {self.project_root}")
        logger.info(f"CASA logs directory: {self.casalogs_dir}")
    
    def move_casa_logs(self):
        """Move CASA log files from root to casalogs directory."""
        # Find all CASA log files in root directory
        casa_log_pattern = self.project_root / "casa-*.log"
        casa_log_files = glob.glob(str(casa_log_pattern))
        
        if not casa_log_files:
            return 0
        
        logger.info(f"Found {len(casa_log_files)} CASA log files in root directory")
        
        # Move each file
        moved_count = 0
        for log_file_path in casa_log_files:
            log_file = Path(log_file_path)
            destination = self.casalogs_dir / log_file.name
            
            try:
                # Move the file
                shutil.move(str(log_file), str(destination))
                logger.info(f"Moved: {log_file.name} -> casalogs/")
                moved_count += 1
            except Exception as e:
                logger.error(f"Failed to move {log_file.name}: {e}")
        
        if moved_count > 0:
            logger.info(f"Successfully moved {moved_count} CASA log files to casalogs directory")
        
        return moved_count
    
    def run_once(self):
        """Run the monitor once."""
        return self.move_casa_logs()
    
    def run_daemon(self, interval_seconds: int = 60):
        """Run the monitor as a daemon."""
        logger.info(f"Starting CASA log monitor daemon (interval: {interval_seconds}s)")
        
        try:
            while True:
                moved_count = self.move_casa_logs()
                if moved_count > 0:
                    logger.info(f"Moved {moved_count} CASA log files")
                
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("CASA log monitor daemon stopped")
        except Exception as e:
            logger.error(f"CASA log monitor daemon error: {e}")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="CASA Log Monitor")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--interval", type=int, default=60, help="Daemon interval in seconds")
    parser.add_argument("--project-root", help="Project root directory")
    
    args = parser.parse_args()
    
    monitor = CASALogMonitor(args.project_root)
    
    if args.daemon:
        monitor.run_daemon(args.interval)
    else:
        moved_count = monitor.run_once()
        if moved_count == 0:
            print("No CASA log files found to move")
        else:
            print(f"Moved {moved_count} CASA log files to casalogs directory")

if __name__ == "__main__":
    main()
