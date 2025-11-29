# Measurement Set Writer Strategies

This document describes the MS writing strategies available in the DSA-110
Continuum Imaging Pipeline.

## Overview

The pipeline converts UVH5 subband files to CASA Measurement Sets using
different writer strategies optimized for different use cases:

| Writer                     | Location            | Use Case                       | Subbands |
| -------------------------- | ------------------- | ------------------------------ | -------- |
| `DirectSubbandWriter`      | Production (`src/`) | 16-subband parallel processing | 1-16     |
| `PyuvdataMonolithicWriter` | Testing (`tests/`)  | Simple test scenarios          | ≤2       |

## Production Writers

Production writers are located in:

```
backend/src/dsa110_contimg/conversion/strategies/writers.py
```

### DirectSubbandWriter

The primary production writer for DSA-110 continuum imaging. Processes 16
subbands in parallel for optimal performance.

**Features:**

- Parallel per-subband MS creation using `ProcessPoolExecutor`
- Automatic SPW concatenation via CASA `concat`
- Optional SPW merging via `mstransform`
- tmpfs staging for I/O optimization
- Checkpoint recovery on failure

**Parameters:**

| Parameter               | Type        | Default    | Description                            |
| ----------------------- | ----------- | ---------- | -------------------------------------- |
| `uv`                    | `UVData`    | required   | UVData object (metadata only)          |
| `ms_path`               | `str`       | required   | Output Measurement Set path            |
| `file_list`             | `List[str]` | required   | List of UVH5 subband file paths        |
| `scratch_dir`           | `str`       | `None`     | Directory for temporary files          |
| `max_workers`           | `int`       | `4`        | Maximum parallel workers               |
| `stage_to_tmpfs`        | `bool`      | `False`    | Stage intermediate files to `/dev/shm` |
| `tmpfs_path`            | `str`       | `/dev/shm` | Path to tmpfs mount                    |
| `merge_spws`            | `bool`      | `False`    | Merge SPWs after concatenation         |
| `remove_sigma_spectrum` | `bool`      | `True`     | Remove SIGMA_SPECTRUM column           |

**Usage:**

```python
from dsa110_contimg.conversion.strategies import DirectSubbandWriter, get_writer

# Option 1: Use get_writer()
writer_cls = get_writer("parallel-subband")  # or "auto", "direct-subband"
writer = writer_cls(
    uvdata,
    "/stage/dsa110-contimg/ms/observation.ms",
    file_list=subband_files,
    scratch_dir="/scratch/conversion",
    max_workers=8,
)
writer.write()

# Option 2: Direct instantiation
from dsa110_contimg.conversion.strategies import DirectSubbandWriter

writer = DirectSubbandWriter(
    uvdata,
    "/stage/dsa110-contimg/ms/observation.ms",
    file_list=subband_files,
)
result = writer.write()  # Returns "parallel-subband"
```

### ParallelSubbandWriter

Backwards-compatible alias for `DirectSubbandWriter`. Use `DirectSubbandWriter`
for new code.

```python
from dsa110_contimg.conversion.strategies import ParallelSubbandWriter

# Equivalent to DirectSubbandWriter
writer = ParallelSubbandWriter(uvdata, ms_path, file_list=files)
```

### get_writer()

Factory function to get writer classes by name.

```python
from dsa110_contimg.conversion.strategies import get_writer

# Valid writer types
writer_cls = get_writer("parallel-subband")  # DirectSubbandWriter
writer_cls = get_writer("direct-subband")    # DirectSubbandWriter
writer_cls = get_writer("auto")              # DirectSubbandWriter (default)

# Blocked writer types (raises ValueError)
get_writer("pyuvdata")  # ValueError: use tests/fixtures/writers.py
```

## Testing Writers

Testing writers are located in:

```
backend/tests/fixtures/writers.py
```

These writers are **intentionally separated** from production code to prevent
accidental use in production pipelines.

### PyuvdataMonolithicWriter

Simple wrapper around `pyuvdata.UVData.write_ms()` for testing scenarios.

**Limitations:**

- Loads all data into memory simultaneously
- Not efficient for >2 subbands
- No parallel processing
- No SPW merging

**Usage:**

```python
from tests.fixtures.writers import PyuvdataMonolithicWriter, get_test_writer

# Option 1: Use get_test_writer()
writer_cls = get_test_writer("pyuvdata")
writer = writer_cls(uvdata, "/tmp/test.ms")
writer.write()

# Option 2: Direct instantiation
writer = PyuvdataMonolithicWriter(uvdata, "/tmp/test.ms")
result = writer.write()  # Returns "pyuvdata"
```

### get_test_writer()

Factory function for testing writers.

```python
from tests.fixtures.writers import get_test_writer

writer_cls = get_test_writer("pyuvdata")           # PyuvdataMonolithicWriter
writer_cls = get_test_writer("pyuvdata-monolithic") # PyuvdataMonolithicWriter
```

## Design Rationale

### Why Separate Production and Testing Writers?

1. **Prevent accidental misuse**: Calling `get_writer("pyuvdata")` in production
   code raises `ValueError` with a clear message directing developers to the
   correct import path.

2. **Clear dependency boundaries**: Production code in `src/` never imports from
   `tests/`, making the dependency graph clean.

3. **Different optimization goals**:
   - Production: Parallel processing, memory efficiency, I/O optimization
   - Testing: Simplicity, fast setup, minimal dependencies

### Writer Selection Guidelines

| Scenario                  | Writer                     | Reason                         |
| ------------------------- | -------------------------- | ------------------------------ |
| Production pipeline       | `DirectSubbandWriter`      | Parallel, memory-efficient     |
| Unit tests                | `PyuvdataMonolithicWriter` | Simple, fast setup             |
| Integration tests (small) | `PyuvdataMonolithicWriter` | Quick validation               |
| Integration tests (full)  | `DirectSubbandWriter`      | Test production path           |
| Benchmarking              | `DirectSubbandWriter`      | Measure production performance |

## Performance Comparison

| Writer                     | 16 Subbands    | 2 Subbands | Memory     |
| -------------------------- | -------------- | ---------- | ---------- |
| `DirectSubbandWriter`      | ~3-4 min       | ~30 sec    | ~2 GB peak |
| `PyuvdataMonolithicWriter` | N/A (too slow) | ~20 sec    | ~4 GB peak |

## See Also

- [Conversion Pipeline Overview](../architecture/pipeline/pipeline_overview.md)
- [CLI Reference](cli.md)
- [Error Handling Guide](../guides/error-handling.md)
