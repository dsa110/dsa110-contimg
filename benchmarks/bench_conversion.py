"""
DSA-110 HDF5 → MS Conversion Benchmarks

Benchmarks for the UVH5 to Measurement Set conversion:
- Single subband loading
- Multi-subband combining
- Direct MS writing

NOTE: These benchmarks are DISABLED by default because:
1. HDF5 files on /data are on slow HDD storage
2. Each subband file is ~145 MB, loading 16 takes several minutes
3. Use --bench bench_conversion to explicitly run these

To run conversion benchmarks explicitly:
    asv run --bench bench_conversion
"""

# Conversion benchmarks disabled - too slow for routine benchmarking
# The files are on HDD and take 5+ minutes per group to load

_SKIP_REASON = "Conversion benchmarks disabled (HDD I/O too slow)"


class TimeUVDataLoad:
    """Benchmark pyuvdata UVData loading - DISABLED."""
    
    def setup(self):
        raise NotImplementedError(_SKIP_REASON)
    
    def time_load_single_subband(self):
        pass


class TimeDirectMSWriter:
    """Benchmark direct MS writing - DISABLED."""
    
    def setup(self):
        raise NotImplementedError(_SKIP_REASON)
    
    def time_direct_ms_write(self):
        pass


class TimeFullConversion:
    """Benchmark full conversion pipeline - DISABLED."""
    
    def setup(self):
        raise NotImplementedError(_SKIP_REASON)
    
    def time_convert_subband_group(self):
        pass
