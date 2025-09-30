#!/usr/bin/env python3
"""
Pipeline Automation System for DSA-110

This module provides automated execution, scheduling, and monitoring
of the DSA-110 continuum imaging pipeline.
"""

import asyncio
import os
import time
import logging
import json
import yaml
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import schedule
import psutil
from croniter import croniter

from dsa110.pipeline.stages.data_ingestion_stage import DataIngestionStage
from dsa110.pipeline.stages.calibration_stage import CalibrationStage
from dsa110.pipeline.stages.imaging_stage import ImagingStage
from dsa110.pipeline.stages.mosaicking_stage import MosaickingStage
from dsa110.pipeline.stages.photometry_stage import PhotometryStage
from dsa110.utils.error_recovery import error_recovery_manager
from dsa110.utils.health_monitoring import health_monitor
from dsa110.utils.logging import get_logger
from dsa110.config.production_config import ProductionConfig

logger = get_logger(__name__)


@dataclass
class AutomationConfig:
    """Configuration for pipeline automation."""
    # Scheduling
    schedule_type: str = "cron"  # "cron", "interval", "manual"
    cron_expression: str = "0 2 * * *"  # Daily at 2 AM
    interval_minutes: int = 60  # For interval scheduling
    
    # Execution
    max_concurrent_jobs: int = 2
    job_timeout: int = 3600  # 1 hour
    retry_failed_jobs: bool = True
    max_retries: int = 3
    
    # Monitoring
    health_check_interval: int = 300  # 5 minutes
    alert_on_failure: bool = True
    alert_email: str = ""
    
    # Data management
    auto_cleanup: bool = True
    cleanup_after_days: int = 7
    archive_old_data: bool = True
    archive_location: str = "/archive/dsa110"
    
    # Performance
    memory_limit_gb: float = 8.0
    cpu_limit_percent: float = 80.0
    disk_space_limit_gb: float = 100.0


@dataclass
class JobStatus:
    """Status of a pipeline job."""
    job_id: str
    status: str  # "pending", "running", "completed", "failed", "cancelled"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    progress: float = 0.0
    current_stage: str = ""
    error_message: str = ""
    output_files: List[str] = None
    
    def __post_init__(self):
        if self.output_files is None:
            self.output_files = []


