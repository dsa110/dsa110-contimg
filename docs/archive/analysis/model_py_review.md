# Model.py Code Review

**Date:** 2025-11-06  
**Reviewer:** AI Assistant  
**Scope:** `src/dsa110_contimg/calibration/model.py`

## Executive Summary

This review covers four key areas:
1. `_calculate_manual_model_data` optimizations
2. Metadata caching implementation
3. Phase center handling verification
4. Error handling and logging

**Overall Assessment:** The code is well-structured with correct phase center handling, but has significant optimization opportunities in the row-by-row loop.

---

## 1. `_calculate_manual_model_data` Optimizations

### Current Implementation

**Performance Characteristics:**
- Row-by-row loop: 1,787,904 iterations (from calibration log)
- Operations per row: ~192 complex multiplications (48 channels × 4 pols)
- Total operations: ~343 million complex operations
- Memory: Creates full `model_data` array upfront (2.75 GB for typical MS)

**Code Structure:**
```python
# Line 155-195: Row-by-row loop
for row_idx in range(nrows):
    if not field_mask[row_idx]:
        continue
    # ... per-row calculations ...
    model_data[row_idx, :, :] = model_complex[:, np.newaxis]
```

### Optimization Opportunities

#### **Critical: Vectorize the Row Loop**

**Current Issue:** The row-by-row loop processes 1.7M rows sequentially, which is extremely slow.

**Recommended Solution:** Vectorize using NumPy broadcasting:

```python
# Vectorized approach (pseudo-code)
# 1. Pre-calculate phase centers for all rows
row_field_indices = field_id[field_mask]  # (nselected_rows,)
row_phase_centers_ra = phase_dir[row_field_indices, 0, 0]  # (nselected_rows,)
row_phase_centers_dec = phase_dir[row_field_indices, 0, 1]  # (nselected_rows,)

# 2. Calculate offsets for all rows at once
offset_ra_rad = (ra_deg - np.degrees(row_phase_centers_ra)) * np.pi / 180.0 * np.cos(row_phase_centers_dec)
offset_dec_rad = (dec_deg - np.degrees(row_phase_centers_dec)) * np.pi / 180.0

# 3. Get frequencies for all rows
row_spw_indices = spw_id[field_mask]  # (nselected_rows,)
row_freqs = chan_freq[row_spw_indices]  # (nselected_rows, nchan)

# 4. Vectorize phase calculation
u_selected = u[field_mask]  # (nselected_rows,)
v_selected = v[field_mask]  # (nselected_rows,)
wavelengths = 3e8 / row_freqs  # (nselected_rows, nchan)

# Broadcasting: (nselected_rows, 1) * (nselected_rows, nchan) -> (nselected_rows, nchan)
phase = 2 * np.pi * (u_selected[:, np.newaxis] * offset_ra_rad[:, np.newaxis] + 
                      v_selected[:, np.newaxis] * offset_dec_rad[:, np.newaxis]) / wavelengths

# 5. Vectorize complex model creation
model_complex = flux_jy * (np.cos(phase) + 1j * np.sin(phase))  # (nselected_rows, nchan)
model_data[field_mask, :, :] = model_complex[:, :, np.newaxis]  # Broadcast to pols
```

**Expected Performance Gain:** 10-100x speedup (from minutes to seconds)

**Memory Trade-off:** 
- Current: 2.75 GB (full array)
- Vectorized: ~3-4 GB (temporary arrays during calculation)
- Acceptable for modern systems

#### **Medium Priority: Chunked Processing for Large MS**

For extremely large MS files (>10M rows), consider chunked processing:

```python
chunk_size = 100000  # Process 100k rows at a time
for chunk_start in range(0, nrows, chunk_size):
    chunk_end = min(chunk_start + chunk_size, nrows)
    chunk_mask = field_mask[chunk_start:chunk_end]
    # ... vectorized calculation for chunk ...
```

#### **Low Priority: Pre-compute Constants**

```python
# Pre-compute constants outside loop
flux_complex = float(flux_jy)
two_pi = 2 * np.pi
c = 3e8
```

### Recommendations

1. **High Priority:** Implement vectorized row processing (10-100x speedup)
2. **Medium Priority:** Add chunked processing for memory-constrained systems
3. **Low Priority:** Pre-compute mathematical constants

---

## 2. Metadata Caching Implementation

### Current Implementation

**Cache Strategy:**
- Uses `@lru_cache(maxsize=64)` on `get_ms_metadata_cached()`
- Cache key includes `(ms_path, mtime)` for automatic invalidation
- Cache stores: `chan_freq`, `phase_dir`, `field_names`, `antenna_names`

**Usage in `_calculate_manual_model_data`:**
```python
# Lines 83-107: Cache check
if get_ms_metadata is not None:
    try:
        metadata = get_ms_metadata(ms_path)
        phase_dir = metadata.get('phase_dir')
        chan_freq = metadata.get('chan_freq')
        # ... validation ...
        use_cached_metadata = True
    except Exception:
        use_cached_metadata = False
```

### Issues Found

#### **Issue 1: Silent Fallback on Cache Failure**

