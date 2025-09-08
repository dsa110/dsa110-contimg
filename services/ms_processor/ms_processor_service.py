"""
MS Processor Service

A modern, async service for processing Measurement Sets using the new
pipeline architecture with distributed state management.
"""

import asyncio
import os
import signal
import sys
from pathlib import Path
from typing import Optional

from core.utils.logging import setup_logging, get_logger
from core.utils.config_loader import load_pipeline_config
from core.messaging.message_queue import MessageQueue, MessageType
from core.utils.distributed_state import DistributedStateManager, initialize_distributed_state
from core.utils.monitoring import HealthChecker, HealthStatus
from .ms_processing_handler import MSProcessingHandler

logger = get_logger(__name__)


class MSProcessorService:
    """Modern MS Processor Service with async processing and distributed state."""

    def __init__(self, config_path: str, environment: str = "development"):
        self.config_path = config_path
        self.environment = environment
        self.config = None
        self.message_queue: Optional[MessageQueue] = None
        self.state_manager: Optional[DistributedStateManager] = None
        self.processing_handler: Optional[MSProcessingHandler] = None
        self.health_checker: Optional[HealthChecker] = None
        self.running = False

    async def initialize(self):
        """Initialize the service with all required components."""
        try:
            # Load configuration
            self.config = load_pipeline_config(environment=self.environment)
            logger.info(f"Loaded configuration for environment: {self.environment}")

            # Initialize distributed state
            await initialize_distributed_state(self.config)
            self.state_manager = DistributedStateManager(self.config)

            # Initialize message queue
            self.message_queue = MessageQueue(self.config)
            await self.message_queue.initialize()

            # Initialize health checker
            self.health_checker = HealthChecker("ms_processor", self.config)
            await self.health_checker.initialize()

            # Initialize processing handler
            self.processing_handler = MSProcessingHandler(
                self.config,
                self.message_queue,
                self.state_manager
            )

            logger.info("MS Processor Service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize MS Processor Service: {e}", exc_info=True)
            return False

    async def start(self):
        """Start the MS processor service."""
        if not await self.initialize():
            logger.error("Failed to initialize service. Cannot start.")
            return False

        try:
            self.running = True
            
            # Set health status to healthy
            await self.health_checker.set_status(HealthStatus.HEALTHY)
            
            logger.info("MS Processor Service started successfully")
            
            # Start background tasks
            tasks = [
                asyncio.create_task(self._health_check_loop()),
                asyncio.create_task(self._message_processing_loop()),
                asyncio.create_task(self._periodic_block_check_loop()),
                asyncio.create_task(self._cleanup_loop())
            ]
            
            # Wait for all tasks
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Error in MS Processor Service: {e}", exc_info=True)
            await self.stop()
            return False

    async def stop(self):
        """Stop the MS processor service."""
        logger.info("Stopping MS Processor Service...")
        self.running = False
        
        try:
            # Set health status to stopping
            if self.health_checker:
                await self.health_checker.set_status(HealthStatus.STOPPING)
            
            # Cleanup resources
            if self.message_queue:
                await self.message_queue.close()
            
            if self.state_manager:
                await self.state_manager.close()
            
            logger.info("MS Processor Service stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping MS Processor Service: {e}", exc_info=True)

    async def _health_check_loop(self):
        """Background health check loop."""
        while self.running:
            try:
                if self.health_checker and self.processing_handler:
                    # Update health metrics
                    stats = await self.processing_handler.get_processing_stats()
                    await self.health_checker.update_metrics({
                        "last_processed_mjd": stats.get("last_processed_mjd", 0),
                        "currently_processing": stats.get("currently_processing", False),
                        "service_status": "running" if self.running else "stopped"
                    })
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}", exc_info=True)
                await asyncio.sleep(30)

    async def _message_processing_loop(self):
        """Background message processing loop."""
        while self.running:
            try:
                if self.message_queue:
                    # Process MS processing messages
                    message = await self.message_queue.consume(MessageType.MS_PROCESSING, timeout=1.0)
                    if message:
                        await self._handle_message(message)
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                logger.error(f"Error in message processing loop: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _periodic_block_check_loop(self):
        """Periodic check for new MS blocks to process."""
        while self.running:
            try:
                if self.processing_handler:
                    # Check for new blocks every 2 minutes
                    await self.processing_handler.check_for_mosaicable_block()
                
                await asyncio.sleep(120)  # Check every 2 minutes
                
            except Exception as e:
                logger.error(f"Error in periodic block check loop: {e}", exc_info=True)
                await asyncio.sleep(120)

    async def _cleanup_loop(self):
        """Periodic cleanup of old state entries."""
        while self.running:
            try:
                if self.state_manager:
                    # Clean up old processing locks and state entries
                    # This is a simple implementation - in production, you'd want more sophisticated cleanup
                    pass
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)
                await asyncio.sleep(3600)

    async def _handle_message(self, message: dict):
        """Handle incoming messages."""
        try:
            message_type = message.get("type")
            
            if message_type == "ms_block_ready":
                # Process a new MS block
                block_info = message.get("block_info")
                if block_info and self.processing_handler:
                    logger.info(f"Processing MS block: {block_info['start_time']} to {block_info['end_time']}")
                    success = await self.processing_handler.process_block(block_info)
                    
                    if success:
                        logger.info(f"Successfully processed MS block ending {block_info['end_time']}")
                    else:
                        logger.error(f"Failed to process MS block ending {block_info['end_time']}")
            
            elif message_type == "health_check":
                # Respond to health check requests
                if self.health_checker:
                    status = await self.health_checker.get_status()
                    response = {
                        "type": "health_response",
                        "service": "ms_processor",
                        "status": status.value if status else "unknown",
                        "timestamp": message.get("timestamp")
                    }
                    await self.message_queue.publish(MessageType.SYSTEM, response)
            
            elif message_type == "get_stats":
                # Respond to stats requests
                stats = await self.processing_handler.get_processing_stats() if self.processing_handler else {}
                response = {
                    "type": "stats_response",
                    "service": "ms_processor",
                    "stats": stats,
                    "timestamp": message.get("timestamp")
                }
                await self.message_queue.publish(MessageType.SYSTEM, response)
            
            elif message_type == "clear_processing_lock":
                # Clear processing lock (for recovery)
                if self.processing_handler:
                    await self.processing_handler.clear_processing_lock()
                    logger.info("Processing lock cleared by request")
            
            else:
                logger.debug(f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    def get_status(self) -> dict:
        """Get current service status."""
        return {
            "running": self.running,
            "config_loaded": self.config is not None,
            "message_queue_connected": self.message_queue is not None,
            "state_manager_connected": self.state_manager is not None,
            "processing_handler_initialized": self.processing_handler is not None
        }


async def main():
    """Main entry point for the MS Processor Service."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MS Processor Service for DSA-110 Pipeline")
    parser.add_argument("-c", "--config", required=True, help="Path to the pipeline YAML config file.")
    parser.add_argument("-e", "--environment", default="development", 
                       choices=["development", "production", "testing"],
                       help="Environment to run in.")
    args = parser.parse_args()

    # Setup logging
    setup_logging(log_dir="logs", config_name="ms_processor")
    
    # Create and run service
    service = MSProcessorService(args.config, args.environment)
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(service.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Service error: {e}", exc_info=True)
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
