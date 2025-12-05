# pylint: disable=broad-exception-caught
"""
Pipeline Stage Integration Module.

Integrates state machine, error recovery, and pipeline metrics into
pipeline stages for comprehensive monitoring and reliability.

This module provides:
- Stage execution wrapper with state machine integration
- Error recovery with automatic retry
- Pipeline metrics collection
- GPU utilization tracking per stage

Usage:
    from dsa110_contimg.pipeline.stage_integration import (
        execute_stage_with_tracking,
        StageExecutionConfig,
    )

    # Execute stage with full tracking
    result = execute_stage_with_tracking(
        stage=my_stage,
        context=pipeline_context,
        config=StageExecutionConfig(
            enable_state_machine=True,
            enable_retry=True,
            enable_metrics=True,
        )
    )
"""

from __future__ import annotations

import functools
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, TypeVar

logger = logging.getLogger(__name__)

# Type variable for generic returns
T = TypeVar("T")


# =============================================================================
# Stage to State Mapping
# =============================================================================


class StageStateMapping(str, Enum):
    """Mapping from pipeline stage names to state machine states."""

    CATALOG_SETUP = "catalog_setup"
    CONVERSION = "conversion"
    CALIBRATION_SOLVE = "calibration_solve"
    CALIBRATION = "calibration"
    IMAGING = "imaging"
    MOSAIC = "mosaic"
    LIGHT_CURVE = "light_curve"
    ORGANIZATION = "organization"
    VALIDATION = "validation"
    CROSS_MATCH = "cross_match"
    ADAPTIVE_PHOTOMETRY = "adaptive_photometry"


# Maps stage names to (processing_state, success_state) tuples
STAGE_STATE_MAP: Dict[str, Tuple[str, str]] = {
    "catalog_setup": ("pending", "pending"),  # No state change for catalog setup
    "conversion": ("converting", "converted"),
    "calibration_solve": ("solving_cal", "applying_cal"),
    "calibration": ("applying_cal", "imaging"),
    "imaging": ("imaging", "done"),
    "mosaic": ("imaging", "done"),  # Mosaic is part of imaging
    "light_curve": ("imaging", "done"),
    "organization": ("done", "done"),  # Post-processing
    "validation": ("done", "done"),  # Post-processing
    "cross_match": ("done", "done"),  # Post-processing
    "adaptive_photometry": ("done", "done"),  # Post-processing
}


# Maps stage names to pipeline metric stages
STAGE_METRIC_MAP: Dict[str, str] = {
    "catalog_setup": "total",  # Not tracked separately
    "conversion": "conversion",
    "calibration_solve": "calibration_solve",
    "calibration": "calibration_apply",
    "imaging": "imaging",
    "mosaic": "imaging",
    "light_curve": "imaging",
    "organization": "qa",
    "validation": "qa",
    "cross_match": "qa",
    "adaptive_photometry": "qa",
}


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class StageExecutionConfig:
    """Configuration for stage execution with tracking.

    Attributes:
        enable_state_machine: Enable state machine transitions
        enable_retry: Enable automatic retry on failure
        enable_metrics: Enable pipeline metrics collection
        max_retries: Maximum retry attempts
        base_delay: Base delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        record_gpu_metrics: Record GPU utilization metrics
        alert_on_failure: Send alerts on stage failure
    """

    enable_state_machine: bool = True
    enable_retry: bool = True
    enable_metrics: bool = True
    max_retries: int = 3
    base_delay: float = 2.0
    max_delay: float = 60.0
    record_gpu_metrics: bool = True
    alert_on_failure: bool = True


@dataclass
class StageExecutionResult:
    """Result of stage execution with tracking.

    Attributes:
        success: Whether execution succeeded
        context: Updated pipeline context (or original on failure)
        duration_s: Total execution duration in seconds
        retry_count: Number of retry attempts
        error: Error message if failed
        metrics: Stage metrics if collected
        state_transitions: List of state transitions made
    """

    success: bool
    context: Any  # PipelineContext
    duration_s: float = 0.0
    retry_count: int = 0
    error: Optional[str] = None
    error_type: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    state_transitions: List[Tuple[str, str]] = field(default_factory=list)


