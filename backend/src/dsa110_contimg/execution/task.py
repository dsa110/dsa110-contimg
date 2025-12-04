"""
Execution task and result dataclasses for unified execution paths.

This module provides standardized data structures for conversion tasks
and their results, ensuring consistent behavior between in-process
and subprocess execution modes.

Part of Issue #11: Subprocess vs In-Process Execution Consistency.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from .errors import ErrorCode


@dataclass
class ExecutionMetrics:
    """Performance metrics for an execution run.

    Attributes:
        load_time_s: Time spent loading UVH5 files
        phase_time_s: Time spent phasing visibilities
        write_time_s: Time spent writing MS
        total_time_s: Total wall-clock time
        memory_peak_mb: Peak memory usage in MB
        files_processed: Number of input files processed
        output_size_bytes: Size of output MS in bytes
    """

    load_time_s: float = 0.0
    phase_time_s: float = 0.0
    write_time_s: float = 0.0
    total_time_s: float = 0.0
    memory_peak_mb: float = 0.0
    files_processed: int = 0
    output_size_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "load_time_s": round(self.load_time_s, 3),
            "phase_time_s": round(self.phase_time_s, 3),
            "write_time_s": round(self.write_time_s, 3),
            "total_time_s": round(self.total_time_s, 3),
            "memory_peak_mb": round(self.memory_peak_mb, 1),
            "files_processed": self.files_processed,
            "output_size_bytes": self.output_size_bytes,
        }


@dataclass
class ResourceLimits:
    """Resource constraints for execution.

    These limits are enforced differently depending on execution mode:
    - Subprocess: Uses rlimit and optionally cgroups for hard enforcement
    - In-process: Uses thread pool limits and monitoring with soft enforcement

    Attributes:
        memory_mb: Maximum memory in MB (None = unlimited)
        cpu_seconds: Maximum CPU time in seconds (None = unlimited)
        omp_threads: Number of OpenMP threads
        mkl_threads: Number of MKL threads
        max_workers: Maximum ThreadPoolExecutor workers
        use_cgroups: Whether to use cgroups for subprocess isolation
        timeout_seconds: Maximum wall-clock time for execution
    """

    memory_mb: Optional[int] = None
    cpu_seconds: Optional[int] = None
    omp_threads: int = 4
    mkl_threads: int = 4
    max_workers: int = 4
    use_cgroups: bool = False
    timeout_seconds: Optional[int] = 600  # 10 minutes default

    def to_env_dict(self) -> Dict[str, str]:
        """Convert thread settings to environment variables."""
        return {
            "OMP_NUM_THREADS": str(self.omp_threads),
            "MKL_NUM_THREADS": str(self.mkl_threads),
            "OPENBLAS_NUM_THREADS": str(self.omp_threads),
            "NUMEXPR_NUM_THREADS": str(self.omp_threads),
        }


@dataclass
class ExecutionTask:
    """Encapsulates all inputs for a conversion job.

    This dataclass provides a unified interface for specifying
    conversion tasks, regardless of execution mode.

    Attributes:
        group_id: Unique identifier for the subband group
        input_dir: Directory containing input HDF5 files
        output_dir: Directory for output MS files
        scratch_dir: Directory for temporary files
        start_time: Start of time window (ISO format)
        end_time: End of time window (ISO format)
        writer: Writer type ("auto", "direct-subband", "parallel-subband")
        resource_limits: Resource constraints for execution
        organize_outputs: Whether to organize outputs into date hierarchy
        is_calibrator: Whether this is a calibrator observation (None = auto-detect)
        env_overrides: Additional environment variables
        stage_to_tmpfs: Whether to stage through tmpfs
        tmpfs_path: Path to tmpfs mount (default /dev/shm)
        rename_calibrator_fields: Whether to auto-rename calibrator fields
        use_interpolated_cal: Whether to use interpolated calibration
    """

    group_id: str
    input_dir: Path
    output_dir: Path
    scratch_dir: Path
    start_time: str
    end_time: str

    # Writer configuration
    writer: str = "auto"

    # Resource limits
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)

    # Path organization
    organize_outputs: bool = True
    is_calibrator: Optional[bool] = None  # Auto-detect if None

    # Environment
    env_overrides: Dict[str, str] = field(default_factory=dict)

    # Staging options
    stage_to_tmpfs: bool = False
    tmpfs_path: Path = field(default_factory=lambda: Path("/dev/shm"))

    # Calibration options
    rename_calibrator_fields: bool = True
    use_interpolated_cal: bool = True

    def __post_init__(self) -> None:
        """Validate and normalize paths after initialization."""
        # Convert string paths to Path objects
        if isinstance(self.input_dir, str):
            self.input_dir = Path(self.input_dir)
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
        if isinstance(self.scratch_dir, str):
            self.scratch_dir = Path(self.scratch_dir)
        if isinstance(self.tmpfs_path, str):
            self.tmpfs_path = Path(self.tmpfs_path)

    def validate(self) -> None:
        """Validate task inputs.

        Raises:
            ValueError: If any input is invalid
        """
        # Validate paths exist or can be created
        if not self.input_dir.exists():
            raise ValueError(f"Input directory does not exist: {self.input_dir}")

        # Validate time format (basic check)
        if not self.start_time or not self.end_time:
            raise ValueError("start_time and end_time are required")

        # Validate writer type
        valid_writers = {"auto", "direct-subband", "parallel-subband"}
        if self.writer not in valid_writers:
            raise ValueError(f"Invalid writer type: {self.writer}. Must be one of {valid_writers}")

        # Validate resource limits
        if self.resource_limits.max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        if self.resource_limits.max_workers > 128:
            raise ValueError("max_workers must be <= 128")

    def to_cli_args(self) -> list[str]:
        """Convert task to CLI arguments for subprocess execution.

        Returns:
            List of command-line arguments for the execution.cli convert command.
            This uses the modern execution CLI (not the deprecated conversion.cli).
        """
        args = [
            "--input-dir", str(self.input_dir.resolve()),
            "--output-dir", str(self.output_dir.resolve()),
            "--start-time", self.start_time,
            "--end-time", self.end_time,
            "--scratch-dir", str(self.scratch_dir.resolve()),
            "--writer", self.writer,
            "--group-id", self.group_id,
            # Force inprocess mode in subprocess - the subprocess itself runs in-process
            "--execution-mode", "inprocess",
        ]

        # Resource limits
        if self.resource_limits.memory_mb:
            args.extend(["--memory-mb", str(self.resource_limits.memory_mb)])
        if self.resource_limits.omp_threads:
            args.extend(["--omp-threads", str(self.resource_limits.omp_threads)])
        if self.resource_limits.max_workers:
            args.extend(["--max-workers", str(self.resource_limits.max_workers)])
        if self.resource_limits.timeout_seconds:
            args.extend(["--timeout", str(self.resource_limits.timeout_seconds)])

        return args

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization/logging."""
        return {
            "group_id": self.group_id,
            "input_dir": str(self.input_dir),
            "output_dir": str(self.output_dir),
            "scratch_dir": str(self.scratch_dir),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "writer": self.writer,
            "resource_limits": {
                "memory_mb": self.resource_limits.memory_mb,
                "omp_threads": self.resource_limits.omp_threads,
                "max_workers": self.resource_limits.max_workers,
                "timeout_seconds": self.resource_limits.timeout_seconds,
            },
            "organize_outputs": self.organize_outputs,
            "is_calibrator": self.is_calibrator,
            "stage_to_tmpfs": self.stage_to_tmpfs,
        }


