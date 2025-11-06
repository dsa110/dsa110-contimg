# Additional Pipeline Optimization Opportunities

**Date:** 2025-01-27  
**Status:** Review & Recommendations

## Executive Summary

After a comprehensive review of the pipeline codebase, several additional optimization opportunities have been identified beyond the high-priority items already implemented. These span memory efficiency, I/O optimization, caching, and computational efficiency.

---

## 1. Batch Subband Loading (HIGH PRIORITY)

**Location:** `conversion/strategies/hdf5_orchestrator.py::_load_and_merge_subbands()`

**Current Pattern:**
```python
acc = []
for i, path in file_iter:
    tmp = UVData()
    tmp.read(path, ...)  # Loads entire subband into memory
    acc.append(tmp)
uv = acc[0]
uv.fast_concat(acc[1:], axis="freq", inplace=True)
```

**Problem:**
- All 16 subbands loaded into memory simultaneously
- Peak memory = 16 × subband_size
- For 5-minute observations: ~16 × 200MB = 3.2GB peak memory
- Merging happens only after all subbands are loaded

**Solution:**
```python
def _load_and_merge_subbands_batched(
    file_list: Sequence[str], 
    batch_size: int = 4,
    show_progress: bool = True
) -> UVData:
    """Load and merge subbands in batches to reduce peak memory."""
    sorted_file_list = sorted(file_list, key=sort_by_subband, reverse=True)
    
    merged = None
    batch_num = 0
    total_batches = (len(sorted_file_list) + batch_size - 1) // batch_size
    
    for i in range(0, len(sorted_file_list), batch_size):
        batch_num += 1
        batch = sorted_file_list[i:i+batch_size]
        logger.info(f"Loading batch {batch_num}/{total_batches} ({len(batch)} subbands)...")
        
        # Load batch
        batch_data = []
        for path in batch:
            tmp = UVData()
            tmp.read(path, ...)
            batch_data.append(tmp)
        
        # Merge batch
        batch_merged = batch_data[0]
        if len(batch_data) > 1:
            batch_merged.fast_concat(batch_data[1:], axis="freq", inplace=True, run_check=False)
        
        # Merge with accumulated result
        if merged is None:
            merged = batch_merged
        else:
            merged.fast_concat([batch_merged], axis="freq", inplace=True, run_check=False)
        
        # Explicit cleanup
        del batch_data, batch_merged
        import gc
        gc.collect()
    
    return merged
```

**Estimated Impact:**
- **Memory reduction:** 40-60% (from 3.2GB → 1.3-1.9GB for 16 subbands)
- **Speed:** Minimal overhead (1-2% slower due to multiple merges)
- **Benefit:** Enables processing on systems with limited RAM

**Implementation Priority:** HIGH (large memory impact, low risk)

---

## 2. Cache MS Metadata Reads (MEDIUM PRIORITY)

**Location:** Multiple files with 197+ `getcol()` calls across 34 files

**Current Pattern:**
```python
# Repeated in multiple places
with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw:
    cf = spw.getcol('CHAN_FREQ')
with table(f"{ms_path}::FIELD", readonly=True) as fld:
    ph = fld.getcol('PHASE_DIR')
```

**Problem:**
- MS metadata read multiple times per workflow
- Each `getcol()` call opens/closes table (small overhead)
- No caching of frequently accessed metadata

**Solution:**
```python
# utils/ms_helpers.py
from functools import lru_cache
from typing import Dict, Tuple

@lru_cache(maxsize=128)
def get_ms_metadata_cached(ms_path: str) -> Dict[str, Any]:
    """Get and cache MS metadata (SPW, FIELD, ANTENNA)."""
    metadata = {}
    
    with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw:
        metadata['chan_freq'] = spw.getcol('CHAN_FREQ')
        metadata['nspw'] = spw.nrows()
    
    with table(f"{ms_path}::FIELD", readonly=True) as fld:
        metadata['phase_dir'] = fld.getcol('PHASE_DIR')
        metadata['field_names'] = fld.getcol('NAME')
    
    with table(f"{ms_path}::ANTENNA", readonly=True) as ant:
        metadata['antenna_names'] = ant.getcol('NAME')
        metadata['nantennas'] = ant.nrows()
    
    return metadata

def clear_ms_metadata_cache():
    """Clear MS metadata cache (call after MS modifications)."""
    get_ms_metadata_cached.cache_clear()
```

