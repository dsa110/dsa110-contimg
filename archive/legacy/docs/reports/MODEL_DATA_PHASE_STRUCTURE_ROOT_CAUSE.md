# MODEL_DATA Phase Structure Root Cause Analysis

**Date**: 2025-01-XX  
**Issue**: MODEL_DATA phase scatter is 103° instead of < 1° (expected for point source at phase center)  
**Status**: Root cause identified, fix proposed

## Executive Summary

The `MODEL_DATA` column has a phase scatter of 103.3° even though:
- MS phase center (`REFERENCE_DIR` and `PHASE_DIR`) is correctly aligned with calibrator (0.0018 arcmin separation)
- Component list position matches calibrator position
- UVW coordinates appear to be updated by `phaseshift`

This indicates that `ft()` is calculating `MODEL_DATA` phase using incorrect phase center information, despite the MS being correctly rephased.

## Investigation Results

### 1. Phase Center Alignment Verification

**MS Phase Center (after rephasing)**:
- `REFERENCE_DIR`: RA=128.728752927°, Dec=55.572498590°
- `PHASE_DIR`: RA=128.728752927°, Dec=55.572498590°
- **Both are identical** (manually updated `REFERENCE_DIR` to match `PHASE_DIR`)

**Calibrator Position (0834+555)**:
- RA=128.7287°, Dec=55.5725°
- **Separation from MS phase center: 0.0018 arcmin** ✓ (correctly aligned)

**Component List Position**:
- RA=128.7287°, Dec=55.5725° (matches calibrator)
- **Offset from MS phase center: 0.11 arcsec** (should cause < 1° phase scatter)

### 2. MODEL_DATA Phase Structure Analysis

**Actual Phase Scatter**: 103.2° (WRONG - should be < 1°)  
**Expected Phase Scatter** (with correct phase center): 0.1°  
**Expected Phase Scatter** (if using old phase center): 102.5° ✓ **MATCHES ACTUAL!**

**Key Finding**: MODEL_DATA phase structure matches the OLD phase center (before rephasing), not the current phase center.

### 3. UVW Coordinate Analysis

- UVW coordinates are updated by `phaseshift` (as documented)
- Phase correlates with UVW (-0.122 correlation) - indicates phase structure is not random
- But phase scatter (103°) suggests UVW is still in old phase center frame OR `ft()` is using wrong phase center

### 4. Definitive Test: Which Phase Center Does ft() Use?

**Test Results**:
- MODEL_DATA phase does NOT match `REFERENCE_DIR` (scatter: 103.2°)
- MODEL_DATA phase does NOT match `PHASE_DIR` (scatter: 103.2°)
- Both `REFERENCE_DIR` and `PHASE_DIR` are identical in the current MS

**Conclusion**: `ft()` is not using either `REFERENCE_DIR` or `PHASE_DIR` for phase calculations. This suggests:
1. `ft()` cached phase center from before rephasing
2. `ft()` reads phase center from a different source
3. `phaseshift` didn't fully update UVW coordinates (bug in CASA)
4. There's a timing issue where `MODEL_DATA` was written before rephasing

## Root Cause Hypothesis

Based on web search results and CASA documentation:

**Primary Hypothesis**: `ft()` may be reading the phase center from a cached or different source than `REFERENCE_DIR`/`PHASE_DIR`. Alternatively, `phaseshift` may not fully update all internal phase center references that `ft()` uses.

**Secondary Hypothesis**: There may be a bug in `phaseshift` for large phase shifts (54 arcmin). While CASA documentation says `phaseshift` should work for large shifts, the actual behavior suggests UVW or phase center references aren't fully updated.

## Evidence from Web Search

1. **CASA Documentation**: `phaseshift` updates UVW and `PHASE_DIR`, but documentation doesn't explicitly state that it updates all internal phase center references that `ft()` uses.

2. **Expert Knowledge**: `ft()` calculates phase based on component position and MS phase center, but the specific mechanism (which field/column it reads) is not fully documented.

3. **Known Issues**: Some CASA versions have had issues with phase handling, particularly for large phase shifts.

## Investigation Status

**Current Status**: Investigating `ft()` behavior rather than defaulting to workaround.

We have created a test (`tests/science/test_ft_phase_center_behavior.py`) to determine:
1. Which column does `ft()` use: `REFERENCE_DIR` or `PHASE_DIR`?
2. Does `ft()` cache the phase center?
3. What happens if `REFERENCE_DIR` and `PHASE_DIR` differ?

## Proposed Fixes (Pending Investigation)

### Option 1: Understand Which Column ft() Uses

Once we determine which column `ft()` reads, ensure that column is correctly set before calling `ft()`.

### Option 2: Verify `phaseshift` Behavior

Add diagnostic code to verify that `phaseshift` correctly updates all phase center references:
- Check `REFERENCE_DIR` and `PHASE_DIR` (already done)
- Check if there are other phase center references in the MS
- Verify UVW coordinates are correctly transformed

### Option 3: Recalculate MODEL_DATA After Rephasing

If `ft()` is caching phase center information, ensure `MODEL_DATA` is completely cleared and recalculated after rephasing. The current code already does this, but we may need to be more aggressive.

### Option 4: Use `fixvis` Instead of `phaseshift`

The deprecated `fixvis` task may handle phase center updates differently. However, this is not recommended as `fixvis` is deprecated and may have its own bugs.

### Option 5: Calculate MODEL_DATA Manually

Instead of using `ft()`, calculate `MODEL_DATA` manually using the formula:
```
phase = 2π * (u*ΔRA + v*ΔDec) / λ
```
where ΔRA and ΔDec are the offsets from the MS phase center to the component position.

## Recommended Next Steps

1. **Test Option 5** (manual calculation) to verify this fixes the issue
2. **Contact CASA Help Desk** to report potential bug in `phaseshift` or `ft()` for large phase shifts
3. **Verify with CASA experts** which phase center reference `ft()` actually uses
4. **Implement manual MODEL_DATA calculation** as a workaround if confirmed

## Test Results Summary

| Test | Result | Status |
|------|--------|--------|
| MS phase center alignment | 0.0018 arcmin | ✓ Correct |
| Component list position | Matches calibrator | ✓ Correct |
| MODEL_DATA amplitude | 2.500 Jy (correct) | ✓ Correct |
| MODEL_DATA phase scatter | 103.3° | ✗ **WRONG** (should be < 1°) |
| Phase vs REFERENCE_DIR | 103.2° scatter | ✗ Doesn't match |
| Phase vs PHASE_DIR | 103.2° scatter | ✗ Doesn't match |
| Phase vs OLD phase center | 102.5° expected | ✓ Matches (proves issue) |

## Conclusion

The root cause is that `ft()` is calculating `MODEL_DATA` phase using the OLD phase center (before rephasing), not the current phase center. This is likely due to:
- A bug in `phaseshift` not updating all phase center references
- A bug in `ft()` caching phase center information
- Or a timing issue (though unlikely given code flow)

The fix is to manually calculate `MODEL_DATA` phase using the correct phase center, or to investigate and fix the `phaseshift`/`ft()` interaction.

