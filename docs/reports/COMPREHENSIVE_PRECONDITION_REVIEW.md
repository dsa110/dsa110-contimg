# Final Comprehensive Precondition Review - "Measure Twice, Cut Once"

**Date:** 2025-11-02  
**Status:** Complete pipeline review

## Summary of All Implemented Checks

### ✅ Conversion Pipeline (HDF5 → MS) - COMPLETE
- Input/output/scratch directory validation
- File existence/readability validation
- Disk space checks
- MS write validation
- Partial file cleanup

### ✅ Calibration Pipeline - COMPLETE
- MS/field/refant validation
- MODEL_DATA validation
- Pre-solve validation (tables exist/compatible)
- **Post-solve validation (solutions exist)** - IMPLEMENTED
- Applycal validation (tables exist/compatible)

### ⚠️ Imaging Pipeline - PARTIAL REVIEW

**Current Checks:**
- Detects datacolumn (CORRECTED_DATA vs DATA) - lines 56-91
- Estimates cell size from UV extents - lines 94-126
- Validates WSClean executable exists - lines 177-195

**Missing Checks:**

1. **MS Existence/Readability** (Priority: High)
   - No validation that MS exists before expensive operations
   - No check that MS is readable
   - No check that MS has data rows

2. **Post-Applycal Validation** (Priority: High)
   - No verification that CORRECTED_DATA was populated after applycal
   - If CORRECTED_DATA is empty/all zeros, imaging proceeds with wrong column
   - Current detection (lines 56-91) only samples, doesn't validate fully

3. **Disk Space Check** (Priority: Medium)
   - No check for available disk space before imaging
   - Images can be large (several GB)
   - Risk of partial/failed images

4. **Image Parameter Validation** (Priority: Low)
   - No validation that image size is reasonable
   - No validation that cell size is reasonable
   - No validation that field selection exists

### ⚠️ Post-Applycal Validation - MISSING

**Issue:** After `applycal` completes, we don't verify that CORRECTED_DATA was actually populated successfully.

**Current Behavior:**
- `applycal.py` validates tables exist/compatible before applying
- `apply_service.py` has optional verification (lines 282-286) but it's not enforced
- Imaging CLI detects datacolumn but doesn't validate CORRECTED_DATA quality

**Risk:**
- CORRECTED_DATA might be empty/all zeros (applycal failed silently)
- Imaging proceeds with wrong column (DATA instead of CORRECTED_DATA)
- Poor quality images without user realizing

**Fix Required:**
```python
# After applycal, verify CORRECTED_DATA is populated
def verify_corrected_data_populated(ms_path: str, min_fraction: float = 0.01) -> bool:
    """Verify CORRECTED_DATA column is populated.
    
    Args:
        ms_path: Path to MS
        min_fraction: Minimum fraction of data that must be non-zero
    
    Returns:
        True if CORRECTED_DATA is populated, False otherwise
    """
    from casacore.tables import table
    import numpy as np
    
    with table(ms_path, readonly=True) as tb:
        if "CORRECTED_DATA" not in tb.colnames():
            return False
        
        # Sample data
        n_rows = tb.nrows()
        if n_rows == 0:
            return False
        
        sample_size = min(10000, n_rows)
        sample = tb.getcol("CORRECTED_DATA", startrow=0, nrow=sample_size)
        flags = tb.getcol("FLAG", startrow=0, nrow=sample_size)
        
        # Check unflagged data
        unflagged = sample[~flags]
        if len(unflagged) == 0:
            return False
        
        # Check fraction non-zero
        non_zero_fraction = np.sum(np.abs(unflagged) > 1e-10) / len(unflagged)
        return non_zero_fraction >= min_fraction
```

### ⚠️ Imaging Precondition Checks - MISSING

**1. MS Validation (Priority: High)**
```python
# At start of imaging CLI
if not os.path.exists(args.ms):
    parser.error(f"MS does not exist: {args.ms}")

try:
    with table(args.ms, readonly=True) as tb:
        if tb.nrows() == 0:
            parser.error(f"MS is empty: {args.ms}")
        # Verify required columns exist
        required_cols = ['DATA', 'ANTENNA1', 'ANTENNA2', 'TIME', 'UVW']
        missing_cols = [c for c in required_cols if c not in tb.colnames()]
        if missing_cols:
            parser.error(f"MS missing required columns: {missing_cols}")
except Exception as e:
    parser.error(f"MS is not readable: {args.ms}. Error: {e}")
```

**2. Disk Space Check (Priority: Medium)**
```python
# Before imaging, estimate image size and check disk space
image_size_estimate = estimate_image_size(args.ms, args.imsize, args.cell)
available_space = shutil.disk_usage(os.path.dirname(args.imagename)).free

if available_space < image_size_estimate * 2:  # 2x safety margin
    parser.error(
        f"Insufficient disk space for images: need ~{image_size_estimate/1e9:.1f}GB, "
        f"available {available_space/1e9:.1f}GB"
    )
```

**3. Field Validation (Priority: Low)**
```python
# Validate field selection exists in MS
if args.field:
    try:
        from dsa110_contimg.calibration.selection import _resolve_field_ids
        field_ids = _resolve_field_ids(args.ms, args.field)
        if not field_ids:
            parser.error(f"Field selection not found in MS: {args.field}")
    except Exception as e:
        parser.error(f"Field validation failed: {e}")
```

## Summary

### ✅ Fully Covered
- Conversion pipeline (all checks implemented)
- Calibration pipeline (all checks implemented, including post-solve validation)
- Applycal preconditions (tables validated before applying)

### ⚠️ Missing High Priority
1. **Post-applycal validation** - Verify CORRECTED_DATA populated after applycal
2. **Imaging MS validation** - Verify MS exists/readable before imaging

### ⚠️ Missing Medium Priority
3. **Imaging disk space check** - Verify sufficient space before imaging

### ⚠️ Missing Low Priority
4. **Imaging field validation** - Verify field selection exists
5. **Imaging parameter validation** - Verify image size/cell size reasonable

## Recommended Next Steps

**Priority 1:**
1. Post-applycal validation (verify CORRECTED_DATA populated)
2. Imaging MS validation (verify MS exists/readable)

**Priority 2:**
3. Imaging disk space check

**Priority 3:**
4. Imaging field validation
5. Imaging parameter validation

