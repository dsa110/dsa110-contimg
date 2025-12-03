"""
Calibration Performance Benchmarks

Measures time and memory for calibration operations:
- Bandpass calibration (~31s baseline)
- Gain calibration (~10s baseline)
- Delay calibration
- Calibration table discovery
- Calibration application

These benchmarks establish baselines before GPU acceleration.
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set up CASA log directory to avoid polluting benchmark directory
try:
    from dsa110_contimg.utils.tempdirs import derive_casa_log_dir
    _casa_log_dir = derive_casa_log_dir()
    os.chdir(str(_casa_log_dir))
except (ImportError, OSError):
    pass  # Best effort


class TimeSuite:
    """Timing benchmarks for calibration operations."""

    # ASV parameters
    timeout = 300.0  # 5 minutes max per benchmark
    processes = 1
    number = 1
    repeat = 3
    warmup_time = 0.0

    def setup(self):
        """Setup test data paths."""
        # Use test data if available, otherwise skip
        self.test_data_dir = Path("/data/dsa110-contimg/test_data")
        self.cal_ms = self.test_data_dir / "cal_sample.ms"
        self.has_test_data = self.cal_ms.exists()

        # Import calibration modules if available
        try:
            from dsa110_contimg.calibration import caltables
            self.caltables = caltables
            self.has_calibration = True
        except ImportError:
            self.has_calibration = False

        # Check for CASA
        try:
            from casatasks import bandpass, gaincal
            self.has_casa = True
        except ImportError:
            self.has_casa = False

    def time_discover_caltables(self):
        """Benchmark calibration table discovery.

        This is a fast operation that should complete in <1s.
        Baseline: ~0.1s
        """
        if not self.has_calibration or not self.has_test_data:
            return  # Skip if not available

        for _ in range(100):  # Run 100 times for measurable time
            self.caltables.discover_caltables(str(self.cal_ms))

    def time_bandpass_solve(self):
        """Benchmark bandpass calibration.

        This is a key performance metric for the pipeline.
        Baseline: ~31s (target: ~3s with GPU)
        """
        if not self.has_casa or not self.has_test_data:
            return  # Skip if not available

        from casatasks import bandpass

        with tempfile.TemporaryDirectory() as tmpdir:
            caltable = os.path.join(tmpdir, "test.bpcal")
            bandpass(
                vis=str(self.cal_ms),
                caltable=caltable,
                field="0",
                refant="24",
                solint="inf",
                combine="scan",
            )

    def time_gaincal_solve(self):
        """Benchmark gain calibration.

        Baseline: ~10s (target: ~1s with GPU)
        """
        if not self.has_casa or not self.has_test_data:
            return  # Skip if not available

        from casatasks import gaincal

        with tempfile.TemporaryDirectory() as tmpdir:
            caltable = os.path.join(tmpdir, "test.gcal")
            gaincal(
                vis=str(self.cal_ms),
                caltable=caltable,
                field="0",
                refant="24",
                solint="inf",
                gaintype="G",
            )


class MemSuite:
    """Memory benchmarks for calibration operations."""

    timeout = 300.0
    processes = 1

    def setup(self):
        """Setup test data paths."""
        self.test_data_dir = Path("/data/dsa110-contimg/test_data")
        self.cal_ms = self.test_data_dir / "cal_sample.ms"
        self.has_test_data = self.cal_ms.exists()

        try:
            from casatasks import bandpass
            self.has_casa = True
        except ImportError:
            self.has_casa = False

    def peakmem_bandpass_solve(self):
        """Track peak memory during bandpass calibration.

        Baseline: ~2GB (target: <4GB with GPU)
        """
        if not self.has_casa or not self.has_test_data:
            return  # Skip if not available

        from casatasks import bandpass

        with tempfile.TemporaryDirectory() as tmpdir:
            caltable = os.path.join(tmpdir, "test.bpcal")
            bandpass(
                vis=str(self.cal_ms),
                caltable=caltable,
                field="0",
                refant="24",
                solint="inf",
                combine="scan",
            )


class SyntheticTimeSuite:
    """Synthetic benchmarks that don't require test data.

    These measure core numerical operations used in calibration.
    """

    timeout = 60.0
    processes = 1
    number = 1
    repeat = 5

    def setup(self):
        """Setup synthetic test data."""
        import numpy as np

        # DSA-110 dimensions: 96 antennas, 768 channels
        self.n_ant = 96
        self.n_chan = 768
        self.n_time = 100
        self.n_bl = self.n_ant * (self.n_ant - 1) // 2  # 4560 baselines

        # Create synthetic visibility data
        np.random.seed(42)
        self.vis = (
            np.random.randn(self.n_bl, self.n_chan, self.n_time)
            + 1j * np.random.randn(self.n_bl, self.n_chan, self.n_time)
        ).astype(np.complex64)

        # Model visibilities (point source)
        self.model = np.ones((self.n_bl, self.n_chan, self.n_time), dtype=np.complex64)

        # Gains per antenna
        self.gains = (
            np.random.randn(self.n_ant, self.n_chan)
            + 1j * np.random.randn(self.n_ant, self.n_chan)
        ).astype(np.complex64)
        self.gains *= 0.1
        self.gains += 1.0

    def time_visibility_correction_cpu(self):
        """Benchmark visibility correction on CPU.

        This is the core operation: V_corrected = V / (g_i * g_j*)
        Baseline for CPU, will compare to GPU.
        """
        import numpy as np

        # Build gain products for all baselines
        corrected = np.zeros_like(self.vis)

        bl_idx = 0
        for i in range(self.n_ant):
            for j in range(i + 1, self.n_ant):
                gain_product = self.gains[i, :, np.newaxis] * np.conj(
                    self.gains[j, :, np.newaxis]
                )
                corrected[bl_idx] = self.vis[bl_idx] / gain_product
                bl_idx += 1

        return corrected

    def time_matrix_solve_cpu(self):
        """Benchmark matrix solve for gain calibration.

        Simulates least-squares gain solving.
        """
        import numpy as np

        # Solve for gains from model/observed ratio
        # Simplified: just do matrix operations representative of cal solve
        n = self.n_ant

        # Create normal equations matrix
        A = np.eye(n, dtype=np.complex64) + 0.1 * np.random.randn(n, n).astype(
            np.complex64
        )
        A = A @ A.conj().T  # Make Hermitian positive definite
        b = np.random.randn(n).astype(np.complex64)

        # Solve for each channel
        solutions = np.zeros((n, self.n_chan), dtype=np.complex64)
        for ch in range(self.n_chan):
            solutions[:, ch] = np.linalg.solve(A, b)

        return solutions

    def time_fft_channelization(self):
        """Benchmark FFT for channel operations.

        Used in delay calibration and bandpass fitting.
        """
        import numpy as np

        # FFT along frequency axis for all baselines/times
        result = np.fft.fft(self.vis, axis=1)
        return result