**Problem:** If cache lookup fails, code silently falls back to direct table read without logging.

**Impact:** 
- Cache failures go unnoticed
- Performance degradation not tracked
- Debugging difficult

**Recommendation:**
```python
except Exception as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Metadata cache lookup failed for {ms_path}: {e}. Falling back to direct read.")
    use_cached_metadata = False
```

#### **Issue 2: Cache Validation Logic is Redundant**

**Problem:** Lines 95-104 check if cached metadata is valid, but this duplicates validation that should happen in `get_ms_metadata()`.

**Current Code:**
```python
if phase_dir is not None and chan_freq is not None:
    nfields = len(phase_dir)
    nspw = len(chan_freq)
    if nfields > 0 and nspw > 0:
        use_cached_metadata = True
    else:
        raise ValueError("Cached metadata incomplete")
```

**Recommendation:** Move validation into `get_ms_metadata()` and trust the cache result.

#### **Issue 3: No Cache Statistics Monitoring**

**Problem:** No way to monitor cache effectiveness in production.

**Recommendation:** Add optional cache statistics logging:

```python
if get_ms_metadata is not None:
    try:
        from dsa110_contimg.utils.ms_helpers import get_cache_stats
        cache_stats = get_cache_stats()
        if cache_stats['ms_metadata']['hit_rate'] < 0.5:
            logger.warning(f"Low metadata cache hit rate: {cache_stats['ms_metadata']['hit_rate']:.2%}")
    except Exception:
        pass  # Non-critical
```

### Recommendations

1. **High Priority:** Add logging for cache failures
2. **Medium Priority:** Simplify cache validation (move to `get_ms_metadata()`)
3. **Low Priority:** Add cache statistics monitoring

---

## 3. Phase Center Handling Verification

### Verification Results

#### **✓ Correct: `_calculate_manual_model_data`**

**Implementation:** Lines 165-173
```python
# Uses each field's PHASE_DIR
phase_center_ra_rad = phase_dir[row_field_idx][0][0]
phase_center_dec_rad = phase_dir[row_field_idx][0][1]
# Calculates offset from THIS field's phase center
offset_ra_rad = (ra_deg - phase_center_ra_deg) * np.pi / 180.0 * np.cos(phase_center_dec_rad)
```

**Status:** ✓ **CORRECT** - Uses per-field phase centers correctly

**Fallback:** Lines 114-118 correctly fall back to `REFERENCE_DIR` if `PHASE_DIR` unavailable

#### **✓ Correct: `write_point_model_with_ft(use_manual=True)`**

**Implementation:** Line 240
```python
if use_manual:
    _calculate_manual_model_data(ms_path, ra_deg, dec_deg, flux_jy, field=field)
    return
```

**Status:** ✓ **CORRECT** - Delegates to manual calculation

#### **⚠ Warning: `write_point_model_with_ft(use_manual=False)`**

**Implementation:** Lines 308-312
```python
# NOTE: ft() reads phase center from FIELD parameters, but uses ONE phase center for ALL fields.
# If fields have different phase centers (e.g., each field phased to its own meridian),
# ft() will use the phase center from one field (typically field 0) for all fields,
# causing phase errors for fields with different phase centers.
```

**Status:** ⚠ **DOCUMENTED LIMITATION** - Correctly documented, but still risky

**Recommendation:** Consider adding runtime validation:

```python
if not use_manual:
    # Validate that all fields share the same phase center
    with casa_table(f"{ms_path}::FIELD", readonly=True) as field_tb:
        if "PHASE_DIR" in field_tb.colnames():
            phase_dirs = field_tb.getcol("PHASE_DIR")
            if len(np.unique(phase_dirs, axis=0)) > 1:
                warnings.warn(
                    "Multiple phase centers detected. ft() will use incorrect phase center. "
                    "Use use_manual=True for correct per-field phase centers.",
                    UserWarning
                )
```

#### **⚠ Deprecated: `write_component_model_with_ft` and `write_image_model_with_ft`**

**Status:** ⚠ **DEPRECATED** - Correctly marked with warnings, but no manual alternative available

**Recommendation:** Consider implementing manual alternatives for component lists and images in future work.

#### **⚠ Deprecated: `write_setjy_model`**

**Status:** ⚠ **DEPRECATED** - Correctly marked, only used as fallback

### Summary

| Function | Phase Center Handling | Status |
|----------|----------------------|--------|
| `_calculate_manual_model_data` | ✓ Per-field PHASE_DIR | **CORRECT** |
| `write_point_model_with_ft(use_manual=True)` | ✓ Delegates to manual | **CORRECT** |
| `write_point_model_with_ft(use_manual=False)` | ⚠ Single phase center | **DOCUMENTED** |
| `write_component_model_with_ft` | ⚠ Uses ft() | **DEPRECATED** |
| `write_image_model_with_ft` | ⚠ Uses ft() | **DEPRECATED** |
| `write_setjy_model` | ⚠ Uses setjy()/ft() | **DEPRECATED** |

**Overall:** Phase center handling is **CORRECT** for the primary code path (`use_manual=True`).

---

## 4. Error Handling and Logging

