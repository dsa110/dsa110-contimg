"""
HDF5 to MS Conversion Benchmarks

Measures time and memory for data conversion operations:
- HDF5 reading
- MS writing
- Data transformation

These benchmarks track conversion pipeline performance.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TimeSuite:
    """Timing benchmarks for conversion operations."""

    timeout = 300.0
    processes = 1
    number = 1
    repeat = 3

    def setup(self):
        """Setup test data paths."""
        self.test_data_dir = Path("/data/dsa110-contimg/test_data")
        self.sample_hdf5 = self.test_data_dir / "sample.hdf5"
        self.has_test_data = self.sample_hdf5.exists()

        try:
            from dsa110_contimg.conversion import hdf5_to_ms

            self.has_converter = True
        except ImportError:
            self.has_converter = False

    def time_hdf5_to_ms(self):
        """Benchmark full HDF5 to MS conversion.

        Baseline: varies by file size
        """
        if not self.has_converter or not self.has_test_data:
            return

        from dsa110_contimg.conversion import hdf5_to_ms

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "output"
            hdf5_to_ms(str(self.sample_hdf5), str(output))


class SyntheticTimeSuite:
    """Synthetic conversion benchmarks."""

    timeout = 60.0
    processes = 1
    number = 1
    repeat = 5

    def setup(self):
        """Setup synthetic data."""
        import numpy as np

        # DSA-110 data dimensions
        self.n_ant = 96
        self.n_chan = 768
        self.n_time = 100
        self.n_pol = 4
        self.n_bl = self.n_ant * (self.n_ant - 1) // 2

        np.random.seed(42)

        # Simulate HDF5 data structure
        self.data = {
            "vis": (
                np.random.randn(self.n_time, self.n_bl, self.n_chan, self.n_pol)
                + 1j
                * np.random.randn(self.n_time, self.n_bl, self.n_chan, self.n_pol)
            ).astype(np.complex64),
            "flags": np.zeros(
                (self.n_time, self.n_bl, self.n_chan, self.n_pol), dtype=bool
            ),
            "weights": np.ones(
                (self.n_time, self.n_bl, self.n_chan, self.n_pol), dtype=np.float32
            ),
            "uvw": np.random.randn(self.n_time, self.n_bl, 3).astype(np.float64),
            "time": np.linspace(0, 1, self.n_time),
        }

    def time_data_transpose(self):
        """Benchmark data transposition (common in conversion).

        HDF5 is often time-major, MS is baseline-major.
        """
        import numpy as np

        # Transpose from (time, bl, chan, pol) to (bl, time, chan, pol)
        transposed = np.transpose(self.data["vis"], (1, 0, 2, 3))
        return transposed.shape

    def time_flag_expansion(self):
        """Benchmark flag array expansion."""
        import numpy as np

        # Expand boolean flags to match visibility shape
        flags = self.data["flags"]
        expanded = np.broadcast_to(flags, self.data["vis"].shape)
        return expanded.shape

    def time_uvw_computation(self):
        """Benchmark UVW coordinate computation.

        Simulates recomputing UVW from antenna positions.
        """
        import numpy as np

        # Antenna positions (ECEF)
        ant_pos = np.random.randn(self.n_ant, 3) * 1000  # meters

        # Phase center
        phase_center = np.array([0.0, 0.0, 1.0])  # Zenith

        # Compute UVW for all baselines (simplified)
        uvw = np.zeros((self.n_bl, 3))
        bl_idx = 0
        for i in range(self.n_ant):
            for j in range(i + 1, self.n_ant):
                baseline = ant_pos[j] - ant_pos[i]
                uvw[bl_idx] = baseline  # Simplified (no rotation)
                bl_idx += 1

        return uvw

    def time_weight_normalization(self):
        """Benchmark weight normalization."""
        import numpy as np

        weights = self.data["weights"].copy()

        # Normalize per baseline
        for bl in range(self.n_bl):
            w = weights[:, bl, :, :]
            w_sum = np.sum(w)
            if w_sum > 0:
                weights[:, bl, :, :] = w / w_sum * w.size

        return weights
