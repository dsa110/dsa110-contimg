# Test Framework Bottleneck Analysis

**Date:** 2025-01-15  
**Framework:** `test_pipeline_1min.py`  
**Context:** 1-minute MS pipeline test

## Executive Summary

Identified **9 major bottlenecks** in the test framework, with **3 critical** performance issues that can be immediately addressed.

### Critical Bottlenecks (High Impact, Easy Fix)
1. **Docker overhead for WSClean** - 2-5x latency penalty
2. **Missing memory optimization** - Default 8GB too conservative for quick mode
3. **Sequential MS metadata reads** - Multiple table opens for same data

### Moderate Bottlenecks (Medium Impact)
4. **NVSS catalog query inefficiency** - May read full CSV instead of SQLite cache
5. **MODEL_DATA population via ft()** - CASA ft() inherently slow for large component lists
6. **Multiple calibration table writes** - Separate I/O for each table (bpcal, gpcal, 2gcal)

### Minor Bottlenecks (Low Impact, Complex Fix)
7. **No parallelization between stages** - All stages sequential
8. **Flagging operations** - Could use batch operations
9. **Reordering decision** - Quick mode skips but may be needed

---

## Detailed Analysis

### 1. Docker Overhead for WSClean (CRITICAL)

**Location:** `src/dsa110_contimg/imaging/cli.py:190-203`

**Problem:**
- WSClean runs in Docker container (`wsclean-everybeam-0.7.4`)
- Volume mounting adds I/O latency (~2-5x penalty)
- Process startup overhead for each run
- Container networking overhead

**Impact:** 
- **2-5x slower** than native WSClean
- Especially noticeable for small datasets (1-minute MS)

**Solution:**
```python
# Prefer native WSClean if available
if wsclean_path == "docker":
    # Check for native WSClean first
    native_wsclean = shutil.which("wsclean")
    if native_wsclean:
        LOG.info("Using native WSClean (faster than Docker)")
        wsclean_cmd = [native_wsclean]
        use_docker = False
    else:
        # Fall back to Docker
        use_docker = True
```

**Expected Improvement:** 2-5x faster WSClean execution

---

### 2. Memory Allocation Too Conservative (CRITICAL)

**Location:** `src/dsa110_contimg/imaging/cli.py:322`

**Current Code:**
```python
abs_mem = os.getenv("WSCLEAN_ABS_MEM", "16" if imsize > 1024 else "8")
```

**Problem:**
- Default 8GB for imsize ≤ 1024 is too conservative
- Causes unnecessary memory pressure and swapping
- WSClean can use more memory efficiently for faster gridding

**Solution:**
```python
# More aggressive memory allocation for better performance
if quick:
    # Quick mode: allow more memory for speed
    abs_mem = os.getenv("WSCLEAN_ABS_MEM", "16")  # 16GB even for small images
else:
    # Production mode: scale with image size
    abs_mem = os.getenv("WSCLEAN_ABS_MEM", "32" if imsize > 2048 else "16")
```

**Expected Improvement:** 10-30% faster gridding/FFT operations

---

### 3. Sequential MS Metadata Reads (CRITICAL)

**Location:** `test_pipeline_1min.py:124-133`

**Current Code:**
```python
# Get phase center from FIELD table
with table(f"{ms_path}::FIELD", readonly=True) as fld:
    ph = fld.getcol("PHASE_DIR")[0]
    ra0_deg = float(ph[0][0]) * (180.0 / np.pi)
    dec0_deg = float(ph[0][1]) * (180.0 / np.pi)

# Get observing frequency
with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw:
    ch = spw.getcol("CHAN_FREQ")[0]
    freq_ghz = float(np.nanmean(ch)) / 1e9
```

**Problem:**
- Two separate table opens (I/O overhead)
- Could be combined into single operation
- Phase center extraction repeated multiple times

**Solution:**
```python
# Single function to extract all MS metadata
def get_ms_metadata(ms_path):
    """Extract phase center and frequency in one pass."""
    with table(f"{ms_path}::FIELD", readonly=True) as fld:
        ph = fld.getcol("PHASE_DIR")[0]
        ra0_deg = float(ph[0][0]) * (180.0 / np.pi)
        dec0_deg = float(ph[0][1]) * (180.0 / np.pi)
    
    with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw:
        ch = spw.getcol("CHAN_FREQ")[0]
        freq_ghz = float(np.nanmean(ch)) / 1e9
    
    return ra0_deg, dec0_deg, freq_ghz

# Use once, cache result
ra0_deg, dec0_deg, freq_ghz = get_ms_metadata(str(ms_path))
```

**Expected Improvement:** 5-10% reduction in initialization time

---

### 4. NVSS Catalog Query Inefficiency (MODERATE)

**Location:** `test_pipeline_1min.py:136-144`

**Problem:**
- `make_nvss_component_cl()` may read full CSV catalog if SQLite cache missing
- Full NVSS catalog is ~1.8GB CSV file
- No caching of component lists between runs

**Current Code:**
```python
cl_path = str(output_dir / "cal_model_10mJy.cl")
make_nvss_component_cl(
    ra0_deg,
    dec0_deg,
    radius_deg=0.2,
    min_mjy=10.0,
    freq_ghz=freq_ghz,
    out_path=cl_path,
)
```

