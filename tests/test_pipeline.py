"""
Tests for the pipeline orchestration framework.
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dsa110_contimg.pipeline.config import ConversionConfig, PathsConfig, PipelineConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.orchestrator import (
    PipelineOrchestrator,
    PipelineStatus,
    StageDefinition,
    StageStatus,
)
from dsa110_contimg.pipeline.resilience import RetryPolicy, RetryStrategy
from dsa110_contimg.pipeline.resources import ResourceManager
from dsa110_contimg.pipeline.stages import PipelineStage
from dsa110_contimg.pipeline.state import (
    InMemoryStateRepository,
    JobState,
    SQLiteStateRepository,
    StateRepository,
)
from dsa110_contimg.pipeline.workflows import WorkflowBuilder


class MockStage(PipelineStage):
    """Mock stage for testing."""

    def __init__(self, name: str, should_fail: bool = False, fail_count: int = 0):
        self.name = name
        self.should_fail = should_fail
        self.fail_count = fail_count
        self._call_count = 0

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute mock stage."""
        self._call_count += 1
        if self.should_fail and self._call_count <= self.fail_count:
            raise ValueError(f"Mock failure in {self.name}")
        return context.with_output(f"{self.name}_output", f"value_{self.name}")

    def validate(self, context: PipelineContext):
        """Validate mock stage."""
        from typing import Optional, Tuple

        return True, None

    def get_name(self) -> str:
        """Get stage name."""
        return self.name


class TestPipelineContext:
    """Test PipelineContext."""

    def test_context_creation(self):
        """Test creating a context."""
        config = PipelineConfig(
            paths=PathsConfig(
                input_dir=Path("/input"),
                output_dir=Path("/output"),
            )
        )
        context = PipelineContext(config=config, job_id=123)
        assert context.config == config
        assert context.job_id == 123
        assert context.inputs == {}
        assert context.outputs == {}

    def test_context_with_output(self):
        """Test adding outputs to context."""
        config = PipelineConfig(
            paths=PathsConfig(
                input_dir=Path("/input"),
                output_dir=Path("/output"),
            )
        )
        context = PipelineContext(config=config)
        new_context = context.with_output("key", "value")

        assert new_context.outputs["key"] == "value"
        assert context.outputs == {}  # Original unchanged

    def test_context_with_outputs(self):
        """Test adding multiple outputs."""
        config = PipelineConfig(
            paths=PathsConfig(
                input_dir=Path("/input"),
                output_dir=Path("/output"),
            )
        )
        context = PipelineContext(config=config)
        new_context = context.with_outputs({"a": 1, "b": 2})

        assert new_context.outputs["a"] == 1
        assert new_context.outputs["b"] == 2


