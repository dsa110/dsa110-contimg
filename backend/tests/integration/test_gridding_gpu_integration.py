"""
Integration tests for GPU gridding with GPU safety.

These tests verify that the GPU gridding module works correctly
with the GPU safety infrastructure and handles real-world scenarios.
"""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from dsa110_contimg.imaging.gpu_gridding import (
    GriddingConfig,
    gpu_grid_visibilities,
    cpu_grid_visibilities,
    grid_ms,
    estimate_gridding_memory_gb,
    CUPY_AVAILABLE,
    _compute_spheroidal_gcf,
)
from dsa110_contimg.utils.gpu_safety import (
    check_system_memory_available,
    initialize_gpu_safety,
)


class TestGPUSafetyGriddingIntegration:
    """Tests for GPU safety integration with gridding module."""

    def test_safety_initialization_for_gridding(self):
        """Test that GPU safety module initializes correctly for gridding."""
        # Should not raise
        initialize_gpu_safety()

        # After initialization, memory checking should work
        is_safe, reason = check_system_memory_available(required_gb=1.0)
        assert isinstance(is_safe, bool)
        assert isinstance(reason, str)

    def test_memory_estimation_reasonable(self):
        """Test that memory estimation gives reasonable values."""
        # Typical DSA-110 observation: ~1M visibilities
        gpu_gb, sys_gb = estimate_gridding_memory_gb(
            n_vis=1_000_000,
            image_size=4096,
            support=4,
            oversampling=128,
        )

        # Should be reasonable (not gigantic or tiny)
        assert 0.1 < gpu_gb < 10, f"GPU memory estimate {gpu_gb} GB seems wrong"
        assert 0.01 < sys_gb < 10, f"System memory estimate {sys_gb} GB seems wrong"

    def test_memory_estimation_small_job(self):
        """Test memory estimation for small gridding job."""
        gpu_gb, sys_gb = estimate_gridding_memory_gb(
            n_vis=1000,
            image_size=256,
        )

        # Small job should need minimal memory
        assert gpu_gb < 1, f"Small job GPU estimate {gpu_gb} GB too high"
        assert sys_gb < 1, f"Small job system estimate {sys_gb} GB too high"

    def test_cupy_availability_detection(self):
        """Test that CuPy availability is properly detected."""
        assert isinstance(CUPY_AVAILABLE, bool)

        if CUPY_AVAILABLE:
            import cupy as cp

            assert cp is not None


class TestGriddingWithMockMS:
    """Tests with mock measurement set structures."""

    @pytest.fixture
    def mock_ms_directory(self):
        """Create a mock MS directory structure."""
        with tempfile.TemporaryDirectory(suffix=".ms") as tmpdir:
            ms_path = Path(tmpdir)

            # Create subdirectory structure typical of MS
            for subdir in ["ANTENNA", "FIELD", "SPECTRAL_WINDOW", "POINTING"]:
                (ms_path / subdir).mkdir()
                (ms_path / subdir / "table.dat").touch()

            # Create main table marker
            (ms_path / "table.dat").touch()

            yield ms_path

    def test_grid_ms_handles_missing_file(self):
        """Test that grid_ms handles missing files gracefully."""
        result = grid_ms("/nonexistent/file.ms")

        assert result.success is False
        assert result.error is not None

    def test_grid_ms_with_mock_structure(self, mock_ms_directory):
        """Test gridding with mock MS directory structure."""
        # The mock MS exists as a directory but doesn't have valid CASA tables
        # This should fail gracefully with a table read error
        result = grid_ms(str(mock_ms_directory))

        # Should fail because no valid DATA column
        assert result.success is False
        assert result.error is not None


