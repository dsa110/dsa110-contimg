"""
DSA-110 Imaging Benchmarks

Benchmarks for WSClean imaging operations:
- Dirty imaging
- Cleaned imaging with various settings
- Primary beam correction

WSClean uses GPU acceleration (IDG gridder), so these benchmarks
help track GPU utilization and I/O patterns.
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


def _find_calibrated_ms():
    """Find an MS with CORRECTED_DATA column."""
    if not TEST_MS_DIR.exists():
        return None
    
    import casacore.tables as ct
    
    for ms_path in TEST_MS_DIR.glob("*.ms"):
        try:
            with ct.table(str(ms_path), readonly=True) as t:
                if "CORRECTED_DATA" in t.colnames():
                    return ms_path
        except Exception:
            continue
    
    # Fallback to any MS
    return _find_test_ms()


class TimeWSCleanDirty:
    """Benchmark WSClean dirty imaging.
    
    Dirty imaging (niter=0) is the fastest imaging mode,
    useful for quick-look and as baseline for clean benchmarks.
    """
    
    timeout = 300
    
    def setup(self):
        """Prepare test MS and output directory."""
        self.test_ms = _find_calibrated_ms()
        if self.test_ms is None:
            raise NotImplementedError("No test MS available")
        
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self.output_dir = SCRATCH_DIR / "bench_wsclean_dirty"
        
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir()
        
        self.imagename = str(self.output_dir / "dirty")
    
    def time_wsclean_dirty(self):
        """Time WSClean dirty imaging."""
        import subprocess
        
        cmd = [
            "wsclean",
            "-size", "512", "512",
            "-scale", "4asec",
            "-niter", "0",
            "-pol", "I",
            "-weight", "briggs", "0",
            "-name", self.imagename,
            "-data-column", "CORRECTED_DATA",
            str(self.test_ms),
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
    
    def teardown(self):
        """Clean up output files."""
        if hasattr(self, "output_dir") and self.output_dir.exists():
            shutil.rmtree(self.output_dir, ignore_errors=True)


class TimeWSCleanClean:
    """Benchmark WSClean cleaning.
    
    Tests standard cleaning with moderate iteration count.
    """
    
    timeout = 600
    
    def setup(self):
        """Prepare test MS and output directory."""
        self.test_ms = _find_calibrated_ms()
        if self.test_ms is None:
            raise NotImplementedError("No test MS available")
        
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self.output_dir = SCRATCH_DIR / "bench_wsclean_clean"
        
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir()
        
        self.imagename = str(self.output_dir / "clean")
    
    def time_wsclean_clean_500iter(self):
        """Time WSClean with 500 iterations."""
        import subprocess
        
        cmd = [
            "wsclean",
            "-size", "512", "512",
            "-scale", "4asec",
            "-niter", "500",
            "-threshold", "0.5mJy",
            "-pol", "I",
            "-weight", "briggs", "0",
            "-name", self.imagename,
            "-data-column", "CORRECTED_DATA",
            str(self.test_ms),
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
    
    def teardown(self):
        """Clean up output files."""
        if hasattr(self, "output_dir") and self.output_dir.exists():
            shutil.rmtree(self.output_dir, ignore_errors=True)


class TimeWSCleanWithIDG:
    """Benchmark WSClean with IDG (GPU) gridder.
    
    IDG provides GPU-accelerated w-stacking gridding.
    Tracks GPU utilization benefits.
    """
    
    timeout = 600
    
    def setup(self):
        """Prepare test MS and output directory."""
        self.test_ms = _find_calibrated_ms()
        if self.test_ms is None:
            raise NotImplementedError("No test MS available")
        
        # Check if IDG is available
        import subprocess
        result = subprocess.run(
            ["wsclean", "--version"],
            capture_output=True,
            text=True,
        )
        if "idg" not in result.stdout.lower():
            raise NotImplementedError("WSClean not built with IDG support")
        
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self.output_dir = SCRATCH_DIR / "bench_wsclean_idg"
        
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir()
        
        self.imagename = str(self.output_dir / "idg")
    
    def time_wsclean_idg(self):
        """Time WSClean with IDG gridder."""
        import subprocess
        
        cmd = [
            "wsclean",
            "-size", "512", "512",
            "-scale", "4asec",
            "-niter", "500",
            "-threshold", "0.5mJy",
            "-pol", "I",
            "-weight", "briggs", "0",
            "-use-idg",
            "-idg-mode", "hybrid",
            "-name", self.imagename,
            "-data-column", "CORRECTED_DATA",
            str(self.test_ms),
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
    
    def teardown(self):
        """Clean up output files."""
        if hasattr(self, "output_dir") and self.output_dir.exists():
            shutil.rmtree(self.output_dir, ignore_errors=True)


class TimeImagingPipeline:
    """Benchmark complete imaging through pipeline wrapper.
    
    Uses dsa110_contimg.imaging module for full pipeline execution.
    """
    
    timeout = 600
    
    def setup(self):
        """Prepare test MS and output directory."""
        self.test_ms = _find_calibrated_ms()
        if self.test_ms is None:
            raise NotImplementedError("No test MS available")
        
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self.output_dir = SCRATCH_DIR / "bench_imaging_pipe"
        
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir()
        
        self.imagename = str(self.output_dir / "pipeline")
    
    def time_pipeline_imaging(self):
        """Time imaging through pipeline wrapper."""
        from dsa110_contimg.imaging.wsclean import run_wsclean
        
        run_wsclean(
            ms_path=str(self.test_ms),
            imagename=self.imagename,
            imsize=512,
            niter=500,
            threshold="0.5mJy",
        )
    
    def teardown(self):
        """Clean up output files."""
        if hasattr(self, "output_dir") and self.output_dir.exists():
            shutil.rmtree(self.output_dir, ignore_errors=True)
