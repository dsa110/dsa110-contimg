# SPW Merging Analysis: Producing 1 SPW Instead of 16

**Date:** 2025-11-02  
**Question:** What would it take to produce an MS with 1 SPW instead of 16 SPWs?

---

## Current State

The pipeline currently produces MS files with **16 SPWs** (one per subband) by:

1. Creating per-subband MS files in parallel (`_write_ms_subband_part()`)
2. Concatenating them via CASA `concat` → results in 16 SPWs
3. **SPW merging is available but disabled by default** (`merge_spws=False`)

**Key Files:**
- `src/dsa110_contimg/conversion/strategies/direct_subband.py` - Writer that creates 16 SPWs
- `src/dsa110_contimg/conversion/merge_spws.py` - Utility to merge SPWs into 1

---

## Solution: Enable SPW Merging

### Option 1: Enable During Conversion (Simplest)

**Current Implementation:** The `DirectSubbandWriter` already has SPW merging capability built-in, but it's disabled by default.

**To Enable:**
1. Pass `merge_spws=True` to the writer via `writer_kwargs`
2. Modify the orchestrator to set `merge_spws=True` in writer kwargs

**Code Changes:**

```python
# In hdf5_orchestrator.py, modify convert_subband_groups_to_ms():
current_writer_kwargs = writer_kwargs or {}
current_writer_kwargs.setdefault("merge_spws", True)  # Enable SPW merging
current_writer_kwargs.setdefault("scratch_dir", scratch_dir)
current_writer_kwargs.setdefault("file_list", file_list)
```

**Or via CLI argument:**
- Add `--merge-spws` flag to orchestrator CLI
- Pass it through to writer kwargs

**What Happens:**
1. Per-subband MS files created (as before)
2. Concatenated into 16-SPW MS (as before)
3. **NEW:** `merge_spws()` called with `mstransform(combinespws=True, regridms=True)`
4. All 16 SPWs merged into 1 SPW with regridded frequency grid
5. `SIGMA_SPECTRUM` column removed (space savings)
6. Final MS has 1 SPW

**Location in Code:**
```307:339:src/dsa110_contimg/conversion/strategies/direct_subband.py
# Merge SPWs into a single SPW if requested
if self.merge_spws:
    try:
        from dsa110_contimg.conversion.merge_spws import merge_spws, get_spw_count
        
        n_spw_before = get_spw_count(str(ms_stage_path))
        if n_spw_before and n_spw_before > 1:
            print(f"Merging {n_spw_before} SPWs into a single SPW...")
            ms_multi_spw = str(ms_stage_path)
            ms_single_spw = str(ms_stage_path) + ".merged"
            
            merge_spws(
                ms_in=ms_multi_spw,
                ms_out=ms_single_spw,
                datacolumn="DATA",
                regridms=True,
                keepflags=True,
                remove_sigma_spectrum=self.remove_sigma_spectrum,
            )
            
            # Replace multi-SPW MS with single-SPW MS
            shutil.rmtree(ms_multi_spw, ignore_errors=True)
            shutil.move(ms_single_spw, ms_multi_spw)
            
            n_spw_after = get_spw_count(str(ms_stage_path))
            if n_spw_after == 1:
                print(f"✓ Successfully merged SPWs: {n_spw_before} → 1")
            else:
                print(f"⚠ Warning: Expected 1 SPW after merge, got {n_spw_after}")
    except Exception as merge_err:
        print(f"Warning: SPW merging failed (non-fatal): {merge_err}")
```

---

### Option 2: Post-Conversion Merge (Standalone)

**Use Existing CLI Tool:**

```bash
python -m dsa110_contimg.conversion.merge_spws \
    <ms_in> <ms_out> \
    --datacolumn DATA \
    --interpolation linear
```

**Or Programmatically:**

```python
from dsa110_contimg.conversion.merge_spws import merge_spws

merge_spws(
    ms_in="path/to/16spw.ms",
    ms_out="path/to/1spw.ms",
    datacolumn="DATA",
    regridms=True,
    interpolation="linear",
    keepflags=True,
    remove_sigma_spectrum=True,
)
```

