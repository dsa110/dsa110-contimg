"""
Streaming converter adapter for the unified execution module.

This module provides adapters that allow the streaming converter to use
the unified execution interface while maintaining backward compatibility.

Part of Issue #11: Subprocess vs In-Process Execution Consistency.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dsa110_contimg.execution import (
    ErrorCode,
    ExecutionResult,
    ExecutionTask,
    InProcessExecutor,
    SubprocessExecutor,
    get_executor,
)
from dsa110_contimg.execution.task import ExecutionMetrics, ResourceLimits

logger = logging.getLogger(__name__)


def create_task_from_group(
    group_id: str,
    input_dir: Path,
    output_dir: Path,
    scratch_dir: Optional[Path] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    writer: str = "auto",
    max_workers: int = 4,
    stage_to_tmpfs: bool = False,
    tmpfs_path: str = "/dev/shm",
    omp_threads: Optional[int] = None,
    memory_mb: Optional[int] = None,
    timeout_seconds: Optional[float] = None,
    env_overrides: Optional[Dict[str, str]] = None,
) -> ExecutionTask:
    """Create an ExecutionTask from streaming converter parameters.

    This adapter function maps the streaming converter's parameters
    to the unified ExecutionTask format.

    Args:
        group_id: Group identifier (timestamp)
        input_dir: Directory containing HDF5 files
        output_dir: Directory for output MS files
        scratch_dir: Scratch directory (default: output_dir/scratch)
        start_time: Start time for query (default: group_id - 1 minute)
        end_time: End time for query (default: group_id + 10 minutes)
        writer: MS writer type
        max_workers: Maximum parallel I/O workers
        stage_to_tmpfs: Whether to stage to tmpfs
        tmpfs_path: Path to tmpfs mount
        omp_threads: OpenMP thread count (default: OMP_NUM_THREADS or 4)
        memory_mb: Memory limit in MB
        timeout_seconds: Execution timeout
        env_overrides: Additional environment variables

    Returns:
        ExecutionTask ready for execution
    """
    # Parse group_id to derive time window if not provided
    if start_time is None or end_time is None:
        try:
            gid_dt = datetime.fromisoformat(group_id)
            if start_time is None:
                start_time = (gid_dt - timedelta(seconds=60)).isoformat()
            if end_time is None:
                end_time = (gid_dt + timedelta(minutes=10)).isoformat()
        except ValueError:
            # Use defaults if group_id isn't a valid timestamp
            start_time = start_time or group_id
            end_time = end_time or group_id

    # Resolve scratch directory
    if scratch_dir is None:
        scratch_dir = Path(output_dir) / "scratch"

    # Build resource limits
    default_omp = int(os.environ.get("OMP_NUM_THREADS", "4"))
    limits = ResourceLimits(
        memory_mb=memory_mb or 0,  # 0 means no limit
        omp_threads=omp_threads or default_omp,
        max_workers=max_workers,
        timeout_seconds=timeout_seconds,
    )

    # Build environment overrides
    env = env_overrides.copy() if env_overrides else {}
    env.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")

    return ExecutionTask(
        group_id=group_id,
        input_dir=Path(input_dir),
        output_dir=Path(output_dir),
        scratch_dir=scratch_dir,
        start_time=start_time,
        end_time=end_time,
        writer=writer,
        resource_limits=limits,
        env_overrides=env,
        stage_to_tmpfs=stage_to_tmpfs,
        tmpfs_path=Path(tmpfs_path) if stage_to_tmpfs else None,
    )


def execute_conversion(
    task: ExecutionTask,
    mode: str = "auto",
    subprocess_mode: bool = False,
) -> Tuple[int, Optional[str], Optional[ExecutionMetrics]]:
    """Execute conversion using the unified execution module.

    This adapter function provides a simple interface for the streaming
    converter to use the unified execution module.

    Args:
        task: ExecutionTask to execute
        mode: Execution mode ("auto", "inprocess", "subprocess")
        subprocess_mode: Legacy flag - if True, forces subprocess mode

    Returns:
        Tuple of (return_code, writer_type, metrics)
        - return_code: 0 for success, non-zero for failure
        - writer_type: Writer used (or None on failure)
        - metrics: ExecutionMetrics (or None on failure)
    """
    # Handle legacy subprocess_mode flag
    if subprocess_mode and mode == "auto":
        mode = "subprocess"

    # Get appropriate executor
    timeout = task.resource_limits.timeout_seconds if task.resource_limits else None
    executor = get_executor(mode, timeout_seconds=timeout)

    logger.info(
        f"Executing conversion for {task.group_id} with {mode} executor",
        extra={
            "group_id": task.group_id,
            "execution_mode": mode,
            "input_dir": str(task.input_dir),
            "output_dir": str(task.output_dir),
        },
    )

    # Execute
    result = executor.run(task)

    # Map result to legacy return format
    if result.success:
        return (
            0,
            result.writer_type or task.writer,
            result.metrics,
        )
    else:
        # Map error code to return code
        return_code = result.return_code or (
            result.error_code.value if result.error_code else 1
        )
        logger.error(
            f"Conversion failed for {task.group_id}: {result.error_message}",
            extra={
                "group_id": task.group_id,
                "error_code": result.error_code,
                "error_message": result.error_message,
            },
        )
        return (return_code, None, result.metrics)


def convert_group_unified(
    group_id: str,
    input_dir: str,
    output_dir: str,
    *,
    scratch_dir: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    writer: str = "auto",
    max_workers: int = 4,
    stage_to_tmpfs: bool = False,
    tmpfs_path: str = "/dev/shm",
    execution_mode: str = "auto",
    subprocess_mode: bool = False,
    omp_threads: Optional[int] = None,
    memory_mb: Optional[int] = None,
    timeout_seconds: Optional[float] = None,
) -> Tuple[int, Optional[str], Optional[ExecutionMetrics]]:
    """High-level function to convert a subband group using unified execution.

    This function combines task creation and execution into a single call,
    providing a drop-in replacement for the streaming converter's conversion
    logic.

    Args:
        group_id: Group identifier (timestamp)
        input_dir: Directory containing HDF5 files
        output_dir: Directory for output MS files
        scratch_dir: Scratch directory (optional)
        start_time: Start time for query (optional)
        end_time: End time for query (optional)
        writer: MS writer type
        max_workers: Maximum parallel I/O workers
        stage_to_tmpfs: Whether to stage to tmpfs
        tmpfs_path: Path to tmpfs mount
        execution_mode: "auto", "inprocess", or "subprocess"
        subprocess_mode: Legacy flag for subprocess mode
        omp_threads: OpenMP thread count
        memory_mb: Memory limit in MB
        timeout_seconds: Execution timeout

    Returns:
        Tuple of (return_code, writer_type, metrics)

    Example:
        # Basic usage
        ret, writer, metrics = convert_group_unified(
            group_id="2025-06-01T12:00:00",
            input_dir="/data/incoming",
            output_dir="/stage/ms",
        )

        if ret == 0:
            print(f"Success using {writer} in {metrics.total_time_s:.1f}s")
        else:
            print(f"Failed with code {ret}")
    """
    task = create_task_from_group(
        group_id=group_id,
        input_dir=Path(input_dir),
        output_dir=Path(output_dir),
        scratch_dir=Path(scratch_dir) if scratch_dir else None,
        start_time=start_time,
        end_time=end_time,
        writer=writer,
        max_workers=max_workers,
        stage_to_tmpfs=stage_to_tmpfs,
        tmpfs_path=tmpfs_path,
        omp_threads=omp_threads,
        memory_mb=memory_mb,
        timeout_seconds=timeout_seconds,
    )

    return execute_conversion(
        task,
        mode=execution_mode,
        subprocess_mode=subprocess_mode,
    )


# Convenience functions for specific execution modes


def convert_group_inprocess(
    group_id: str,
    input_dir: str,
    output_dir: str,
    **kwargs,
) -> Tuple[int, Optional[str], Optional[ExecutionMetrics]]:
    """Convert a group using in-process execution.

    This is a convenience wrapper around convert_group_unified with
    execution_mode="inprocess".
    """
    return convert_group_unified(
        group_id=group_id,
        input_dir=input_dir,
        output_dir=output_dir,
        execution_mode="inprocess",
        **kwargs,
    )


def convert_group_subprocess(
    group_id: str,
    input_dir: str,
    output_dir: str,
    **kwargs,
) -> Tuple[int, Optional[str], Optional[ExecutionMetrics]]:
    """Convert a group using subprocess execution.

    This is a convenience wrapper around convert_group_unified with
    execution_mode="subprocess".
    """
    return convert_group_unified(
        group_id=group_id,
        input_dir=input_dir,
        output_dir=output_dir,
        execution_mode="subprocess",
        **kwargs,
    )
