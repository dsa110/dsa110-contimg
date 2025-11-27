"""
DSA-110 Calibration Benchmarks

Lightweight benchmarks for the calibration pipeline stages.
Uses a small subset of data to keep benchmark times reasonable.

For full-scale timing, use the standalone timing_benchmark.py script.
"""

import shutil
from pathlib import Path

# Test MS path - must exist for benchmarks to run
TEST_MS_DIR = Path("/stage/dsa110-contimg/ms")
SCRATCH_DIR = Path("/scratch/asv_benchmarks")


def _find_test_ms():
    """Find a suitable test MS file."""
    if not TEST_MS_DIR.exists():
        return None
    ms_files = list(TEST_MS_DIR.glob("*.ms"))
    if not ms_files:
        return None
    # Prefer smaller files for faster benchmarks
    return min(ms_files, key=lambda p: sum(f.stat().st_size for f in p.rglob("*") if f.is_file()))


class TimeCalibrationImport:
    """Benchmark import time for calibration modules.
    
    Import time matters for CLI responsiveness.
    """
    
    timeout = 60
    
    def time_import_calibration_module(self):
        """Time importing the calibration module."""
        import sys
        
        # Force reimport
        mods_to_remove = [k for k in sys.modules if k.startswith("dsa110_contimg.calibration")]
        for mod in mods_to_remove:
            del sys.modules[mod]
        
        import dsa110_contimg.calibration.calibration  # noqa: F401
    
    def time_import_casa_tasks(self):
        """Time importing casatasks."""
        import sys
        
        mods_to_remove = [k for k in sys.modules if k.startswith("casatasks")]
        for mod in mods_to_remove:
            del sys.modules[mod]
        
        from casatasks import bandpass, gaincal, applycal  # noqa: F401


class TimeBandpassSolve:
    """Benchmark bandpass calibration solve.
    
    Uses a small field selection to keep benchmark times reasonable.
    """
    
    timeout = 180
    number = 1  # Only run once (too slow for multiple iterations)
    repeat = 1
    
    def setup(self):
        """Prepare test MS and working directory."""
        self.test_ms = _find_test_ms()
        if self.test_ms is None:
            raise NotImplementedError("No test MS available")
        
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self.work_ms = SCRATCH_DIR / f"bench_bp_{self.test_ms.name}"
        self.caltable = SCRATCH_DIR / "bench_bp.bcal"
        
        # Skip setup if cached copy exists
        if not self.work_ms.exists():
            shutil.copytree(self.test_ms, self.work_ms)
        
        if self.caltable.exists():
            shutil.rmtree(self.caltable)
        
        self.refant = "103"
        self.field = "0"
    
    def time_bandpass_single_field(self):
        """Time bandpass solve on single field."""
        from casatasks import bandpass
        
        bandpass(
            vis=str(self.work_ms),
            caltable=str(self.caltable),
            field=self.field,
            refant=self.refant,
            solint="inf",
            combine="scan",
            minsnr=3.0,
        )


class TimeGainSolve:
    """Benchmark gain calibration solve."""
    
    timeout = 120
    number = 1
    repeat = 1
    
    def setup(self):
        """Prepare test MS."""
        self.test_ms = _find_test_ms()
        if self.test_ms is None:
            raise NotImplementedError("No test MS available")
        
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self.work_ms = SCRATCH_DIR / f"bench_gain_{self.test_ms.name}"
        self.caltable = SCRATCH_DIR / "bench_gain.gcal"
        
        if not self.work_ms.exists():
            shutil.copytree(self.test_ms, self.work_ms)
        
        if self.caltable.exists():
            shutil.rmtree(self.caltable)
        
        self.refant = "103"
        self.field = "0"
    
    def time_gaincal_single_field(self):
        """Time gain solve on single field."""
        from casatasks import gaincal
        
        gaincal(
            vis=str(self.work_ms),
            caltable=str(self.caltable),
            field=self.field,
            refant=self.refant,
            solint="inf",
            gaintype="G",
            calmode="ap",
            minsnr=3.0,
        )


class TimeApplyCal:
    """Benchmark calibration application."""
    
    timeout = 180
    number = 1
    repeat = 1
    
    def setup(self):
        """Prepare test MS with calibration table."""
        self.test_ms = _find_test_ms()
        if self.test_ms is None:
            raise NotImplementedError("No test MS available")
        
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self.work_ms = SCRATCH_DIR / f"bench_apply_{self.test_ms.name}"
        self.caltable = SCRATCH_DIR / "bench_apply.gcal"
        
        if not self.work_ms.exists():
            shutil.copytree(self.test_ms, self.work_ms)
        
        # Create a simple gain table if needed
        if not self.caltable.exists():
            from casatasks import gaincal
            gaincal(
                vis=str(self.work_ms),
                caltable=str(self.caltable),
                field="0",
                refant="103",
                solint="inf",
                gaintype="G",
                calmode="ap",
                minsnr=1.0,
            )
    
    def time_applycal_single_table(self):
        """Time applying single calibration table."""
        from casatasks import applycal
        
        applycal(
            vis=str(self.work_ms),
            field="0",  # Single field only
            gaintable=[str(self.caltable)],
            applymode="calflag",
        )
