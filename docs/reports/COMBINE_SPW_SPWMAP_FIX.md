# Critical Fix: spwmap Required for combine_spw Bandpass Tables

**Date:** 2025-11-05  
**Severity:** CRITICAL  
**Status:** FIXED - Implemented in `src/dsa110_contimg/calibration/calibration.py`

---

## Problem Summary

When `--combine-spw` is used for bandpass calibration, CASA creates a bandpass table with solutions only for the aggregate SPW=0. However, when gain calibration then tries to apply this bandpass table, it fails for SPWs 1-15 because:

1. **Bandpass table structure**: Contains solutions only for SPW=0 (the combined aggregate)
2. **Gain calibration**: Tries to apply bandpass table directly to each SPW without `spwmap`
3. **Result**: SPWs 1-15 fail with "missing (pre-)calibration" error

---

## Evidence from CASA Log

### Bandpass Solve (Line 186)
```
combine='scan,spw'  # Combines all 16 SPWs into aggregate SPW=0
```

### Bandpass Results (Lines 421-436)
```
SPW: 0 [1, 1]  # Has solutions
SPW: 1 [0, 0]  # No solutions
SPW: 2 [0, 0]  # No solutions
...
SPW: 15 [0, 0] # No solutions
```

### Gain Calibration Error (Lines 490-493)
```
WARN Spectral window(s) 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
WARN   could not be solved due to missing (pre-)calibration
WARN     in one or more of the specified tables.
```

### Missing spwmap (Line 461)
```
gaintable=['..._bpcal'], spwmap=[]  # Empty - should be [0]*16
```

---

## Root Cause

When `combine='spw'` is used in `bandpass`:
- CASA combines all SPWs during the solve
- Creates a single solution assigned to SPW=0 (lowest SPW ID)
- Bandpass table only contains SPW=0 solutions

When `gaincal` applies this table:
- Without `spwmap`, CASA tries to apply table directly to each MS SPW
- Table has no solutions for SPWs 1-15, so calibration fails

---

## Solution

**Automatic `spwmap` Detection**: When applying a bandpass table in `solve_gains`:

1. **Check bandpass table SPW count**: Count unique SPW IDs in the table
2. **Check MS SPW count**: Count SPWs in the MS
3. **If table has 1 SPW but MS has multiple SPWs**: Set `spwmap=[0]*n_ms_spw`
4. **Pass `spwmap` to `gaincal`**: Apply the mapping to all bandpass tables

---

## Implementation

### Helper Functions Added

1. **`_get_caltable_spw_count(caltable_path: str)`** (lines 17-36):
   - Reads calibration table and counts unique SPW IDs
   - Returns `None` if unable to read

2. **`_determine_spwmap_for_bptables(bptables: List[str], ms_path: str)`** (lines 39-77):
   - Detects if bandpass table was created with `combine_spw=True`
   - Compares table SPW count (should be 1) with MS SPW count
   - Returns `[0]*n_ms_spw` if mapping needed, `None` otherwise

### `solve_gains` Updated

1. **Automatic Detection** (line 761):
   - Calls `_determine_spwmap_for_bptables()` before first `gaincal`
   - Stores result in `spwmap` variable

2. **First Gain Solve** (lines 784-785):
   - Adds `spwmap` to `kwargs` if detected
   - Passes to `casa_gaincal()`

3. **Second Gain Solve** (lines 818-819):
   - Also applies `spwmap` to short-timescale solve
   - Ensures consistent mapping across all gain solves

### Code Changes

- **File**: `src/dsa110_contimg/calibration/calibration.py`
- **Lines**: 17-77 (helper functions), 761, 784-785, 818-819
- **Import Added**: `from dsa110_contimg.conversion.merge_spws import get_spw_count`

### Testing

- ✅ Code compiles successfully
- ⏳ Needs runtime testing with `--combine-spw` to verify all 16 SPWs get solutions
- ⏳ Needs verification without `--combine-spw` that behavior is unchanged

---

## References

- CASA Documentation: `bandpass` with `combine='spw'` requires `spwmap` when applying
- Log file: `src/casa-20251105-094006.log` lines 186, 421-436, 490-493, 543-559
- Code: `src/dsa110_contimg/calibration/calibration.py` `solve_gains()` function

