"""
Imaging Performance Benchmarks

Measures time and memory for imaging operations:
- Dirty image creation (~30s baseline)
- CLEAN deconvolution (~60s baseline)
- Gridding operations
- FFT operations

These benchmarks establish baselines before GPU acceleration.
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TimeSuite:
    """Timing benchmarks for imaging operations."""

    timeout = 600.0  # 10 minutes max
    processes = 1
    number = 1
    repeat = 3
    warmup_time = 0.0

    def setup(self):
        """Setup test data paths."""
        self.test_data_dir = Path("/data/dsa110-contimg/test_data")
        self.imaging_ms = self.test_data_dir / "imaging_sample.ms"
        self.has_test_data = self.imaging_ms.exists()

        try:
            from casatasks import tclean
            self.has_casa = True
        except ImportError:
            self.has_casa = False

    def time_tclean_dirty(self):
        """Benchmark dirty image creation.

        No deconvolution, just gridding + FFT.
        Baseline: ~30s (target: ~3s with GPU)
        """
        if not self.has_casa or not self.has_test_data:
            return

        from casatasks import tclean

        with tempfile.TemporaryDirectory() as tmpdir:
            imagename = os.path.join(tmpdir, "test_dirty")
            tclean(
                vis=str(self.imaging_ms),
                imagename=imagename,
                imsize=[512, 512],
                cell="12arcsec",
                niter=0,  # Dirty image only
                gridder="standard",
            )

    def time_tclean_clean(self):
        """Benchmark CLEAN deconvolution.

        Full imaging with deconvolution.
        Baseline: ~60s (target: ~6s with GPU)
        """
        if not self.has_casa or not self.has_test_data:
            return

        from casatasks import tclean

        with tempfile.TemporaryDirectory() as tmpdir:
            imagename = os.path.join(tmpdir, "test_clean")
            tclean(
                vis=str(self.imaging_ms),
                imagename=imagename,
                imsize=[512, 512],
                cell="12arcsec",
                niter=1000,
                threshold="1mJy",
                gridder="standard",
            )


class SyntheticTimeSuite:
    """Synthetic imaging benchmarks without test data."""

    timeout = 120.0
    processes = 1
    number = 1
    repeat = 5

    def setup(self):
        """Setup synthetic imaging data."""
        import numpy as np

        # Image dimensions
        self.imsize = 512
        self.n_vis = 100000  # Number of visibilities

        # Synthetic UVW coordinates
        np.random.seed(42)
        self.uvw = np.random.randn(self.n_vis, 3).astype(np.float32)
        self.uvw[:, 0] *= 1000  # U range
        self.uvw[:, 1] *= 1000  # V range
        self.uvw[:, 2] *= 100  # W range

        # Synthetic visibilities
        self.vis = (
            np.random.randn(self.n_vis) + 1j * np.random.randn(self.n_vis)
        ).astype(np.complex64)

        # Weights
        self.weights = np.ones(self.n_vis, dtype=np.float32)

    def time_gridding_nearest_cpu(self):
        """Benchmark nearest-neighbor gridding on CPU.

        Simple gridding without convolution kernel.
        """
        import numpy as np

        grid = np.zeros((self.imsize, self.imsize), dtype=np.complex64)
        weight_grid = np.zeros((self.imsize, self.imsize), dtype=np.float32)

        # Grid cell size (arbitrary for benchmark)
        cell_rad = 1.0 / (self.imsize * 12.0)  # ~12 arcsec

        # Nearest-neighbor gridding
        for i in range(self.n_vis):
            u_pix = int(self.uvw[i, 0] * cell_rad + self.imsize // 2)
            v_pix = int(self.uvw[i, 1] * cell_rad + self.imsize // 2)

            if 0 <= u_pix < self.imsize and 0 <= v_pix < self.imsize:
                grid[v_pix, u_pix] += self.vis[i] * self.weights[i]
                weight_grid[v_pix, u_pix] += self.weights[i]

        # Normalize
        mask = weight_grid > 0
        grid[mask] /= weight_grid[mask]

        return grid

    def time_gridding_vectorized_cpu(self):
        """Benchmark vectorized gridding on CPU.

        NumPy-optimized gridding.
        """
        import numpy as np

        cell_rad = 1.0 / (self.imsize * 12.0)

        # Compute pixel coordinates
        u_pix = (self.uvw[:, 0] * cell_rad + self.imsize // 2).astype(np.int32)
        v_pix = (self.uvw[:, 1] * cell_rad + self.imsize // 2).astype(np.int32)

        # Filter valid pixels
        valid = (
            (u_pix >= 0)
            & (u_pix < self.imsize)
            & (v_pix >= 0)
            & (v_pix < self.imsize)
        )

        u_valid = u_pix[valid]
        v_valid = v_pix[valid]
        vis_valid = self.vis[valid] * self.weights[valid]
        weight_valid = self.weights[valid]

        # Use np.add.at for accumulation
        grid = np.zeros((self.imsize, self.imsize), dtype=np.complex64)
        weight_grid = np.zeros((self.imsize, self.imsize), dtype=np.float32)

        np.add.at(grid, (v_valid, u_valid), vis_valid)
        np.add.at(weight_grid, (v_valid, u_valid), weight_valid)

        # Normalize
        mask = weight_grid > 0
        grid[mask] /= weight_grid[mask]

        return grid

    def time_fft2_image(self):
        """Benchmark 2D FFT for image creation.

        Core operation for gridded visibilities -> image.
        """
        import numpy as np

        # Create complex grid
        grid = (
            np.random.randn(self.imsize, self.imsize)
            + 1j * np.random.randn(self.imsize, self.imsize)
        ).astype(np.complex64)

        # FFT to image domain
        image = np.fft.ifft2(np.fft.ifftshift(grid))
        image = np.fft.fftshift(image)

        return np.real(image)

    def time_fft2_large_image(self):
        """Benchmark 2D FFT for large image (2048x2048)."""
        import numpy as np

        large_size = 2048
        grid = (
            np.random.randn(large_size, large_size)
            + 1j * np.random.randn(large_size, large_size)
        ).astype(np.complex64)

        image = np.fft.ifft2(np.fft.ifftshift(grid))
        image = np.fft.fftshift(image)

        return np.real(image)
