# End-to-End Pipeline Review: "Measure Twice, Cut Once" Analysis

**Date:** 2025-11-02  
**Review Scope:** Complete mosaicking pipeline from planning to final output

## Executive Summary

The pipeline is **generally well-validated** but has several opportunities to improve adherence to "measure twice, cut once" philosophy. Key gaps:

1. **Missing upfront validation** - Expensive operations start before all pre-conditions are verified
2. **Late error detection** - Some checks happen inside expensive operations rather than upfront
3. **Missing dry-run/preview** - No way to validate plan without executing
4. **Redundant checks** - Some validations happen multiple times

---

## Detailed Analysis

### ✅ Strengths (Good "Measure Twice" Practices)

1. **Comprehensive validation pipeline** - Multiple validation stages
2. **Error handling with context** - Good error messages with recovery hints
3. **Post-mosaic validation** - Validates final product
4. **Disk space checks** - Prevents wasted time (though placement could be earlier)

### ⚠️ Issues Found

#### 1. Missing Pre-Flight Validation (CRITICAL)

**Issue:** Expensive validation operations start before verifying basic pre-conditions.

**Current Flow:**
```python
cmd_build() 
  → Load tiles from DB ✓
  → Check if tiles list empty ✓
  → Start expensive validation (imhead calls, image reads) ⚠️
  → Check disk space INSIDE _build_weighted_mosaic() ⚠️
```

**Problems:**
- No upfront check that all tile files exist before starting
- No check that output directory exists/is writable
- No check that all PB images exist before building
- Disk space check happens inside `_build_weighted_mosaic()` instead of upfront

**"Measure Twice" Violation:** We start expensive operations before validating all pre-conditions.

**Fix:** Add comprehensive pre-flight validation before any expensive operations.

---

#### 2. Late Error Detection (MODERATE)

**Issue:** Some critical checks happen inside expensive operations.

**Examples:**
- PB image existence checked inside `_build_weighted_mosaic()` after validation
- Disk space checked inside `_build_weighted_mosaic()` after validation
- Output path validation happens implicitly (may fail late)

**"Measure Twice" Violation:** We validate tiles but don't validate dependencies until building.

**Fix:** Move all dependency checks to pre-flight validation.

---

#### 3. Missing Dry-Run Mode (ENHANCEMENT)

**Issue:** No way to validate a mosaic plan without executing it.

**Use Case:** User wants to verify:
- All tiles exist
- All PB images exist
- Validation will pass
- Output location is valid
- Resource requirements

**"Measure Twice" Violation:** Must execute to validate plan.

**Fix:** Add `--dry-run` flag that performs all validations without building.

---

#### 4. Missing Output Path Validation (MODERATE)

**Issue:** No upfront validation of output path.

**Current:** Output path checked implicitly when writing (may fail late).

**Missing Checks:**
- Output directory exists or can be created
- Output directory is writable
- Output path doesn't already exist (or warn if overwriting)
- Output path has sufficient space

**"Measure Twice" Violation:** We don't validate output until write time.

**Fix:** Validate output path in pre-flight checks.

---

#### 5. Redundant Tile Existence Checks (MINOR)

**Issue:** Tile existence checked multiple times:
- `validate_tile_quality()` checks existence
- `_find_pb_path()` checks existence
- `_build_weighted_mosaic()` checks existence again

**"Measure Twice" Violation:** We check the same thing multiple times.

**Fix:** Consolidate existence checks in pre-flight validation.

---

#### 6. Missing Tile Count Validation (MINOR)

**Issue:** No validation that tile count is reasonable.

**Missing Checks:**
- Minimum tile count (e.g., warn if < 4 tiles)
- Maximum tile count (e.g., warn if > 1000 tiles - might be planning error)
- Tile overlap validation (do tiles actually overlap?)

**"Measure Twice" Violation:** We don't validate the plan structure.

**Fix:** Add tile count and overlap validation.

---

#### 7. Missing Resource Estimation (ENHANCEMENT)

**Issue:** No upfront estimate of resource requirements.

**Missing:**
- Estimated processing time
- Estimated disk space (more accurate than current)
- Estimated memory requirements
- Number of operations to perform

**"Measure Twice" Violation:** Users don't know what they're committing to.

**Fix:** Add resource estimation before building.

---

#### 8. Validation Order Inefficiency (MINOR)

**Issue:** Validation checks happen in order that may not be optimal.

**Current Order:**
1. Basic grid consistency (fast)
2. Tile quality validation (expensive - reads all tiles)
3. Astrometric check (expensive - catalog queries)
4. Calibration check (moderate - DB queries)
5. PB consistency (moderate - reads PB images)

**Optimization:** Could fail fast on basic checks before expensive ones.

**"Measure Twice" Violation:** We do expensive checks before verifying basic pre-conditions.

**Fix:** Reorder to fail fast on basic checks.

---

## Recommended Implementation Priority

### Priority 1: Pre-Flight Validation (CRITICAL)
- Check all tile files exist before validation
- Check all PB images exist before building
- Check output directory exists/is writable
- Move disk space check to pre-flight
- Validate output path upfront

### Priority 2: Dry-Run Mode (HIGH)
- Add `--dry-run` flag
- Perform all validations without building
- Report resource estimates
- Provide summary of what would be built

### Priority 3: Resource Estimation (MODERATE)
- Estimate processing time
- Estimate disk space more accurately
- Estimate memory requirements
- Report before starting

### Priority 4: Optimization (LOW)
- Consolidate redundant checks
- Reorder validation for fail-fast
- Cache PB path lookups

---

## Implementation Plan

### Phase 1: Pre-Flight Validation Function
```python
def validate_preflight_conditions(
    tiles: List[str],
    output_path: str,
    metrics_dict: Dict[str, TileQualityMetrics],
    require_pb: bool = True,
) -> Tuple[bool, List[str]]:
    """Validate all pre-conditions before expensive operations."""
    issues = []
    
    # Check all tiles exist
    # Check output directory
    # Check PB images exist
    # Check disk space
    # Check write permissions
    
    return len(issues) == 0, issues
```

### Phase 2: Dry-Run Mode
```python
sp.add_argument('--dry-run', action='store_true',
                help='Validate mosaic plan without building')
```

### Phase 3: Resource Estimation
```python
def estimate_resources(
    tiles: List[str],
    output_path: str,
) -> Dict[str, Any]:
    """Estimate resource requirements."""
    return {
        'estimated_disk_gb': ...,
        'estimated_time_minutes': ...,
        'estimated_memory_gb': ...,
        'operations': ...,
    }
```

---

## Conclusion

The pipeline is **functional and well-validated** but could better adhere to "measure twice, cut once" by:

1. **Validating all pre-conditions upfront** before expensive operations
2. **Providing dry-run mode** for plan validation
3. **Estimating resources** before committing to build
4. **Consolidating redundant checks** for efficiency

**Estimated Impact:** 
- Pre-flight validation: Prevents ~90% of late-stage failures
- Dry-run mode: Improves user experience significantly
- Resource estimation: Helps users plan better

**Recommended Next Steps:**
1. Implement pre-flight validation function
2. Add dry-run mode
3. Add resource estimation
4. Refactor to use pre-flight validation throughout

