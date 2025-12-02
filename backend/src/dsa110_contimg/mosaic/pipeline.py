"""
Pipeline definitions for mosaicking.

Two pipelines:
- NightlyMosaicPipeline: Runs at scheduled time, processes previous 24 hours
- OnDemandMosaicPipeline: User-requested mosaic via API
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .jobs import (
    JobResult,
    MosaicBuildJob,
    MosaicJobConfig,
    MosaicPlanningJob,
    MosaicQAJob,
)
from .tiers import MosaicTier, select_tier_for_request

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of a pipeline execution.
    
    Attributes:
        success: Whether all jobs succeeded
        plan_id: ID of the mosaic plan
        mosaic_id: ID of the completed mosaic (if built)
        mosaic_path: Path to the mosaic file (if built)
        qa_status: QA status (PASS/WARN/FAIL)
        message: Human-readable status message
        errors: List of error messages
    """
    
    success: bool
    plan_id: int | None = None
    mosaic_id: int | None = None
    mosaic_path: str | None = None
    qa_status: str | None = None
    message: str = ""
    errors: list[str] = field(default_factory=list)


@dataclass 
class MosaicPipelineConfig:
    """Configuration for mosaic pipelines.
    
    Attributes:
        database_path: Path to the unified database
        mosaic_dir: Directory for output mosaics
        images_table: Name of the images table
        max_retries: Maximum retry attempts per job
        notify_on_failure: Whether to send notifications on failure
    """
    
    database_path: Path
    mosaic_dir: Path
    images_table: str = "images"
    max_retries: int = 2
    notify_on_failure: bool = True


def run_nightly_mosaic(
    config: MosaicPipelineConfig,
    target_date: datetime | None = None,
) -> PipelineResult:
    """Run nightly science-tier mosaic.
    
    Processes the previous 24 hours of data.
    
    Args:
        config: Pipeline configuration
        target_date: Date to process (default: yesterday UTC)
        
    Returns:
        PipelineResult with execution status
        
    Example:
        >>> config = MosaicPipelineConfig(
        ...     database_path=Path("pipeline.sqlite3"),
        ...     mosaic_dir=Path("/data/mosaics"),
        ... )
        >>> result = run_nightly_mosaic(config)
        >>> if result.success:
        ...     print(f"Created: {result.mosaic_path}")
    """
    # Calculate time range for yesterday UTC
    if target_date is None:
        now = datetime.now(timezone.utc)
        target_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Previous 24 hours
    end_time = int(target_date.timestamp())
    start_time = end_time - 86400
    
    # Generate unique name
    date_str = target_date.strftime("%Y%m%d")
    mosaic_name = f"nightly_{date_str}"
    
    logger.info(f"Starting nightly mosaic pipeline: {mosaic_name}")
    
    return run_mosaic_pipeline(
        config=config,
        mosaic_name=mosaic_name,
        start_time=start_time,
        end_time=end_time,
        tier="science",
    )


def run_on_demand_mosaic(
    config: MosaicPipelineConfig,
    name: str,
    start_time: int,
    end_time: int,
    tier: str | None = None,
) -> PipelineResult:
    """Run on-demand mosaic for user request.
    
    Args:
        config: Pipeline configuration
        name: Unique mosaic name
        start_time: Start time (Unix timestamp)
        end_time: End time (Unix timestamp)
        tier: Tier to use (auto-selected if not provided)
        
    Returns:
        PipelineResult with execution status
        
    Example:
        >>> result = run_on_demand_mosaic(
        ...     config=config,
        ...     name="custom_mosaic_001",
        ...     start_time=1700000000,
        ...     end_time=1700086400,
        ...     tier="science",
        ... )
    """
    # Auto-select tier if not provided
    if tier is None:
        time_range_hours = (end_time - start_time) / 3600
        selected_tier = select_tier_for_request(time_range_hours)
        tier = selected_tier.value
    
    logger.info(f"Starting on-demand mosaic pipeline: {name} (tier={tier})")
    
    return run_mosaic_pipeline(
        config=config,
        mosaic_name=name,
        start_time=start_time,
        end_time=end_time,
        tier=tier,
    )


