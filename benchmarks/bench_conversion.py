"""
DSA-110 HDF5 :arrow_right: MS Conversion Benchmarks

Benchmarks for the UVH5 to Measurement Set conversion pipeline.
Following the actual pipeline workflow:
1. Copy HDF5 files from /data/incoming (HDD) to /scratch (SSD)
2. Run conversion from SSD
3. Output MS to /scratch

This mirrors how the streaming converter stages data before processing.
"""

import shutil
from collections import defaultdict
from pathlib import Path

HDF5_DIR = Path("/data/incoming")
SCRATCH_DIR = Path("/scratch/asv_benchmarks")


def _find_subband_group():
    """Find a complete subband group (16 files with same timestamp)."""
    if not HDF5_DIR.exists():
        return None
    
    # Group files by timestamp prefix
    groups = defaultdict(list)
    for f in HDF5_DIR.glob("*_sb*.hdf5"):
        name = f.name
        if "_sb" in name:
            timestamp = name.split("_sb")[0]
            groups[timestamp].append(f)
    
    # Find complete groups (16 subbands)
    for timestamp, files in sorted(groups.items(), reverse=True):
        if len(files) >= 16:
            return sorted(files)[:16]
    
    return None


def _stage_files_to_ssd(hdf5_files, dest_dir):
    """Copy HDF5 files to SSD scratch, return new paths."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    staged = []
    for f in hdf5_files:
        dest = dest_dir / f.name
        if not dest.exists():
            shutil.copy2(f, dest)
        staged.append(dest)
    return staged


class TimeUVDataLoad:
    """Benchmark pyuvdata UVData loading from SSD.
    
    Files are staged to /scratch before timing.
    """
    
    timeout = 300
    number = 1
    repeat = 1
    
    def setup(self):
        """Stage HDF5 files to SSD."""
        self.hdf5_files = _find_subband_group()
        if self.hdf5_files is None:
            raise NotImplementedError("No complete HDF5 subband group available")
        
        # Stage files to SSD (like the real pipeline does)
        self.staging_dir = SCRATCH_DIR / "hdf5_staged"
        self.staged_files = _stage_files_to_ssd(self.hdf5_files, self.staging_dir)
        self.single_file = self.staged_files[0]
    
    def time_load_single_subband(self):
        """Time loading a single subband HDF5 file from SSD."""
        from pyuvdata import UVData
        
        uvd = UVData()
        uvd.read(
            str(self.single_file),
            file_type="uvh5",
            run_check=False,
            run_check_acceptability=False,
            strict_uvw_antpos_check=False,
        )
    
    def time_load_four_subbands(self):
        """Time loading and combining 4 subbands from SSD using pipeline function."""
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            _load_and_merge_subbands,
        )
        
        _load_and_merge_subbands(
            [str(f) for f in self.staged_files[:4]],
            batch_size=4,
        )


class TimeFullConversion:
    """Benchmark complete HDF5 :arrow_right: MS conversion from SSD.
    
    Uses the pipeline's actual conversion functions with files staged to SSD.
    """
    
    timeout = 600
    number = 1
    repeat = 1
    
    def setup(self):
        """Stage HDF5 files to SSD and prepare output directory."""
        self.hdf5_files = _find_subband_group()
        if self.hdf5_files is None:
            raise NotImplementedError("No complete HDF5 subband group available")
        
        # Stage input files to SSD
        self.staging_dir = SCRATCH_DIR / "hdf5_staged"
        self.staged_files = _stage_files_to_ssd(self.hdf5_files, self.staging_dir)
        
        # Output directory on SSD
        self.output_dir = SCRATCH_DIR / "ms_output"
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True)
    
    def time_convert_subband_group(self):
        """Time full subband group conversion from SSD."""
        from astropy import units as u
        from astropy.time import Time

        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            convert_subband_groups_to_ms,
        )
        
        # Get timestamp from first file for time range
        name = self.staged_files[0].name
        timestamp = name.split("_sb")[0]
        
        # Need start < end, add 1 second
        t = Time(timestamp, format="isot")
        start_time = (t - 1 * u.s).isot
        end_time = (t + 1 * u.s).isot
        
        convert_subband_groups_to_ms(
            input_dir=str(self.staging_dir),
            output_dir=str(self.output_dir),
            start_time=start_time,
            end_time=end_time,
        )
    
    def teardown(self):
        """Clean up output MS files (keep staged HDF5 for reuse)."""
        if hasattr(self, "output_dir") and self.output_dir.exists():
            shutil.rmtree(self.output_dir, ignore_errors=True)
