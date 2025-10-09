#!/usr/bin/env python3
"""
CASA Log Daemon - Continuously monitors for casa-*.log files and moves them to state directory
"""

import os
import sys
import time
import logging
import signal
import shutil
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime

class CasaLogHandler(FileSystemEventHandler):
    """Handler for file system events related to casa-*.log files"""
    
    def __init__(self, source_root, target_root):
        self.source_root = Path(source_root)
        self.target_root = Path(target_root)
        self.logger = logging.getLogger(__name__)
        
        # Ensure target directory exists
        self.target_root.mkdir(parents=True, exist_ok=True)
        
    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # Check if it's a casa-*.log file
        if file_path.name.startswith('casa-') and file_path.name.endswith('.log'):
            self.logger.info(f"Detected new casa log file: {file_path}")
            self.move_file(file_path)
    
    def on_moved(self, event):
        """Handle file move events (in case files are moved into the directory)"""
        if event.is_directory:
            return
            
        file_path = Path(event.dest_path)
        
        # Check if it's a casa-*.log file
        if file_path.name.startswith('casa-') and file_path.name.endswith('.log'):
            self.logger.info(f"Detected moved casa log file: {file_path}")
            self.move_file(file_path)
    
    def move_file(self, file_path):
        """Move a casa-*.log file to the target directory preserving structure"""
        try:
            # Calculate relative path from source root
            try:
                rel_path = file_path.relative_to(self.source_root)
            except ValueError:
                # File is not under source root, skip it
                self.logger.warning(f"File {file_path} is not under source root {self.source_root}")
                return
            
            # Skip files already in the target directory
            if str(rel_path).startswith('state/'):
                return
            
            # Create target path
            target_path = self.target_root / rel_path
            target_dir = target_path.parent
            
            # Create target directory if it doesn't exist
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Wait a moment to ensure file is fully written
            time.sleep(1)
            
            # Check if file still exists and is readable
            if not file_path.exists():
                self.logger.warning(f"File {file_path} no longer exists, skipping")
                return
                
            # Move the file
            shutil.move(str(file_path), str(target_path))
            self.logger.info(f"Successfully moved: {file_path} -> {target_path}")
            
        except Exception as e:
            self.logger.error(f"Error moving file {file_path}: {e}")

class CasaLogDaemon:
    """Main daemon class for monitoring casa-*.log files"""
    
    def __init__(self, source_root="/data/dsa110-contimg", target_root="/data/dsa110-contimg/state"):
        self.source_root = Path(source_root)
        self.target_root = Path(target_root)
        self.observer = None
        self.running = False
        
        # Setup logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = self.target_root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"casa_log_daemon_{datetime.now().strftime('%Y%m%d')}.log"
        
        # Clear any existing handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        
        # Configure root logger
        logging.basicConfig(
            level=logging.INFO,
            handlers=[file_handler, console_handler]
        )
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def start(self):
        """Start the daemon"""
        self.logger.info("Starting CASA Log Daemon...")
        self.logger.info(f"Monitoring: {self.source_root}")
        self.logger.info(f"Target: {self.target_root}")
        
        # Create event handler
        event_handler = CasaLogHandler(self.source_root, self.target_root)
        
        # Create observer
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.source_root), recursive=True)
        
        # Start observer
        self.observer.start()
        self.running = True
        
        self.logger.info("Daemon started successfully")
        
        # Move any existing casa-*.log files
        self.move_existing_files()
        
        # Keep running
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        finally:
            self.stop()
    
    def move_existing_files(self):
        """Move any existing casa-*.log files that haven't been moved yet"""
        self.logger.info("Checking for existing casa-*.log files...")
        
        count = 0
        for file_path in self.source_root.rglob("casa-*.log"):
            # Skip files in the target directory
            if str(file_path.relative_to(self.source_root)).startswith('state/'):
                continue
                
            self.logger.info(f"Moving existing file: {file_path}")
            CasaLogHandler(self.source_root, self.target_root).move_file(file_path)
            count += 1
        
        self.logger.info(f"Moved {count} existing casa-*.log files")
    
    def stop(self):
        """Stop the daemon"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
        self.running = False
        print("Daemon stopped")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CASA Log Daemon - Monitor and move casa-*.log files')
    parser.add_argument('--source', default='/data/dsa110-contimg',
                       help='Source directory to monitor (default: /data/dsa110-contimg)')
    parser.add_argument('--target', default='/data/dsa110-contimg/state',
                       help='Target directory for moved files (default: /data/dsa110-contimg/state)')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as daemon (fork to background)')
    
    args = parser.parse_args()
    
    # Create daemon instance
    daemon = CasaLogDaemon(args.source, args.target)
    
    if args.daemon:
        # Fork to background
        pid = os.fork()
        if pid > 0:
            # Parent process
            print(f"Daemon started with PID: {pid}")
            sys.exit(0)
        else:
            # Child process
            os.setsid()
            os.chdir('/')
            os.umask(0)
    
    # Start the daemon
    daemon.start()

if __name__ == "__main__":
    main()
