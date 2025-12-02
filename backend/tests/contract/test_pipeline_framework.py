"""
Contract tests for the generic pipeline framework.

Tests the pipeline/base.py, executor.py, scheduler.py, and registry.py modules.
"""

import asyncio
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from dsa110_contimg.pipeline import (
    Job,
    JobConfig,
    JobResult,
    NotificationConfig,
    Pipeline,
    PipelineExecutor,
    PipelineRegistry,
    PipelineScheduler,
    RetryBackoff,
    RetryPolicy,
    get_job_registry,
    get_pipeline_registry,
    register_job,
    register_pipeline,
    reset_registries,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset registries before each test."""
    reset_registries()
    yield
    reset_registries()


@pytest.fixture
def temp_db():
    """Create a temporary database."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()


# =============================================================================
# Test Jobs for Testing
# =============================================================================


@dataclass
class SimpleJob(Job):
    """A simple test job."""
    
    job_type: str = "simple_job"
    value: int = 0
    config: Any = None  # Accept optional config from executor
    
    def execute(self) -> JobResult:
        return JobResult.ok(
            outputs={"doubled": self.value * 2},
            message=f"Doubled {self.value}"
        )


@dataclass
class FailingJob(Job):
    """A job that always fails."""
    
    job_type: str = "failing_job"
    error_msg: str = "Intentional failure"
    config: Any = None  # Accept optional config from executor
    
    def execute(self) -> JobResult:
        return JobResult.fail(self.error_msg)


@dataclass
class ChainedJob(Job):
    """A job that uses output from previous job."""
    
    job_type: str = "chained_job"
    input_value: int = 0
    config: Any = None  # Accept optional config from executor
    
    def execute(self) -> JobResult:
        return JobResult.ok(
            outputs={"result": self.input_value + 100},
            message=f"Added 100 to {self.input_value}"
        )


# =============================================================================
# Test JobResult
# =============================================================================


class TestJobResult:
    """Tests for JobResult dataclass."""
    
    def test_ok_creates_success_result(self):
        """JobResult.ok() creates a successful result."""
        result = JobResult.ok(outputs={"key": "value"}, message="Success!")
        
        assert result.success is True
        assert result.outputs == {"key": "value"}
        assert result.message == "Success!"
        assert result.error is None
    
    def test_ok_with_empty_outputs(self):
        """JobResult.ok() works with empty outputs."""
        result = JobResult.ok()
        
        assert result.success is True
        assert result.outputs == {}
        assert result.message == ""
    
    def test_fail_creates_failed_result(self):
        """JobResult.fail() creates a failed result."""
        result = JobResult.fail("Something went wrong")
        
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.outputs == {}


# =============================================================================
# Test RetryPolicy
# =============================================================================


class TestRetryPolicy:
    """Tests for RetryPolicy configuration."""
    
    def test_default_values(self):
        """RetryPolicy has sensible defaults."""
        policy = RetryPolicy()
        
        assert policy.max_retries == 2
        assert policy.backoff == RetryBackoff.EXPONENTIAL
        assert policy.initial_delay_seconds == 2.0
        assert policy.max_delay_seconds == 60.0
    
    def test_exponential_backoff_delays(self):
        """Exponential backoff calculates correct delays."""
        policy = RetryPolicy(
            max_retries=5,
            backoff=RetryBackoff.EXPONENTIAL,
            initial_delay_seconds=1.0,
            max_delay_seconds=30.0,
        )
        
        assert policy.get_delay(0) == 0  # First attempt, no delay
        assert policy.get_delay(1) == 1.0  # First retry: 1s
        assert policy.get_delay(2) == 2.0  # Second retry: 2s
        assert policy.get_delay(3) == 4.0  # Third retry: 4s
        assert policy.get_delay(4) == 8.0  # Fourth retry: 8s
    
    def test_fixed_backoff_delays(self):
        """Fixed backoff returns constant delay."""
        policy = RetryPolicy(
            backoff=RetryBackoff.FIXED,
            initial_delay_seconds=5.0,
        )
        
        assert policy.get_delay(0) == 0  # First attempt
        assert policy.get_delay(1) == 5.0
        assert policy.get_delay(2) == 5.0
        assert policy.get_delay(3) == 5.0
    
    def test_max_delay_cap(self):
        """Delays are capped at max_delay_seconds."""
        policy = RetryPolicy(
            backoff=RetryBackoff.EXPONENTIAL,
            initial_delay_seconds=10.0,
            max_delay_seconds=25.0,
        )
        
        # 10 * 2^5 = 320, but capped at 25
        assert policy.get_delay(6) == 25.0


# =============================================================================
# Test Job Base Class
# =============================================================================


class TestJobBase:
    """Tests for Job base class."""
    
    def test_simple_job_execution(self):
        """Simple job executes and returns result."""
        job = SimpleJob(value=5)
        result = job.execute()
        
        assert result.success is True
        assert result.outputs["doubled"] == 10
    
    def test_failing_job_execution(self):
        """Failing job returns failure result."""
        job = FailingJob(error_msg="Test error")
        result = job.execute()
        
        assert result.success is False
        assert result.error == "Test error"
    
    def test_to_absurd_params_excludes_private(self):
        """to_absurd_params() excludes private attributes."""
        job = SimpleJob(value=42)
        job._private = "hidden"
        
        params = job.to_absurd_params()
        
        assert "value" in params
        assert "job_type" in params
        assert "_private" not in params
    
    def test_validate_default_returns_true(self):
        """Default validate() returns True."""
        job = SimpleJob(value=1)
        is_valid, error = job.validate()
        
        assert is_valid is True
        assert error is None


# =============================================================================
# Test Pipeline Base Class
# =============================================================================


class SimplePipeline(Pipeline):
    """A simple test pipeline."""
    
    pipeline_name = "simple_pipeline"
    schedule = None
    
    def __init__(self, config=None, value: int = 10):
        self.value = value
        super().__init__(config)
    
    def build(self) -> None:
        self.add_job(
            SimpleJob,
            job_id="step1",
            params={"value": self.value},
        )
        self.add_job(
            ChainedJob,
            job_id="step2",
            params={"input_value": "${step1.doubled}"},
            dependencies=["step1"],
        )


class ScheduledPipeline(Pipeline):
    """A pipeline with a schedule."""
    
    pipeline_name = "scheduled_pipeline"
    schedule = "0 3 * * *"  # 3 AM daily
    
    def build(self) -> None:
        self.add_job(
            SimpleJob,
            job_id="job1",
            params={"value": 1},
        )


class TestPipelineBase:
    """Tests for Pipeline base class."""
    
    def test_pipeline_initialization(self):
        """Pipeline initializes with jobs from build()."""
        pipeline = SimplePipeline(value=5)
        
        assert pipeline.pipeline_name == "simple_pipeline"
        assert len(pipeline.jobs) == 2
    
    def test_pipeline_job_graph(self):
        """Pipeline builds correct job graph."""
        pipeline = SimplePipeline()
        
        job1 = pipeline.get_job("step1")
        job2 = pipeline.get_job("step2")
        
        assert job1 is not None
        assert job2 is not None
        assert job1.dependencies == []
        assert job2.dependencies == ["step1"]
    
    def test_pipeline_execution_order(self):
        """Pipeline computes correct execution order."""
        pipeline = SimplePipeline()
        
        order = pipeline.get_execution_order()
        
        assert order == ["step1", "step2"]
    
    def test_pipeline_retry_policy(self):
        """Pipeline configures retry policy."""
        pipeline = SimplePipeline()
        pipeline.set_retry_policy(max_retries=5, backoff="fixed")
        
        assert pipeline.retry_policy.max_retries == 5
        assert pipeline.retry_policy.backoff == RetryBackoff.FIXED
    
    def test_pipeline_notifications(self):
        """Pipeline configures notifications."""
        pipeline = SimplePipeline()
        pipeline.add_notification(
            on_failure="step2",
            channels=["email", "slack"],
            recipients=["admin@example.com"],
        )
        
        assert len(pipeline.notifications) == 1
        notif = pipeline.notifications[0]
        assert notif.job_id == "step2"
        assert "email" in notif.channels
    
    def test_pipeline_schedule_attribute(self):
        """Pipeline with schedule attribute is accessible."""
        pipeline = ScheduledPipeline()
        
        assert pipeline.schedule == "0 3 * * *"


# =============================================================================
# Test Job Registry
# =============================================================================


class TestJobRegistry:
    """Tests for JobRegistry."""
    
    def test_register_job_decorator(self):
        """@register_job decorator registers job."""
        @register_job
        @dataclass
        class TestJob(Job):
            job_type: str = "test_registry_job"
            
            def execute(self) -> JobResult:
                return JobResult.ok()
        
        registry = get_job_registry()
        assert "test_registry_job" in registry
    
    def test_get_registered_job(self):
        """Can retrieve registered job class."""
        @register_job
        @dataclass
        class AnotherJob(Job):
            job_type: str = "another_job"
            
            def execute(self) -> JobResult:
                return JobResult.ok()
        
        registry = get_job_registry()
        job_class = registry.get("another_job")
        
        assert job_class is AnotherJob
    
    def test_list_job_types(self):
        """Can list all registered job types."""
        @register_job
        @dataclass
        class JobA(Job):
            job_type: str = "job_a"
            def execute(self) -> JobResult:
                return JobResult.ok()
        
        @register_job
        @dataclass
        class JobB(Job):
            job_type: str = "job_b"
            def execute(self) -> JobResult:
                return JobResult.ok()
        
        registry = get_job_registry()
        types = registry.list_types()
        
        assert "job_a" in types
        assert "job_b" in types


# =============================================================================
# Test Pipeline Registry
# =============================================================================


class TestPipelineRegistry:
    """Tests for PipelineRegistry."""
    
    def test_register_pipeline_decorator(self):
        """@register_pipeline decorator registers pipeline."""
        @register_pipeline
        class TestPipeline(Pipeline):
            pipeline_name = "test_registry_pipeline"
            schedule = None
            
            def build(self) -> None:
                pass
        
        registry = get_pipeline_registry()
        assert "test_registry_pipeline" in registry
    
    def test_get_scheduled_pipelines(self):
        """Can get only scheduled pipelines."""
        @register_pipeline
        class ScheduledTest(Pipeline):
            pipeline_name = "scheduled_test"
            schedule = "0 * * * *"
            
            def build(self) -> None:
                pass
        
        @register_pipeline
        class UnscheduledTest(Pipeline):
            pipeline_name = "unscheduled_test"
            schedule = None
            
            def build(self) -> None:
                pass
        
        registry = get_pipeline_registry()
        scheduled = registry.get_scheduled()
        
        scheduled_names = [p.pipeline_name for p in scheduled]
        assert "scheduled_test" in scheduled_names
        assert "unscheduled_test" not in scheduled_names


# =============================================================================
# Test Pipeline Executor
# =============================================================================


class TestPipelineExecutor:
    """Tests for PipelineExecutor."""
    
    def test_executor_creates_tables(self, temp_db):
        """Executor creates tracking tables on init."""
        executor = PipelineExecutor(temp_db)
        
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        
        assert "pipeline_executions" in tables
        assert "pipeline_jobs" in tables
    
    @pytest.mark.asyncio
    async def test_executor_records_execution(self, temp_db):
        """Executor records execution in database."""
        executor = PipelineExecutor(temp_db)
        pipeline = SimplePipeline(value=5)
        
        execution_id = await executor.execute(pipeline)
        
        assert execution_id.startswith("simple_pipeline_")
        
        # Check database
        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM pipeline_executions WHERE execution_id = ?",
            (execution_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        assert row is not None
        assert row["pipeline_name"] == "simple_pipeline"
        assert row["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_executor_records_jobs(self, temp_db):
        """Executor records individual jobs in database."""
        executor = PipelineExecutor(temp_db)
        pipeline = SimplePipeline(value=5)
        
        execution_id = await executor.execute(pipeline)
        
        # Check database
        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM pipeline_jobs WHERE execution_id = ? ORDER BY created_at",
            (execution_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        assert len(rows) == 2
        assert rows[0]["job_id"] == "step1"
        assert rows[1]["job_id"] == "step2"
    
    @pytest.mark.asyncio
    async def test_executor_get_status(self, temp_db):
        """Executor can retrieve execution status."""
        executor = PipelineExecutor(temp_db)
        pipeline = SimplePipeline(value=5)
        
        execution_id = await executor.execute(pipeline)
        status = await executor.get_status(execution_id)
        
        assert status.execution_id == execution_id
        assert status.pipeline_name == "simple_pipeline"
        assert status.status == "running"
        assert len(status.jobs) == 2


# =============================================================================
# Test Pipeline Scheduler
# =============================================================================


class TestPipelineScheduler:
    """Tests for PipelineScheduler."""
    
    def test_scheduler_register_pipeline(self, temp_db):
        """Scheduler registers pipelines."""
        scheduler = PipelineScheduler(temp_db)
        scheduler.register(ScheduledPipeline)
        
        assert "scheduled_pipeline" in scheduler.pipelines
    
    def test_scheduler_rejects_unscheduled(self, temp_db):
        """Scheduler rejects pipelines without schedule."""
        scheduler = PipelineScheduler(temp_db)
        
        with pytest.raises(ValueError, match="no schedule defined"):
            scheduler.register(SimplePipeline)
    
    def test_scheduler_unregister(self, temp_db):
        """Scheduler can unregister pipelines."""
        scheduler = PipelineScheduler(temp_db)
        scheduler.register(ScheduledPipeline)
        scheduler.unregister("scheduled_pipeline")
        
        assert "scheduled_pipeline" not in scheduler.pipelines


# =============================================================================
# Test Mosaic Pipeline Integration
# =============================================================================


class TestMosaicPipelineV2:
    """Tests for the V2 mosaic pipelines using generic framework.
    
    Note: These tests don't use the reset_registry fixture because
    they're checking the pre-registered pipelines from module import.
    """
    
    @pytest.fixture(autouse=False)  # Don't use autouse reset
    def _no_reset(self):
        """Skip the autouse reset fixture for these tests."""
        pass
    
    def test_nightly_pipeline_v2_structure(self):
        """NightlyMosaicPipelineV2 has correct structure."""
        from dsa110_contimg.mosaic.pipeline import (
            MosaicPipelineConfig,
            NightlyMosaicPipelineV2,
        )
        
        # Create a minimal config
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MosaicPipelineConfig(
                database_path=Path(tmpdir) / "test.db",
                mosaic_dir=Path(tmpdir) / "mosaics",
            )
            
            pipeline = NightlyMosaicPipelineV2(config)
            
            assert pipeline.pipeline_name == "nightly_mosaic_v2"
            assert len(pipeline.jobs) == 3
            
            job_ids = [j.job_id for j in pipeline.jobs]
            assert "plan" in job_ids
            assert "build" in job_ids
            assert "qa" in job_ids
    
    def test_nightly_pipeline_v2_has_schedule(self):
        """NightlyMosaicPipelineV2 has correct schedule."""
        from dsa110_contimg.mosaic.pipeline import NightlyMosaicPipelineV2
        
        assert NightlyMosaicPipelineV2.schedule == "0 3 * * *"
    
    def test_on_demand_pipeline_v2_no_schedule(self):
        """OnDemandMosaicPipelineV2 has no schedule."""
        from dsa110_contimg.mosaic.pipeline import OnDemandMosaicPipelineV2
        
        assert OnDemandMosaicPipelineV2.schedule is None
    
    def test_on_demand_pipeline_v2_structure(self):
        """OnDemandMosaicPipelineV2 has correct structure."""
        from dsa110_contimg.mosaic.pipeline import (
            MosaicPipelineConfig,
            OnDemandMosaicPipelineV2,
        )
        
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MosaicPipelineConfig(
                database_path=Path(tmpdir) / "test.db",
                mosaic_dir=Path(tmpdir) / "mosaics",
            )
            
            pipeline = OnDemandMosaicPipelineV2(
                config=config,
                name="test_mosaic",
                start_time=1000000,
                end_time=1100000,
            )
            
            assert pipeline.pipeline_name == "on_demand_mosaic_v2"
            assert len(pipeline.jobs) == 3
    
    def test_mosaic_jobs_have_correct_types(self):
        """Mosaic jobs have correct job_type values."""
        from dsa110_contimg.mosaic.jobs import (
            MosaicBuildJob,
            MosaicPlanningJob,
            MosaicQAJob,
        )
        
        assert MosaicPlanningJob.job_type == "mosaic_planning"
        assert MosaicBuildJob.job_type == "mosaic_build"
        assert MosaicQAJob.job_type == "mosaic_qa"
