# Critical K-Calibration Issues Discovered - 2025-11-02

## Issue: Missing Precondition Check - MODEL_DATA Requirement ⚠️ CRITICAL

### Problem

During K-calibration of the 0834_555 MS, **MODEL_DATA was not populated** before running `gaincal` with `gaintype='K'`. More critically, **we did not establish MODEL_DATA as a required precondition** before attempting calibration.

### Root Cause

**Violation of "measure twice, cut once" philosophy:**
- We failed to establish MODEL_DATA as a **necessary condition** before K-calibration
- We didn't verify preconditions before proceeding
- The code allowed K-calibration to proceed without MODEL_DATA

### Why This Matters

**For a robust, consistent pipeline:**
- We need an approach that works **generally** for **all calibrators** (bright or faint)
- Not an approach that "sometimes works" for "bright sources"
- Preconditions must be established and verified **before** proceeding
- This prevents wasted time and ensures consistent results

### Impact

1. **Lost time**: Ran K-calibration without verifying preconditions
2. **Uncertainty**: Can't guarantee solutions are correct (even if they appear reasonable)
3. **Inconsistency**: Approach may work for bright sources but fail for faint ones
4. **Pipeline reliability**: Violates systematic, robust development principles

### Fix Applied

**1. Made MODEL_DATA a hard requirement** in `src/dsa110_contimg/calibration/cli.py`:
- Lines 431-438: Changed warning to **error** when `--model-source` is not specified
- Prevents calibration from proceeding without MODEL_DATA

**2. Added precondition check** in `src/dsa110_contimg/calibration/calibration.py`:
- Lines 94-109: Verify MODEL_DATA exists and is populated before solving delays
- Raises clear error if precondition not met
- Documents precondition in function docstring

**3. Moved MODEL_DATA population** to BEFORE K-calibration:
- Lines 368-441: MODEL_DATA population now happens before `solve_delay()` (line 446)
- Ensures precondition is met before proceeding

### Philosophy: "Measure Twice, Cut Once"

This incident demonstrates the importance of:
- **Establishing preconditions upfront**: MODEL_DATA must exist and be populated
- **Verifying before proceeding**: Check requirements, don't assume
- **Consistent, reliable approach**: Work for all cases, not just "sometimes"
- **Prevent wasted time**: Catch issues early, not after processing

### Related Files

- `src/dsa110_contimg/calibration/cli.py`: Calibration workflow (precondition enforcement)
- `src/dsa110_contimg/calibration/calibration.py`: Delay solve function (precondition check)

## Issue 2: Hardcoded Reference Frequency - Fixed ✓

### Problem

QA validation code used hardcoded 1400 MHz for FPARAM interpretation, which may not match the actual observation frequency.

### Fix Applied

**Extract reference frequency from MS SPECTRAL_WINDOW table** in `src/dsa110_contimg/qa/calibration_quality.py`:
- Lines 164-207: Infers MS path from caltable path
- Reads `REF_FREQUENCY` from MS `SPECTRAL_WINDOW` subtable
- Uses median frequency across SPWs if multiple SPWs exist
- Falls back to 1400 MHz only if MS cannot be found

### Verification

Tested on actual K-calibration table:
- ✓ Successfully extracts reference frequency from MS
- ✓ Uses actual frequency (1405.1 MHz) instead of default
- ✓ Provides accurate delay statistics