# =============================================================================
# State Machine Integration
# =============================================================================


def _get_ms_path_from_context(context: Any) -> Optional[str]:
    """Extract MS path from pipeline context.

    Args:
        context: PipelineContext instance

    Returns:
        MS path if found, None otherwise
    """
    # Check outputs first (most common for mid-pipeline stages)
    if hasattr(context, "outputs"):
        if "ms_path" in context.outputs:
            return str(context.outputs["ms_path"])
        if "ms_paths" in context.outputs and context.outputs["ms_paths"]:
            return str(context.outputs["ms_paths"][0])

    # Check inputs
    if hasattr(context, "inputs"):
        if "input_path" in context.inputs:
            return str(context.inputs["input_path"])
        if "ms_path" in context.inputs:
            return str(context.inputs["ms_path"])

    return None


@contextmanager
def state_machine_context(
    stage_name: str,
    ms_path: str,
    enable: bool = True,
) -> Generator[Dict[str, Any], None, None]:
    """Context manager for state machine integration.

    Automatically transitions state machine on entry/exit and handles
    failures by transitioning to FAILED state.

    Args:
        stage_name: Name of the pipeline stage
        ms_path: Path to MS being processed
        enable: Whether to actually track state (for conditional enabling)

    Yields:
        Context dict for storing checkpoint data
    """
    if not enable or not ms_path:
        yield {}
        return

    # Import here to avoid circular imports
    from dsa110_contimg.database.state_machine import (
        MSState,
        StateTransitionError,
        get_state_machine,
    )

    checkpoint_data: Dict[str, Any] = {}

    # Get state mapping for this stage
    state_tuple = STAGE_STATE_MAP.get(stage_name, ("pending", "pending"))
    processing_state_str, success_state_str = state_tuple

    # Skip state tracking for stages that don't change state
    if processing_state_str == success_state_str == "pending":
        yield checkpoint_data
        return

    if processing_state_str == success_state_str == "done":
        yield checkpoint_data
        return

    try:
        processing_state = MSState(processing_state_str)
        success_state = MSState(success_state_str)
    except ValueError as e:
        logger.warning("Invalid state mapping for %s: %s", stage_name, e)
        yield checkpoint_data
        return

    sm = get_state_machine()

    try:
        # Transition to processing state
        try:
            sm.transition(ms_path, processing_state)
            logger.debug("State transition: %s -> %s", ms_path, processing_state.value)
        except StateTransitionError as e:
            # Already in processing state or invalid transition - log and continue
            logger.debug("State transition skipped for %s: %s", stage_name, e)

        yield checkpoint_data

        # Success - transition to success state
        try:
            sm.transition(ms_path, success_state)
            logger.debug("State transition: %s -> %s (success)", ms_path, success_state.value)
        except StateTransitionError as e:
            logger.debug("Success state transition skipped for %s: %s", stage_name, e)

    except Exception as exc:
        # Failure - mark as failed with checkpoint data
        try:
            sm.mark_failed(ms_path, exc, checkpoint=checkpoint_data)
            logger.warning("Stage %s failed, state -> FAILED: %s", stage_name, str(exc)[:200])
        except (StateTransitionError, RuntimeError) as e:
            logger.debug("Failed state transition skipped for %s: %s", stage_name, e)
        raise


# =============================================================================
# Metrics Integration
# =============================================================================


