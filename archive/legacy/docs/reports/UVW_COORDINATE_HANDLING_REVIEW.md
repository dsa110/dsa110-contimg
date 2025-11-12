# UVW Coordinate Handling Review

**Date:** 2025-01-XX  
**Status:** Review Complete - Critical Fix Applied  
**Priority:** Critical

---

## Executive Summary

Reviewed all UVW coordinate handling throughout the codebase. Found and fixed **one critical bug** where the code attempted to correct UVW coordinates by simple addition/subtraction, which is mathematically incorrect. UVW coordinates must be rotated/transformed when phase center changes, not simply offset.

---

## Key Findings

### ✅ Correct UVW Handling

1. **Initial UVW Computation (Conversion)**
   - **Location:** `conversion/helpers.py:compute_and_set_uvw()`
   - **Method:** Uses pyuvdata utilities to compute UVW from antenna positions and phase center
   - **Correct:** Computes UVW using proper coordinate transformation (rotation matrices)
   - **Details:**
     - Calculates apparent coordinates per unique time
     - Computes frame position angle
     - Uses pyuvdata's `calc_uvw()` or fast path `_PU_CALC_UVW()`
     - Properly transforms baseline vectors to UVW frame

2. **UVW Validation (Precision Check)**
   - **Location:** `conversion/helpers.py:validate_uvw_precision()`
   - **Purpose:** Validates UVW coordinate precision to prevent calibration decorrelation
   - **Correct:** Checks for unreasonable values and detects computation failures
   - **Threshold:** 0.1λ tolerance (configurable)

3. **UVW Verification (After Rephasing)**
   - **Location:** `calibration/uvw_verification.py`
   - **Purpose:** Verifies UVW transformation after `phaseshift`
   - **Correct:** Compares actual UVW change to expected change
   - **Adjusts tolerance** for large phase shifts (>50 arcmin)

4. **Rephasing with phaseshift**
   - **Location:** `calibration/cli.py`
   - **Method:** Uses CASA `phaseshift` task for rephasing
   - **Correct:** `phaseshift` correctly transforms both UVW AND visibility phases together
   - **Verification:** UVW transformation is verified after rephasing

### ❌ Critical Bug Fixed

**Location:** `calibration/cli.py` (lines 1229-1265, now removed)

**Problem:** Code attempted to "correct" UVW coordinates by simple addition/subtraction:
```python
uvw_data[:, 0] += uvw_correction_u  # WRONG - simple offset
uvw_data[:, 1] += uvw_correction_v  # WRONG - simple offset
```

**Why This Is Wrong:**
1. **UVW coordinates are projections onto a plane perpendicular to phase center**
2. **When phase center changes, the entire coordinate system rotates**
3. **Simple offset does NOT account for geometric rotation**
4. **Even if UVW is "fixed" by offset, DATA column visibility phases remain wrong**
5. **This causes DATA/MODEL misalignment and calibration failures**

**Correct Approach:**
- Use `phaseshift` which performs **coordinate rotation** to transform UVW
- `phaseshift` updates both UVW coordinates AND visibility phases together
- This ensures DATA column and UVW frame remain consistent

**Fix Applied:**
- Removed incorrect direct UVW offset correction code
- Always use `phaseshift` for rephasing (which handles full transformation)
- Added comment explaining why simple offset is incorrect

---

## UVW Coordinate Mathematics

### Correct Transformation

When phase center changes, UVW coordinates must be **rotated**, not translated:

\[ \mathbf{b}' = \mathbf{R} \cdot \mathbf{b} \]

where:
- **b** = baseline vector in Earth-Centered-Fixed coordinates
- **R** = rotation matrix transforming from old to new phase center direction
- **b'** = rotated baseline vector

The UV coordinates are then recalculated by projecting the rotated baseline onto a plane perpendicular to the new phase center direction.

### Why Simple Offset Doesn't Work

UV coordinates are not absolute positions—they are **projections of baseline vectors**:
- Changing phase center rotates the entire reference frame
- The UV plane itself rotates in 3D space
- Each baseline's projection changes direction and magnitude
- Simple offset cannot account for this geometric rotation

---

## UVW Handling Best Practices

### ✅ DO

1. **Use proper tools for UVW transformation:**
   - `phaseshift` (CASA) for rephasing MS
   - `compute_and_set_uvw()` (pyuvdata) for initial computation
   - These handle coordinate rotation correctly

2. **Verify UVW alignment after rephasing:**
   - Check U/V means are near zero (< 100 m for correctly phased MS)
   - Verify UVW transformation magnitude matches expected change
   - Use `verify_uvw_transformation()` for validation

3. **Keep UVW and DATA column in sync:**
   - Always use `phaseshift` which updates both together
   - Never modify UVW directly without updating visibility phases

### ❌ DON'T

1. **Never correct UVW by simple addition/subtraction:**
   - UVW requires coordinate rotation, not translation
   - Direct modification breaks DATA/UVW consistency

2. **Never modify UVW without updating DATA column:**
   - UVW and DATA must reference the same phase center
   - Inconsistent phase centers cause calibration failures

3. **Never assume UVW is correct just because phase center matches:**
   - UVW can be misaligned even if `REFERENCE_DIR`/`PHASE_DIR` match
   - Always verify UVW alignment (U/V means near zero)

---

## Code Locations

### UVW Computation

- **Initial computation:** `conversion/helpers.py:compute_and_set_uvw()` (lines 315-412)
- **During conversion:** `conversion/strategies/direct_subband.py` (line 520)
- **Meridian phasing:** `conversion/helpers.py:phase_to_meridian()` (line 245)

### UVW Validation

- **Precision check:** `conversion/helpers.py:validate_uvw_precision()` (lines 560-619)
- **Alignment check:** `calibration/cli.py` (lines 1168-1224)
- **Transformation verification:** `calibration/uvw_verification.py`

### UVW Usage

- **MODEL_DATA calculation:** `calibration/model.py:_calculate_manual_model_data()` (lines 96-99)
  - Uses UVW from MS for phase calculation
  - Correct: Uses PHASE_DIR (matches DATA column phasing)

---

## Verification

### UVW Alignment Check

After rephasing, verify UVW alignment:
- **U mean should be < 100 m** (ideally < 10 m)
- **V mean should be < 100 m** (ideally < 10 m)
- **W mean can be non-zero** (depends on source elevation)

### UVW Transformation Verification

After `phaseshift`, verify transformation:
- **UVW change matches expected magnitude** (within tolerance)
- **Tolerance adjusted for large phase shifts** (>50 arcmin)

---

## Conclusion

UVW coordinate handling is now **correct throughout the codebase**:

1. ✅ Initial UVW computation uses proper coordinate transformation
2. ✅ UVW validation checks for precision and alignment
3. ✅ Rephasing uses `phaseshift` (correct rotation/transformation)
4. ✅ UVW verification after rephasing
5. ✅ **FIXED:** Removed incorrect direct UVW offset correction

**All UVW operations now use proper coordinate transformation methods.**

---

## References

- CASA Documentation: [UV Manipulation](https://casadocs.readthedocs.io/en/v6.5.1/notebooks/uv_manipulation.html)
- CASA Memo: [Convention for UVW calculations in CASA](https://casa.nrao.edu/Memos/CoordConvention.pdf)
- Perplexity Validation: UVW coordinates require rotation/transformation, not simple offset

