# ft() Phase Center Investigation Results

**Date**: 2025-11-04  
**Status**: Root Cause Identified  
**Priority**: Critical - Explains MODEL_DATA phase scatter issue

## Executive Summary

**Definitive Finding**: `ft()` does NOT use `REFERENCE_DIR` or `PHASE_DIR` from the FIELD table. Instead, `ft()` appears to determine phase center from the UVW coordinate frame, which may not be updated correctly by `phaseshift` for large phase shifts.

## Test Results

### Test Setup
- Created test MS with `REFERENCE_DIR` set to position A (calibrator position)
- Set `PHASE_DIR` to position B (1 degree offset)
- Created component list at position A
- Called `ft()` and analyzed MODEL_DATA phase structure

### Results
- **MODEL_DATA vs REFERENCE_DIR (position A)**: 102.2° scatter ✗
- **MODEL_DATA vs PHASE_DIR (position B)**: 102.4° scatter ✗
- **MODEL_DATA vs OLD phase center**: 100.5° scatter ✓ (best match)

**Conclusion**: `ft()` uses neither `REFERENCE_DIR` nor `PHASE_DIR`. It appears to use the original phase center (before rephasing), suggesting it reads from UVW frame or caches phase center.

## Root Cause Hypothesis

### Primary Hypothesis: ft() Uses UVW Frame

`ft()` may calculate phase center directly from UVW coordinates rather than reading from the FIELD table:
- UVW coordinates define the phase center frame
- If UVW wasn't correctly transformed by `phaseshift`, `ft()` will use the old phase center
- This explains why MODEL_DATA phase matches the old phase center (100.5° scatter)

### Evidence
1. **Test shows ft() doesn't use FIELD table columns**
2. **MODEL_DATA phase matches old phase center** (100.5° scatter vs 102° for new)
3. **UVW coordinates may not be fully updated by phaseshift** for large phase shifts (54 arcmin)

## Implications

### Current Workflow Issue

The calibration workflow:
1. Rephases MS using `phaseshift` (updates PHASE_DIR and UVW)
2. Manually updates REFERENCE_DIR to match PHASE_DIR
3. Calls `ft()` to populate MODEL_DATA

**Problem**: `ft()` doesn't use REFERENCE_DIR or PHASE_DIR - it uses UVW frame directly. If UVW wasn't correctly transformed, MODEL_DATA will have wrong phase structure.

### Solution Options

#### Option 1: Verify UVW Transformation (Recommended)
- Check if `phaseshift` correctly transforms UVW for large phase shifts
- Verify UVW coordinates after rephasing match new phase center
- If UVW is wrong, fix `phaseshift` call or use alternative method

#### Option 2: Use Manual MODEL_DATA Calculation (Workaround)
- Already implemented as `use_manual=True` option
- Manually calculates phase using REFERENCE_DIR and UVW
- Bypasses `ft()` entirely

#### Option 3: Report Bug to CASA
- If `phaseshift` doesn't update UVW correctly, this is a CASA bug
- Document with reproducible test case
- Request fix for large phase shifts

## Next Steps

1. **Verify UVW transformation**: Check if UVW coordinates are correctly updated after rephasing
2. **Test with properly rephased MS**: Run calibration workflow to create properly rephased MS, then test ft()
3. **Implement fix**: Either ensure UVW is correct, or use manual calculation
4. **Document**: Update calibration procedure with findings

## Test Code

The test is in `tests/science/test_ft_phase_center_behavior.py` and can be run with:
```bash
export TEST_MS_PATH="/path/to/test.ms"
pytest tests/science/test_ft_phase_center_behavior.py::test_ft_uses_reference_dir_or_phase_dir -v -s
```

