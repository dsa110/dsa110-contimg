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
from .executor import ExecutionStatus, PipelineExecutor
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

__all__ = [
    # Base classes
    "Job",
    "JobConfig",
    "JobResult",
    "NotificationConfig",
    "Pipeline",
    "RetryBackoff",
    "RetryPolicy",
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
]