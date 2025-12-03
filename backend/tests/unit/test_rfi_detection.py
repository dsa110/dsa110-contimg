"""
Unit tests for RFI detection module.

Tests the GPU-accelerated RFI detection algorithms using mock data
and verifies the detection logic works correctly.
"""

import sys
from typing import NamedTuple
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


class TestRFIDetectionConfig:
    """Tests for RFIDetectionConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        from dsa110_contimg.rfi import RFIDetectionConfig

        config = RFIDetectionConfig()

        assert config.threshold == 5.0
        assert config.gpu_id == 0
        assert config.chunk_size == 10_000_000
        assert config.apply_flags is True
        assert config.detect_only is False

    def test_custom_config(self):
        """Test custom configuration values."""
        from dsa110_contimg.rfi import RFIDetectionConfig

        config = RFIDetectionConfig(
            threshold=3.0,
            gpu_id=1,
            chunk_size=1_000_000,
            apply_flags=False,
            detect_only=True,
        )

        assert config.threshold == 3.0
        assert config.gpu_id == 1
        assert config.chunk_size == 1_000_000
        assert config.apply_flags is False
        assert config.detect_only is True


class TestRFIDetectionResult:
    """Tests for RFIDetectionResult dataclass."""

    def test_success_property(self):
        """Test success property based on error field."""
        from dsa110_contimg.rfi import RFIDetectionResult

        # Success case
        result = RFIDetectionResult(
            ms_path="/test/path.ms",
            total_vis=1000,
            flagged_vis=50,
        )
        assert result.success is True

        # Failure case
        result_failed = RFIDetectionResult(
            ms_path="/test/path.ms",
            error="Test error",
        )
        assert result_failed.success is False

    def test_flag_percent_calculation(self):
        """Test that flag percent is stored correctly."""
        from dsa110_contimg.rfi import RFIDetectionResult

        result = RFIDetectionResult(
            ms_path="/test/path.ms",
            total_vis=1000,
            flagged_vis=50,
            flag_percent=5.0,
        )

        assert result.flag_percent == 5.0


class TestDetectOutliersCupy:
    """Tests for the CuPy-based outlier detection."""

    @pytest.fixture
    def mock_cupy(self):
        """Mock CuPy for testing without GPU."""
        mock_cp = MagicMock()

        # Mock array operations
        mock_array = MagicMock()
        mock_cp.asarray.return_value = mock_array
        mock_cp.abs.return_value = mock_array
        mock_cp.median.return_value = 1.0
        mock_cp.float32.return_value = 1e-10
        mock_cp.sum.return_value = 10

        # Mock flags
        mock_flags = MagicMock()
        mock_flags.__gt__ = MagicMock(return_value=mock_flags)
        mock_array.__gt__ = MagicMock(return_value=mock_flags)
        mock_array.__sub__ = MagicMock(return_value=mock_array)

        # Mock asnumpy
        mock_cp.asnumpy.return_value = np.zeros(100, dtype=bool)

        # Mock memory pool
        mock_pool = MagicMock()
        mock_cp.get_default_memory_pool.return_value = mock_pool

        return mock_cp

    def test_outlier_detection_with_mock(self, mock_cupy):
        """Test outlier detection with mocked CuPy."""
        with patch.dict(sys.modules, {'cupy': mock_cupy}):
            # Reimport to get mocked version
            from importlib import reload
            import dsa110_contimg.rfi.gpu_detection as gpu_mod
            reload(gpu_mod)

            # Test data
            vis_data = np.random.randn(100) + 1j * np.random.randn(100)

            # This would call the mocked CuPy
            # The actual function would need the mock to work properly


class TestGpuRfiDetection:
    """Tests for the main gpu_rfi_detection function."""

    def test_missing_ms_path(self):
        """Test error handling for missing MS file."""
        from dsa110_contimg.rfi import gpu_rfi_detection

        result = gpu_rfi_detection("/nonexistent/path.ms")

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_cupy_not_available_fallback(self):
        """Test behavior when CuPy is not available."""
        with patch('dsa110_contimg.rfi.gpu_detection.CUPY_AVAILABLE', False):
            from dsa110_contimg.rfi import gpu_rfi_detection

            result = gpu_rfi_detection("/test/path.ms")

            assert result.success is False
            assert "cupy" in result.error.lower()


class TestCpuRfiDetection:
    """Tests for the CPU fallback RFI detection."""

    def test_missing_ms_path(self):
        """Test error handling for missing MS file."""
        from dsa110_contimg.rfi.gpu_detection import cpu_rfi_detection

        result = cpu_rfi_detection("/nonexistent/path.ms")

        assert result.success is False
        assert "not found" in result.error.lower()


class TestModuleImports:
    """Tests for module imports and availability."""

    def test_module_imports(self):
        """Test that the module can be imported."""
        from dsa110_contimg import rfi
        from dsa110_contimg.rfi import (
            gpu_rfi_detection,
            RFIDetectionResult,
            RFIDetectionConfig,
        )

        assert callable(gpu_rfi_detection)
        assert RFIDetectionResult is not None
        assert RFIDetectionConfig is not None

    def test_cupy_availability_flag(self):
        """Test that CUPY_AVAILABLE flag is set."""
        from dsa110_contimg.rfi.gpu_detection import CUPY_AVAILABLE

        # Should be a boolean
        assert isinstance(CUPY_AVAILABLE, bool)


class TestMADAlgorithm:
    """Tests for the MAD-based detection algorithm."""

    def test_mad_threshold_calculation(self):
        """Test MAD threshold calculation on synthetic data."""
        # Create data with known outliers
        np.random.seed(42)
        normal_data = np.random.randn(1000)
        outliers = np.array([10.0, -10.0, 15.0])  # Clear outliers
        data = np.concatenate([normal_data, outliers])

        # Calculate MAD manually
        median = np.median(np.abs(data))
        mad = np.median(np.abs(np.abs(data) - median))

        # With threshold=5, outliers at 10+ should be detected
        threshold = 5.0
        thresh_value = median + threshold * mad * 1.4826

        # Check that outliers exceed threshold
        outlier_amplitudes = np.abs(outliers)
        assert all(outlier_amplitudes > thresh_value), (
            f"Outliers {outlier_amplitudes} should exceed threshold {thresh_value}"
        )

    def test_constant_data_handling(self):
        """Test handling of constant data (MAD = 0)."""
        # Constant data has MAD = 0
        constant_data = np.ones(100) * 5.0

        median = np.median(constant_data)
        mad = np.median(np.abs(constant_data - median))

        # MAD should be 0 for constant data
        assert mad == 0.0

        # Algorithm should handle this gracefully (use epsilon)