**Usage:**
```python
# Instead of multiple getcol() calls:
metadata = get_ms_metadata_cached(ms_path)
chan_freq = metadata['chan_freq']
phase_dir = metadata['phase_dir']
```

**Estimated Impact:**
- **Speed:** 10-20% faster for operations that read MS metadata multiple times
- **Memory:** Minimal (cache size limited by LRU)
- **Benefit:** Eliminates redundant table opens

**Implementation Priority:** MEDIUM (moderate speedup, low risk)

---

## 3. Batch Database Queries in Mosaic Validation (MEDIUM PRIORITY)

**Location:** `mosaic/validation.py` (already partially implemented)

**Current Status:**
- `validate_tiles_consistency()` already uses batch queries ✓
- `validate_tile_quality()` still queries per tile

**Opportunity:**
```python
def validate_tiles_quality_batched(
    tiles: List[str],
    products_db: Optional[Path] = None,
    **kwargs
) -> Dict[str, TileQualityMetrics]:
    """Validate multiple tiles with batched database queries."""
    # Batch query for all tiles
    db_data = {}
    if products_db:
        with sqlite3.connect(str(products_db)) as conn:
            conn.row_factory = sqlite3.Row
            placeholders = ','.join(['?'] * len(tiles))
            rows = conn.execute(
                f"""SELECT path, ms_path, noise_jy, dynamic_range, 
                    pbcor_applied, calibration_applied 
                    FROM images WHERE path IN ({placeholders})""",
                tiles
            ).fetchall()
            db_data = {row['path']: row for row in rows}
    
    # Validate each tile (reuse DB data)
    metrics_dict = {}
    for tile in tiles:
        tile_data = db_data.get(tile, {})
        metrics = validate_tile_quality(tile, products_db, **kwargs)
        # Merge with DB data
        if tile_data:
            metrics.ms_path = tile_data.get('ms_path')
            metrics.calibration_applied = bool(tile_data.get('calibration_applied'))
        metrics_dict[tile] = metrics
    
    return metrics_dict
```

**Estimated Impact:**
- **Speed:** 30-50% faster for large tile sets (100+ tiles)
- **Database load:** Reduced from N queries to 1 query per operation
- **Benefit:** Significant for mosaic operations

**Implementation Priority:** MEDIUM (good speedup, already partially done)

---

## 4. Optimize MODEL_DATA Calculation (HIGH PRIORITY)

**Location:** `calibration/model.py::_calculate_manual_model_data()`

**Current Pattern:**
- Manual MODEL_DATA calculation already optimized (uses vectorized operations)
- But: No caching of phase/frequency calculations for multiple calibrations

**Opportunity:**
- Cache phase center calculations for repeated calibrations
- Pre-compute frequency-dependent terms

**Estimated Impact:**
- **Speed:** 5-10% faster for repeated calibrations on same MS
- **Benefit:** Minimal but cumulative over many calibrations

**Implementation Priority:** LOW (already well optimized)

---

## 5. Parallel Independent Operations (MEDIUM PRIORITY)

**Location:** Multiple pipeline scripts

**Current Pattern:**
```python
# Sequential execution
for ms_path in ms_paths:
    calibrate(ms_path)
    apply_calibration(ms_path)
    image(ms_path)
```