def run_mosaic_pipeline(
    config: MosaicPipelineConfig,
    mosaic_name: str,
    start_time: int,
    end_time: int,
    tier: str,
) -> PipelineResult:
    """Execute full mosaic pipeline: Plan → Build → QA.
    
    Args:
        config: Pipeline configuration
        mosaic_name: Unique name for the mosaic
        start_time: Start time (Unix timestamp)
        end_time: End time (Unix timestamp)
        tier: Tier to use
        
    Returns:
        PipelineResult with full execution status
    """
    errors = []
    
    # Create job config
    job_config = MosaicJobConfig(
        database_path=config.database_path,
        mosaic_dir=config.mosaic_dir,
        images_table=config.images_table,
    )
    
    # Step 1: Planning
    logger.info(f"Step 1/3: Planning mosaic '{mosaic_name}'")
    
    plan_job = MosaicPlanningJob(
        start_time=start_time,
        end_time=end_time,
        tier=tier,
        mosaic_name=mosaic_name,
        config=job_config,
    )
    
    plan_result = _execute_with_retry(plan_job, config.max_retries)
    
    if not plan_result.success:
        errors.append(f"Planning failed: {plan_result.error}")
        return PipelineResult(
            success=False,
            message="Pipeline failed at planning stage",
            errors=errors,
        )
    
    plan_id = plan_result.outputs['plan_id']
    logger.info(f"Planning complete: plan_id={plan_id}, "
                f"n_images={plan_result.outputs['n_images']}")
    
    # Step 2: Building
    logger.info(f"Step 2/3: Building mosaic for plan {plan_id}")
    
    build_job = MosaicBuildJob(
        plan_id=plan_id,
        config=job_config,
    )
    
    build_result = _execute_with_retry(build_job, config.max_retries)
    
    if not build_result.success:
        errors.append(f"Build failed: {build_result.error}")
        return PipelineResult(
            success=False,
            plan_id=plan_id,
            message="Pipeline failed at build stage",
            errors=errors,
        )
    
    mosaic_id = build_result.outputs['mosaic_id']
    mosaic_path = build_result.outputs['mosaic_path']
    logger.info(f"Build complete: mosaic_id={mosaic_id}, path={mosaic_path}")
    
    # Step 3: QA
    logger.info(f"Step 3/3: Running QA for mosaic {mosaic_id}")
    
    qa_job = MosaicQAJob(
        mosaic_id=mosaic_id,
        config=job_config,
    )
    
    qa_result = _execute_with_retry(qa_job, config.max_retries)
    
    if not qa_result.success:
        errors.append(f"QA failed: {qa_result.error}")
        return PipelineResult(
            success=False,
            plan_id=plan_id,
            mosaic_id=mosaic_id,
            mosaic_path=mosaic_path,
            message="Pipeline failed at QA stage",
            errors=errors,
        )
    
    qa_status = qa_result.outputs['qa_status']
    logger.info(f"QA complete: status={qa_status}")
    
    # Pipeline complete
    success = qa_status != "FAIL"
    
    return PipelineResult(
        success=success,
        plan_id=plan_id,
        mosaic_id=mosaic_id,
        mosaic_path=mosaic_path,
        qa_status=qa_status,
        message=f"Mosaic pipeline complete: {qa_status}",
        errors=errors,
    )


def _execute_with_retry(job: Any, max_retries: int) -> JobResult:
    """Execute a job with retries.
    
    Args:
        job: Job instance with execute() method
        max_retries: Maximum retry attempts
        
    Returns:
        JobResult from final attempt
    """
    last_result = None
    
    for attempt in range(max_retries + 1):
        if attempt > 0:
            wait_time = 2 ** attempt  # Exponential backoff
            logger.info(f"Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
            time.sleep(wait_time)
        
        try:
            result = job.execute()
            if result.success:
                return result
            last_result = result
            logger.warning(f"Job failed: {result.error}")
        except Exception as e:
            logger.exception(f"Job raised exception: {e}")
            last_result = JobResult.fail(str(e))
    
    return last_result or JobResult.fail("Unknown error")


# Convenience functions for ABSURD integration

async def execute_mosaic_pipeline_task(params: dict[str, Any]) -> dict[str, Any]:
    """Execute mosaic pipeline as an ABSURD task.
    
    This function wraps the synchronous pipeline for use with ABSURD.
    
    Args:
        params: Task parameters including:
            - database_path: Path to database
            - mosaic_dir: Output directory
            - name: Mosaic name
            - start_time: Start time (Unix)
            - end_time: End time (Unix)
            - tier: Optional tier override
            
    Returns:
        Task result dict
    """
    import asyncio
    
    config = MosaicPipelineConfig(
        database_path=Path(params['database_path']),
        mosaic_dir=Path(params['mosaic_dir']),
        images_table=params.get('images_table', 'images'),
    )
    
    # Run in thread pool to avoid blocking
    result = await asyncio.to_thread(
        run_on_demand_mosaic,
        config=config,
        name=params['name'],
        start_time=params['start_time'],
        end_time=params['end_time'],
        tier=params.get('tier'),
    )
    
    if result.success:
        return {
            'status': 'success',
            'outputs': {
                'plan_id': result.plan_id,
                'mosaic_id': result.mosaic_id,
                'mosaic_path': result.mosaic_path,
                'qa_status': result.qa_status,
            },
            'message': result.message,
        }
    else:
        return {
            'status': 'error',
            'message': result.message,
            'errors': result.errors,
        }
