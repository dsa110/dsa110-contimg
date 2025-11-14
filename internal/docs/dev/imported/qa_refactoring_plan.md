# QA System Refactoring Plan - Phase 3

**Date:** November 11, 2025  
**Goal:** Refactor existing validators to use new patterns while maintaining backward compatibility

## Strategy

**Approach:** Create wrapper/adapter functions that use new patterns internally while keeping existing APIs unchanged. This ensures:
- ✅ No breaking changes
- ✅ Gradual migration path
- ✅ New code uses new patterns
- ✅ Existing code continues to work

## Files to Refactor

### Priority 1: Core Validators (Most Used)

1. **`catalog_validation.py`** (1,051 lines)
   - `validate_astrometry()` → Use `AstrometryConfig`
   - `validate_flux_scale()` → Use `FluxScaleConfig`
   - `validate_source_counts()` → Use `SourceCountsConfig`
   - Return types: Custom dataclasses → Keep, but add `ValidationResult` conversion

2. **`image_quality.py`** (390 lines)
   - `validate_image_quality()` → Use `ImageQualityConfig`
   - `quick_image_check()` → Use new error handling
   - Return types: `ImageQualityMetrics` / `Tuple[bool, str]` → Keep, add conversion

3. **`ms_quality.py`** (351 lines)
   - `validate_ms_quality()` → Use centralized config
   - `quick_ms_check()` → Use new error handling
   - Return types: `MsQualityMetrics` / `Tuple[bool, str]` → Keep, add conversion

### Priority 2: Calibration Validators

4. **`calibration_quality.py`** (1,774 lines)
   - `validate_caltable_quality()` → Use `CalibrationConfig`
   - `check_caltable_completeness()` → Use new error handling
   - `check_corrected_data_quality()` → Use new error handling
   - Return types: Mixed → Standardize

## Refactoring Steps

### Step 1: Add Configuration Support (Non-Breaking)

For each validator function:
1. Add optional `config` parameter (defaults to `get_default_config().<type>`)
2. Use config values instead of hardcoded thresholds
3. Keep existing function signatures unchanged

### Step 2: Standardize Error Handling (Non-Breaking)

1. Wrap existing error handling in try/except
2. Raise `ValidationError` subclasses instead of generic exceptions
3. Keep return types unchanged (backward compatibility)

### Step 3: Add Result Conversion (New Feature)

1. Add helper functions to convert existing result types to `ValidationResult`
2. Make conversion optional (don't break existing code)
3. Use in new code paths

### Step 4: Update Pipeline Integration

1. Update `pipeline_quality.py` to use new config
2. Add new validations to pipeline stages
3. Update HTML report generation

## Implementation Order

1. ✅ **`image_quality.py`** - Smallest, simplest (390 lines)
2. ✅ **`ms_quality.py`** - Similar pattern (351 lines)
3. ✅ **`catalog_validation.py`** - Most complex, but critical (1,051 lines)
4. ✅ **`calibration_quality.py`** - Large, but less critical (1,774 lines)

## Backward Compatibility Guarantees

- ✅ All existing function signatures remain unchanged
- ✅ All existing return types remain unchanged
- ✅ All existing behavior preserved
- ✅ New features are opt-in (via optional parameters)

## Testing Strategy

1. **Unit Tests:** Test that existing functions still work
2. **Integration Tests:** Test with pipeline
3. **Regression Tests:** Ensure no behavior changes

