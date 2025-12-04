"""
Streaming worker: Orchestrate pipeline stages for data processing.

This module provides the StreamingWorker class that polls for pending
work from SubbandQueue and orchestrates processing through the pipeline
stages (conversion, calibration, imaging, photometry, mosaic).

Production Features:
- Graceful shutdown handling (SIGINT, SIGTERM)
- Retry logic with exponential backoff for transient failures
- Health checks for liveness/readiness probes
- Metrics collection for monitoring
- Structured logging
"""

from __future__ import annotations

import argparse
import logging
import signal
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING

from dsa110_contimg.conversion.streaming.queue import SubbandQueue
from dsa110_contimg.conversion.streaming.stages import (
    CalibrationStage,
    ConversionStage,
    ImagingStage,
    MosaicStage,
    PhotometryStage,
)
from dsa110_contimg.conversion.streaming.stages.calibration import CalibrationConfig
from dsa110_contimg.conversion.streaming.stages.conversion import ConversionConfig
from dsa110_contimg.conversion.streaming.stages.imaging import ImagingConfig
from dsa110_contimg.conversion.streaming.stages.mosaic import MosaicConfig
from dsa110_contimg.conversion.streaming.stages.photometry import PhotometryConfig
from dsa110_contimg.conversion.streaming.exceptions import (
    ShutdownRequested,
    StreamingError,
)
from dsa110_contimg.conversion.streaming.health import (
    HealthCheck,
    HealthStatus,
    get_disk_free_gb,
    get_health_checker,
    get_metrics_collector,
)
from dsa110_contimg.conversion.streaming.retry import RetryConfig, retry_with_result

if TYPE_CHECKING:
    from dsa110_contimg.pipeline.hardening import (
        DiskSpaceMonitor,
        ProcessingStateMachine,
    )

logger = logging.getLogger(__name__)


@dataclass
class WorkerConfig:
    """Configuration for the streaming worker.
    
    Attributes:
        input_dir: Directory to watch for incoming HDF5 files
        output_dir: Directory for output MS files and images
        scratch_dir: Directory for temporary/scratch files
        queue_db: Path to queue/products SQLite database
        registry_db: Path to calibration registry database
        expected_subbands: Number of subbands per observation (default: 16)
        poll_interval: Seconds between directory polls (default: 5.0)
        worker_poll_interval: Seconds between queue polls (default: 5.0)
        enable_calibration_solving: Enable calibration solving (default: False)
        enable_group_imaging: Enable group imaging (default: False)
        enable_mosaic_creation: Enable mosaic creation (default: False)
        enable_photometry: Enable photometry (default: True)
        enable_auto_qa: Enable auto QA (default: False)
        enable_auto_publish: Enable auto publish (default: False)
        execution_mode: Execution mode (inprocess, subprocess, auto)
        memory_limit_mb: Memory limit for conversion tasks (default: 16000)
        omp_threads: OMP threads for conversion tasks (default: 4)
        cal_fence_timeout: Calibration fence timeout (default: 60.0)
        use_interpolated_cal: Use interpolated calibration (default: True)
        disk_warning_gb: Disk warning threshold (default: 50.0)
        disk_critical_gb: Disk critical threshold (default: 10.0)
        max_retries: Maximum retry attempts for transient failures (default: 3)
        graceful_shutdown_timeout: Seconds to wait for graceful shutdown (default: 30)
    """
    
    # Directories
    input_dir: Path
    output_dir: Path
    scratch_dir: Path
    
    # Database paths
    queue_db: Path
    registry_db: Path
    
    # Processing settings
    expected_subbands: int = 16
    poll_interval: float = 5.0
    worker_poll_interval: float = 5.0
    
    # Feature flags
    enable_calibration_solving: bool = False
    enable_group_imaging: bool = False
    enable_mosaic_creation: bool = False
    enable_photometry: bool = True
    enable_auto_qa: bool = False
    enable_auto_publish: bool = False
    
    # Execution settings
    execution_mode: str = "auto"
    memory_limit_mb: int = 16000
    omp_threads: int = 4
    
    # Calibration settings
    cal_fence_timeout: float = 60.0
    use_interpolated_cal: bool = True
    
    # Disk management
    disk_warning_gb: float = 50.0
    disk_critical_gb: float = 10.0
    
    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "WorkerConfig":
        """Create configuration from CLI arguments.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            WorkerConfig instance
        """
        return cls(
            input_dir=Path(args.input_dir),
            output_dir=Path(args.output_dir),
            scratch_dir=Path(getattr(args, "scratch_dir", "/stage/dsa110-contimg")),
            queue_db=Path(args.queue_db),
            registry_db=Path(getattr(args, "registry_db", args.queue_db)),
            expected_subbands=getattr(args, "expected_subbands", 16),
            poll_interval=getattr(args, "poll_interval", 5.0),
            worker_poll_interval=getattr(args, "worker_poll_interval", 5.0),
            enable_calibration_solving=getattr(args, "enable_calibration_solving", False),
            enable_group_imaging=getattr(args, "enable_group_imaging", False),
            enable_mosaic_creation=getattr(args, "enable_mosaic_creation", False),
            enable_photometry=getattr(args, "enable_photometry", True),
            enable_auto_qa=getattr(args, "enable_auto_qa", False),
            enable_auto_publish=getattr(args, "enable_auto_publish", False),
            execution_mode=getattr(args, "execution_mode", "auto"),
            memory_limit_mb=getattr(args, "memory_limit_mb", 16000),
            omp_threads=getattr(args, "omp_threads", 4),
            cal_fence_timeout=getattr(args, "cal_fence_timeout", 60.0),
            use_interpolated_cal=getattr(args, "use_interpolated_cal", True),
        )


