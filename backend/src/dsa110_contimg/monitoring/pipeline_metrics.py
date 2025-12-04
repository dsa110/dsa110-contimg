"""
Pipeline Metrics Module for DSA-110 Continuum Imaging.

Provides comprehensive metrics collection for pipeline operations:
- GPU utilization per pipeline stage
- Processing time breakdown (CPU vs GPU)
- Memory high-water marks per job
- Throughput metrics (MS/hour)

Usage:
    from dsa110_contimg.monitoring.pipeline_metrics import (
        PipelineMetrics, StageMetrics, get_metrics_collector
    )

    # Record stage execution
    with metrics.stage_context("imaging", ms_path) as stage:
        stage.record_gpu_time(2.5)
        stage.record_cpu_time(1.0)
        # ... processing ...

    # Get metrics summary
    summary = metrics.get_summary()
"""

from __future__ import annotations

import logging
import sqlite3
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Deque, Dict, Generator, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


# =============================================================================
# Metric Types
# =============================================================================


class PipelineStage(str, Enum):
    """Pipeline processing stages."""

    CONVERSION = "conversion"
    RFI_FLAGGING = "rfi_flagging"
    CALIBRATION_SOLVE = "calibration_solve"
    CALIBRATION_APPLY = "calibration_apply"
    IMAGING = "imaging"
    QA = "qa"
    TOTAL = "total"


class ProcessingMode(str, Enum):
    """Processing mode for timing breakdown."""

    CPU = "cpu"
    GPU = "gpu"
    IO = "io"
    IDLE = "idle"


# =============================================================================
# Metric Data Classes
# =============================================================================


@dataclass
class StageTimingMetrics:
    """Timing metrics for a pipeline stage.

    Attributes:
        stage: Pipeline stage name
        total_time_s: Total wall-clock time
        cpu_time_s: Time spent in CPU operations
        gpu_time_s: Time spent in GPU operations
        io_time_s: Time spent in I/O operations
        idle_time_s: Time spent waiting/idle
    """

    stage: PipelineStage
    total_time_s: float = 0.0
    cpu_time_s: float = 0.0
    gpu_time_s: float = 0.0
    io_time_s: float = 0.0
    idle_time_s: float = 0.0

    @property
    def gpu_fraction(self) -> float:
        """Fraction of time spent on GPU (0.0-1.0)."""
        if self.total_time_s <= 0:
            return 0.0
        return self.gpu_time_s / self.total_time_s

    @property
    def speedup_ratio(self) -> float:
        """Speedup ratio (CPU+GPU time / total time)."""
        compute_time = self.cpu_time_s + self.gpu_time_s
        if self.total_time_s <= 0 or compute_time <= 0:
            return 1.0
        return compute_time / self.total_time_s

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stage": self.stage.value,
            "total_time_s": round(self.total_time_s, 3),
            "cpu_time_s": round(self.cpu_time_s, 3),
            "gpu_time_s": round(self.gpu_time_s, 3),
            "io_time_s": round(self.io_time_s, 3),
            "idle_time_s": round(self.idle_time_s, 3),
            "gpu_fraction": round(self.gpu_fraction, 3),
        }


