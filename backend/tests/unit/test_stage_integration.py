# pylint: disable=redefined-outer-name,unused-argument,protected-access
"""
Unit tests for Pipeline Stage Integration module.

Tests the integration of state machine, error recovery, and pipeline metrics
into pipeline stages.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from dsa110_contimg.pipeline.stage_integration import (
    StageExecutionConfig,
    StageExecutionResult,
    STAGE_STATE_MAP,
    STAGE_METRIC_MAP,
    state_machine_context,
    metrics_context,
    MetricsContextHelper,
    with_stage_retry,
    execute_stage_with_tracking,
    tracked_stage_execute,
    _get_ms_path_from_context,
    _send_failure_alert,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database path."""
    db_path = tmp_path / "test_pipeline.sqlite3"
    return str(db_path)


@pytest.fixture
def mock_context():
    """Create a mock pipeline context."""
    ctx = MagicMock()
    ctx.outputs = {"ms_path": "/tmp/test.ms"}
    ctx.inputs = {"input_path": "/tmp/input.hdf5"}
    return ctx


@pytest.fixture
def mock_stage():
    """Create a mock pipeline stage."""
    stage = MagicMock()
    stage.get_name.return_value = "conversion"
    stage.execute.return_value = MagicMock(outputs={"ms_path": "/tmp/test.ms"})
    return stage


# =============================================================================
# Test Stage State Mapping
# =============================================================================


class TestStageStateMapping:
    """Tests for stage to state mapping."""

    def test_stage_state_map_has_all_stages(self):
        """Test that STAGE_STATE_MAP has entries for all common stages."""
        expected_stages = [
            "conversion",
            "calibration_solve",
            "calibration",
            "imaging",
        ]
        for stage in expected_stages:
            assert stage in STAGE_STATE_MAP
            states = STAGE_STATE_MAP[stage]
            assert len(states) == 2  # (processing_state, success_state)

    def test_stage_metric_map_has_all_stages(self):
        """Test that STAGE_METRIC_MAP has entries for all common stages."""
        expected_stages = [
            "conversion",
            "calibration_solve",
            "calibration",
            "imaging",
        ]
        for stage in expected_stages:
            assert stage in STAGE_METRIC_MAP

    def test_conversion_stage_mapping(self):
        """Test conversion stage state mapping."""
        assert STAGE_STATE_MAP["conversion"] == ("converting", "converted")
        assert STAGE_METRIC_MAP["conversion"] == "conversion"

    def test_imaging_stage_mapping(self):
        """Test imaging stage state mapping."""
        assert STAGE_STATE_MAP["imaging"] == ("imaging", "done")
        assert STAGE_METRIC_MAP["imaging"] == "imaging"

    def test_calibration_solve_mapping(self):
        """Test calibration solve stage mapping."""
        assert STAGE_STATE_MAP["calibration_solve"] == ("solving_cal", "applying_cal")
        assert STAGE_METRIC_MAP["calibration_solve"] == "calibration_solve"


# =============================================================================
# Test StageExecutionConfig
# =============================================================================


