"""
Pipeline definitions for mosaicking.

Two pipeline classes using the generic pipeline framework:
- NightlyMosaicPipeline: Runs at scheduled time, processes previous 24 hours
- OnDemandMosaicPipeline: User-requested mosaic via API

Both use a job graph with dependencies:
    MosaicPlanningJob → MosaicBuildJob → MosaicQAJob
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from dsa110_contimg.pipeline import (
    Pipeline,
    register_pipeline,
    RetryPolicy,
    RetryBackoff,
    NotificationConfig,
)

from .jobs import (
    JobResult,
    MosaicBuildJob,
    MosaicJobConfig,
    MosaicPlanningJob,
    MosaicQAJob,
)
from .tiers import select_tier_for_request


# Re-export for backward compatibility
__all__ = [
    "PipelineStatus",
    "MosaicPipelineConfig",
    "PipelineResult",
    "NightlyMosaicPipeline",
    "OnDemandMosaicPipeline",
    "run_nightly_mosaic",
    "run_on_demand_mosaic",
    "run_mosaic_pipeline",
    "execute_mosaic_pipeline_task",
    # Re-exported from pipeline framework
    "RetryPolicy",
    "RetryBackoff",
    "NotificationConfig",
]

logger = logging.getLogger(__name__)


# =============================================================================
# Pipeline Status Enum (for API compatibility)
# =============================================================================


class PipelineStatus(str, Enum):
    """Status of a pipeline execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# =============================================================================
# Configuration Dataclasses
# =============================================================================


