# Pre-Calibration Precondition Review - "Measure Twice, Cut Once"

**Date:** 2025-11-02  
**Review Scope:** All steps before calibration solve operations

## Overview

This document reviews all preconditions that should be checked before expensive calibration operations, following the "measure twice, cut once" philosophy.

## Current Precondition Checks

### ✅ Already Implemented

1. **MODEL_DATA population** (cli.py:431-442)
   - ✅ Hard requirement: `--model-source` must be specified
   - ✅ Checked in `solve_delay()` (calibration.py:108-125)

2. **K-calibration preconditions** (calibration.py:102-163)
   - ✅ MODEL_DATA exists and is populated
   - ✅ Field selection resolves correctly
   - ✅ Data exists for selected field
   - ✅ Reference antenna exists in field
   - ✅ Unflagged data available

3. **BP-calibration preconditions** (calibration.py:265-283)
   - ✅ K-table exists and is compatible (if provided)
   - ✅ K-table refant validation

4. **G-calibration preconditions** (calibration.py:385-405)
   - ✅ K-table and BP-tables exist and are compatible
   - ✅ Calibration table refant validation

5. **Applycal preconditions** (applycal.py:30-43)
   - ✅ Calibration tables exist and are compatible

## Missing Precondition Checks

### ❌ Critical: MS Validation

**Location:** `cli.py:207` (entry point)

**Issue:** No validation that MS exists and is readable before proceeding.

**Risk:** Expensive operations (field selection, flagging, subset creation) may fail after significant time.

**Fix Required:**
```python
# At start of calibrate command
if not os.path.exists(args.ms):
    p.error(f"MS does not exist: {args.ms}")

# Try to open MS to verify it's readable
try:
    from casacore.tables import table
    with table(args.ms, readonly=True) as tb:
        nrows = tb.nrows()
        if nrows == 0:
            p.error(f"MS is empty: {args.ms}")
except Exception as e:
    p.error(f"MS is not readable: {args.ms}. Error: {e}")
```

### ❌ Critical: Reference Antenna Validation

**Location:** `cli.py:307-308` (after refant selection)

**Issue:** No validation that refant exists in MS before proceeding.

**Risk:** All calibration operations will fail after field selection, flagging, MODEL_DATA population.

**Fix Required:**
```python
# After refant selection, validate refant exists in MS
from casacore.tables import table
with table(ms_in, readonly=True) as tb:
    ant1 = tb.getcol('ANTENNA1')
    ant2 = tb.getcol('ANTENNA2')
    all_antennas = set(ant1) | set(ant2)
    refant_int = int(refant) if isinstance(refant, str) else refant
    if refant_int not in all_antennas:
        p.error(
            f"Reference antenna {refant} not found in MS. "
            f"Available antennas: {sorted(all_antennas)}"
        )
```

### ❌ Critical: Field Validation

**Location:** `cli.py:285-286` (after field selection)

**Issue:** No validation that selected field(s) exist in MS before proceeding.

**Risk:** All calibration operations will fail after flagging, MODEL_DATA population.

**Fix Required:**
```python
# After field selection, validate fields exist in MS
from casacore.tables import table
with table(ms_in, readonly=True) as tb:
    field_ids = tb.getcol('FIELD_ID')
    available_fields = sorted(set(field_ids))
    
    # Resolve field selection
    target_ids = _resolve_field_ids(ms_in, field_sel)
    if not target_ids:
        p.error(f"Unable to resolve field selection: {field_sel}")
    
    missing_fields = set(target_ids) - set(available_fields)
    if missing_fields:
        p.error(
            f"Selected fields not found in MS: {sorted(missing_fields)}. "
            f"Available fields: {available_fields}"
        )
```

### ⚠️ Medium: MODEL_DATA Population Success

**Location:** `cli.py:443-446` (after MODEL_DATA population)

**Issue:** Exception during MODEL_DATA population is caught but only prints warning. Calibration proceeds anyway.

