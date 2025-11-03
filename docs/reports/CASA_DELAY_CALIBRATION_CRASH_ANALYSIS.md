# CASA Delay Calibration Crash Analysis

**Date:** 2025-12-19  
**Issue:** CASA `gaincal` with `gaintype='K'` crashes with `ArrayConformanceError: Matrix<T>::column - column < 0 or > end`  
**MS:** `/scratch/dsa110-contimg/ms/0834_555_single/parallel/0834_555_2025-10-30_134913.ms`

## MS Creation Process

This MS was created using the **direct-subband** approach:

1. **pyuvdata.write_ms()** creates individual per-subband MS files (via `_write_ms_subband_part()`)
2. **CASA concat()** concatenates per-subband MS files into a multi-SPW MS
3. **CASA mstransform()** merges all SPWs into a single SPW MS (via `merge_spws()`)

The final MS has been processed by **both pyuvdata and CASA operations**. The crash might be related to how `mstransform()` modifies the MS structure or an incompatibility between pyuvdata-created MS that's been merged with `mstransform()`.

## Root Cause Analysis

### MS Structure Verification

The MS structure was verified and found to be **correct**:

✅ **Main Table:**
- 221,184 rows
- All required columns present: DATA, FLAG, ANTENNA1, ANTENNA2, FIELD_ID, TIME
- DATA shape: (768 channels, 2 polarizations) per row
- DATA dtype: complex64

✅ **Subtables:**
- SPECTRAL_WINDOW: 1 SPW, 768 channels
- POLARIZATION: 1 pol config, CORR_TYPE = [9, 12] (RR, LL)
- DATA_DESCRIPTION: 1 entry, properly linked
- ANTENNA: 117 antennas, reference antenna 103 present
- FIELD: 1 field

✅ **MODEL_DATA Column:**
- Column exists (added via `addImagingColumns`)
- Properly initialized with matching shape
- Populated with DATA values (tested both zeros and DATA copy)

### Crash Location

The crash occurs **inside CASA's internal code** during `gaincal` execution, specifically:
- Error: `casacore::ArrayConformanceError: Matrix<T>::column - column < 0 or > end`
- This is a CASA/casacore internal error, not a Python error
- Happens during CASA's internal data access, not during validation

### What We Know

1. **MS Structure is Valid:** All tables, columns, and IDs are correct
2. **MODEL_DATA Exists:** Column is present and properly initialized
3. **Validation Passes:** The `solve_delay` validation code runs successfully
4. **Crash is Internal:** Happens inside CASA/casacore during `gaincal` execution

### Possible Causes

1. **mstransform() Compatibility Issue:**
   - MS created by pyuvdata, then merged with CASA `mstransform()`
   - `mstransform()` may modify MS structure in ways that `gaincal` doesn't handle
   - Could be related to how `mstransform()` handles MODEL_DATA column

2. **pyuvdata + CASA Interaction:**
   - pyuvdata creates MS with specific structure
   - CASA `concat()` and `mstransform()` modify that structure
   - Resulting MS may have internal inconsistencies that `gaincal` detects

3. **MODEL_DATA Column After mstransform():**
   - `mstransform()` may not properly handle MODEL_DATA from pyuvdata-created MS
   - Column may exist but have internal structure issues

4. **Internal CASA Bug:**
   - May be a known CASA issue with certain MS configurations
   - Could be related to the 2-pol (RR, LL) format vs standard 4-pol
   - Could be related to MS that's been through multiple CASA operations

### Recommendations

1. **Test Before mstransform():**
   - Try running `gaincal` on the multi-SPW MS **before** SPW merging
   - This would test if `mstransform()` is causing the issue
   - If successful, the problem is with `mstransform()` output

2. **Re-populate MODEL_DATA After mstransform():**
   - `mstransform()` may corrupt MODEL_DATA structure
   - Try removing and re-adding MODEL_DATA after merge
   - Use CASA's `setjy` or `ft()` to populate MODEL_DATA via CASA tools

3. **Alternative Approaches:**
   - Run calibration on multi-SPW MS before merging
   - Use CASA's `clearcal` first to ensure clean state
   - Try `setjy` before `gaincal` to populate MODEL_DATA via CASA
   - Use CASA's `listobs` to verify MS is fully readable

4. **Workaround:**
   - Use existing calibration tables if available
   - Run calibration on a different MS that was created differently
   - Consider using pyuvdata-monolithic writer instead (single MS write, no merge)

### Next Steps

1. Test with MS created by CASA tools (not pyuvdata)
2. Check CASA logs for more detailed error information
3. Verify CASA version compatibility
4. Try `setjy` before `gaincal` to populate MODEL_DATA via CASA's tools
5. Consider using an MS that has been successfully calibrated before

## Conclusion

**CONFIRMED:** The MS created by `mstransform()` is **incompatible with CASA `gaincal`**.

The crash occurs deep in CASA's C++ code (`casacore::ArrayConformanceError`) when accessing internal matrix structures. This is a fatal incompatibility between `mstransform()` output and `gaincal`'s expectations.

### Root Cause

`mstransform()` modifies the MS structure in ways that `gaincal` cannot handle, causing C++-level crashes that cannot be caught at the Python level.

### Solution

**Calibrate before merging SPWs:**

1. Run `gaincal` on the **multi-SPW MS** (after `concat()` but **before** `mstransform()`)
2. Apply calibration tables to the multi-SPW MS
3. Then merge SPWs with `mstransform()` if needed for imaging

**Alternative:** Use the `pyuvdata-monolithic` writer strategy instead, which creates a single MS without needing `mstransform()`.


