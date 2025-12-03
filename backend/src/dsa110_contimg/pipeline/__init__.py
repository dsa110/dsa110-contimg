"""
Pipeline framework: Declarative job orchestration on top of ABSURD.

This module provides a framework for building declarative pipelines
that compile to ABSURD task chains. It includes:

- Base classes for Jobs and Pipelines
- Pipeline executor for task spawning
- Scheduler for cron-based triggering
- Registries for job/pipeline discovery

Quick Start:
    from dsa110_contimg.pipeline import (
        Job, Pipeline, JobResult,
        PipelineExecutor, PipelineScheduler,
        register_job, register_pipeline,
    )

    @register_job
    @dataclass
    class MyJob(Job):
        job_type = "my_job"
        input_path: str

        def execute(self) -> JobResult:
            # ... do work ...
            return JobResult.ok({"output": result})

    @register_pipeline
    class MyPipeline(Pipeline):
        pipeline_name = "my_pipeline"
        schedule = "0 3 * * *"

        def build(self):
            self.add_job(MyJob, "step1", {"input_path": "/data/input"})
"""

from .base import (
    Job,
    JobConfig,
    JobResult,
    NotificationConfig,
    Pipeline,
    RetryBackoff,
    RetryPolicy,
)
from .events import (
    Event,
    EventEmitter,
    EventType,
    emit_ese_detection,
    emit_job_event,
    emit_pipeline_event,
)
from .executor import ExecutionStatus, PipelineExecutor
from .handlers import (
    ESEMosaicHandler,
    HandlerConfig,
    QAAlertHandler,
    StreamingCalHandler,
    check_ms_for_calibrator,
    emit_data_ingested,
    setup_event_handlers,
)
from .registry import (
    JobRegistry,
    PipelineRegistry,
    get_job_registry,
    get_pipeline_registry,
    register_job,
    register_pipeline,
    reset_registries,
)
from .scheduler import PipelineScheduler, run_scheduler
from .error_recovery import (
    BackoffStrategy,
    Checkpoint,
    CheckpointManager,
    DeadLetterEntry,
    DeadLetterQueue,
    DeadLetterReason,
    ErrorRecoveryManager,
    RetryAttempt,
    RetryOutcome,
    RetryResult,
    execute_with_retry_sync,
    with_retry,
    with_retry_sync,
    QUICK_RETRY_POLICY,
    STANDARD_RETRY_POLICY,
    AGGRESSIVE_RETRY_POLICY,
)
from .stage_integration import (
    StageExecutionConfig,
    StageExecutionResult,
    StageStateMapping,
    STAGE_STATE_MAP,
    STAGE_METRIC_MAP,
    state_machine_context,
    metrics_context,
    MetricsContextHelper,
    with_stage_retry,
    execute_stage_with_tracking,
    tracked_stage_execute,
)

__all__ = [
    # Base classes
    "Job",
    "JobConfig",
    "JobResult",
    "NotificationConfig",
    "Pipeline",
    "RetryBackoff",
    "RetryPolicy",
    # Events
    "Event",
    "EventEmitter",
    "EventType",
    "emit_ese_detection",
    "emit_job_event",
    "emit_pipeline_event",
    # Handlers
    "ESEMosaicHandler",
    "HandlerConfig",
    "QAAlertHandler",
    "StreamingCalHandler",
    "check_ms_for_calibrator",
    "emit_data_ingested",
    "setup_event_handlers",
    # Executor
    "ExecutionStatus",
    "PipelineExecutor",
    # Scheduler
    "PipelineScheduler",
    "run_scheduler",
    # Registry
    "JobRegistry",
    "PipelineRegistry",
    "get_job_registry",
    "get_pipeline_registry",
    "register_job",
    "register_pipeline",
    "reset_registries",
    # Error Recovery
    "BackoffStrategy",
    "Checkpoint",
    "CheckpointManager",
    "DeadLetterEntry",
    "DeadLetterQueue",
    "DeadLetterReason",
    "ErrorRecoveryManager",
    "RetryAttempt",
    "RetryOutcome",
    "RetryResult",
    "execute_with_retry_sync",
    "with_retry",
    "with_retry_sync",
    "QUICK_RETRY_POLICY",
    "STANDARD_RETRY_POLICY",
    "AGGRESSIVE_RETRY_POLICY",
    # Stage Integration
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