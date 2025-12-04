"""
Unit tests for the execution module.

Tests the unified execution abstraction for Issue #11.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dsa110_contimg.execution import (
    ErrorCode,
    ExecutionResult,
    ExecutionTask,
    InProcessExecutor,
    ResourceManager,
    SubprocessExecutor,
    ValidationError,
    ValidationResult,
    get_executor,
    get_recommended_limits,
    map_exception_to_error_code,
    resource_limits,
    validate_execution_task,
)
from dsa110_contimg.execution.task import ExecutionMetrics, ResourceLimits


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
        scratch_dir = tmp_path / "scratch"

        task = ExecutionTask(
            group_id="2025-06-01T12:00:00",
            input_dir=input_dir,
            output_dir=output_dir,
            scratch_dir=scratch_dir,
            start_time="2025-06-01T12:00:00",
            end_time="2025-06-01T13:00:00",
        )

        assert task.group_id == "2025-06-01T12:00:00"
        assert task.input_dir == input_dir
        assert task.output_dir == output_dir
        assert task.writer == "auto"
        assert isinstance(task.resource_limits, ResourceLimits)

    def test_create_full_task(self, tmp_path: Path) -> None:
        """Test creating task with custom resource limits."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        scratch_dir = tmp_path / "scratch"

        limits = ResourceLimits(memory_mb=8000, omp_threads=8, max_workers=8)

        task = ExecutionTask(
            group_id="test-group",
            input_dir=input_dir,
            output_dir=output_dir,
            scratch_dir=scratch_dir,
            start_time="2025-06-01T12:00:00",
            end_time="2025-06-01T13:00:00",
            writer="parallel-subband",
            resource_limits=limits,
            env_overrides={"CUSTOM_VAR": "value"},
            stage_to_tmpfs=True,
            tmpfs_path=Path("/dev/shm/conversion"),
        )

        assert task.writer == "parallel-subband"
        assert task.resource_limits.memory_mb == 8000
        assert task.env_overrides["CUSTOM_VAR"] == "value"
        assert task.stage_to_tmpfs is True

    def test_to_cli_args(self, tmp_path: Path) -> None:
        """Test converting task to CLI arguments."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        scratch_dir = tmp_path / "scratch"
        scratch_dir.mkdir()

        task = ExecutionTask(
            group_id="test",
            input_dir=input_dir,
            output_dir=output_dir,
            scratch_dir=scratch_dir,
            start_time="2025-06-01T12:00:00",
            end_time="2025-06-01T13:00:00",
        )

        args = task.to_cli_args()

        assert str(input_dir.resolve()) in args
        assert str(output_dir.resolve()) in args
        assert "--scratch-dir" in args

    def test_validation(self, tmp_path: Path) -> None:
        """Test task validation."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        scratch_dir = tmp_path / "scratch"

        task = ExecutionTask(
            group_id="test",
            input_dir=input_dir,
            output_dir=output_dir,
            scratch_dir=scratch_dir,
            start_time="2025-06-01T12:00:00",
            end_time="2025-06-01T13:00:00",
        )

        # Should not raise
        task.validate()

    def test_validation_missing_input(self, tmp_path: Path) -> None:
        """Test validation fails for missing input dir."""
        input_dir = tmp_path / "nonexistent"
        output_dir = tmp_path / "output"
        scratch_dir = tmp_path / "scratch"

        task = ExecutionTask(
            group_id="test",
            input_dir=input_dir,
            output_dir=output_dir,
            scratch_dir=scratch_dir,
            start_time="2025-06-01T12:00:00",
            end_time="2025-06-01T13:00:00",
        )

        with pytest.raises(ValueError, match="does not exist"):
            task.validate()


# ============================================================================
# ExecutionResult Tests
# ============================================================================


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_successful_result(self, tmp_path: Path) -> None:
        """Test creating a successful result."""
        ms_path = tmp_path / "output.ms"
        metrics = ExecutionMetrics(total_time_s=60.0, files_processed=2)

        result = ExecutionResult.success_result(
            ms_path=ms_path,
            metrics=metrics,
            execution_mode="inprocess",
            writer_type="parallel-subband",
        )

        assert result.success is True
        assert result.return_code == 0
        assert result.ms_path == ms_path
        assert result.execution_mode == "inprocess"

    def test_failed_result(self) -> None:
        """Test creating a failed result."""
        result = ExecutionResult.failure_result(
            error_code=ErrorCode.OOM_ERROR,
            error_message="Out of memory while loading subbands",
            execution_mode="subprocess",
        )

        assert result.success is False
        assert result.error_code == ErrorCode.OOM_ERROR
        assert "memory" in result.error_message.lower()

    def test_to_dict(self, tmp_path: Path) -> None:
        """Test converting result to dictionary."""
        ms_path = tmp_path / "output.ms"
        result = ExecutionResult.success_result(
            ms_path=ms_path,
            metrics=ExecutionMetrics(),
            execution_mode="inprocess",
        )

        d = result.to_dict()
        assert d["success"] is True
        assert d["return_code"] == 0
        assert d["execution_mode"] == "inprocess"

    def test_duration_property(self) -> None:
        """Test duration calculation."""
        started = time.time()
        result = ExecutionResult(
            success=True,
            return_code=0,
            execution_mode="inprocess",
            started_at=started,
        )

        # Duration should be close to 0 since we just created it
        assert result.duration_seconds >= 0


