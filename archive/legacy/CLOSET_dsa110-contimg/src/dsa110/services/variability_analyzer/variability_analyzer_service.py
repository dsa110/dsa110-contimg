"""
Variability Analyzer Service

A modern, async service for analyzing variability in photometry data
using the new pipeline architecture.
"""

import asyncio
import os
import signal
import sys
from pathlib import Path
from typing import Optional

from dsa110.utils.logging import setup_logging, get_logger
from dsa110.utils.config_loader import load_pipeline_config
from dsa110.messaging.message_queue import MessageQueue, MessageType
from dsa110.utils.distributed_state import DistributedStateManager, initialize_distributed_state
from dsa110.utils.monitoring import HealthChecker, HealthStatus
from .variability_analysis_handler import VariabilityAnalysisHandler

logger = get_logger(__name__)


class VariabilityAnalyzerService:
    """Modern Variability Analyzer Service with async processing and distributed state."""

    def __init__(self, config_path: str, environment: str = "development"):
        self.config_path = config_path
        self.environment = environment
        self.config = None
        self.message_queue: Optional[MessageQueue] = None
        self.state_manager: Optional[DistributedStateManager] = None
        self.analysis_handler: Optional[VariabilityAnalysisHandler] = None
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
            self.health_checker = HealthChecker("variability_analyzer", self.config)
            await self.health_checker.initialize()

            # Initialize analysis handler
            self.analysis_handler = VariabilityAnalysisHandler(
                self.config,
                self.message_queue,
                self.state_manager
            )

            logger.info("Variability Analyzer Service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Variability Analyzer Service: {e}", exc_info=True)
            return False

    async def start(self):
        """Start the variability analyzer service."""
        if not await self.initialize():
            logger.error("Failed to initialize service. Cannot start.")
            return False

        try:
            self.running = True
            
            # Set health status to healthy
            await self.health_checker.set_status(HealthStatus.HEALTHY)
            
            logger.info("Variability Analyzer Service started successfully")
            
            # Start background tasks
            tasks = [
                asyncio.create_task(self._health_check_loop()),
                asyncio.create_task(self._message_processing_loop()),
                asyncio.create_task(self._periodic_analysis_loop())
            ]
            
            # Wait for all tasks
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Error in Variability Analyzer Service: {e}", exc_info=True)
            await self.stop()
            return False

    async def stop(self):
        """Stop the variability analyzer service."""
        logger.info("Stopping Variability Analyzer Service...")
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
            
            logger.info("Variability Analyzer Service stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping Variability Analyzer Service: {e}", exc_info=True)

    async def _health_check_loop(self):
        """Background health check loop."""
        while self.running:
            try:
                if self.health_checker and self.analysis_handler:
                    # Update health metrics
                    stats = await self.analysis_handler.get_analysis_stats()
                    await self.health_checker.update_metrics({
                        "last_analysis": stats.get("last_analysis", {}).get("timestamp", "never"),
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
                    # Process variability analysis messages
                    message = await self.message_queue.consume(MessageType.VARIABILITY_ANALYSIS, timeout=1.0)
                    if message:
                        await self._handle_message(message)
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                logger.error(f"Error in message processing loop: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _periodic_analysis_loop(self):
        """Periodic variability analysis loop."""
        while self.running:
            try:
                if self.analysis_handler:
                    # Run analysis
                    result = await self.analysis_handler.analyze_variability()
                    logger.debug(f"Periodic analysis result: {result['status']}")
                
                # Sleep for the analysis interval
                analysis_interval = self.config['services'].get('variability_analysis_interval_hours', 1)
                await asyncio.sleep(analysis_interval * 3600)  # Convert hours to seconds
                
            except Exception as e:
                logger.error(f"Error in periodic analysis loop: {e}", exc_info=True)
                await asyncio.sleep(3600)  # Sleep 1 hour on error

    async def _handle_message(self, message: dict):
        """Handle incoming messages."""
        try:
            message_type = message.get("type")
            
            if message_type == "run_analysis":
                # Run variability analysis on demand
                force = message.get("force", False)
                if self.analysis_handler:
                    logger.info(f"Running variability analysis (force={force})")
                    result = await self.analysis_handler.analyze_variability(force_analysis=force)
                    logger.info(f"Analysis result: {result['status']}")
            
            elif message_type == "get_summary":
                # Get variability summary
                if self.analysis_handler:
                    summary = await self.analysis_handler.get_variability_summary()
                    response = {
                        "type": "summary_response",
                        "service": "variability_analyzer",
                        "summary": summary,
                        "timestamp": message.get("timestamp")
                    }
                    await self.message_queue.publish(MessageType.SYSTEM, response)
            
            elif message_type == "health_check":
                # Respond to health check requests
                if self.health_checker:
                    status = await self.health_checker.get_status()
                    response = {
                        "type": "health_response",
                        "service": "variability_analyzer",
                        "status": status.value if status else "unknown",
                        "timestamp": message.get("timestamp")
                    }
                    await self.message_queue.publish(MessageType.SYSTEM, response)
            
            elif message_type == "get_stats":
                # Respond to stats requests
                stats = await self.analysis_handler.get_analysis_stats() if self.analysis_handler else {}
                response = {
                    "type": "stats_response",
                    "service": "variability_analyzer",
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
            "config_loaded": self.config is not None,
            "message_queue_connected": self.message_queue is not None,
            "state_manager_connected": self.state_manager is not None,
            "analysis_handler_initialized": self.analysis_handler is not None
        }


async def main():
    """Main entry point for the Variability Analyzer Service."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Variability Analyzer Service for DSA-110 Pipeline")
    parser.add_argument("-c", "--config", required=True, help="Path to the pipeline YAML config file.")
    parser.add_argument("-e", "--environment", default="development", 
                       choices=["development", "production", "testing"],
                       help="Environment to run in.")
    args = parser.parse_args()

    # Setup logging
    setup_logging(log_dir="logs", config_name="variability_analyzer")
    
    # Create and run service
    service = VariabilityAnalyzerService(args.config, args.environment)
    
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
