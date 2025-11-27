"""
DSA-110 RFI Flagging Benchmarks

Benchmarks for RFI flagging operations:
- AOFlagger (Docker-based)
- Zero flagging
- Flag reset operations

Note: AOFlagger is I/O-bound (runs in Docker container), so these benchmarks
help identify I/O bottlenecks rather than CPU optimization opportunities.
"""

import os
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


class TimeFlagReset:
    """Benchmark flag reset operations.
    
    Reset is typically fast but measures baseline overhead.
    """
    
    timeout = 60
    
    def setup(self):
        """Prepare test MS."""
        self.test_ms = _find_test_ms()
        if self.test_ms is None:
            raise NotImplementedError("No test MS available")
        
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self.work_ms = SCRATCH_DIR / f"bench_reset_{self.test_ms.name}"
        
        if self.work_ms.exists():
            shutil.rmtree(self.work_ms)
        
        shutil.copytree(self.test_ms, self.work_ms)
    
    def time_reset_flags(self):
        """Time flag reset using pipeline function."""
        from dsa110_contimg.calibration.flagging import reset_flags
        
        reset_flags(str(self.work_ms))
    
    def teardown(self):
        """Clean up working files."""
        if hasattr(self, "work_ms") and self.work_ms.exists():
            shutil.rmtree(self.work_ms, ignore_errors=True)


class TimeFlagZeros:
    """Benchmark zero-value flagging.
    
    Flags visibilities with zero or near-zero values.
    """
    
    timeout = 120
    
    def setup(self):
        """Prepare test MS."""
        self.test_ms = _find_test_ms()
        if self.test_ms is None:
            raise NotImplementedError("No test MS available")
        
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self.work_ms = SCRATCH_DIR / f"bench_zeros_{self.test_ms.name}"
        
        if self.work_ms.exists():
            shutil.rmtree(self.work_ms)
        
        shutil.copytree(self.test_ms, self.work_ms)
        
        # Reset flags first for consistent baseline
        from dsa110_contimg.calibration.flagging import reset_flags
        reset_flags(str(self.work_ms))
    
    def time_flag_zeros(self):
        """Time zero flagging using pipeline function."""
        from dsa110_contimg.calibration.flagging import flag_zeros
        
        flag_zeros(str(self.work_ms))
    
    def teardown(self):
        """Clean up working files."""
        if hasattr(self, "work_ms") and self.work_ms.exists():
            shutil.rmtree(self.work_ms, ignore_errors=True)


class TimeFlagRFI:
    """Benchmark AOFlagger RFI flagging.
    
    This is typically the slowest operation due to:
    - Docker container startup overhead
    - I/O-intensive processing
    - Full MS iteration
    
    Track this to detect I/O regressions.
    """
    
    timeout = 600  # AOFlagger can take several minutes
    
    def setup(self):
        """Prepare test MS."""
        self.test_ms = _find_test_ms()
        if self.test_ms is None:
            raise NotImplementedError("No test MS available")
        
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self.work_ms = SCRATCH_DIR / f"bench_rfi_{self.test_ms.name}"
        
        if self.work_ms.exists():
            shutil.rmtree(self.work_ms)
        
        shutil.copytree(self.test_ms, self.work_ms)
        
        # Reset flags first
        from dsa110_contimg.calibration.flagging import reset_flags
        reset_flags(str(self.work_ms))
    
    def time_flag_rfi(self):
        """Time AOFlagger RFI flagging using pipeline function."""
        from dsa110_contimg.calibration.flagging import flag_rfi
        
        flag_rfi(str(self.work_ms))
    
    def teardown(self):
        """Clean up working files."""
        if hasattr(self, "work_ms") and self.work_ms.exists():
            shutil.rmtree(self.work_ms, ignore_errors=True)


class TimeFlagPipeline:
    """Benchmark complete flagging pipeline.
    
    Measures total flagging time: reset → zeros → RFI.
    """
    
    timeout = 600
    
    def setup(self):
        """Prepare test MS."""
        self.test_ms = _find_test_ms()
        if self.test_ms is None:
            raise NotImplementedError("No test MS available")
        
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self.work_ms = SCRATCH_DIR / f"bench_flagpipe_{self.test_ms.name}"
        
        if self.work_ms.exists():
            shutil.rmtree(self.work_ms)
        
        shutil.copytree(self.test_ms, self.work_ms)
    
    def time_full_flagging_pipeline(self):
        """Time complete flagging pipeline."""
        from dsa110_contimg.calibration.flagging import (
            flag_rfi,
            flag_zeros,
            reset_flags,
        )
        
        reset_flags(str(self.work_ms))
        flag_zeros(str(self.work_ms))
        flag_rfi(str(self.work_ms))
    
    def teardown(self):
        """Clean up working files."""
        if hasattr(self, "work_ms") and self.work_ms.exists():
            shutil.rmtree(self.work_ms, ignore_errors=True)
