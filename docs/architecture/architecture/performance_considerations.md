# Performance Considerations for Pipeline Stages

This document outlines performance considerations, optimizations, and best
practices for pipeline stages.

## Overview

The DSA-110 Continuum Imaging Pipeline processes large datasets (GB to TB scale)
and must balance throughput, latency, and resource usage. This guide helps
developers write performant stages.

## Storage Architecture

Understanding storage types is critical for performance optimization:

| Mount Point | Type     | Speed     | Purpose                                |
| ----------- | -------- | --------- | -------------------------------------- |
| `/data/`    | HDD      | ~150 MB/s | Raw HDF5 files, source code, databases |
| `/stage/`   | NVMe SSD | ~2 GB/s   | Output MS files, working data          |
| `/scratch/` | NVMe SSD | ~2 GB/s   | Temporary files, builds                |
| `/dev/shm/` | tmpfs    | RAM speed | In-memory staging during conversion    |

**Key implications**:

- Read from `/data/` (HDD) is the I/O bottleneck
- Write to `/stage/` (SSD) is fast; prefer SSD for output
- Use `/dev/shm/` for intermediate files that are immediately consumed
- Use `/scratch/` for builds and temporary processing

## Key Performance Metrics

### 1. Throughput

**Definition:** Amount of data processed per unit time

**Targets:**

- Conversion: Process subband groups efficiently
- Calibration: Solve calibration tables quickly
- Imaging: Generate images within time windows
- Validation: Complete QA checks promptly

**Measurement:**

```python
import time
start_time = time.time()
result_context = stage.execute(context)
elapsed_time = time.time() - start_time
throughput = data_size_mb / elapsed_time  # MB/s
```

### 2. Latency

**Definition:** Time from input to output

**Targets:**

- Stage execution: Minimize per-stage latency
- Pipeline end-to-end: Complete within observation windows
- User-facing operations: Respond within seconds

**Considerations:**

- Parallel processing where possible
- Efficient I/O operations
- Minimize data copying
- Use appropriate data structures

### 3. Resource Usage

**Definition:** CPU, memory, disk, network usage

**Targets:**

- Memory: Stay within available RAM
- Disk: Minimize temporary file usage
- CPU: Utilize available cores efficiently
- Network: Minimize data transfer

## Performance Patterns

### Pattern 1: Lazy Evaluation

**Problem:** Loading all data into memory at once

**Anti-Pattern:**

```python
# BAD: Loads entire dataset
def execute(self, context: PipelineContext) -> PipelineContext:
    all_data = load_all_data(context.inputs["input_path"])  # May be GB!
    processed = process_all(all_data)
    return context.with_output("output", processed)
```

**Solution:**

```python
# GOOD: Process in chunks
def execute(self, context: PipelineContext) -> PipelineContext:
    input_path = context.inputs["input_path"]
    # Process in chunks, streaming where possible
    results = []
    for chunk in stream_data(input_path, chunk_size=1024*1024):  # 1MB chunks
        processed = process_chunk(chunk)
        results.append(processed)
    return context.with_output("output", combine_results(results))
```

### Pattern 2: Parallel Processing

**Problem:** Sequential processing of independent tasks

**Anti-Pattern:**

```python
# BAD: Sequential processing
def execute(self, context: PipelineContext) -> PipelineContext:
    results = []
    for item in items:
        result = process_item(item)  # Slow!
        results.append(result)
    return context.with_output("output", results)
```

**Solution:**

```python
# GOOD: Parallel processing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

def execute(self, context: PipelineContext) -> PipelineContext:
    items = context.inputs["items"]
    max_workers = self.config.conversion.max_workers

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_item, items))

    return context.with_output("output", results)
```

### Pattern 3: Efficient I/O

**Problem:** Inefficient file operations

**Anti-Pattern:**

```python
# BAD: Multiple small reads
def execute(self, context: PipelineContext) -> PipelineContext:
    with open(input_path, 'r') as f:
        for line in f:
            process_line(line)  # Many small I/O operations
```

**Solution:**

```python
# GOOD: Batch reads
def execute(self, context: PipelineContext) -> PipelineContext:
    with open(input_path, 'rb') as f:
        while True:
            chunk = f.read(1024 * 1024)  # 1MB chunks
            if not chunk:
                break
            process_chunk(chunk)
```