@dataclass
class MemoryMetrics:
    """Memory metrics for a job.

    Attributes:
        peak_ram_gb: Peak RAM usage in GB
        peak_gpu_mem_gb: Peak GPU memory usage in GB
        average_ram_gb: Average RAM usage
        average_gpu_mem_gb: Average GPU memory usage
    """

    peak_ram_gb: float = 0.0
    peak_gpu_mem_gb: float = 0.0
    average_ram_gb: float = 0.0
    average_gpu_mem_gb: float = 0.0
    samples: int = 0

    def update(self, ram_gb: float, gpu_mem_gb: float = 0.0) -> None:
        """Update metrics with new sample.

        Args:
            ram_gb: Current RAM usage in GB
            gpu_mem_gb: Current GPU memory usage in GB
        """
        self.peak_ram_gb = max(self.peak_ram_gb, ram_gb)
        self.peak_gpu_mem_gb = max(self.peak_gpu_mem_gb, gpu_mem_gb)

        # Running average
        self.samples += 1
        alpha = 1.0 / self.samples
        self.average_ram_gb = (1 - alpha) * self.average_ram_gb + alpha * ram_gb
        self.average_gpu_mem_gb = (
            (1 - alpha) * self.average_gpu_mem_gb + alpha * gpu_mem_gb
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "peak_ram_gb": round(self.peak_ram_gb, 3),
            "peak_gpu_mem_gb": round(self.peak_gpu_mem_gb, 3),
            "average_ram_gb": round(self.average_ram_gb, 3),
            "average_gpu_mem_gb": round(self.average_gpu_mem_gb, 3),
        }


@dataclass
class GPUUtilizationMetrics:
    """GPU utilization metrics.

    Attributes:
        gpu_id: GPU device ID
        utilization_pct: GPU compute utilization percentage
        memory_utilization_pct: GPU memory utilization percentage
        timestamp: Measurement timestamp
    """

    gpu_id: int
    utilization_pct: float
    memory_utilization_pct: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class ThroughputMetrics:
    """Throughput metrics.

    Attributes:
        ms_processed: Number of MS files processed
        ms_per_hour: Processing rate (MS per hour)
        bytes_processed: Total bytes processed
        gb_per_hour: Data throughput (GB per hour)
        time_window_hours: Time window for calculations
    """

    ms_processed: int = 0
    ms_per_hour: float = 0.0
    bytes_processed: int = 0
    gb_per_hour: float = 0.0
    time_window_hours: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ms_processed": self.ms_processed,
            "ms_per_hour": round(self.ms_per_hour, 2),
            "bytes_processed": self.bytes_processed,
            "gb_per_hour": round(self.gb_per_hour, 2),
            "time_window_hours": self.time_window_hours,
        }


@dataclass
class IngestRateMetrics:
    """Ingest (incoming data) rate metrics.

    Tracks rate of incoming subband groups vs processing rate
    to detect when the pipeline is falling behind.

    Attributes:
        groups_arrived: Number of subband groups that arrived
        groups_per_hour: Arrival rate (groups per hour)
        groups_processed: Number of groups successfully processed
        processed_per_hour: Processing rate (groups per hour)
        backlog_groups: Current backlog (arrived - processed)
        backlog_growing: True if backlog is increasing
        time_window_hours: Time window for calculations
    """

    groups_arrived: int = 0
    groups_per_hour: float = 0.0
    groups_processed: int = 0
    processed_per_hour: float = 0.0
    backlog_groups: int = 0
    backlog_growing: bool = False
    time_window_hours: float = 1.0

    @property
    def rate_ratio(self) -> float:
        """Ratio of processing rate to arrival rate.

        Returns:
            >1.0 means pipeline is keeping up
            <1.0 means pipeline is falling behind
        """
        if self.groups_per_hour <= 0:
            return float("inf")  # No incoming data
        return self.processed_per_hour / self.groups_per_hour

    @property
    def is_keeping_up(self) -> bool:
        """Check if pipeline is keeping up with incoming data."""
        return self.rate_ratio >= 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "groups_arrived": self.groups_arrived,
            "groups_per_hour": round(self.groups_per_hour, 2),
            "groups_processed": self.groups_processed,
            "processed_per_hour": round(self.processed_per_hour, 2),
            "backlog_groups": self.backlog_groups,
            "backlog_growing": self.backlog_growing,
            "rate_ratio": round(self.rate_ratio, 2) if self.rate_ratio != float("inf") else None,
            "is_keeping_up": self.is_keeping_up,
            "time_window_hours": self.time_window_hours,
        }


