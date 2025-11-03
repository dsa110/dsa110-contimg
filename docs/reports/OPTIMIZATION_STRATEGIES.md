# Mosaicking Pipeline Optimization Strategies

**Date:** 2025-11-02  
**Status:** Recommendations for Implementation

## Executive Summary

After thorough code review, several optimization opportunities have been identified that could significantly improve performance, reduce redundant operations, and improve resource efficiency.

## Optimization Opportunities

### 1. Cache Header Metadata (HIGH IMPACT, MODERATE EFFORT)

**Issue:** Tile headers are read multiple times redundantly:
- `_check_consistent_tiles()` calls `imhead()` for each tile
- `validate_tiles_consistency()` calls `imhead()` again for grid consistency  
- `validate_tiles_consistency()` calls `imhead()` again for beam consistency
- **Result:** ~3x redundant `imhead()` calls per tile

**Impact:** 
- For 100 tiles: ~300 `imhead()` calls instead of 100
- Each `imhead()` call is relatively expensive (file I/O + parsing)

**Solution:**
```python
# Cache tile headers during first read
@lru_cache(maxsize=None)
def _get_tile_header(tile_path: str) -> dict:
    """Get and cache tile header."""
    return safe_imhead(imagename=tile_path, mode='list')

# Or use a shared cache dictionary
_tile_header_cache = {}

def get_tile_header(tile_path: str) -> dict:
    if tile_path not in _tile_header_cache:
        _tile_header_cache[tile_path] = safe_imhead(imagename=tile_path, mode='list')
    return _tile_header_cache[tile_path]
```

**Estimated Speedup:** 2-3x faster validation for large tile sets

---

### 2. Cache PB Path Lookups (MODERATE IMPACT, LOW EFFORT)

**Issue:** `_find_pb_path()` is called multiple times for the same tile:
- In `validate_tile_quality()`
- In `validate_preflight_conditions()`
- In `_build_weighted_mosaic()`

**Solution:**
```python
# Cache PB path lookups
_pb_path_cache = {}

def find_pb_path_cached(tile_path: str) -> Optional[str]:
    if tile_path not in _pb_path_cache:
        _pb_path_cache[tile_path] = _find_pb_path(tile_path)
    return _pb_path_cache[tile_path]
```

**Estimated Speedup:** Eliminates redundant file system operations

---

### 3. Parallel Tile Processing (HIGH IMPACT, HIGH EFFORT)

**Issue:** All tiles are processed sequentially in loops:
- PB images read sequentially
- Tile images read sequentially  
- Regridding happens sequentially

**Solution:**
```python
from concurrent.futures import ThreadPoolExecutor
from functools import partial

def _read_pb_image(tile_pb_pair, output_path, ref_shape):
    """Read and process PB image (parallelizable)."""
    tile, pb_path = tile_pb_pair
    # ... existing logic ...
    return pb_data, pb_img

# Parallel processing
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = executor.map(
        partial(_read_pb_image, output_path=output_path, ref_shape=ref_shape),
        zip(tiles, pb_paths)
    )
    pb_results = list(futures)
```

**Challenges:**
- CASA tools may not be thread-safe
- Need to test with real data
- Memory usage increases with parallelism

**Estimated Speedup:** 2-4x for I/O-bound operations (depends on cores/disk)

---

### 4. Batch Database Queries (MODERATE IMPACT, LOW EFFORT)

**Issue:** Individual database queries per tile:
- `validate_tile_quality()` queries DB once per tile
- Could batch queries

**Solution:**
```python
# Batch query for all tiles
def validate_tiles_consistency_batched(tiles, products_db):
    with sqlite3.connect(str(products_db)) as conn:
        conn.row_factory = sqlite3.Row
        # Single query for all tiles
        placeholders = ','.join(['?'] * len(tiles))
        rows = conn.execute(
            f"SELECT path, ms_path, noise_jy, dynamic_range FROM images WHERE path IN ({placeholders})",
            tiles
        ).fetchall()
        
        # Build lookup dict
        db_data = {row['path']: row for row in rows}
    
    # Use lookup dict in validation
    for tile in tiles:
        tile_data = db_data.get(tile, {})
        # ... use tile_data ...
```

