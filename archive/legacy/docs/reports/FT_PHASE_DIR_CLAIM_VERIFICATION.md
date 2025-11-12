# ft() PHASE_DIR Claim Verification

**Date:** 2025-11-05  
**Status:** Verification Needed  
**Claim:** `ft()` determines phase center from PHASE_DIR

---

## Claim vs. Previous Test Results

### User Claim
**"ft() determines phase center from PHASE_DIR"**

### Previous Test Results
**From `docs/reports/FT_PHASE_CENTER_INVESTIGATION_RESULTS.md`:**

Test setup:
- Created test MS with `REFERENCE_DIR` set to position A (calibrator position)
- Set `PHASE_DIR` to position B (1 degree offset)
- Created component list at position A
- Called `ft()` and analyzed MODEL_DATA phase structure

**Results:**
- **MODEL_DATA vs REFERENCE_DIR (position A)**: 102.2° scatter ✗
- **MODEL_DATA vs PHASE_DIR (position B)**: 102.4° scatter ✗
- **MODEL_DATA vs OLD phase center**: 100.5° scatter ✓ (best match)

**Previous Conclusion:** `ft()` uses neither `REFERENCE_DIR` nor `PHASE_DIR`. It appears to use the original phase center (before rephasing), suggesting it reads from UVW frame or caches phase center.

---

## Discrepancy Analysis

### Possible Explanations

1. **Test Conditions:**
   - Previous test used MS that was rephased
   - Maybe `ft()` uses PHASE_DIR correctly for non-rephased MS?
   - Maybe `ft()` uses PHASE_DIR but there's a bug for large phase shifts?

2. **CASA Version Differences:**
   - Different CASA versions may behave differently
   - Source code may have changed

3. **Implementation Details:**
   - `ft()` may read PHASE_DIR but not use it correctly for phase calculations
   - `ft()` may read PHASE_DIR but apply it incorrectly after rephasing

4. **Test Flaw:**
   - Previous test may have had a flaw
   - UVW coordinates may not have been correctly transformed

---

## Verification Needed

### Questions to Answer

1. **Does `ft()` read PHASE_DIR from FIELD table?**
   - Source code analysis needed
   - Or authoritative documentation

2. **Does `ft()` use PHASE_DIR for phase calculations?**
   - Even if it reads PHASE_DIR, does it use it correctly?

3. **What happens after rephasing?**
   - Does `ft()` use updated PHASE_DIR correctly after `phaseshift`?
   - Or does it cache/use old phase center?

4. **What about large phase shifts?**
   - Does `ft()` work correctly for small shifts but fail for large ones (54 arcmin)?

---

## Current Status

**Need to verify:** Whether `ft()` actually uses PHASE_DIR and if so, why our tests showed it doesn't.

**If user is correct:** We need to understand:
- Why our test showed 102.4° scatter when PHASE_DIR was set to position B
- What conditions cause `ft()` to fail to use PHASE_DIR correctly
- Whether this is a bug or expected behavior under certain conditions

---

## Next Steps

1. Verify user's claim with source code or authoritative documentation
2. Re-run test with fresh MS (not rephased) to see if `ft()` uses PHASE_DIR correctly
3. Test with small vs. large phase shifts to see if there's a threshold
4. Check CASA version differences

---

## References

- Previous test: `docs/reports/FT_PHASE_CENTER_INVESTIGATION_RESULTS.md`
- Test code: `tests/science/test_ft_phase_center_behavior.py`

