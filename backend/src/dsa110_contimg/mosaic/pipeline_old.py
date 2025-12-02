"""
Pipeline definitions for mosaicking.

Two pipeline classes (ABSURD-style):
- NightlyMosaicPipeline: Runs at scheduled time, processes previous 24 hours
- OnDemandMosaicPipeline: User-requested mosaic via API

Both use a job graph with dependencies:
    MosaicPlanningJob → MosaicBuildJob → MosaicQAJob
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from .jobs import (
    JobResult,
    MosaicBuildJob,
    MosaicJobConfig,
    MosaicPlanningJob,
    MosaicQAJob,
)
from .tiers import MosaicTier, select_tier_for_request

logger = logging.getLogger(__name__)


# =============================================================================
# Pipeline Status and Enums
# =============================================================================


class PipelineStatus(str, Enum):
    """Status of a pipeline execution."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RetryBackoff(str, Enum):
    """Retry backoff strategy."""
    
    CONSTANT = "constant"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


# =============================================================================
# Result and Config Dataclasses
# =============================================================================


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


@dataclass
class RetryPolicy:
    """Configuration for job retry behavior.
    
    Attributes:
        max_retries: Maximum retry attempts
        backoff: Backoff strategy
        initial_delay_seconds: Initial delay before first retry
        max_delay_seconds: Maximum delay between retries
    """
    
    max_retries: int = 2
    backoff: RetryBackoff = RetryBackoff.EXPONENTIAL
    initial_delay_seconds: float = 2.0
    max_delay_seconds: float = 60.0
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number (0-indexed)."""
        if attempt == 0:
            return 0
        
        if self.backoff == RetryBackoff.CONSTANT:
            delay = self.initial_delay_seconds
        elif self.backoff == RetryBackoff.LINEAR:
            delay = self.initial_delay_seconds * attempt
        else:  # EXPONENTIAL
            delay = self.initial_delay_seconds * (2 ** (attempt - 1))
        
        return min(delay, self.max_delay_seconds)


@dataclass
class NotificationConfig:
    """Configuration for pipeline notifications.
    
    Attributes:
        enabled: Whether notifications are enabled
        on_failure: Notify on job/pipeline failure
        on_success: Notify on successful completion
        channels: Notification channels (email, slack, webhook)
        recipients: List of recipients (emails, webhook URLs)
    """
    
    enabled: bool = True
    on_failure: bool = True
    on_success: bool = False
    channels: list[str] = field(default_factory=lambda: ["email"])
    recipients: list[str] = field(default_factory=list)


@dataclass 
class MosaicPipelineConfig:
    """Configuration for mosaic pipelines.
    
    Attributes:
        database_path: Path to the unified database
        mosaic_dir: Directory for output mosaics
        images_table: Name of the images table
        retry_policy: Job retry configuration
        notifications: Notification configuration
    """
    
    database_path: Path
    mosaic_dir: Path
    images_table: str = "images"
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    
    # Legacy compatibility
    @property
    def max_retries(self) -> int:
        return self.retry_policy.max_retries
    
    @property
    def notify_on_failure(self) -> bool:
        return self.notifications.enabled and self.notifications.on_failure


# =============================================================================
# Job Node for Dependency Graph
# =============================================================================


@dataclass
class JobNode:
    """A job in the pipeline dependency graph.
    
    Attributes:
        job_id: Unique identifier for this job
        job_class: The job class to instantiate
        params: Parameters for the job (can include ${ref} placeholders)
        dependencies: List of job_ids this job depends on
        result: Result after execution
    """
    
    job_id: str
    job_class: type
    params: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    result: JobResult | None = None


# =============================================================================
# Base Pipeline Class
# =============================================================================


class MosaicPipeline(ABC):
    """Base class for ABSURD-style mosaic pipelines.
    
    Pipelines define a job graph with dependencies and execution policies.
    The graph is executed by running jobs in dependency order.
    
    Subclasses should implement:
    - pipeline_name: Unique name for this pipeline type
    - build_job_graph(): Define the jobs and dependencies
    
    Example:
        class MyPipeline(MosaicPipeline):
            pipeline_name = "my_pipeline"
            
            def build_job_graph(self) -> None:
                self.add_job(
                    job_id='plan',
                    job_class=MosaicPlanningJob,
                    params={'tier': 'science'}
                )
                self.add_job(
                    job_id='build',
                    job_class=MosaicBuildJob,
                    params={'plan_id': '${plan.plan_id}'},
                    dependencies=['plan']
                )
    """
    
    pipeline_name: str = "mosaic_pipeline"
    
    def __init__(self, config: MosaicPipelineConfig):
        """Initialize pipeline.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config
        self._jobs: dict[str, JobNode] = {}
        self._execution_order: list[str] = []
        self._results: dict[str, JobResult] = {}
        self._status = PipelineStatus.PENDING
        self._execution_id: str | None = None
        self._started_at: datetime | None = None
        self._completed_at: datetime | None = None
        
        # Build the job graph
        self.build_job_graph()
        self._compute_execution_order()
    
    @abstractmethod
    def build_job_graph(self) -> None:
        """Define jobs and dependencies.
        
        Subclasses implement this to add jobs via add_job().
        """
        ...
    
    def add_job(
        self,
        job_id: str,
        job_class: type,
        params: dict[str, Any] | None = None,
        dependencies: list[str] | None = None,
    ) -> None:
        """Add a job to the pipeline graph.
        
        Args:
            job_id: Unique identifier for this job
            job_class: The job class to instantiate
            params: Parameters for the job. Can include '${other_job.output_key}'
                   to reference outputs from dependency jobs.
            dependencies: List of job_ids this job depends on
        """
        if job_id in self._jobs:
            raise ValueError(f"Job '{job_id}' already exists in pipeline")
        
        # Validate dependencies exist
        for dep in (dependencies or []):
            if dep not in self._jobs:
                raise ValueError(
                    f"Job '{job_id}' depends on '{dep}' which hasn't been added yet. "
                    f"Add dependencies before dependents."
                )
        
        self._jobs[job_id] = JobNode(
            job_id=job_id,
            job_class=job_class,
            params=params or {},
            dependencies=dependencies or [],
        )
    
    def _compute_execution_order(self) -> None:
        """Compute topological order for job execution."""
        # Simple topological sort using Kahn's algorithm
        in_degree = {job_id: len(node.dependencies) for job_id, node in self._jobs.items()}
        queue = [job_id for job_id, degree in in_degree.items() if degree == 0]
        order = []
        
        while queue:
            job_id = queue.pop(0)
            order.append(job_id)
            
            # Reduce in-degree for dependents
            for other_id, node in self._jobs.items():
                if job_id in node.dependencies:
                    in_degree[other_id] -= 1
                    if in_degree[other_id] == 0:
                        queue.append(other_id)
        
        if len(order) != len(self._jobs):
            raise ValueError("Circular dependency detected in job graph")
        
        self._execution_order = order
    
    def _resolve_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Resolve parameter references like ${job_id.output_key}.
        
        Args:
            params: Parameters with potential references
            
        Returns:
            Resolved parameters with actual values
        """
        resolved = {}
        
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # Parse reference: ${job_id.output_key}
                ref = value[2:-1]
                if "." in ref:
                    job_id, output_key = ref.split(".", 1)
                    if job_id in self._results and self._results[job_id].success:
                        resolved[key] = self._results[job_id].outputs.get(output_key)
                    else:
                        raise ValueError(
                            f"Cannot resolve '{value}': job '{job_id}' not completed"
                        )
                else:
                    raise ValueError(f"Invalid reference format: '{value}'")
            else:
                resolved[key] = value
        
        return resolved
    
    def _create_job_config(self) -> MosaicJobConfig:
        """Create job configuration from pipeline config."""
        return MosaicJobConfig(
            database_path=self.config.database_path,
            mosaic_dir=self.config.mosaic_dir,
            images_table=self.config.images_table,
        )
    
    def _execute_job_with_retry(self, job_node: JobNode) -> JobResult:
        """Execute a single job with retry policy.
        
        Args:
            job_node: The job to execute
            
        Returns:
            JobResult from final attempt
        """
        retry_policy = self.config.retry_policy
        last_result: JobResult | None = None
        
        for attempt in range(retry_policy.max_retries + 1):
            delay = retry_policy.get_delay(attempt)
            if delay > 0:
                logger.info(
                    f"Retrying job '{job_node.job_id}' in {delay:.1f}s "
                    f"(attempt {attempt + 1}/{retry_policy.max_retries + 1})"
                )
                time.sleep(delay)
            
            try:
                # Resolve parameters with outputs from completed jobs
                resolved_params = self._resolve_params(job_node.params)
                
                # Create job instance
                job = job_node.job_class(
                    config=self._create_job_config(),
                    **resolved_params,
                )
                
                result = job.execute()
                if result.success:
                    return result
                
                last_result = result
                logger.warning(f"Job '{job_node.job_id}' failed: {result.error}")
                
            except Exception as e:
                logger.exception(f"Job '{job_node.job_id}' raised exception: {e}")
                last_result = JobResult.fail(str(e))
        
        return last_result or JobResult.fail("Unknown error")
    
    def _send_notification(
        self,
        event: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Send notification if configured.
        
        Args:
            event: Event type (failure, success, etc.)
            message: Notification message
            details: Additional details
        """
        notifications = self.config.notifications
        
        if not notifications.enabled:
            return
        
        if event == "failure" and not notifications.on_failure:
            return
        if event == "success" and not notifications.on_success:
            return
        
        # Log notification (actual sending would integrate with alerting system)
        logger.info(
            f"[Notification:{event}] {message} "
            f"(channels={notifications.channels}, recipients={notifications.recipients})"
        )
        
        # TODO: Integrate with monitoring/tasks.py send_alert
    
    def start(self) -> str:
        """Start pipeline execution.
        
        Returns:
            Execution ID
        """
        import uuid
        
        self._execution_id = f"{self.pipeline_name}_{uuid.uuid4().hex[:8]}"
        self._status = PipelineStatus.RUNNING
        self._started_at = datetime.now(timezone.utc)
        
        logger.info(f"Starting pipeline '{self.pipeline_name}' (id={self._execution_id})")
        
        return self._execution_id
    
    def execute(self) -> PipelineResult:
        """Execute the pipeline synchronously.
        
        Returns:
            PipelineResult with execution status
        """
        self.start()
        errors: list[str] = []
        
        plan_id: int | None = None
        mosaic_id: int | None = None
        mosaic_path: str | None = None
        qa_status: str | None = None
        
        try:
            for job_id in self._execution_order:
                job_node = self._jobs[job_id]
                logger.info(f"Executing job '{job_id}'")
                
                result = self._execute_job_with_retry(job_node)
                self._results[job_id] = result
                job_node.result = result
                
                if not result.success:
                    errors.append(f"Job '{job_id}' failed: {result.error}")
                    self._status = PipelineStatus.FAILED
                    self._send_notification(
                        "failure",
                        f"Pipeline failed at job '{job_id}'",
                        {"error": result.error},
                    )
                    break
                
                # Extract key outputs
                if job_id == "plan":
                    plan_id = result.outputs.get("plan_id")
                elif job_id == "build":
                    mosaic_id = result.outputs.get("mosaic_id")
                    mosaic_path = result.outputs.get("mosaic_path")
                elif job_id == "qa":
                    qa_status = result.outputs.get("qa_status")
            
            else:
                # All jobs completed successfully
                self._status = PipelineStatus.COMPLETED
                if qa_status != "FAIL":
                    self._send_notification(
                        "success",
                        f"Pipeline completed: {mosaic_path}",
                    )
        
        except Exception as e:
            logger.exception(f"Pipeline execution error: {e}")
            errors.append(str(e))
            self._status = PipelineStatus.FAILED
        
        finally:
            self._completed_at = datetime.now(timezone.utc)
        
        success = self._status == PipelineStatus.COMPLETED and qa_status != "FAIL"
        
        return PipelineResult(
            success=success,
            plan_id=plan_id,
            mosaic_id=mosaic_id,
            mosaic_path=mosaic_path,
            qa_status=qa_status,
            message=f"Pipeline {self._status.value}: {qa_status or 'N/A'}",
            errors=errors,
            execution_id=self._execution_id,
            started_at=self._started_at,
            completed_at=self._completed_at,
        )