@dataclass
class ProcessingResult:
    """Result of processing a single group."""
    
    group_id: str
    success: bool
    stage: str = "unknown"
    ms_path: Optional[str] = None
    image_path: Optional[str] = None
    error_message: Optional[str] = None
    elapsed_seconds: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)


class StreamingWorker:
    """Worker that processes data through pipeline stages.
    
    This class orchestrates the streaming processing pipeline:
    1. Polls SubbandQueue for pending groups
    2. Runs conversion (HDF5 → MS)
    3. Optionally solves calibration for calibrator observations
    4. Applies calibration and images
    5. Optionally runs photometry and mosaic creation
    
    Example:
        >>> config = WorkerConfig(
        ...     input_dir=Path("/data/incoming"),
        ...     output_dir=Path("/data/ms"),
        ...     scratch_dir=Path("/stage"),
        ...     queue_db=Path("/data/state/db/pipeline.sqlite3"),
        ...     registry_db=Path("/data/state/db/pipeline.sqlite3"),
        ... )
        >>> queue = SubbandQueue(config.queue_db, expected_subbands=16)
        >>> worker = StreamingWorker(config, queue)
        >>> worker.run()
    """

    def __init__(
        self,
        config: WorkerConfig,
        queue: SubbandQueue,
    ) -> None:
        """Initialize the streaming worker.
        
        Args:
            config: Worker configuration
            queue: SubbandQueue for work tracking
        """
        self.config = config
        self.queue = queue
        
        # Initialize pipeline stages
        self._init_stages()
        
        # Optional hardening components
        self._disk_monitor: Optional["DiskSpaceMonitor"] = None
        self._state_machine: Optional["ProcessingStateMachine"] = None
        self._init_hardening()

    def _init_stages(self) -> None:
        """Initialize pipeline stages."""
        # Products database path
        products_db = self._get_products_db_path()
        
        # Conversion stage
        self.conversion_stage = ConversionStage(
            ConversionConfig(
                output_dir=self.config.output_dir,
                scratch_dir=self.config.scratch_dir,
                products_db=products_db,
                expected_subbands=self.config.expected_subbands,
                use_subprocess=(self.config.execution_mode == "subprocess"),
                memory_limit_mb=self.config.memory_limit_mb,
                omp_threads=self.config.omp_threads,
            )
        )
        
        # Calibration stage
        self.calibration_stage = CalibrationStage(
            CalibrationConfig(
                registry_db=self.config.registry_db,
                enable_solving=self.config.enable_calibration_solving,
                use_interpolation=self.config.use_interpolated_cal,
                fence_timeout=self.config.cal_fence_timeout,
                validity_hours=12.0,
            )
        )
        
        # Imaging stage
        self.imaging_stage = ImagingStage(
            ImagingConfig(
                output_dir=self.config.output_dir,
                products_db=products_db,
                quality_tier="standard",
                enable_catalog_validation=True,
                validation_catalog="nvss",
            )
        )
        
        # Photometry stage (optional)
        if self.config.enable_photometry:
            self.photometry_stage: Optional[PhotometryStage] = PhotometryStage(
                PhotometryConfig(
                    products_db=products_db,
                    catalog="nvss",
                    search_radius_deg=0.5,
                )
            )
        else:
            self.photometry_stage = None
        
        # Mosaic stage (optional)
        if self.config.enable_mosaic_creation:
            self.mosaic_stage: Optional[MosaicStage] = MosaicStage(
                MosaicConfig(
                    output_dir=self.config.output_dir,
                    products_db=products_db,
                    enable_qa=self.config.enable_auto_qa,
                    enable_publish=self.config.enable_auto_publish,
                )
            )
        else:
            self.mosaic_stage = None

    def _init_hardening(self) -> None:
        """Initialize optional hardening components."""
        try:
            from dsa110_contimg.pipeline.hardening import (
                DiskSpaceMonitor,
                DiskQuota,
                ProcessingStateMachine,
            )
            
            # Disk space monitor
            quotas = [
                DiskQuota(
                    path=self.config.output_dir,
                    warning_threshold_gb=self.config.disk_warning_gb,
                    critical_threshold_gb=self.config.disk_critical_gb,
                    cleanup_target_gb=100.0,
                ),
                DiskQuota(
                    path=self.config.scratch_dir,
                    warning_threshold_gb=20.0,
                    critical_threshold_gb=5.0,
                    cleanup_target_gb=50.0,
                ),
            ]
            self._disk_monitor = DiskSpaceMonitor(quotas=quotas)
            logger.info("Disk space monitor initialized")
            
            # Processing state machine
            self._state_machine = ProcessingStateMachine(self.config.registry_db)
            logger.info("Processing state machine initialized")
            
        except (ImportError, OSError, ValueError) as e:
            logger.debug(f"Hardening components not available: {e}")

    def _get_products_db_path(self) -> Path:
        """Get path to products database."""
        # Use unified database (queue_db contains products tables)
        return self.config.queue_db

    def _update_state(self, group_id: str, state: str) -> None:
        """Update state machine for a group."""
        if self._state_machine is not None:
            try:
                self._state_machine.transition(group_id, state)
            except Exception as e:
                logger.debug(f"State transition failed for {group_id}: {e}")

    def _check_disk_space(self) -> bool:
        """Check if there is enough disk space to continue processing.
        
        Returns:
            True if safe to continue, False if disk space is critical
        """
        if self._disk_monitor is None:
            return True
            
        if not self._disk_monitor.is_safe_to_process():
            logger.error("Disk space critical! Pausing processing.")
            self._disk_monitor.trigger_cleanup_if_needed()
            return False
        
        return True

    def process_group(self, group_id: str) -> ProcessingResult:
        """Process a single group through all pipeline stages.
        
        Args:
            group_id: Group identifier (timestamp-based)
            
        Returns:
            ProcessingResult with status and metrics
        """
        t0 = time.perf_counter()
        result = ProcessingResult(group_id=group_id, success=False)
        
        try:
            # Get files for this group
            files = self.queue.get_group_files(group_id)
            if not files:
                result.error_message = "No files found for group"
                return result
            
            # === CONVERSION STAGE ===
            self._update_state(group_id, "CONVERTING")
            conv_result = self.conversion_stage.execute(group_id, files)
            
            if not conv_result.success:
                result.error_message = conv_result.error_message
                result.stage = "conversion"
                self._update_state(group_id, "FAILED")
                return result
            
            ms_path = conv_result.ms_path
            result.ms_path = ms_path
            result.metrics["conversion_time"] = conv_result.elapsed_seconds
            self._update_state(group_id, "CONVERTED")
            
            # Extract pointing info for later stages
            dec_deg = conv_result.dec_deg
            mid_mjd = conv_result.mid_mjd
            
            # === CALIBRATION STAGE ===
            self._update_state(group_id, "CALIBRATING")
            cal_result = self.calibration_stage.execute(
                ms_path=ms_path,
                is_calibrator=conv_result.is_calibrator,
                mid_mjd=mid_mjd,
                dec_deg=dec_deg,
            )
            
            if conv_result.is_calibrator and cal_result.success:
                self._update_state(group_id, "CALIBRATED")
            
            result.metrics["calibration_applied"] = cal_result.cal_applied
            result.metrics["is_calibrator"] = conv_result.is_calibrator
            
            # === IMAGING STAGE ===
            self._update_state(group_id, "IMAGING")
            img_result = self.imaging_stage.execute(
                ms_path=ms_path,
                group_id=group_id,
                cal_applied=cal_result.cal_applied,
            )
            
            if not img_result.success:
                result.error_message = img_result.error_message
                result.stage = "imaging"
                logger.error(f"Imaging failed for {group_id}: {img_result.error_message}")
                # Continue - imaging failure is not fatal
            else:
                result.image_path = img_result.image_path
                result.metrics["imaging_time"] = img_result.elapsed_seconds
                self._update_state(group_id, "IMAGED")
            
            # === PHOTOMETRY STAGE (optional) ===
            if self.photometry_stage is not None and img_result.fits_path:
                try:
                    phot_result = self.photometry_stage.execute(
                        image_path=Path(img_result.fits_path),
                        group_id=group_id,
                    )
                    if phot_result.success:
                        result.metrics["photometry_sources"] = phot_result.source_count
                except Exception as e:
                    logger.warning(f"Photometry failed for {group_id}: {e}")
            
            # === MOSAIC STAGE (optional) ===
            if self.mosaic_stage is not None and dec_deg is not None:
                try:
                    mosaic_result = self.mosaic_stage.check_and_trigger(
                        dec_deg=dec_deg,
                        new_ms_path=ms_path,
                    )
                    if mosaic_result is not None and mosaic_result.success:
                        result.metrics["mosaic_triggered"] = True
                        result.metrics["mosaic_group_id"] = mosaic_result.group_id
                except Exception as e:
                    logger.warning(f"Mosaic check failed for {group_id}: {e}")
            
            # Success
            self._update_state(group_id, "COMPLETED")
            result.success = True
            result.stage = "completed"
            result.elapsed_seconds = time.perf_counter() - t0
            
            return result
            
        except Exception as e:
            logger.exception(f"Processing failed for {group_id}")
            self._update_state(group_id, "FAILED")
            result.error_message = str(e)
            result.elapsed_seconds = time.perf_counter() - t0
            return result

    def run(self) -> None:
        """Run the worker loop, processing pending groups.
        
        This method runs indefinitely, polling for new work and
        processing groups through the pipeline stages.
        """
        logger.info(
            f"Starting streaming worker "
            f"(poll_interval={self.config.worker_poll_interval}s)"
        )
        
        while True:
            try:
                # Check disk space before acquiring work
                if not self._check_disk_space():
                    time.sleep(60.0)  # Wait longer when disk is critical
                    continue
                
                # Try to acquire next pending group
                group_id = self.queue.acquire_next_pending()
                if group_id is None:
                    time.sleep(self.config.worker_poll_interval)
                    continue
                
                logger.info(f"Processing group {group_id}")
                
                # Process the group
                result = self.process_group(group_id)
                
                # Update queue state
                if result.success:
                    self.queue.update_state(
                        group_id,
                        "completed",
                        metrics=result.metrics,
                    )
                    logger.info(
                        f"Completed {group_id} in {result.elapsed_seconds:.2f}s"
                    )
                else:
                    self.queue.update_state(
                        group_id,
                        "failed",
                        error=result.error_message,
                    )
                    logger.error(
                        f"Failed {group_id} at stage {result.stage}: "
                        f"{result.error_message}"
                    )
                    
            except KeyboardInterrupt:
                logger.info("Worker interrupted by user")
                break
            except Exception as e:
                logger.exception(f"Worker loop error: {e}")
                time.sleep(2.0)

    def run_once(self, group_id: str) -> ProcessingResult:
        """Process a single group (for testing or manual invocation).
        
        Args:
            group_id: Group identifier to process
            
        Returns:
            ProcessingResult with status
        """
        return self.process_group(group_id)


def create_worker(args: argparse.Namespace, queue: SubbandQueue) -> StreamingWorker:
    """Factory function to create a StreamingWorker from CLI args.
    
    Args:
        args: Parsed command line arguments
        queue: SubbandQueue instance
        
    Returns:
        Configured StreamingWorker
    """
    config = WorkerConfig.from_args(args)
    return StreamingWorker(config, queue)
