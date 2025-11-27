"""
DSA-110 Calibration Benchmarks

Benchmarks for the calibration pipeline stages using actual pipeline functions.
These benchmarks measure:
- Bandpass calibration (solve_bandpass)
- Gain calibration (solve_gains)  
- Delay calibration (solve_delay)
- Calibration application (applycal)

Following casabench patterns: only the operation is timed, setup/teardown excluded.
"""

import os
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
        import importlib
        import sys
        
        # Force reimport
        mods_to_remove = [k for k in sys.modules if k.startswith("dsa110_contimg.calibration")]
        for mod in mods_to_remove:
            del sys.modules[mod]
        
        import dsa110_contimg.calibration.calibration  # noqa: F401
    
    def time_import_casa_tasks(self):
        """Time importing casatasks."""
        import importlib
        import sys
        
        mods_to_remove = [k for k in sys.modules if k.startswith("casatasks")]
        for mod in mods_to_remove:
            del sys.modules[mod]
        
        from casatasks import bandpass, gaincal, applycal  # noqa: F401


class TimeBandpassSolve:
    """Benchmark bandpass calibration solve.
    
    Uses actual pipeline solve_bandpass() function which includes:
    - MODEL_DATA validation
    - CASA bandpass task execution
    - Caltable quality checks
    """
    
    timeout = 300
    
    def setup(self):
        """Prepare test MS and working directory."""
        self.test_ms = _find_test_ms()
        if self.test_ms is None:
            raise NotImplementedError("No test MS available")
        
        # Create scratch working copy to avoid modifying original
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self.work_ms = SCRATCH_DIR / f"bench_bp_{self.test_ms.name}"
        self.caltable_dir = SCRATCH_DIR / "caltables_bp"
        
        if self.work_ms.exists():
            shutil.rmtree(self.work_ms)
        if self.caltable_dir.exists():
            shutil.rmtree(self.caltable_dir)
        
        shutil.copytree(self.test_ms, self.work_ms)
        self.caltable_dir.mkdir(exist_ok=True)
        
        # Pre-populate MODEL_DATA (required precondition)
        from dsa110_contimg.calibration.model import populate_model_from_catalog
        try:
            populate_model_from_catalog(str(self.work_ms), field="0")
        except Exception:
            # Fallback to setjy
            from casatasks import setjy
            setjy(vis=str(self.work_ms), field="0", standard="Perley-Butler 2017")
        
        self.refant = "103,113,114,106,112"
        self.field = "0"
    
    def time_solve_bandpass(self):
        """Time bandpass solve using pipeline function."""
        from dsa110_contimg.calibration.calibration import solve_bandpass
        
        solve_bandpass(
            str(self.work_ms),
            self.field,
            self.refant,
            None,  # No K-table
            table_prefix=str(self.caltable_dir / "bench"),
            combine_fields=False,
            combine_spw=False,
            minsnr=3.0,
        )
    
    def teardown(self):
        """Clean up working files."""
        if hasattr(self, "work_ms") and self.work_ms.exists():
            shutil.rmtree(self.work_ms, ignore_errors=True)
        if hasattr(self, "caltable_dir") and self.caltable_dir.exists():
            shutil.rmtree(self.caltable_dir, ignore_errors=True)


class TimeGainSolve:
    """Benchmark gain calibration solve.
    
    Uses actual pipeline solve_gains() function which includes:
    - MODEL_DATA validation
    - Bandpass table validation
    - CASA gaincal task execution
    - Caltable quality checks
    """
    
    timeout = 300
    
    def setup(self):
        """Prepare test MS with bandpass tables."""
        self.test_ms = _find_test_ms()
        if self.test_ms is None:
            raise NotImplementedError("No test MS available")
        
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self.work_ms = SCRATCH_DIR / f"bench_gain_{self.test_ms.name}"
        self.caltable_dir = SCRATCH_DIR / "caltables_gain"
        
        if self.work_ms.exists():
            shutil.rmtree(self.work_ms)
        if self.caltable_dir.exists():
            shutil.rmtree(self.caltable_dir)
        
        shutil.copytree(self.test_ms, self.work_ms)
        self.caltable_dir.mkdir(exist_ok=True)
        
        # Pre-populate MODEL_DATA
        from dsa110_contimg.calibration.model import populate_model_from_catalog
        try:
            populate_model_from_catalog(str(self.work_ms), field="0")
        except Exception:
            from casatasks import setjy
            setjy(vis=str(self.work_ms), field="0", standard="Perley-Butler 2017")
        
        # Create bandpass table first (required for gain solve)
        from dsa110_contimg.calibration.calibration import solve_bandpass
        
        self.refant = "103,113,114,106,112"
        self.field = "0"
        
        self.bptables = solve_bandpass(
            str(self.work_ms),
            self.field,
            self.refant,
            None,
            table_prefix=str(self.caltable_dir / "setup"),
            minsnr=3.0,
        )
    
    def time_solve_gains(self):
        """Time gain solve using pipeline function."""
        from dsa110_contimg.calibration.calibration import solve_gains
        
        solve_gains(
            str(self.work_ms),
            self.field,
            self.refant,
            None,  # No K-table
            self.bptables,
            table_prefix=str(self.caltable_dir / "bench"),
            combine_fields=False,
            minsnr=3.0,
        )
    
    def teardown(self):
        """Clean up working files."""
        if hasattr(self, "work_ms") and self.work_ms.exists():
            shutil.rmtree(self.work_ms, ignore_errors=True)
        if hasattr(self, "caltable_dir") and self.caltable_dir.exists():
            shutil.rmtree(self.caltable_dir, ignore_errors=True)