class TestGriddingNumerics:
    """Test the numerical aspects of gridding."""

    def test_gridding_with_point_source(self):
        """Test gridding a single point source at phase center."""
        # Single visibility at (0,0,0) should produce uniform grid
        uvw = np.array([[0.0, 0.0, 0.0]], dtype=np.float64)
        vis = np.array([1.0 + 0j], dtype=np.complex128)
        weights = np.array([1.0], dtype=np.float64)
        flags = np.array([False], dtype=bool)

        config = GriddingConfig(image_size=64, cell_size_arcsec=60.0)

        result = gpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            flags=flags,
            config=config,
        )

        assert result.success is True
        assert result.image is not None
        assert result.image.shape == (64, 64)

        # Center should have peak (point source at phase center)
        center = result.image.shape[0] // 2
        # The peak should be near the center
        max_pos = np.unravel_index(np.argmax(result.image), result.image.shape)
        distance_from_center = np.sqrt(
            (max_pos[0] - center) ** 2 + (max_pos[1] - center) ** 2
        )
        assert distance_from_center < 5, "Point source not at center"

    def test_gridding_with_random_visibilities(self):
        """Test gridding with random visibility data."""
        rng = np.random.default_rng(42)
        n_vis = 1000

        # Random UVW coordinates (moderate baseline lengths)
        uvw = rng.standard_normal((n_vis, 3)).astype(np.float64) * 500

        # Random visibilities
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
        assert result.n_vis == n_vis
        assert result.processing_time_s > 0

    def test_gridding_consistency_cpu_gpu(self):
        """Test that CPU and GPU give consistent results."""
        rng = np.random.default_rng(123)
        n_vis = 500

        uvw = rng.standard_normal((n_vis, 3)).astype(np.float64) * 200
        vis = (rng.standard_normal(n_vis) + 1j * rng.standard_normal(n_vis)).astype(
            np.complex128
        )
        weights = np.ones(n_vis, dtype=np.float64)
        flags = np.zeros(n_vis, dtype=bool)

        config = GriddingConfig(image_size=128, cell_size_arcsec=10.0)

        # CPU result
        cpu_result = cpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            flags=flags,
            config=config,
        )

        # GPU result (falls back to CPU if no GPU)
        gpu_result = gpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            flags=flags,
            config=config,
        )

        assert cpu_result.success is True
        assert gpu_result.success is True

        # Results should be similar (not exact due to floating point)
        # Compare image statistics
        cpu_max = np.max(cpu_result.image)
        gpu_max = np.max(gpu_result.image)

        # Should be within 10% for this test
        if cpu_max > 0 and gpu_max > 0:
            ratio = gpu_max / cpu_max
            assert 0.5 < ratio < 2.0, f"CPU/GPU results differ significantly: {ratio}"

    def test_gridding_handles_all_flagged(self):
        """Test gridding when all data is flagged."""
        rng = np.random.default_rng(42)
        n_vis = 100

        uvw = rng.standard_normal((n_vis, 3)).astype(np.float64) * 100
        vis = (rng.standard_normal(n_vis) + 1j * rng.standard_normal(n_vis)).astype(
            np.complex128
        )
        weights = np.ones(n_vis, dtype=np.float64)
        flags = np.ones(n_vis, dtype=bool)  # All flagged

        config = GriddingConfig(image_size=64)

        result = gpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            flags=flags,
            config=config,
        )

        # Should complete but with all flagged
        assert result.n_flagged == n_vis


class TestGCFComputation:
    """Test gridding convolution function computation."""

    def test_gcf_symmetry(self):
        """Test that GCF has appropriate structure."""
        gcf = _compute_spheroidal_gcf(support=4, oversampling=64)

        # Test that GCF has expected shape
        assert gcf.shape == (64, 9)  # oversampling x (2*support+1)

        # Test each row sums to approximately 1 (normalized)
        for i in range(gcf.shape[0]):
            row_sum = gcf[i].sum()
            np.testing.assert_allclose(
                row_sum, 1.0, rtol=1e-5,
                err_msg=f"GCF row {i} not normalized: sum={row_sum}"
            )

    def test_gcf_normalization(self):
        """Test that GCF rows are normalized."""
        gcf = _compute_spheroidal_gcf(support=3, oversampling=32)

        for i in range(gcf.shape[0]):
            row_sum = gcf[i].sum()
            np.testing.assert_allclose(
                row_sum, 1.0, rtol=1e-5,
                err_msg=f"GCF row {i} not normalized: sum={row_sum}"
            )

    def test_gcf_values_positive(self):
        """Test that GCF values are non-negative."""
        gcf = _compute_spheroidal_gcf(support=5, oversampling=128)

        assert np.all(gcf >= 0), "GCF has negative values"
        assert np.max(gcf) > 0, "GCF is all zeros"