# ============================================================================
# ErrorCode Tests
# ============================================================================


class TestErrorCode:
    """Tests for error code handling."""

    def test_error_code_values(self) -> None:
        """Test that error codes have expected values."""
        assert ErrorCode.SUCCESS.value == 0
        assert ErrorCode.GENERAL_ERROR.value == 1
        assert ErrorCode.IO_ERROR.value == 2
        assert ErrorCode.OOM_ERROR.value == 3
        assert ErrorCode.TIMEOUT_ERROR.value == 4
        assert ErrorCode.VALIDATION_ERROR.value == 5

    def test_map_file_not_found(self) -> None:
        """Test mapping FileNotFoundError to IO_ERROR."""
        exc = FileNotFoundError("file.txt")
        code, msg = map_exception_to_error_code(exc)
        assert code == ErrorCode.IO_ERROR

    def test_map_memory_error(self) -> None:
        """Test mapping MemoryError to OOM_ERROR."""
        exc = MemoryError()
        code, msg = map_exception_to_error_code(exc)
        assert code == ErrorCode.OOM_ERROR

    def test_map_value_error(self) -> None:
        """Test mapping ValueError to VALIDATION_ERROR."""
        exc = ValueError("invalid value")
        code, msg = map_exception_to_error_code(exc)
        assert code == ErrorCode.VALIDATION_ERROR

    def test_map_unknown_error(self) -> None:
        """Test mapping unknown errors to GENERAL_ERROR."""
        exc = RuntimeError("unknown")
        code, msg = map_exception_to_error_code(exc)
        assert code == ErrorCode.GENERAL_ERROR

    def test_error_code_description(self) -> None:
        """Test error code descriptions."""
        assert "success" in ErrorCode.SUCCESS.description.lower()
        assert "memory" in ErrorCode.OOM_ERROR.description.lower()


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
            start_time="2025-06-01T12:00:00",
            end_time="2025-06-01T13:00:00",
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
            start_time="2025-06-01T12:00:00",
            end_time="2025-06-01T13:00:00",
        )

        assert result.valid is False
        assert any("does not exist" in e for e in result.errors)

    def test_validate_invalid_writer(self, tmp_path: Path) -> None:
        """Test validation with invalid writer."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        result = validate_execution_task(
            input_dir=input_dir,
            output_dir=output_dir,
            start_time="2025-06-01T12:00:00",
            end_time="2025-06-01T13:00:00",
            writer="invalid-writer",
        )

        assert result.valid is False
        assert any("Invalid writer" in e for e in result.errors)

    def test_validation_result_raise_if_invalid(self) -> None:
        """Test raise_if_invalid method."""
        result = ValidationResult.failure(["Error 1", "Error 2"])

        with pytest.raises(ValidationError) as exc_info:
            result.raise_if_invalid()

        assert "Error 1" in str(exc_info.value)


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
            # May or may not be present depending on state
            pass
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
            scratch_dir=tmp_path / "scratch",
            start_time="2025-06-01T12:00:00",
            end_time="2025-06-01T13:00:00",
        )

        executor = InProcessExecutor()
        result = executor.run(task)

        assert result.success is False
        assert result.error_code == ErrorCode.VALIDATION_ERROR

    @patch("dsa110_contimg.conversion.hdf5_orchestrator.convert_subband_groups_to_ms")
    def test_successful_execution(
        self, mock_convert: MagicMock, tmp_path: Path
    ) -> None:
        """Test successful in-process execution."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        scratch_dir = tmp_path / "scratch"
        scratch_dir.mkdir()

        mock_convert.return_value = {
            "converted": ["group1", "group2"],
            "skipped": [],
            "failed": [],
        }

        task = ExecutionTask(
            group_id="test",
            input_dir=input_dir,
            output_dir=output_dir,
            scratch_dir=scratch_dir,
            start_time="2025-06-01T12:00:00",
            end_time="2025-06-01T13:00:00",
        )

        executor = InProcessExecutor()
        result = executor.run(task)

        assert result.success is True
        assert result.execution_mode == "inprocess"

    @patch("dsa110_contimg.conversion.hdf5_orchestrator.convert_subband_groups_to_ms")
    def test_all_groups_failed(self, mock_convert: MagicMock, tmp_path: Path) -> None:
        """Test when all groups fail to convert."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        scratch_dir = tmp_path / "scratch"
        scratch_dir.mkdir()

        mock_convert.return_value = {
            "converted": [],
            "skipped": [],
            "failed": [{"group_id": "g1", "error": "fail"}],
        }

        task = ExecutionTask(
            group_id="test",
            input_dir=input_dir,
            output_dir=output_dir,
            scratch_dir=scratch_dir,
            start_time="2025-06-01T12:00:00",
            end_time="2025-06-01T13:00:00",
        )

        executor = InProcessExecutor()
        result = executor.run(task)

        assert result.success is False
        assert result.error_code == ErrorCode.CONVERSION_ERROR

    @patch("dsa110_contimg.conversion.hdf5_orchestrator.convert_subband_groups_to_ms")
    def test_memory_error(self, mock_convert: MagicMock, tmp_path: Path) -> None:
        """Test handling of MemoryError."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        scratch_dir = tmp_path / "scratch"
        scratch_dir.mkdir()

        mock_convert.side_effect = MemoryError("out of memory")

        task = ExecutionTask(
            group_id="test",
            input_dir=input_dir,
            output_dir=output_dir,
            scratch_dir=scratch_dir,
            start_time="2025-06-01T12:00:00",
            end_time="2025-06-01T13:00:00",
        )

        executor = InProcessExecutor()
        result = executor.run(task)

        assert result.success is False
        assert result.error_code == ErrorCode.OOM_ERROR