class TimeApplyCal:
    """Benchmark calibration application.
    
    Uses CASA applycal to apply calibration tables to all fields.
    """
    
    timeout = 300
    
    def setup(self):
        """Prepare test MS with calibration tables."""
        self.test_ms = _find_test_ms()
        if self.test_ms is None:
            raise NotImplementedError("No test MS available")
        
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self.work_ms = SCRATCH_DIR / f"bench_apply_{self.test_ms.name}"
        self.caltable_dir = SCRATCH_DIR / "caltables_apply"
        
        if self.work_ms.exists():
            shutil.rmtree(self.work_ms)
        if self.caltable_dir.exists():
            shutil.rmtree(self.caltable_dir)
        
        shutil.copytree(self.test_ms, self.work_ms)
        self.caltable_dir.mkdir(exist_ok=True)
        
        # Create calibration tables
        from dsa110_contimg.calibration.model import populate_model_from_catalog
        try:
            populate_model_from_catalog(str(self.work_ms), field="0")
        except Exception:
            from casatasks import setjy
            setjy(vis=str(self.work_ms), field="0", standard="Perley-Butler 2017")
        
        from dsa110_contimg.calibration.calibration import solve_bandpass, solve_gains
        
        self.refant = "103,113,114,106,112"
        self.field = "0"
        
        self.bptables = solve_bandpass(
            str(self.work_ms),
            self.field,
            self.refant,
            None,
            table_prefix=str(self.caltable_dir / "setup"),
            minsnr=3.0,
        )
        
        self.gtables = solve_gains(
            str(self.work_ms),
            self.field,
            self.refant,
            None,
            self.bptables,
            table_prefix=str(self.caltable_dir / "setup"),
            minsnr=3.0,
        )
        
        self.gaintables = self.bptables + self.gtables
    
    def time_applycal(self):
        """Time applying calibration to all fields."""
        from casatasks import applycal
        
        applycal(
            vis=str(self.work_ms),
            field="",  # All fields
            gaintable=self.gaintables,
            applymode="calflag",
        )
    
    def teardown(self):
        """Clean up working files."""
        if hasattr(self, "work_ms") and self.work_ms.exists():
            shutil.rmtree(self.work_ms, ignore_errors=True)
        if hasattr(self, "caltable_dir") and self.caltable_dir.exists():
            shutil.rmtree(self.caltable_dir, ignore_errors=True)


class TimeModelPopulation:
    """Benchmark MODEL_DATA population.
    
    Uses pipeline's populate_model_from_catalog() which:
    - Auto-detects calibrator from field names
    - Calculates MODEL_DATA using manual calculation (bypasses ft() bugs)
    """
    
    timeout = 120
    
    def setup(self):
        """Prepare test MS."""
        self.test_ms = _find_test_ms()
        if self.test_ms is None:
            raise NotImplementedError("No test MS available")
        
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self.work_ms = SCRATCH_DIR / f"bench_model_{self.test_ms.name}"
        
        if self.work_ms.exists():
            shutil.rmtree(self.work_ms)
        
        shutil.copytree(self.test_ms, self.work_ms)
    
    def time_populate_model_from_catalog(self):
        """Time MODEL_DATA population from catalog."""
        from dsa110_contimg.calibration.model import populate_model_from_catalog
        
        populate_model_from_catalog(str(self.work_ms), field="0")
    
    def teardown(self):
        """Clean up working files."""
        if hasattr(self, "work_ms") and self.work_ms.exists():
            shutil.rmtree(self.work_ms, ignore_errors=True)
