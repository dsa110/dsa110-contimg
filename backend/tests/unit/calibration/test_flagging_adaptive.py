"""
Tests for adaptive RFI flagging module.

Tests the CalibrationFailure exception and flag_rfi_adaptive function.
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

from dsa110_contimg.calibration.flagging_adaptive import (
    CalibrationFailure,
    flag_rfi_adaptive,
    flag_rfi_with_gpu_fallback,
    FlaggingStrategy,
    AdaptiveFlaggingResult,
    DEFAULT_STRATEGY_CHAIN,
    _get_flag_fraction,
)


class TestCalibrationFailure:
    """Tests for CalibrationFailure exception."""

    def test_exception_can_be_raised(self):
        """Test that CalibrationFailure can be raised and caught."""
        with pytest.raises(CalibrationFailure) as exc_info:
            raise CalibrationFailure("Calibration failed")
        assert "Calibration failed" in str(exc_info.value)

    def test_exception_is_exception_subclass(self):
        """Test that CalibrationFailure is an Exception subclass."""
        assert issubclass(CalibrationFailure, Exception)

    def test_exception_message_preserved(self):
        """Test that exception message is preserved."""
        msg = "Bandpass calibration failed: SNR too low"
        exc = CalibrationFailure(msg)
        assert str(exc) == msg


class TestFlaggingStrategy:
    """Tests for FlaggingStrategy dataclass."""

    def test_default_strategy_creation(self):
        """Test creating a default strategy."""
        strategy = FlaggingStrategy(
            name="test",
            backend="aoflagger",
        )
        assert strategy.name == "test"
        assert strategy.backend == "aoflagger"
        assert strategy.strategy_file is None
        assert strategy.aggressive is False
        assert strategy.threshold_scale == 1.0
        assert strategy.use_gpu is False

    def test_custom_strategy_creation(self):
        """Test creating a custom strategy."""
        strategy = FlaggingStrategy(
            name="aggressive_gpu",
            backend="casa",
            strategy_file="/path/to/strategy.lua",
            aggressive=True,
            threshold_scale=0.8,
            use_gpu=True,
        )
        assert strategy.name == "aggressive_gpu"
        assert strategy.backend == "casa"
        assert strategy.strategy_file == "/path/to/strategy.lua"
        assert strategy.aggressive is True
        assert strategy.threshold_scale == 0.8
        assert strategy.use_gpu is True


class TestDefaultStrategyChain:
    """Tests for the default strategy chain."""

    def test_chain_has_expected_length(self):
        """Test that default chain has expected number of strategies."""
        assert len(DEFAULT_STRATEGY_CHAIN) >= 2

    def test_chain_starts_with_default(self):
        """Test that chain starts with default strategy."""
        assert DEFAULT_STRATEGY_CHAIN[0].name == "default"
        assert DEFAULT_STRATEGY_CHAIN[0].aggressive is False

    def test_chain_has_aggressive_strategy(self):
        """Test that chain includes an aggressive strategy."""
        aggressive_strategies = [s for s in DEFAULT_STRATEGY_CHAIN if s.aggressive]
        assert len(aggressive_strategies) >= 1


class TestAdaptiveFlaggingResult:
    """Tests for AdaptiveFlaggingResult TypedDict."""

    def test_result_creation(self):
        """Test creating a result dict."""
        result: AdaptiveFlaggingResult = {
            "success": True,
            "strategy": "default",
            "attempts": 1,
            "flagged_fraction": 0.15,
            "calibration_error": None,
            "processing_time_s": 5.2,
        }
        assert result["success"] is True
        assert result["strategy"] == "default"
        assert result["attempts"] == 1
        assert result["flagged_fraction"] == 0.15


class TestFlagRfiAdaptive:
    """Tests for the flag_rfi_adaptive function."""

    def test_successful_on_first_attempt(self):
        """Test adaptive flagging succeeds on first attempt."""
        mock_calibrate = MagicMock()  # Doesn't raise = success

        with patch(
            "dsa110_contimg.calibration.flagging_adaptive._apply_flagging_strategy"
        ) as mock_apply:
            mock_apply.return_value = 0.10  # 10% flagged

            result = flag_rfi_adaptive(
                ms_path="/test/path.ms",
                refant="103",
                calibrate_fn=mock_calibrate,
            )

        assert result["success"] is True
        assert result["attempts"] == 1
        assert result["strategy"] == "default"
        mock_calibrate.assert_called_once()

    def test_falls_back_on_calibration_failure(self):
        """Test adaptive flagging falls back to aggressive on failure."""
        call_count = [0]

        def mock_calibrate(ms_path, refant, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise CalibrationFailure("First attempt failed")
            # Second attempt succeeds

        with patch(
            "dsa110_contimg.calibration.flagging_adaptive._apply_flagging_strategy"
        ) as mock_apply:
            mock_apply.return_value = 0.15

            result = flag_rfi_adaptive(
                ms_path="/test/path.ms",
                refant="103",
                calibrate_fn=mock_calibrate,
            )

        assert result["success"] is True
        assert result["attempts"] == 2
        assert result["strategy"] == "aggressive"

    def test_returns_failure_when_all_strategies_exhausted(self):
        """Test adaptive flagging fails when all strategies exhausted."""

        def mock_calibrate(ms_path, refant, **kwargs):
            raise CalibrationFailure("Always fails")

        with patch(
            "dsa110_contimg.calibration.flagging_adaptive._apply_flagging_strategy"
        ) as mock_apply:
            mock_apply.return_value = 0.20

            result = flag_rfi_adaptive(
                ms_path="/test/path.ms",
                refant="103",
                calibrate_fn=mock_calibrate,
                max_attempts=2,
            )

        assert result["success"] is False
        assert result["attempts"] == 2
        assert result["calibration_error"] is not None

    def test_custom_strategy_chain(self):
        """Test using a custom strategy chain."""
        custom_chain = [
            FlaggingStrategy(name="custom1", backend="casa"),
            FlaggingStrategy(name="custom2", backend="aoflagger", aggressive=True),
        ]

        call_count = [0]

        def mock_calibrate(ms_path, refant, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise CalibrationFailure("First attempt failed")

        with patch(
            "dsa110_contimg.calibration.flagging_adaptive._apply_flagging_strategy"
        ) as mock_apply:
            mock_apply.return_value = 0.12

            result = flag_rfi_adaptive(
                ms_path="/test/path.ms",
                refant="103",
                calibrate_fn=mock_calibrate,
                strategy_chain=custom_chain,
            )

        assert result["success"] is True
        assert result["strategy"] == "custom2"

    def test_use_gpu_rfi_prepends_gpu_strategy(self):
        """Test that use_gpu_rfi=True adds GPU strategy to chain."""
        mock_calibrate = MagicMock()

        with patch(
            "dsa110_contimg.calibration.flagging_adaptive._apply_flagging_strategy"
        ) as mock_apply:
            mock_apply.return_value = 0.08

            result = flag_rfi_adaptive(
                ms_path="/test/path.ms",
                refant="103",
                calibrate_fn=mock_calibrate,
                use_gpu_rfi=True,
            )

        # Should succeed with GPU strategy first
        assert result["success"] is True
        assert result["strategy"] == "gpu_default"


class TestFlagRfiWithGpuFallback:
    """Tests for flag_rfi_with_gpu_fallback function."""

    def test_falls_back_to_standard_when_gpu_unavailable(self):
        """Test fallback to standard flagging when GPU not available."""
        with patch(
            "dsa110_contimg.calibration.flagging.flag_rfi"
        ) as mock_flag_rfi, patch(
            "dsa110_contimg.calibration.flagging_adaptive._get_flag_fraction"
        ) as mock_fraction:
            mock_fraction.return_value = 0.12

            result = flag_rfi_with_gpu_fallback(
                ms_path="/test/path.ms",
                prefer_gpu=False,  # Skip GPU
            )

        assert result["success"] is True
        assert result["method"] == "aoflagger"
        mock_flag_rfi.assert_called_once()

    def test_uses_custom_backend(self):
        """Test using custom backend."""
        with patch(
            "dsa110_contimg.calibration.flagging.flag_rfi"
        ) as mock_flag_rfi, patch(
            "dsa110_contimg.calibration.flagging_adaptive._get_flag_fraction"
        ) as mock_fraction:
            mock_fraction.return_value = 0.15

            result = flag_rfi_with_gpu_fallback(
                ms_path="/test/path.ms",
                backend="casa",
                prefer_gpu=False,
            )

        assert result["method"] == "casa"
        mock_flag_rfi.assert_called_once_with(
            "/test/path.ms", backend="casa", strategy=None
        )


class TestModuleExports:
    """Test that module exports are correct."""

    def test_exports_available(self):
        """Test that all expected exports are available."""
        from dsa110_contimg.calibration.flagging_adaptive import (
            CalibrationFailure,
            flag_rfi_adaptive,
            flag_rfi_with_gpu_fallback,
            FlaggingStrategy,
            AdaptiveFlaggingResult,
            DEFAULT_STRATEGY_CHAIN,
        )

        assert CalibrationFailure is not None
        assert callable(flag_rfi_adaptive)
        assert callable(flag_rfi_with_gpu_fallback)
        assert FlaggingStrategy is not None
        assert len(DEFAULT_STRATEGY_CHAIN) > 0

    def test_exports_from_calibration_init(self):
        """Test that exports are available from calibration package."""
        from dsa110_contimg.calibration import (
            CalibrationFailure,
            flag_rfi_adaptive,
            flag_rfi_with_gpu_fallback,
        )

        assert CalibrationFailure is not None
        assert callable(flag_rfi_adaptive)
        assert callable(flag_rfi_with_gpu_fallback)