# =============================================================================
# Concrete Pipeline Classes
# =============================================================================


class NightlyMosaicPipeline(MosaicPipeline):
    """Nightly science-tier mosaic pipeline.
    
    Runs at scheduled time (e.g., 03:00 UTC), processes previous 24 hours.
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
        >>> pipeline = NightlyMosaicPipeline(config, target_date=datetime.now())
        >>> result = pipeline.execute()
    """
    
    pipeline_name = "nightly_mosaic"
    
    def __init__(
        self,
        config: MosaicPipelineConfig,
        target_date: datetime | None = None,
    ):
        """Initialize nightly pipeline.
        
        Args:
            config: Pipeline configuration
            target_date: Date to process (default: yesterday UTC)
        """
        # Calculate time range
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
    
    def build_job_graph(self) -> None:
        """Build the nightly pipeline job graph."""
        # Job 1: Planning
        self.add_job(
            job_id="plan",
            job_class=MosaicPlanningJob,
            params={
                "start_time": self.start_time,
                "end_time": self.end_time,
                "tier": "science",
                "mosaic_name": self.mosaic_name,
            },
        )
        
        # Job 2: Build (depends on plan)
        self.add_job(
            job_id="build",
            job_class=MosaicBuildJob,
            params={
                "plan_id": "${plan.plan_id}",
            },
            dependencies=["plan"],
        )
        
        # Job 3: QA (depends on build)
        self.add_job(
            job_id="qa",
            job_class=MosaicQAJob,
            params={
                "mosaic_id": "${build.mosaic_id}",
            },
            dependencies=["build"],
        )