### Pattern 4: Memory Management

**Problem:** Keeping large objects in memory unnecessarily

**Anti-Pattern:**

```python
# BAD: Keeping large intermediate results
def execute(self, context: PipelineContext) -> PipelineContext:
    data = load_large_dataset()  # GB in memory
    intermediate = process_step1(data)  # Another GB
    result = process_step2(intermediate)  # Another GB
    # All three in memory at once!
    return context.with_output("output", result)
```

**Solution:**

```python
# GOOD: Release memory promptly
def execute(self, context: PipelineContext) -> PipelineContext:
    data = load_large_dataset()
    intermediate = process_step1(data)
    del data  # Release memory
    result = process_step2(intermediate)
    del intermediate  # Release memory
    return context.with_output("output", result)
```

### Pattern 5: Caching

**Problem:** Recomputing expensive operations

**Anti-Pattern:**

```python
# BAD: Recomputing every time
def execute(self, context: PipelineContext) -> PipelineContext:
    catalog = build_catalog()  # Expensive!
    matches = match_sources(catalog)
    return context.with_output("matches", matches)
```

**Solution:**

```python
# GOOD: Cache expensive operations
from functools import lru_cache

@lru_cache(maxsize=1)
def get_catalog(dec_deg):
    return build_catalog(dec_deg)

def execute(self, context: PipelineContext) -> PipelineContext:
    dec = extract_declination(context)
    catalog = get_catalog(dec)  # Cached!
    matches = match_sources(catalog)
    return context.with_output("matches", matches)
```

## HDF5 I/O Optimization

DSA-110 UVH5 files use HDF5 with compressed chunks, typically 2-4 MB per chunk.
The default h5py chunk cache (1 MB) is insufficient, causing **up to 1000x
slowdown** due to repeated chunk decompression.

### The Problem

When the chunk cache is smaller than the chunk size, h5py must:

1. Decompress the chunk to read data
2. Evict it from cache (cache full)
3. Re-decompress the same chunk for the next read

With DSA-110's 2-4 MB chunks and 1 MB default cache, this causes catastrophic
performance degradation for random access patterns.

### Solution 1: Global h5py Cache Configuration (Recommended)

The pipeline automatically configures h5py's default chunk cache via
monkey-patching. This affects **all** h5py.File() calls, including those in
third-party libraries like pyuvdata.

**Automatic activation**: The CLI and streaming converter call this at startup:

```python
from dsa110_contimg.utils.hdf5_io import configure_h5py_cache_defaults

configure_h5py_cache_defaults()  # Sets 16 MB cache for ALL h5py.File() calls
```

**Measured performance improvement**: 32% faster total conversion time, 48%
faster HDF5 reading phase (tested on 16-subband group conversion).

**For custom scripts**, call this before importing pyuvdata:

```python
# MUST be called BEFORE importing pyuvdata or other h5py-using libraries
from dsa110_contimg.utils.hdf5_io import configure_h5py_cache_defaults
configure_h5py_cache_defaults()

# Now pyuvdata will use 16 MB cache by default
from pyuvdata import UVData
uv = UVData()
uv.read("file.uvh5")  # Uses optimized 16 MB cache automatically
```

### Solution 2: Explicit Context Managers

For direct h5py access, use the optimized context managers:

```python
from dsa110_contimg.utils.hdf5_io import (
    open_uvh5,           # 16 MB cache - standard reads
    open_uvh5_metadata,  # 1 MB cache - header only
    open_uvh5_streaming, # 0 cache - single-pass sequential
    open_uvh5_large_cache,  # 64 MB cache - random access
)

# Quick metadata read (timestamps, frequencies)
with open_uvh5_metadata("/path/to/file.hdf5") as f:
    times = f["Header/time_array"][:]

# Standard visibility reads
with open_uvh5("/path/to/file.hdf5") as f:
    visdata = f["Data/visdata"][:]

# Intensive random access (downsampling, crossmatch)
with open_uvh5_large_cache("/path/to/file.hdf5") as f:
    # Random slicing operations
    subset = f["Data/visdata"][::10, :, :]
```

