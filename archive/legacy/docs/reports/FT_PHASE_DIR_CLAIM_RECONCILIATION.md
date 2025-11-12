# ft() PHASE_DIR Claim Reconciliation

**Date:** 2025-11-05  
**Status:** Investigating Discrepancy  
**User Claim:** `ft()` determines phase center from PHASE_DIR  
**Our Test Results:** `ft()` doesn't use PHASE_DIR correctly (102.4° scatter)

---

## Discrepancy

### User Statement
**"ft() determines phase center from PHASE_DIR"**

### Our Test Results
**From `FT_PHASE_CENTER_INVESTIGATION_RESULTS.md`:**
- MODEL_DATA vs PHASE_DIR (position B): **102.4° scatter** ✗
- MODEL_DATA vs OLD phase center: **100.5° scatter** ✓ (best match)

**Conclusion:** `ft()` doesn't appear to use PHASE_DIR correctly.

---

## Possible Reconciliation

### Scenario 1: ft() Reads PHASE_DIR But Doesn't Use It Correctly

**If `ft()` reads PHASE_DIR but fails to use it correctly:**
- `ft()` may read PHASE_DIR from FIELD table
- But calculate phase using wrong coordinate system
- Or apply PHASE_DIR incorrectly after rephasing
- This would explain: PHASE_DIR is read, but not used correctly

**Evidence:** Our test showed 102.4° scatter when PHASE_DIR was set to position B, suggesting `ft()` didn't use it.

---

### Scenario 2: ft() Uses PHASE_DIR But Only for Non-Rephased MS

**If `ft()` uses PHASE_DIR correctly for original MS:**
- `ft()` reads PHASE_DIR correctly for MS that hasn't been rephased
- But fails after `phaseshift` updates PHASE_DIR
- This could be a bug in how `ft()` handles updated PHASE_DIR

**Evidence:** Our test used a rephased MS, which may have triggered a bug.

---

### Scenario 3: ft() Uses PHASE_DIR But There's a Caching Issue

**If `ft()` caches phase center:**
- `ft()` may read PHASE_DIR on first access and cache it
- Subsequent calls use cached value, even if PHASE_DIR changed
- This would explain why MODEL_DATA matches old phase center

**Evidence:** Our test showed MODEL_DATA matched old phase center (100.5° scatter), suggesting caching.

---

### Scenario 4: ft() Uses PHASE_DIR But UVW Transformation Is Wrong

**If `ft()` uses PHASE_DIR but UVW wasn't correctly transformed:**
- `ft()` reads PHASE_DIR correctly
- But calculates phase using UVW coordinates that weren't correctly updated
- Result: Phase calculation uses wrong UVW frame

**Evidence:** Our test showed MODEL_DATA matched old phase center, suggesting UVW issue.

---

### Scenario 5: User Has Different Information

**If user has source code or authoritative documentation:**
- Source code may show `ft()` reads PHASE_DIR
- But implementation may have bugs for certain conditions
- Our test may have hit a bug condition

**Action Needed:** Verify user's source of information.

---

## Key Questions

1. **Does `ft()` read PHASE_DIR from FIELD table?**
   - User says yes
   - We need to verify with source code or authoritative docs

2. **Does `ft()` use PHASE_DIR correctly for phase calculations?**
   - Our test suggests no (102.4° scatter)
   - But maybe it's supposed to work and there's a bug?

3. **What conditions cause `ft()` to fail?**
   - After rephasing?
   - Large phase shifts?
   - Caching issues?

4. **Is there a difference between reading and using?**
   - Maybe `ft()` reads PHASE_DIR but doesn't use it correctly?

---

## Next Steps

1. **Verify user's claim** - Source code or authoritative documentation
2. **Re-run test** - With fresh MS (not rephased) to see if `ft()` works correctly
3. **Test conditions** - Small vs. large phase shifts, before vs. after rephasing
4. **Understand the bug** - If `ft()` is supposed to use PHASE_DIR, why doesn't it work?

---

## Current Understanding (Pending Verification)

**If user is correct:**
- `ft()` is designed to use PHASE_DIR
- But there's a bug or condition where it doesn't work correctly
- Our manual calculation is still the workaround until the bug is fixed

**If our tests are correct:**
- `ft()` doesn't use PHASE_DIR (or uses it incorrectly)
- Manual calculation is the correct solution

---

## References

- Previous test: `docs/reports/FT_PHASE_CENTER_INVESTIGATION_RESULTS.md`
- Test code: `tests/science/test_ft_phase_center_behavior.py`
- User claim: "ft() determines phase center from PHASE_DIR"

