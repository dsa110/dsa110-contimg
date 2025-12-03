"""
Integration tests for GPU safety with RFI detection.

These tests verify that the GPU safety guards work correctly
with the new RFI detection module.
"""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from dsa110_contimg.rfi import (
    RFIDetectionConfig,
    RFIDetectionResult,
    gpu_rfi_detection,
)
from dsa110_contimg.rfi.gpu_detection import cpu_rfi_detection, CUPY_AVAILABLE
from dsa110_contimg.utils.gpu_safety import (
    check_system_memory_available,
    initialize_gpu_safety,
    get_gpu_memory_info,
)


class TestGPUSafetyIntegration:
    """Tests for GPU safety integration with RFI module."""

    def test_safety_initialization(self):
        """Test that GPU safety module initializes correctly."""
        # Should not raise
        initialize_gpu_safety()

        # After initialization, memory checking should work
        is_safe, reason = check_system_memory_available(required_gb=6.0)
        assert isinstance(is_safe, bool)
        assert isinstance(reason, str)

    def test_gpu_memory_info_callable(self):
        """Test that GPU memory info function is callable."""
        # Should return a dict or handle no GPU gracefully
        try:
            usage = get_gpu_memory_info()
            if usage:
                assert isinstance(usage, dict)
        except RuntimeError:
            # Expected if no GPU available
            pass

    def test_rfi_detection_handles_missing_file(self):
        """Test that RFI detection handles missing files gracefully."""
        result = gpu_rfi_detection("/nonexistent/file.ms")

        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower()

    def test_cpu_fallback_handles_missing_file(self):
        """Test that CPU fallback handles missing files gracefully."""
        result = cpu_rfi_detection("/nonexistent/file.ms")

        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower()

    def test_rfi_config_respects_thresholds(self):
        """Test that RFI config properly stores threshold values."""
        config = RFIDetectionConfig(
            threshold=3.0,
            gpu_id=0,
            chunk_size=1_000_000,
        )

        assert config.threshold == 3.0
        assert config.chunk_size == 1_000_000

    def test_cupy_availability_detection(self):
        """Test that CuPy availability is properly detected."""
        # CUPY_AVAILABLE should be a boolean
        assert isinstance(CUPY_AVAILABLE, bool)

        if CUPY_AVAILABLE:
            # If CuPy is available, verify it imports
            import cupy as cp
            assert cp is not None
        else:
            # If not available, gpu_rfi_detection should report an error
            result = gpu_rfi_detection("/test.ms")
            assert not result.success or "cupy" in result.error.lower()


class TestRFIWithMockMS:
    """Tests with mock measurement set structures."""

    @pytest.fixture
    def mock_ms_directory(self):
        """Create a mock MS directory structure."""
        with tempfile.TemporaryDirectory(suffix=".ms") as tmpdir:
            ms_path = Path(tmpdir)

            # Create subdirectory structure
            for subdir in ["ANTENNA", "FIELD", "SPECTRAL_WINDOW"]:
                (ms_path / subdir).mkdir()
                (ms_path / subdir / "table.dat").touch()

            # Create main table marker
            (ms_path / "table.dat").touch()

            yield ms_path

    def test_detection_with_mock_ms_structure(self, mock_ms_directory):
        """Test RFI detection with mock MS directory structure."""
        # The mock MS exists as a directory but doesn't have valid CASA tables
        # This should fail gracefully with a table read error, not crash
        result = gpu_rfi_detection(str(mock_ms_directory))

        # Should fail because no valid DATA column
        assert result.success is False
        assert result.error is not None

    def test_cpu_fallback_with_mock_ms(self, mock_ms_directory):
        """Test CPU RFI detection with mock MS structure."""
        result = cpu_rfi_detection(str(mock_ms_directory))

        # Should fail gracefully
        assert result.success is False
        assert result.error is not None


class TestMADAlgorithmNumerics:
    """Test the numerical stability of MAD algorithm."""

    def test_mad_with_synthetic_data(self):
        """Test MAD calculation on synthetic visibility data."""
        np.random.seed(42)

        # Create synthetic visibility data with known outliers
        n_samples = 10000
        normal_vis = np.random.randn(n_samples) + 1j * np.random.randn(n_samples)
        normal_vis *= 10  # Scale up

        # Add 1% outliers
        n_outliers = 100
        outlier_indices = np.random.choice(n_samples, n_outliers, replace=False)
        normal_vis[outlier_indices] *= 100  # Make them 100x stronger

        # Calculate amplitude
        amplitude = np.abs(normal_vis)

        # Manual MAD calculation
        median_amp = np.median(amplitude)
        mad = np.median(np.abs(amplitude - median_amp))

        # MAD should be reasonable (not zero, not huge)
        assert mad > 0
        assert mad < np.max(amplitude)

        # With 5-sigma threshold, we should detect most outliers
        threshold = 5.0
        thresh_value = median_amp + threshold * mad * 1.4826
        detected = amplitude > thresh_value

        # Should detect most of the injected outliers
        detected_outliers = sum(detected[outlier_indices])
        assert detected_outliers > n_outliers * 0.5, (
            f"Only detected {detected_outliers}/{n_outliers} outliers"
        )

    def test_mad_with_constant_data(self):
        """Test MAD with constant data (edge case)."""
        constant_data = np.ones(1000) * 5.0

        median = np.median(constant_data)
        mad = np.median(np.abs(constant_data - median))

        # MAD should be 0 for constant data
        assert mad == 0.0

        # Algorithm should handle this with epsilon
        epsilon = 1e-10
        mad_safe = max(mad, epsilon)
        assert mad_safe == epsilon

    def test_mad_with_single_outlier(self):
        """Test MAD detection of single strong outlier."""
        # Normal data
        data = np.random.randn(1000)

        # Add one very strong outlier
        data[500] = 1000.0

        median = np.median(np.abs(data))
        mad = np.median(np.abs(np.abs(data) - median))

        # MAD should be robust to single outlier
        assert mad < 100  # Should not be dominated by outlier

        # But the outlier should exceed threshold
        threshold = 5.0
        thresh_value = median + threshold * mad * 1.4826
        assert np.abs(data[500]) > thresh_value


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    def test_config_to_result_flow(self):
        """Test configuration flows through to result."""
        config = RFIDetectionConfig(
            threshold=3.5,
            gpu_id=0,
            chunk_size=5_000_000,
        )

        # Run detection (will fail on missing file, but config should be used)
        result = gpu_rfi_detection("/test.ms", config=config)

        # Result should exist (even if failed)
        assert isinstance(result, RFIDetectionResult)
        assert result.ms_path == "/test.ms"

    def test_override_config_values(self):
        """Test that explicit parameters override config."""
        config = RFIDetectionConfig(
            threshold=3.0,
            gpu_id=1,
        )

        # Explicit threshold should override
        result = gpu_rfi_detection(
            "/test.ms",
            config=config,
            threshold=5.0,
        )

        # Should use threshold=5.0 (explicit override)
        assert result.threshold == 5.0
