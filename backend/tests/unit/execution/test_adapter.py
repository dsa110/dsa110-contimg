"""
Unit tests for the execution adapter module.

Tests the adapter functions that bridge the streaming converter
with the unified execution module.

Part of Issue #11: Subprocess vs In-Process Execution Consistency.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dsa110_contimg.execution import (
    ErrorCode,
    convert_group_inprocess,
    convert_group_subprocess,
    convert_group_unified,
    create_task_from_group,
    execute_conversion,
)
from dsa110_contimg.execution.task import ExecutionTask, ResourceLimits


class TestCreateTaskFromGroup:
    """Tests for create_task_from_group adapter function."""

    def test_basic_task_creation(self, tmp_path: Path) -> None:
        """Test creating a task with minimal parameters."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        task = create_task_from_group(
            group_id="2025-06-01T12:00:00",
            input_dir=input_dir,
            output_dir=output_dir,
        )

        assert task.group_id == "2025-06-01T12:00:00"
        assert task.input_dir == input_dir
        assert task.output_dir == output_dir
        assert task.scratch_dir == output_dir / "scratch"

    def test_time_window_derivation(self, tmp_path: Path) -> None:
        """Test that time window is derived from group_id."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        task = create_task_from_group(
            group_id="2025-06-01T12:00:00",
            input_dir=input_dir,
            output_dir=output_dir,
        )

        # Start time should be ~1 minute before group_id
        expected_start = datetime(2025, 6, 1, 11, 59, 0)
        # End time should be ~10 minutes after group_id
        expected_end = datetime(2025, 6, 1, 12, 10, 0)

        assert task.start_time == expected_start.isoformat()
        assert task.end_time == expected_end.isoformat()

    def test_explicit_time_window(self, tmp_path: Path) -> None:
        """Test that explicit time window overrides derivation."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        task = create_task_from_group(
            group_id="2025-06-01T12:00:00",
            input_dir=input_dir,
            output_dir=output_dir,
            start_time="2025-06-01T00:00:00",
            end_time="2025-06-01T23:59:59",
        )

        assert task.start_time == "2025-06-01T00:00:00"
        assert task.end_time == "2025-06-01T23:59:59"

    def test_resource_limits(self, tmp_path: Path) -> None:
        """Test that resource limits are set correctly."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        task = create_task_from_group(
            group_id="2025-06-01T12:00:00",
            input_dir=input_dir,
            output_dir=output_dir,
            max_workers=8,
            omp_threads=4,
            memory_mb=16384,
            timeout_seconds=3600,
        )

        assert task.resource_limits.max_workers == 8
        assert task.resource_limits.omp_threads == 4
        assert task.resource_limits.memory_mb == 16384
        assert task.resource_limits.timeout_seconds == 3600

    def test_environment_overrides(self, tmp_path: Path) -> None:
        """Test that environment overrides are applied."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        task = create_task_from_group(
            group_id="2025-06-01T12:00:00",
            input_dir=input_dir,
            output_dir=output_dir,
            env_overrides={"CUSTOM_VAR": "custom_value"},
        )

        assert "HDF5_USE_FILE_LOCKING" in task.env_overrides
        assert task.env_overrides["CUSTOM_VAR"] == "custom_value"

    def test_tmpfs_staging(self, tmp_path: Path) -> None:
        """Test tmpfs staging configuration."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        task = create_task_from_group(
            group_id="2025-06-01T12:00:00",
            input_dir=input_dir,
            output_dir=output_dir,
            stage_to_tmpfs=True,
            tmpfs_path="/dev/shm/conversion",
        )

        assert task.stage_to_tmpfs is True
        assert task.tmpfs_path == Path("/dev/shm/conversion")


class TestExecuteConversion:
    """Tests for execute_conversion adapter function."""

    @patch("dsa110_contimg.execution.adapter.get_executor")
    def test_inprocess_execution(self, mock_get_executor: MagicMock, tmp_path: Path) -> None:
        """Test in-process execution returns correct format."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        # Mock executor
        mock_executor = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.writer_type = "parallel-subband"
        mock_result.metrics = MagicMock(total_time_s=10.0)
        mock_executor.run.return_value = mock_result
        mock_get_executor.return_value = mock_executor

        task = create_task_from_group(
            group_id="2025-06-01T12:00:00",
            input_dir=input_dir,
            output_dir=output_dir,
        )

        ret, writer, metrics = execute_conversion(task, mode="inprocess")

        assert ret == 0
        assert writer == "parallel-subband"
        assert metrics is not None
        mock_get_executor.assert_called_with("inprocess", timeout_seconds=None)

    @patch("dsa110_contimg.execution.adapter.get_executor")
    def test_subprocess_execution(self, mock_get_executor: MagicMock, tmp_path: Path) -> None:
        """Test subprocess execution returns correct format."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        mock_executor = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.writer_type = "direct-subband"
        mock_result.metrics = MagicMock()
        mock_executor.run.return_value = mock_result
        mock_get_executor.return_value = mock_executor

        task = create_task_from_group(
            group_id="2025-06-01T12:00:00",
            input_dir=input_dir,
            output_dir=output_dir,
        )

        ret, writer, metrics = execute_conversion(task, mode="subprocess")

        assert ret == 0
        assert writer == "direct-subband"
        mock_get_executor.assert_called_with("subprocess", timeout_seconds=None)

    @patch("dsa110_contimg.execution.adapter.get_executor")
    def test_legacy_subprocess_mode_flag(
        self, mock_get_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that legacy subprocess_mode flag forces subprocess execution."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        mock_executor = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.writer_type = "auto"
        mock_result.metrics = None
        mock_executor.run.return_value = mock_result
        mock_get_executor.return_value = mock_executor

        task = create_task_from_group(
            group_id="2025-06-01T12:00:00",
            input_dir=input_dir,
            output_dir=output_dir,
        )

        execute_conversion(task, mode="auto", subprocess_mode=True)

        # Should use subprocess mode despite mode="auto"
        mock_get_executor.assert_called_with("subprocess", timeout_seconds=None)

    @patch("dsa110_contimg.execution.adapter.get_executor")
    def test_failure_handling(self, mock_get_executor: MagicMock, tmp_path: Path) -> None:
        """Test that failures return correct error code."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        mock_executor = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_code = ErrorCode.OOM_ERROR
        mock_result.error_message = "Out of memory"
        mock_result.return_code = 137
        mock_result.metrics = None
        mock_executor.run.return_value = mock_result
        mock_get_executor.return_value = mock_executor

        task = create_task_from_group(
            group_id="2025-06-01T12:00:00",
            input_dir=input_dir,
            output_dir=output_dir,
        )

        ret, writer, metrics = execute_conversion(task)

        assert ret == 137
        assert writer is None
        assert metrics is None


