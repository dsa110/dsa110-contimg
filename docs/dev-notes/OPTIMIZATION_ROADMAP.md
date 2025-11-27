# Performance Optimization Roadmap

**Created**: 2025-11-27  
**Status**: In Progress  
**Branch**: `master-dev`

## Overview

This roadmap tracks the implementation of performance optimizations for the
DSA-110 continuum imaging pipeline. The groundwork has been laid with core
modules; this document tracks integration into production code paths.

## Current Performance Baseline

| Metric                  | Before Optimization | After Phase 1 | Target         |
| ----------------------- | ------------------- | ------------- | -------------- |
| Single group conversion | 2m 40s              | 1m 43s        | < 1m 30s       |
| HDF5 read time          | 115.8s              | 56.7s         | < 45s          |
| Streaming latency       | —                   | —             | < 2m per group |

---

## Phase 1: Foundation (✅ COMPLETED)

### 1.1 HDF5 Chunk Cache Optimization

- [x] Create `utils/hdf5_io.py` with context managers
- [x] Implement `configure_h5py_cache_defaults()` monkey-patch
- [x] Integrate into CLI entry point (`conversion/cli.py`)
- [x] Integrate into streaming converter
- [x] Document in `performance_considerations.md`

### 1.2 Numba Acceleration Module

- [x] Create `utils/numba_accel.py`
- [x] Implement `angular_separation_jit()` with parallel support
- [x] Implement `rotate_xyz_to_uvw_jit()` with parallel support
- [x] Implement `approx_lst_jit()` for fast LST calculation
- [x] Implement `compute_phase_corrections_jit()`
- [x] Implement `warm_up_jit()` for pre-compilation
- [x] Add graceful fallback when numba unavailable

### 1.3 Parallel I/O Infrastructure

- [x] Implement `_load_and_merge_subbands_parallel()` in orchestrator
- [x] Add `parallel_io` and `max_io_workers` parameters
- [x] Pre-allocate result arrays to avoid resizing

### 1.4 Memory-Mapped I/O

- [x] Add `open_uvh5_mmap()` context manager
- [x] Export from `utils/__init__.py`

---

## Phase 2: Numba Integration (🔄 IN PROGRESS)

**Goal**: Replace numpy/astropy computations with JIT-compiled versions in hot
paths.

### 2.1 UVW Calculation Acceleration

**File**: `conversion/helpers_coordinates.py`  
**Function**: `compute_and_set_uvw()`  
**Effort**: 4 hours  
**Priority**: HIGH

- [ ] Profile current `compute_and_set_uvw()` to identify bottlenecks
- [ ] Replace pyuvdata's `calc_uvw` with `rotate_xyz_to_uvw_jit()` where
      applicable
- [ ] Benchmark improvement (target: 5-10x for UVW computation)
- [ ] Add unit tests for numerical equivalence
- [ ] Update docstrings with performance notes

```python
# Target integration point in compute_and_set_uvw():
from dsa110_contimg.utils.numba_accel import rotate_xyz_to_uvw_jit

# Replace:
#   uvw_all = uvutils.calc_uvw(...)
# With:
#   uvw_all = rotate_xyz_to_uvw_jit(baseline_xyz, ha_array, dec_rad)
```

### 2.2 LST Calculation Optimization

**File**: `conversion/helpers_coordinates.py`  
**Function**: `get_meridian_coords()`  
**Effort**: 2 hours  
**Priority**: MEDIUM

- [ ] Profile astropy overhead in `get_meridian_coords()`
- [ ] Add fast path using `approx_lst_jit()` for phase tracking
- [ ] Keep astropy path for high-precision requirements
- [ ] Add accuracy threshold parameter (default: use fast path)

```python
# Target integration:
def get_meridian_coords(pt_dec, time_mjd, fast=True):
    if fast:
        from dsa110_contimg.utils.numba_accel import approx_lst_jit
        lst = approx_lst_jit(np.array([time_mjd]), OVRO_LON_RAD)[0]
        ra = lst  # RA = LST at meridian
        return ra * u.rad, pt_dec
    else:
        # Existing astropy implementation
        ...
```

### 2.3 Streaming Converter JIT Warm-up

**File**: `conversion/streaming/streaming_converter.py`  
**Effort**: 1 hour  
**Priority**: HIGH

- [ ] Call `warm_up_jit()` during daemon initialization
- [ ] Log warm-up timing
- [ ] Ensure warm-up happens before first observation processing

```python
# In StreamingConverter.__init__() or start():
from dsa110_contimg.utils.numba_accel import warm_up_jit, NUMBA_AVAILABLE

if NUMBA_AVAILABLE:
    t0 = time.time()
    warm_up_jit()
    logger.info(f"JIT functions warmed up in {time.time()-t0:.2f}s")
```

---

## Phase 3: Memory-Mapped I/O Integration

**Goal**: Use memory-mapped I/O for appropriate scenarios.

### 3.1 Fast File Validation

**File**: `conversion/streaming/streaming_converter.py`  
**Effort**: 2 hours  
**Priority**: MEDIUM

- [ ] Create `quick_validate_uvh5()` using `open_uvh5_mmap()`
- [ ] Replace current validation in queue processor
- [ ] Benchmark validation speed improvement