class TestStateRepository:
    """Test StateRepository implementations."""

    def test_in_memory_repository(self):
        """Test in-memory repository."""
        repo = InMemoryStateRepository()

        # Create job
        job_id = repo.create_job("test", {"param": "value"})
        assert job_id == 1

        # Get job
        job = repo.get_job(job_id)
        assert job is not None
        assert job.type == "test"
        assert job.status == "pending"
        assert job.context["param"] == "value"

        # Update job
        repo.update_job(job_id, {"status": "running"})
        job = repo.get_job(job_id)
        assert job.status == "running"

        # List jobs
        jobs = repo.list_jobs()
        assert len(jobs) == 1

    def test_sqlite_repository(self):
        """Test SQLite repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo = SQLiteStateRepository(db_path)

            # Create job
            job_id = repo.create_job("test", {"param": "value"})
            assert job_id > 0

            # Get job
            job = repo.get_job(job_id)
            assert job is not None
            assert job.type == "test"

            # Update job
            repo.update_job(job_id, {"status": "running"})
            job = repo.get_job(job_id)
            assert job.status == "running"

            # Cleanup
            repo.close()


class TestResourceManager:
    """Test ResourceManager."""

    def test_temp_dir(self):
        """Test temporary directory management."""
        config = PipelineConfig(
            paths=PathsConfig(
                input_dir=Path("/input"),
                output_dir=Path("/output"),
            )
        )
        rm = ResourceManager(config)

        with rm.temp_dir() as tmp:
            assert tmp.exists()
            assert tmp.is_dir()
            test_file = tmp / "test.txt"
            test_file.write_text("test")
            assert test_file.exists()

        # Directory should be cleaned up
        assert not tmp.exists()

    def test_cleanup_all(self):
        """Test cleanup_all."""
        config = PipelineConfig(
            paths=PathsConfig(
                input_dir=Path("/input"),
                output_dir=Path("/output"),
            )
        )
        rm = ResourceManager(config)

        tmp1 = None
        tmp2 = None
        with rm.temp_dir() as tmp:
            tmp1 = tmp
            with rm.temp_dir() as tmp:
                tmp2 = tmp
                assert tmp1.exists()
                assert tmp2.exists()

        rm.cleanup_all()
        # Already cleaned up by context manager, but verify
        assert not tmp1.exists()
        assert not tmp2.exists()


class TestPipelineConfig:
    """Test PipelineConfig."""

    def test_from_dict(self):
        """Test loading config from dictionary."""
        data = {
            "paths": {
                "input_dir": "/input",
                "output_dir": "/output",
            },
            "conversion": {
                "writer": "auto",
                "max_workers": 8,
            },
        }
        config = PipelineConfig.from_dict(data)

        assert config.paths.input_dir == Path("/input")
        assert config.paths.output_dir == Path("/output")
        assert config.conversion.writer == "auto"
        assert config.conversion.max_workers == 8

    def test_legacy_format(self):
        """Test loading legacy format (flat structure)."""
        data = {
            "input_dir": "/input",
            "output_dir": "/output",
            "writer": "auto",
            "max_workers": 4,
        }
        config = PipelineConfig.from_dict(data)

        assert config.paths.input_dir == Path("/input")
        assert config.paths.output_dir == Path("/output")
        assert config.conversion.writer == "auto"
        assert config.conversion.max_workers == 4


class TestPipelineOrchestrator:
    """Test PipelineOrchestrator."""

    def test_simple_execution(self):
        """Test simple pipeline execution."""
        config = PipelineConfig(
            paths=PathsConfig(
                input_dir=Path("/input"),
                output_dir=Path("/output"),
            )
        )
        context = PipelineContext(config=config)

        stage1 = MockStage("stage1")
        stage2 = MockStage("stage2")

        stages = [
            StageDefinition("stage1", stage1, []),
            StageDefinition("stage2", stage2, ["stage1"]),
        ]

        orchestrator = PipelineOrchestrator(stages)
        result = orchestrator.execute(context)

        assert result.status == PipelineStatus.COMPLETED
        assert "stage1_output" in result.context.outputs
        assert "stage2_output" in result.context.outputs
        assert result.stage_results["stage1"].status == StageStatus.COMPLETED
        assert result.stage_results["stage2"].status == StageStatus.COMPLETED

    def test_dependency_resolution(self):
        """Test dependency resolution."""
        config = PipelineConfig(
            paths=PathsConfig(
                input_dir=Path("/input"),
                output_dir=Path("/output"),
            )
        )
        context = PipelineContext(config=config)

        # Create stages out of order
        stages = [
            StageDefinition("stage3", MockStage("stage3"), ["stage2"]),
            StageDefinition("stage1", MockStage("stage1"), []),
            StageDefinition("stage2", MockStage("stage2"), ["stage1"]),
        ]

        orchestrator = PipelineOrchestrator(stages)
        result = orchestrator.execute(context)

        # Should execute in correct order: stage1 -> stage2 -> stage3
        assert result.status == PipelineStatus.COMPLETED
        execution_order = list(result.stage_results.keys())
        assert execution_order == ["stage1", "stage2", "stage3"]

    def test_retry_policy(self):
        """Test retry policy."""
        config = PipelineConfig(
            paths=PathsConfig(
                input_dir=Path("/input"),
                output_dir=Path("/output"),
            )
        )
        context = PipelineContext(config=config)

        # Stage that fails twice then succeeds
        stage = MockStage("retry_stage", should_fail=True, fail_count=2)
        retry_policy = RetryPolicy(
            max_attempts=3,
            strategy=RetryStrategy.IMMEDIATE,
        )

        stages = [
            StageDefinition("retry_stage", stage, [], retry_policy=retry_policy),
        ]

        orchestrator = PipelineOrchestrator(stages)
        result = orchestrator.execute(context)

        # Should succeed after retries
        assert result.status == PipelineStatus.COMPLETED
        assert result.stage_results["retry_stage"].attempt == 3

    def test_circular_dependency(self):
        """Test circular dependency detection."""
        config = PipelineConfig(
            paths=PathsConfig(
                input_dir=Path("/input"),
                output_dir=Path("/output"),
            )
        )
        context = PipelineContext(config=config)

        stages = [
            StageDefinition("stage1", MockStage("stage1"), ["stage2"]),
            StageDefinition("stage2", MockStage("stage2"), ["stage1"]),
        ]

        orchestrator = PipelineOrchestrator(stages)

        with pytest.raises(ValueError, match="Circular dependency"):
            orchestrator.execute(context)


class TestWorkflowBuilder:
    """Test WorkflowBuilder."""

    def test_build_workflow(self):
        """Test building a workflow."""
        config = PipelineConfig(
            paths=PathsConfig(
                input_dir=Path("/input"),
                output_dir=Path("/output"),
            )
        )
        context = PipelineContext(config=config)

        workflow = (
            WorkflowBuilder()
            .add_stage("stage1", MockStage("stage1"))
            .add_stage("stage2", MockStage("stage2"), depends_on=["stage1"])
            .build()
        )

        result = workflow.execute(context)
        assert result.status == PipelineStatus.COMPLETED


class TestRetryPolicy:
    """Test RetryPolicy."""

    def test_exponential_backoff(self):
        """Test exponential backoff."""
        policy = RetryPolicy(
            max_attempts=5,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            initial_delay=1.0,
            max_delay=10.0,
        )

        assert policy.get_delay(1) == 1.0
        assert policy.get_delay(2) == 2.0
        assert policy.get_delay(3) == 4.0
        assert policy.get_delay(4) == 8.0
        assert policy.get_delay(5) == 10.0  # Capped at max_delay

    def test_should_retry(self):
        """Test should_retry logic."""
        policy = RetryPolicy(max_attempts=3)

        assert policy.should_retry(1, ValueError("test"))
        assert policy.should_retry(2, ValueError("test"))
        assert not policy.should_retry(3, ValueError("test"))
        assert not policy.should_retry(4, ValueError("test"))