**Estimated Speedup:** Significant for large tile sets (100+ tiles)

---

### 5. Optimize Validation Order (LOW IMPACT, LOW EFFORT)

**Issue:** Expensive validations happen before basic checks:
- Astrometric check (catalog queries) happens after basic validation
- Could fail fast on basic checks

**Solution:**
```python
# Reorder validation: fail fast on basic checks
def optimized_validation_order(tiles):
    # 1. Fast: Check file existence (pre-flight already does this)
    # 2. Fast: Check grid consistency (imhead)
    # 3. Moderate: Check tile quality (read images)
    # 4. Expensive: Astrometric check (catalog queries)
    # 5. Moderate: Calibration check (DB queries)
    # 6. Moderate: PB consistency (read PB images)
    
    # If step 2 fails, skip expensive steps
    if not basic_grid_check(tiles):
        return False, ["Grid inconsistency"], {}
    
    # Continue with other checks...
```

**Estimated Speedup:** Faster failure detection (saves time on invalid inputs)

---

## Implementation Priority

### Phase 1: Quick Wins (1-2 days)
1. ✅ **Cache header metadata** - High impact, low risk
2. ✅ **Cache PB path lookups** - Low effort, immediate benefit
3. ✅ **Batch database queries** - Moderate impact, low risk

### Phase 2: Performance Improvements (3-5 days)
4. ✅ **Optimize validation order** - Low effort, better UX
5. ⚠️ **Parallel processing** - High impact, needs testing

### Phase 3: Advanced Optimizations (1-2 weeks)
6. ⚠️ **Validation result caching** - Moderate impact, needs persistence
7. ⚠️ **Streaming/chunked processing** - Enables very large mosaics

---

## Expected Overall Impact

**Current Performance:**
- 100 tiles: ~10-15 minutes (validation + build)
- Memory: ~500 MB - 1 GB

**After Phase 1 Optimizations:**
- 100 tiles: ~5-8 minutes (50% faster)
- Memory: ~500 MB - 1 GB

**After Phase 2 Optimizations:**
- 100 tiles: ~3-5 minutes (70% faster)
- Memory: ~500 MB - 1 GB

---

## Recommendations

**Immediate Actions:**
1. Implement header caching (Phase 1)
2. Implement PB path caching (Phase 1)
3. Implement batch database queries (Phase 1)

**Short-term:**
4. Test parallel processing with real data
5. Implement validation result caching

**Long-term:**
6. Consider streaming processing for very large mosaics

---

## Risk Assessment

**Low Risk:**
- Header caching
- PB path caching
- Batch database queries
- Validation order optimization

**Moderate Risk:**
- Validation result caching (cache invalidation)
- Parallel processing (thread safety, testing)

**High Risk:**
- Streaming processing (architectural changes)

## Additional Caching Strategies

See `docs/reports/ADDITIONAL_CACHING_STRATEGIES.md` for comprehensive list of additional caching opportunities including:

1. **Coordinate System (WCS) Caching** - Cache coordsys() calls
2. **Image Statistics Caching** - Cache RMS, dynamic range computations
3. **PB Statistics Caching** - Cache PB response min/max
4. **Catalog Query Caching** - Cache NVSS catalog queries
5. **Validation Results Persistence** - Persist validation results to disk
6. **Regridding Results Caching** - Cache regridded images
7. **File Metadata Caching** - Cache file mtimes, sizes
8. **Grid Consistency Caching** - Cache reference grid info

**Expected Combined Impact:** 80-90% performance improvement for repeated operations.

---

## Conclusion

The most impactful optimizations are:
1. **Caching** (headers, PB paths, validation results)
2. **Parallel processing** (if thread-safe)
3. **Batch operations** (database queries, file I/O)

These three categories would provide **50-70% performance improvement** with moderate implementation effort.

