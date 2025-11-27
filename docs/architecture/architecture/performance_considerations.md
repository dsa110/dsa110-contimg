# Performance Considerations for Pipeline Stages

This document outlines performance considerations, optimizations, and best
practices for pipeline stages.

## Overview

The DSA-110 Continuum Imaging Pipeline processes large datasets (GB to TB scale)
and must balance throughput, latency, and resource usage. This guide helps
developers write performant stages.

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

### Solution: Use `dsa110_contimg.utils.hdf5_io`

The `hdf5_io` module provides optimized context managers:

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

| Access Pattern  | Function                  | Cache Size | Use Case              |
| --------------- | ------------------------- | ---------- | --------------------- |
| Metadata only   | `open_uvh5_metadata()`    | 1 MB       | Quick header reads    |
| Sequential read | `open_uvh5()`             | 16 MB      | Normal processing     |
| Single-pass     | `open_uvh5_streaming()`   | 0          | Streaming ingest      |
| Random access   | `open_uvh5_large_cache()` | 64 MB      | Downsampling, slicing |

### Performance Impact

- **Metadata reads**: Already fast via `FastMeta`, now with proper cache
- **Sequential reads**: 10-100x improvement
- **Random access**: Up to 1000x improvement

### Reference

Based on HDF Group best practices:
[Improving I/O Performance When Working with HDF5 Compressed Datasets](https://www.hdfgroup.org/2022/10/improving-io-performance-when-working-with-hdf5-compressed-datasets/)

## Stage-Specific Performance

### Conversion Stage

**Bottlenecks:**

- UVH5 file reading (see [HDF5 I/O Optimization](#hdf5-io-optimization))
- MS file writing
- Data format conversion

**Optimizations:**

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