class PipelineAutomation:
    """
    Automated pipeline execution and management system.
    
    Provides scheduling, monitoring, and automated execution
    of the DSA-110 continuum imaging pipeline.
    """
    
    def __init__(self, config: AutomationConfig = None, pipeline_config: Dict[str, Any] = None):
        """
        Initialize the pipeline automation system.
        
        Args:
            config: Automation configuration
            pipeline_config: Pipeline configuration
        """
        self.config = config or AutomationConfig()
        self.pipeline_config = pipeline_config or self._get_default_pipeline_config()
        
        # Initialize pipeline stages
        self.data_ingestion = DataIngestionStage(self.pipeline_config)
        self.calibration = CalibrationStage(self.pipeline_config)
        self.imaging = ImagingStage(self.pipeline_config)
        self.mosaicking = MosaickingStage(self.pipeline_config)
        self.photometry = PhotometryStage(self.pipeline_config)
        
        # Job management
        self.active_jobs: Dict[str, JobStatus] = {}
        self.job_history: List[JobStatus] = []
        self.job_queue: List[str] = []
        
        # Monitoring
        self.health_check_task = None
        self.scheduler_task = None
        self.is_running = False
        
        # Callbacks
        self.job_callbacks: Dict[str, List[Callable]] = {
            'job_started': [],
            'job_completed': [],
            'job_failed': [],
            'job_progress': []
        }
    
    def _get_default_pipeline_config(self) -> Dict[str, Any]:
        """Get default pipeline configuration."""
        return {
            'pipeline': {
                'name': 'DSA-110 Automated Pipeline',
                'version': '1.0.0',
                'environment': 'production'
            },
            'paths': {
                'data_dir': '/data/dsa110/raw',
                'output_dir': '/data/dsa110/processed',
                'log_dir': '/data/dsa110/logs'
            },
            'stages': {
                'data_ingestion': {'enabled': True, 'max_concurrent': 1},
                'calibration': {'enabled': True, 'max_concurrent': 1},
                'imaging': {'enabled': True, 'max_concurrent': 1},
                'mosaicking': {'enabled': True, 'max_concurrent': 1},
                'photometry': {'enabled': True, 'max_concurrent': 1}
            },
            'error_handling': {
                'max_retries': 3,
                'retry_delay': 5.0
            },
            'monitoring': {
                'enabled': True,
                'log_level': 'INFO'
            }
        }
    
    async def start_automation(self):
        """Start the automation system."""
        logger.info("Starting pipeline automation system")
        
        self.is_running = True
        
        # Start health monitoring
        self.health_check_task = asyncio.create_task(self._health_monitor_loop())
        
        # Start scheduler
        if self.config.schedule_type == "cron":
            self.scheduler_task = asyncio.create_task(self._cron_scheduler_loop())
        elif self.config.schedule_type == "interval":
            self.scheduler_task = asyncio.create_task(self._interval_scheduler_loop())
        
        logger.info("Pipeline automation system started")
    
    async def stop_automation(self):
        """Stop the automation system."""
        logger.info("Stopping pipeline automation system")
        
        self.is_running = False
        
        # Cancel tasks
        if self.health_check_task:
            self.health_check_task.cancel()
        if self.scheduler_task:
            self.scheduler_task.cancel()
        
        # Wait for active jobs to complete
        await self._wait_for_active_jobs()
        
        logger.info("Pipeline automation system stopped")
    
    async def _health_monitor_loop(self):
        """Health monitoring loop."""
        while self.is_running:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _cron_scheduler_loop(self):
        """Cron-based scheduler loop."""
        cron = croniter(self.config.cron_expression)
        
        while self.is_running:
            try:
                # Calculate next run time
                next_run = cron.get_next(datetime)
                now = datetime.now()
                
                # Wait until next run time
                wait_seconds = (next_run - now).total_seconds()
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)
                
                # Trigger pipeline execution
                if self.is_running:
                    await self._trigger_pipeline_execution()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cron scheduler error: {e}")
                await asyncio.sleep(60)
    
    async def _interval_scheduler_loop(self):
        """Interval-based scheduler loop."""
        while self.is_running:
            try:
                await self._trigger_pipeline_execution()
                await asyncio.sleep(self.config.interval_minutes * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Interval scheduler error: {e}")
                await asyncio.sleep(60)
    
    async def _trigger_pipeline_execution(self):
        """Trigger pipeline execution."""
        if len(self.active_jobs) >= self.config.max_concurrent_jobs:
            logger.warning("Maximum concurrent jobs reached, skipping execution")
            return
        
        # Create new job
        job_id = f"job_{int(time.time())}"
        job_status = JobStatus(job_id=job_id, status="pending")
        self.active_jobs[job_id] = job_status
        
        # Execute pipeline
        asyncio.create_task(self._execute_pipeline_job(job_status))
        
        logger.info(f"Triggered pipeline execution: {job_id}")
    
    async def _execute_pipeline_job(self, job_status: JobStatus):
        """Execute a pipeline job."""
        job_status.status = "running"
        job_status.start_time = datetime.now()
        
        try:
            # Notify job started
            await self._notify_job_callbacks('job_started', job_status)
            
            # Execute pipeline stages
            await self._run_pipeline_stages(job_status)
            
            # Mark as completed
            job_status.status = "completed"
            job_status.end_time = datetime.now()
            job_status.progress = 100.0
            
            # Notify job completed
            await self._notify_job_callbacks('job_completed', job_status)
            
            logger.info(f"Pipeline job {job_status.job_id} completed successfully")
            
        except Exception as e:
            # Mark as failed
            job_status.status = "failed"
            job_status.end_time = datetime.now()
            job_status.error_message = str(e)
            
            # Notify job failed
            await self._notify_job_callbacks('job_failed', job_status)
            
            logger.error(f"Pipeline job {job_status.job_id} failed: {e}")
            
            # Retry if configured
            if self.config.retry_failed_jobs and job_status.job_id not in [j.job_id for j in self.job_history if j.job_id == job_status.job_id]:
                retry_count = len([j for j in self.job_history if j.job_id == job_status.job_id])
                if retry_count < self.config.max_retries:
                    logger.info(f"Retrying job {job_status.job_id} (attempt {retry_count + 1})")
                    await asyncio.sleep(60)  # Wait before retry
                    asyncio.create_task(self._execute_pipeline_job(job_status))
                    return
        
        finally:
            # Move to history
            self.job_history.append(job_status)
            if job_status.job_id in self.active_jobs:
                del self.active_jobs[job_status.job_id]
    
    async def _run_pipeline_stages(self, job_status: JobStatus):
        """Run all pipeline stages."""
        try:
            # Stage 1: Data Ingestion
            job_status.current_stage = "data_ingestion"
            job_status.progress = 10.0
            await self._notify_job_callbacks('job_progress', job_status)
            
            ingestion_result = await self._run_data_ingestion()
            if not ingestion_result['success']:
                raise Exception(f"Data ingestion failed: {ingestion_result['error']}")
            
            ms_files = ingestion_result['ms_files']
            job_status.output_files.extend(ms_files)
            
            # Stage 2: Calibration
            job_status.current_stage = "calibration"
            job_status.progress = 30.0
            await self._notify_job_callbacks('job_progress', job_status)
            
            calibration_result = await self._run_calibration(ms_files)
            if not calibration_result['success']:
                raise Exception(f"Calibration failed: {calibration_result['error']}")
            
            bcal_table = calibration_result['bcal_table']
            gcal_table = calibration_result['gcal_table']
            job_status.output_files.extend([bcal_table, gcal_table])
            
            # Stage 3: Imaging
            job_status.current_stage = "imaging"
            job_status.progress = 50.0
            await self._notify_job_callbacks('job_progress', job_status)
            
            imaging_result = await self._run_imaging(ms_files, bcal_table, gcal_table)
            if not imaging_result['success']:
                raise Exception(f"Imaging failed: {imaging_result['error']}")
            
            image_files = imaging_result['image_files']
            job_status.output_files.extend(image_files)
            
            # Stage 4: Mosaicking
            job_status.current_stage = "mosaicking"
            job_status.progress = 70.0
            await self._notify_job_callbacks('job_progress', job_status)
            
            mosaicking_result = await self._run_mosaicking(image_files)
            if not mosaicking_result['success']:
                raise Exception(f"Mosaicking failed: {mosaicking_result['error']}")
            
            mosaic_file = mosaicking_result['mosaic_file']
            job_status.output_files.append(mosaic_file)
            
            # Stage 5: Photometry
            job_status.current_stage = "photometry"
            job_status.progress = 90.0
            await self._notify_job_callbacks('job_progress', job_status)
            
            photometry_result = await self._run_photometry(mosaic_file)
            if photometry_result['success']:
                job_status.output_files.append(photometry_result['photometry_file'])
            
            # Cleanup if configured
            if self.config.auto_cleanup:
                await self._cleanup_old_data()
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            raise
    
    async def _run_data_ingestion(self) -> Dict[str, Any]:
        """Run data ingestion stage."""
        try:
            # Find HDF5 files to process
            hdf5_files = self._find_hdf5_files()
            if not hdf5_files:
                return {'success': False, 'error': 'No HDF5 files found'}
            
            # Process files
            ms_files = []
            for hdf5_file in hdf5_files:
                result = await self.data_ingestion.process_timestamp(
                    timestamp=self._extract_timestamp_from_filename(hdf5_file),
                    hdf5_dir=os.path.dirname(hdf5_file)
                )
                if result:
                    ms_files.append(result)
            
            return {'success': True, 'ms_files': ms_files}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _run_calibration(self, ms_files: List[str]) -> Dict[str, Any]:
        """Run calibration stage."""
        try:
            # Create processing block
            block = self._create_processing_block(ms_files)
            
            # Setup calibration
            setup_result = await self.calibration.setup_calibration(block)
            if not setup_result['success']:
                return {'success': False, 'error': f"Calibration setup failed: {setup_result['error']}"}
            
            return {
                'success': True,
                'bcal_table': setup_result['bcal_table'],
                'gcal_table': setup_result['gcal_table']
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _run_imaging(self, ms_files: List[str], bcal_table: str, gcal_table: str) -> Dict[str, Any]:
        """Run imaging stage."""
        try:
            image_files = []
            
            for ms_file in ms_files:
                result = await self.imaging.process_ms(
                    ms_path=ms_file,
                    bcal_table=bcal_table,
                    gcal_table=gcal_table
                )
                
                if result['success']:
                    image_files.append(result['image_path'])
                else:
                    return {'success': False, 'error': f"Imaging failed for {ms_file}: {result['error']}"}
            
            return {'success': True, 'image_files': image_files}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _run_mosaicking(self, image_files: List[str]) -> Dict[str, Any]:
        """Run mosaicking stage."""
        try:
            # Create processing block
            block = self._create_processing_block(image_files)
            
            # Create primary beam files
            pb_files = [img.replace('.image', '.pb') for img in image_files]
            
            result = await self.mosaicking.create_mosaic(
                image_list=image_files,
                pb_list=pb_files,
                block=block
            )
            
            if not result['success']:
                return {'success': False, 'error': f"Mosaicking failed: {result['error']}"}
            
            return {'success': True, 'mosaic_file': result['image_path']}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _run_photometry(self, mosaic_file: str) -> Dict[str, Any]:
        """Run photometry stage."""
        try:
            mosaic_time = datetime.now()
            
            result = await self.photometry.process_mosaic(
                mosaic_fits_path=mosaic_file,
                mosaic_time=mosaic_time
            )
            
            if not result['success']:
                return {'success': False, 'error': f"Photometry failed: {result['error']}"}
            
            return {'success': True, 'photometry_file': f"{mosaic_file}.photometry"}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _find_hdf5_files(self) -> List[str]:
        """Find HDF5 files to process."""
        data_dir = self.pipeline_config['paths']['data_dir']
        hdf5_files = []
        
        if os.path.exists(data_dir):
            for root, dirs, files in os.walk(data_dir):
                for file in files:
                    if file.endswith('.h5') or file.endswith('.hdf5'):
                        hdf5_files.append(os.path.join(root, file))
        
        return hdf5_files
    
    def _extract_timestamp_from_filename(self, filename: str) -> str:
        """Extract timestamp from filename."""
        # Simplified implementation
        # In practice, this would parse the actual timestamp from the filename
        return datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    
    def _create_processing_block(self, files: List[str]) -> Any:
        """Create a processing block object."""
        # Simplified implementation
        class ProcessingBlock:
            def __init__(self, start_time, end_time):
                self.start_time = start_time
                self.end_time = end_time
        
        return ProcessingBlock(
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now()
        )
    
    async def _cleanup_old_data(self):
        """Cleanup old data files."""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config.cleanup_after_days)
            
            # Cleanup old output files
            output_dir = self.pipeline_config['paths']['output_dir']
            if os.path.exists(output_dir):
                for root, dirs, files in os.walk(output_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        if file_time < cutoff_date:
                            if self.config.archive_old_data:
                                # Archive file
                                archive_path = os.path.join(self.config.archive_location, file)
                                os.makedirs(os.path.dirname(archive_path), exist_ok=True)
                                os.rename(file_path, archive_path)
                            else:
                                # Delete file
                                os.remove(file_path)
            
            logger.info("Data cleanup completed")
            
        except Exception as e:
            logger.error(f"Data cleanup failed: {e}")
    
    async def _perform_health_check(self):
        """Perform health check."""
        try:
            # Check system resources
            memory_usage = psutil.virtual_memory().percent
            cpu_usage = psutil.cpu_percent()
            disk_usage = psutil.disk_usage('/').percent
            
            # Check resource limits
            if memory_usage > self.config.memory_limit_gb * 12.5:  # Convert GB to percentage
                logger.warning(f"High memory usage: {memory_usage:.1f}%")
            
            if cpu_usage > self.config.cpu_limit_percent:
                logger.warning(f"High CPU usage: {cpu_usage:.1f}%")
            
            if disk_usage > self.config.disk_space_limit_gb:
                logger.warning(f"High disk usage: {disk_usage:.1f}%")
            
            # Check active jobs
            if len(self.active_jobs) > self.config.max_concurrent_jobs:
                logger.warning(f"Too many active jobs: {len(self.active_jobs)}")
            
            # Check for stuck jobs
            for job_id, job_status in self.active_jobs.items():
                if job_status.status == "running":
                    runtime = (datetime.now() - job_status.start_time).total_seconds()
                    if runtime > self.config.job_timeout:
                        logger.warning(f"Job {job_id} has been running for {runtime:.0f}s")
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    async def _wait_for_active_jobs(self):
        """Wait for active jobs to complete."""
        while self.active_jobs:
            logger.info(f"Waiting for {len(self.active_jobs)} active jobs to complete")
            await asyncio.sleep(5)
    
    async def _notify_job_callbacks(self, event_type: str, job_status: JobStatus):
        """Notify job callbacks."""
        for callback in self.job_callbacks.get(event_type, []):
            try:
                await callback(job_status)
            except Exception as e:
                logger.error(f"Job callback failed: {e}")
    
    def add_job_callback(self, event_type: str, callback: Callable):
        """Add a job callback."""
        if event_type in self.job_callbacks:
            self.job_callbacks[event_type].append(callback)
    
    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """Get job status by ID."""
        if job_id in self.active_jobs:
            return self.active_jobs[job_id]
        
        for job in self.job_history:
            if job.job_id == job_id:
                return job
        
        return None
    
    def get_all_jobs(self) -> List[JobStatus]:
        """Get all jobs (active and history)."""
        return list(self.active_jobs.values()) + self.job_history
    
    def get_job_statistics(self) -> Dict[str, Any]:
        """Get job statistics."""
        all_jobs = self.get_all_jobs()
        
        if not all_jobs:
            return {
                'total_jobs': 0,
                'active_jobs': 0,
                'completed_jobs': 0,
                'failed_jobs': 0,
                'success_rate': 0.0,
                'avg_duration': 0.0
            }
        
        completed_jobs = [j for j in all_jobs if j.status == "completed"]
        failed_jobs = [j for j in all_jobs if j.status == "failed"]
        active_jobs = [j for j in all_jobs if j.status == "running"]
        
        # Calculate average duration
        durations = []
        for job in completed_jobs:
            if job.start_time and job.end_time:
                duration = (job.end_time - job.start_time).total_seconds()
                durations.append(duration)
        
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        
        return {
            'total_jobs': len(all_jobs),
            'active_jobs': len(active_jobs),
            'completed_jobs': len(completed_jobs),
            'failed_jobs': len(failed_jobs),
            'success_rate': len(completed_jobs) / len(all_jobs) * 100 if all_jobs else 0.0,
            'avg_duration': avg_duration
        }
    
    def generate_automation_report(self) -> str:
        """Generate automation report."""
        report = []
        report.append("# DSA-110 Pipeline Automation Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Configuration
        report.append("## Configuration")
        report.append(f"- Schedule Type: {self.config.schedule_type}")
        report.append(f"- Cron Expression: {self.config.cron_expression}")
        report.append(f"- Max Concurrent Jobs: {self.config.max_concurrent_jobs}")
        report.append(f"- Job Timeout: {self.config.job_timeout}s")
        report.append(f"- Auto Cleanup: {self.config.auto_cleanup}")
        report.append("")
        
        # Statistics
        stats = self.get_job_statistics()
        report.append("## Statistics")
        report.append(f"- Total Jobs: {stats['total_jobs']}")
        report.append(f"- Active Jobs: {stats['active_jobs']}")
        report.append(f"- Completed Jobs: {stats['completed_jobs']}")
        report.append(f"- Failed Jobs: {stats['failed_jobs']}")
        report.append(f"- Success Rate: {stats['success_rate']:.1f}%")
        report.append(f"- Average Duration: {stats['avg_duration']:.1f}s")
        report.append("")
        
        # Recent jobs
        recent_jobs = sorted(self.get_all_jobs(), key=lambda x: x.start_time or datetime.min, reverse=True)[:10]
        report.append("## Recent Jobs")
        for job in recent_jobs:
            status_icon = "✅" if job.status == "completed" else "❌" if job.status == "failed" else "⏳"
            report.append(f"- {status_icon} {job.job_id} - {job.status} - {job.current_stage}")
        
        return "\n".join(report)


# Example usage
if __name__ == "__main__":
    # Create automation configuration
    config = AutomationConfig(
        schedule_type="interval",
        interval_minutes=30,
        max_concurrent_jobs=1
    )
    
    # Create automation system
    automation = PipelineAutomation(config)
    
    print("Pipeline automation system ready!")
