# pipeline/hdf5_watcher_service.py

import time
import os
import sys
import argparse
import json
from collections import defaultdict
from fnmatch import fnmatch
import yaml # Requires pip install pyyaml

# Watchdog imports
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Pipeline imports (assuming they are in the same parent directory)
try:
    from .pipeline_utils import setup_logging, get_logger
    from .ms_creation import find_hdf5_sets, process_hdf5_set
    # Import config parser logic if separate (assuming direct load for now)
except ImportError:
    # Allow running script directly for testing, adjust paths
    sys.path.append(os.path.dirname(__file__))
    from pipeline_utils import setup_logging, get_logger
    from ms_creation import find_hdf5_sets, process_hdf5_set

# Global logger setup later in main
logger = None
# Global config loaded later in main
config = None
# Track processed timestamps to avoid reprocessing in the same run
processed_timestamps = set()

class HDF5EventHandler(FileSystemEventHandler):
    """Handles filesystem events for HDF5 files."""

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.expected_subbands = self.config['services']['hdf5_expected_subbands']
        self.spws_to_include = set(self.config['ms_creation']['spws'])
        self.incoming_path = self.config['paths']['hdf5_incoming']
        logger.info(f"HDF5 Event Handler initialized. Watching: {self.incoming_path}")
        logger.info(f"Expecting {self.expected_subbands} subbands matching SPWs: {self.spws_to_include}")


    def on_closed(self, event):
        """Called when a file is closed (good indicator that writing is done)."""
        if event.is_directory:
            return

        filepath = event.src_path
        filename = os.path.basename(filepath)

        # Basic check for expected filename pattern
        if fnmatch(filename, '20*T*.hdf5'):
            logger.debug(f"File closed event detected: {filename}")
            try:
                timestamp_str = filename.split('_')[0]
            except IndexError:
                logger.warning(f"Could not parse timestamp from filename: {filename}")
                return

            # Avoid reprocessing if already handled in this session
            if timestamp_str in processed_timestamps:
                logger.debug(f"Timestamp {timestamp_str} already processed in this session.")
                return

            # Check if this timestamp now forms a complete set
            self.check_set_completeness(timestamp_str)

    def check_set_completeness(self, timestamp_str):
        """Checks if all expected HDF5 files for a timestamp exist."""
        logger.debug(f"Checking completeness for timestamp: {timestamp_str}")
        found_files = {}
        try:
            # List files matching the timestamp pattern
            pattern = os.path.join(self.incoming_path, f"{timestamp_str}_*.hdf5")
            current_files = glob.glob(pattern)

            for f_path in current_files:
                f_name = os.path.basename(f_path)
                try:
                    spw_str = f_name.split('_')[1].replace('.hdf5', '')
                    base_spw = spw_str.split('spl')[0] # Get 'sbXX' part
                    if base_spw in self.spws_to_include:
                         # Using base_spw as key assumes only one variant (e.g., spl or not) per base sb
                         found_files[base_spw] = f_path
                except IndexError:
                    continue # Ignore files that don't match pattern

            # Check if the count matches the *number* of SPWs we care about
            if len(found_files) == len(self.spws_to_include):
                logger.info(f"Complete set found for timestamp {timestamp_str} with {len(found_files)} files.")
                # Sort files by SPW name/number for ms_creation module
                sorted_filepaths = [found_files[spw] for spw in sorted(list(self.spws_to_include))]

                # Process the set
                try:
                    logger.info(f"Submitting HDF5 set for {timestamp_str} to be processed...")
                    # process_hdf5_set handles the actual conversion and file moving/deletion
                    ms_path = process_hdf5_set(self.config, timestamp_str, sorted_filepaths)
                    if ms_path:
                        logger.info(f"Successfully processed set for {timestamp_str}. MS: {ms_path}")
                        processed_timestamps.add(timestamp_str) # Mark as processed
                    else:
                        logger.error(f"Processing failed for HDF5 set {timestamp_str}.")
                        # Consider moving failed set to an error directory?
                except Exception as e:
                    logger.error(f"Exception during HDF5 set processing call for {timestamp_str}: {e}", exc_info=True)

            else:
                 logger.debug(f"Set for {timestamp_str} is incomplete ({len(found_files)}/{len(self.spws_to_include)} required SPWs found).")

        except Exception as e:
            logger.error(f"Error during completeness check for {timestamp_str}: {e}", exc_info=True)


def run_hdf5_watcher(config_path):
    """Main function to run the HDF5 watcher service."""
    global logger, config, processed_timestamps

    # --- Load Config ---
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        if config is None: raise ValueError("Config file is empty or invalid YAML.")
    except Exception as e:
        print(f"FATAL: Could not load/parse config file {config_path}: {e}")
        sys.exit(1)

    # --- Setup Logging ---
    log_dir = config['paths'].get('log_dir', '../logs')
    # Ensure log dir path is absolute or relative to script location if needed
    if not os.path.isabs(log_dir):
         log_dir = os.path.join(os.path.dirname(__file__), log_dir)
    logger = setup_logging(log_dir, config_name="hdf5_watcher")

    # --- Initialize Watcher ---
    watch_path = config['paths']['hdf5_incoming']
    if not os.path.isdir(watch_path):
        logger.error(f"Incoming HDF5 directory not found: {watch_path}. Exiting.")
        sys.exit(1)

    event_handler = HDF5EventHandler(config)
    observer = Observer()
    observer.schedule(event_handler, watch_path, recursive=False) # Don't watch subdirectories

    logger.info(f"Starting HDF5 watcher on directory: {watch_path}")
    observer.start()

    try:
        while True:
            # Keep the main thread alive. Add health checks or periodic tasks here if needed.
            time.sleep(config['services'].get('hdf5_watcher_poll_interval_sec', 60)) # Use poll interval for sleep
            logger.debug("Watcher alive...")
            # Optional: Periodically clear the processed_timestamps set? Or rely on restarts.
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, stopping watcher.")
    except Exception as e:
        logger.error(f"Watcher main loop encountered an error: {e}", exc_info=True)
    finally:
        logger.info("Stopping observer...")
        observer.stop()
        observer.join()
        logger.info("HDF5 watcher stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HDF5 Watcher Service for DSA-110 Pipeline")
    parser.add_argument("-c", "--config", required=True, help="Path to the pipeline YAML config file.")
    args = parser.parse_args()
    run_hdf5_watcher(args.config)