"""
Unit tests for the refactored streaming module.

Tests the new modular streaming infrastructure including:
- SubbandQueue
- StreamingWatcher  
- StreamingWorker
- Pipeline stages
- Health and retry infrastructure
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# Skip if streaming module is not available
pytest.importorskip("dsa110_contimg.conversion.streaming")

from dsa110_contimg.conversion.streaming import (
    SubbandQueue,
    StreamingWatcher,
    StreamingWorker,
    WorkerConfig,
)
from dsa110_contimg.conversion.streaming.exceptions import (
    CalibrationError,
    ConversionError,
    DiskSpaceError,
    ImagingError,
    QueueError,
    ShutdownRequested,
    StreamingError,
    ValidationError,
)
from dsa110_contimg.conversion.streaming.health import (
    HealthCheck,
    HealthChecker,
    HealthStatus,
    PipelineMetrics,
)
from dsa110_contimg.conversion.streaming.retry import (
    RetryConfig,
    retry,
)


class TestSubbandQueue:
    """Tests for SubbandQueue class."""

    def test_queue_creation(self, tmp_path: Path) -> None:
        """Test queue can be created with default settings."""
        db_path = tmp_path / "test.db"
        queue = SubbandQueue(db_path, expected_subbands=16, chunk_duration_minutes=5.0)
        assert queue is not None
        queue.close()

    def test_record_subband(self, tmp_path: Path) -> None:
        """Test recording a subband file."""
        db_path = tmp_path / "test.db"
        queue = SubbandQueue(db_path, expected_subbands=16, chunk_duration_minutes=5.0)

        queue.record_subband("20231201_120000", 1, tmp_path / "sb01.hdf5")
        counts = queue.count_by_state()

        assert "collecting" in counts
        assert counts["collecting"] == 1
        queue.close()

    def test_multiple_subbands_same_group(self, tmp_path: Path) -> None:
        """Test recording multiple subbands in the same group."""
        db_path = tmp_path / "test.db"
        queue = SubbandQueue(db_path, expected_subbands=4, chunk_duration_minutes=5.0)

        for i in range(4):
            queue.record_subband("20231201_120000", i, tmp_path / f"sb{i:02d}.hdf5")

        counts = queue.count_by_state()
        # After all subbands arrive, group may transition to pending
        assert sum(counts.values()) >= 1
        queue.close()

    def test_group_info_retrieval(self, tmp_path: Path) -> None:
        """Test retrieving group information."""
        db_path = tmp_path / "test.db"
        queue = SubbandQueue(db_path, expected_subbands=16, chunk_duration_minutes=5.0)

        queue.record_subband("20231201_120000", 1, tmp_path / "sb01.hdf5")
        info = queue.get_group_info("20231201_120000")

        assert info is not None
        assert info["group_id"] == "20231201_120000"
        assert info["expected_subbands"] == 16
        queue.close()

    def test_count_by_state(self, tmp_path: Path) -> None:
        """Test counting groups by state."""
        db_path = tmp_path / "test.db"
        queue = SubbandQueue(db_path, expected_subbands=16, chunk_duration_minutes=5.0)

        # Add groups
        queue.record_subband("group1", 1, tmp_path / "g1_sb01.hdf5")
        queue.record_subband("group2", 1, tmp_path / "g2_sb01.hdf5")

        counts = queue.count_by_state()
        assert isinstance(counts, dict)
        queue.close()


class TestStreamingWatcher:
    """Tests for StreamingWatcher class."""

    def test_watcher_creation(self, tmp_path: Path) -> None:
        """Test watcher can be created."""
        db_path = tmp_path / "test.db"

        queue = SubbandQueue(db_path, expected_subbands=16, chunk_duration_minutes=5.0)
        watcher = StreamingWatcher(queue=queue)

        assert watcher is not None
        queue.close()


class TestWorkerConfig:
    """Tests for WorkerConfig dataclass."""

    def test_default_config(self, tmp_path: Path) -> None:
        """Test WorkerConfig with default values."""
        config = WorkerConfig(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            scratch_dir=tmp_path / "scratch",
            queue_db=tmp_path / "db.sqlite",
            registry_db=tmp_path / "registry.sqlite",
        )

        assert config.output_dir == tmp_path / "output"
        # Default values - note calibration solving is disabled by default
        assert config.enable_calibration_solving is False  # Default
        assert config.enable_photometry is True  # Default

    def test_custom_config(self, tmp_path: Path) -> None:
        """Test WorkerConfig with custom values."""
        config = WorkerConfig(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            scratch_dir=tmp_path / "scratch",
            queue_db=tmp_path / "db.sqlite",
            registry_db=tmp_path / "registry.sqlite",
            enable_calibration_solving=False,
            enable_photometry=False,
        )

        assert config.enable_calibration_solving is False
        assert config.enable_photometry is False


class TestExceptions:
    """Tests for streaming exception classes."""

    def test_streaming_error_base(self) -> None:
        """Test base StreamingError."""
        error = StreamingError("Test error")
        assert str(error) == "Test error"
        # Default retryable is False in the actual implementation
        assert error.retryable is False

    def test_conversion_error(self) -> None:
        """Test ConversionError."""
        error = ConversionError("Conversion failed", group_id="test_group")
        assert "Conversion failed" in str(error)
        assert error.group_id == "test_group"

    def test_calibration_error(self) -> None:
        """Test CalibrationError."""
        error = CalibrationError("Cal failed", retryable=False)
        assert error.retryable is False

    def test_imaging_error(self) -> None:
        """Test ImagingError."""
        error = ImagingError("Imaging failed")
        assert isinstance(error, StreamingError)

    def test_queue_error(self) -> None:
        """Test QueueError."""
        error = QueueError("Queue error")
        assert isinstance(error, StreamingError)

    def test_disk_space_error(self) -> None:
        """Test DiskSpaceError."""
        error = DiskSpaceError("Out of space", required_gb=100, available_gb=10)
        assert error.required_gb == 100
        assert error.available_gb == 10

    def test_validation_error(self) -> None:
        """Test ValidationError."""
        error = ValidationError("Invalid data", file_path="/tmp/test.hdf5")
        assert "Invalid data" in str(error)
        assert error.file_path == "/tmp/test.hdf5"

    def test_shutdown_requested(self) -> None:
        """Test ShutdownRequested exception."""
        error = ShutdownRequested("Graceful shutdown")
        assert isinstance(error, StreamingError)


class TestHealthInfrastructure:
    """Tests for health check infrastructure."""

    def test_health_status_enum(self) -> None:
        """Test HealthStatus enum values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_health_check_dataclass(self) -> None:
        """Test HealthCheck dataclass creation."""
        check = HealthCheck(
            name="test_check",
            status=HealthStatus.HEALTHY,
            message="All good",
            details={"latency_ms": 10},
        )

        assert check.name == "test_check"
        assert check.status == HealthStatus.HEALTHY
        assert check.message == "All good"
        assert check.details["latency_ms"] == 10
        assert check.checked_at > 0

    def test_health_checker_registration(self) -> None:
        """Test registering health checks."""
        checker = HealthChecker()

        def sample_check() -> HealthCheck:
            return HealthCheck(name="sample", status=HealthStatus.HEALTHY)

        checker.register_check("sample", sample_check)
        result = checker.run_check("sample")

        assert result is not None
        assert result.status == HealthStatus.HEALTHY

    def test_health_checker_unregister(self) -> None:
        """Test unregistering health checks."""
        checker = HealthChecker()

        def sample_check() -> HealthCheck:
            return HealthCheck(name="sample", status=HealthStatus.HEALTHY)

        checker.register_check("sample", sample_check)
        checker.unregister_check("sample")
        result = checker.run_check("sample")

        assert result is None

    def test_pipeline_metrics(self) -> None:
        """Test PipelineMetrics dataclass."""
        metrics = PipelineMetrics()

        assert metrics.groups_processed == 0
        assert metrics.groups_failed == 0
        assert metrics.queue_pending == 0

        metrics.groups_processed = 10
        metrics.groups_failed = 2
        assert metrics.groups_processed == 10
        assert metrics.groups_failed == 2