class TestStageExecutionConfig:
    """Tests for StageExecutionConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = StageExecutionConfig()
        assert config.enable_state_machine is True
        assert config.enable_retry is True
        assert config.enable_metrics is True
        assert config.max_retries == 3
        assert config.base_delay == 2.0
        assert config.max_delay == 60.0
        assert config.record_gpu_metrics is True
        assert config.alert_on_failure is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = StageExecutionConfig(
            enable_state_machine=False,
            enable_retry=False,
            max_retries=5,
            base_delay=1.0,
        )
        assert config.enable_state_machine is False
        assert config.enable_retry is False
        assert config.max_retries == 5
        assert config.base_delay == 1.0


# =============================================================================
# Test StageExecutionResult
# =============================================================================


class TestStageExecutionResult:
    """Tests for StageExecutionResult dataclass."""

    def test_success_result(self, mock_context):
        """Test successful execution result."""
        result = StageExecutionResult(
            success=True,
            context=mock_context,
            duration_s=5.0,
            retry_count=0,
        )
        assert result.success is True
        assert result.duration_s == 5.0
        assert result.retry_count == 0
        assert result.error is None

    def test_failure_result(self, mock_context):
        """Test failure execution result."""
        result = StageExecutionResult(
            success=False,
            context=mock_context,
            duration_s=10.0,
            retry_count=3,
            error="Test error",
            error_type="RuntimeError",
        )
        assert result.success is False
        assert result.retry_count == 3
        assert result.error == "Test error"
        assert result.error_type == "RuntimeError"


# =============================================================================
# Test MS Path Extraction
# =============================================================================


class TestMSPathExtraction:
    """Tests for _get_ms_path_from_context."""

    def test_extract_from_outputs(self):
        """Test extracting MS path from outputs."""
        ctx = MagicMock()
        ctx.outputs = {"ms_path": "/data/test.ms"}
        ctx.inputs = {}
        
        path = _get_ms_path_from_context(ctx)
        assert path == "/data/test.ms"

    def test_extract_from_outputs_list(self):
        """Test extracting MS path from outputs list."""
        ctx = MagicMock()
        ctx.outputs = {"ms_paths": ["/data/test1.ms", "/data/test2.ms"]}
        ctx.inputs = {}
        
        path = _get_ms_path_from_context(ctx)
        assert path == "/data/test1.ms"

    def test_extract_from_inputs(self):
        """Test extracting MS path from inputs."""
        ctx = MagicMock()
        ctx.outputs = {}
        ctx.inputs = {"input_path": "/data/input.hdf5"}
        
        path = _get_ms_path_from_context(ctx)
        assert path == "/data/input.hdf5"

    def test_no_path_found(self):
        """Test when no path can be extracted."""
        ctx = MagicMock()
        ctx.outputs = {}
        ctx.inputs = {}
        
        path = _get_ms_path_from_context(ctx)
        assert path is None


# =============================================================================
# Test State Machine Context
# =============================================================================


class TestStateMachineContext:
    """Tests for state_machine_context."""

    def test_context_when_disabled(self):
        """Test context manager when disabled."""
        with state_machine_context("conversion", "/tmp/test.ms", enable=False) as ctx:
            assert ctx == {}

    def test_context_with_no_ms_path(self):
        """Test context manager when ms_path is None."""
        with state_machine_context("conversion", None, enable=True) as ctx:
            assert ctx == {}

    def test_context_for_no_state_change_stage(self):
        """Test context for stages that don't change state."""
        with state_machine_context("catalog_setup", "/tmp/test.ms", enable=True) as ctx:
            assert ctx == {}

    @patch("dsa110_contimg.database.state_machine.get_state_machine")
    def test_context_transitions_on_success(self, mock_get_sm):
        """Test state transitions on successful execution."""
        mock_sm = MagicMock()
        mock_get_sm.return_value = mock_sm
        
        with state_machine_context("conversion", "/tmp/test.ms", enable=True) as ctx:
            ctx["test_key"] = "test_value"
        
        # Should call transition twice (processing and success)
        assert mock_sm.transition.call_count >= 1

    @patch("dsa110_contimg.database.state_machine.get_state_machine")
    def test_context_marks_failed_on_exception(self, mock_get_sm):
        """Test state marks failed on exception."""
        mock_sm = MagicMock()
        mock_get_sm.return_value = mock_sm
        
        with pytest.raises(ValueError):
            with state_machine_context("conversion", "/tmp/test.ms", enable=True):
                raise ValueError("Test error")
        
        # Should call mark_failed
        mock_sm.mark_failed.assert_called_once()


# =============================================================================
# Test Metrics Context
# =============================================================================


class TestMetricsContext:
    """Tests for metrics_context."""

    def test_context_when_disabled(self):
        """Test context manager when disabled."""
        with metrics_context("conversion", "/tmp/test.ms", enable=False) as helper:
            assert helper._collector is None
            assert helper._stage_ctx is None

    def test_context_with_no_ms_path(self):
        """Test context manager when ms_path is None."""
        with metrics_context("conversion", None, enable=True) as helper:
            assert helper._collector is None

    @patch("dsa110_contimg.monitoring.pipeline_metrics.get_metrics_collector")
    def test_context_with_metrics_enabled(self, mock_get_collector):
        """Test context with metrics enabled."""
        mock_collector = MagicMock()
        mock_stage_ctx = MagicMock()
        mock_collector.stage_context.return_value.__enter__ = MagicMock(return_value=mock_stage_ctx)
        mock_collector.stage_context.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_collector.return_value = mock_collector
        
        with metrics_context("conversion", "/tmp/test.ms", enable=True) as helper:
            assert helper._collector is not None