class TestConvertGroupUnified:
    """Tests for convert_group_unified high-level function."""

    @patch("dsa110_contimg.execution.adapter.execute_conversion")
    @patch("dsa110_contimg.execution.adapter.create_task_from_group")
    def test_basic_call(
        self, mock_create_task: MagicMock, mock_execute: MagicMock, tmp_path: Path
    ) -> None:
        """Test basic unified conversion call."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        mock_task = MagicMock()
        mock_create_task.return_value = mock_task
        mock_execute.return_value = (0, "auto", None)

        ret, writer, metrics = convert_group_unified(
            group_id="2025-06-01T12:00:00",
            input_dir=str(input_dir),
            output_dir=str(output_dir),
        )

        assert ret == 0
        assert writer == "auto"
        mock_create_task.assert_called_once()
        mock_execute.assert_called_once_with(
            mock_task, mode="auto", subprocess_mode=False
        )

    @patch("dsa110_contimg.execution.adapter.execute_conversion")
    @patch("dsa110_contimg.execution.adapter.create_task_from_group")
    def test_inprocess_convenience(
        self, mock_create_task: MagicMock, mock_execute: MagicMock, tmp_path: Path
    ) -> None:
        """Test convert_group_inprocess convenience function."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        mock_task = MagicMock()
        mock_create_task.return_value = mock_task
        mock_execute.return_value = (0, "parallel-subband", None)

        ret, writer, metrics = convert_group_inprocess(
            group_id="2025-06-01T12:00:00",
            input_dir=str(input_dir),
            output_dir=str(output_dir),
        )

        assert ret == 0
        mock_execute.assert_called_once_with(
            mock_task, mode="inprocess", subprocess_mode=False
        )

    @patch("dsa110_contimg.execution.adapter.execute_conversion")
    @patch("dsa110_contimg.execution.adapter.create_task_from_group")
    def test_subprocess_convenience(
        self, mock_create_task: MagicMock, mock_execute: MagicMock, tmp_path: Path
    ) -> None:
        """Test convert_group_subprocess convenience function."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        mock_task = MagicMock()
        mock_create_task.return_value = mock_task
        mock_execute.return_value = (0, "direct-subband", None)

        ret, writer, metrics = convert_group_subprocess(
            group_id="2025-06-01T12:00:00",
            input_dir=str(input_dir),
            output_dir=str(output_dir),
        )

        assert ret == 0
        mock_execute.assert_called_once_with(
            mock_task, mode="subprocess", subprocess_mode=False
        )
