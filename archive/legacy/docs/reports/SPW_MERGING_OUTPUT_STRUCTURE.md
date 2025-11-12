# SPW Merging Output MS Structure

**Date:** 2025-11-02  
**Question:** What will the output MS look like using the SPW merging procedure?

---

## Overview

When `--merge-spws` is enabled, the output MS will have **1 SPW instead of 16 SPWs**, with all frequencies from all 16 subbands combined into a single contiguous spectral window.

---

## Input MS Structure (16 SPWs)

**Before merging:**
```
MS: input.ms
├── SPECTRAL_WINDOW table (16 rows)
│   ├── SPW 0: CHAN_FREQ = [f0_0, f0_1, ..., f0_N] (N channels)
│   ├── SPW 1: CHAN_FREQ = [f1_0, f1_1, ..., f1_N] (N channels)
│   ├── ...
│   └── SPW 15: CHAN_FREQ = [f15_0, f15_1, ..., f15_N] (N channels)
│
├── DATA_DESCRIPTION table (16 rows)
│   ├── Each row links to one SPW
│   └── SPECTRAL_WINDOW_ID = [0, 1, 2, ..., 15]
│
├── MAIN table
│   ├── SPW_ID column: Values 0-15
│   ├── DATA column: Shape (Nbaselines, Ntimes, Nchans_per_SPW, Npols)
│   └── Frequency axis varies by SPW_ID
│
└── Total frequency channels: 16 × N (if each subband has N channels)
```

---

## Output MS Structure (1 SPW)

**After merging with `--merge-spws`:**
```
MS: output.ms
├── SPECTRAL_WINDOW table (1 row)
│   └── SPW 0: CHAN_FREQ = [f_min, ..., f_max] (16×N channels, sorted)
│       ├── Start frequency: min(f0_0, f1_0, ..., f15_0)
│       ├── End frequency: max(f0_N, f1_N, ..., f15_N)
│       ├── Channel width: median(all frequency differences)
│       └── Total channels: Sum of all channels from all 16 SPWs
│
├── DATA_DESCRIPTION table (1 row)
│   └── SPECTRAL_WINDOW_ID = [0] (single SPW)
│
├── MAIN table
│   ├── SPW_ID column: All rows = 0 (single SPW)
│   ├── DATA column: Shape (Nbaselines, Ntimes, 16×N_channels, Npols)
│   ├── CHAN_FREQ: Contiguous frequency grid (interpolated)
│   └── All frequencies from all 16 subbands combined
│
└── Frequency coverage: Full bandwidth from all subbands
```

---

## Key Transformations

### 1. SPECTRAL_WINDOW Table

**Input (16 SPWs):**
```
Row 0:  CHAN_FREQ = [1400000000, 1400010000, ..., 1400100000]  # 100 channels
Row 1:  CHAN_FREQ = [1400100000, 1400110000, ..., 1400200000]  # 100 channels
...
Row 15: CHAN_FREQ = [1401500000, 1401510000, ..., 1401600000]  # 100 channels
```

**Output (1 SPW):**
```
Row 0:  CHAN_FREQ = [1400000000, 1400001000, ..., 1401600000]  # 1600 channels
        (All frequencies flattened, sorted, and interpolated to uniform grid)
```

**Calculation:**
- All frequencies from all 16 SPWs are collected
- Flattened: `all_freq = [f0_0, f0_1, ..., f15_N]`
- Sorted: `all_freq = sorted(all_freq)` → ascending order
- Channel width: `median(diff(all_freq))` → uniform spacing
- Total channels: `sum(channels_per_SPW)` → typically 16×N

### 2. DATA Column Structure

**Input (16 SPWs):**
```python
# Each visibility row has data for ONE SPW
Row 0: SPW_ID=0, DATA.shape = (1, 1, N_channels, 4)  # 4 pols
Row 1: SPW_ID=1, DATA.shape = (1, 1, N_channels, 4)
...
Row 15: SPW_ID=15, DATA.shape = (1, 1, N_channels, 4)
```

**Output (1 SPW):**
```python
# Each visibility row has data for ALL frequencies
Row 0: SPW_ID=0, DATA.shape = (1, 1, 16×N_channels, 4)
       # All 16 subbands' frequencies in single row
```

**Data Transformation:**
- Original data from each SPW is **interpolated** to the new frequency grid
- Linear interpolation by default (configurable)
- Gaps between subbands are filled via interpolation
- Overlapping frequencies are properly weighted

### 3. Frequency Grid Properties

**Contiguous Grid:**
```
Input frequencies (may have gaps):
  SPW 0: [1400.000, 1400.010, ..., 1400.100] MHz
  SPW 1: [1400.110, 1400.120, ..., 1400.200] MHz  ← Gap!
  SPW 2: [1400.201, 1400.211, ..., 1400.301] MHz
  ...

Output frequencies (contiguous, uniform):
  SPW 0: [1400.000, 1400.001, 1400.002, ..., 1401.600] MHz
         ↑ All frequencies in one continuous spectrum
         ↑ Uniform channel width (median of differences)
```

**Interpolation:**
- Frequencies between subbands are **interpolated** (not extrapolated)
- Original subband frequencies are preserved exactly
- Intermediate frequencies (if any) use linear interpolation
- Edge frequencies use nearest neighbor if needed

### 4. Metadata Tables

**ANTENNA table:** ✓ Unchanged (same antennas)
**FIELD table:** ✓ Unchanged (same fields)
**OBSERVATION table:** ✓ Unchanged (same observation info)
**POLARIZATION table:** ✓ Unchanged (same polarizations)

