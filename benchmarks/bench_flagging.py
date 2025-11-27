"""
DSA-110 RFI Flagging Benchmarks

Lightweight benchmarks for flagging operations.
Uses cached MS copies to avoid repeated setup overhead.

Note: AOFlagger is I/O-bound and takes several minutes.
Full flagging benchmarks are disabled by default.
"""

import shutil
from pathlib import Path

TEST_MS_DIR = Path("/stage/dsa110-contimg/ms")
SCRATCH_DIR = Path("/scratch/asv_benchmarks")


def _find_test_ms():
    """Find a suitable test MS file."""
    if not TEST_MS_DIR.exists():
        return None
    ms_files = list(TEST_MS_DIR.glob("*.ms"))
    if not ms_files:
        return None
    return min(ms_files, key=lambda p: sum(f.stat().st_size for f in p.rglob("*") if f.is_file()))


def _get_cached_ms(name_prefix):
    """Get or create a cached MS copy."""
    test_ms = _find_test_ms()
    if test_ms is None:
        return None
    
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    cached_ms = SCRATCH_DIR / f"{name_prefix}_{test_ms.name}"
    
    if not cached_ms.exists():
        shutil.copytree(test_ms, cached_ms)
    
    return cached_ms


class TimeFlagReset:
    """Benchmark flag reset operations.
    
    Reset is fast and measures baseline flagging overhead.
    """
    
    timeout = 60
    number = 1
    repeat = 1
    
    def setup(self):
        """Get cached MS."""
        self.work_ms = _get_cached_ms("bench_reset")
        if self.work_ms is None:
            raise NotImplementedError("No test MS available")
    
    def time_reset_flags(self):
        """Time flag reset using pipeline function."""
        from dsa110_contimg.calibration.flagging import reset_flags
        reset_flags(str(self.work_ms))


class TimeFlagZeros:
    """Benchmark zero-value flagging."""
    
    timeout = 120
    number = 1
    repeat = 1
    
    def setup(self):
        """Get cached MS."""
        self.work_ms = _get_cached_ms("bench_zeros")
        if self.work_ms is None:
            raise NotImplementedError("No test MS available")
    
    def time_flag_zeros(self):
        """Time zero flagging using pipeline function."""
        from dsa110_contimg.calibration.flagging import flag_zeros
        flag_zeros(str(self.work_ms))


class TimeFlagRFI:
    """Benchmark AOFlagger RFI flagging.
    
    DISABLED by default - takes 3+ minutes.
    """
    
    timeout = 600
    number = 1
    repeat = 1
    
    def setup(self):
        """Skip by default - too slow."""
        raise NotImplementedError("AOFlagger benchmark disabled (takes 3+ min)")
    
    def time_flag_rfi(self):
        """Time AOFlagger RFI flagging."""
        pass
