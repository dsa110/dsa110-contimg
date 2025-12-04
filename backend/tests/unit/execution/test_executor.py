"""
Unit tests for the execution module.

Tests the unified execution abstraction for Issue #11.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from dsa110_contimg.execution import (
    ExecutionErrorCode,
    ExecutionResult,
    ExecutionTask,
    InProcessExecutor,
    ResourceManager,
    SubprocessExecutor,
    ValidationError,
    ValidationResult,
    get_executor,
    get_recommended_limits,
    map_exception_to_code,
    resource_limits,
    validate_execution_task,
)


# ============================================================================
# ExecutionTask Tests
# ============================================================================


class TestExecutionTask:
    """Tests for ExecutionTask dataclass."""

    def test_create_minimal_task(self, tmp_path: Path) -> None:
        """Test creating task with minimal required fields."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        task = ExecutionTask(
            group_id="2025-06-01T12:00:00",
            input_dir=input_dir,
            output_dir=output_dir,
            start_time=datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 6, 1, 13, 0, tzinfo=timezone.utc),
        )

        assert task.group_id == "2025-06-01T12:00:00"
        assert task.input_dir == input_dir
        assert task.output_dir == output_dir
        assert task.writer == "auto"
        assert task.resource_limits == {}
        assert task.env_overrides == {}

    def test_create_full_task(self, tmp_path: Path) -> None:
        """Test creating task with all fields."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        scratch_dir = tmp_path / "scratch"

        task = ExecutionTask(
            group_id="test-group",
            input_dir=input_dir,
            output_dir=output_dir,
            scratch_dir=scratch_dir,
            start_time=datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 6, 1, 13, 0, tzinfo=timezone.utc),
            writer="parallel-subband",
            resource_limits={"memory_mb": 8000, "omp_threads": 4},
            env_overrides={"CUSTOM_VAR": "value"},
            stage_to_tmpfs=True,
            tmpfs_path=Path("/dev/shm/conversion"),
        )

        assert task.writer == "parallel-subband"
        assert task.resource_limits["memory_mb"] == 8000
        assert task.env_overrides["CUSTOM_VAR"] == "value"
        assert task.stage_to_tmpfs is True


# ============================================================================
# ExecutionResult Tests
# ============================================================================


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_successful_result(self) -> None:
        """Test creating a successful result."""
        started = datetime.now(timezone.utc)
        ended = started + timedelta(seconds=60)

        result = ExecutionResult(
            success=True,
            return_code=0,
            error_code=ExecutionErrorCode.SUCCESS,
            final_paths=["output/group1.ms", "output/group2.ms"],
            metrics={"groups_converted": 2},
            execution_mode="in-process",
            started_at=started,
            ended_at=ended,
        )

        assert result.success is True
        assert result.return_code == 0
        assert result.error_code == ExecutionErrorCode.SUCCESS
        assert len(result.final_paths) == 2
        assert result.duration_seconds == pytest.approx(60.0, abs=0.1)

    def test_failed_result(self) -> None:
        """Test creating a failed result."""
        result = ExecutionResult(
            success=False,
            return_code=3,
            error_code=ExecutionErrorCode.OOM,
            error_type="MemoryError",
            message="Out of memory while loading subbands",
            traceback="...",
            execution_mode="subprocess",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
        )

        assert result.success is False
        assert result.error_code == ExecutionErrorCode.OOM
        assert result.error_type == "MemoryError"
        assert "memory" in result.message.lower()

    def test_to_dict(self) -> None:
        """Test converting result to dictionary."""
        result = ExecutionResult(
            success=True,
            return_code=0,
            error_code=ExecutionErrorCode.SUCCESS,
            execution_mode="in-process",
            started_at=datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc),
            ended_at=datetime(2025, 6, 1, 12, 1, tzinfo=timezone.utc),
        )

        d = result.to_dict()
        assert d["success"] is True
        assert d["return_code"] == 0
        assert d["error_code"] == "SUCCESS"
        assert d["execution_mode"] == "in-process"
        assert "duration_seconds" in d

    def test_duration_with_missing_times(self) -> None:
        """Test duration calculation with missing timestamps."""
        result = ExecutionResult(
            success=True,
            return_code=0,
            error_code=ExecutionErrorCode.SUCCESS,
            execution_mode="in-process",
        )

        assert result.duration_seconds is None


# ============================================================================
# ExecutionErrorCode Tests
# ============================================================================


class TestExecutionErrorCode:
    """Tests for error code handling."""

    def test_error_code_values(self) -> None:
        """Test that error codes have expected values."""
        assert ExecutionErrorCode.SUCCESS.value == 0
        assert ExecutionErrorCode.GENERAL.value == 1
        assert ExecutionErrorCode.IO.value == 2
        assert ExecutionErrorCode.OOM.value == 3
        assert ExecutionErrorCode.TIMEOUT.value == 4
        assert ExecutionErrorCode.VALIDATION.value == 5

    def test_map_file_not_found(self) -> None:
        """Test mapping FileNotFoundError to IO."""
        exc = FileNotFoundError("file.txt")
        assert map_exception_to_code(exc) == ExecutionErrorCode.IO

    def test_map_memory_error(self) -> None:
        """Test mapping MemoryError to OOM."""
        exc = MemoryError()
        assert map_exception_to_code(exc) == ExecutionErrorCode.OOM

    def test_map_timeout_error(self) -> None:
        """Test mapping TimeoutError to TIMEOUT."""
        exc = TimeoutError()
        assert map_exception_to_code(exc) == ExecutionErrorCode.TIMEOUT

    def test_map_unknown_error(self) -> None:
        """Test mapping unknown errors to GENERAL."""
        exc = RuntimeError("unknown")
        assert map_exception_to_code(exc) == ExecutionErrorCode.GENERAL


# ============================================================================
# Validation Tests
# ============================================================================


class TestValidation:
    """Tests for task validation."""

    def test_validate_valid_task(self, tmp_path: Path) -> None:
        """Test validation of a valid task."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        result = validate_execution_task(
            input_dir=input_dir,
            output_dir=output_dir,
            start_time=datetime(2025, 6, 1, 12, 0),
            end_time=datetime(2025, 6, 1, 13, 0),
        )

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_missing_input_dir(self, tmp_path: Path) -> None:
        """Test validation with missing input directory."""
        input_dir = tmp_path / "nonexistent"
        output_dir = tmp_path / "output"

        result = validate_execution_task(
            input_dir=input_dir,
            output_dir=output_dir,
            start_time=datetime(2025, 6, 1, 12, 0),
            end_time=datetime(2025, 6, 1, 13, 0),
        )

        assert result.valid is False
        assert any("does not exist" in e for e in result.errors)

    def test_validate_invalid_time_range(self, tmp_path: Path) -> None:
        """Test validation with invalid time range."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        result = validate_execution_task(
            input_dir=input_dir,
            output_dir=output_dir,
            start_time=datetime(2025, 6, 1, 13, 0),  # After end
            end_time=datetime(2025, 6, 1, 12, 0),
        )

        assert result.valid is False
        assert any("before" in e for e in result.errors)

    def test_validate_invalid_writer(self, tmp_path: Path) -> None:
        """Test validation with invalid writer."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        result = validate_execution_task(
            input_dir=input_dir,
            output_dir=output_dir,
            start_time=datetime(2025, 6, 1, 12, 0),
            end_time=datetime(2025, 6, 1, 13, 0),
            writer="invalid-writer",
        )

        assert result.valid is False
        assert any("Invalid writer" in e for e in result.errors)

    def test_validate_low_memory_limit(self, tmp_path: Path) -> None:
        """Test validation with too-low memory limit."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        result = validate_execution_task(
            input_dir=input_dir,
            output_dir=output_dir,
            start_time=datetime(2025, 6, 1, 12, 0),
            end_time=datetime(2025, 6, 1, 13, 0),
            memory_mb=100,  # Too low
        )

        assert result.valid is False
        assert any("too low" in e for e in result.errors)

    def test_validation_result_raise_if_invalid(self) -> None:
        """Test raise_if_invalid method."""
        result = ValidationResult.failure(["Error 1", "Error 2"])

        with pytest.raises(ValidationError) as exc_info:
            result.raise_if_invalid()

        assert "Error 1" in str(exc_info.value)
        assert "Error 2" in str(exc_info.value)


# ============================================================================
# ResourceManager Tests
# ============================================================================


class TestResourceManager:
    """Tests for ResourceManager."""

    def test_get_env_vars(self) -> None:
        """Test getting environment variables."""
        rm = ResourceManager(omp_threads=8, mkl_threads=8)
        env = rm.get_env_vars()

        assert env["OMP_NUM_THREADS"] == "8"
        assert env["MKL_NUM_THREADS"] == "8"
        assert env["OPENBLAS_NUM_THREADS"] == "8"

    def test_inprocess_limits_context(self) -> None:
        """Test in-process limits context manager."""
        original_omp = os.environ.get("OMP_NUM_THREADS")

        with resource_limits(omp_threads=2, mode="inprocess") as rm:
            assert os.environ["OMP_NUM_THREADS"] == "2"
            stats = rm.get_usage_stats()
            assert "memory_mb" in stats

        # Should be restored
        if original_omp is None:
            assert "OMP_NUM_THREADS" not in os.environ or os.environ.get("OMP_NUM_THREADS") != "2"
        else:
            assert os.environ.get("OMP_NUM_THREADS") == original_omp

    def test_get_recommended_limits(self) -> None:
        """Test recommended limits calculation."""
        limits = get_recommended_limits(available_memory_gb=32.0)

        assert limits["memory_mb"] == 24576  # 32 * 1024 * 0.75
        assert limits["omp_threads"] >= 1
        assert limits["max_workers"] >= 1


# ============================================================================
# Executor Tests
# ============================================================================


class TestInProcessExecutor:
    """Tests for InProcessExecutor."""

    def test_validation_error(self, tmp_path: Path) -> None:
        """Test that validation errors are returned properly."""
        task = ExecutionTask(
            group_id="test",
            input_dir=tmp_path / "nonexistent",  # Doesn't exist
            output_dir=tmp_path / "output",
            start_time=datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 6, 1, 13, 0, tzinfo=timezone.utc),
        )

        executor = InProcessExecutor()
        result = executor.run(task)

        assert result.success is False
        assert result.error_code == ExecutionErrorCode.VALIDATION
        assert result.error_type == "ValidationError"

    @patch("dsa110_contimg.execution.executor.convert_subband_groups_to_ms")
    def test_successful_execution(
        self, mock_convert: MagicMock, tmp_path: Path
    ) -> None:
        """Test successful in-process execution."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        mock_convert.return_value = {
            "converted": ["group1", "group2"],
            "skipped": [],
            "failed": [],
        }

        task = ExecutionTask(
            group_id="test",
            input_dir=input_dir,
            output_dir=output_dir,
            start_time=datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 6, 1, 13, 0, tzinfo=timezone.utc),
        )

        executor = InProcessExecutor()
        result = executor.run(task)

        assert result.success is True
        assert result.error_code == ExecutionErrorCode.SUCCESS
        assert result.execution_mode == "in-process"
        assert len(result.final_paths) == 2
        assert result.metrics["groups_converted"] == 2

    @patch("dsa110_contimg.execution.executor.convert_subband_groups_to_ms")
    def test_all_groups_failed(self, mock_convert: MagicMock, tmp_path: Path) -> None:
        """Test when all groups fail to convert."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        mock_convert.return_value = {
            "converted": [],
            "skipped": [],
            "failed": [{"group_id": "g1", "error": "fail"}],
        }

        task = ExecutionTask(
            group_id="test",
            input_dir=input_dir,
            output_dir=output_dir,
            start_time=datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 6, 1, 13, 0, tzinfo=timezone.utc),
        )

        executor = InProcessExecutor()
        result = executor.run(task)

        assert result.success is False
        assert result.error_code == ExecutionErrorCode.GENERAL
        assert "failed to convert" in result.message

    @patch("dsa110_contimg.execution.executor.convert_subband_groups_to_ms")
    def test_memory_error(self, mock_convert: MagicMock, tmp_path: Path) -> None:
        """Test handling of MemoryError."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        mock_convert.side_effect = MemoryError("out of memory")

        task = ExecutionTask(
            group_id="test",
            input_dir=input_dir,
            output_dir=output_dir,
            start_time=datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 6, 1, 13, 0, tzinfo=timezone.utc),
        )

        executor = InProcessExecutor()
        result = executor.run(task)

        assert result.success is False
        assert result.error_code == ExecutionErrorCode.OOM
        assert result.error_type == "MemoryError"