class TestSubprocessExecutor:
    """Tests for SubprocessExecutor."""

    def test_validation_error(self, tmp_path: Path) -> None:
        """Test validation error before subprocess spawn."""
        task = ExecutionTask(
            group_id="test",
            input_dir=tmp_path / "nonexistent",
            output_dir=tmp_path / "output",
            scratch_dir=tmp_path / "scratch",
            start_time="2025-06-01T12:00:00",
            end_time="2025-06-01T13:00:00",
        )

        executor = SubprocessExecutor()
        result = executor.run(task)

        assert result.success is False
        assert result.error_code == ErrorCode.VALIDATION_ERROR

    def test_build_command(self, tmp_path: Path) -> None:
        """Test command building."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        scratch_dir = tmp_path / "scratch"
        scratch_dir.mkdir()

        task = ExecutionTask(
            group_id="test",
            input_dir=input_dir,
            output_dir=output_dir,
            scratch_dir=scratch_dir,
            start_time="2025-06-01T12:00:00",
            end_time="2025-06-01T13:00:00",
            writer="parallel-subband",
        )

        executor = SubprocessExecutor()
        cmd = executor._build_command(task)

        assert "groups" in cmd
        assert str(input_dir.resolve()) in cmd
        assert str(output_dir.resolve()) in cmd
        assert "--writer" in cmd
        assert "parallel-subband" in cmd

    def test_build_environment(self, tmp_path: Path) -> None:
        """Test environment building."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        scratch_dir = tmp_path / "scratch"
        scratch_dir.mkdir()

        limits = ResourceLimits(omp_threads=8)

        task = ExecutionTask(
            group_id="test",
            input_dir=input_dir,
            output_dir=output_dir,
            scratch_dir=scratch_dir,
            start_time="2025-06-01T12:00:00",
            end_time="2025-06-01T13:00:00",
            resource_limits=limits,
            env_overrides={"CUSTOM_VAR": "custom_value"},
        )

        executor = SubprocessExecutor()
        env = executor._build_environment(task)

        assert env["OMP_NUM_THREADS"] == "8"
        assert env["CUSTOM_VAR"] == "custom_value"

    def test_map_return_codes(self) -> None:
        """Test return code mapping."""
        executor = SubprocessExecutor()

        assert executor._map_return_code(0) == ErrorCode.SUCCESS
        assert executor._map_return_code(137) == ErrorCode.OOM_ERROR
        assert executor._map_return_code(124) == ErrorCode.TIMEOUT_ERROR
        assert executor._map_return_code(ErrorCode.IO_ERROR.value) == ErrorCode.IO_ERROR
        assert executor._map_return_code(99) == ErrorCode.GENERAL_ERROR


class TestGetExecutor:
    """Tests for get_executor factory."""

    def test_get_inprocess_executor(self) -> None:
        """Test getting in-process executor."""
        executor = get_executor("inprocess")
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