@contextmanager
def metrics_context(
    stage_name: str,
    ms_path: str,
    enable: bool = True,
    record_gpu: bool = True,
) -> Generator["MetricsContextHelper", None, None]:
    """Context manager for pipeline metrics collection.

    Args:
        stage_name: Name of the pipeline stage
        ms_path: Path to MS being processed
        enable: Whether to collect metrics
        record_gpu: Whether to record GPU metrics

    Yields:
        MetricsContextHelper for recording additional metrics
    """
    if not enable or not ms_path:
        yield MetricsContextHelper(None, None, None)
        return

    # Import here to avoid circular imports
    from dsa110_contimg.monitoring.pipeline_metrics import (
        PipelineStage as MetricStage,
    )
    from dsa110_contimg.monitoring.pipeline_metrics import (
        get_metrics_collector,
    )

    # Get metric stage mapping
    metric_stage_str = STAGE_METRIC_MAP.get(stage_name, "total")

    try:
        metric_stage = MetricStage(metric_stage_str)
    except ValueError:
        metric_stage = MetricStage.TOTAL

    collector = get_metrics_collector()
    start_time = time.time()

    try:
        with collector.stage_context(metric_stage, ms_path) as stage_ctx:
            helper = MetricsContextHelper(collector, stage_ctx, record_gpu)
            yield helper
    except Exception:
        # Record duration even on failure
        duration = time.time() - start_time
        try:
            job = collector.get_job(ms_path)
            if job:
                timing = job.get_timing(metric_stage)
                timing.total_time_s = duration
        except Exception as e:
            logger.debug("Failed to record failure metrics: %s", e)
        raise


class MetricsContextHelper:
    """Helper class for recording metrics within a stage context."""

    def __init__(self, collector: Any, stage_ctx: Any, record_gpu: Optional[bool]):
        self._collector = collector
        self._stage_ctx = stage_ctx
        self._record_gpu = record_gpu
        self._cpu_start: Optional[float] = None
        self._gpu_start: Optional[float] = None

    def start_cpu_timer(self) -> None:
        """Start CPU timing."""
        self._cpu_start = time.time()

    def stop_cpu_timer(self) -> float:
        """Stop CPU timer and record time.

        Returns:
            Elapsed CPU time in seconds
        """
        if self._cpu_start is None:
            return 0.0
        elapsed = time.time() - self._cpu_start
        if self._stage_ctx:
            self._stage_ctx.record_cpu_time(elapsed)
        self._cpu_start = None
        return elapsed

    def start_gpu_timer(self) -> None:
        """Start GPU timing."""
        self._gpu_start = time.time()

    def stop_gpu_timer(self) -> float:
        """Stop GPU timer and record time.

        Returns:
            Elapsed GPU time in seconds
        """
        if self._gpu_start is None:
            return 0.0
        elapsed = time.time() - self._gpu_start
        if self._stage_ctx:
            self._stage_ctx.record_gpu_time(elapsed)
        self._gpu_start = None
        return elapsed

    def record_cpu_time(self, seconds: float) -> None:
        """Record CPU time directly."""
        if self._stage_ctx:
            self._stage_ctx.record_cpu_time(seconds)

    def record_gpu_time(self, seconds: float) -> None:
        """Record GPU time directly."""
        if self._stage_ctx:
            self._stage_ctx.record_gpu_time(seconds)

    def record_io_time(self, seconds: float) -> None:
        """Record I/O time directly."""
        if self._stage_ctx:
            self._stage_ctx.record_io_time(seconds)

    def record_memory(self, ram_gb: float, gpu_mem_gb: float = 0.0) -> None:
        """Record memory sample."""
        if self._collector and self._stage_ctx:
            try:
                from dsa110_contimg.monitoring.pipeline_metrics import record_memory_sample

                ms_path = getattr(self._stage_ctx, "job_metrics", {})
                if hasattr(ms_path, "ms_path"):
                    record_memory_sample(ms_path.ms_path, ram_gb, gpu_mem_gb)
            except Exception as e:
                logger.debug("Failed to record memory sample: %s", e)


# =============================================================================
# Error Recovery Integration
# =============================================================================


