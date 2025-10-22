# UVH5 Downsampling Guide

This guide covers the UVH5 downsampling tools for reducing file sizes and processing time in the DSA-110 continuum imaging pipeline.

## Overview

The downsampling tools provide three levels of functionality:

1. **Single File Processing** (`downsample_hdf5_fast.py`) - Process individual UVH5 files
2. **Batch Processing** (`downsample_hdf5_batch.py`) - Process directories of UVH5 files in parallel
3. **Original Implementation** (`downsample_hdf5.py`) - Reference implementation (slower)

## Quick Start

### Single File Downsampling

```bash
# Time downsampling by factor of 2
python3 src/dsa110_contimg/conversion/downsample_hdf5_fast.py input.uvh5 output.uvh5 --time-factor 2

# Frequency downsampling by factor of 4
python3 src/dsa110_contimg/conversion/downsample_hdf5_fast.py input.uvh5 output.uvh5 --freq-factor 4

# Combined downsampling
python3 src/dsa110_contimg/conversion/downsample_hdf5_fast.py input.uvh5 output.uvh5 --time-factor 2 --freq-factor 4
```

### Batch Processing

```bash
# Process all UVH5 files in a directory
python3 src/dsa110_contimg/conversion/downsample_hdf5_batch.py input_dir/ output_dir/ --time-factor 2

# Process with parallel workers
python3 src/dsa110_contimg/conversion/downsample_hdf5_batch.py input_dir/ output_dir/ --time-factor 2 --freq-factor 4 --max-workers 4
```

## Performance Results

Based on testing with real DSA-110 data (111,744 integrations, 48 channels, 138.6 MB):

| Operation | Time | Compression Ratio | File Size |
|-----------|------|-------------------|-----------|
| Time downsampling (2x) | 2.7s | 2.1x | 66.9 MB |
| Frequency downsampling (4x) | 2.0s | 3.8x | 36.5 MB |
| Combined (2x time, 4x freq) | 1.6s | 7.2x | 19.2 MB |
| Batch processing (3 files) | 2.6s | 7.2x | 57.5 MB total |

## Command Line Options

### Common Options

- `--time-factor N`: Downsample time by merging N integrations (default: 1)
- `--freq-factor N`: Downsample frequency by merging N channels (default: 1)
- `--method {average,weighted}`: Merging method (default: average)
- `--chunk-size N`: Processing chunk size (default: 10000)
- `--verbose, -v`: Enable verbose logging

### Batch Processing Options

- `--max-workers N`: Maximum parallel workers (default: CPU count)
- `input_dir`: Input directory containing UVH5 files
- `output_dir`: Output directory for processed files

## File Naming Convention

The batch processor automatically creates descriptive output filenames:

- Time only: `filename_ds2t.hdf5`
- Frequency only: `filename_ds4f.hdf5`
- Combined: `filename_ds2t4f.hdf5`

## Integration with Pipeline

### Pre-processing for Calibration

```bash
# Downsample before MS conversion to reduce processing time
python3 src/dsa110_contimg/conversion/downsample_hdf5_batch.py \
    /data/raw_uvh5/ \
    /data/downsampled_uvh5/ \
    --time-factor 2 \
    --freq-factor 4 \
    --max-workers 8

# Then convert to MS
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    --input-dir /data/downsampled_uvh5/ \
    --output-dir /data/ms_files/
```

### Memory Management

For very large files, adjust chunk size:

```bash
# For files with >1M integrations
python3 src/dsa110_contimg/conversion/downsample_hdf5_fast.py \
    large_file.uvh5 output.uvh5 \
    --time-factor 2 \
    --chunk-size 5000
```

## Technical Details

### Downsampling Methods

1. **Average**: Simple arithmetic mean
   - Visibilities: `mean(vis_data)`
   - Flags: `any(flags)` (OR operation)
   - Nsamples: `sum(nsamples)`

2. **Weighted**: Sample-weighted average
   - Visibilities: `sum(vis_data * weights)` where `weights = nsamples / sum(nsamples)`
   - Flags: `any(flags)`
   - Nsamples: `sum(nsamples)`

### Performance Optimizations

- **Bulk Operations**: Process 10,000 integrations per chunk
- **Optimal Chunking**: HDF5 datasets chunked for efficient I/O
- **Parallel Processing**: Multi-core processing for batch operations
- **Compression**: gzip compression for further size reduction
- **Memory Efficiency**: Streaming processing to handle large files

### Data Integrity

- Preserves all header metadata
- Maintains UVH5 format compatibility
- Handles UVW coordinate averaging
- Updates integration times and channel widths
- Preserves antenna and polarization information

## Troubleshooting

### Common Issues

1. **Memory Errors**: Reduce `--chunk-size`
2. **Slow Processing**: Use `--max-workers` for parallel processing
3. **Import Errors**: Ensure you're in the casa6 conda environment

### Performance Tips

1. Use batch processing for multiple files
2. Adjust chunk size based on available memory
3. Use parallel processing for large datasets
4. Consider frequency downsampling for significant size reduction

## Examples

### Complete Workflow

```bash
# 1. Downsample all subbands
python3 src/dsa110_contimg/conversion/downsample_hdf5_batch.py \
    /data/raw_subbands/ \
    /data/downsampled_subbands/ \
    --time-factor 2 \
    --freq-factor 4 \
    --max-workers 8

# 2. Convert to MS
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    --input-dir /data/downsampled_subbands/ \
    --output-dir /data/ms_files/

# 3. Run calibration
bash scripts/calibrate_bandpass.sh \
    --ms /data/ms_files/ \
    --auto-fields \
    --cal-catalog /data/catalogs/vlacalibrators.txt
```

### Custom Processing

```bash
# Aggressive downsampling for quick testing
python3 src/dsa110_contimg/conversion/downsample_hdf5_fast.py \
    input.uvh5 output.uvh5 \
    --time-factor 4 \
    --freq-factor 8 \
    --method weighted \
    --chunk-size 2000
```

This downsampling approach provides significant performance improvements and file size reduction while maintaining data quality for calibration and imaging workflows.
