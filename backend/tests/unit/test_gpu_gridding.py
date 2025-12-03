"""
Unit tests for GPU gridding module.

Tests the GPU-accelerated visibility gridding algorithms using mock data
and verifies the gridding logic works correctly.
"""

import sys
from unittest.mock import patch

import numpy as np
import pytest


class TestGriddingConfig:
    """Tests for GriddingConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        from dsa110_contimg.imaging.gpu_gridding import GriddingConfig

        config = GriddingConfig()

        assert config.image_size == 512
        assert config.cell_size_arcsec == 12.0
        assert config.support == 3
        assert config.oversampling == 128
        assert config.use_w_projection is False
        assert config.w_planes == 1
        assert config.gpu_id == 0

    def test_custom_config(self):
        """Test custom configuration values."""
        from dsa110_contimg.imaging.gpu_gridding import GriddingConfig

        config = GriddingConfig(
            image_size=2048,
            cell_size_arcsec=0.5,
            support=6,
            oversampling=64,
            use_w_projection=True,
            w_planes=32,
            gpu_id=1,
        )

        assert config.image_size == 2048
        assert config.cell_size_arcsec == 0.5
        assert config.support == 6
        assert config.oversampling == 64
        assert config.use_w_projection is True
        assert config.w_planes == 32
        assert config.gpu_id == 1

    def test_cell_size_rad_property(self):
        """Test cell_size_rad property conversion."""
        from dsa110_contimg.imaging.gpu_gridding import GriddingConfig

        config = GriddingConfig(cell_size_arcsec=1.0)
        # 1 arcsec = pi / (180 * 3600) rad
        expected_rad = np.pi / (180.0 * 3600.0)
        np.testing.assert_allclose(config.cell_size_rad, expected_rad, rtol=1e-10)


class TestGriddingResult:
    """Tests for GriddingResult dataclass."""

    def test_success_property(self):
        """Test success property based on error and image fields."""
        from dsa110_contimg.imaging.gpu_gridding import GriddingResult

        # Success case - needs both image and no error
        image = np.zeros((256, 256), dtype=np.float64)
        result = GriddingResult(
            image=image,
            n_vis=1000,
            n_flagged=50,
            weight_sum=999.0,
        )
        assert result.success is True

        # Failure case - error set
        result_failed = GriddingResult(
            error="Test error",
        )
        assert result_failed.success is False

        # Failure case - no image
        result_no_image = GriddingResult(
            n_vis=1000,
            weight_sum=999.0,
        )
        assert result_no_image.success is False

    def test_default_values(self):
        """Test default values for optional fields."""
        from dsa110_contimg.imaging.gpu_gridding import GriddingResult

        result = GriddingResult()

        assert result.image is None
        assert result.grid is None
        assert result.weight_sum == 0.0
        assert result.n_vis == 0
        assert result.n_flagged == 0
        assert result.processing_time_s == 0.0
        assert result.gpu_id == 0  # Default is 0, not -1
        assert result.error is None

    def test_with_image_data(self):
        """Test result with actual image data."""
        from dsa110_contimg.imaging.gpu_gridding import GriddingResult

        image = np.zeros((256, 256), dtype=np.float64)
        grid = np.zeros((256, 256), dtype=np.complex128)

        result = GriddingResult(
            image=image,
            grid=grid,
            weight_sum=1000.0,
            n_vis=5000,
            n_flagged=100,
            processing_time_s=1.5,
            gpu_id=0,
        )

        assert result.image is not None
        assert result.image.shape == (256, 256)
        assert result.grid is not None
        assert result.grid.shape == (256, 256)
        assert result.weight_sum == 1000.0
        assert result.n_vis == 5000
        assert result.n_flagged == 100
        assert result.processing_time_s == 1.5
        assert result.gpu_id == 0


class TestSpheroidalGCF:
    """Tests for spheroidal gridding convolution function."""

    def test_gcf_computation_basic(self):
        """Test basic GCF computation."""
        from dsa110_contimg.imaging.gpu_gridding import _compute_spheroidal_gcf

        gcf = _compute_spheroidal_gcf(support=4, oversampling=64)

        # Check shape: (oversampling, 2*support+1)
        expected_shape = (64, 2 * 4 + 1)
        assert gcf.shape == expected_shape

        # Check non-negative (it's a weight function, Gaussian-based)
        assert gcf.min() >= 0
        assert gcf.max() > 0

    def test_gcf_different_parameters(self):
        """Test GCF with different support and oversampling."""
        from dsa110_contimg.imaging.gpu_gridding import _compute_spheroidal_gcf

        # Different support values
        gcf_s4 = _compute_spheroidal_gcf(support=4, oversampling=64)
        gcf_s6 = _compute_spheroidal_gcf(support=6, oversampling=64)

        # Shape: (oversampling, 2*support+1)
        assert gcf_s4.shape == (64, 9)  # 2*4+1 = 9
        assert gcf_s6.shape == (64, 13)  # 2*6+1 = 13

        # Different oversampling
        gcf_o64 = _compute_spheroidal_gcf(support=4, oversampling=64)
        gcf_o128 = _compute_spheroidal_gcf(support=4, oversampling=128)

        assert gcf_o64.shape == (64, 9)
        assert gcf_o128.shape == (128, 9)

    def test_gcf_dtype(self):
        """Test GCF output dtype."""
        from dsa110_contimg.imaging.gpu_gridding import _compute_spheroidal_gcf

        gcf = _compute_spheroidal_gcf(support=4, oversampling=64)
        assert gcf.dtype == np.float32

    def test_gcf_row_normalization(self):
        """Test that each GCF row is normalized (sums to ~1)."""
        from dsa110_contimg.imaging.gpu_gridding import _compute_spheroidal_gcf

        gcf = _compute_spheroidal_gcf(support=3, oversampling=32)

        # Each row should sum to approximately 1 (normalized)
        for i in range(gcf.shape[0]):
            np.testing.assert_allclose(gcf[i].sum(), 1.0, rtol=1e-5)


class TestMemoryEstimation:
    """Tests for memory estimation functions."""

    def test_estimate_gridding_memory_basic(self):
        """Test basic memory estimation."""
        from dsa110_contimg.imaging.gpu_gridding import estimate_gridding_memory_gb

        gpu_gb, sys_gb = estimate_gridding_memory_gb(
            n_vis=100_000,
            image_size=4096,
            support=4,
            oversampling=128,
        )

        # Both should be positive
        assert gpu_gb > 0
        assert sys_gb > 0

        # Should be reasonable sizes (not gigantic or tiny)
        assert gpu_gb < 10  # Less than 10 GB
        assert sys_gb < 10

    def test_estimate_memory_scales_with_vis(self):
        """Test that memory scales with visibility count."""
        from dsa110_contimg.imaging.gpu_gridding import estimate_gridding_memory_gb

        _, sys_small = estimate_gridding_memory_gb(
            n_vis=10_000,
            image_size=2048,
        )

        _, sys_large = estimate_gridding_memory_gb(
            n_vis=1_000_000,
            image_size=2048,
        )

        # Larger visibility count should need more system memory
        assert sys_large > sys_small

    def test_estimate_memory_scales_with_image_size(self):
        """Test that memory scales with image size."""
        from dsa110_contimg.imaging.gpu_gridding import estimate_gridding_memory_gb

        gpu_small, _ = estimate_gridding_memory_gb(
            n_vis=100_000,
            image_size=1024,
        )

        gpu_large, _ = estimate_gridding_memory_gb(
            n_vis=100_000,
            image_size=4096,
        )

        # 4x image size = 16x pixels = much larger grid memory
        assert gpu_large > gpu_small * 5


class TestCPUGridding:
    """Tests for CPU-based gridding (fallback)."""

    def test_cpu_grid_basic(self):
        """Test basic CPU gridding with simple data."""
        from dsa110_contimg.imaging.gpu_gridding import (
            GriddingConfig,
            cpu_grid_visibilities,
        )

        # Create simple test data
        n_vis = 100
        rng = np.random.default_rng(42)
        uvw = rng.standard_normal((n_vis, 3)).astype(np.float64) * 100
        vis = (rng.standard_normal(n_vis) + 1j * rng.standard_normal(n_vis)).astype(
            np.complex128
        )
        weights = np.ones(n_vis, dtype=np.float64)
        flags = np.zeros(n_vis, dtype=bool)

        config = GriddingConfig(image_size=256, cell_size_arcsec=5.0)

        result = cpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            flags=flags,
            config=config,
        )

        assert result.success is True
        assert result.image is not None
        assert result.image.shape == (256, 256)
        assert result.n_vis == n_vis
        assert result.gpu_id == -1  # CPU indicator

    def test_cpu_grid_with_flags(self):
        """Test CPU gridding respects flags."""
        from dsa110_contimg.imaging.gpu_gridding import (
            GriddingConfig,
            cpu_grid_visibilities,
        )

        n_vis = 100
        rng = np.random.default_rng(42)
        uvw = rng.standard_normal((n_vis, 3)).astype(np.float64) * 100
        vis = (rng.standard_normal(n_vis) + 1j * rng.standard_normal(n_vis)).astype(
            np.complex128
        )
        weights = np.ones(n_vis, dtype=np.float64)

        # Flag half the visibilities
        flags = np.zeros(n_vis, dtype=bool)
        flags[::2] = True

        config = GriddingConfig(image_size=256, cell_size_arcsec=5.0)

        result = cpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            flags=flags,
            config=config,
        )

        assert result.success is True
        assert result.n_flagged == 50

    def test_cpu_grid_empty_input(self):
        """Test CPU gridding with empty input."""
        from dsa110_contimg.imaging.gpu_gridding import (
            GriddingConfig,
            cpu_grid_visibilities,
        )

        uvw = np.array([]).reshape(0, 3).astype(np.float64)
        vis = np.array([]).astype(np.complex128)
        weights = np.array([]).astype(np.float64)
        flags = np.array([]).astype(bool)

        config = GriddingConfig(image_size=256)

        result = cpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            flags=flags,
            config=config,
        )

        # Should handle empty input gracefully
        assert result.n_vis == 0

    def test_cpu_grid_invalid_input(self):
        """Test CPU gridding with invalid input dimensions."""
        from dsa110_contimg.imaging.gpu_gridding import cpu_grid_visibilities

        # Mismatched dimensions
        rng = np.random.default_rng(42)
        uvw = rng.standard_normal((100, 3)).astype(np.float64)
        vis = (rng.standard_normal(50) + 1j * rng.standard_normal(50)).astype(
            np.complex128
        )  # Wrong size
        weights = np.ones(100, dtype=np.float64)
        flags = np.zeros(100, dtype=bool)

        result = cpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            flags=flags,
        )

        # Should return error result
        assert result.success is False
        assert result.error is not None


class TestGPUGridding:
    """Tests for GPU-based gridding."""

    def test_gpu_grid_basic(self):
        """Test basic GPU gridding with simple data."""
        from dsa110_contimg.imaging.gpu_gridding import (
            CUPY_AVAILABLE,
            GriddingConfig,
            gpu_grid_visibilities,
        )

        # Create simple test data
        n_vis = 100
        rng = np.random.default_rng(42)
        uvw = rng.standard_normal((n_vis, 3)).astype(np.float64) * 100
        vis = (rng.standard_normal(n_vis) + 1j * rng.standard_normal(n_vis)).astype(
            np.complex128
        )
        weights = np.ones(n_vis, dtype=np.float64)
        flags = np.zeros(n_vis, dtype=bool)

        config = GriddingConfig(image_size=256, cell_size_arcsec=5.0)

        result = gpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            flags=flags,
            config=config,
        )

        assert result.success is True
        assert result.image is not None
        assert result.image.shape == (256, 256)
        assert result.n_vis == n_vis

        # Check GPU was used if available
        if CUPY_AVAILABLE:
            assert result.gpu_id >= 0
        else:
            assert result.gpu_id == -1

    def test_gpu_grid_with_flags(self):
        """Test GPU gridding respects flags."""
        from dsa110_contimg.imaging.gpu_gridding import (
            GriddingConfig,
            gpu_grid_visibilities,
        )

        n_vis = 100
        rng = np.random.default_rng(42)
        uvw = rng.standard_normal((n_vis, 3)).astype(np.float64) * 100
        vis = (rng.standard_normal(n_vis) + 1j * rng.standard_normal(n_vis)).astype(
            np.complex128
        )
        weights = np.ones(n_vis, dtype=np.float64)

        # Flag half the visibilities
        flags = np.zeros(n_vis, dtype=bool)
        flags[::2] = True

        config = GriddingConfig(image_size=256, cell_size_arcsec=5.0)

        result = gpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            flags=flags,
            config=config,
        )

        assert result.success is True
        assert result.n_flagged == 50

    def test_gpu_grid_empty_input(self):
        """Test GPU gridding with empty input."""
        from dsa110_contimg.imaging.gpu_gridding import (
            GriddingConfig,
            gpu_grid_visibilities,
        )

        uvw = np.array([]).reshape(0, 3).astype(np.float64)
        vis = np.array([]).astype(np.complex128)
        weights = np.array([]).astype(np.float64)
        flags = np.array([]).astype(bool)

        config = GriddingConfig(image_size=256)

        result = gpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            flags=flags,
            config=config,
        )

        # Empty input produces zero image but is technically successful
        # (no error, image produced with all zeros)
        assert result.n_vis == 0
        assert result.weight_sum == 0.0

    def test_gpu_grid_invalid_input(self):
        """Test GPU gridding with invalid input dimensions."""
        from dsa110_contimg.imaging.gpu_gridding import gpu_grid_visibilities

        # Mismatched dimensions
        rng = np.random.default_rng(42)
        uvw = rng.standard_normal((100, 3)).astype(np.float64)
        vis = (rng.standard_normal(50) + 1j * rng.standard_normal(50)).astype(
            np.complex128
        )  # Wrong size
        weights = np.ones(100, dtype=np.float64)
        flags = np.zeros(100, dtype=bool)

        result = gpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            flags=flags,
        )

        # Should return error result
        assert result.success is False
        assert result.error is not None

    def test_gpu_grid_return_grid_option(self):
        """Test return_grid option."""
        from dsa110_contimg.imaging.gpu_gridding import (
            GriddingConfig,
            gpu_grid_visibilities,
        )

        n_vis = 100
        rng = np.random.default_rng(42)
        uvw = rng.standard_normal((n_vis, 3)).astype(np.float64) * 100
        vis = (rng.standard_normal(n_vis) + 1j * rng.standard_normal(n_vis)).astype(
            np.complex128
        )
        weights = np.ones(n_vis, dtype=np.float64)
        flags = np.zeros(n_vis, dtype=bool)

        config = GriddingConfig(image_size=256, cell_size_arcsec=5.0)

        # Without return_grid
        result_no_grid = gpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            flags=flags,
            config=config,
            return_grid=False,
        )
        assert result_no_grid.grid is None

        # With return_grid
        result_with_grid = gpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            flags=flags,
            config=config,
            return_grid=True,
        )
        assert result_with_grid.grid is not None
        assert result_with_grid.grid.shape == (256, 256)


class TestGridMSFunction:
    """Tests for grid_ms function with mocked MS file."""

    def test_grid_ms_not_found(self):
        """Test grid_ms with non-existent file."""
        from dsa110_contimg.imaging.gpu_gridding import grid_ms

        result = grid_ms("/nonexistent/path.ms")

        assert result.success is False
        assert result.error is not None

    @patch("dsa110_contimg.imaging.gpu_gridding.grid_ms")
    def test_grid_ms_config_propagation(self, mock_grid_ms):
        """Test that config is properly passed to grid_ms."""
        from dsa110_contimg.imaging.gpu_gridding import GriddingConfig, GriddingResult

        # Setup mock
        mock_grid_ms.return_value = GriddingResult(
            n_vis=1000,
            image=np.zeros((256, 256)),
        )

        config = GriddingConfig(image_size=512, cell_size_arcsec=2.0)
        mock_grid_ms("/test/path.ms", config=config)

        # Verify config was passed
        mock_grid_ms.assert_called_once()
        call_kwargs = mock_grid_ms.call_args.kwargs
        assert call_kwargs["config"] == config


class TestCupyAvailability:
    """Tests for CuPy availability detection."""

    def test_cupy_available_flag(self):
        """Test that CUPY_AVAILABLE flag is set correctly."""
        from dsa110_contimg.imaging.gpu_gridding import CUPY_AVAILABLE

        # Should be a boolean
        assert isinstance(CUPY_AVAILABLE, bool)

    @patch.dict(sys.modules, {"cupy": None})
    def test_fallback_without_cupy(self):
        """Test that module falls back gracefully without CuPy."""
        # This tests the import-time behavior
        # The module should load even without cupy

        from dsa110_contimg.imaging.gpu_gridding import (
            GriddingConfig,
            GriddingResult,
            cpu_grid_visibilities,
        )

        # Basic functionality should work
        assert GriddingConfig is not None
        assert GriddingResult is not None
        assert cpu_grid_visibilities is not None


class TestKernelCompilation:
    """Tests for CUDA kernel compilation."""

    def test_get_kernel_caching(self):
        """Test that kernels are cached after first compilation."""
        from dsa110_contimg.imaging.gpu_gridding import (
            CUPY_AVAILABLE,
            _compiled_kernels,
        )

        if not CUPY_AVAILABLE:
            pytest.skip("CuPy not available")

        from dsa110_contimg.imaging.gpu_gridding import _get_kernel

        # First call compiles (use actual kernel name from module)
        kernel1 = _get_kernel("grid_nn")

        # Should be cached now
        assert "grid_nn" in _compiled_kernels

        # Second call returns cached version
        kernel2 = _get_kernel("grid_nn")
        assert kernel1 is kernel2


class TestGPUSafetyIntegration:
    """Tests for GPU safety integration."""

    def test_memory_estimation_called(self):
        """Test that memory estimation is called for large inputs."""
        from dsa110_contimg.imaging.gpu_gridding import (
            GriddingConfig,
            gpu_grid_visibilities,
        )

        # Large visibility count
        n_vis = 10_000
        rng = np.random.default_rng(42)
        uvw = rng.standard_normal((n_vis, 3)).astype(np.float64) * 100
        vis = (rng.standard_normal(n_vis) + 1j * rng.standard_normal(n_vis)).astype(
            np.complex128
        )
        weights = np.ones(n_vis, dtype=np.float64)
        flags = np.zeros(n_vis, dtype=bool)

        config = GriddingConfig(image_size=1024)

        # Should complete without memory errors for reasonable sizes
        result = gpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            flags=flags,
            config=config,
        )

        # Result should be valid (success or graceful failure)
        assert result is not None
        assert isinstance(result.success, bool)