**Risk:** K-calibration may fail or produce unreliable results.

**Current Behavior:**
```python
except Exception as e:
    print("MODEL_DATA population failed: {}. K-calibration may be unreliable.".format(e))
# Calibration proceeds anyway
```

**Fix Required:** Make MODEL_DATA population failure a hard error (unless `--skip-k`):
```python
except Exception as e:
    if not args.skip_k:
        p.error(
            f"MODEL_DATA population failed: {e}. "
            f"This is required for K-calibration. Fix the error and retry."
        )
    else:
        print(f"MODEL_DATA population failed: {e}. Skipping K-calibration as requested.")
```

### ⚠️ Medium: Fast Subset MS Validation

**Location:** `cli.py:313-329` (fast subset creation)

**Issue:** No validation that subset MS was created successfully or is readable.

**Risk:** Calibration proceeds with original MS instead of subset, causing confusion.

**Fix Required:**
```python
if args.fast and (args.timebin or args.chanbin):
    # ... create subset ...
    # Validate subset was created
    if not os.path.exists(ms_fast):
        p.error(f"Fast subset MS creation failed: {ms_fast}")
    
    # Verify subset is readable
    try:
        from casacore.tables import table
        with table(ms_fast, readonly=True) as tb:
            if tb.nrows() == 0:
                p.error(f"Fast subset MS is empty: {ms_fast}")
    except Exception as e:
        p.error(f"Fast subset MS is not readable: {ms_fast}. Error: {e}")
```

### ⚠️ Low: Catalog File Validation

**Location:** `cli.py:214` (catalog path)

**Issue:** No validation that catalog file exists before calling `select_bandpass_from_catalog`.

**Risk:** Field selection fails after some processing.

**Fix Required:**
```python
if args.cal_catalog:
    if not os.path.exists(args.cal_catalog):
        p.error(f"Calibrator catalog not found: {args.cal_catalog}")
```

### ⚠️ Low: Refant Ranking File Validation

**Location:** `cli.py:290-306` (refant ranking)

**Issue:** Exception during ranking file read is caught but only prints warning. Falls back to `--refant`.

**Risk:** If `--refant` is also None, fails late. Otherwise, proceeds with potentially wrong refant.

**Current Behavior:**
```python
except Exception as e:
    print("Failed to read refant ranking ({}); falling back to --refant".format(e))
# Falls back to --refant (which may be None)
```

**Fix Required:** More explicit error handling:
```python
except Exception as e:
    if args.refant is None:
        p.error(
            f"Failed to read refant ranking ({e}) and --refant not provided. "
            f"Provide one or the other."
        )
    print(f"Failed to read refant ranking ({e}); using --refant={args.refant}")
```

## Recommended Implementation Order

### Priority 1: Critical Preconditions (Fail Fast)

1. **MS existence and readability** - Check immediately at entry point
2. **Reference antenna validation** - Check after refant selection, before any calibration
3. **Field validation** - Check after field selection, before any calibration
4. **MODEL_DATA population success** - Hard error if K-calibration is enabled

### Priority 2: Medium Preconditions (Prevent Confusion)

5. **Fast subset MS validation** - Verify subset was created successfully
6. **Catalog file validation** - Verify catalog exists before field selection

### Priority 3: Low Preconditions (Better Error Messages)

7. **Refant ranking file validation** - Better error messages if file missing

## Summary

**Current State:** Good precondition checks during calibration solve operations, but missing critical checks at the CLI entry point.

**Missing Critical Checks:**
- MS existence and readability
- Reference antenna presence in MS
- Field existence in MS
- MODEL_DATA population success (currently warning only)

**Impact:** Calibration may fail after expensive operations (flagging, MODEL_DATA population, subset creation), wasting time and causing confusion.

**Recommendation:** Implement Priority 1 checks immediately to ensure we "measure twice" before any expensive operations.

