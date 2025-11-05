# Recommended Code Changes Based on CASA Best Practices Review

**Date:** 2025-01-XX  
**Based on:** CASA Best Practices Review and Perplexity validation

---

## Summary

Our calibration code **follows CASA best practices** and is well-aligned with standard workflows. However, there are a few minor improvements that could enhance compliance and usability:

1. **Remove unused fluxscale parameter** (cleanup)
2. **Consider adding fluxscale support** (optional enhancement)
3. **Document intentional design decisions** (clarification)

---

## 1. Remove Unused `do_fluxscale` Parameter (Cleanup)

### Current State

**Location:** `src/dsa110_contimg/calibration/calibration.py` (line 611)

```python
def solve_gains(
    ...
    do_fluxscale: bool = False,
    ...
) -> List[str]:
    ...
    # Note: Flux scaling removed - not used in phase-only calibration workflow
```

**Problem:**
- Parameter exists but is never used
- Comment indicates it was intentionally removed
- Import of `casatasks.fluxscale` exists but is unused (line 7)

**Recommendation:** Remove the unused parameter and import to clean up the code

**Impact:** Low - purely cleanup, no functional change

**Code Change:**
```python
# Remove from function signature:
def solve_gains(
    ms: str,
    cal_field: str,
    refant: str,
    ktable: Optional[str],
    bptables: List[str],
    table_prefix: Optional[str] = None,
    t_short: str = "60s",
    # do_fluxscale: bool = False,  # REMOVE THIS LINE
    combine_fields: bool = False,
    ...
)

# Remove unused import:
# from casatasks import fluxscale as casa_fluxscale  # REMOVE THIS LINE
```

**Rationale:** The parameter was removed intentionally for phase-only workflows. Keeping dead code creates confusion and maintenance burden.

---

## 2. Optional: Add Fluxscale Support (Enhancement)

### Current State

Fluxscale is a CASA best practice for transferring flux scale from primary to secondary calibrators. Our code intentionally skips this because:

1. We use single calibrator workflows (0834+555)
2. We use phase-only gain calibration (fluxscale is for amplitude calibration)
3. Flux scale is set via `setjy`/catalog model, not transferred

**However:** If we ever support multiple calibrators or amplitude+phase calibration, fluxscale would be useful.

### Recommendation

**Option A: Keep as-is** (Recommended for current workflow)
- Our single-calibrator, phase-only workflow doesn't need fluxscale
- Adding unused features increases complexity
- Current approach matches our use case

**Option B: Add conditional fluxscale support** (If we expand to multi-calibrator workflows)
- Only enable when `gain_calmode='ap'` (amplitude+phase)
- Only enable when multiple calibrator fields are present
- Add CLI flag `--do-fluxscale` for explicit control

**Code Change (if implementing Option B):**
```python
# In solve_gains(), after phase-only solve:
if do_fluxscale and not phase_only:
    # fluxscale requires amplitude solutions
    # Transfer flux scale from primary to secondary calibrators
    casa_fluxscale(
        vis=ms,
        caltable=f"{table_prefix}_gpcal",
        fluxtable=f"{table_prefix}_fluxcal",
        reference=primary_cal_field,  # Field with known flux
        transfer=secondary_cal_fields,  # List of other calibrator fields
    )
    out.append(f"{table_prefix}_fluxcal")
```

**Impact:** Low - only needed if expanding to multi-calibrator workflows

---

## 3. Document Intentional Design Decisions (Clarification)

### Current State

Several design decisions are implicit in comments but not clearly documented:

1. **Why fluxscale is skipped:** "Flux scaling removed - not used in phase-only calibration workflow"
2. **Why K-calibration is skipped:** Well-documented in CLI help text
3. **Why we use manual MODEL_DATA calculation:** Documented in code comments

### Recommendation

Add clear documentation explaining these intentional design decisions:

**Location:** `src/dsa110_contimg/calibration/calibration.py` (module docstring or function docstrings)

```python
"""
Calibration Module Design Decisions:

1. K-calibration (delay): Skipped by default for DSA-110 (connected-element array).
   Residual delays on short baselines (<2.6 km) are absorbed into gain calibration.
   This matches VLA/ALMA practice.

2. Fluxscale: Not used in current workflow. We use:
   - Single calibrator (0834+555) with known flux from VLA catalog
   - Phase-only gain calibration (fluxscale is for amplitude calibration)
   - Flux scale set via setjy/catalog model, not transferred
   
   If expanding to multi-calibrator or amplitude+phase workflows, fluxscale can be
   added via --do-fluxscale flag.

3. MODEL_DATA calculation: Uses manual calculation (not ft()) to bypass CASA ft()
   phase center bugs. Ensures correct phase structure after rephasing.
"""
```

**Impact:** Low - documentation improvement only

---

## 4. No Other Changes Needed

### Verified Compliant Practices

All major aspects follow CASA best practices:

✓ **Calibration sequence:** Flag → MODEL_DATA → K → BP → G (correct)  
✓ **MODEL_DATA validation:** Checks for populated (not zeros) before calibration  
✓ **Pre-bandpass phase:** solint=30s for time-variable drifts (appropriate)  
✓ **Autocorrelation flagging:** Done before calibration solves (correct)  
✓ **MS preparation:** initweights with dowtsp=True before calibration  
✓ **Table validation:** Validates tables after each solve  

---

## Recommended Action Plan

### Priority 1: Cleanup (Low Risk)
1. Remove unused `do_fluxscale` parameter from `solve_gains()`
2. Remove unused `casatasks.fluxscale` import
3. Update function docstring to remove fluxscale reference

### Priority 2: Documentation (No Risk)
1. Add module-level docstring explaining design decisions
2. Document why fluxscale is intentionally skipped
3. Clarify when fluxscale would be useful (multi-calibrator workflows)

### Priority 3: Future Enhancement (Optional)
1. Only add fluxscale support if expanding to multi-calibrator or amplitude+phase workflows
2. Implement conditional fluxscale (only when `gain_calmode='ap'` and multiple calibrators)

---

## Conclusion

**No critical changes needed.** The code follows CASA best practices. The recommended changes are:

1. **Cleanup:** Remove unused fluxscale parameter (reduces confusion)
2. **Documentation:** Clarify intentional design decisions (improves maintainability)
3. **Future:** Consider fluxscale only if workflow expands (optional enhancement)

These changes are **non-breaking** and improve code clarity without affecting functionality.

