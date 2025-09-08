#!/usr/bin/env python3
"""
Production Pipeline Startup Script for DSA-110

This script starts the DSA-110 pipeline in production mode with
automated execution, monitoring, and error handling.
"""

import asyncio
import os
import sys
import signal
import logging
import argparse
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.automation.pipeline_automation import PipelineAutomation, AutomationConfig
from core.config.production_config import ProductionConfig, Environment
from core.utils.logging import get_logger
from core.utils.health_monitoring import health_monitor

logger = get_logger(__name__)


class ProductionPipelineManager:
    """
    Production pipeline manager for DSA-110.
    
    Manages the production pipeline with automated execution,
    monitoring, and error handling.
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the production pipeline manager.
        
        Args:
            config_path: Path to production configuration file
        """
        self.config_path = config_path
        self.production_config = None
        self.automation = None
        self.is_running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.is_running = False
    
    async def initialize(self):
        """Initialize the production pipeline."""
        try:
            # Load production configuration
            if self.config_path and os.path.exists(self.config_path):
                self.production_config = ProductionConfig.from_file(self.config_path)
            else:
                self.production_config = ProductionConfig()
            
            logger.info("Production configuration loaded")
            
            # Create automation configuration
            automation_config = self._create_automation_config()
            
            # Initialize automation system
            self.automation = PipelineAutomation(automation_config)
            
            # Setup job callbacks
            self._setup_job_callbacks()
            
            logger.info("Production pipeline initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize production pipeline: {e}")
            raise
    
    def _create_automation_config(self) -> AutomationConfig:
        """Create automation configuration from production config."""
        return AutomationConfig(
            schedule_type=self.production_config.pipeline.schedule_type,
            cron_expression=self.production_config.pipeline.cron_expression,
            interval_minutes=self.production_config.pipeline.interval_minutes,
            max_concurrent_jobs=self.production_config.pipeline.max_concurrent_jobs,
            job_timeout=self.production_config.pipeline.job_timeout,
            retry_failed_jobs=self.production_config.pipeline.retry_failed_jobs,
            max_retries=self.production_config.pipeline.max_retries,
            health_check_interval=self.production_config.monitoring.health_check_interval,
            alert_on_failure=self.production_config.monitoring.alert_on_failure,
            alert_email=self.production_config.monitoring.alert_email,
            auto_cleanup=self.production_config.data_management.auto_cleanup,
            cleanup_after_days=self.production_config.data_management.cleanup_after_days,
            archive_old_data=self.production_config.data_management.archive_old_data,
            archive_location=self.production_config.data_management.archive_location,
            memory_limit_gb=self.production_config.resources.memory_limit_gb,
            cpu_limit_percent=self.production_config.resources.cpu_limit_percent,
            disk_space_limit_gb=self.production_config.resources.disk_space_limit_gb
        )
    
    def _setup_job_callbacks(self):
        """Setup job callbacks for monitoring and alerting."""
        # Job started callback
        async def on_job_started(job_status):
            logger.info(f"Job {job_status.job_id} started - Stage: {job_status.current_stage}")
        
        # Job completed callback
        async def on_job_completed(job_status):
            logger.info(f"Job {job_status.job_id} completed successfully")
            logger.info(f"Output files: {job_status.output_files}")
        
        # Job failed callback
        async def on_job_failed(job_status):
            logger.error(f"Job {job_status.job_id} failed: {job_status.error_message}")
            
            # Send alert if configured
            if self.production_config.monitoring.alert_on_failure:
                await self._send_alert(f"Pipeline job {job_status.job_id} failed: {job_status.error_message}")
        
        # Job progress callback
        async def on_job_progress(job_status):
            logger.info(f"Job {job_status.job_id} progress: {job_status.progress:.1f}% - Stage: {job_status.current_stage}")
        
        # Register callbacks
        self.automation.add_job_callback('job_started', on_job_started)
        self.automation.add_job_callback('job_completed', on_job_completed)
        self.automation.add_job_callback('job_failed', on_job_failed)
        self.automation.add_job_callback('job_progress', on_job_progress)
    
    async def _send_alert(self, message: str):
        """Send alert notification."""
        try:
            # In a real implementation, this would send email, Slack, etc.
            logger.warning(f"ALERT: {message}")
            
            # For now, just log to a dedicated alert file
            alert_file = os.path.join(self.production_config.paths.log_dir, 'alerts.log')
            os.makedirs(os.path.dirname(alert_file), exist_ok=True)
            
            with open(alert_file, 'a') as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    async def start(self):
        """Start the production pipeline."""
        try:
            logger.info("Starting DSA-110 production pipeline...")
            
            # Initialize pipeline
            await self.initialize()
            
            # Start automation system
            await self.automation.start_automation()
            
            self.is_running = True
            logger.info("Production pipeline started successfully")
            
            # Main loop
            await self._main_loop()
            
        except Exception as e:
            logger.error(f"Failed to start production pipeline: {e}")
            raise
    
    async def stop(self):
        """Stop the production pipeline."""
        try:
            logger.info("Stopping DSA-110 production pipeline...")
            
            self.is_running = False
            
            # Stop automation system
            if self.automation:
                await self.automation.stop_automation()
            
            logger.info("Production pipeline stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping production pipeline: {e}")
    
    async def _main_loop(self):
        """Main production loop."""
        while self.is_running:
            try:
                # Check system health
                await self._check_system_health()
                
                # Generate status report
                await self._generate_status_report()
                
                # Wait before next iteration
                await asyncio.sleep(60)  # 1 minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(60)
    
    async def _check_system_health(self):
        """Check system health and performance."""
        try:
            # Check disk space
            disk_usage = psutil.disk_usage('/').percent
            if disk_usage > 90:
                logger.warning(f"High disk usage: {disk_usage:.1f}%")
                await self._send_alert(f"High disk usage: {disk_usage:.1f}%")
            
            # Check memory usage
            memory_usage = psutil.virtual_memory().percent
            if memory_usage > 90:
                logger.warning(f"High memory usage: {memory_usage:.1f}%")
                await self._send_alert(f"High memory usage: {memory_usage:.1f}%")
            
            # Check CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            if cpu_usage > 95:
                logger.warning(f"High CPU usage: {cpu_usage:.1f}%")
                await self._send_alert(f"High CPU usage: {cpu_usage:.1f}%")
            
            # Check job statistics
            if self.automation:
                stats = self.automation.get_job_statistics()
                if stats['failed_jobs'] > 0:
                    failure_rate = stats['failed_jobs'] / stats['total_jobs'] * 100
                    if failure_rate > 20:  # 20% failure rate
                        logger.warning(f"High job failure rate: {failure_rate:.1f}%")
                        await self._send_alert(f"High job failure rate: {failure_rate:.1f}%")
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    async def _generate_status_report(self):
        """Generate periodic status report."""
        try:
            if self.automation:
                # Generate automation report
                report = self.automation.generate_automation_report()
                
                # Save report
                report_path = os.path.join(
                    self.production_config.paths.log_dir,
                    f"status_report_{time.strftime('%Y%m%d_%H%M%S')}.md"
                )
                
                with open(report_path, 'w') as f:
                    f.write(report)
                
                logger.info(f"Status report saved to: {report_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate status report: {e}")
    
    async def run_manual_job(self):
        """Run a manual pipeline job."""
        try:
            logger.info("Running manual pipeline job...")
            
            if not self.automation:
                await self.initialize()
            
            # Trigger manual execution
            await self.automation._trigger_pipeline_execution()
            
            logger.info("Manual job triggered successfully")
            
        except Exception as e:
            logger.error(f"Failed to run manual job: {e}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        try:
            status = {
                'is_running': self.is_running,
                'automation_active': self.automation is not None,
                'production_config': self.production_config.to_dict() if self.production_config else None
            }
            
            if self.automation:
                status['job_statistics'] = self.automation.get_job_statistics()
                status['active_jobs'] = len(self.automation.active_jobs)
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {'error': str(e)}


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='DSA-110 Production Pipeline')
    parser.add_argument('--config', help='Path to production configuration file')
    parser.add_argument('--manual', action='store_true',
                       help='Run a single manual job and exit')
    parser.add_argument('--status', action='store_true',
                       help='Show pipeline status and exit')
    
    args = parser.parse_args()
    
    # Create pipeline manager
    manager = ProductionPipelineManager(args.config)
    
    try:
        if args.status:
            # Show status
            status = manager.get_status()
            print("Pipeline Status:")
            print(f"  Running: {status.get('is_running', False)}")
            print(f"  Automation Active: {status.get('automation_active', False)}")
            if 'job_statistics' in status:
                stats = status['job_statistics']
                print(f"  Total Jobs: {stats.get('total_jobs', 0)}")
                print(f"  Active Jobs: {stats.get('active_jobs', 0)}")
                print(f"  Success Rate: {stats.get('success_rate', 0):.1f}%")
            return
        
        elif args.manual:
            # Run manual job
            await manager.initialize()
            await manager.run_manual_job()
            await manager.stop()
        
        else:
            # Start production pipeline
            await manager.start()
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        await manager.stop()
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Import required modules
    import time
    import psutil
    
    asyncio.run(main())
