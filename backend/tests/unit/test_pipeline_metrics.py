"""
Unit tests for pipeline metrics module.

Tests:
- StageTimingMetrics calculations
- MemoryMetrics tracking
- ThroughputMetrics computation
- JobMetrics tracking
- PipelineMetricsCollector operations
- Stage context manager
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from dsa110_contimg.monitoring.pipeline_metrics import (
    GPUUtilizationMetrics,
    JobMetrics,
    MemoryMetrics,
    PipelineMetricsCollector,
    PipelineStage,
    ProcessingMode,
    StageContext,
    StageTimingMetrics,
    ThroughputMetrics,
    close_metrics_collector,
    get_metrics_collector,
    record_memory_sample,
    record_stage_timing,
)


# =============================================================================
# StageTimingMetrics Tests
# =============================================================================


class TestStageTimingMetrics:
    """Tests for StageTimingMetrics."""

    def test_default_values(self):
        """Test default timing values."""
        timing = StageTimingMetrics(stage=PipelineStage.IMAGING)
        assert timing.total_time_s == 0.0
        assert timing.cpu_time_s == 0.0
        assert timing.gpu_time_s == 0.0
        assert timing.io_time_s == 0.0
        assert timing.idle_time_s == 0.0

    def test_gpu_fraction_calculation(self):
        """Test GPU fraction calculation."""
        timing = StageTimingMetrics(
            stage=PipelineStage.IMAGING,
            total_time_s=10.0,
            gpu_time_s=7.0,
        )
        assert timing.gpu_fraction == 0.7

    def test_gpu_fraction_zero_total(self):
        """Test GPU fraction with zero total time."""
        timing = StageTimingMetrics(stage=PipelineStage.IMAGING, total_time_s=0.0)
        assert timing.gpu_fraction == 0.0

    def test_speedup_ratio(self):
        """Test speedup ratio calculation."""
        timing = StageTimingMetrics(
            stage=PipelineStage.IMAGING,
            total_time_s=10.0,
            cpu_time_s=2.0,
            gpu_time_s=3.0,
        )
        # (2 + 3) / 10 = 0.5
        assert timing.speedup_ratio == 0.5

    def test_to_dict(self):
        """Test dictionary serialization."""
        timing = StageTimingMetrics(
            stage=PipelineStage.CALIBRATION_APPLY,
            total_time_s=5.5,
            cpu_time_s=1.5,
            gpu_time_s=3.0,
            io_time_s=0.5,
            idle_time_s=0.5,
        )

        d = timing.to_dict()
        assert d["stage"] == "calibration_apply"
        assert d["total_time_s"] == 5.5
        assert d["gpu_fraction"] == pytest.approx(3.0 / 5.5, rel=0.01)


# =============================================================================
# MemoryMetrics Tests
# =============================================================================


class TestMemoryMetrics:
    """Tests for MemoryMetrics."""

    def test_initial_values(self):
        """Test initial memory values."""
        mem = MemoryMetrics()
        assert mem.peak_ram_gb == 0.0
        assert mem.peak_gpu_mem_gb == 0.0
        assert mem.average_ram_gb == 0.0
        assert mem.samples == 0

    def test_update_peaks(self):
        """Test peak tracking."""
        mem = MemoryMetrics()

        mem.update(ram_gb=4.0, gpu_mem_gb=2.0)
        mem.update(ram_gb=6.0, gpu_mem_gb=3.0)
        mem.update(ram_gb=5.0, gpu_mem_gb=1.0)

        assert mem.peak_ram_gb == 6.0
        assert mem.peak_gpu_mem_gb == 3.0

    def test_update_averages(self):
        """Test running average calculation."""
        mem = MemoryMetrics()

        mem.update(ram_gb=4.0)
        mem.update(ram_gb=6.0)

        # After 2 samples: running average should be around 5.0
        assert 4.5 <= mem.average_ram_gb <= 5.5
        assert mem.samples == 2

    def test_to_dict(self):
        """Test dictionary serialization."""
        mem = MemoryMetrics(
            peak_ram_gb=8.0,
            peak_gpu_mem_gb=4.0,
            average_ram_gb=6.0,
            average_gpu_mem_gb=3.0,
        )

        d = mem.to_dict()
        assert d["peak_ram_gb"] == 8.0
        assert d["peak_gpu_mem_gb"] == 4.0


# =============================================================================
# ThroughputMetrics Tests
# =============================================================================


class TestThroughputMetrics:
    """Tests for ThroughputMetrics."""

    def test_to_dict(self):
        """Test dictionary serialization."""
        throughput = ThroughputMetrics(
            ms_processed=100,
            ms_per_hour=25.0,
            bytes_processed=1_000_000_000,
            gb_per_hour=0.25,
            time_window_hours=4.0,
        )

        d = throughput.to_dict()
        assert d["ms_processed"] == 100
        assert d["ms_per_hour"] == 25.0
        assert d["gb_per_hour"] == 0.25


# =============================================================================
# JobMetrics Tests
# =============================================================================


class TestJobMetrics:
    """Tests for JobMetrics."""

    def test_creation(self):
        """Test job metrics creation."""
        job = JobMetrics(ms_path="/data/test.ms")

        assert job.ms_path == "/data/test.ms"
        assert job.started_at > 0
        assert job.ended_at is None
        assert not job.is_complete

    def test_duration_active(self):
        """Test duration for active job."""
        job = JobMetrics(ms_path="/data/test.ms")
        job.started_at = time.time() - 10.0  # Started 10s ago

        assert 9.9 <= job.duration_s <= 10.5

    def test_duration_complete(self):
        """Test duration for completed job."""
        job = JobMetrics(ms_path="/data/test.ms")
        job.started_at = 1000.0
        job.ended_at = 1015.0

        assert job.duration_s == 15.0
        assert job.is_complete

    def test_get_timing(self):
        """Test getting/creating timing metrics."""
        job = JobMetrics(ms_path="/data/test.ms")

        timing = job.get_timing(PipelineStage.IMAGING)
        assert timing.stage == PipelineStage.IMAGING

        # Same object returned on second call
        timing2 = job.get_timing(PipelineStage.IMAGING)
        assert timing is timing2

    def test_to_dict(self):
        """Test dictionary serialization."""
        job = JobMetrics(ms_path="/data/test.ms")
        job.success = True
        job.ended_at = time.time()

        timing = job.get_timing(PipelineStage.IMAGING)
        timing.gpu_time_s = 5.0

        d = job.to_dict()
        assert d["ms_path"] == "/data/test.ms"
        assert d["success"] is True
        assert "imaging" in d["stage_timings"]


# =============================================================================
# GPUUtilizationMetrics Tests
# =============================================================================


class TestGPUUtilizationMetrics:
    """Tests for GPUUtilizationMetrics."""

    def test_creation(self):
        """Test creation with values."""
        metric = GPUUtilizationMetrics(
            gpu_id=0,
            utilization_pct=75.0,
            memory_utilization_pct=60.0,
        )

        assert metric.gpu_id == 0
        assert metric.utilization_pct == 75.0
        assert metric.memory_utilization_pct == 60.0
        assert metric.timestamp > 0


# =============================================================================
# PipelineMetricsCollector Tests
# =============================================================================


class TestPipelineMetricsCollector:
    """Tests for PipelineMetricsCollector."""

    @pytest.fixture
    def collector(self):
        """Create a fresh collector for each test."""
        return PipelineMetricsCollector()

    def test_start_job(self, collector):
        """Test starting job tracking."""
        job = collector.start_job("/data/test.ms")

        assert job.ms_path == "/data/test.ms"
        assert not job.is_complete

    def test_end_job(self, collector):
        """Test ending job tracking."""
        collector.start_job("/data/test.ms")

        job = collector.end_job("/data/test.ms", success=True, size_bytes=1_000_000)

        assert job is not None
        assert job.is_complete
        assert job.success is True

    def test_end_job_not_found(self, collector):
        """Test ending job that doesn't exist."""
        job = collector.end_job("/data/nonexistent.ms", success=True)
        assert job is None

    def test_get_job_active(self, collector):
        """Test getting active job."""
        collector.start_job("/data/test.ms")

        job = collector.get_job("/data/test.ms")
        assert job is not None
        assert job.ms_path == "/data/test.ms"

    def test_get_job_completed(self, collector):
        """Test getting completed job from history."""
        collector.start_job("/data/test.ms")
        collector.end_job("/data/test.ms", success=True)

        job = collector.get_job("/data/test.ms")
        assert job is not None
        assert job.is_complete

    def test_stage_context(self, collector):
        """Test stage context manager."""
        collector.start_job("/data/test.ms")

        with collector.stage_context("imaging", "/data/test.ms") as ctx:
            ctx.record_cpu_time(1.0)
            ctx.record_gpu_time(3.0)
            time.sleep(0.01)  # Some actual time passes

        job = collector.get_job("/data/test.ms")
        timing = job.get_timing(PipelineStage.IMAGING)

        assert timing.cpu_time_s == 1.0
        assert timing.gpu_time_s == 3.0
        assert timing.total_time_s >= 0.01

    def test_stage_context_memory_recording(self, collector):
        """Test recording memory in stage context."""
        collector.start_job("/data/test.ms")

        with collector.stage_context("imaging", "/data/test.ms") as ctx:
            ctx.record_memory(ram_gb=4.0, gpu_mem_gb=2.0)
            ctx.record_memory(ram_gb=6.0, gpu_mem_gb=4.0)

        job = collector.get_job("/data/test.ms")
        assert job.memory.peak_ram_gb == 6.0
        assert job.memory.peak_gpu_mem_gb == 4.0

    def test_get_throughput(self, collector):
        """Test throughput calculation."""
        # Add several completed jobs
        for i in range(5):
            collector.start_job(f"/data/test{i}.ms")
            collector.end_job(f"/data/test{i}.ms", success=True, size_bytes=1_000_000_000)

        throughput = collector.get_throughput(hours=1.0)

        assert throughput.ms_processed == 5
        assert throughput.ms_per_hour == 5.0
        assert throughput.bytes_processed == 5_000_000_000

    def test_get_stage_gpu_utilization(self, collector):
        """Test GPU utilization tracking by stage."""
        collector._record_gpu_utilization(PipelineStage.IMAGING, 75.0)
        collector._record_gpu_utilization(PipelineStage.IMAGING, 85.0)

        util = collector.get_stage_gpu_utilization(PipelineStage.IMAGING)
        assert util["imaging"] == 80.0  # Average

    def test_get_stage_timing_summary(self, collector):
        """Test stage timing aggregation."""
        for i in range(3):
            collector.start_job(f"/data/test{i}.ms")
            with collector.stage_context("imaging", f"/data/test{i}.ms") as ctx:
                ctx.record_gpu_time(2.0)
            collector.end_job(f"/data/test{i}.ms", success=True)

        summary = collector.get_stage_timing_summary(hours=1.0)

        assert "imaging" in summary
        assert summary["imaging"]["gpu_time_s"] == 6.0  # 3 jobs x 2.0s

    def test_get_memory_high_water_marks(self, collector):
        """Test memory high-water mark tracking."""
        for ram in [4.0, 8.0, 6.0]:
            collector.start_job(f"/data/test{ram}.ms")
            job = collector.get_job(f"/data/test{ram}.ms")
            job.memory.update(ram_gb=ram, gpu_mem_gb=ram / 2)
            collector.end_job(f"/data/test{ram}.ms", success=True)

        marks = collector.get_memory_high_water_marks(hours=1.0)

        assert marks["peak_ram_gb"] == 8.0
        assert marks["peak_gpu_mem_gb"] == 4.0

    def test_get_summary(self, collector):
        """Test comprehensive summary."""
        for i in range(2):
            collector.start_job(f"/data/test{i}.ms")
            collector.end_job(f"/data/test{i}.ms", success=True)

        summary = collector.get_summary(hours=1.0)

        assert summary["jobs_completed"] == 2
        assert summary["success_rate"] == 1.0
        assert "throughput" in summary
        assert "memory_high_water_marks" in summary

    def test_get_active_jobs(self, collector):
        """Test listing active jobs."""
        collector.start_job("/data/active1.ms")
        collector.start_job("/data/active2.ms")

        active = collector.get_active_jobs()

        assert len(active) == 2
        paths = [j["ms_path"] for j in active]
        assert "/data/active1.ms" in paths
        assert "/data/active2.ms" in paths

    def test_get_recent_jobs(self, collector):
        """Test listing recent completed jobs."""
        for i in range(5):
            collector.start_job(f"/data/test{i}.ms")
            collector.end_job(f"/data/test{i}.ms", success=(i % 2 == 0))

        recent = collector.get_recent_jobs(limit=3)
        assert len(recent) == 3

        success_only = collector.get_recent_jobs(limit=10, success_only=True)
        assert len(success_only) == 3  # 0, 2, 4 succeeded