class OnDemandMosaicPipeline(MosaicPipeline):
    """User-requested mosaic pipeline via API.
    
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
    
    def __init__(
        self,
        config: MosaicPipelineConfig,
        name: str,
        start_time: int,
        end_time: int,
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
    
    def build_job_graph(self) -> None:
        """Build the on-demand pipeline job graph."""
        # Job 1: Planning
        self.add_job(
            job_id="plan",
            job_class=MosaicPlanningJob,
            params={
                "start_time": self.start_time,
                "end_time": self.end_time,
                "tier": self.tier,
                "mosaic_name": self.mosaic_name,
            },
        )
        
        # Job 2: Build (depends on plan)
        self.add_job(
            job_id="build",
            job_class=MosaicBuildJob,
            params={
                "plan_id": "${plan.plan_id}",
            },
            dependencies=["plan"],
        )
        
        # Job 3: QA (depends on build)
        self.add_job(
            job_id="qa",
            job_class=MosaicQAJob,
            params={
                "mosaic_id": "${build.mosaic_id}",
            },
            dependencies=["build"],
        )


# =============================================================================
# Backward-Compatible Functions
# =============================================================================


def run_nightly_mosaic(
    config: MosaicPipelineConfig,
    target_date: datetime | None = None,
) -> PipelineResult:
    """Run nightly science-tier mosaic.
    
    Processes the previous 24 hours of data.
    
    Note: This is a backward-compatible wrapper around NightlyMosaicPipeline.
    New code should use NightlyMosaicPipeline directly.
    
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
    pipeline = NightlyMosaicPipeline(config, target_date=target_date)
    return pipeline.execute()


