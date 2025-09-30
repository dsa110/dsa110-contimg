"""
HDF5 Event Handler

Handles filesystem events for HDF5 files and triggers processing
when complete sets are detected.
"""

import asyncio
import os
import glob
import fnmatch
from typing import Set, Dict, List, Optional
from datetime import datetime
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from core.utils.logging import get_logger
from core.messaging.message_queue import MessageQueue, MessageType
from core.utils.distributed_state import DistributedStateManager
from core.data_ingestion.ms_creation import process_hdf5_set

logger = get_logger(__name__)


class HDF5EventHandler(FileSystemEventHandler):
    """Handles filesystem events for HDF5 files with async processing."""

    def __init__(self, config: dict, message_queue: MessageQueue, state_manager: DistributedStateManager):
        super().__init__()
        self.config = config
        self.message_queue = message_queue
        self.state_manager = state_manager
        
        # Configuration
        self.expected_subbands = config['services']['hdf5_expected_subbands']
        self.spws_to_include = set(config['ms_creation']['spws'])
        self.incoming_path = Path(config['paths']['hdf5_incoming'])
        
        # Track processed timestamps to avoid reprocessing
        self.processed_timestamps: Set[str] = set()
        
        logger.info(f"HDF5 Event Handler initialized. Watching: {self.incoming_path}")
        logger.info(f"Expecting {self.expected_subbands} subbands matching SPWs: {self.spws_to_include}")

    def on_closed(self, event):
        """Called when a file is closed (good indicator that writing is done)."""
        if event.is_directory:
            return

        filepath = event.src_path
        filename = os.path.basename(filepath)

        # Basic check for expected filename pattern
        if fnmatch.fnmatch(filename, '20*T*.hdf5'):
            logger.debug(f"File closed event detected: {filename}")
            try:
                timestamp_str = filename.split('_')[0]
            except IndexError:
                logger.warning(f"Could not parse timestamp from filename: {filename}")
                return

            # Avoid reprocessing if already handled in this session
            if timestamp_str in self.processed_timestamps:
                logger.debug(f"Timestamp {timestamp_str} already processed in this session.")
                return

            # Schedule async check for completeness
            asyncio.create_task(self._check_set_completeness_async(timestamp_str))

    async def _check_set_completeness_async(self, timestamp_str: str):
        """Async wrapper for checking set completeness."""
        try:
            await self.check_set_completeness(timestamp_str)
        except Exception as e:
            logger.error(f"Error in async completeness check for {timestamp_str}: {e}", exc_info=True)

    async def check_set_completeness(self, timestamp_str: str):
        """Checks if all expected HDF5 files for a timestamp exist."""
        logger.debug(f"Checking completeness for timestamp: {timestamp_str}")
        
        # Use distributed state to check if already processing this timestamp
        state_key = f"hdf5_processing:{timestamp_str}"
        if await self.state_manager.has_key(state_key):
            logger.debug(f"Timestamp {timestamp_str} already being processed by another instance.")
            return

        # Set processing lock
        await self.state_manager.set(
            state_key, 
            {"status": "checking", "timestamp": timestamp_str},
            ttl=300  # 5 minute TTL
        )

        try:
            found_files = {}
            
            # List files matching the timestamp pattern
            pattern = str(self.incoming_path / f"{timestamp_str}_*.hdf5")
            current_files = glob.glob(pattern)

            for f_path in current_files:
                f_name = os.path.basename(f_path)
                try:
                    spw_str = f_name.split('_')[1].replace('.hdf5', '')
                    base_spw = spw_str.split('spl')[0]  # Get 'sbXX' part
                    if base_spw in self.spws_to_include:
                        found_files[base_spw] = f_path
                except IndexError:
                    continue  # Ignore files that don't match pattern

            # Check if the count matches the number of SPWs we care about
            if len(found_files) == len(self.spws_to_include):
                logger.info(f"Complete set found for timestamp {timestamp_str} with {len(found_files)} files.")
                
                # Sort files by SPW name/number for ms_creation module
                sorted_filepaths = [found_files[spw] for spw in sorted(list(self.spws_to_include))]

                # Update state to processing
                await self.state_manager.set(
                    state_key,
                    {"status": "processing", "timestamp": timestamp_str, "files": sorted_filepaths},
                    ttl=1800  # 30 minute TTL for processing
                )

                # Send message to processing queue
                message = {
                    "type": "hdf5_set_complete",
                    "timestamp": timestamp_str,
                    "files": sorted_filepaths,
                    "timestamp_utc": datetime.utcnow().isoformat()
                }
                
                await self.message_queue.publish(MessageType.HDF5_PROCESSING, message)
                logger.info(f"Published HDF5 processing message for {timestamp_str}")

            else:
                logger.debug(f"Set for {timestamp_str} is incomplete ({len(found_files)}/{len(self.spws_to_include)} required SPWs found).")
                # Remove the checking lock since we're not processing
                await self.state_manager.delete(state_key)

        except Exception as e:
            logger.error(f"Error during completeness check for {timestamp_str}: {e}", exc_info=True)
            # Remove the lock on error
            await self.state_manager.delete(state_key)

    async def process_hdf5_set_direct(self, timestamp_str: str, file_paths: List[str]) -> Optional[str]:
        """Directly process an HDF5 set (for testing or manual triggers)."""
        try:
            logger.info(f"Processing HDF5 set directly for {timestamp_str}")
            ms_path = process_hdf5_set(self.config, timestamp_str, file_paths)
            
            if ms_path:
                logger.info(f"Successfully processed HDF5 set for {timestamp_str}. MS: {ms_path}")
                self.processed_timestamps.add(timestamp_str)
                
                # Send completion message
                message = {
                    "type": "hdf5_processing_complete",
                    "timestamp": timestamp_str,
                    "ms_path": ms_path,
                    "timestamp_utc": datetime.utcnow().isoformat()
                }
                await self.message_queue.publish(MessageType.MS_CREATION, message)
                
                return ms_path
            else:
                logger.error(f"Processing failed for HDF5 set {timestamp_str}.")
                return None
                
        except Exception as e:
            logger.error(f"Exception during HDF5 set processing for {timestamp_str}: {e}", exc_info=True)
            return None

    def get_processing_stats(self) -> Dict:
        """Get current processing statistics."""
        return {
            "processed_timestamps": len(self.processed_timestamps),
            "expected_subbands": self.expected_subbands,
            "spws_to_include": list(self.spws_to_include),
            "incoming_path": str(self.incoming_path)
        }