@dataclass
class MosaicPipelineConfig:
    """Configuration for mosaic pipelines.

    Attributes:
        database_path: Path to the unified database
        mosaic_dir: Directory for output mosaics
        images_table: Name of the images table
    """

    database_path: Path
    mosaic_dir: Path
    images_table: str = "images"


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
        execution_id: Unique execution ID
        started_at: Pipeline start time
        completed_at: Pipeline completion time
    """

    success: bool
    plan_id: int | None = None
    mosaic_id: int | None = None
    mosaic_path: str | None = None
    qa_status: str | None = None
    message: str = ""
    errors: list[str] = field(default_factory=list)
    execution_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


# =============================================================================
# Pipeline Classes
# =============================================================================


@register_pipeline
class NightlyMosaicPipeline(Pipeline):
    """Nightly mosaic pipeline using the generic framework.

    Runs at 03:00 UTC daily, processes previous 24 hours of data.
    Always uses 'science' tier for publication-quality mosaics.

    Job graph:
        plan (MosaicPlanningJob)
          └─> build (MosaicBuildJob)
                └─> qa (MosaicQAJob)

    Example:
        >>> config = MosaicPipelineConfig(
        ...     database_path=Path("pipeline.sqlite3"),
        ...     mosaic_dir=Path("/data/mosaics"),
        ... )
        >>> pipeline = NightlyMosaicPipeline(config)
        >>> result = pipeline.execute()
    """

    pipeline_name = "nightly_mosaic"
    schedule = "0 3 * * *"  # 3 AM UTC daily

    def __init__(
        self,
        config: MosaicPipelineConfig | None = None,
        target_date: datetime | None = None,
    ):
        """Initialize nightly pipeline.

        Args:
            config: Pipeline configuration
            target_date: Date to process (default: yesterday UTC)
        """
        # Calculate time range for previous 24 hours
        if target_date is None:
            now = datetime.now(timezone.utc)
            target_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

        self.target_date = target_date
        self.end_time = int(target_date.timestamp())
        self.start_time = self.end_time - 86400  # 24 hours

        # Generate mosaic name
        date_str = target_date.strftime("%Y%m%d")
        self.mosaic_name = f"nightly_{date_str}"

        super().__init__(config)

    def build(self) -> None:
        """Build the nightly pipeline job graph."""
        # Job 1: Planning
        self.add_job(
            MosaicPlanningJob,
            job_id="plan",
            params={
                "start_time": self.start_time,
                "end_time": self.end_time,
                "tier": "science",
                "mosaic_name": self.mosaic_name,
            },
        )

        # Job 2: Build (depends on plan)
        self.add_job(
            MosaicBuildJob,
            job_id="build",
            params={
                "plan_id": "${plan.plan_id}",
            },
            dependencies=["plan"],
        )

        # Job 3: QA (depends on build)
        self.add_job(
            MosaicQAJob,
            job_id="qa",
            params={
                "mosaic_id": "${build.mosaic_id}",
            },
            dependencies=["build"],
        )

        # Configure retry and notifications
        self.set_retry_policy(max_retries=2, backoff="exponential")
        self.add_notification(
            on_failure="qa",
            channels=["email"],
            recipients=["observer@dsa110.org"],
        )


@register_pipeline
class OnDemandMosaicPipeline(Pipeline):
    """On-demand mosaic pipeline for API-triggered requests.

    Same job structure as nightly, but with user-specified parameters.
    Tier is auto-selected based on time range if not provided.

    Job graph:
        plan (MosaicPlanningJob)
          └─> build (MosaicBuildJob)
                └─> qa (MosaicQAJob)

    Example:
        >>> pipeline = OnDemandMosaicPipeline(
        ...     config=config,
        ...     name="custom_mosaic",
        ...     start_time=1700000000,
        ...     end_time=1700086400,
        ...     tier="deep",
        ... )
        >>> result = pipeline.execute()
    """

    pipeline_name = "on_demand_mosaic"
    schedule = None  # On-demand, not scheduled

    def __init__(
        self,
        config: MosaicPipelineConfig | None = None,
        name: str = "mosaic",
        start_time: int = 0,
        end_time: int = 0,
        tier: str | None = None,
    ):
        """Initialize on-demand pipeline.

        Args:
            config: Pipeline configuration
            name: Unique mosaic name
            start_time: Start time (Unix timestamp)
            end_time: End time (Unix timestamp)
            tier: Tier to use (auto-selected if not provided)
        """
        self.mosaic_name = name
        self.start_time = start_time
        self.end_time = end_time

        # Auto-select tier if not provided
        if tier is None:
            time_range_hours = (end_time - start_time) / 3600
            selected_tier = select_tier_for_request(time_range_hours)
            self.tier = selected_tier.value
        else:
            self.tier = tier

        super().__init__(config)

    def build(self) -> None:
        """Build the on-demand pipeline job graph."""
        # Job 1: Planning
        self.add_job(
            MosaicPlanningJob,
            job_id="plan",
            params={
                "start_time": self.start_time,
                "end_time": self.end_time,
                "tier": self.tier,
                "mosaic_name": self.mosaic_name,
            },
        )

        # Job 2: Build (depends on plan)
        self.add_job(
            MosaicBuildJob,
            job_id="build",
            params={
                "plan_id": "${plan.plan_id}",
            },
            dependencies=["plan"],
        )

        # Job 3: QA (depends on build)
        self.add_job(
            MosaicQAJob,
            job_id="qa",
            params={
                "mosaic_id": "${build.mosaic_id}",
            },
            dependencies=["build"],
        )

        # Configure retry
        self.set_retry_policy(max_retries=2, backoff="exponential")


# =============================================================================
# Backward-Compatible Wrapper Functions
# =============================================================================


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
    """
    from dsa110_contimg.pipeline import PipelineExecutor
    import asyncio

    pipeline = NightlyMosaicPipeline(config, target_date=target_date)

    # Use executor for proper tracking
    executor = PipelineExecutor(config.database_path)
    execution_id = asyncio.get_event_loop().run_until_complete(
        executor.execute(pipeline)
    )

    # Get status
    status = asyncio.get_event_loop().run_until_complete(
        executor.get_status(execution_id)
    )

    # Convert to PipelineResult
    return _status_to_result(status, pipeline)


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
    """
    from dsa110_contimg.pipeline import PipelineExecutor
    import asyncio

    pipeline = OnDemandMosaicPipeline(
        config=config,
        name=name,
        start_time=start_time,
        end_time=end_time,
        tier=tier,
    )

    # Use executor for proper tracking
    executor = PipelineExecutor(config.database_path)
    execution_id = asyncio.get_event_loop().run_until_complete(
        executor.execute(pipeline)
    )

    # Get status
    status = asyncio.get_event_loop().run_until_complete(
        executor.get_status(execution_id)
    )

    return _status_to_result(status, pipeline)


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
    return run_on_demand_mosaic(
        config=config,
        name=mosaic_name,
        start_time=start_time,
        end_time=end_time,
        tier=tier,
    )


def _status_to_result(status: Any, pipeline: Pipeline) -> PipelineResult:
    """Convert executor status to PipelineResult."""
    from datetime import datetime

    # Extract job outputs
    plan_id = None
    mosaic_id = None
    mosaic_path = None
    qa_status = None
    errors = []

    for job in status.jobs:
        if job.get("outputs_json"):
            import json
            outputs = json.loads(job["outputs_json"])
            if job["job_id"] == "plan":
                plan_id = outputs.get("plan_id")
            elif job["job_id"] == "build":
                mosaic_id = outputs.get("mosaic_id")
                mosaic_path = outputs.get("mosaic_path")
            elif job["job_id"] == "qa":
                qa_status = outputs.get("qa_status")

        if job.get("error"):
            errors.append(f"{job['job_id']}: {job['error']}")

    success = status.status == "completed" and not errors

    return PipelineResult(
        success=success,
        plan_id=plan_id,
        mosaic_id=mosaic_id,
        mosaic_path=mosaic_path,
        qa_status=qa_status,
        message=f"Pipeline {status.status}",
        errors=errors,
        execution_id=status.execution_id,
        started_at=datetime.fromtimestamp(status.started_at, tz=timezone.utc) if status.started_at else None,
        completed_at=datetime.fromtimestamp(status.completed_at, tz=timezone.utc) if status.completed_at else None,
    )


# =============================================================================
# ABSURD Task Integration
# =============================================================================


async def execute_mosaic_pipeline_task(params: dict[str, Any]) -> dict[str, Any]:
    """Execute mosaic pipeline as an ABSURD task.

    This function wraps the pipeline for use with ABSURD task queue.

    Args:
        params: Task parameters including:
            - database_path: Path to database
            - mosaic_dir: Output directory
            - name: Mosaic name
            - start_time: Start time (Unix)
            - end_time: End time (Unix)
            - tier: Optional tier override
            - pipeline_type: "nightly" or "on_demand" (default)

    Returns:
        Task result dict
    """
    from dsa110_contimg.pipeline import PipelineExecutor

    # Build config
    config = MosaicPipelineConfig(
        database_path=Path(params["database_path"]),
        mosaic_dir=Path(params["mosaic_dir"]),
        images_table=params.get("images_table", "images"),
    )

    # Select and create pipeline
    pipeline_type = params.get("pipeline_type", "on_demand")

    if pipeline_type == "nightly":
        target_date = None
        if "target_date" in params:
            target_date = datetime.fromisoformat(params["target_date"])
        pipeline = NightlyMosaicPipeline(config, target_date=target_date)
    else:
        pipeline = OnDemandMosaicPipeline(
            config=config,
            name=params["name"],
            start_time=params["start_time"],
            end_time=params["end_time"],
            tier=params.get("tier"),
        )

    # Execute via executor
    executor = PipelineExecutor(config.database_path)
    execution_id = await executor.execute(pipeline)
    status = await executor.get_status(execution_id)

    result = _status_to_result(status, pipeline)

    if result.success:
        return {
            "status": "success",
            "execution_id": result.execution_id,
            "outputs": {
                "plan_id": result.plan_id,
                "mosaic_id": result.mosaic_id,
                "mosaic_path": result.mosaic_path,
                "qa_status": result.qa_status,
            },
            "message": result.message,
            "started_at": result.started_at.isoformat() if result.started_at else None,
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
        }
    else:
        return {
            "status": "error",
            "execution_id": result.execution_id,
            "message": result.message,
            "errors": result.errors,
        }
