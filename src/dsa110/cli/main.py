#!/usr/bin/env python3
"""
DSA-110 Continuum Imaging Pipeline Main Entry Point
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dsa110.utils.health_monitoring import HealthMonitor
from dsa110.utils.monitoring_dashboard import MonitoringDashboard
from dsa110.pipeline.orchestrator import PipelineOrchestrator
from dsa110.config.production_config import ProductionConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main entry point for the DSA-110 pipeline."""
    try:
        logger.info("Starting DSA-110 Continuum Imaging Pipeline...")
        
        # Load configuration
        config = ProductionConfig()
        logger.info(f"Configuration loaded: {config.environment}")
        
        # Initialize health monitor
        health_monitor = HealthMonitor()
        logger.info("Health monitoring initialized")
        
        # Initialize monitoring dashboard
        dashboard = MonitoringDashboard()
        await dashboard.start_dashboard(open_browser=False)
        logger.info("Monitoring dashboard started")
        
        # Initialize pipeline orchestrator
        orchestrator = PipelineOrchestrator(config)
        logger.info("Pipeline orchestrator initialized")
        
        # Keep the service running
        logger.info("DSA-110 Pipeline is running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down DSA-110 Pipeline...")
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Cleanup
        try:
            logger.info("Cleaning up resources...")
        except:
            pass
        logger.info("DSA-110 Pipeline stopped")

if __name__ == "__main__":
    asyncio.run(main())