class TestRetryInfrastructure:
    """Tests for retry infrastructure."""

    def test_retry_config_defaults(self) -> None:
        """Test RetryConfig default values."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.initial_delay_s == 1.0
        assert config.max_delay_s == 60.0
        assert config.exponential_base == 2.0

    def test_retry_config_custom(self) -> None:
        """Test RetryConfig with custom values."""
        config = RetryConfig(
            max_attempts=5,
            initial_delay_s=0.5,
            max_delay_s=30.0,
        )

        assert config.max_attempts == 5
        assert config.initial_delay_s == 0.5
        assert config.max_delay_s == 30.0

    def test_retry_config_should_retry(self) -> None:
        """Test should_retry method."""
        config = RetryConfig(max_attempts=3, retryable_exceptions=(ValueError,))

        # Should retry on first attempt
        assert config.should_retry(ValueError("test"), 1) is True

        # Should not retry after max attempts
        assert config.should_retry(ValueError("test"), 3) is False

        # Should not retry non-retryable exceptions
        assert config.should_retry(TypeError("test"), 1) is False

    def test_retry_config_get_delay(self) -> None:
        """Test delay calculation."""
        config = RetryConfig(
            initial_delay_s=1.0,
            max_delay_s=10.0,
            exponential_base=2.0,
            jitter_factor=0,  # No jitter for deterministic test
        )

        delay1 = config.get_delay(1)
        delay2 = config.get_delay(2)
        delay3 = config.get_delay(3)

        # Exponential backoff: 1, 2, 4 (capped at 10)
        assert delay1 == 1.0
        assert delay2 == 2.0
        assert delay3 == 4.0

    def test_retry_decorator_success(self) -> None:
        """Test retry decorator with successful function."""
        config = RetryConfig(max_attempts=3, retryable_exceptions=(ValueError,))

        @retry(config=config)
        def success_fn() -> str:
            return "success"

        result = success_fn()
        assert result == "success"

    def test_retry_decorator_eventual_success(self) -> None:
        """Test retry decorator with eventual success."""
        config = RetryConfig(
            max_attempts=3,
            initial_delay_s=0.01,
            retryable_exceptions=(ValueError,),
        )

        attempt_count = 0

        @retry(config=config)
        def flaky_fn() -> str:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Simulated error")
            return "success"

        result = flaky_fn()
        assert result == "success"
        assert attempt_count == 3

    def test_retry_decorator_exhausted(self) -> None:
        """Test retry decorator when retries exhausted."""
        config = RetryConfig(
            max_attempts=2,
            initial_delay_s=0.01,
            retryable_exceptions=(ValueError,),
        )

        @retry(config=config)
        def always_fail() -> str:
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_fail()


class TestStageImports:
    """Tests for pipeline stage imports."""

    def test_conversion_stage_import(self) -> None:
        """Test ConversionStage can be imported."""
        from dsa110_contimg.conversion.streaming.stages import ConversionStage

        assert ConversionStage is not None

    def test_calibration_stage_import(self) -> None:
        """Test CalibrationStage can be imported."""
        from dsa110_contimg.conversion.streaming.stages import CalibrationStage

        assert CalibrationStage is not None

    def test_imaging_stage_import(self) -> None:
        """Test ImagingStage can be imported."""
        from dsa110_contimg.conversion.streaming.stages import ImagingStage

        assert ImagingStage is not None

    def test_photometry_stage_import(self) -> None:
        """Test PhotometryStage can be imported."""
        from dsa110_contimg.conversion.streaming.stages import PhotometryStage

        assert PhotometryStage is not None

    def test_mosaic_stage_import(self) -> None:
        """Test MosaicStage can be imported."""
        from dsa110_contimg.conversion.streaming.stages import MosaicStage

        assert MosaicStage is not None


class TestCLIModule:
    """Tests for CLI module."""

    def test_cli_imports(self) -> None:
        """Test CLI module can be imported."""
        from dsa110_contimg.conversion.streaming.cli import build_parser, main

        assert build_parser is not None
        assert main is not None

    def test_parser_creation(self) -> None:
        """Test argument parser can be created."""
        from dsa110_contimg.conversion.streaming.cli import build_parser

        parser = build_parser()
        assert parser is not None
        assert parser.description is not None

    def test_parser_required_args(self) -> None:
        """Test parser has required arguments."""
        from dsa110_contimg.conversion.streaming.cli import build_parser

        parser = build_parser()

        # Check that required arguments exist
        actions = {a.dest: a for a in parser._actions}
        assert "input_dir" in actions
        assert "output_dir" in actions


class TestModuleExports:
    """Tests for module-level exports."""

    def test_all_exports_available(self) -> None:
        """Test all expected exports are available."""
        from dsa110_contimg.conversion.streaming import (
            CalibrationStage,
            ConversionStage,
            ImagingStage,
            MosaicStage,
            PhotometryStage,
            StreamingPipeline,
            StreamingWatcher,
            StreamingWorker,
            SubbandQueue,
            WorkerConfig,
            run_streaming_pipeline,
        )

        # All should be non-None
        assert SubbandQueue is not None
        assert StreamingWatcher is not None
        assert StreamingWorker is not None
        assert WorkerConfig is not None
        assert ConversionStage is not None
        assert CalibrationStage is not None
        assert ImagingStage is not None
        assert PhotometryStage is not None
        assert MosaicStage is not None
        assert run_streaming_pipeline is not None
        assert StreamingPipeline is not None
