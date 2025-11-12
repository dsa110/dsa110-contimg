"""
Service Manager

Unified service orchestration and health monitoring for all DSA-110 pipeline services.
"""

import asyncio
import os
import signal
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime

from dsa110.utils.logging import setup_logging, get_logger
from dsa110.utils.config_loader import load_pipeline_config
from dsa110.messaging.message_queue import MessageQueue, MessageType
from dsa110.utils.distributed_state import DistributedStateManager, initialize_distributed_state
from dsa110.utils.monitoring import HealthChecker, HealthStatus

from .hdf5_watcher import HDF5WatcherService
from .ms_processor import MSProcessorService
from .variability_analyzer import VariabilityAnalyzerService

logger = get_logger(__name__)


class ServiceManager:
    """Manages all pipeline services with unified orchestration."""

    def __init__(self, config_path: str, environment: str = "development"):
        self.config_path = config_path
        self.environment = environment
        self.config = None
        self.message_queue: Optional[MessageQueue] = None
        self.state_manager: Optional[DistributedStateManager] = None
        self.health_checker: Optional[HealthChecker] = None
        
        # Services
        self.services: Dict[str, Any] = {}
        self.running = False

    async def initialize(self):
        """Initialize the service manager and all services."""
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
            self.health_checker = HealthChecker("service_manager", self.config)
            await self.health_checker.initialize()

            # Initialize services
            self.services = {
                "hdf5_watcher": HDF5WatcherService(self.config_path, self.environment),
                "ms_processor": MSProcessorService(self.config_path, self.environment),
                "variability_analyzer": VariabilityAnalyzerService(self.config_path, self.environment)
            }

            logger.info("Service Manager initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Service Manager: {e}", exc_info=True)
            return False

    async def start_all_services(self):
        """Start all services."""
        if not await self.initialize():
            logger.error("Failed to initialize service manager. Cannot start services.")
            return False

        try:
            self.running = True
            
            # Set health status to healthy
            await self.health_checker.set_status(HealthStatus.HEALTHY)
            
            logger.info("Starting all pipeline services...")
            
            # Start all services
            service_tasks = []
            for service_name, service in self.services.items():
                logger.info(f"Starting {service_name}...")
                task = asyncio.create_task(service.start())
                service_tasks.append(task)
            
            # Start background management tasks
            management_tasks = [
                asyncio.create_task(self._health_monitoring_loop()),
                asyncio.create_task(self._service_management_loop()),
                asyncio.create_task(self._message_routing_loop())
            ]
            
            # Wait for all tasks
            all_tasks = service_tasks + management_tasks
            await asyncio.gather(*all_tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Error in Service Manager: {e}", exc_info=True)
            await self.stop_all_services()
            return False

    async def stop_all_services(self):
        """Stop all services."""
        logger.info("Stopping all pipeline services...")
        self.running = False
        
        try:
            # Set health status to stopping
            if self.health_checker:
                await self.health_checker.set_status(HealthStatus.STOPPING)
            
            # Stop all services
            for service_name, service in self.services.items():
                try:
                    logger.info(f"Stopping {service_name}...")
                    await service.stop()
                except Exception as e:
                    logger.error(f"Error stopping {service_name}: {e}")
            
            # Cleanup resources
            if self.message_queue:
                await self.message_queue.close()
            
            if self.state_manager:
                await self.state_manager.close()
            
            logger.info("All services stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping services: {e}", exc_info=True)

    async def start_service(self, service_name: str) -> bool:
        """Start a specific service."""
        if service_name not in self.services:
            logger.error(f"Unknown service: {service_name}")
            return False
        
        try:
            service = self.services[service_name]
            logger.info(f"Starting {service_name}...")
            await service.start()
            return True
        except Exception as e:
            logger.error(f"Error starting {service_name}: {e}")
            return False

    async def stop_service(self, service_name: str) -> bool:
        """Stop a specific service."""
        if service_name not in self.services:
            logger.error(f"Unknown service: {service_name}")
            return False
        
        try:
            service = self.services[service_name]
            logger.info(f"Stopping {service_name}...")
            await service.stop()
            return True
        except Exception as e:
            logger.error(f"Error stopping {service_name}: {e}")
            return False

    async def restart_service(self, service_name: str) -> bool:
        """Restart a specific service."""
        logger.info(f"Restarting {service_name}...")
        await self.stop_service(service_name)
        await asyncio.sleep(2)  # Brief pause
        return await self.start_service(service_name)

    async def get_service_status(self, service_name: str = None) -> Dict[str, Any]:
        """Get status of all services or a specific service."""
        if service_name:
            if service_name not in self.services:
                return {"error": f"Unknown service: {service_name}"}
            
            service = self.services[service_name]
            return {
                "service": service_name,
                "status": service.get_status(),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            status = {}
            for name, service in self.services.items():
                status[name] = {
                    "status": service.get_status(),
                    "timestamp": datetime.utcnow().isoformat()
                }
            return status

    async def _health_monitoring_loop(self):
        """Background health monitoring loop."""
        while self.running:
            try:
                if self.health_checker:
                    # Update health metrics
                    service_status = await self.get_service_status()
                    healthy_services = sum(1 for s in service_status.values() if s["status"].get("running", False))
                    total_services = len(service_status)
                    
                    await self.health_checker.update_metrics({
                        "total_services": total_services,
                        "healthy_services": healthy_services,
                        "service_health_ratio": healthy_services / total_services if total_services > 0 else 0,
                        "service_status": service_status
                    })
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(30)

    async def _service_management_loop(self):
        """Background service management loop."""
        while self.running:
            try:
                # Check service health and restart if needed
                for service_name, service in self.services.items():
                    try:
                        status = service.get_status()
                        if not status.get("running", False):
                            logger.warning(f"Service {service_name} is not running, attempting restart...")
                            await self.restart_service(service_name)
                    except Exception as e:
                        logger.error(f"Error checking service {service_name}: {e}")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in service management loop: {e}", exc_info=True)
                await asyncio.sleep(60)

    async def _message_routing_loop(self):
        """Background message routing loop."""
        while self.running:
            try:
                if self.message_queue:
                    # Process system messages
                    message = await self.message_queue.consume(MessageType.SYSTEM, timeout=1.0)
                    if message:
                        await self._handle_system_message(message)
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                logger.error(f"Error in message routing loop: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _handle_system_message(self, message: dict):
        """Handle system-level messages."""
        try:
            message_type = message.get("type")
            
            if message_type == "get_all_status":
                # Respond with status of all services
                status = await self.get_service_status()
                response = {
                    "type": "all_status_response",
                    "services": status,
                    "timestamp": datetime.utcnow().isoformat()
                }
                await self.message_queue.publish(MessageType.SYSTEM, response)
            
            elif message_type == "restart_service":
                # Restart a specific service
                service_name = message.get("service_name")
                if service_name:
                    success = await self.restart_service(service_name)
                    response = {
                        "type": "restart_response",
                        "service_name": service_name,
                        "success": success,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await self.message_queue.publish(MessageType.SYSTEM, response)
            
            elif message_type == "health_check":
                # Respond to health check requests
                if self.health_checker:
                    status = await self.health_checker.get_status()
                    response = {
                        "type": "health_response",
                        "service": "service_manager",
                        "status": status.value if status else "unknown",
                        "timestamp": message.get("timestamp")
                    }
                    await self.message_queue.publish(MessageType.SYSTEM, response)
            
            else:
                logger.debug(f"Unknown system message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling system message: {e}", exc_info=True)


async def main():
    """Main entry point for the Service Manager."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Service Manager for DSA-110 Pipeline")
    parser.add_argument("-c", "--config", required=True, help="Path to the pipeline YAML config file.")
    parser.add_argument("-e", "--environment", default="development", 
                       choices=["development", "production", "testing"],
                       help="Environment to run in.")
    parser.add_argument("--service", help="Start only a specific service (hdf5_watcher, ms_processor, variability_analyzer)")
    args = parser.parse_args()

    # Setup logging
    setup_logging(log_dir="logs", config_name="service_manager")
    
    # Create service manager
    manager = ServiceManager(args.config, args.environment)
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(manager.stop_all_services())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.service:
            # Start only specific service
            await manager.initialize()
            await manager.start_service(args.service)
        else:
            # Start all services
            await manager.start_all_services()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Service manager error: {e}", exc_info=True)
    finally:
        await manager.stop_all_services()


if __name__ == "__main__":
    asyncio.run(main())