def with_stage_retry(
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    retryable_exceptions: tuple = (Exception,),
    non_retryable_exceptions: tuple = (
        KeyboardInterrupt,
        SystemExit,
        MemoryError,
    ),
):
    """Decorator for adding retry logic to stage execute methods.

    This decorator wraps stage execute() methods with retry logic,
    integrating with the error recovery module.

    Args:
        max_retries: Maximum retry attempts
        base_delay: Base delay between retries
        max_delay: Maximum delay cap
        retryable_exceptions: Exceptions that trigger retry
        non_retryable_exceptions: Exceptions that don't retry

    Returns:
        Decorated function
    """
    # Import here to avoid circular imports
    from dsa110_contimg.pipeline.error_recovery import (
        BackoffStrategy,
        RetryPolicy,
        execute_with_retry_sync,
    )

    policy = RetryPolicy(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        backoff_strategy=BackoffStrategy.EXPONENTIAL,
        retryable_exceptions=retryable_exceptions,
    )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                # Check for non-retryable exceptions before retry logic
                result = execute_with_retry_sync(
                    func,
                    *args,
                    policy=policy,
                    operation_name=func.__name__,
                    **kwargs,
                )

                if result.success:
                    return result.result

                # All retries exhausted
                raise RuntimeError(
                    f"Stage execution failed after {result.attempt_count} attempts: "
                    f"{result.final_error}"
                )
            except non_retryable_exceptions:
                # Re-raise non-retryable exceptions immediately
                raise

        return wrapper

    return decorator


# =============================================================================
# Combined Stage Execution
# =============================================================================


def execute_stage_with_tracking(
    stage: Any,  # PipelineStage
    context: Any,  # PipelineContext
    config: Optional[StageExecutionConfig] = None,
) -> StageExecutionResult:
    """Execute a pipeline stage with full tracking.

    Combines state machine transitions, error recovery, and metrics
    collection into a single execution wrapper.

    Args:
        stage: PipelineStage instance to execute
        context: PipelineContext with inputs/outputs
        config: Execution configuration

    Returns:
        StageExecutionResult with execution outcome
    """
    config = config or StageExecutionConfig()
    start_time = time.time()
    state_transitions: List[Tuple[str, str]] = []
    retry_count = 0
    collected_metrics: Dict[str, Any] = {}

    # Get stage name and MS path
    stage_name = stage.get_name() if hasattr(stage, "get_name") else "unknown"
    ms_path = _get_ms_path_from_context(context)

    def _execute_once() -> Any:
        """Execute stage once with tracking."""
        nonlocal collected_metrics

        with state_machine_context(
            stage_name, ms_path, enable=config.enable_state_machine
        ) as sm_ctx:
            with metrics_context(
                stage_name,
                ms_path,
                enable=config.enable_metrics,
                record_gpu=config.record_gpu_metrics,
            ) as metrics_helper:
                # Execute the stage
                result_context = stage.execute(context)

                # Store any checkpoint data
                sm_ctx.update(
                    {
                        "stage": stage_name,
                        "ms_path": ms_path,
                        "completed_at": time.time(),
                    }
                )

                return result_context

    # Execute with retry if enabled
    if config.enable_retry:
        from dsa110_contimg.pipeline.error_recovery import (
            BackoffStrategy,
            RetryPolicy,
            execute_with_retry_sync,
        )

        policy = RetryPolicy(
            max_retries=config.max_retries,
            base_delay=config.base_delay,
            max_delay=config.max_delay,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
        )

        retry_result = execute_with_retry_sync(
            _execute_once,
            policy=policy,
            operation_name=f"stage_{stage_name}",
        )

        retry_count = retry_result.attempt_count - 1  # First attempt is not a retry
        duration = time.time() - start_time

        if retry_result.success:
            return StageExecutionResult(
                success=True,
                context=retry_result.result,
                duration_s=duration,
                retry_count=retry_count,
                metrics=collected_metrics,
                state_transitions=state_transitions,
            )
        else:
            # Send alert if enabled
            if config.alert_on_failure:
                _send_failure_alert(stage_name, ms_path, retry_result.final_error)

            return StageExecutionResult(
                success=False,
                context=context,  # Return original context on failure
                duration_s=duration,
                retry_count=retry_count,
                error=retry_result.final_error,
                error_type=retry_result.final_error_type,
                metrics=collected_metrics,
                state_transitions=state_transitions,
            )

    else:
        # Execute without retry
        try:
            result_context = _execute_once()
            duration = time.time() - start_time

            return StageExecutionResult(
                success=True,
                context=result_context,
                duration_s=duration,
                retry_count=0,
                metrics=collected_metrics,
                state_transitions=state_transitions,
            )
        except Exception as exc:
            duration = time.time() - start_time

            if config.alert_on_failure:
                _send_failure_alert(stage_name, ms_path, str(exc))

            return StageExecutionResult(
                success=False,
                context=context,
                duration_s=duration,
                retry_count=0,
                error=str(exc),
                error_type=type(exc).__name__,
                metrics=collected_metrics,
                state_transitions=state_transitions,
            )