---

## Technical Details

### What `merge_spws()` Does

**Process:**
1. Reads all SPWs from `SPECTRAL_WINDOW` table
2. Flattens and sorts all frequencies across all SPWs
3. Calculates global frequency grid (median channel width)
4. Calls `mstransform(combinespws=True, regridms=True)`:
   - Regrids all channels to a contiguous frequency grid
   - Interpolates data (default: linear interpolation)
   - Preserves flags (`keepflags=True`)
5. Removes `SIGMA_SPECTRUM` column (redundant, saves disk space)

**Frequency Grid:**
- Start: Lowest frequency across all SPWs
- Channels: Total number of channels (sum of all SPWs)
- Width: Median channel width across all SPWs
- Mode: `'frequency'` with linear interpolation

**Code Reference:**
```71:93:src/dsa110_contimg/conversion/merge_spws.py
if regridms:
    # Build global frequency grid from all SPWs
    with table(f"{ms_in}::SPECTRAL_WINDOW", readonly=True) as spw:
        cf = np.asarray(spw.getcol('CHAN_FREQ'))  # shape (nspw, nchan)

    # Flatten and sort all frequencies
    all_freq = np.sort(cf.reshape(-1))

    # Calculate channel width (median of frequency differences)
    freq_diffs = np.diff(all_freq)
    dnu = float(np.median(freq_diffs[freq_diffs > 0]))

    nchan = int(all_freq.size)
    start = float(all_freq[0])

    kwargs.update(
        mode='frequency',
        nchan=nchan,
        start=f'{start}Hz',
        width=f'{dnu}Hz',
        interpolation=interpolation,
    )
```

---

## Known Issues & Considerations

### 1. **mstransform Incompatibility with CASA gaincal**

**Status:** Documented in code comments but not fully tested

**Issue:** The code comment in `direct_subband.py` states:
> "By default, SPW merging is disabled (merge_spws=False) to avoid mstransform incompatibility with CASA gaincal"

**Implication:** MS files merged via `mstransform` may not be compatible with CASA `gaincal` for delay (K) calibration.

**Workaround:** 
- Perform calibration **before** merging SPWs
- Use merged MS only for imaging (post-calibration)
- Or: Test `gaincal` on merged MS to verify compatibility

**Recommended Workflow (if merging enabled):**
1. Convert → 16-SPW MS
2. Calibrate → K/BP/G tables (on 16-SPW MS)
3. Apply calibration → CORRECTED_DATA in 16-SPW MS
4. **Then merge** → 1-SPW MS (from CORRECTED_DATA)
5. Image → Use 1-SPW MS for tclean

---

### 2. **Data Interpolation**

**Impact:** Merging with `regridms=True` performs interpolation:
- **Linear interpolation** (default) smooths data slightly
- May introduce minor artifacts at SPW boundaries
- Frequency gaps between SPWs are filled via interpolation

**Alternative:** Use `regridms=False` to combine without interpolation:
- Faster (no interpolation)
- Preserves original data exactly
- **But:** May have discontinuous frequency coverage if subbands have gaps
- Use `merge_spws_simple()` for this

**Trade-off:**
- `regridms=True`: Smooth, contiguous frequency grid, but interpolated
- `regridms=False`: Original data preserved, but may have gaps

---

### 3. **Disk Space & Performance**

**Disk Space:**
- Merged MS is similar size (slightly larger due to interpolation)
- `SIGMA_SPECTRUM` removal saves some space
- No significant space savings from merging

**Performance:**
- Merging adds ~1-5 minutes per MS (depends on size)
- `mstransform` is single-threaded (no parallelization)
- Memory usage: Moderate (loads one SPW at a time)

---

## Implementation Plan

### Phase 1: Enable Option (Minimal Change) ✅ COMPLETED

**Changes Made:**
1. ✅ Added `--merge-spws` CLI flag to `hdf5_orchestrator.py`
2. ✅ Pass flag through to writer kwargs in `main()`
3. ✅ Default: `False` (maintains backward compatibility)

