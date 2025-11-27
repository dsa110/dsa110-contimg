"""
DSA-110 Memory Usage Benchmarks

Memory profiling benchmarks for the DSA-110 continuum imaging pipeline.
Uses ASV's peakmem_* and mem_* benchmarks to track RAM usage.

ASV Memory Benchmark Types:
- peakmem_*: Peak memory usage during operation
- mem_*: Memory usage at a specific point

These complement the timing benchmarks to ensure performance improvements
don't come at the cost of excessive memory usage.
"""

import shutil
from pathlib import Path

# Test data paths
MS_DIR = Path("/stage/dsa110-contimg/ms")
SCRATCH_DIR = Path("/scratch/asv_benchmarks")
HDF5_DIR = Path("/data/incoming")


def _find_test_ms():
    """Find a suitable test MS file."""
    if not MS_DIR.exists():
        return None
    
    ms_files = list(MS_DIR.glob("*.ms"))
    if not ms_files:
        return None
    
    # Prefer a medium-sized MS
    for ms in sorted(ms_files, key=lambda p: p.stat().st_size):
        # Skip tiny (<10MB) or huge (>10GB) files
        size = ms.stat().st_size
        if 10e6 < size < 10e9:
            return ms
    
    # Fall back to first available
    return ms_files[0]


def _find_subband_group():
    """Find a complete subband group (16 files with same timestamp)."""
    if not HDF5_DIR.exists():
        return None
    
    from collections import defaultdict
    groups = defaultdict(list)
    for f in HDF5_DIR.glob("*_sb*.hdf5"):
        name = f.name
        if "_sb" in name:
            timestamp = name.split("_sb")[0]
            groups[timestamp].append(f)
    
    for timestamp, files in sorted(groups.items(), reverse=True):
        if len(files) >= 16:
            return sorted(files)[:16]
    
    return None


class MemUVDataLoad:
    """Memory benchmarks for pyuvdata UVData loading."""
    
    timeout = 300
    
    def setup(self):
        """Find test data."""
        self.hdf5_files = _find_subband_group()
        if self.hdf5_files is None:
            raise NotImplementedError("No HDF5 files available")
        
        # Stage a single file to scratch
        self.staging_dir = SCRATCH_DIR / "mem_bench"
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        
        self.single_file = self.staging_dir / self.hdf5_files[0].name
        if not self.single_file.exists():
            shutil.copy2(self.hdf5_files[0], self.single_file)
    
    def peakmem_load_single_subband(self):
        """Peak memory when loading one HDF5 subband."""
        from pyuvdata import UVData
        
        uvd = UVData()
        uvd.read(
            str(self.single_file),
            file_type="uvh5",
            run_check=False,
            run_check_acceptability=False,
            strict_uvw_antpos_check=False,
        )
        return uvd  # Return to prevent garbage collection during measurement


class MemSubbandMerge:
    """Memory benchmarks for subband merging operations."""
    
    timeout = 600
    
    def setup(self):
        """Stage multiple subbands."""
        self.hdf5_files = _find_subband_group()
        if self.hdf5_files is None:
            raise NotImplementedError("No HDF5 files available")
        
        # Stage 4 subbands
        self.staging_dir = SCRATCH_DIR / "mem_bench_merge"
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        
        self.staged_files = []
        for f in self.hdf5_files[:4]:
            dest = self.staging_dir / f.name
            if not dest.exists():
                shutil.copy2(f, dest)
            self.staged_files.append(dest)
    
    def peakmem_merge_four_subbands(self):
        """Peak memory when loading and merging 4 subbands."""
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            _load_and_merge_subbands,
        )
        
        uvd = _load_and_merge_subbands(
            [str(f) for f in self.staged_files],
            batch_size=4,
        )
        return uvd


class MemCalibration:
    """Memory benchmarks for calibration operations."""
    
    timeout = 300
    
    def setup(self):
        """Find and copy test MS."""
        self.ms_path = _find_test_ms()
        if self.ms_path is None:
            raise NotImplementedError("No test MS available")
        
        # Work on a copy
        self.work_dir = SCRATCH_DIR / "mem_cal"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        self.ms_copy = self.work_dir / "test.ms"
        if self.ms_copy.exists():
            shutil.rmtree(self.ms_copy)
        shutil.copytree(self.ms_path, self.ms_copy)
        
        # Output caltable path
        self.caltable = self.work_dir / "test.bcal"
    
    def peakmem_bandpass_solve(self):
        """Peak memory during bandpass calibration."""
        from dsa110_contimg.calibration.calibration_tasks import solve_bandpass
        
        if self.caltable.exists():
            shutil.rmtree(self.caltable)
        
        solve_bandpass(
            vis=str(self.ms_copy),
            caltable=str(self.caltable),
            field="0",  # First field
            refant="1",
            solint="inf",
            combine="scan",
        )
    
    def teardown(self):
        """Clean up."""
        if hasattr(self, "work_dir") and self.work_dir.exists():
            shutil.rmtree(self.work_dir, ignore_errors=True)


class MemMSTableAccess:
    """Memory benchmarks for MS table operations."""
    
    timeout = 120
    
    def setup(self):
        """Find test MS."""
        self.ms_path = _find_test_ms()
        if self.ms_path is None:
            raise NotImplementedError("No test MS available")
    
    def peakmem_read_visibilities(self):
        """Peak memory when reading visibility data from MS."""
        from casacore.tables import table
        
        with table(str(self.ms_path), readonly=True, ack=False) as tb:
            data = tb.getcol("DATA")
            return data
    
    def peakmem_read_flags(self):
        """Peak memory when reading flag data from MS."""
        from casacore.tables import table
        
        with table(str(self.ms_path), readonly=True, ack=False) as tb:
            flags = tb.getcol("FLAG")
            return flags
