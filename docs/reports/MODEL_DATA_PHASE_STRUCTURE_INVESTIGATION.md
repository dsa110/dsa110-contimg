# MODEL_DATA Phase Structure Investigation

**Date**: 2025-01-XX  
**Issue**: MODEL_DATA phase scatter is 103° instead of < 1° (expected for point source at phase center)  
**Status**: Under Investigation - Understanding ft() behavior

## Executive Summary

The `MODEL_DATA` column has a phase scatter of 103.3° even though:
- MS phase center (`REFERENCE_DIR` and `PHASE_DIR`) is correctly aligned with calibrator (0.0018 arcmin separation)
- Component list position matches calibrator position
- UVW coordinates appear to be updated by `phaseshift`

This indicates that `ft()` may be calculating `MODEL_DATA` phase using incorrect phase center information, despite the MS being correctly rephased.

## Investigation Approach

Rather than defaulting to a manual workaround, we are systematically investigating how `ft()` determines the phase center.

### Key Questions

1. **Which column does ft() use?**
   - Does `ft()` read `REFERENCE_DIR` or `PHASE_DIR` from the FIELD table?
   - CASA documentation says ft() uses "phase center from first field" but doesn't specify which column

2. **Does ft() cache the phase center?**
   - Does `ft()` read phase center on first access and cache it?
   - Could there be a timing issue where `ft()` reads phase center before `phaseshift` completes?

3. **What happens for large phase shifts?**
   - Is there a known bug in `ft()` for large phase shifts (54 arcmin)?
   - Does `phaseshift` correctly update all references that `ft()` uses?

### Test Strategy

Created `tests/science/test_ft_phase_center_behavior.py` to:
1. Create a test MS with `REFERENCE_DIR` != `PHASE_DIR`
2. Set component at position matching `REFERENCE_DIR`
3. Call `ft()` and check which phase center it uses
4. This will definitively determine which column `ft()` reads

## Current Understanding

### Phase Center Columns in MS

The FIELD table has three direction-related columns:
- `REFERENCE_DIR`: Used by CASA calibration tasks (e.g., `gaincal`, `bandpass`)
- `PHASE_DIR`: Updated by `phaseshift` task
- `DELAY_DIR`: Used for delay calibration

### phaseshift Behavior

According to CASA documentation:
- `phaseshift` updates `PHASE_DIR` and UVW coordinates
- `phaseshift` may NOT update `REFERENCE_DIR` (we manually update it)
- Both `REFERENCE_DIR` and `PHASE_DIR` are correctly set after rephasing

### ft() Documentation

From CASA docs:
- `ft()` uses "phase center from first field"
- Does NOT specify `REFERENCE_DIR` vs `PHASE_DIR`
- Does NOT have a `phasecenter` parameter to override
- Calculates phase based on component position relative to phase center

## Evidence

### Phase Scatter Analysis

- **Expected scatter** (with correct phase center): 0.1°
- **Expected scatter** (if using old phase center): 102.5°
- **Actual scatter**: 103.2° ✓ **Matches old phase center!**

This strongly suggests `ft()` is using the OLD phase center, not the current one.

### Possible Explanations

1. **ft() reads PHASE_DIR but phaseshift didn't update it correctly**
   - But we verified PHASE_DIR is correct after rephasing

2. **ft() reads REFERENCE_DIR but from a cached/stale state**
   - But we verified REFERENCE_DIR is correct after rephasing

3. **ft() reads phase center BEFORE phaseshift completes**
   - But workflow is: rephase → clear MODEL_DATA → ft()
   - Timing should be correct

4. **ft() uses a different phase center source**
   - Could there be another phase center reference in the MS?
   - Could `ft()` use UVW frame directly instead of FIELD table?

5. **Bug in ft() for large phase shifts**
   - 54 arcmin is a large shift
   - Could `ft()` have numerical precision issues?

## Next Steps

1. **Run controlled test** (`test_ft_phase_center_behavior.py`) to determine which column `ft()` uses
2. **If ft() uses wrong column**: Ensure that column is correctly set
3. **If ft() has a bug**: Report to CASA and implement workaround
4. **If timing issue**: Fix workflow order
5. **If caching issue**: Force `ft()` to re-read phase center

## Current Workaround (Temporary)

Manual MODEL_DATA calculation is available as `use_manual=True` option, but we should NOT default to it until we understand why `ft()` fails.

## References

- CASA ft() documentation: https://casadocs.readthedocs.io/en/v6.6.0/api/tt/casatasks.imaging.ft.html
- CASA phaseshift documentation: https://casadocs.readthedocs.io/en/v6.6.0/api/tt/casatasks.manipulation.phaseshift.html