### Cache Size Guidelines

| Access Pattern  | Function                          | Cache Size | Use Case              |
| --------------- | --------------------------------- | ---------- | --------------------- |
| Global default  | `configure_h5py_cache_defaults()` | 16 MB      | All h5py.File() calls |
| Metadata only   | `open_uvh5_metadata()`            | 1 MB       | Quick header reads    |
| Sequential read | `open_uvh5()`                     | 16 MB      | Normal processing     |
| Single-pass     | `open_uvh5_streaming()`           | 0          | Streaming ingest      |
| Random access   | `open_uvh5_large_cache()`         | 64 MB      | Downsampling, slicing |

### Performance Impact

- **Global cache patch**: 32% faster conversion, 48% faster HDF5 reads
- **Metadata reads**: Already fast via `FastMeta`, now with proper cache
- **Sequential reads**: 10-100x improvement
- **Random access**: Up to 1000x improvement

### Checking Cache Status

```python
from dsa110_contimg.utils.hdf5_io import get_h5py_cache_info

info = get_h5py_cache_info()
print(info)
# {'default_rdcc_nbytes': 16777216, 'default_rdcc_nslots': 1009,
#  'default_rdcc_nbytes_mb': 16.0, 'configured_by_pipeline': True,
#  'patch_applied': True}
```

### Reference