class TestSubprocessExecutor:
    """Tests for SubprocessExecutor."""

    def test_validation_error(self, tmp_path: Path) -> None:
        """Test validation error before subprocess spawn."""
        task = ExecutionTask(
            group_id="test",
            input_dir=tmp_path / "nonexistent",
            output_dir=tmp_path / "output",
            start_time=datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 6, 1, 13, 0, tzinfo=timezone.utc),
        )

        executor = SubprocessExecutor()
        result = executor.run(task)

        assert result.success is False
        assert result.error_code == ExecutionErrorCode.VALIDATION

    def test_build_command(self, tmp_path: Path) -> None:
        """Test command building."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        scratch_dir = tmp_path / "scratch"

        task = ExecutionTask(
            group_id="test",
            input_dir=input_dir,
            output_dir=output_dir,
            scratch_dir=scratch_dir,
            start_time=datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 6, 1, 13, 0, tzinfo=timezone.utc),
            writer="parallel-subband",
            resource_limits={"omp_threads": 4},
        )

        executor = SubprocessExecutor()
        cmd = executor._build_command(task)

        assert "groups" in cmd
        assert str(input_dir) in cmd
        assert str(output_dir) in cmd
        assert "--writer" in cmd
        assert "parallel-subband" in cmd
        assert "--scratch-dir" in cmd
        assert "--omp-threads" in cmd
        assert "4" in cmd

    def test_build_environment(self, tmp_path: Path) -> None:
        """Test environment building."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"

        task = ExecutionTask(
            group_id="test",
            input_dir=input_dir,
            output_dir=output_dir,
            start_time=datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 6, 1, 13, 0, tzinfo=timezone.utc),
            resource_limits={"omp_threads": 8},
            env_overrides={"CUSTOM_VAR": "custom_value"},
        )

        executor = SubprocessExecutor()
        env = executor._build_environment(task)

        assert env["OMP_NUM_THREADS"] == "8"
        assert env["CUSTOM_VAR"] == "custom_value"

    def test_map_return_codes(self) -> None:
        """Test return code mapping."""
        executor = SubprocessExecutor()

        assert executor._map_return_code(0) == ExecutionErrorCode.SUCCESS
        assert executor._map_return_code(137) == ExecutionErrorCode.OOM
        assert executor._map_return_code(124) == ExecutionErrorCode.TIMEOUT
        assert executor._map_return_code(2) == ExecutionErrorCode.IO
        assert executor._map_return_code(99) == ExecutionErrorCode.GENERAL


class TestGetExecutor:
    """Tests for get_executor factory."""

    def test_get_inprocess_executor(self) -> None:
        """Test getting in-process executor."""
        executor = get_executor("in-process")
        assert isinstance(executor, InProcessExecutor)

    def test_get_subprocess_executor(self) -> None:
        """Test getting subprocess executor."""
        executor = get_executor("subprocess", timeout_seconds=3600)
        assert isinstance(executor, SubprocessExecutor)
        assert executor.timeout_seconds == 3600

    def test_get_auto_executor(self) -> None:
        """Test auto selection defaults to in-process."""
        executor = get_executor("auto")
        assert isinstance(executor, InProcessExecutor)

    def test_invalid_mode(self) -> None:
        """Test that invalid mode raises error."""
        with pytest.raises(ValueError, match="Unknown execution mode"):
            get_executor("invalid-mode")