### Current State

#### **Error Handling Patterns**

1. **Silent Failures (Lines 21, 30):**
```python
def _ensure_imaging_columns(ms_path: str) -> None:
    try:
        addImagingColumns(ms_path)
    except Exception:
        pass  # Silent failure
```

**Issue:** No logging, failures go unnoticed

**Recommendation:**
```python
def _ensure_imaging_columns(ms_path: str) -> None:
    try:
        addImagingColumns(ms_path)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Could not add imaging columns to {ms_path}: {e}")
        # Non-fatal, continue
```

2. **Warnings for Deprecated Functions (Lines 344, 380, 491):**
```python
warnings.warn(
    "write_component_model_with_ft() uses ft() which has known phase center bugs...",
    DeprecationWarning,
    stacklevel=2
)
```

**Status:** ✓ **GOOD** - Proper deprecation warnings

3. **Non-Fatal Warnings (Lines 298-305):**
```python
except Exception as e:
    warnings.warn(
        f"Failed to explicitly clear MODEL_DATA before ft(): {e}. "
        "Continuing with ft() call, but MODEL_DATA may not be properly cleared.",
        RuntimeWarning
    )
```

**Status:** ✓ **GOOD** - Appropriate warning level

4. **Error Logging (Line 458):**
```python
except Exception as e:
    LOG.error(f"Failed to export model image: {e}")
```

**Status:** ✓ **GOOD** - Proper error logging

#### **Logging Coverage**

**Current Logging:**
- ✓ `export_model_as_fits`: Has INFO and ERROR logging
- ✗ `_calculate_manual_model_data`: No logging
- ✗ `write_point_model_with_ft`: No logging
- ✗ `_ensure_imaging_columns`: No logging
- ✗ `_initialize_corrected_from_data`: No logging

**Missing Logging:**
- No progress logging for long-running operations
- No performance metrics (timing)
- No validation logging (field selection, metadata validation)

### Recommendations

#### **High Priority: Add Logging to Critical Functions**

```python
import logging
logger = logging.getLogger(__name__)

def _calculate_manual_model_data(...):
    logger.info(f"Calculating MODEL_DATA for {ms_path} (field={field}, flux={flux_jy} Jy)")
    start_time = time.time()
    
    # ... calculation ...
    
    elapsed = time.time() - start_time
    logger.info(f"MODEL_DATA calculation completed in {elapsed:.2f}s ({nrows:,} rows)")
```

#### **Medium Priority: Add Validation Logging**

```python
# Log field selection
if field_indices is not None:
    logger.debug(f"Field selection: {field_indices} ({len(field_indices)} fields)")
else:
    logger.debug("No field selection: processing all fields")

# Log metadata source
if use_cached_metadata:
    logger.debug("Using cached MS metadata")
else:
    logger.debug("Reading MS metadata directly from tables")
```

#### **Low Priority: Add Performance Metrics**

```python
# Log performance metrics
logger.debug(f"Processing {nrows:,} rows, {nchan} channels, {npol} pols")
logger.debug(f"Memory usage: {model_data.nbytes / 1e9:.2f} GB")
```

### Summary

| Function | Error Handling | Logging | Status |
|----------|---------------|---------|--------|
| `_ensure_imaging_columns` | Silent failure | None | ⚠ Needs logging |
| `_initialize_corrected_from_data` | Silent failure | None | ⚠ Needs logging |
| `_calculate_manual_model_data` | Try/except | None | ⚠ Needs logging |
| `write_point_model_with_ft` | Warnings | None | ⚠ Needs logging |
| `export_model_as_fits` | Error logging | INFO/ERROR | ✓ Good |
| Deprecated functions | Deprecation warnings | None | ✓ Good |

---

## Summary of Recommendations

### High Priority (Performance & Reliability)

1. **Vectorize `_calculate_manual_model_data` row loop** (10-100x speedup)
2. **Add logging to critical functions** (debugging, monitoring)
3. **Add cache failure logging** (track cache effectiveness)

### Medium Priority (Code Quality)

4. **Simplify cache validation** (move to `get_ms_metadata()`)
5. **Add runtime validation for `use_manual=False`** (prevent phase errors)
6. **Add progress/performance logging** (monitoring)

### Low Priority (Nice to Have)

7. **Pre-compute mathematical constants** (minor optimization)
8. **Add chunked processing option** (memory-constrained systems)
9. **Add cache statistics monitoring** (monitoring)

---

## Implementation Priority

**Phase 1 (Immediate):**
- Vectorize row loop in `_calculate_manual_model_data`
- Add basic logging to critical functions

**Phase 2 (Short-term):**
- Improve error handling and logging
- Add cache monitoring

**Phase 3 (Long-term):**
- Consider manual alternatives for component lists/images
- Add comprehensive performance metrics

---

## Testing Recommendations

1. **Performance Testing:** Benchmark vectorized vs. row-by-row implementation
2. **Cache Testing:** Verify cache invalidation on MS modification
3. **Phase Center Testing:** Validate per-field phase center handling with test MS
4. **Error Handling Testing:** Test all error paths and verify logging

---

**End of Review**

