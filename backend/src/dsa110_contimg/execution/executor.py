"""
Unified execution interface for the conversion pipeline.

This module provides the Executor abstraction that enables consistent
execution of conversion tasks in both in-process and subprocess modes.

Part of Issue #11: Subprocess vs In-Process Execution Consistency.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
import time
import traceback
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from dsa110_contimg.execution.errors import ErrorCode, map_exception_to_error_code
from dsa110_contimg.execution.resources import ResourceManager, resource_limits
from dsa110_contimg.execution.task import (
    ExecutionMetrics,
    ExecutionResult,
    ExecutionTask,
)

logger = logging.getLogger(__name__)


class Executor(ABC):
    """Abstract base class for execution strategies.

    This provides a unified interface for running conversion tasks
    regardless of whether they execute in-process or as subprocesses.

    The key guarantee is that both implementations produce:
    - Identical output file layouts
    - Consistent error codes
    - Comparable resource tracking

    Subclasses must implement:
    - run(task: ExecutionTask) -> ExecutionResult

    Example:
        task = ExecutionTask(
            group_id="2025-06-01T12:00:00",
            input_dir=Path("/data/incoming"),
            output_dir=Path("/stage/ms"),
            scratch_dir=Path("/scratch"),
            start_time="2025-06-01T12:00:00",
            end_time="2025-06-01T13:00:00",
        )

        executor = InProcessExecutor()
        result = executor.run(task)

        if result.success:
            print(f"Converted to: {result.final_paths}")
        else:
            print(f"Failed: {result.error_code} - {result.error_message}")
    """

    @abstractmethod
    def run(self, task: ExecutionTask) -> ExecutionResult:
        """Execute the conversion task.

        Args:
            task: The execution task specification

        Returns:
            ExecutionResult with success/failure status and metadata
        """
        pass

    def validate_task(self, task: ExecutionTask) -> Optional[str]:
        """Validate a task before execution.

        Args:
            task: Task to validate

        Returns:
            Error message if validation fails, None otherwise
        """
        try:
            task.validate()
            return None
        except ValueError as e:
            return str(e)


class InProcessExecutor(Executor):
    """Execute conversion tasks in the current process.

    This executor runs conversion directly in the same Python process,
    using the hdf5_orchestrator module. It's more efficient for small
    batches but provides weaker isolation.

    Resource limits are applied via:
    - Environment variables (OMP_NUM_THREADS, etc.)
    - Soft monitoring (can warn but not hard-kill on memory)
    """

    def run(self, task: ExecutionTask) -> ExecutionResult:
        """Run conversion in-process.

        Args:
            task: The execution task

        Returns:
            ExecutionResult with outcome
        """
        started_at = time.time()

        # Validate first
        validation_error = self.validate_task(task)
        if validation_error:
            return ExecutionResult.failure_result(
                error_code=ErrorCode.VALIDATION_ERROR,
                error_message=validation_error,
                execution_mode="inprocess",
            )

        # Extract resource limits
        limits = task.resource_limits
        memory_mb = limits.memory_mb
        omp_threads = limits.omp_threads
        max_workers = limits.max_workers

        try:
            with resource_limits(
                memory_mb=memory_mb,
                omp_threads=omp_threads,
                max_workers=max_workers,
                mode="inprocess",
            ) as rm:
                # Import here to avoid circular imports
                from dsa110_contimg.conversion.hdf5_orchestrator import (
                    convert_subband_groups_to_ms,
                )

                result = convert_subband_groups_to_ms(
                    input_dir=str(task.input_dir),
                    output_dir=str(task.output_dir),
                    start_time=task.start_time,
                    end_time=task.end_time,
                )

                # Gather metrics
                usage_stats = rm.get_usage_stats()

                metrics = ExecutionMetrics(
                    total_time_s=time.time() - started_at,
                    memory_peak_mb=usage_stats.get("max_rss_mb", 0.0),
                    files_processed=len(result.get("converted", [])),
                )

                # Check resource limits
                limit_error = rm.check_limits()
                if limit_error:
                    logger.warning(f"Resource limit warning: {limit_error}")

                # Determine success
                has_failures = len(result.get("failed", [])) > 0
                has_conversions = len(result.get("converted", [])) > 0

                if has_failures and not has_conversions:
                    # All failed
                    error_details = result.get("failed", [{}])[0]
                    return ExecutionResult.failure_result(
                        error_code=ErrorCode.CONVERSION_ERROR,
                        error_message=f"All {len(result['failed'])} groups failed: {error_details.get('error', 'unknown')}",
                        execution_mode="inprocess",
                    )

                # Some or all succeeded
                if result.get("converted"):
                    # Get the first MS path from converted groups
                    first_ms = Path(task.output_dir) / f"{result['converted'][0]}.ms"
                    return ExecutionResult.success_result(
                        ms_path=first_ms,
                        metrics=metrics,
                        execution_mode="inprocess",
                        writer_type=task.writer,
                    )
                else:
                    # Nothing converted (everything skipped?)
                    return ExecutionResult(
                        success=True,
                        return_code=0,
                        metrics=metrics,
                        execution_mode="inprocess",
                        ended_at=time.time(),
                    )

        except MemoryError as e:
            return ExecutionResult.failure_result(
                error_code=ErrorCode.OOM_ERROR,
                error_message=str(e) or "Out of memory",
                traceback=traceback.format_exc(),
                execution_mode="inprocess",
            )

        except Exception as e:
            error_code, error_message = map_exception_to_error_code(e)
            return ExecutionResult.failure_result(
                error_code=error_code,
                error_message=error_message,
                traceback=traceback.format_exc(),
                execution_mode="inprocess",
            )


class SubprocessExecutor(Executor):
    """Execute conversion tasks in isolated subprocesses.

    This executor spawns a new Python process for each conversion task,
    providing strong isolation. Resource limits are enforced via rlimit.

    The subprocess calls the conversion CLI with appropriate arguments.
    """

    def __init__(
        self,
        python_executable: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        """Initialize subprocess executor.

        Args:
            python_executable: Path to Python executable (default: current)
            timeout_seconds: Subprocess timeout (default: from task resource_limits)
        """
        self.python_executable = python_executable or sys.executable
        self.timeout_seconds = timeout_seconds

    def run(self, task: ExecutionTask) -> ExecutionResult:
        """Run conversion in a subprocess.

        Args:
            task: The execution task

        Returns:
            ExecutionResult with outcome
        """
        started_at = time.time()

        # Validate first
        validation_error = self.validate_task(task)
        if validation_error:
            return ExecutionResult.failure_result(
                error_code=ErrorCode.VALIDATION_ERROR,
                error_message=validation_error,
                execution_mode="subprocess",
            )

        # Build command
        cmd = self._build_command(task)

        # Build environment
        env = self._build_environment(task)

        # Create result file for structured output
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as result_file:
            result_path = result_file.name

        cmd.extend(["--result-file", result_path])

        logger.debug(f"Executing subprocess: {' '.join(cmd)}")

        # Determine timeout
        timeout = self.timeout_seconds or task.resource_limits.timeout_seconds

        try:
            # Create resource manager for preexec_fn
            resource_manager = ResourceManager(
                memory_mb=task.resource_limits.memory_mb,
                cpu_seconds=task.resource_limits.cpu_seconds,
                omp_threads=task.resource_limits.omp_threads,
            )

            process = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                timeout=timeout,
                text=True,
                preexec_fn=resource_manager.apply_subprocess_limits,
            )

            stdout = process.stdout or ""
            stderr = process.stderr or ""

            # Try to read structured result
            metrics = ExecutionMetrics(total_time_s=time.time() - started_at)
            ms_path: Optional[Path] = None

            if os.path.exists(result_path):
                try:
                    with open(result_path) as f:
                        result_data = json.load(f)
                    if result_data.get("converted"):
                        ms_path = Path(task.output_dir) / f"{result_data['converted'][0]}.ms"
                    if result_data.get("metrics"):
                        result_metrics = result_data["metrics"]
                        metrics = ExecutionMetrics(
                            load_time_s=result_metrics.get("load_time_s", 0),
                            phase_time_s=result_metrics.get("phase_time_s", 0),
                            write_time_s=result_metrics.get("write_time_s", 0),
                            total_time_s=result_metrics.get(
                                "total_time_s", time.time() - started_at
                            ),
                            memory_peak_mb=result_metrics.get("memory_peak_mb", 0),
                            files_processed=result_metrics.get("files_processed", 0),
                        )
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"Failed to read result file: {e}")

            # Map return code to error code
            error_code = self._map_return_code(process.returncode)

            if process.returncode == 0:
                return ExecutionResult.success_result(
                    ms_path=ms_path or Path(task.output_dir),
                    metrics=metrics,
                    execution_mode="subprocess",
                    writer_type=task.writer,
                )
            else:
                return ExecutionResult.failure_result(
                    error_code=error_code,
                    error_message=stderr or f"Subprocess exited with code {process.returncode}",
                    execution_mode="subprocess",
                )

        except subprocess.TimeoutExpired:
            return ExecutionResult.failure_result(
                error_code=ErrorCode.TIMEOUT_ERROR,
                error_message=f"Subprocess timed out after {timeout}s",
                execution_mode="subprocess",
            )

        except OSError as e:
            return ExecutionResult.failure_result(
                error_code=ErrorCode.IO_ERROR,
                error_message=f"Failed to spawn subprocess: {e}",
                execution_mode="subprocess",
            )

        finally:
            # Clean up result file
            if os.path.exists(result_path):
                try:
                    os.unlink(result_path)
                except OSError:
                    pass

    def _build_command(self, task: ExecutionTask) -> List[str]:
        """Build the subprocess command line.

        Args:
            task: Execution task

        Returns:
            Command as list of strings
        """
        cli_args = task.to_cli_args()
        # Use the execution.cli module (not the deprecated conversion.cli)
        return [
            self.python_executable,
            "-m",
            "dsa110_contimg.execution.cli",
            "convert",
        ] + cli_args

    def _build_environment(self, task: ExecutionTask) -> Dict[str, str]:
        """Build environment variables for subprocess.

        Args:
            task: Execution task

        Returns:
            Environment dictionary
        """
        env = os.environ.copy()

        # Apply task-specific environment overrides
        env.update(task.env_overrides)

        # Set thread limits from ResourceLimits
        env.update(task.resource_limits.to_env_dict())

        return env

    def _map_return_code(self, code: int) -> ErrorCode:
        """Map subprocess return code to ErrorCode.

        Args:
            code: Process return code

        Returns:
            Corresponding ErrorCode
        """
        if code == 0:
            return ErrorCode.SUCCESS
        elif code == 137:  # SIGKILL (often OOM)
            return ErrorCode.OOM_ERROR
        elif code == 124:  # timeout command code
            return ErrorCode.TIMEOUT_ERROR
        elif code == ErrorCode.IO_ERROR.value:
            return ErrorCode.IO_ERROR
        elif code == ErrorCode.VALIDATION_ERROR.value:
            return ErrorCode.VALIDATION_ERROR
        elif code == ErrorCode.CONVERSION_ERROR.value:
            return ErrorCode.CONVERSION_ERROR
        else:
            return ErrorCode.GENERAL_ERROR


def get_executor(mode: str = "auto", **kwargs: Any) -> Executor:
    """Factory function to get an executor instance.

    Args:
        mode: Execution mode - "inprocess", "subprocess", or "auto"
        **kwargs: Additional arguments passed to executor constructor

    Returns:
        Appropriate Executor instance

    Example:
        executor = get_executor("subprocess", timeout_seconds=3600)
        result = executor.run(task)
    """
    if mode == "inprocess":
        return InProcessExecutor()
    elif mode == "subprocess":
        return SubprocessExecutor(**kwargs)
    elif mode == "auto":
        # Default to in-process for efficiency
        # Could add heuristics based on task size
        return InProcessExecutor()
    else:
        raise ValueError(
            f"Unknown execution mode: {mode}. Must be 'inprocess', 'subprocess', or 'auto'"
        )
