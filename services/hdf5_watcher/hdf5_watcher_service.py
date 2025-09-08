"""
HDF5 Watcher Service

A modern, async service for monitoring HDF5 file creation and triggering
MS conversion using the new pipeline architecture.
"""

import asyncio
import os
import signal
import sys
from pathlib import Path
from typing import Optional

from watchdog.observers import Observer

from core.utils.logging import setup_logging, get_logger
from core.utils.config_loader import load_pipeline_config
from core.messaging.message_queue import MessageQueue, MessageType
from core.utils.distributed_state import DistributedStateManager, initialize_distributed_state
from core.utils.monitoring import HealthChecker, HealthStatus
from .hdf5_event_handler import HDF5EventHandler

logger = get_logger(__name__)


class HDF5WatcherService:
    """Modern HDF5 Watcher Service with async processing and distributed state."""

    def __init__(self, config_path: str, environment: str = "development"):
        self.config_path = config_path
        self.environment = environment
        self.config = None
        self.message_queue: Optional[MessageQueue] = None
        self.state_manager: Optional[DistributedStateManager] = None
        self.event_handler: Optional[HDF5EventHandler] = None
        self.observer: Optional[Observer] = None
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
            self.health_checker = HealthChecker("hdf5_watcher", self.config)
            await self.health_checker.initialize()

            # Initialize event handler
            self.event_handler = HDF5EventHandler(
                self.config, 
                self.message_queue, 
                self.state_manager
            )

            # Initialize file system observer
            self.observer = Observer()
            watch_path = Path(self.config['paths']['hdf5_incoming'])
            
            if not watch_path.exists():
                logger.warning(f"Watch path does not exist: {watch_path}. Creating directory.")
                watch_path.mkdir(parents=True, exist_ok=True)

            self.observer.schedule(self.event_handler, str(watch_path), recursive=False)
            
            logger.info(f"HDF5 Watcher Service initialized successfully")
            logger.info(f"Watching directory: {watch_path}")
            
            return True

        except Exception as e:
            logger.error(f"Failed to initialize HDF5 Watcher Service: {e}", exc_info=True)
            return False

    async def start(self):
        """Start the HDF5 watcher service."""
        if not await self.initialize():
            logger.error("Failed to initialize service. Cannot start.")
            return False

        try:
            # Start observer
            self.observer.start()
            self.running = True
            
            # Set health status to healthy
            await self.health_checker.set_status(HealthStatus.HEALTHY)
            
            logger.info("HDF5 Watcher Service started successfully")
            
            # Start background tasks
            tasks = [
                asyncio.create_task(self._health_check_loop()),
                asyncio.create_task(self._message_processing_loop()),
                asyncio.create_task(self._periodic_cleanup_loop())
            ]
            
            # Wait for all tasks
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Error in HDF5 Watcher Service: {e}", exc_info=True)
            await self.stop()
            return False

    async def stop(self):
        """Stop the HDF5 watcher service."""
        logger.info("Stopping HDF5 Watcher Service...")
        self.running = False
        
        try:
            # Set health status to stopping
            if self.health_checker:
                await self.health_checker.set_status(HealthStatus.STOPPING)
            
            # Stop observer
            if self.observer:
                self.observer.stop()
                self.observer.join()
            
            # Cleanup resources
            if self.message_queue:
                await self.message_queue.close()
            
            if self.state_manager:
                await self.state_manager.close()
            
            logger.info("HDF5 Watcher Service stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping HDF5 Watcher Service: {e}", exc_info=True)

    async def _health_check_loop(self):
        """Background health check loop."""
        while self.running:
            try:
                if self.health_checker:
                    # Update health metrics
                    stats = self.event_handler.get_processing_stats() if self.event_handler else {}
                    await self.health_checker.update_metrics({
                        "processed_timestamps": stats.get("processed_timestamps", 0),
                        "expected_subbands": stats.get("expected_subbands", 0),
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
                    # Process any incoming messages
                    message = await self.message_queue.consume(MessageType.HDF5_WATCHER, timeout=1.0)
                    if message:
                        await self._handle_message(message)
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                logger.error(f"Error in message processing loop: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _periodic_cleanup_loop(self):
        """Periodic cleanup of old state entries."""
        while self.running:
            try:
                if self.state_manager:
                    # Clean up old processing locks (older than 1 hour)
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
            
            if message_type == "health_check":
                # Respond to health check requests
                if self.health_checker:
                    status = await self.health_checker.get_status()
                    response = {
                        "type": "health_response",
                        "service": "hdf5_watcher",
                        "status": status.value if status else "unknown",
                        "timestamp": message.get("timestamp")
                    }
                    await self.message_queue.publish(MessageType.SYSTEM, response)
            
            elif message_type == "get_stats":
                # Respond to stats requests
                stats = self.event_handler.get_processing_stats() if self.event_handler else {}
                response = {
                    "type": "stats_response",
                    "service": "hdf5_watcher",
                    "stats": stats,
                    "timestamp": message.get("timestamp")
                }
                await self.message_queue.publish(MessageType.SYSTEM, response)
            
            else:
                logger.debug(f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    def get_status(self) -> dict:
        """Get current service status."""
        return {
            "running": self.running,
            "observer_running": self.observer.is_alive() if self.observer else False,
            "config_loaded": self.config is not None,
            "message_queue_connected": self.message_queue is not None,
            "state_manager_connected": self.state_manager is not None
        }


async def main():
    """Main entry point for the HDF5 Watcher Service."""
    import argparse
    
    parser = argparse.ArgumentParser(description="HDF5 Watcher Service for DSA-110 Pipeline")
    parser.add_argument("-c", "--config", required=True, help="Path to the pipeline YAML config file.")
    parser.add_argument("-e", "--environment", default="development", 
                       choices=["development", "production", "testing"],
                       help="Environment to run in.")
    args = parser.parse_args()

    # Setup logging
    setup_logging(log_dir="logs", config_name="hdf5_watcher")
    
    # Create and run service
    service = HDF5WatcherService(args.config, args.environment)
    
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