@dataclass
class JobMetrics:
    """Complete metrics for a single job.

    Attributes:
        ms_path: Path to MS being processed
        started_at: Job start timestamp
        ended_at: Job end timestamp (None if in progress)
        stage_timings: Timing breakdown by stage
        memory: Memory metrics
        success: Whether job succeeded
        error_message: Error if failed
    """

    ms_path: str
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    stage_timings: Dict[PipelineStage, StageTimingMetrics] = field(default_factory=dict)
    memory: MemoryMetrics = field(default_factory=MemoryMetrics)
    success: Optional[bool] = None
    error_message: Optional[str] = None

    @property
    def duration_s(self) -> float:
        """Total job duration in seconds."""
        end = self.ended_at or time.time()
        return end - self.started_at

    @property
    def is_complete(self) -> bool:
        """Whether job has completed."""
        return self.ended_at is not None

    def get_timing(self, stage: PipelineStage) -> StageTimingMetrics:
        """Get or create timing metrics for stage."""
        if stage not in self.stage_timings:
            self.stage_timings[stage] = StageTimingMetrics(stage=stage)
        return self.stage_timings[stage]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ms_path": self.ms_path,
            "started_at": datetime.fromtimestamp(self.started_at).isoformat(),
            "ended_at": (
                datetime.fromtimestamp(self.ended_at).isoformat()
                if self.ended_at
                else None
            ),
            "duration_s": round(self.duration_s, 3),
            "success": self.success,
            "error_message": self.error_message,
            "stage_timings": {
                k.value: v.to_dict() for k, v in self.stage_timings.items()
            },
            "memory": self.memory.to_dict(),
        }


# =============================================================================
# Stage Context Manager
# =============================================================================


class StageContext:
    """Context manager for tracking stage metrics.

    Usage:
        with metrics.stage_context("imaging", ms_path) as stage:
            stage.record_gpu_time(2.5)
            stage.record_cpu_time(1.0)
            # ... processing ...
    """

    def __init__(
        self,
        stage: PipelineStage,
        job_metrics: JobMetrics,
        collector: PipelineMetricsCollector,
    ):
        self.stage = stage
        self.job_metrics = job_metrics
        self.collector = collector
        self.timing = job_metrics.get_timing(stage)
        self._start_time = 0.0
        self._gpu_samples: List[GPUUtilizationMetrics] = []

    def __enter__(self) -> StageContext:
        self._start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.timing.total_time_s = time.time() - self._start_time

        # Calculate idle time as remainder
        compute_time = (
            self.timing.cpu_time_s + self.timing.gpu_time_s + self.timing.io_time_s
        )
        self.timing.idle_time_s = max(0, self.timing.total_time_s - compute_time)

        # Record GPU samples
        if self._gpu_samples:
            avg_util = sum(s.utilization_pct for s in self._gpu_samples) / len(
                self._gpu_samples
            )
            self.collector._record_gpu_utilization(self.stage, avg_util)

    def record_cpu_time(self, seconds: float) -> None:
        """Record CPU processing time.

        Args:
            seconds: Time spent in CPU operations
        """
        self.timing.cpu_time_s += seconds

    def record_gpu_time(self, seconds: float) -> None:
        """Record GPU processing time.

        Args:
            seconds: Time spent in GPU operations
        """
        self.timing.gpu_time_s += seconds

    def record_io_time(self, seconds: float) -> None:
        """Record I/O time.

        Args:
            seconds: Time spent in I/O operations
        """
        self.timing.io_time_s += seconds

    def record_memory(self, ram_gb: float, gpu_mem_gb: float = 0.0) -> None:
        """Record memory sample.

        Args:
            ram_gb: Current RAM usage in GB
            gpu_mem_gb: Current GPU memory usage in GB
        """
        self.job_metrics.memory.update(ram_gb, gpu_mem_gb)

    def record_gpu_utilization(self, gpu_id: int, util_pct: float, mem_pct: float) -> None:
        """Record GPU utilization sample.

        Args:
            gpu_id: GPU device ID
            util_pct: GPU compute utilization percentage
            mem_pct: GPU memory utilization percentage
        """
        self._gpu_samples.append(
            GPUUtilizationMetrics(
                gpu_id=gpu_id,
                utilization_pct=util_pct,
                memory_utilization_pct=mem_pct,
            )
        )


