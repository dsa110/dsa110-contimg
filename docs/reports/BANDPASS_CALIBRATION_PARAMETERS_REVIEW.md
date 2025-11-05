# Bandpass Calibration Parameters Review

**Date:** 2025-11-05  
**Investigation:** Review of bandpass calibration parameters against CASA best practices  
**Status:** ✅ **MOSTLY COMPLETE - One optional parameter identified**

---

## Summary

Our bandpass calibration implementation is **comprehensive and follows CASA best practices**. One optional parameter (`fillgaps`) was identified that could be useful in some scenarios, but it's not required for correct operation.

---

## Current Implementation

### Parameters Currently Set

**Location:** `src/dsa110_contimg/calibration/calibration.py` (lines 538-559)

```python
kwargs = dict(
    vis=ms,
    caltable=f"{table_prefix}_bpcal",
    field=field_selector,
    solint="inf",  # Per-channel solution (bandpass)
    refant=refant,
    combine=comb,  # scan,field,spw as configured
    solnorm=True,  # Normalize solutions
    bandtype="B",  # Per-channel bandpass
    selectdata=True,  # Required to use uvrange parameter
    minsnr=minsnr,  # Minimum SNR threshold
)
# Conditional parameters:
if uvrange:
    kwargs["uvrange"] = uvrange
if prebandpass_phase_table:
    kwargs["gaintable"] = [prebandpass_phase_table]
```

**Status:** ✅ **All essential parameters are present**

---

## Missing Optional Parameters

### 1. `fillgaps` Parameter

**CASA Documentation:**
- **Default:** `0` (don't interpolate)
- **Purpose:** Fill flagged solution channels by interpolation
- **Example:** `fillgaps=3` (interpolate gaps 3 channels wide and narrower)
- **Usage:** Interpolates flagged channels in the bandpass solution table

**Tutorial Examples:**
- ERIS tutorial: `fillgaps=16` (used for e-MERLIN data)
- Some tutorials use `fillgaps=1` to `fillgaps=3` for narrow gaps

**When to Use:**
- When some channels have flagged solutions but surrounding channels are good
- Useful for filling isolated flagged channels in the bandpass solution
- **Not recommended** for large gaps or systematic flagging

**Recommendation:**
- **Optional enhancement** - not required for correct operation
- Could be added as CLI parameter: `--bp-fillgaps <int>`
- Default: `0` (no interpolation) - matches CASA default
- Useful when there are isolated flagged channels in bandpass solutions

**Impact:** **Low Priority**
- Current behavior (no interpolation) is correct and matches CASA default
- Interpolation is only useful if there are isolated flagged channels
- Most flagged channels are likely at edges (expected) or due to low SNR (should remain flagged)

### 2. `minblperant` Parameter

**CASA Documentation:**
- **Default:** `4` (minimum baselines per antenna required for solve)
- **Purpose:** Excludes antennas with fewer baselines from solutions
- **Rationale:** 
  - Amplitude solutions with fewer than 4 baselines are only trivially constrained
  - Phase solutions with fewer than 3 baselines are only trivially constrained
  - Solutions with too few baselines are no better than baseline-based solutions

**Tutorial Examples:**
- ERIS tutorial: `minblperant=2` (for smaller arrays)
- CASA default: `4` (standard for most arrays)

**When to Use:**
- For small arrays (<10 antennas), may need to lower to `2` or `3`
- For large arrays (>20 antennas), default `4` is appropriate
- DSA-110 has ~110 antennas, so default `4` is appropriate

**Current Behavior:**
- **Uses CASA default** (`4`) - not explicitly set in kwargs
- This is **correct** for DSA-110 (large array)
- CASA will use default value automatically

**Recommendation:**
- **No change needed** - CASA default is appropriate
- Could add as optional CLI parameter for small-array testing: `--bp-minblperant <int>`
- **Low priority** - default works well for DSA-110

**Impact:** **Very Low Priority**
- CASA default (`4`) is appropriate for DSA-110
- No explicit setting needed (CASA handles defaults)
- Would only be useful for testing with smaller arrays

---

## Comparison with CASA Best Practices

### Required Parameters ✅

| Parameter | Status | Notes |
|-----------|--------|-------|
| `vis` | ✅ Set | Measurement Set path |
| `caltable` | ✅ Set | Output calibration table |
| `field` | ✅ Set | Field selector |
| `solint` | ✅ Set | `'inf'` (per-channel solution) |
| `refant` | ✅ Set | Reference antenna |
| `combine` | ✅ Set | `scan`, optionally `field`, `spw` |
| `solnorm` | ✅ Set | `True` (normalize solutions) |
| `bandtype` | ✅ Set | `'B'` (per-channel) |
| `minsnr` | ✅ Set | Configurable (default 3.0) |

### Optional but Recommended ✅

| Parameter | Status | Notes |
|-----------|--------|-------|
| `uvrange` | ✅ Conditional | Set when provided via CLI/env |
| `gaintable` | ✅ Conditional | Set when pre-bandpass phase is enabled |
| `selectdata` | ✅ Set | Required for `uvrange` parameter |

### Optional Enhancements ⚠️

| Parameter | Status | Recommendation |
|-----------|--------|----------------|
| `fillgaps` | ⚠️ Missing (uses default 0) | **Optional** - could add as CLI parameter |
| `minblperant` | ⚠️ Missing (uses default 4) | **No change needed** - default is correct |

---

## Conclusion

### Missing Parameters: **NO CRITICAL MISSING PARAMETERS**

**Optional Enhancements Identified:**

1. **`fillgaps` parameter** (optional):
   - **Priority:** Low
   - **Impact:** Useful for filling isolated flagged channels
   - **Recommendation:** Could add as `--bp-fillgaps <int>` CLI parameter
   - **Default:** `0` (no interpolation, matches CASA default)
   - **Use case:** When bandpass solutions have isolated flagged channels that could be interpolated

2. **`minblperant` parameter** (very low priority):
   - **Priority:** Very Low
   - **Impact:** CASA default (`4`) is appropriate for DSA-110
   - **Recommendation:** No change needed
   - **Use case:** Only useful for testing with smaller arrays

### Recommendation

**Current implementation is correct and complete for standard operation.**

The only optional enhancement would be to add `--bp-fillgaps` as a CLI parameter for cases where interpolation of isolated flagged channels is desired. However, this is not required for correct operation, and the current behavior (no interpolation) matches CASA defaults and best practices.

---

## References

1. **CASA Documentation:**
   - `bandpass` task parameters: `fillgaps`, `minblperant`
   - Default values and usage guidelines

2. **Tutorial Examples:**
   - ERIS 2024: Uses `fillgaps=16` for e-MERLIN data
   - CASA tutorials: Various examples with `fillgaps=1` to `fillgaps=3`

3. **Codebase:**
   - `src/dsa110_contimg/calibration/calibration.py` (lines 538-559)
   - `src/dsa110_contimg/calibration/cli.py` (lines 273-294)

