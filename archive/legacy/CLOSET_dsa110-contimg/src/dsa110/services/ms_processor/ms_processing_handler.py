"""
MS Processing Handler

Handles the processing of Measurement Sets using the new pipeline architecture.
"""

import asyncio
import os
import glob
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

from astropy.time import Time
from astropy.coordinates import SkyCoord
import astropy.units as u

from dsa110.utils.logging import get_logger
from dsa110.messaging.message_queue import MessageQueue, MessageType
from dsa110.utils.distributed_state import DistributedStateManager
from dsa110.pipeline.enhanced_orchestrator import EnhancedPipelineOrchestrator
from dsa110.telescope.dsa110 import DSA110_LOCATION

logger = get_logger(__name__)


class MSProcessingHandler:
    """Handles MS processing with distributed state management and error recovery."""

    def __init__(self, config: dict, message_queue: MessageQueue, state_manager: DistributedStateManager):
        self.config = config
        self.message_queue = message_queue
        self.state_manager = state_manager
        
        # Configuration
        self.ms_dir = Path(config['paths']['pipeline_base_dir']) / config['paths']['ms_stage1_dir']
        self.mosaic_duration = timedelta(minutes=config['services']['mosaic_duration_min'])
        self.mosaic_overlap = timedelta(minutes=config['services']['mosaic_overlap_min'])
        self.ms_chunk_duration = timedelta(minutes=config['services']['ms_chunk_duration_min'])
        self.num_ms_per_block = int(self.mosaic_duration / self.ms_chunk_duration)
        
        if self.num_ms_per_block <= 0:
            raise ValueError("Calculated number of MS per block is zero or negative.")

        logger.info(f"MS Processing Handler initialized")
        logger.info(f"MS directory: {self.ms_dir}")
        logger.info(f"Mosaic duration={self.mosaic_duration}, overlap={self.mosaic_overlap}, MS/block={self.num_ms_per_block}")

    async def check_for_mosaicable_block(self) -> bool:
        """Check if enough MS files exist for the next processing block."""
        try:
            # Check if already processing
            processing_key = "ms_processing:current_block"
            if await self.state_manager.has_key(processing_key):
                current_block = await self.state_manager.get(processing_key)
                logger.debug(f"Already processing block ending {current_block.get('end_mjd')}. Skipping check.")
                return False

            logger.debug("Checking for mosaicable block...")

            # Get last processed block time
            last_end_mjd = await self._get_last_processed_time()
            if last_end_mjd is None:
                # Find the earliest MS file to establish a starting point
                last_end_mjd = await self._find_initial_start_time()
                if last_end_mjd is None:
                    logger.debug("No MS files found yet.")
                    return False

            # Calculate time range for the next block
            last_end_time = Time(last_end_mjd, format='mjd', scale='utc')
            next_block_start_time = last_end_time - self.mosaic_overlap
            next_block_end_time = next_block_start_time + self.mosaic_duration
            next_block_end_mjd = next_block_end_time.mjd

            logger.info(f"Checking for MS files needed for block: {next_block_start_time.iso} to {next_block_end_time.iso}")

            # Find MS files within this time range
            required_ms_files = await self._find_ms_files_in_range(next_block_start_time, next_block_end_time)

            if len(required_ms_files) >= self.num_ms_per_block:
                # Found a complete block!
                block_ms_files = sorted(required_ms_files)[:self.num_ms_per_block]
                logger.info(f"Found {len(block_ms_files)} MS files - sufficient for block ending {next_block_end_time.iso}")

                # Set processing lock
                block_info = {
                    "start_time": next_block_start_time.iso,
                    "end_time": next_block_end_time.iso,
                    "start_mjd": next_block_start_time.mjd,
                    "end_mjd": next_block_end_mjd,
                    "ms_files": block_ms_files,
                    "status": "processing",
                    "created_at": datetime.utcnow().isoformat()
                }
                
                await self.state_manager.set(processing_key, block_info, ttl=3600)  # 1 hour TTL

                # Send processing message
                message = {
                    "type": "ms_block_ready",
                    "block_info": block_info,
                    "timestamp_utc": datetime.utcnow().isoformat()
                }
                
                await self.message_queue.publish(MessageType.MS_PROCESSING, message)
                logger.info(f"Published MS processing message for block ending {next_block_end_time.iso}")

                return True
            else:
                logger.debug(f"Block ending {next_block_end_time.iso} is incomplete ({len(required_ms_files)}/{self.num_ms_per_block} MS files found).")
                return False

        except Exception as e:
            logger.error(f"Error during MS block check: {e}", exc_info=True)
            return False

    async def process_block(self, block_info: Dict[str, Any]) -> bool:
        """Process a complete MS block using the enhanced orchestrator."""
        try:
            logger.info(f"Starting processing of block: {block_info['start_time']} to {block_info['end_time']}")
            
            # Initialize enhanced orchestrator
            orchestrator = EnhancedPipelineOrchestrator(self.config)
            await orchestrator.initialize_advanced_features()

            # Create processing block
            from dsa110.pipeline.orchestrator import ProcessingBlock
            processing_block = ProcessingBlock(
                block_id=f"block_{block_info['start_mjd']:.6f}",
                start_time=Time(block_info['start_mjd'], format='mjd', scale='utc'),
                end_time=Time(block_info['end_mjd'], format='mjd', scale='utc'),
                ms_files=block_info['ms_files']
            )

            # Process with error recovery
            result = await orchestrator.process_block_with_recovery(processing_block)
            
            if result.success:
                logger.info(f"Successfully processed block ending {block_info['end_time']}")
                
                # Update last processed time
                await self._update_last_processed_time(block_info['end_mjd'])
                
                # Send completion message
                message = {
                    "type": "ms_processing_complete",
                    "block_info": block_info,
                    "result": {
                        "success": result.success,
                        "processing_time": result.processing_time,
                        "outputs": result.outputs
                    },
                    "timestamp_utc": datetime.utcnow().isoformat()
                }
                await self.message_queue.publish(MessageType.MS_PROCESSING, message)
                
                return True
            else:
                logger.error(f"Failed to process block ending {block_info['end_time']}: {result.error}")
                
                # Send failure message
                message = {
                    "type": "ms_processing_failed",
                    "block_info": block_info,
                    "error": str(result.error),
                    "timestamp_utc": datetime.utcnow().isoformat()
                }
                await self.message_queue.publish(MessageType.MS_PROCESSING, message)
                
                return False

        except Exception as e:
            logger.error(f"Exception during block processing: {e}", exc_info=True)
            return False

    async def _get_last_processed_time(self) -> Optional[float]:
        """Get the MJD of the last successfully processed block."""
        try:
            last_time_key = "ms_processing:last_processed_time"
            last_time = await self.state_manager.get(last_time_key)
            return last_time.get('end_mjd') if last_time else None
        except Exception as e:
            logger.error(f"Error getting last processed time: {e}")
            return None

    async def _update_last_processed_time(self, end_mjd: float):
        """Update the MJD of the last successfully processed block."""
        try:
            last_time_key = "ms_processing:last_processed_time"
            last_time_info = {
                "end_mjd": end_mjd,
                "end_time": Time(end_mjd, format='mjd', scale='utc').iso,
                "updated_at": datetime.utcnow().isoformat()
            }
            await self.state_manager.set(last_time_key, last_time_info, ttl=86400)  # 24 hour TTL
        except Exception as e:
            logger.error(f"Error updating last processed time: {e}")

    async def _find_initial_start_time(self) -> Optional[float]:
        """Find the initial start time from the first MS file."""
        try:
            all_ms = sorted(glob.glob(str(self.ms_dir / "drift_*.ms")))
            if not all_ms:
                return None
            
            first_ms_name = os.path.basename(all_ms[0])
            # Assumes drift_YYYYMMDDTHHMMSS.ms format
            start_timestamp_str = first_ms_name.split('_')[1].replace('.ms', '')
            start_time = Time(datetime.strptime(start_timestamp_str, "%Y%m%dT%H%M%S"), format='datetime', scale='utc')
            
            # Set the 'last end time' such that the first block starts near the first MS
            last_end_time = start_time + self.mosaic_overlap
            logger.info(f"First MS found at {start_time.iso}. Setting initial 'last block end' to MJD {last_end_time.mjd:.6f}")
            
            return last_end_time.mjd

        except Exception as e:
            logger.error(f"Could not determine start time from MS files: {e}")
            return None

    async def _find_ms_files_in_range(self, start_time: Time, end_time: Time) -> List[str]:
        """Find MS files within the specified time range."""
        try:
            required_ms_files = []
            all_ms_files = glob.glob(str(self.ms_dir / "drift_*.ms"))
            
            for ms_path in all_ms_files:
                ms_name = os.path.basename(ms_path)
                try:
                    # Extract time from filename (assuming drift_YYYYMMDDTHHMMSS.ms)
                    ts_str = ms_name.split('_')[1].replace('.ms', '')
                    ms_time = Time(datetime.strptime(ts_str, "%Y%m%dT%H%M%S"), format='datetime', scale='utc')
                    
                    # Check if the MS start time is within the block range
                    if start_time <= ms_time < end_time:
                        required_ms_files.append(ms_path)
                        
                except (IndexError, ValueError) as e:
                    logger.warning(f"Could not parse timestamp from MS file {ms_name}: {e}")
                    continue

            logger.debug(f"Found {len(required_ms_files)} MS files in range.")
            return required_ms_files

        except Exception as e:
            logger.error(f"Error finding MS files in range: {e}")
            return []

    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics."""
        try:
            last_processed = await self._get_last_processed_time()
            current_block = await self.state_manager.get("ms_processing:current_block")
            
            return {
                "last_processed_mjd": last_processed,
                "last_processed_time": Time(last_processed, format='mjd', scale='utc').iso if last_processed else None,
                "currently_processing": current_block is not None,
                "current_block_info": current_block,
                "ms_directory": str(self.ms_dir),
                "mosaic_duration_minutes": self.mosaic_duration.total_seconds() / 60,
                "mosaic_overlap_minutes": self.mosaic_overlap.total_seconds() / 60,
                "ms_per_block": self.num_ms_per_block
            }
        except Exception as e:
            logger.error(f"Error getting processing stats: {e}")
            return {"error": str(e)}

    async def clear_processing_lock(self):
        """Clear the current processing lock (for recovery)."""
        try:
            await self.state_manager.delete("ms_processing:current_block")
            logger.info("Cleared processing lock")
        except Exception as e:
            logger.error(f"Error clearing processing lock: {e}")