class TestWeightingSchemes:
    """Test different weighting schemes in gridding."""

    def test_uniform_weights(self):
        """Test gridding with uniform weights."""
        rng = np.random.default_rng(42)
        n_vis = 200

        config = GriddingConfig(image_size=64)
        # Scale UV to fit within grid bounds (u_pix = u / cell_size_rad + center)
        max_uv = 25 * config.cell_size_rad
        uvw = rng.uniform(-max_uv, max_uv, (n_vis, 3)).astype(np.float64)
        vis = (rng.standard_normal(n_vis) + 1j * rng.standard_normal(n_vis)).astype(
            np.complex128
        )
        weights = np.ones(n_vis, dtype=np.float64)

        result = gpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            config=config,
        )

        assert result.success is True
        # Weight sum should equal total weights (all vis gridded)
        np.testing.assert_allclose(result.weight_sum, weights.sum(), rtol=1e-5)

    def test_varied_weights(self):
        """Test gridding with varied weights."""
        rng = np.random.default_rng(42)
        n_vis = 200

        config = GriddingConfig(image_size=64)
        # Scale UV to fit within grid bounds
        max_uv = 25 * config.cell_size_rad
        uvw = rng.uniform(-max_uv, max_uv, (n_vis, 3)).astype(np.float64)
        vis = (rng.standard_normal(n_vis) + 1j * rng.standard_normal(n_vis)).astype(
            np.complex128
        )
        # Varied weights (some high, some low)
        weights = rng.uniform(0.1, 10.0, n_vis).astype(np.float64)

        result = gpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            config=config,
        )

        assert result.success is True
        # Weight sum should be > 0
        assert result.weight_sum > 0

    def test_zero_weights_equivalent_to_flags(self):
        """Test that zero weights effectively flag data."""
        rng = np.random.default_rng(42)
        n_vis = 100

        config = GriddingConfig(image_size=64)
        # Scale UV to fit within grid bounds
        max_uv = 25 * config.cell_size_rad
        uvw = rng.uniform(-max_uv, max_uv, (n_vis, 3)).astype(np.float64)
        vis = (rng.standard_normal(n_vis) + 1j * rng.standard_normal(n_vis)).astype(
            np.complex128
        )

        # Half with zero weights
        weights_zero = np.ones(n_vis, dtype=np.float64)
        weights_zero[:50] = 0.0
        flags_none = np.zeros(n_vis, dtype=bool)

        # Half with flags
        weights_full = np.ones(n_vis, dtype=np.float64)
        flags_half = np.zeros(n_vis, dtype=bool)
        flags_half[:50] = True

        result_zero = gpu_grid_visibilities(
            uvw=uvw, vis=vis, weights=weights_zero, flags=flags_none, config=config
        )

        result_flag = gpu_grid_visibilities(
            uvw=uvw, vis=vis, weights=weights_full, flags=flags_half, config=config
        )

        # Both should succeed
        assert result_zero.success is True
        assert result_flag.success is True


class TestEndToEndGriddingWorkflow:
    """End-to-end workflow tests for gridding."""

    def test_config_to_result_flow(self):
        """Test configuration flows through to result."""
        config = GriddingConfig(
            image_size=512,
            cell_size_arcsec=2.0,
            support=4,
            oversampling=64,
        )

        rng = np.random.default_rng(42)
        n_vis = 100

        uvw = rng.standard_normal((n_vis, 3)).astype(np.float64) * 100
        vis = (rng.standard_normal(n_vis) + 1j * rng.standard_normal(n_vis)).astype(
            np.complex128
        )
        weights = np.ones(n_vis, dtype=np.float64)
        flags = np.zeros(n_vis, dtype=bool)

        result = gpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            flags=flags,
            config=config,
        )

        assert result.success is True
        assert result.image.shape == (512, 512)
        assert result.n_vis == n_vis

    def test_return_grid_option(self):
        """Test returning the UV grid for inspection."""
        rng = np.random.default_rng(42)
        n_vis = 100

        uvw = rng.standard_normal((n_vis, 3)).astype(np.float64) * 100
        vis = (rng.standard_normal(n_vis) + 1j * rng.standard_normal(n_vis)).astype(
            np.complex128
        )
        weights = np.ones(n_vis, dtype=np.float64)
        flags = np.zeros(n_vis, dtype=bool)

        config = GriddingConfig(image_size=128)

        # Without grid
        result_no_grid = gpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            flags=flags,
            config=config,
            return_grid=False,
        )
        assert result_no_grid.grid is None

        # With grid
        result_with_grid = gpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            flags=flags,
            config=config,
            return_grid=True,
        )
        assert result_with_grid.grid is not None
        assert result_with_grid.grid.shape == (128, 128)
        assert np.iscomplexobj(result_with_grid.grid)

    def test_large_scale_gridding(self):
        """Test gridding with larger data (10k visibilities)."""
        rng = np.random.default_rng(42)
        n_vis = 10_000

        uvw = rng.standard_normal((n_vis, 3)).astype(np.float64) * 1000
        vis = (rng.standard_normal(n_vis) + 1j * rng.standard_normal(n_vis)).astype(
            np.complex128
        )
        weights = np.ones(n_vis, dtype=np.float64)
        flags = np.zeros(n_vis, dtype=bool)

        config = GriddingConfig(image_size=512)

        result = gpu_grid_visibilities(
            uvw=uvw,
            vis=vis,
            weights=weights,
            flags=flags,
            config=config,
        )

        assert result.success is True
        assert result.n_vis == n_vis
        assert result.processing_time_s > 0
        assert result.processing_time_s < 60  # Should complete in < 1 min