**Opportunity:**
```python
# Parallel independent operations
from concurrent.futures import ProcessPoolExecutor

def process_ms_pipeline(ms_path: str) -> dict:
    """Process single MS through pipeline."""
    calibrate(ms_path)
    apply_calibration(ms_path)
    image(ms_path)
    return {'ms_path': ms_path, 'status': 'done'}

# Parallel execution (if independent)
with ProcessPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(process_ms_pipeline, ms_paths))
```

**Challenges:**
- CASA tools may not be thread-safe (need testing)
- Memory usage increases with parallelism
- Need careful error handling

**Estimated Impact:**
- **Speed:** 2-4x faster for independent MS processing (depends on cores)
- **Benefit:** Significant for batch operations

**Implementation Priority:** MEDIUM (high impact but requires testing)

---

## 6. Reduce Redundant Flag Validation (LOW PRIORITY)

**Location:** `calibration/cli_calibrate.py`, `calibration/cli_flag.py`

**Current Pattern:**
- Flag statistics computed multiple times (after flagging, before calibration)
- Uses sampling (already optimized), but could cache results

**Opportunity:**
- Cache flag statistics between operations
- Skip redundant validation if flags haven't changed

**Estimated Impact:**
- **Speed:** 5-10% faster for calibration workflows
- **Benefit:** Minimal but cumulative

**Implementation Priority:** LOW (small impact, already optimized)

---

## 7. Optimize CASA Table Iteration (LOW PRIORITY)

**Location:** Multiple files using `table()` context manager

**Current Pattern:**
```python
with table(ms_path, readonly=True) as tb:
    for i in range(tb.nrows()):
        row = tb.getrow(i)  # Individual row reads
```

**Optimization:**
```python
# Use getcol() with row ranges instead of getrow() in loops
with table(ms_path, readonly=True) as tb:
    nrows = tb.nrows()
    chunk_size = 10000
    for start in range(0, nrows, chunk_size):
        end = min(start + chunk_size, nrows)
        data = tb.getcol('DATA', startrow=start, nrow=end-start)  # Batch read
```

**Estimated Impact:**
- **Speed:** 20-30% faster for row-by-row processing
- **Benefit:** Better for large MS files

**Implementation Priority:** LOW (already using getcol() in most places)

---

## 8. Cache Image Headers in Mosaicking (HIGH PRIORITY - Already Identified)

**Location:** `mosaic/validation.py`, `mosaic/cli.py`

**Status:** Already documented in `OPTIMIZATION_STRATEGIES.md`

**Recommendation:** Implement header caching for tile validation operations

**Estimated Impact:**
- **Speed:** 2-3x faster validation for large tile sets
- **Benefit:** Significant for mosaic operations

**Implementation Priority:** HIGH (already documented, needs implementation)

---

## Summary of Recommendations

### High Priority:
1. **Batch Subband Loading** - HIGH** (40-60% memory reduction)
2. **Image Header Caching** - HIGH** (2-3x speedup for mosaicking)

### Medium Priority:
3. **Cache MS Metadata** - MEDIUM** (10-20% speedup)
4. **Batch Database Queries** - MEDIUM** (30-50% speedup, partially done)
5. **Parallel Independent Operations** - MEDIUM** (2-4x speedup, requires testing)

### Low Priority:
6. **Reduce Redundant Flag Validation** - LOW** (5-10% speedup)
7. **Optimize CASA Table Iteration** - LOW** (20-30% speedup, mostly done)
8. **Optimize MODEL_DATA Calculation** - LOW** (5-10% speedup, already good)

---

## Implementation Order

1. **Batch Subband Loading** (highest impact, low risk)
2. **Image Header Caching** (high impact, already documented)
3. **Cache MS Metadata** (moderate impact, low risk)
4. **Batch Database Queries** (moderate impact, partially done)
5. **Parallel Operations** (high impact, requires testing)

---

## Notes

- Most I/O optimizations already implemented (sampling, progress bars)
- Memory optimizations have highest impact for large datasets
- Caching strategies provide cumulative benefits
- Parallel operations require careful testing due to CASA tool constraints