# =============================================================================
# Singleton Tests
# =============================================================================


class TestSingleton:
    """Tests for singleton access."""

    def test_get_metrics_collector_singleton(self):
        """Test singleton pattern."""
        close_metrics_collector()  # Reset

        c1 = get_metrics_collector()
        c2 = get_metrics_collector()

        assert c1 is c2

        close_metrics_collector()  # Cleanup

    def test_close_metrics_collector(self):
        """Test closing singleton."""
        close_metrics_collector()

        c1 = get_metrics_collector()
        close_metrics_collector()
        c2 = get_metrics_collector()

        assert c1 is not c2


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_record_stage_timing(self):
        """Test record_stage_timing function."""
        close_metrics_collector()
        collector = get_metrics_collector()

        record_stage_timing(
            ms_path="/data/test.ms",
            stage="imaging",
            cpu_time_s=1.0,
            gpu_time_s=3.0,
            total_time_s=5.0,
        )

        job = collector.get_job("/data/test.ms")
        assert job is not None

        timing = job.get_timing(PipelineStage.IMAGING)
        assert timing.cpu_time_s == 1.0
        assert timing.gpu_time_s == 3.0

        close_metrics_collector()

    def test_record_memory_sample(self):
        """Test record_memory_sample function."""
        close_metrics_collector()
        collector = get_metrics_collector()

        # First create the job
        collector.start_job("/data/test.ms")

        record_memory_sample(
            ms_path="/data/test.ms",
            ram_gb=8.0,
            gpu_mem_gb=4.0,
        )

        job = collector.get_job("/data/test.ms")
        assert job.memory.peak_ram_gb == 8.0
        assert job.memory.peak_gpu_mem_gb == 4.0

        close_metrics_collector()