**DATA_DESCRIPTION table:**
```
Input: 16 rows (one per SPW)
Output: 1 row (single SPW)
```

---

## Example: DSA-110 Specific Case

### Typical DSA-110 Subband Structure

**Input (16 SPWs):**
- Each subband: ~100 frequency channels
- Total: 16 × 100 = 1,600 channels across all SPWs
- Frequency range: ~1.4 GHz to ~1.41 GHz (example)
- Channel width: ~10 kHz per subband

**Output (1 SPW):**
- **SPW count:** 1 (instead of 16)
- **Total channels:** 1,600 (sum of all subband channels)
- **Frequency range:** Same as input (1.4 to 1.41 GHz)
- **Channel width:** ~10 kHz (median of all channel widths)
- **Grid:** Contiguous, uniform spacing
- **Coverage:** Full bandwidth from all 16 subbands

---

## Data Quality Preservation

### ✅ Preserved
- **Flags:** All flagging information preserved (`keepflags=True`)
- **Weights:** Automatically handled by mstransform (uses WEIGHT/WEIGHT_SPECTRUM)
- **Antenna information:** Unchanged
- **Time information:** Unchanged
- **Baseline information:** Unchanged
- **Polarization:** Unchanged (4 pols: XX, XY, YX, YY)

### ⚠️ Modified
- **Frequency grid:** Interpolated to uniform grid
- **Data values:** Slightly interpolated (linear interpolation)
- **SPW structure:** Reduced from 16 SPWs to 1 SPW
- **SIGMA_SPECTRUM:** Removed (redundant column, saves space)

### ❌ Not Created
- **MODEL_DATA:** Only created if explicitly requested (not by default)
- **CORRECTED_DATA:** Only if calibration was applied before merging
- **Additional columns:** Only standard CASA columns

---

## CASA Tools Compatibility

### After Merging, the MS Will:

**✅ Work with:**
- `tclean` (imaging) ✓
- `listobs` (inspection) ✓
- `plotms` (plotting) ✓
- Most CASA imaging/analysis tools ✓

**⚠️ May need testing:**
- `gaincal` (calibration) - Best practice: calibrate before merging
- `bandpass` (calibration) - Best practice: calibrate before merging
- `applycal` - Should work if caltables are compatible

---

## File Size Comparison

**Input MS (16 SPWs):**
- Size: ~X GB (example)
- Structure: 16 SPWs, separate frequency axes

**Output MS (1 SPW):**
- Size: ~X GB (similar, may be slightly larger due to interpolation)
- Structure: 1 SPW, single contiguous frequency axis
- SIGMA_SPECTRUM removed: Saves some space

**Note:** File size doesn't change significantly because:
- Same number of visibilities
- Same number of channels (sum of all SPWs)
- Interpolation adds minimal overhead
- SIGMA_SPECTRUM removal saves some space

---

## Verification Commands

### Check SPW Count
```bash
# Before merging
python -m dsa110_contimg.conversion.merge_spws <ms_path>  # Check count
# Or use listobs:
listobs(vis='input.ms')  # Shows 16 SPWs

# After merging
listobs(vis='output.ms')  # Shows 1 SPW
```

### Inspect Frequency Grid
```python
from casacore.tables import table
import numpy as np

# Check SPW structure
with table('output.ms::SPECTRAL_WINDOW', readonly=True) as spw:
    print(f"Number of SPWs: {spw.nrows()}")  # Should be 1
    chan_freq = spw.getcol('CHAN_FREQ')
    print(f"Frequency range: {chan_freq.min():.3f} to {chan_freq.max():.3f} MHz")
    print(f"Total channels: {chan_freq.size}")
    print(f"Channel width: {np.median(np.diff(chan_freq)):.3f} MHz")
```

### Verify Data Integrity
```python
# Check that data spans full bandwidth
with table('output.ms', readonly=True) as tb:
    print(f"Rows: {tb.nrows()}")
    print(f"SPW_ID values: {set(tb.getcol('DATA_DESC_ID'))}")  # Should be {0}
    data = tb.getcol('DATA')
    print(f"Data shape: {data.shape}")  # Should be (..., 16×N_channels, 4)
```

---

## Summary

**Output MS Characteristics:**
1. **1 SPW** (instead of 16)
2. **Contiguous frequency grid** (all subbands combined)
3. **Full bandwidth coverage** (from all 16 subbands)
4. **Uniform channel spacing** (median of all channel widths)
5. **Interpolated data** (linear interpolation for gaps)
6. **Same baselines, times, antennas** (unchanged)
7. **Flags preserved** (data quality maintained)
8. **Weights automatically handled** (by mstransform)
9. **SIGMA_SPECTRUM removed** (space savings)

**Key Difference from Input:**
- **Input:** 16 separate frequency windows (SPWs)
- **Output:** 1 continuous frequency spectrum (SPW)
- **Data:** Interpolated to uniform grid (minor smoothing)
- **Structure:** Simpler (single SPW for easier imaging)

---

**This structure is optimal for:**
- Wide-band continuum imaging
- Simplified imaging workflows (no need to specify SPW ranges)
- Tools that prefer single-SPW data
- Simplified data handling

**Considerations:**
- Calibration should ideally be performed on 16-SPW MS first
- Then merge CORRECTED_DATA for imaging
- Or merge DATA if calibration on merged MS is verified compatible