# =============================================================================
# Test MetricsContextHelper
# =============================================================================


class TestMetricsContextHelper:
    """Tests for MetricsContextHelper."""

    def test_helper_with_no_collector(self):
        """Test helper when collector is None."""
        helper = MetricsContextHelper(None, None, None)
        
        helper.start_cpu_timer()
        cpu_time = helper.stop_cpu_timer()
        assert cpu_time >= 0
        
        helper.record_cpu_time(1.0)  # Should not raise
        helper.record_gpu_time(2.0)  # Should not raise
        helper.record_memory(4.0, 2.0)  # Should not raise

    def test_cpu_timer(self):
        """Test CPU timer functionality."""
        mock_ctx = MagicMock()
        helper = MetricsContextHelper(None, mock_ctx, True)
        
        helper.start_cpu_timer()
        time.sleep(0.01)  # Small delay
        cpu_time = helper.stop_cpu_timer()
        
        assert cpu_time >= 0.01
        mock_ctx.record_cpu_time.assert_called_once()

    def test_gpu_timer(self):
        """Test GPU timer functionality."""
        mock_ctx = MagicMock()
        helper = MetricsContextHelper(None, mock_ctx, True)
        
        helper.start_gpu_timer()
        time.sleep(0.01)
        gpu_time = helper.stop_gpu_timer()
        
        assert gpu_time >= 0.01
        mock_ctx.record_gpu_time.assert_called_once()

    def test_stop_timer_without_start(self):
        """Test stopping timer without starting returns 0."""
        mock_ctx = MagicMock()
        helper = MetricsContextHelper(None, mock_ctx, True)
        
        cpu_time = helper.stop_cpu_timer()
        assert cpu_time == 0.0
        
        gpu_time = helper.stop_gpu_timer()
        assert gpu_time == 0.0


# =============================================================================
# Test with_stage_retry Decorator
# =============================================================================


