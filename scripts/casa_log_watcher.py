#!/usr/bin/env python3
"""
CASA Log File Watcher

This script watches the root directory for new CASA log files and automatically
moves them to the casalogs directory. It uses the watchdog library to monitor
file system events.
"""

import os
import time
import shutil
from pathlib import Path
import logging
from datetime import datetime

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("Warning: watchdog library not available. Install with: pip install watchdog")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CASALogHandler(FileSystemEventHandler):
    """Handler for CASA log file events."""
    
    def __init__(self, project_root: Path, casalogs_dir: Path):
        self.project_root = project_root
        self.casalogs_dir = casalogs_dir
        self.casalogs_dir.mkdir(exist_ok=True)
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Check if it's a CASA log file
        if file_path.name.startswith('casa-') and file_path.name.endswith('.log'):
            logger.info(f"New CASA log file detected: {file_path.name}")
            
            # Wait a moment for the file to be fully written
            time.sleep(0.5)
            
            # Move the file to casalogs directory
            try:
                destination = self.casalogs_dir / file_path.name
                shutil.move(str(file_path), str(destination))
                logger.info(f"Moved: {file_path.name} -> casalogs/")
            except Exception as e:
                logger.error(f"Failed to move {file_path.name}: {e}")

class CASALogWatcher:
    """CASA log file watcher."""
    
    def __init__(self, project_root: str = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent
        else:
            project_root = Path(project_root)
        
        self.project_root = project_root
        self.casalogs_dir = project_root / "casalogs"
        self.observer = None
        
        logger.info(f"CASA log watcher initialized for: {self.project_root}")
        logger.info(f"CASA logs directory: {self.casalogs_dir}")
    
    def start(self):
        """Start watching for CASA log files."""
        if not WATCHDOG_AVAILABLE:
            logger.error("watchdog library not available. Cannot start watcher.")
            return False
        
        try:
            # Create event handler
            event_handler = CASALogHandler(self.project_root, self.casalogs_dir)
            
            # Create observer
            self.observer = Observer()
            self.observer.schedule(event_handler, str(self.project_root), recursive=False)
            
            # Start observer
            self.observer.start()
            logger.info("CASA log watcher started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start CASA log watcher: {e}")
            return False
    
    def stop(self):
        """Stop watching for CASA log files."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("CASA log watcher stopped")
    
    def run_daemon(self):
        """Run the watcher as a daemon."""
        if not self.start():
            return
        
        try:
            logger.info("CASA log watcher running as daemon. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("CASA log watcher stopped by user")
        finally:
            self.stop()

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="CASA Log File Watcher")
    parser.add_argument("--project-root", help="Project root directory")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    
    args = parser.parse_args()
    
    watcher = CASALogWatcher(args.project_root)
    
    if args.daemon:
        watcher.run_daemon()
    else:
        if watcher.start():
            try:
                print("CASA log watcher started. Press Ctrl+C to stop.")
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("CASA log watcher stopped by user")
            finally:
                watcher.stop()
        else:
            print("Failed to start CASA log watcher")

if __name__ == "__main__":
    main()