# =============================================================================
# Metrics Collector
# =============================================================================


class PipelineMetricsCollector:
    """Collects and aggregates pipeline metrics.

    Thread-safe collector for recording metrics from multiple
    concurrent pipeline jobs.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        history_size: int = 1000,
    ):
        """Initialize metrics collector.

        Args:
            db_path: Path for persistent metrics storage (optional)
            history_size: Number of completed jobs to keep in memory
        """
        self.db_path = db_path
        self._lock = Lock()
        self._active_jobs: Dict[str, JobMetrics] = {}
        self._completed_jobs: Deque[JobMetrics] = deque(maxlen=history_size)
        self._stage_gpu_utilization: Dict[PipelineStage, List[float]] = defaultdict(list)
        self._throughput_timestamps: Deque[Tuple[float, int]] = deque(maxlen=1000)
        # Track incoming data arrivals for backlog monitoring
        self._ingest_timestamps: Deque[Tuple[float, str]] = deque(maxlen=2000)
        self._previous_backlog: int = 0  # For tracking if backlog is growing

        if db_path:
            self._init_db()

    def _init_db(self) -> None:
        """Initialize database for persistent storage."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ms_path TEXT NOT NULL,
                started_at REAL NOT NULL,
                ended_at REAL,
                duration_s REAL,
                success INTEGER,
                error_message TEXT,
                stage_timings_json TEXT,
                memory_json TEXT,
                created_at REAL DEFAULT (unixepoch())
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_metrics_ms ON pipeline_metrics(ms_path)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_metrics_started ON pipeline_metrics(started_at)
        """)
        conn.commit()
        conn.close()

    def start_job(self, ms_path: str) -> JobMetrics:
        """Start tracking a new job.

        Args:
            ms_path: Path to MS being processed

        Returns:
            JobMetrics instance for the job
        """
        with self._lock:
            job = JobMetrics(ms_path=ms_path)
            self._active_jobs[ms_path] = job
            logger.debug("Started metrics tracking for %s", ms_path)
            return job

    def end_job(
        self,
        ms_path: str,
        success: bool,
        error_message: Optional[str] = None,
        size_bytes: int = 0,
    ) -> Optional[JobMetrics]:
        """End tracking for a job.

        Args:
            ms_path: Path to MS
            success: Whether job succeeded
            error_message: Error message if failed
            size_bytes: Size of MS file for throughput calculation

        Returns:
            Completed JobMetrics or None if not found
        """
        with self._lock:
            job = self._active_jobs.pop(ms_path, None)
            if not job:
                return None

            job.ended_at = time.time()
            job.success = success
            job.error_message = error_message

            self._completed_jobs.append(job)
            self._throughput_timestamps.append((time.time(), size_bytes))

            logger.debug(
                "Ended metrics for %s: success=%s, duration=%.1fs",
                ms_path,
                success,
                job.duration_s,
            )

            if self.db_path:
                self._persist_job(job)

            return job

    def _persist_job(self, job: JobMetrics) -> None:
        """Persist job metrics to database."""
        import json

        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.execute(
                """
                INSERT INTO pipeline_metrics
                    (ms_path, started_at, ended_at, duration_s, success,
                     error_message, stage_timings_json, memory_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.ms_path,
                    job.started_at,
                    job.ended_at,
                    job.duration_s,
                    1 if job.success else 0,
                    job.error_message,
                    json.dumps(
                        {k.value: v.to_dict() for k, v in job.stage_timings.items()}
                    ),
                    json.dumps(job.memory.to_dict()),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Failed to persist metrics: %s", e)

    def get_job(self, ms_path: str) -> Optional[JobMetrics]:
        """Get metrics for a job (active or completed).

        Args:
            ms_path: Path to MS

        Returns:
            JobMetrics if found
        """
        with self._lock:
            if ms_path in self._active_jobs:
                return self._active_jobs[ms_path]

            for job in self._completed_jobs:
                if job.ms_path == ms_path:
                    return job

        return None

    @contextmanager
    def stage_context(
        self, stage: Union[str, PipelineStage], ms_path: str
    ) -> Generator[StageContext, None, None]:
        """Context manager for tracking stage execution.

        Args:
            stage: Pipeline stage name or enum
            ms_path: Path to MS being processed

        Yields:
            StageContext for recording metrics
        """
        if isinstance(stage, str):
            stage = PipelineStage(stage)

        job = self.get_job(ms_path)
        if not job:
            job = self.start_job(ms_path)

        ctx = StageContext(stage, job, self)
        with ctx:
            yield ctx

    def _record_gpu_utilization(
        self, stage: PipelineStage, utilization_pct: float
    ) -> None:
        """Record GPU utilization sample for stage."""
        with self._lock:
            samples = self._stage_gpu_utilization[stage]
            samples.append(utilization_pct)
            # Keep last 100 samples per stage
            if len(samples) > 100:
                samples.pop(0)

    def get_throughput(self, hours: float = 1.0) -> ThroughputMetrics:
        """Get throughput metrics for time window.

        Args:
            hours: Time window in hours

        Returns:
            ThroughputMetrics for the window
        """
        with self._lock:
            cutoff = time.time() - (hours * 3600)
            recent = [
                (ts, size)
                for ts, size in self._throughput_timestamps
                if ts >= cutoff
            ]

            ms_count = len(recent)
            total_bytes = sum(size for _, size in recent)

            return ThroughputMetrics(
                ms_processed=ms_count,
                ms_per_hour=ms_count / hours if hours > 0 else 0,
                bytes_processed=total_bytes,
                gb_per_hour=(total_bytes / 1e9) / hours if hours > 0 else 0,
                time_window_hours=hours,
            )

    def record_ingest(self, group_id: str) -> None:
        """Record arrival of a new subband group for ingest rate tracking.

        Call this when a new complete subband group arrives
        in the incoming directory.

        Args:
            group_id: Unique identifier for the subband group
        """
        with self._lock:
            self._ingest_timestamps.append((time.time(), group_id))

    def get_ingest_rate(self, hours: float = 1.0) -> IngestRateMetrics:
        """Get ingest rate metrics comparing incoming vs processed data.

        This helps detect when the pipeline is falling behind
        the incoming data rate.

        Args:
            hours: Time window in hours

        Returns:
            IngestRateMetrics showing arrival vs processing rates
        """
        with self._lock:
            cutoff = time.time() - (hours * 3600)

            # Count arrivals in window
            recent_arrivals = [
                (ts, gid)
                for ts, gid in self._ingest_timestamps
                if ts >= cutoff
            ]
            groups_arrived = len(recent_arrivals)
            groups_per_hour = groups_arrived / hours if hours > 0 else 0.0

            # Count processed in window
            recent_processed = [
                (ts, size)
                for ts, size in self._throughput_timestamps
                if ts >= cutoff
            ]
            groups_processed = len(recent_processed)
            processed_per_hour = groups_processed / hours if hours > 0 else 0.0

            # Calculate backlog
            # Total arrivals - total processed (since collector start)
            total_arrived = len(self._ingest_timestamps)
            total_processed = len(self._throughput_timestamps)
            backlog = max(0, total_arrived - total_processed)

            # Track if backlog is growing
            backlog_growing = backlog > self._previous_backlog
            self._previous_backlog = backlog

            return IngestRateMetrics(
                groups_arrived=groups_arrived,
                groups_per_hour=groups_per_hour,
                groups_processed=groups_processed,
                processed_per_hour=processed_per_hour,
                backlog_groups=backlog,
                backlog_growing=backlog_growing,
                time_window_hours=hours,
            )

    def get_stage_gpu_utilization(
        self, stage: Optional[PipelineStage] = None
    ) -> Dict[str, float]:
        """Get average GPU utilization by stage.

        Args:
            stage: Specific stage or None for all

        Returns:
            Dictionary of stage -> average utilization percentage
        """
        with self._lock:
            if stage:
                samples = self._stage_gpu_utilization.get(stage, [])
                if samples:
                    return {stage.value: sum(samples) / len(samples)}
                return {stage.value: 0.0}

            return {
                s.value: (sum(samples) / len(samples)) if samples else 0.0
                for s, samples in self._stage_gpu_utilization.items()
            }

    def get_stage_timing_summary(
        self, hours: float = 24.0
    ) -> Dict[str, Dict[str, float]]:
        """Get aggregated timing breakdown by stage.

        Args:
            hours: Time window in hours

        Returns:
            Dictionary of stage -> timing breakdown
        """
        cutoff = time.time() - (hours * 3600)
        stage_totals: Dict[PipelineStage, StageTimingMetrics] = {}

        with self._lock:
            for job in self._completed_jobs:
                if job.started_at < cutoff:
                    continue

                for stage, timing in job.stage_timings.items():
                    if stage not in stage_totals:
                        stage_totals[stage] = StageTimingMetrics(stage=stage)

                    stage_totals[stage].total_time_s += timing.total_time_s
                    stage_totals[stage].cpu_time_s += timing.cpu_time_s
                    stage_totals[stage].gpu_time_s += timing.gpu_time_s
                    stage_totals[stage].io_time_s += timing.io_time_s
                    stage_totals[stage].idle_time_s += timing.idle_time_s

        return {s.value: t.to_dict() for s, t in stage_totals.items()}

    def get_memory_high_water_marks(
        self, hours: float = 24.0
    ) -> Dict[str, float]:
        """Get memory high-water marks.

        Args:
            hours: Time window in hours

        Returns:
            Dictionary with peak RAM and GPU memory
        """
        cutoff = time.time() - (hours * 3600)
        peak_ram = 0.0
        peak_gpu = 0.0

        with self._lock:
            for job in self._completed_jobs:
                if job.started_at < cutoff:
                    continue
                peak_ram = max(peak_ram, job.memory.peak_ram_gb)
                peak_gpu = max(peak_gpu, job.memory.peak_gpu_mem_gb)

        return {
            "peak_ram_gb": round(peak_ram, 3),
            "peak_gpu_mem_gb": round(peak_gpu, 3),
        }

    def get_summary(self, hours: float = 24.0) -> Dict[str, Any]:
        """Get comprehensive metrics summary.

        Args:
            hours: Time window in hours

        Returns:
            Complete metrics summary
        """
        throughput = self.get_throughput(hours)
        gpu_util = self.get_stage_gpu_utilization()
        timing = self.get_stage_timing_summary(hours)
        memory = self.get_memory_high_water_marks(hours)

        # Calculate success rate
        cutoff = time.time() - (hours * 3600)
        with self._lock:
            recent_jobs = [j for j in self._completed_jobs if j.started_at >= cutoff]
            success_count = sum(1 for j in recent_jobs if j.success)
            total_count = len(recent_jobs)

        success_rate = success_count / total_count if total_count > 0 else 0.0

        # Get ingest rate metrics
        ingest_rate = self.get_ingest_rate(hours)

        return {
            "time_window_hours": hours,
            "jobs_completed": total_count,
            "success_rate": round(success_rate, 3),
            "throughput": throughput.to_dict(),
            "ingest_rate": ingest_rate.to_dict(),
            "gpu_utilization_by_stage": gpu_util,
            "timing_by_stage": timing,
            "memory_high_water_marks": memory,
            "active_jobs": len(self._active_jobs),
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get list of currently active jobs.

        Returns:
            List of active job summaries
        """
        with self._lock:
            return [
                {
                    "ms_path": job.ms_path,
                    "started_at": datetime.fromtimestamp(job.started_at).isoformat(),
                    "duration_s": job.duration_s,
                    "current_stage": (
                        list(job.stage_timings.keys())[-1].value
                        if job.stage_timings
                        else "starting"
                    ),
                }
                for job in self._active_jobs.values()
            ]

    def get_recent_jobs(
        self, limit: int = 50, success_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get recent completed jobs.

        Args:
            limit: Maximum jobs to return
            success_only: Only return successful jobs

        Returns:
            List of job summaries
        """
        with self._lock:
            jobs = list(self._completed_jobs)

        if success_only:
            jobs = [j for j in jobs if j.success]

        # Most recent first
        jobs = sorted(jobs, key=lambda j: j.ended_at or 0, reverse=True)

        return [j.to_dict() for j in jobs[:limit]]


# =============================================================================
# Singleton Access
# =============================================================================

_metrics_collector: Optional[PipelineMetricsCollector] = None
_metrics_lock = Lock()


def get_metrics_collector(
    db_path: Optional[str] = None,
) -> PipelineMetricsCollector:
    """Get or create singleton metrics collector.

    Args:
        db_path: Optional database path for persistence

    Returns:
        PipelineMetricsCollector singleton
    """
    global _metrics_collector

    with _metrics_lock:
        if _metrics_collector is None:
            _metrics_collector = PipelineMetricsCollector(db_path=db_path)
        return _metrics_collector


def close_metrics_collector() -> None:
    """Close singleton metrics collector."""
    global _metrics_collector

    with _metrics_lock:
        _metrics_collector = None


# =============================================================================
# Convenience Functions
# =============================================================================


def record_stage_timing(
    ms_path: str,
    stage: Union[str, PipelineStage],
    cpu_time_s: float = 0.0,
    gpu_time_s: float = 0.0,
    io_time_s: float = 0.0,
    total_time_s: float = 0.0,
) -> None:
    """Record timing for a pipeline stage.

    Convenience function for recording stage timing without context manager.

    Args:
        ms_path: Path to MS
        stage: Pipeline stage
        cpu_time_s: CPU time in seconds
        gpu_time_s: GPU time in seconds
        io_time_s: I/O time in seconds
        total_time_s: Total time (calculated if not provided)
    """
    if isinstance(stage, str):
        stage = PipelineStage(stage)

    collector = get_metrics_collector()
    job = collector.get_job(ms_path)

    if not job:
        job = collector.start_job(ms_path)

    timing = job.get_timing(stage)
    timing.cpu_time_s = cpu_time_s
    timing.gpu_time_s = gpu_time_s
    timing.io_time_s = io_time_s
    timing.total_time_s = total_time_s or (cpu_time_s + gpu_time_s + io_time_s)
    timing.idle_time_s = max(0, timing.total_time_s - cpu_time_s - gpu_time_s - io_time_s)


def record_memory_sample(
    ms_path: str,
    ram_gb: float,
    gpu_mem_gb: float = 0.0,
) -> None:
    """Record memory sample for a job.

    Args:
        ms_path: Path to MS
        ram_gb: Current RAM usage in GB
        gpu_mem_gb: Current GPU memory usage in GB
    """
    collector = get_metrics_collector()
    job = collector.get_job(ms_path)

    if job:
        job.memory.update(ram_gb, gpu_mem_gb)


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Enums
    "PipelineStage",
    "ProcessingMode",
    # Data Classes
    "StageTimingMetrics",
    "MemoryMetrics",
    "GPUUtilizationMetrics",
    "ThroughputMetrics",
    "JobMetrics",
    # Context Manager
    "StageContext",
    # Collector
    "PipelineMetricsCollector",
    "get_metrics_collector",
    "close_metrics_collector",
    # Convenience Functions
    "record_stage_timing",
    "record_memory_sample",
]