@dataclass
class ExecutionResult:
    """Standardized result from any execution mode.

    This dataclass ensures that both in-process and subprocess
    execution modes return results in an identical format.

    Attributes:
        success: Whether execution completed successfully
        return_code: Exit code (0 = success, see ErrorCode for others)
        error_code: Canonical error code if failed
        error_message: Human-readable error description
        traceback: Full traceback if available
        ms_path: Path to output MS file
        final_paths: Dictionary of output paths by type
        metrics: Performance metrics
        execution_mode: "inprocess" or "subprocess"
        started_at: Unix timestamp when execution started
        ended_at: Unix timestamp when execution ended
        writer_type: Actual writer type used
    """

    success: bool
    return_code: int

    # Error details (if failed)
    error_code: Optional[ErrorCode] = None
    error_message: Optional[str] = None
    traceback: Optional[str] = None

    # Output paths (if successful)
    ms_path: Optional[Path] = None
    final_paths: Dict[str, Path] = field(default_factory=dict)

    # Performance metrics
    metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)

    # Execution metadata
    execution_mode: str = "unknown"
    started_at: float = field(default_factory=time.time)
    ended_at: float = 0.0
    writer_type: str = "unknown"

    @property
    def duration_seconds(self) -> float:
        """Calculate execution duration."""
        if self.ended_at > 0:
            return self.ended_at - self.started_at
        return time.time() - self.started_at

    @classmethod
    def success_result(
        cls,
        ms_path: Path,
        metrics: ExecutionMetrics,
        execution_mode: str = "unknown",
        writer_type: str = "unknown",
    ) -> "ExecutionResult":
        """Create a successful result.

        Args:
            ms_path: Path to output MS
            metrics: Execution metrics
            execution_mode: "inprocess" or "subprocess"
            writer_type: Writer type used

        Returns:
            ExecutionResult with success=True
        """
        return cls(
            success=True,
            return_code=0,
            ms_path=ms_path,
            final_paths={"ms": ms_path},
            metrics=metrics,
            execution_mode=execution_mode,
            writer_type=writer_type,
            ended_at=time.time(),
        )

    @classmethod
    def failure_result(
        cls,
        error_code: ErrorCode,
        error_message: str,
        traceback: Optional[str] = None,
        execution_mode: str = "unknown",
    ) -> "ExecutionResult":
        """Create a failure result.

        Args:
            error_code: Canonical error code
            error_message: Human-readable description
            traceback: Full traceback if available
            execution_mode: "inprocess" or "subprocess"

        Returns:
            ExecutionResult with success=False
        """
        return cls(
            success=False,
            return_code=error_code.value,
            error_code=error_code,
            error_message=error_message,
            traceback=traceback,
            execution_mode=execution_mode,
            ended_at=time.time(),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization/logging."""
        return {
            "success": self.success,
            "return_code": self.return_code,
            "error_code": self.error_code.name if self.error_code else None,
            "error_message": self.error_message,
            "ms_path": str(self.ms_path) if self.ms_path else None,
            "metrics": self.metrics.to_dict(),
            "execution_mode": self.execution_mode,
            "duration_seconds": round(self.duration_seconds, 3),
            "writer_type": self.writer_type,
        }