# =============================================================================
# StageContext Tests
# =============================================================================


class TestStageContext:
    """Tests for StageContext helper."""

    def test_record_methods(self):
        """Test all recording methods."""
        collector = PipelineMetricsCollector()
        job = collector.start_job("/data/test.ms")

        ctx = StageContext(PipelineStage.IMAGING, job, collector)

        with ctx:
            ctx.record_cpu_time(1.0)
            ctx.record_gpu_time(2.0)
            ctx.record_io_time(0.5)
            ctx.record_memory(4.0, 2.0)
            ctx.record_gpu_utilization(0, 75.0, 60.0)

        timing = job.get_timing(PipelineStage.IMAGING)
        assert timing.cpu_time_s == 1.0
        assert timing.gpu_time_s == 2.0
        assert timing.io_time_s == 0.5

        assert job.memory.peak_ram_gb == 4.0


# =============================================================================
# Database Persistence Tests
# =============================================================================


class TestDatabasePersistence:
    """Tests for database persistence."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary database path."""
        return str(tmp_path / "test_metrics.db")

    def test_persist_job(self, temp_db):
        """Test job persistence to database."""
        collector = PipelineMetricsCollector(db_path=temp_db)

        collector.start_job("/data/test.ms")
        with collector.stage_context("imaging", "/data/test.ms") as ctx:
            ctx.record_gpu_time(2.5)
        collector.end_job("/data/test.ms", success=True)

        # Verify database was created and has data
        import sqlite3

        conn = sqlite3.connect(temp_db)
        cursor = conn.execute("SELECT COUNT(*) FROM pipeline_metrics")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1


# =============================================================================
# PipelineStage Enum Tests
# =============================================================================


class TestPipelineStageEnum:
    """Tests for PipelineStage enum."""

    def test_all_stages_defined(self):
        """Test all expected stages exist."""
        stages = [
            PipelineStage.CONVERSION,
            PipelineStage.RFI_FLAGGING,
            PipelineStage.CALIBRATION_SOLVE,
            PipelineStage.CALIBRATION_APPLY,
            PipelineStage.IMAGING,
            PipelineStage.QA,
            PipelineStage.TOTAL,
        ]
        assert len(stages) == 7

    def test_stage_values(self):
        """Test stage string values."""
        assert PipelineStage.IMAGING.value == "imaging"
        assert PipelineStage.RFI_FLAGGING.value == "rfi_flagging"