Based on HDF Group best practices:
[Improving I/O Performance When Working with HDF5 Compressed Datasets](https://www.hdfgroup.org/2022/10/improving-io-performance-when-working-with-hdf5-compressed-datasets/)

## Conversion Pipeline Optimizations

The conversion pipeline (UVH5 → MS) has been optimized with several techniques
implemented in November 2025. These optimizations reduce total conversion time
by ~35% and HDF5 read time by ~48%.

### Optimization Summary

| Optimization             | Speedup | Location                                      |
| ------------------------ | ------- | --------------------------------------------- |
| h5py 16MB chunk cache    | 32%     | `utils/hdf5_io.py`                            |
| Batch Time() conversion  | 21.9x   | `conversion/helpers_coordinates.py`           |
| Parallel subband loading | ~2-3x   | `conversion/strategies/hdf5_orchestrator.py`  |
| Pre-allocated arrays     | ~10-15% | Multiple files                                |
| JIT warm-up at startup   | ~64ms   | `conversion/streaming/streaming_converter.py` |

### Batch Time Conversion

**Problem**: Creating `astropy.Time` objects in a loop is expensive (~2.7ms per
call for 24 times).

**Solution**: Batch convert all times with a single `Time()` call.

```python
# SLOW: Per-iteration Time object creation
for i, time_jd in enumerate(unique_times):
    time_mjd = Time(time_jd, format="jd").mjd  # 2.7ms for 24 times

# FAST: Batch conversion (21.9x faster)
mjd_unique = Time(unique_times, format="jd").mjd  # 0.12ms for 24 times
for i in range(n_unique):
    time_mjd = float(mjd_unique[i])
```

**Impact**: 21.9x speedup for JD→MJD conversion in `phase_to_meridian()`.

### Pre-allocation Patterns

**Problem**: Dynamic list resizing causes GC pressure with large objects.

**Solution**: Pre-allocate arrays and lists with known sizes.

```python
# SLOW: Dynamic list growth
acc = []
for path in file_paths:
    uvdata = UVData()
    uvdata.read(path)
    acc.append(uvdata)  # List resizing

# FAST: Pre-allocated list with index assignment
acc = [None] * len(file_paths)
for i, path in enumerate(file_paths):
    uvdata = UVData()
    uvdata.read(path)
    acc[i] = uvdata  # Direct index assignment
acc = [x for x in acc if x is not None]  # Safety filter
```

**Impact**: Reduced GC pressure when processing 16 subbands (~2-4 GB each).

### Parallel I/O for Subband Loading

**Problem**: Loading 16 subbands sequentially is I/O-bound.

**Solution**: Use `ThreadPoolExecutor` to parallelize HDF5 reads.

```bash
# CLI options for parallel I/O control
python -m dsa110_contimg.conversion.cli groups \
    --parallel-io \              # Enable parallel loading (default)
    --io-batch-size 4 \          # Subbands per batch
    --max-workers 4 \            # Thread pool size
    /data/incoming /stage/ms "2025-01-01" "2025-01-02"

# Disable for debugging or low-memory systems
python -m dsa110_contimg.conversion.cli groups \
    --no-parallel-io \
    /data/incoming /stage/ms "2025-01-01" "2025-01-02"
```

**Impact**: ~2-3x speedup for I/O-bound subband loading on systems with
sufficient memory and I/O bandwidth.

### Astropy for Astrometric Precision

**Note**: The pipeline uses rigorous `astropy` calculations for LST and
coordinate transformations instead of approximate numba fast paths. While numba
provided ~327x speedup for LST calculation, the ~1200 arcsec offset from
aberration-corrected ICRS coordinates was deemed unacceptable for scientific
data products. Astrometric rigor takes priority over performance in phase center
calculations.

### Optimization Decision Tree

Use this decision tree when optimizing conversion code:

```text
Is the operation I/O-bound?
├─ Yes → Consider parallel I/O with ThreadPoolExecutor
│        └─ Check: Is there enough memory for concurrent loads?
│
├─ No, it's CPU-bound
│   ├─ Is it a numpy/array operation?
│   │   └─ Yes → Use vectorized operations, avoid loops
│   │
│   ├─ Is it creating many small objects?
│   │   └─ Yes → Pre-allocate arrays/lists
│   │
│   └─ Is it calling astropy repeatedly?
│       └─ Yes → Batch the calls (e.g., Time(array) not Time(scalar))
│
└─ Is astrometric precision required?
    ├─ Yes → Use astropy (fast=False)
    └─ No  → Consider numba fast path (if available)
```

### Performance Regression Tests

Regression tests ensure optimizations remain effective. Run with:

```bash
conda activate casa6
python -m pytest tests/performance/test_io_optimizations.py -v
```

Key thresholds:

- Batch Time() conversion: <0.6ms for 24 times
- Batch speedup: >5x compared to per-iteration
- JIT warm-up: <500ms

See `tests/performance/test_io_optimizations.py` for detailed assertions.

### Benchmark Results (November 2025)

**Test**: 0834+555 calibrator conversion, 9 groups of 16 subbands each

| Metric                 | Value             |
| ---------------------- | ----------------- |
| Mean conversion time   | 2m 08s (128.6s)   |
| Median conversion time | 2m 08s (128.1s)   |
| Min conversion time    | 1m 18s (78.4s)    |
| Max conversion time    | 2m 31s (151.3s)   |
| Standard deviation     | ±20.5s            |
| MS file size           | ~5.1 GB per group |

**Pipeline stages included in timing**:

1. HDF5 parallel loading (4 subbands per batch)
2. Phase center computation (rigorous astropy)
3. Per-subband MS writes
4. MS concatenation (16 parts → 1)
5. Move from `/dev/shm/` to `/stage/` (SSD)
6. MS configuration and validation

**Notes**:

- First group is often faster (~78s) due to filesystem caching effects
- Variance is normal due to I/O patterns and concurrent system activity
- Reads from `/data/` (HDD) are the primary bottleneck
- Writes to `/stage/` (NVMe SSD) are fast

## Stage-Specific Performance

### Conversion Stage

**Bottlenecks:**

- UVH5 file reading (see [HDF5 I/O Optimization](#hdf5-io-optimization))
- MS file writing
- Data format conversion

**Optimizations:**

- Global h5py cache configuration (automatic in CLI)
- Use `hdf5_io` functions for optimized HDF5 access
- Use tmpfs for staging (fast I/O)
- Parallel subband processing
- Efficient data structures
- Minimize data copying

**Example:**

```python
# Use tmpfs for fast I/O
if self.config.conversion.stage_to_tmpfs:
    tmpfs_path = context.config.paths.scratch_dir
    # Write to tmpfs first, then move to final location
```

### Calibration Stage

**Bottlenecks:**

- CASA calibration solving
- Table I/O
- Calibrator selection

**Optimizations:**

- Cache calibration tables
- Parallel calibration solving
- Efficient table storage
- Minimize CASA overhead

### Imaging Stage

**Bottlenecks:**

- tclean execution
- Image I/O
- Memory usage

**Optimizations:**

- Use appropriate imaging parameters
- Efficient memory management
- Parallel imaging where possible
- Optimize tclean settings

### Validation Stage

**Bottlenecks:**

- Catalog queries
- Cross-matching
- Report generation

**Optimizations:**

- Cache catalog queries
- Efficient matching algorithms
- Parallel validation checks
- Lazy report generation

## Resource Management

### Memory

**Best Practices:**

- Monitor memory usage
- Release large objects promptly
- Use generators for large datasets
- Set memory limits

**Example:**

```python
import psutil
import os

def execute(self, context: PipelineContext) -> PipelineContext:
    process = psutil.Process(os.getpid())
    memory_before = process.memory_info().rss / 1024 / 1024  # MB

    result = process_data(context)

    memory_after = process.memory_info().rss / 1024 / 1024  # MB
    logger.info(f"Memory usage: {memory_before:.1f}MB -> {memory_after:.1f}MB")

    return context.with_output("result", result)
```

### Disk Space

**Best Practices:**

- Use tmpfs for temporary files
- Clean up temporary files promptly
- Monitor disk usage
- Compress intermediate data

**Example:**

```python
def execute(self, context: PipelineContext) -> PipelineContext:
    # Use tmpfs for temporary files
    temp_dir = Path(context.config.paths.scratch_dir) / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Process with temporary files
        result = process_with_temp_files(temp_dir)
        return context.with_output("result", result)
    finally:
        # Always clean up
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
```

### CPU Usage

**Best Practices:**

- Use all available cores
- Balance parallelism vs overhead
- Profile CPU-bound operations
- Use appropriate algorithms

**Example:**

```python
import multiprocessing

def execute(self, context: PipelineContext) -> PipelineContext:
    max_workers = min(
        self.config.conversion.max_workers,
        multiprocessing.cpu_count()
    )

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_item, items))

    return context.with_output("results", results)
```

## Profiling

### CPU Profiling

```python
import cProfile
import pstats

def execute(self, context: PipelineContext) -> PipelineContext:
    profiler = cProfile.Profile()
    profiler.enable()

    result = process_data(context)

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions

    return context.with_output("result", result)
```

### Memory Profiling

```python
from memory_profiler import profile

@profile
def execute(self, context: PipelineContext) -> PipelineContext:
    result = process_data(context)
    return context.with_output("result", result)
```

### I/O Profiling

```python
import time

def execute(self, context: PipelineContext) -> PipelineContext:
    io_times = {}

    start = time.time()
    data = read_file(input_path)
    io_times['read'] = time.time() - start

    start = time.time()
    write_file(output_path, result)
    io_times['write'] = time.time() - start

    logger.info(f"I/O times: {io_times}")
    return context.with_output("result", result)
```

## Performance Testing

### Benchmarking

```python
import time
import statistics

def benchmark_stage(stage, context, iterations=10):
    times = []
    for _ in range(iterations):
        start = time.time()
        result = stage.execute(context)
        elapsed = time.time() - start
        times.append(elapsed)

    return {
        'mean': statistics.mean(times),
        'median': statistics.median(times),
        'stdev': statistics.stdev(times),
        'min': min(times),
        'max': max(times)
    }
```

### Load Testing

```python
def load_test_stage(stage, contexts, max_concurrent=4):
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = [executor.submit(stage.execute, ctx) for ctx in contexts]
        results = [f.result() for f in futures]

    return results
```

## Performance Checklist

When writing a new stage:

- [ ] Profile CPU usage
- [ ] Monitor memory usage
- [ ] Check disk I/O patterns
- [ ] Use parallel processing where appropriate
- [ ] Minimize data copying
- [ ] Release memory promptly
- [ ] Clean up temporary files
- [ ] Use efficient data structures
- [ ] Cache expensive operations
- [ ] Test with realistic data sizes
- [ ] Benchmark performance
- [ ] Document performance characteristics

## Related Documentation

- [Pipeline Stage Architecture](../pipeline/pipeline_stage_architecture.md)
- [Pipeline Patterns](../pipeline/pipeline_patterns.md)
- Testing Guide
