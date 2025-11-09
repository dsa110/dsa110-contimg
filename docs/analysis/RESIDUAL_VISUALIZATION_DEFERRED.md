# Residual Visualization - Deferred Decision

**Date:** 2025-01-27  
**Status:** DEFERRED  
**Decision:** To be added after validating more fundamental stages

---

## Decision Summary

Residual visualization has been **deferred** to focus on validating more fundamental stages of the pipeline first.

---

## Current State

### What Works Now
- ✅ **Residual statistics** - Mean, std, max calculated and returned
- ✅ **Fit quality metrics** - Chi-squared, reduced chi-squared, R-squared
- ✅ **Fit parameters** - All model parameters available
- ✅ **API endpoint** - Returns all statistics in response

### Known Limitation
- ⚠️ **No visual residual image** - Can't see where fit fails spatially
- ⚠️ Statistics only - No pixel-by-pixel visualization

### Workaround
- Use residual statistics (mean, std, max) to assess fit quality
- Check chi-squared and R-squared values
- Visually inspect fit overlay on image

---

## Rationale for Deferral

### 1. Focus on Core Functionality
- Validate fundamental stages first
- Ensure core features work correctly
- Add visualization polish later

### 2. Current Tools Are Sufficient
- Residual statistics provide fit quality assessment
- Chi-squared and R-squared indicate goodness of fit
- Users can assess fit quality from statistics

### 3. Resource Prioritization
- Medium effort (4-6 hours)
- Medium value (visualization enhancement)
- Better to validate core features first

### 4. Can Be Added Later
- No blocking dependencies
- Can be added when needed
- Low risk of deferral

---

## What's Available Now

### Residual Statistics (Already Implemented)

```python
{
    "statistics": {
        "chi_squared": 1234.56,
        "reduced_chi_squared": 1.23,
        "r_squared": 0.95
    },
    "residuals": {
        "mean": 0.001,
        "std": 0.05,
        "max": 0.25
    }
}
```

**Users can:**
- Check reduced chi-squared (should be ~1.0 for good fit)
- Check R-squared (higher is better, >0.9 is good)
- Check residual mean (should be ~0)
- Check residual std (indicates scatter)

---

## When to Revisit

### Triggers for Re-evaluation
1. **User requests** - If users frequently need visual residual inspection
2. **Core validation complete** - After fundamental stages validated
3. **Quality issues** - If statistics alone insufficient for debugging
4. **Production polish** - When preparing for production release

### Implementation Readiness
- ✅ Implementation approach documented in roadmap
- ✅ Technical feasibility confirmed
- ✅ No blocking dependencies
- ✅ Can be added quickly when prioritized

---

## Next Steps

1. **Document current capabilities** - Note that statistics are available
2. **Focus on validation** - Test core functionality with real data
3. **Revisit later** - After core validation complete

---

## Related Documents

- `docs/analysis/PHASE2_LIMITATIONS_ROADMAP.md` - Full roadmap
- `docs/analysis/PRIORITY1_COMPLETION.md` - Region mask implementation
- `docs/analysis/PHASE2_WEEKS6-7_COMPLETION.md` - Image fitting implementation

---

**Status:** DEFERRED - To be added after validating more fundamental stages

