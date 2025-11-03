# Medium Priority Precondition Checks Implementation

**Date:** 2025-11-02  
**Status:** COMPLETED

## Summary

Implemented medium priority precondition checks for post-flagging validation, MODEL_DATA flux validation, and imaging disk space checks.

## Implementation Details

### 1. Post-Flagging Validation ✅

**File:** `src/dsa110_contimg/calibration/cli.py` (lines 450-482)

**Changes:**
- Added validation after flagging completes (after `reset_flags`, `flag_zeros`, `flag_rfi`)
- Checks fraction of unflagged data remaining
- **Hard error** if < 10% unflagged (raises `p.error`)
- **Warning** if 10-30% unflagged (logs warning, continues)
- **Info** if ≥ 30% unflagged (logs success message)

**Behavior:**
- Runs automatically after flagging if `--no-flagging` is not set
- Prevents calibration from proceeding if insufficient data remains
- Provides actionable error messages

**Thresholds:**
- Error: < 10% unflagged data
- Warning: 10-30% unflagged data
- Success: ≥ 30% unflagged data

### 2. MODEL_DATA Flux Validation ✅

**File:** `src/dsa110_contimg/calibration/cli.py` (lines 602-641)

**Changes:**
- Added validation after MODEL_DATA population (before K-calibration)
- Samples up to 10,000 rows to check flux values
- Checks median, min, and max flux values
- **Warning** if median flux < 1 μJy or > 1 MJy
- **Info** if flux values are reasonable

**Behavior:**
- Runs automatically after MODEL_DATA population if K-calibration is enabled
- Non-fatal (logs warnings, doesn't fail calibration)
- Provides diagnostic information about flux values

**Thresholds:**
- Warning: median flux < 1e-6 Jy (1 microJy) or > 1e6 Jy (1 MJy)
- Success: median flux in reasonable range

### 3. Imaging Disk Space Check ✅

**File:** `src/dsa110_contimg/imaging/cli.py` (lines 422-455)

**Changes:**
- Added disk space check before imaging operations
- Estimates image size based on `imsize` parameter
- Accounts for multiple image products (.image, .model, .residual, .pb, .pbcor, etc.)
- Uses 10x safety margin for overhead
- **Warning** if insufficient space (logs warning, continues)
- **Info** if sufficient space (logs success message)

**Behavior:**
- Runs automatically before any imaging operations
- Non-fatal (logs warnings, doesn't fail imaging)
- Creates output directory if it doesn't exist

**Estimation:**
- Formula: `imsize^2 * 4 bytes * 10 images * 10x margin`
- Accounts for: .image, .model, .residual, .pb, .pbcor, weights, and overhead

## Testing

All code compiles successfully:
- ✅ `calibration/cli.py` - no syntax errors
- ✅ `imaging/cli.py` - no syntax errors

## Impact

### Benefits
1. **Prevents wasted time**: Post-flagging validation catches over-flagging before calibration
2. **Early detection**: MODEL_DATA flux validation catches unrealistic models early
3. **Resource awareness**: Disk space check prevents imaging failures due to insufficient space
4. **Clear diagnostics**: All checks provide actionable information

### Behavior
- **Post-flagging**: Hard error if < 10% unflagged (prevents calibration)
- **MODEL_DATA flux**: Warning only (non-fatal, allows calibration)
- **Disk space**: Warning only (non-fatal, allows imaging)

## Next Steps

**Priority 3 (Low):**
- Field validation before imaging (verify field selection exists)
- Image parameter validation (verify imsize/cell size reasonable)
- Data coverage validation (verify sufficient time/frequency coverage)