**Files Modified:**
- `src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py`
  - Added `--merge-spws` argument in `add_args()` (lines 655-664)
  - Added flag handling in `main()` (lines 703-705)

**Status:** ✅ **IMPLEMENTED** (2025-11-02)

**Usage:**
```bash
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming /data/ms \
    "2025-11-02 00:00:00" "2025-11-02 23:59:59" \
    --writer parallel-subband \
    --merge-spws  # Enable SPW merging
```

---

### Phase 2: Test Compatibility (Critical)

**Testing Required:**
1. Create merged MS (1 SPW) from test data
2. Run `gaincal` on merged MS to verify compatibility
3. If incompatible, document workflow (calibrate before merge)

**Test Cases:**
- K-calibration on merged MS
- BP-calibration on merged MS
- G-calibration on merged MS
- Imaging on merged MS (should work)

**Estimated Effort:** 2-4 hours

---

### Phase 3: Pipeline Integration (Optional)

**If merging is desired for all MS files:**

1. **Calibration Strategy:**
   - Keep calibration on 16-SPW MS (avoid compatibility issues)
   - Merge after applying calibration (use CORRECTED_DATA)

2. **Workflow Modification:**
   ```
   Convert → 16-SPW MS
   Calibrate → Caltables (on 16-SPW MS)
   Apply Cal → CORRECTED_DATA (in 16-SPW MS)
   Merge SPWs → 1-SPW MS (from CORRECTED_DATA)
   Image → Use 1-SPW MS
   ```

3. **Update:**
   - `streaming_converter.py`: Add merge step after applycal
   - `imaging/worker.py`: Check for 1-SPW or 16-SPW MS

**Estimated Effort:** 4-8 hours

---

## Alternative: Merge at Different Stage

### Option A: Merge Before Calibration (If Compatible)

**If `gaincal` works on merged MS:**
- Merge immediately after conversion
- Calibrate on 1-SPW MS
- Simpler workflow

**Risk:** May not work if `gaincal` requires multi-SPW structure

---

### Option B: Merge After Imaging (Post-Processing)

**Use Case:** If you want 1-SPW for downstream analysis

**Approach:**
- Keep existing 16-SPW MS through calibration/imaging
- Merge as post-processing step if needed
- Keep both versions (16-SPW and 1-SPW)

**Pros:** No workflow disruption, flexibility

---

## Summary

**What It Takes:**

1. **Minimal Change (Enable Existing Feature):**
   - Add `--merge-spws` flag to orchestrator
   - Set `merge_spws=True` in writer kwargs
   - **Effort:** 30 minutes

2. **Compatibility Testing:**
   - Verify `gaincal` works on merged MS
   - Test full calibration pipeline
   - **Effort:** 2-4 hours

3. **Workflow Integration (If Needed):**
   - Calibrate on 16-SPW MS first
   - Merge after applying calibration
   - Update pipeline stages
   - **Effort:** 4-8 hours

**Current Status:**
- ✅ SPW merging functionality **already exists**
- ✅ Can be enabled with minimal code changes
- ⚠️  Compatibility with `gaincal` needs verification
- ⚠️  Recommended: Calibrate before merging

**Recommendation:**
1. Enable SPW merging via CLI flag (`--merge-spws`)
2. Test `gaincal` compatibility on merged MS
3. If incompatible, implement merge-after-calibration workflow
4. Document chosen approach in pipeline workflow

---

## Code Examples

### Enable SPW Merging via CLI

```bash
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming /data/ms \
    "2025-11-02 00:00:00" "2025-11-02 23:59:59" \
    --writer parallel-subband \
    --merge-spws  # NEW FLAG
```

### Enable SPW Merging Programmatically

```python
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
    convert_subband_groups_to_ms
)

convert_subband_groups_to_ms(
    input_dir="/data/incoming",
    output_dir="/data/ms",
    start_time="2025-11-02 00:00:00",
    end_time="2025-11-02 23:59:59",
    writer="parallel-subband",
    writer_kwargs={
        "merge_spws": True,  # Enable SPW merging
        "regridms": True,
        "interpolation": "linear",
    }
)
```

---

**Review Complete:** 2025-11-02

