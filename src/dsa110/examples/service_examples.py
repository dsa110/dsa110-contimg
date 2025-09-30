#!/usr/bin/env python3
"""
Service Examples

Examples of how to use the DSA-110 pipeline services.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.utils.logging import setup_logging, get_logger
from services.hdf5_watcher import HDF5WatcherService
from services.ms_processor import MSProcessorService
from services.variability_analyzer import VariabilityAnalyzerService
from services.service_manager import ServiceManager

logger = get_logger(__name__)


async def example_hdf5_watcher():
    """Example of running the HDF5 Watcher Service."""
    print("=== HDF5 Watcher Service Example ===")
    
    config_path = "config/pipeline_config.yaml"
    service = HDF5WatcherService(config_path, environment="development")
    
    try:
        await service.initialize()
        print("HDF5 Watcher Service initialized successfully")
        
        # Run for a short time as an example
        print("Running HDF5 Watcher Service for 30 seconds...")
        await asyncio.wait_for(service.start(), timeout=30)
        
    except asyncio.TimeoutError:
        print("HDF5 Watcher Service example completed (timeout)")
    except Exception as e:
        print(f"Error in HDF5 Watcher Service example: {e}")
    finally:
        await service.stop()
        print("HDF5 Watcher Service stopped")


async def example_ms_processor():
    """Example of running the MS Processor Service."""
    print("=== MS Processor Service Example ===")
    
    config_path = "config/pipeline_config.yaml"
    service = MSProcessorService(config_path, environment="development")
    
    try:
        await service.initialize()
        print("MS Processor Service initialized successfully")
        
        # Run for a short time as an example
        print("Running MS Processor Service for 30 seconds...")
        await asyncio.wait_for(service.start(), timeout=30)
        
    except asyncio.TimeoutError:
        print("MS Processor Service example completed (timeout)")
    except Exception as e:
        print(f"Error in MS Processor Service example: {e}")
    finally:
        await service.stop()
        print("MS Processor Service stopped")


async def example_variability_analyzer():
    """Example of running the Variability Analyzer Service."""
    print("=== Variability Analyzer Service Example ===")
    
    config_path = "config/pipeline_config.yaml"
    service = VariabilityAnalyzerService(config_path, environment="development")
    
    try:
        await service.initialize()
        print("Variability Analyzer Service initialized successfully")
        
        # Run for a short time as an example
        print("Running Variability Analyzer Service for 30 seconds...")
        await asyncio.wait_for(service.start(), timeout=30)
        
    except asyncio.TimeoutError:
        print("Variability Analyzer Service example completed (timeout)")
    except Exception as e:
        print(f"Error in Variability Analyzer Service example: {e}")
    finally:
        await service.stop()
        print("Variability Analyzer Service stopped")


async def example_service_manager():
    """Example of running the Service Manager."""
    print("=== Service Manager Example ===")
    
    config_path = "config/pipeline_config.yaml"
    manager = ServiceManager(config_path, environment="development")
    
    try:
        await manager.initialize()
        print("Service Manager initialized successfully")
        
        # Start all services
        print("Starting all services...")
        await manager.start_all_services()
        
    except Exception as e:
        print(f"Error in Service Manager example: {e}")
    finally:
        await manager.stop_all_services()
        print("All services stopped")


async def example_individual_service():
    """Example of running a specific service."""
    print("=== Individual Service Example ===")
    
    config_path = "config/pipeline_config.yaml"
    manager = ServiceManager(config_path, environment="development")
    
    try:
        await manager.initialize()
        print("Service Manager initialized successfully")
        
        # Start only the HDF5 watcher
        print("Starting HDF5 Watcher Service...")
        success = await manager.start_service("hdf5_watcher")
        print(f"HDF5 Watcher Service started: {success}")
        
        # Get service status
        status = await manager.get_service_status("hdf5_watcher")
        print(f"Service status: {status}")
        
        # Wait a bit
        await asyncio.sleep(10)
        
        # Stop the service
        print("Stopping HDF5 Watcher Service...")
        success = await manager.stop_service("hdf5_watcher")
        print(f"HDF5 Watcher Service stopped: {success}")
        
    except Exception as e:
        print(f"Error in individual service example: {e}")
    finally:
        await manager.stop_all_services()
        print("All services stopped")


async def main():
    """Main function to run examples."""
    # Setup logging
    setup_logging(log_dir="logs", config_name="service_examples")
    
    print("DSA-110 Pipeline Service Examples")
    print("=" * 50)
    
    # Check if Redis is available
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("Redis connection successful")
    except Exception as e:
        print(f"Warning: Redis not available: {e}")
        print("Some examples may not work without Redis")
    
    print()
    
    # Run examples
    examples = [
        ("HDF5 Watcher Service", example_hdf5_watcher),
        ("MS Processor Service", example_ms_processor),
        ("Variability Analyzer Service", example_variability_analyzer),
        ("Service Manager", example_service_manager),
        ("Individual Service", example_individual_service)
    ]
    
    for name, example_func in examples:
        print(f"\nRunning {name} example...")
        try:
            await example_func()
        except Exception as e:
            print(f"Error running {name} example: {e}")
        print(f"{name} example completed")
        print("-" * 30)
    
    print("\nAll examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
