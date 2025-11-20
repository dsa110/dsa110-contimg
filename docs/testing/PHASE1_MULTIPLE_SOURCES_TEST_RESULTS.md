# Phase 1: Multiple Sources Adaptive Binning Test Results

**Date:** 2025-11-09  
**Test Type:** Multiple sources processed in parallel  
**MS:** `/stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T13:45:34.ms`  
**Sources:** 3 sources processed concurrently

## Test Configuration

- **Source 1:** RA=124.526792°, Dec=54.620694° (known source)
- **Source 2:** RA=124.530000°, Dec=54.625000° (offset ~0.003°)
- **Source 3:** RA=124.523000°, Dec=54.616000° (offset ~0.005°)
- **Target SNR:** 5.0
- **Max bin width:** 4
- **Max SPWs:** 8 (per source)
- **Parallel workers:** 4 (per source)
- **Backend:** tclean

## Results Summary

### Performance

- **Total runtime:** ~20 minutes (1200 seconds)
- **All 3 sources completed successfully**
- **Each source:** 8/8 SPWs imaged

### Detections

- **Source 1:** 6 detections, Success: True
- **Source 2:** 1 detection, Success: True
- **Source 3:** 6 detections, Success: True

## Critical Issue: CASA Table Lock Conflicts

### Problem

When multiple adaptive binning processes run in parallel on the same MS, CASA's
table locking mechanism causes **resource deadlock errors**:

```
Error (Resource deadlock avoided) when acquiring lock on
/stage/.../ms/.../table.lock
```

### Root Cause

- CASA `tclean` requires **write access** to the MS (to write MODEL_DATA column)
- Multiple processes trying to access the same MS simultaneously conflict on the
  table lock
- CASA's locking mechanism doesn't support concurrent write access

### Impact

- Many SPW imaging attempts failed initially due to lock contention
- Processes eventually completed by retrying, but inefficient
- Warning messages: "Failed to clear MODEL_DATA before ft()"
- Some SPWs may have been skipped: "Expected 16 images but got 8"

### Solutions

#### Option 1: Serialize MS Access (Recommended)

Process multiple sources sequentially, or implement a lock mechanism to
serialize access:

```python
# Use a file lock to serialize MS access
import fcntl
with open(lock_file, 'w') as lock:
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
    # Process MS
```

#### Option 2: Copy MS for Each Process

Create a copy of the MS for each parallel process (expensive but avoids
conflicts).

#### Option 3: Use WSClean Backend

WSClean reads the MS but doesn't write MODEL_DATA, potentially avoiding some
locking issues. However, WSClean doesn't support SPW selection directly.

#### Option 4: Accept Sequential Processing

For multiple sources on the same MS, process them sequentially rather than in
parallel.

## Recommendations

1. **For production use:** Implement MS access serialization when processing
   multiple sources on the same MS.

2. **For testing:** Process sources sequentially or use separate MS files for
   parallel testing.

3. **Consider:** Adding a `--serialize-ms-access` flag to the adaptive binning
   CLI to automatically serialize access when multiple processes might conflict.

## Next Steps

1. Implement MS access serialization mechanism
2. Test with serialized access to verify no deadlocks
3. Consider pipeline integration with proper locking

## Files Generated

- **Source 1 images:**
  `/tmp/adaptive_binning_multiple_sources/source1/spw_images/*.pbcor.fits`
- **Source 2 images:**
  `/tmp/adaptive_binning_multiple_sources/source2/spw_images/*.pbcor.fits`
- **Source 3 images:**
  `/tmp/adaptive_binning_multiple_sources/source3/spw_images/*.pbcor.fits`
- **Log files:** `/tmp/adaptive_binning_multiple_sources.log.source{1,2,3}`
