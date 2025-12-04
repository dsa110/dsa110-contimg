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
import shutil
import subprocess
import sys
import tempfile
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from dsa110_contimg.execution.errors import ExecutionErrorCode, map_exception_to_code
from dsa110_contimg.execution.resources import ResourceManager, resource_limits
from dsa110_contimg.execution.task import ExecutionResult, ExecutionTask
from dsa110_contimg.execution.validate import validate_execution_task

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
            start_time=datetime(2025, 6, 1, 12, 0),
            end_time=datetime(2025, 6, 1, 13, 0),
        )

        executor = InProcessExecutor()
        result = executor.run(task)

        if result.success:
            print(f"Converted to: {result.final_paths}")
        else:
            print(f"Failed: {result.error_code} - {result.message}")
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
        result = validate_execution_task(
            input_dir=task.input_dir,
            output_dir=task.output_dir,
            start_time=task.start_time,
            end_time=task.end_time,
            writer=task.writer,
            scratch_dir=task.scratch_dir,
            memory_mb=task.resource_limits.get("memory_mb"),
            omp_threads=task.resource_limits.get("omp_threads"),
            max_workers=task.resource_limits.get("max_workers"),
        )
        if not result.valid:
            return "; ".join(result.errors)
        return None


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
        started_at = datetime.now(timezone.utc)
        metrics: Dict[str, Any] = {}

        # Validate first
        validation_error = self.validate_task(task)
        if validation_error:
            return ExecutionResult(
                success=False,
                return_code=ExecutionErrorCode.VALIDATION.value,
                error_code=ExecutionErrorCode.VALIDATION,
                error_type="ValidationError",
                message=validation_error,
                execution_mode="in-process",
                started_at=started_at,
                ended_at=datetime.now(timezone.utc),
            )

        # Extract resource limits
        memory_mb = task.resource_limits.get("memory_mb")
        omp_threads = task.resource_limits.get("omp_threads", 4)
        max_workers = task.resource_limits.get("max_workers", 4)

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
                    start_time=task.start_time.isoformat(),
                    end_time=task.end_time.isoformat(),
                )

                # Gather metrics
                metrics = rm.get_usage_stats()
                metrics["groups_converted"] = len(result.get("converted", []))
                metrics["groups_skipped"] = len(result.get("skipped", []))
                metrics["groups_failed"] = len(result.get("failed", []))

                # Check resource limits
                limit_error = rm.check_limits()
                if limit_error:
                    logger.warning(f"Resource limit warning: {limit_error}")
                    metrics["resource_warning"] = limit_error

                # Determine success
                has_failures = len(result.get("failed", [])) > 0
                has_conversions = len(result.get("converted", [])) > 0

                if has_failures and not has_conversions:
                    # All failed
                    return ExecutionResult(
                        success=False,
                        return_code=ExecutionErrorCode.GENERAL.value,
                        error_code=ExecutionErrorCode.GENERAL,
                        error_type="ConversionError",
                        message=f"All {len(result['failed'])} groups failed to convert",
                        metrics=metrics,
                        execution_mode="in-process",
                        started_at=started_at,
                        ended_at=datetime.now(timezone.utc),
                    )

                # Some or all succeeded
                return ExecutionResult(
                    success=True,
                    return_code=ExecutionErrorCode.SUCCESS.value,
                    error_code=ExecutionErrorCode.SUCCESS,
                    final_paths=result.get("converted", []),
                    metrics=metrics,
                    execution_mode="in-process",
                    started_at=started_at,
                    ended_at=datetime.now(timezone.utc),
                )

        except MemoryError as e:
            return ExecutionResult(
                success=False,
                return_code=ExecutionErrorCode.OOM.value,
                error_code=ExecutionErrorCode.OOM,
                error_type="MemoryError",
                message=str(e) or "Out of memory",
                traceback=traceback.format_exc(),
                metrics=metrics,
                execution_mode="in-process",
                started_at=started_at,
                ended_at=datetime.now(timezone.utc),
            )

        except TimeoutError as e:
            return ExecutionResult(
                success=False,
                return_code=ExecutionErrorCode.TIMEOUT.value,
                error_code=ExecutionErrorCode.TIMEOUT,
                error_type="TimeoutError",
                message=str(e),
                traceback=traceback.format_exc(),
                metrics=metrics,
                execution_mode="in-process",
                started_at=started_at,
                ended_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            error_code = map_exception_to_code(e)
            return ExecutionResult(
                success=False,
                return_code=error_code.value,
                error_code=error_code,
                error_type=type(e).__name__,
                message=str(e),
                traceback=traceback.format_exc(),
                metrics=metrics,
                execution_mode="in-process",
                started_at=started_at,
                ended_at=datetime.now(timezone.utc),
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
            timeout_seconds: Subprocess timeout (default: no timeout)
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
        started_at = datetime.now(timezone.utc)

        # Validate first
        validation_error = self.validate_task(task)
        if validation_error:
            return ExecutionResult(
                success=False,
                return_code=ExecutionErrorCode.VALIDATION.value,
                error_code=ExecutionErrorCode.VALIDATION,
                error_type="ValidationError",
                message=validation_error,
                execution_mode="subprocess",
                started_at=started_at,
                ended_at=datetime.now(timezone.utc),
            )

        # Build command
        cmd = self._build_command(task)

        # Build environment
        env = self._build_environment(task)

        # Create result file for structured output
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as result_file:
            result_path = result_file.name

        cmd.extend(["--result-file", result_path])

        logger.debug(f"Executing subprocess: {' '.join(cmd)}")

        try:
            # Create resource manager for preexec_fn
            resource_manager = ResourceManager(
                memory_mb=task.resource_limits.get("memory_mb"),
                cpu_seconds=task.resource_limits.get("cpu_seconds"),
                omp_threads=task.resource_limits.get("omp_threads", 4),
            )

            process = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                timeout=self.timeout_seconds,
                text=True,
                preexec_fn=resource_manager.apply_subprocess_limits,
            )

            stdout = process.stdout or ""
            stderr = process.stderr or ""

            # Try to read structured result
            metrics: Dict[str, Any] = {}
            final_paths: List[str] = []

            if os.path.exists(result_path):
                try:
                    with open(result_path) as f:
                        result_data = json.load(f)
                    final_paths = result_data.get("converted", [])
                    metrics = result_data.get("metrics", {})
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"Failed to read result file: {e}")

            # Map return code to error code
            error_code = self._map_return_code(process.returncode)

            return ExecutionResult(
                success=(process.returncode == 0),
                return_code=process.returncode,
                error_code=error_code,
                error_type=None if process.returncode == 0 else "SubprocessError",
                message=stderr if process.returncode != 0 else None,
                stdout=stdout,
                stderr=stderr,
                final_paths=final_paths,
                metrics=metrics,
                execution_mode="subprocess",
                started_at=started_at,
                ended_at=datetime.now(timezone.utc),
            )

        except subprocess.TimeoutExpired as e:
            return ExecutionResult(
                success=False,
                return_code=ExecutionErrorCode.TIMEOUT.value,
                error_code=ExecutionErrorCode.TIMEOUT,
                error_type="TimeoutError",
                message=f"Subprocess timed out after {self.timeout_seconds}s",
                stdout=e.stdout or "",
                stderr=e.stderr or "",
                execution_mode="subprocess",
                started_at=started_at,
                ended_at=datetime.now(timezone.utc),
            )

        except OSError as e:
            return ExecutionResult(
                success=False,
                return_code=ExecutionErrorCode.IO.value,
                error_code=ExecutionErrorCode.IO,
                error_type="OSError",
                message=f"Failed to spawn subprocess: {e}",
                execution_mode="subprocess",
                started_at=started_at,
                ended_at=datetime.now(timezone.utc),
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
        cmd = [
            self.python_executable,
            "-m",
            "dsa110_contimg.conversion.cli",
            "groups",
            str(task.input_dir),
            str(task.output_dir),
            task.start_time.isoformat(),
            task.end_time.isoformat(),
        ]

        # Add optional arguments
        if task.writer != "auto":
            cmd.extend(["--writer", task.writer])

        if task.scratch_dir:
            cmd.extend(["--scratch-dir", str(task.scratch_dir)])

        # Resource limits as CLI args
        if "omp_threads" in task.resource_limits:
            cmd.extend(["--omp-threads", str(task.resource_limits["omp_threads"])])

        return cmd

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

        # Set thread limits
        resource_manager = ResourceManager(
            omp_threads=task.resource_limits.get("omp_threads", 4),
            mkl_threads=task.resource_limits.get("mkl_threads", 4),
        )
        env.update(resource_manager.get_env_vars())

        return env

    def _map_return_code(self, code: int) -> ExecutionErrorCode:
        """Map subprocess return code to ExecutionErrorCode.

        Args:
            code: Process return code

        Returns:
            Corresponding ExecutionErrorCode
        """
        if code == 0:
            return ExecutionErrorCode.SUCCESS
        elif code == 137:  # SIGKILL (often OOM)
            return ExecutionErrorCode.OOM
        elif code == 124:  # timeout command code
            return ExecutionErrorCode.TIMEOUT
        elif code == 2:  # Common for I/O errors
            return ExecutionErrorCode.IO
        elif code == 5:  # Validation errors in our CLI
            return ExecutionErrorCode.VALIDATION
        else:
            return ExecutionErrorCode.GENERAL


def get_executor(mode: str = "auto", **kwargs: Any) -> Executor:
    """Factory function to get an executor instance.

    Args:
        mode: Execution mode - "in-process", "subprocess", or "auto"
        **kwargs: Additional arguments passed to executor constructor

    Returns:
        Appropriate Executor instance

    Example:
        executor = get_executor("subprocess", timeout_seconds=3600)
        result = executor.run(task)
    """
    if mode == "in-process":
        return InProcessExecutor()
    elif mode == "subprocess":
        return SubprocessExecutor(**kwargs)
    elif mode == "auto":
        # Default to in-process for efficiency
        # Could add heuristics based on task size
        return InProcessExecutor()
    else:
        raise ValueError(f"Unknown execution mode: {mode}")