def run_on_demand_mosaic(
    config: MosaicPipelineConfig,
    name: str,
    start_time: int,
    end_time: int,
    tier: str | None = None,
) -> PipelineResult:
    """Run on-demand mosaic for user request.
    
    Note: This is a backward-compatible wrapper around OnDemandMosaicPipeline.
    New code should use OnDemandMosaicPipeline directly.
    
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
    pipeline = OnDemandMosaicPipeline(
        config=config,
        name=name,
        start_time=start_time,
        end_time=end_time,
        tier=tier,
    )
    return pipeline.execute()


def run_mosaic_pipeline(
    config: MosaicPipelineConfig,
    mosaic_name: str,
    start_time: int,
    end_time: int,
    tier: str,
) -> PipelineResult:
    """Execute full mosaic pipeline: Plan → Build → QA.
    
    Note: This is a backward-compatible wrapper. Consider using
    OnDemandMosaicPipeline directly for more control.
    
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


def _execute_with_retry(job: Any, max_retries: int) -> JobResult:
    """Execute a job with retries.
    
    Note: This is a backward-compatible function. New code should use
    MosaicPipeline's built-in retry mechanism.
    
    Args:
        job: Job instance with execute() method
        max_retries: Maximum retry attempts
        
    Returns:
        JobResult from final attempt
    """
    policy = RetryPolicy(max_retries=max_retries)
    last_result: JobResult | None = None
    
    for attempt in range(max_retries + 1):
        delay = policy.get_delay(attempt)
        if delay > 0:
            logger.info(f"Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries + 1})")
            time.sleep(delay)
        
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
    import asyncio
    
    # Build config
    retry_policy = RetryPolicy(
        max_retries=params.get("max_retries", 2),
        backoff=RetryBackoff(params.get("backoff", "exponential")),
    )
    
    config = MosaicPipelineConfig(
        database_path=Path(params["database_path"]),
        mosaic_dir=Path(params["mosaic_dir"]),
        images_table=params.get("images_table", "images"),
        retry_policy=retry_policy,
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
    
    # Run in thread pool to avoid blocking
    result = await asyncio.to_thread(pipeline.execute)
    
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


# =============================================================================
# Generic Pipeline Framework Integration
# =============================================================================
# 
# The classes below use the new generic pipeline framework from
# dsa110_contimg.pipeline, which provides:
# - Execution tracking in database
# - ABSURD task integration
# - Cron-based scheduling
#
# These are the preferred classes for new code.

from dsa110_contimg.pipeline import Pipeline as GenericPipeline
from dsa110_contimg.pipeline import register_pipeline


@register_pipeline
class NightlyMosaicPipelineV2(GenericPipeline):
    """Nightly mosaic pipeline using the generic framework.
    
    This is the preferred pipeline for new deployments.
    Uses the generic Pipeline base class for:
    - Database execution tracking
    - ABSURD task spawning
    - Cron-based scheduling
    
    Schedule: 03:00 UTC daily
    """
    
    pipeline_name = "nightly_mosaic_v2"
    schedule = "0 3 * * *"  # 3 AM UTC daily
    
    def __init__(self, config: MosaicPipelineConfig | None = None):
        """Initialize nightly pipeline.
        
        Args:
            config: Pipeline configuration (uses MosaicPipelineConfig)
        """
        # Calculate time range for previous 24 hours
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
class OnDemandMosaicPipelineV2(GenericPipeline):
    """On-demand mosaic pipeline using the generic framework.
    
    This is the preferred pipeline for API-triggered mosaics.
    No schedule - triggered on demand.
    """
    
    pipeline_name = "on_demand_mosaic_v2"
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