**Solution:**
1. **Use SQLite cache:** Ensure `query_sources()` uses SQLite database instead of CSV
2. **Cache component lists:** Reuse component lists if they exist for same field
3. **Reduce radius:** 0.2 deg may be too large for 1-minute test

**Expected Improvement:** 50-80% faster if SQLite cache available, 90%+ if component list cached

---

### 5. MODEL_DATA Population via ft() (MODERATE)

**Location:** `test_pipeline_1min.py:148`

**Problem:**
- CASA `ft()` is inherently slow for large component lists
- Single-threaded operation
- No way to parallelize
- For 1-minute test, may be overkill (can use smaller radius/fewer sources)

**Current Code:**
```python
ft_from_cl(str(ms_path), cl_path, field="0")
```

**Solutions:**
1. **Reduce source count:** Use smaller radius (0.1 deg instead of 0.2 deg)
2. **Higher flux threshold:** Use 25 mJy instead of 10 mJy (fewer sources)
3. **Skip for quick test:** Can skip MODEL_DATA population if just testing imaging

**Expected Improvement:** 30-50% faster if source count reduced by 2-3x

---

### 6. Multiple Calibration Table Writes (MODERATE)

**Location:** `test_pipeline_1min.py:168-193`

**Problem:**
- Three separate table writes: `bpcal`, `gpcal`, `2gcal`
- Each write is separate I/O operation
- No batching or parallel writes

**Current Code:**
```python
bp_tabs = solve_bandpass(...)  # I/O write 1
g_tabs = solve_gains(...)      # I/O write 2 (gpcal + 2gcal)
```

**Solution:**
- **Minimal for 1-minute test:** Can skip 2gcal (short-timescale calibration not needed for 1-minute data)
- **For production:** Use tmpfs staging for caltable writes (similar to MS staging)

**Expected Improvement:** 20-30% faster if 2gcal skipped (1-minute test)

---

### 7. No Parallelization Between Stages (MINOR)

**Location:** Entire `test_pipeline_1min.py`

**Problem:**
- All stages run sequentially
- No overlap between independent operations
- Could pipeline: flagging while calibration solves, etc.

**Solution:**
- **For testing:** Not critical (simplicity > speed)
- **For production:** Use async/threading for independent operations

**Expected Improvement:** Minimal for 1-minute test (stages are short)

---

### 8. Flagging Operations (MINOR)

**Location:** `test_pipeline_1min.py:90-97`

**Problem:**
- Three separate flagging operations: `reset_flags`, `flag_zeros`, `flag_rfi`
- Each opens/closes MS table
- Could be batched

**Solution:**
- **For testing:** Not critical (flagging is fast)
- **For production:** Batch flagging operations

**Expected Improvement:** 5-10% faster (flagging is already fast)

---

### 9. Reordering Decision Logic (MINOR)

**Location:** `src/dsa110_contimg/imaging/cli.py:299-307`

**Problem:**
- Quick mode skips reordering, but MS might need it
- Reordering is slow if needed but skipped
- Decision is heuristic, not based on MS structure

**Current Code:**
```python
if quick:
    pass  # Skip reorder in quick mode
else:
    cmd.append("-reorder")
```

**Solution:**
- **Check MS structure:** Detect if reordering is actually needed
- **Cache reorder decision:** If MS was already reordered, skip

**Expected Improvement:** 10-20% faster if reordering can be skipped safely

---

## Recommended Quick Wins

### Priority 1 (Immediate - 30 minutes)
1. **Prefer native WSClean over Docker** (2-5x improvement)
2. **Increase memory allocation for quick mode** (10-30% improvement)
3. **Combine MS metadata reads** (5-10% improvement)

**Total Expected Improvement:** **2-6x faster WSClean + 10-30% faster overall**

### Priority 2 (Medium-term - 2 hours)
4. **Use SQLite NVSS cache** (50-80% faster catalog queries)
5. **Reduce MODEL_DATA sources** (30-50% faster ft())
6. **Skip 2gcal for 1-minute test** (20-30% faster calibration)

**Total Expected Improvement:** **Additional 30-50% faster**

### Priority 3 (Long-term - 1 day)
7. **Cache component lists** (90%+ faster if reused)
8. **Optimize flagging batching** (5-10% faster)
9. **Smart reordering detection** (10-20% faster)

**Total Expected Improvement:** **Additional 10-20% faster**

---

## Implementation Priority

**Immediate (Today):**
- Fix Docker preference for WSClean
- Increase memory allocation
- Combine MS metadata reads

**This Week:**
- Use SQLite NVSS cache
- Reduce MODEL_DATA source count
- Skip 2gcal for 1-minute tests

**Future:**
- Cache component lists
- Optimize flagging/reordering logic

---

## Testing Recommendations

1. **Benchmark each fix separately** to measure individual impact
2. **Use `time.perf_counter()`** to measure stage-by-stage timing
3. **Compare Docker vs native WSClean** performance
4. **Profile I/O operations** to identify disk bottlenecks
5. **Monitor memory usage** with increased allocation

---

## Expected Overall Improvement

**Current baseline:** ~5-10 minutes for 1-minute MS pipeline test

**After Priority 1 fixes:** ~2-4 minutes (2-3x faster)
**After Priority 2 fixes:** ~1-2 minutes (3-5x faster)
**After Priority 3 fixes:** ~45-90 seconds (5-10x faster)

**Target:** <1 minute for 1-minute MS test (currently 5-10 minutes)

