"""
DSA-110 Imaging Benchmarks

Lightweight benchmarks for WSClean imaging.
These benchmarks are DISABLED by default because imaging takes several minutes.

For full-scale timing, use the standalone timing_benchmark.py script.
"""

from pathlib import Path

TEST_MS_DIR = Path("/stage/dsa110-contimg/ms")
SCRATCH_DIR = Path("/scratch/asv_benchmarks")

_SKIP_REASON = "Imaging benchmarks disabled (takes 5+ minutes)"


class TimeDirtyImaging:
    """Benchmark dirty imaging with WSClean - DISABLED."""
    
    def setup(self):
        raise NotImplementedError(_SKIP_REASON)
    
    def time_wsclean_dirty(self):
        pass


class TimeCleanImaging:
    """Benchmark CLEAN imaging with WSClean - DISABLED."""
    
    def setup(self):
        raise NotImplementedError(_SKIP_REASON)
    
    def time_wsclean_clean(self):
        pass
