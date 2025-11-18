"""
Observability and monitoring for pipeline execution.

Provides structured logging, metrics collection, and tracing capabilities.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages import StageStatus

# Try to import psutil for resource metrics
try:
    import psutil

    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False


@dataclass
class StageMetrics:
    """Metrics for a pipeline stage execution."""

    stage_name: str
    duration_seconds: float
    input_size_bytes: Optional[int] = None
    output_size_bytes: Optional[int] = None
    memory_peak_mb: Optional[float] = None
    cpu_time_seconds: Optional[float] = None
    attempt: int = 1
    status: StageStatus = StageStatus.PENDING


class PipelineObserver:
    """Observes pipeline execution for monitoring and logging.

    Provides structured logging and metrics collection for pipeline stages.
    Can be extended to integrate with monitoring systems (Prometheus, etc.).
    """

    def __init__(self, logger_name: str = "pipeline", collect_resource_metrics: bool = True):
        """Initialize pipeline observer.

        Args:
            logger_name: Name for the logger
            collect_resource_metrics: Whether to collect memory/CPU metrics
        """
        self.logger = logging.getLogger(logger_name)
        self.metrics: List[StageMetrics] = []
        self._stage_start_times: Dict[str, float] = {}
        self._collect_resource_metrics = collect_resource_metrics and _PSUTIL_AVAILABLE
        self._stage_start_resources: Dict[str, Dict[str, float]] = {}

    def stage_started(self, stage_name: str, context: PipelineContext) -> None:
        """Called when a stage starts execution.

        Args:
            stage_name: Name of the stage
            context: Pipeline context
        """
        self._stage_start_times[stage_name] = time.time()

        # Collect resource metrics at start
        if self._collect_resource_metrics:
            try:
                process = psutil.Process()
                mem_info = process.memory_info()
                cpu_percent = process.cpu_percent()

                self._stage_start_resources[stage_name] = {
                    "memory_mb": mem_info.rss / (1024 * 1024),
                    "cpu_percent": cpu_percent,
                }
            except Exception as e:
                self.logger.debug(f"Could not collect start resources for {stage_name}: {e}")

        self.logger.info(
            "stage_started",
            extra={
                "stage": stage_name,
                "job_id": context.job_id,
                "inputs": context.inputs,
            },
        )

    def stage_completed(self, stage_name: str, context: PipelineContext, duration: float) -> None:
        """Called when a stage completes successfully.

        Args:
            stage_name: Name of the stage
            context: Pipeline context after stage execution
            duration: Duration in seconds
        """
        # Collect resource metrics at completion
        memory_peak_mb = None
        cpu_time_seconds = None

        if self._collect_resource_metrics:
            try:
                process = psutil.Process()
                mem_info = process.memory_info()
                memory_peak_mb = mem_info.rss / (1024 * 1024)

                # Calculate CPU time (approximate)
                cpu_percent = process.cpu_percent()
                cpu_time_seconds = (cpu_percent / 100.0) * duration

                # Get peak memory if we have start metrics
                if stage_name in self._stage_start_resources:
                    start_mem = self._stage_start_resources[stage_name]["memory_mb"]
                    memory_peak_mb = max(memory_peak_mb, start_mem)
            except Exception as e:
                self.logger.debug(f"Could not collect completion resources for {stage_name}: {e}")

        metrics = StageMetrics(
            stage_name=stage_name,
            duration_seconds=duration,
            status=StageStatus.COMPLETED,
            memory_peak_mb=memory_peak_mb,
            cpu_time_seconds=cpu_time_seconds,
        )
        self.metrics.append(metrics)

        extra_data = {
            "stage": stage_name,
            "job_id": context.job_id,
            "duration_seconds": duration,
            "outputs": context.outputs,
        }

        if memory_peak_mb is not None:
            extra_data["memory_peak_mb"] = memory_peak_mb
        if cpu_time_seconds is not None:
            extra_data["cpu_time_seconds"] = cpu_time_seconds

        self.logger.info("stage_completed", extra=extra_data)

    def stage_failed(
        self,
        stage_name: str,
        context: PipelineContext,
        error: Exception,
        duration: float,
        attempt: int = 1,
    ) -> None:
        """Called when a stage fails.

        Args:
            stage_name: Name of the stage
            context: Pipeline context
            error: Exception that occurred
            duration: Duration in seconds before failure
            attempt: Attempt number
        """
        metrics = StageMetrics(
            stage_name=stage_name,
            duration_seconds=duration,
            status=StageStatus.FAILED,
            attempt=attempt,
        )
        self.metrics.append(metrics)

        self.logger.error(
            "stage_failed",
            extra={
                "stage": stage_name,
                "job_id": context.job_id,
                "error": str(error),
                "error_type": type(error).__name__,
                "duration_seconds": duration,
                "attempt": attempt,
            },
            exc_info=error,
        )

    def stage_skipped(self, stage_name: str, context: PipelineContext, reason: str) -> None:
        """Called when a stage is skipped.

        Args:
            stage_name: Name of the stage
            context: Pipeline context
            reason: Reason for skipping
        """
        self.logger.info(
            "stage_skipped",
            extra={
                "stage": stage_name,
                "job_id": context.job_id,
                "reason": reason,
            },
        )

    def pipeline_started(self, context: PipelineContext) -> None:
        """Called when pipeline execution starts.

        Args:
            context: Initial pipeline context
        """
        self.logger.info(
            "pipeline_started",
            extra={
                "job_id": context.job_id,
                "inputs": context.inputs,
            },
        )

    def pipeline_completed(self, context: PipelineContext, duration: float, status: str) -> None:
        """Called when pipeline execution completes.

        Args:
            context: Final pipeline context
            duration: Total duration in seconds
            status: Final pipeline status
        """
        self.logger.info(
            "pipeline_completed",
            extra={
                "job_id": context.job_id,
                "status": status,
                "duration_seconds": duration,
                "outputs": context.outputs,
                "total_stages": len(self.metrics),
            },
        )

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics.

        Returns:
            Dictionary with metrics summary
        """
        if not self.metrics:
            return {}

        total_duration = sum(m.duration_seconds for m in self.metrics)
        completed = sum(1 for m in self.metrics if m.status == StageStatus.COMPLETED)
        failed = sum(1 for m in self.metrics if m.status == StageStatus.FAILED)

        return {
            "total_stages": len(self.metrics),
            "completed_stages": completed,
            "failed_stages": failed,
            "total_duration_seconds": total_duration,
            "average_duration_seconds": (total_duration / len(self.metrics) if self.metrics else 0),
        }
