"""
GPU Performance Benchmarks

Measures GPU-accelerated operations:
- CuPy FFT vs NumPy FFT
- GPU gridding vs CPU gridding
- GPU matrix operations vs CPU

These benchmarks compare GPU acceleration to CPU baselines.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class GPUTimeSuite:
    """GPU timing benchmarks using CuPy."""

    timeout = 120.0
    processes = 1
    number = 1
    repeat = 5

    def setup(self):
        """Setup GPU and synthetic data."""
        import numpy as np

        # Check for CuPy
        try:
            import cupy as cp

            self.cp = cp
            self.has_gpu = True

            # Clear GPU memory
            cp.get_default_memory_pool().free_all_blocks()

            # Check GPU memory
            mem_info = cp.cuda.Device(0).mem_info
            self.gpu_free_gb = mem_info[0] / 1e9
        except (ImportError, Exception):
            self.has_gpu = False
            return

        # Image dimensions
        self.imsize = 512
        self.large_imsize = 2048
        self.n_vis = 100000

        # Create CPU arrays
        np.random.seed(42)
        self.grid_np = (
            np.random.randn(self.imsize, self.imsize)
            + 1j * np.random.randn(self.imsize, self.imsize)
        ).astype(np.complex64)

        self.large_grid_np = (
            np.random.randn(self.large_imsize, self.large_imsize)
            + 1j * np.random.randn(self.large_imsize, self.large_imsize)
        ).astype(np.complex64)

        # Visibility data
        self.vis_np = (
            np.random.randn(self.n_vis) + 1j * np.random.randn(self.n_vis)
        ).astype(np.complex64)

        # DSA-110 calibration dimensions
        self.n_ant = 96
        self.n_chan = 768
        self.n_bl = self.n_ant * (self.n_ant - 1) // 2

        self.gains_np = (
            np.random.randn(self.n_ant, self.n_chan)
            + 1j * np.random.randn(self.n_ant, self.n_chan)
        ).astype(np.complex64)

    # =========================================================================
    # FFT Benchmarks
    # =========================================================================

    def time_fft2_cpu_512(self):
        """CPU FFT 512x512 (baseline)."""
        if not self.has_gpu:
            return
        import numpy as np

        return np.fft.fft2(self.grid_np)

    def time_fft2_gpu_512(self):
        """GPU FFT 512x512."""
        if not self.has_gpu:
            return

        grid_gpu = self.cp.asarray(self.grid_np)
        result = self.cp.fft.fft2(grid_gpu)
        self.cp.cuda.Stream.null.synchronize()  # Ensure completion

        return result

    def time_fft2_cpu_2048(self):
        """CPU FFT 2048x2048 (baseline)."""
        if not self.has_gpu:
            return
        import numpy as np

        return np.fft.fft2(self.large_grid_np)

    def time_fft2_gpu_2048(self):
        """GPU FFT 2048x2048."""
        if not self.has_gpu:
            return

        grid_gpu = self.cp.asarray(self.large_grid_np)
        result = self.cp.fft.fft2(grid_gpu)
        self.cp.cuda.Stream.null.synchronize()

        return result

    # =========================================================================
    # Matrix Operation Benchmarks
    # =========================================================================

    def time_matmul_cpu(self):
        """CPU matrix multiply (baseline)."""
        if not self.has_gpu:
            return

        # 96x768 @ 768x96 = 96x96 (per-channel gain covariance)
        matrix = self.gains_np  # 96 x 768
        return matrix @ matrix.conj().T

    def time_matmul_gpu(self):
        """GPU matrix multiply."""
        if not self.has_gpu:
            return

        A_gpu = self.cp.asarray(self.gains_np)
        result = A_gpu @ A_gpu.conj().T
        self.cp.cuda.Stream.null.synchronize()

        return result

    def time_solve_cpu(self):
        """CPU linear solve (baseline)."""
        if not self.has_gpu:
            return
        import numpy as np

        n = self.n_ant
        A = np.eye(n, dtype=np.complex64) + 0.1 * np.random.randn(n, n).astype(
            np.complex64
        )
        A = A @ A.conj().T
        b = np.random.randn(n).astype(np.complex64)

        return np.linalg.solve(A, b)

    def time_solve_gpu(self):
        """GPU linear solve."""
        if not self.has_gpu:
            return
        import numpy as np

        n = self.n_ant
        A = np.eye(n, dtype=np.complex64) + 0.1 * np.random.randn(n, n).astype(
            np.complex64
        )
        A = A @ A.conj().T
        b = np.random.randn(n).astype(np.complex64)

        A_gpu = self.cp.asarray(A)
        b_gpu = self.cp.asarray(b)
        result = self.cp.linalg.solve(A_gpu, b_gpu)
        self.cp.cuda.Stream.null.synchronize()

        return result

    # =========================================================================
    # Visibility Processing Benchmarks
    # =========================================================================

    def time_vis_correction_cpu(self):
        """CPU visibility correction (baseline)."""
        if not self.has_gpu:
            return
        import numpy as np

        # Simulate correcting visibilities by gains
        # V_corrected = V / (g_i * g_j*)
        n_sample = 10000
        vis = self.vis_np[:n_sample]
        gains = self.gains_np[:, 0]  # Use first channel

        # Simplified: multiply by conjugate gains
        result = np.zeros(n_sample, dtype=np.complex64)
        for i in range(n_sample):
            ant_i = i % self.n_ant
            ant_j = (i + 1) % self.n_ant
            result[i] = vis[i] / (gains[ant_i] * np.conj(gains[ant_j]))

        return result

    def time_vis_correction_gpu(self):
        """GPU visibility correction."""
        if not self.has_gpu:
            return

        n_sample = 10000
        vis_gpu = self.cp.asarray(self.vis_np[:n_sample])
        gains_gpu = self.cp.asarray(self.gains_np[:, 0])

        # Vectorized on GPU
        ant_i = self.cp.arange(n_sample) % self.n_ant
        ant_j = (self.cp.arange(n_sample) + 1) % self.n_ant

        gain_product = gains_gpu[ant_i] * self.cp.conj(gains_gpu[ant_j])
        result = vis_gpu / gain_product
        self.cp.cuda.Stream.null.synchronize()

        return result


class GPUMemSuite:
    """GPU memory benchmarks."""

    timeout = 60.0
    processes = 1

    def setup(self):
        """Setup GPU."""
        try:
            import cupy as cp

            self.cp = cp
            self.has_gpu = True
        except ImportError:
            self.has_gpu = False

    def peakmem_fft2_gpu_2048(self):
        """Track GPU memory for large FFT."""
        if not self.has_gpu:
            return

        import numpy as np

        grid = (
            np.random.randn(2048, 2048) + 1j * np.random.randn(2048, 2048)
        ).astype(np.complex64)

        grid_gpu = self.cp.asarray(grid)
        self.cp.fft.fft2(grid_gpu)
        self.cp.cuda.Stream.null.synchronize()

        # Report GPU memory used
        mem_pool = self.cp.get_default_memory_pool()
        return mem_pool.used_bytes() / 1e9  # GB


class GPUGriddingTimeSuite:
    """GPU Gridding benchmarks for Phase 2 operations."""

    timeout = 120.0
    processes = 1
    number = 1
    repeat = 3

    params = [
        (64, 256, 512, 1024),  # image sizes
        (10000, 100000, 500000),  # n_vis
    ]
    param_names = ["image_size", "n_vis"]

    def setup(self, image_size, n_vis):
        """Setup gridding test data."""
        import numpy as np

        # Check for CuPy
        try:
            import cupy as cp
            self.cp = cp
            self.has_gpu = True
            cp.get_default_memory_pool().free_all_blocks()
        except (ImportError, Exception):
            self.has_gpu = False
            return

        self.image_size = image_size
        self.n_vis = n_vis

        # Import gridding module
        try:
            from dsa110_contimg.imaging.gpu_gridding import (
                gpu_grid_visibilities,
                cpu_grid_visibilities,
                GriddingConfig,
            )
            self.gpu_grid = gpu_grid_visibilities
            self.cpu_grid = cpu_grid_visibilities
            self.GriddingConfig = GriddingConfig
        except ImportError:
            self.has_gpu = False
            return

        # Create test data
        np.random.seed(42)
        config = GriddingConfig(image_size=image_size)
        max_uv = 25 * config.cell_size_rad

        self.uvw = np.random.uniform(-max_uv, max_uv, (n_vis, 3)).astype(np.float64)
        self.vis = (
            np.random.randn(n_vis) + 1j * np.random.randn(n_vis)
        ).astype(np.complex128)
        self.weights = np.ones(n_vis, dtype=np.float64)
        self.config = config

    def time_gridding_cpu(self, _image_size, _n_vis):
        """CPU gridding baseline.

        Args:
            _image_size: ASV parameterized image size (used in setup).
            _n_vis: ASV parameterized visibility count (used in setup).
        """
        if not self.has_gpu:
            return

        result = self.cpu_grid(
            self.uvw, self.vis, self.weights, config=self.config
        )
        return result.image

    def time_gridding_gpu(self, _image_size, _n_vis):
        """GPU gridding.

        Args:
            _image_size: ASV parameterized image size (used in setup).
            _n_vis: ASV parameterized visibility count (used in setup).
        """
        if not self.has_gpu:
            return

        result = self.gpu_grid(
            self.uvw, self.vis, self.weights, config=self.config
        )
        return result.image


class GPUCalibrationTimeSuite:
    """GPU Calibration benchmarks for Phase 2 operations."""

    timeout = 120.0
    processes = 1
    number = 1
    repeat = 3

    params = [
        (5, 20, 64, 110),  # n_antennas
        (1000, 10000, 100000),  # n_vis
    ]
    param_names = ["n_antennas", "n_vis"]

    def setup(self, n_antennas, n_vis):
        """Setup calibration test data."""
        import numpy as np

        # Check for calibration module
        try:
            from dsa110_contimg.calibration.gpu_calibration import (
                apply_gains,
                solve_per_antenna_gains,
                CUPY_AVAILABLE,
            )
            self.apply_gains = apply_gains
            self.solve_gains = solve_per_antenna_gains
            self.has_gpu = CUPY_AVAILABLE
        except ImportError:
            self.has_gpu = False
            return

        self.n_antennas = n_antennas
        self.n_vis = n_vis

        # Create test data
        np.random.seed(42)
        self.vis = (
            np.random.randn(n_vis) + 1j * np.random.randn(n_vis)
        ).astype(np.complex128)
        self.gains = (
            np.random.uniform(0.9, 1.1, n_antennas) +
            1j * np.random.uniform(-0.05, 0.05, n_antennas)
        ).astype(np.complex128)
        self.ant1 = np.random.randint(0, n_antennas, n_vis).astype(np.int32)
        self.ant2 = np.random.randint(0, n_antennas, n_vis).astype(np.int32)
        self.weights = np.ones(n_vis, dtype=np.float64)

        # Model visibilities
        self.model = self.vis * self.gains[self.ant1] * np.conj(self.gains[self.ant2])

    def time_apply_gains_cpu(self, _n_antennas, _n_vis):
        """CPU gain application baseline.

        Args:
            _n_antennas: ASV parameterized antenna count (used in setup).
            _n_vis: ASV parameterized visibility count (used in setup).
        """
        if not self.has_gpu:
            return

        vis_copy = self.vis.copy()
        result = self.apply_gains(
            vis_copy, self.gains, self.ant1, self.ant2, use_gpu=False
        )
        return result

    def time_apply_gains_gpu(self, _n_antennas, _n_vis):
        """GPU gain application.

        Args:
            _n_antennas: ASV parameterized antenna count (used in setup).
            _n_vis: ASV parameterized visibility count (used in setup).
        """
        if not self.has_gpu:
            return

        vis_copy = self.vis.copy()
        result = self.apply_gains(
            vis_copy, self.gains, self.ant1, self.ant2, use_gpu=True
        )
        return result

    def time_solve_gains_cpu(self, _n_antennas, _n_vis):
        """CPU gain solving baseline.

        Args:
            _n_antennas: ASV parameterized antenna count (used in setup).
            _n_vis: ASV parameterized visibility count (used in setup).
        """
        if not self.has_gpu:
            return

        result = self.solve_gains(
            self.vis, self.model, self.ant1, self.ant2,
            self.weights, self.n_antennas, use_gpu=False
        )
        return result

    def time_solve_gains_gpu(self, _n_antennas, _n_vis):
        """GPU gain solving.

        Args:
            _n_antennas: ASV parameterized antenna count (used in setup).
            _n_vis: ASV parameterized visibility count (used in setup).
        """
        if not self.has_gpu:
            return

        result = self.solve_gains(
            self.vis, self.model, self.ant1, self.ant2,
            self.weights, self.n_antennas, use_gpu=True
        )
        return result