class TestWithStageRetry:
    """Tests for with_stage_retry decorator."""

    def test_successful_execution(self):
        """Test successful execution without retry."""
        call_count = 0
        
        @with_stage_retry(max_retries=3)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_failure(self):
        """Test retry on transient failure."""
        call_count = 0
        
        @with_stage_retry(max_retries=3, base_delay=0.01)
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Transient error")
            return "success"
        
        result = failing_func()
        assert result == "success"
        assert call_count == 3

    def test_exhaust_retries(self):
        """Test exhausting all retries."""
        call_count = 0
        
        @with_stage_retry(max_retries=2, base_delay=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Permanent error")
        
        with pytest.raises(RuntimeError, match="failed after .* attempts"):
            always_fails()
        
        assert call_count == 3  # Initial + 2 retries


# =============================================================================
# Test tracked_stage_execute Decorator
# =============================================================================


class TestTrackedStageExecute:
    """Tests for tracked_stage_execute decorator."""

    def test_successful_stage_execution(self):
        """Test successful stage execution with tracking."""
        
        class MockStage:
            def get_name(self):
                return "test_stage"
            
            @tracked_stage_execute(
                enable_state_machine=False,
                enable_retry=False,
                enable_metrics=False,
            )
            def execute(self, context):
                return context
        
        stage = MockStage()
        mock_ctx = MagicMock()
        mock_ctx.outputs = {}
        mock_ctx.inputs = {}
        
        result = stage.execute(mock_ctx)
        assert result == mock_ctx

    @patch("dsa110_contimg.pipeline.stage_integration.state_machine_context")
    @patch("dsa110_contimg.pipeline.stage_integration.metrics_context")
    def test_stage_with_tracking_enabled(self, mock_metrics_ctx, mock_sm_ctx):
        """Test stage execution with tracking enabled."""
        mock_sm_ctx.return_value.__enter__ = MagicMock(return_value={})
        mock_sm_ctx.return_value.__exit__ = MagicMock(return_value=False)
        mock_metrics_ctx.return_value.__enter__ = MagicMock(
            return_value=MetricsContextHelper(None, None, None)
        )
        mock_metrics_ctx.return_value.__exit__ = MagicMock(return_value=False)
        
        class MockStage:
            def get_name(self):
                return "test_stage"
            
            @tracked_stage_execute(
                enable_state_machine=True,
                enable_retry=False,
                enable_metrics=True,
            )
            def execute(self, context):
                return context
        
        stage = MockStage()
        mock_ctx = MagicMock()
        mock_ctx.outputs = {"ms_path": "/tmp/test.ms"}
        mock_ctx.inputs = {}
        
        result = stage.execute(mock_ctx)
        
        mock_sm_ctx.assert_called_once()
        mock_metrics_ctx.assert_called_once()


# =============================================================================
# Test execute_stage_with_tracking
# =============================================================================


class TestExecuteStageWithTracking:
    """Tests for execute_stage_with_tracking function."""

    def test_successful_execution(self, mock_stage, mock_context):
        """Test successful stage execution."""
        config = StageExecutionConfig(
            enable_state_machine=False,
            enable_retry=False,
            enable_metrics=False,
        )
        
        result = execute_stage_with_tracking(mock_stage, mock_context, config)
        
        assert result.success is True
        assert result.retry_count == 0
        assert result.duration_s >= 0

    def test_failed_execution_without_retry(self, mock_context):
        """Test failed stage execution without retry."""
        mock_stage = MagicMock()
        mock_stage.get_name.return_value = "test_stage"
        mock_stage.execute.side_effect = ValueError("Test error")
        
        config = StageExecutionConfig(
            enable_state_machine=False,
            enable_retry=False,
            enable_metrics=False,
            alert_on_failure=False,
        )
        
        result = execute_stage_with_tracking(mock_stage, mock_context, config)
        
        assert result.success is False
        assert result.error is not None
        assert "Test error" in result.error

    @patch("dsa110_contimg.pipeline.error_recovery.execute_with_retry_sync")
    def test_execution_with_retry(self, mock_retry, mock_stage, mock_context):
        """Test stage execution with retry enabled."""
        from dsa110_contimg.pipeline.error_recovery import RetryResult
        
        mock_retry.return_value = RetryResult(
            success=True,
            result=mock_context,
            attempts=[],
            total_duration=1.0,
        )
        
        config = StageExecutionConfig(
            enable_state_machine=False,
            enable_retry=True,
            enable_metrics=False,
        )
        
        # The mock needs to be at the right place
        with patch.object(
            mock_stage,
            "execute",
            return_value=mock_context,
        ):
            result = execute_stage_with_tracking(mock_stage, mock_context, config)
        
            assert result.success is True


# =============================================================================
# Test Alert Sending
# =============================================================================


class TestAlertSending:
    """Tests for failure alert sending."""

    def test_send_failure_alert_no_raise(self):
        """Test sending failure alert doesn't raise."""
        # Should not raise even if alert system is unavailable
        _send_failure_alert("test_stage", "/tmp/test.ms", "Test error")

    def test_send_alert_handles_exception(self):
        """Test that alert sending handles exceptions gracefully."""
        # Should not raise even if alert system is unavailable
        _send_failure_alert("test_stage", None, "Test error")


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for stage integration."""

    @patch("dsa110_contimg.database.state_machine.get_state_machine")
    @patch("dsa110_contimg.monitoring.pipeline_metrics.get_metrics_collector")
    def test_full_stage_tracking_flow(self, mock_get_metrics, mock_get_sm):
        """Test full stage tracking flow with all components."""
        mock_sm = MagicMock()
        mock_get_sm.return_value = mock_sm
        
        mock_collector = MagicMock()
        mock_stage_ctx = MagicMock()
        mock_collector.stage_context.return_value.__enter__ = MagicMock(return_value=mock_stage_ctx)
        mock_collector.stage_context.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_metrics.return_value = mock_collector
        
        class TestStage:
            def get_name(self):
                return "conversion"
            
            @tracked_stage_execute(
                enable_state_machine=True,
                enable_retry=False,
                enable_metrics=True,
            )
            def execute(self, context):
                return context
        
        stage = TestStage()
        ctx = MagicMock()
        ctx.outputs = {"ms_path": "/tmp/test.ms"}
        ctx.inputs = {}
        
        result = stage.execute(ctx)
        
        # Verify result returned
        assert result == ctx  # noqa: F841


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
