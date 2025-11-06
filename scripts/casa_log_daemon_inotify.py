#!/usr/bin/env python3
"""
CASA Log Daemon using inotifywait - Low CPU, recursive monitoring
Uses kernel-level inotify for efficient monitoring of all subdirectories
"""

import os
import sys
import time
import logging
import signal
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

class CasaLogHandler:
    """Handler for casa-*.log files"""
    
    def __init__(self, source_root, target_root):
        self.source_root = Path(source_root)
        self.target_root = Path(target_root)
        self.logger = logging.getLogger(__name__)
        
        # Ensure target directory exists
        self.target_root.mkdir(parents=True, exist_ok=True)
    
    def move_file(self, file_path):
        """Move a casa-*.log file to the target directory"""
        try:
            file_path = Path(file_path)
            
            # Calculate relative path from source root
            try:
                rel_path = file_path.relative_to(self.source_root)
            except ValueError:
                # File is not under source root, skip it
                self.logger.warning(f"File {file_path} is not under source root {self.source_root}")
                return
            
            # Skip files already in the target logs directory
            if str(rel_path).startswith('state/logs/'):
                return
            
            # Move all logs directly to target_root (which is already /state/logs/)
            target_path = self.target_root / file_path.name
            
            # Create target directory if it doesn't exist
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle filename collisions by appending timestamp if file exists
            if target_path.exists():
                timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
                stem = target_path.stem
                target_path = target_path.parent / f"{stem}_{timestamp}{target_path.suffix}"
            
            # Wait a moment to ensure file is fully written
            time.sleep(0.5)
            
            # Check if file still exists and is readable
            if not file_path.exists():
                self.logger.warning(f"File {file_path} no longer exists, skipping")
                return
                
            # Move the file
            shutil.move(str(file_path), str(target_path))
            self.logger.info(f"Successfully moved: {file_path} -> {target_path}")
            
        except Exception as e:
            self.logger.error(f"Error moving file {file_path}: {e}")

class CasaLogDaemonInotify:
    """Main daemon class using inotifywait for efficient recursive monitoring"""
    
    def __init__(self, source_root="/data/dsa110-contimg", target_root="/data/dsa110-contimg/state/logs"):
        self.source_root = Path(source_root)
        self.target_root = Path(target_root)
        self.process = None
        self.running = False
        
        # Setup logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Create handler
        self.handler = CasaLogHandler(self.source_root, self.target_root)
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = self.target_root
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
        """Start the daemon using inotifywait"""
        self.logger.info("Starting CASA Log Daemon (inotifywait)...")
        self.logger.info(f"Monitoring: {self.source_root} (recursive)")
        self.logger.info(f"Target: {self.target_root}")
        
        # Build inotifywait command
        # -m: monitor mode (continuous)
        # -r: recursive
        # -e create,moved_to: only watch for file creation and moves
        # --format: output format with directory and filename
        # --exclude: exclude state/logs directory to avoid watching our target
        cmd = [
            'inotifywait',
            '-m',
            '-r',
            '-e', 'create,moved_to',
            '--format', '%w%f',
            '--exclude', '^' + str(self.target_root),
            str(self.source_root)
        ]
        
        self.logger.info(f"Running: {' '.join(cmd)}")
        
        try:
            # Start inotifywait process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            self.running = True
            self.logger.info("Daemon started successfully")
            
            # Move any existing casa-*.log files first
            self.move_existing_files()
            
            # Process events from inotifywait
            for line in self.process.stdout:
                if not self.running:
                    break
                    
                line = line.strip()
                if not line:
                    continue
                
                file_path = Path(line)
                
                # Check if it's a casa-*.log file
                if file_path.name.startswith('casa-') and file_path.name.endswith('.log'):
                    self.logger.info(f"Detected casa log file: {file_path}")
                    self.handler.move_file(file_path)
        
        except FileNotFoundError:
            self.logger.error("inotifywait not found. Please install inotify-tools: apt-get install inotify-tools")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Error in inotifywait process: {e}")
        finally:
            self.stop()
    
    def move_existing_files(self):
        """Move any existing casa-*.log files that haven't been moved yet"""
        self.logger.info("Checking for existing casa-*.log files...")
        
        count = 0
        # Use find command for efficiency (native, fast)
        try:
            result = subprocess.run(
                ['find', str(self.source_root), '-type', 'f', '-name', 'casa-*.log'],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout for very large trees
            )
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                file_path = Path(line)
                
                # Skip files already in state/logs/
                try:
                    rel_path = file_path.relative_to(self.source_root)
                    if str(rel_path).startswith('state/logs/'):
                        continue
                except ValueError:
                    continue
                
                self.logger.info(f"Moving existing file: {file_path}")
                self.handler.move_file(file_path)
                count += 1
                
        except subprocess.TimeoutExpired:
            self.logger.warning("find command timed out, skipping existing file check")
        except Exception as e:
            self.logger.error(f"Error finding existing files: {e}")
        
        self.logger.info(f"Moved {count} existing casa-*.log files")
    
    def stop(self):
        """Stop the daemon"""
        self.running = False
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.logger.info("Daemon stopped")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CASA Log Daemon (inotifywait) - Monitor and move casa-*.log files')
    parser.add_argument('--source', default='/data/dsa110-contimg',
                       help='Source directory to monitor (default: /data/dsa110-contimg)')
    parser.add_argument('--target', default='/data/dsa110-contimg/state/logs',
                       help='Target directory for moved files (default: /data/dsa110-contimg/state/logs)')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as daemon (fork to background)')
    
    args = parser.parse_args()
    
    # Create daemon instance
    daemon = CasaLogDaemonInotify(args.source, args.target)
    
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