def _send_failure_alert(stage_name: str, ms_path: Optional[str], error: Optional[str]) -> None:
    """Send alert for stage failure.

    Args:
        stage_name: Name of the failed stage
        ms_path: Path to MS being processed
        error: Error message
    """
    try:
        from dsa110_contimg.monitoring.tasks import send_alert

        title = f"Pipeline Stage Failed: {stage_name}"
        message = f"Stage '{stage_name}' failed"
        if ms_path:
            message += f" for MS: {Path(ms_path).name}"
        if error:
            message += f"\nError: {error[:500]}"

        # Fire and forget - don't block on alert
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(send_alert("error", title, message))
            else:
                loop.run_until_complete(send_alert("error", title, message))
        except RuntimeError:
            # No event loop - skip alert
            logger.debug("Could not send alert: no event loop")
    except Exception as e:
        logger.debug("Failed to send failure alert: %s", e)


# =============================================================================
# Decorator for Stage Methods
# =============================================================================


def tracked_stage_execute(
    enable_state_machine: bool = True,
    enable_retry: bool = True,
    enable_metrics: bool = True,
    max_retries: int = 3,
    base_delay: float = 2.0,
    alert_on_failure: bool = True,
):
    """Decorator for stage execute() methods with full tracking.

    Adds state machine integration, error recovery, and metrics
    collection to a stage's execute method.

    Args:
        enable_state_machine: Enable state machine transitions
        enable_retry: Enable automatic retry on failure
        enable_metrics: Enable pipeline metrics collection
        max_retries: Maximum retry attempts
        base_delay: Base delay between retries
        alert_on_failure: Send alerts on failure

    Returns:
        Decorated execute method

    Example:
        class MyStage(PipelineStage):
            @tracked_stage_execute(max_retries=2)
            def execute(self, context):
                # Stage logic here
                return context.with_output("result", value)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, context, *args, **kwargs):
            # Get stage name
            stage_name = self.get_name() if hasattr(self, "get_name") else func.__name__

            # Get MS path from context
            ms_path = _get_ms_path_from_context(context)

            # Track execution
            start_time = time.time()
            retry_count = 0

            def _execute_once():
                with state_machine_context(stage_name, ms_path, enable=enable_state_machine):
                    with metrics_context(stage_name, ms_path, enable=enable_metrics):
                        return func(self, context, *args, **kwargs)

            if enable_retry:
                from dsa110_contimg.pipeline.error_recovery import (
                    BackoffStrategy,
                    RetryPolicy,
                    execute_with_retry_sync,
                )

                policy = RetryPolicy(
                    max_retries=max_retries,
                    base_delay=base_delay,
                    max_delay=60.0,
                    backoff_strategy=BackoffStrategy.EXPONENTIAL,
                )

                result = execute_with_retry_sync(
                    _execute_once,
                    policy=policy,
                    operation_name=f"stage_{stage_name}",
                )

                if result.success:
                    return result.result
                else:
                    if alert_on_failure:
                        _send_failure_alert(stage_name, ms_path, result.final_error)
                    raise RuntimeError(
                        f"Stage '{stage_name}' failed after {result.attempt_count} "
                        f"attempts: {result.final_error}"
                    )
            else:
                try:
                    return _execute_once()
                except Exception as exc:
                    if alert_on_failure:
                        _send_failure_alert(stage_name, ms_path, str(exc))
                    raise

        return wrapper

    return decorator


# =============================================================================
# Public Exports
# =============================================================================

__all__ = [
    "StageExecutionConfig",
    "StageExecutionResult",
    "StageStateMapping",
    "STAGE_STATE_MAP",
    "STAGE_METRIC_MAP",
    "state_machine_context",
    "metrics_context",
    "MetricsContextHelper",
    "with_stage_retry",
    "execute_stage_with_tracking",
    "tracked_stage_execute",
]
