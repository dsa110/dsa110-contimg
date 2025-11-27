"""
DSA-110 HDF5 → MS Conversion Benchmarks

Benchmarks for the UVH5 to Measurement Set conversion:
- Single subband loading
- Multi-subband combining
- Direct MS writing
"""

import shutil
from pathlib import Path

HDF5_DIR = Path("/data/incoming")
SCRATCH_DIR = Path("/scratch/asv_benchmarks")


def _find_subband_group():
    """Find a complete subband group (16 files with same timestamp)."""
    if not HDF5_DIR.exists():
        return None
    
    from collections import defaultdict
    
    # Group files by timestamp prefix
    groups = defaultdict(list)
    for f in HDF5_DIR.glob("*_sb*.hdf5"):
        # Extract timestamp (everything before _sb)
        name = f.name
        if "_sb" in name:
            timestamp = name.split("_sb")[0]
            groups[timestamp].append(f)
    
    # Find complete groups (16 subbands)
    for timestamp, files in sorted(groups.items(), reverse=True):
        if len(files) >= 16:
            return sorted(files)[:16]
    
    # Return partial group if no complete one
    for timestamp, files in sorted(groups.items(), reverse=True):
        if len(files) >= 4:  # Minimum for useful test
            return sorted(files)
    
    return None


class TimeUVDataLoad:
    """Benchmark pyuvdata UVData loading.
    
    Loading UVH5 files is I/O intensive.
    """
    
    timeout = 120
    
    def setup(self):
        """Find test HDF5 files."""
        self.hdf5_files = _find_subband_group()
        if self.hdf5_files is None:
            raise NotImplementedError("No HDF5 files available")
        
        # Use just one file for single-file benchmark
        self.single_file = self.hdf5_files[0]
    
    def time_load_single_subband(self):
        """Time loading a single subband HDF5 file."""
        from pyuvdata import UVData
        
        uvd = UVData()
        uvd.read(str(self.single_file), file_type="uvh5")
    
    def time_load_four_subbands(self):
        """Time loading 4 subbands and combining."""
        from pyuvdata import UVData
        
        uvd = UVData()
        for i, f in enumerate(self.hdf5_files[:4]):
            if i == 0:
                uvd.read(str(f), file_type="uvh5")
            else:
                uvd2 = UVData()
                uvd2.read(str(f), file_type="uvh5")
                uvd += uvd2


class TimeDirectMSWriter:
    """Benchmark direct MS writing.
    
    Uses the pipeline's DirectSubbandWriter for parallel subband writing.
    """
    
    timeout = 300
    
    def setup(self):
        """Prepare test data and output directory."""
        self.hdf5_files = _find_subband_group()
        if self.hdf5_files is None:
            raise NotImplementedError("No HDF5 files available")
        
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self.output_dir = SCRATCH_DIR / "bench_conversion"
        
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir()
        
        # Load first subband for writer test
        from pyuvdata import UVData
        self.uvd = UVData()
        self.uvd.read(str(self.hdf5_files[0]), file_type="uvh5")
        
        self.output_ms = self.output_dir / "bench_output.ms"
    
    def time_direct_ms_write(self):
        """Time direct MS writing using pipeline writer."""
        from dsa110_contimg.conversion.strategies.writers import get_writer
        
        writer_cls = get_writer("parallel-subband")
        writer = writer_cls(
            self.uvd,
            str(self.output_ms),
            file_list=[str(f) for f in self.hdf5_files[:4]],
        )
        writer.write()
    
    def teardown(self):
        """Clean up output files."""
        if hasattr(self, "output_dir") and self.output_dir.exists():
            shutil.rmtree(self.output_dir, ignore_errors=True)


class TimeFullConversion:
    """Benchmark complete HDF5 → MS conversion pipeline.
    
    Uses the full orchestrator for realistic timing.
    """
    
    timeout = 600
    
    def setup(self):
        """Prepare test data."""
        self.hdf5_files = _find_subband_group()
        if self.hdf5_files is None:
            raise NotImplementedError("No HDF5 files available")
        
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self.output_dir = SCRATCH_DIR / "bench_full_conversion"
        
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir()
        
        # Get timestamp from first file
        name = self.hdf5_files[0].name
        self.timestamp = name.split("_sb")[0]
    
    def time_convert_subband_group(self):
        """Time full subband group conversion."""
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            convert_single_group,
        )
        
        convert_single_group(
            [str(f) for f in self.hdf5_files],
            str(self.output_dir),
        )
    
    def teardown(self):
        """Clean up output files."""
        if hasattr(self, "output_dir") and self.output_dir.exists():
            shutil.rmtree(self.output_dir, ignore_errors=True)