```python
from dsa110_contimg.utils.hdf5_io import open_uvh5_mmap

def quick_validate_uvh5(path: str) -> tuple[bool, str]:
    """Fast validation using memory-mapped read."""
    try:
        with open_uvh5_mmap(path) as f:
            if "Header" not in f:
                return False, "Missing Header group"
            if "Data" not in f:
                return False, "Missing Data group"
            if f["Header/time_array"].shape[0] == 0:
                return False, "Empty time_array"
            return True, "OK"
    except Exception as e:
        return False, str(e)
```

### 3.2 QA Script Optimization

**Files**: `qa/*.py`  
**Effort**: 3 hours  
**Priority**: LOW

- [ ] Identify QA scripts that read HDF5 files
- [ ] Replace `h5py.File()` with `open_uvh5_mmap()` for read-only access
- [ ] Add memory usage monitoring

---

## Phase 4: Parallel Loading Integration

**Goal**: Enable parallel subband loading in all applicable code paths.

### 4.1 PyUVData Writer Strategy

**File**: `conversion/strategies/pyuvdata_monolithic.py`  
**Effort**: 2 hours  
**Priority**: MEDIUM

- [ ] Update to use `_load_and_merge_subbands()` with `parallel_io=True`
- [ ] Add CLI flag `--parallel-load` (default: True)
- [ ] Benchmark improvement for pyuvdata writer

### 4.2 Benchmark Suite Update

**File**: `benchmarks/bench_conversion.py`  
**Effort**: 1 hour  
**Priority**: LOW

- [ ] Add benchmark for parallel vs sequential loading
- [ ] Add benchmark for different `max_io_workers` values
- [ ] Document optimal worker count for different storage types

---

## Phase 5: Pre-allocation Patterns

**Goal**: Apply pre-allocation pattern to reduce GC pressure in hot paths.

### 5.1 Visibility Processing Pre-allocation

**File**: `conversion/strategies/direct_subband.py`  
**Effort**: 3 hours  
**Priority**: MEDIUM

- [ ] Profile memory allocation patterns during conversion
- [ ] Pre-allocate visibility arrays based on expected size
- [ ] Reduce intermediate array creation in concat operations

### 5.2 Phase Center Array Reuse

**File**: `conversion/helpers_coordinates.py`  
**Effort**: 2 hours  
**Priority**: LOW

- [ ] Identify repeated array allocations in `phase_to_meridian()`
- [ ] Create reusable buffer for phase center calculations
- [ ] Benchmark memory usage reduction

---

## Phase 6: Measurement & Validation

### 6.1 Performance Regression Tests

**Effort**: 4 hours  
**Priority**: HIGH

- [ ] Add performance assertions to CI
- [ ] Set thresholds based on current optimized performance
- [ ] Alert on >10% regression

### 6.2 Documentation Update

**Effort**: 2 hours  
**Priority**: MEDIUM

- [ ] Update `performance_considerations.md` with all optimizations
- [ ] Add optimization decision tree (when to use what)
- [ ] Document environment-specific tuning (HDD vs SSD vs NVMe)

---

## Implementation Schedule

| Week | Phase    | Tasks                             | Owner |
| ---- | -------- | --------------------------------- | ----- |
| 1    | 2.1, 2.3 | UVW acceleration, JIT warm-up     | TBD   |
| 2    | 2.2, 3.1 | LST optimization, fast validation | TBD   |
| 3    | 4.1, 4.2 | Parallel loading integration      | TBD   |
| 4    | 5.1, 5.2 | Pre-allocation patterns           | TBD   |
| 5    | 6.1, 6.2 | Testing & documentation           | TBD   |

---

## Success Metrics

| Metric                     | Current | Phase 2 Target | Phase 5 Target |
| -------------------------- | ------- | -------------- | -------------- |
| Single group conversion    | 1m 43s  | 1m 30s         | < 1m 15s       |
| Streaming latency          | ~2m     | < 1m 45s       | < 1m 30s       |
| Memory usage (16 subbands) | ~4 GB   | ~3.5 GB        | < 3 GB         |
| CI benchmark variance      | ±15%    | ±10%           | ±5%            |

---

## Dependencies

- **numba >= 0.58**: Required for parallel prange support
- **h5py >= 3.8**: Required for core driver memory mapping
- **numpy >= 1.24**: Required for efficient array operations

---

## Risks & Mitigations

| Risk                                        | Impact | Mitigation                            |
| ------------------------------------------- | ------ | ------------------------------------- |
| Numba not available in some environments    | Medium | Graceful fallback already implemented |
| Memory mapping fails on large files         | Low    | Size check before using mmap          |
| Parallel loading causes resource contention | Medium | Configurable worker count             |
| JIT compilation adds startup latency        | Low    | warm_up_jit() at daemon start         |

---

## References

- [HDF Group: Improving I/O Performance](https://support.hdfgroup.org/documentation/hdf5/latest/improve_compressed_perf.html)
- [Numba Documentation](https://numba.readthedocs.io/)
- [h5py Core Driver](https://docs.h5py.org/en/stable/high/file.html#file-drivers)
- `docs/architecture/performance_considerations.md`
