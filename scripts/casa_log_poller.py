#!/usr/bin/env python3
"""
CASA Log File Poller

This script polls the root directory for new CASA log files and automatically
moves them to the casalogs directory. It's a simpler alternative to the file
watcher that doesn't require additional dependencies.
"""

import os
import time
import shutil
from pathlib import Path
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CASALogPoller:
    """CASA log file poller."""
    
    def __init__(self, project_root: str = None, poll_interval: float = 1.0):
        if project_root is None:
            project_root = Path(__file__).parent.parent
        else:
            project_root = Path(project_root)
        
        self.project_root = project_root
        self.casalogs_dir = project_root / "casalogs"
        self.poll_interval = poll_interval
        self.casalogs_dir.mkdir(exist_ok=True)
        
        # Track existing log files
        self.known_log_files = set()
        self._update_known_files()
        
        logger.info(f"CASA log poller initialized for: {self.project_root}")
        logger.info(f"CASA logs directory: {self.casalogs_dir}")
        logger.info(f"Poll interval: {poll_interval} seconds")
    
    def _update_known_files(self):
        """Update the set of known log files."""
        casa_log_files = list(self.project_root.glob("casa-*.log"))
        self.known_log_files = {f.name for f in casa_log_files}
    
    def _move_new_log_files(self):
        """Move any new CASA log files to casalogs directory."""
        casa_log_files = list(self.project_root.glob("casa-*.log"))
        new_files = [f for f in casa_log_files if f.name not in self.known_log_files]
        
        if not new_files:
            return 0
        
        logger.info(f"Found {len(new_files)} new CASA log files")
        
        moved_count = 0
        for log_file in new_files:
            try:
                # Wait a moment for the file to be fully written
                time.sleep(0.1)
                
                # Move the file
                destination = self.casalogs_dir / log_file.name
                shutil.move(str(log_file), str(destination))
                logger.info(f"Moved: {log_file.name} -> casalogs/")
                moved_count += 1
                
                # Update known files
                self.known_log_files.add(log_file.name)
                
            except Exception as e:
                logger.error(f"Failed to move {log_file.name}: {e}")
        
        return moved_count
    
    def poll_once(self):
        """Poll once for new log files."""
        self._update_known_files()
        return self._move_new_log_files()
    
    def run_daemon(self):
        """Run the poller as a daemon."""
        logger.info("CASA log poller running as daemon. Press Ctrl+C to stop.")
        
        try:
            while True:
                moved_count = self._move_new_log_files()
                if moved_count > 0:
                    logger.info(f"Moved {moved_count} CASA log files")
                
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            logger.info("CASA log poller stopped by user")
        except Exception as e:
            logger.error(f"CASA log poller error: {e}")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="CASA Log File Poller")
    parser.add_argument("--project-root", help="Project root directory")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--interval", type=float, default=1.0, help="Poll interval in seconds")
    
    args = parser.parse_args()
    
    poller = CASALogPoller(args.project_root, args.interval)
    
    if args.daemon:
        poller.run_daemon()
    else:
        moved_count = poller.poll_once()
        if moved_count == 0:
            print("No new CASA log files found to move")
        else:
            print(f"Moved {moved_count} CASA log files to casalogs directory")

if __name__ == "__main__":
    main()
