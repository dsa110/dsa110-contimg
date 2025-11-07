"""
Observability and monitoring for pipeline execution.

Provides structured logging, metrics collection, and tracing capabilities.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages import StageStatus


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
    
    def __init__(self, logger_name: str = "pipeline"):
        """Initialize pipeline observer.
        
        Args:
            logger_name: Name for the logger
        """
        self.logger = logging.getLogger(logger_name)
        self.metrics: List[StageMetrics] = []
        self._stage_start_times: Dict[str, float] = {}
    
    def stage_started(self, stage_name: str, context: PipelineContext) -> None:
        """Called when a stage starts execution.
        
        Args:
            stage_name: Name of the stage
            context: Pipeline context
        """
        self._stage_start_times[stage_name] = time.time()
        
        self.logger.info(
            "stage_started",
            extra={
                "stage": stage_name,
                "job_id": context.job_id,
                "inputs": context.inputs,
            }
        )
    
    def stage_completed(
        self,
        stage_name: str,
        context: PipelineContext,
        duration: float
    ) -> None:
        """Called when a stage completes successfully.
        
        Args:
            stage_name: Name of the stage
            context: Pipeline context after stage execution
            duration: Duration in seconds
        """
        metrics = StageMetrics(
            stage_name=stage_name,
            duration_seconds=duration,
            status=StageStatus.COMPLETED,
        )
        self.metrics.append(metrics)
        
        self.logger.info(
            "stage_completed",
            extra={
                "stage": stage_name,
                "job_id": context.job_id,
                "duration_seconds": duration,
                "outputs": context.outputs,
            }
        )
    
    def stage_failed(
        self,
        stage_name: str,
        context: PipelineContext,
        error: Exception,
        duration: float,
        attempt: int = 1
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
    
    def stage_skipped(
        self,
        stage_name: str,
        context: PipelineContext,
        reason: str
    ) -> None:
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
            }
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
            }
        )
    
    def pipeline_completed(
        self,
        context: PipelineContext,
        duration: float,
        status: str
    ) -> None:
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
            }
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
            "average_duration_seconds": total_duration / len(self.metrics) if self.metrics else 0,
        }

