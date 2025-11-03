# Calibration Stages Precondition Review - "Measure Twice, Cut Once"

**Date:** 2025-11-02  
**Review Scope:** All calibration stages (K → BP → G → Apply)

## Current Precondition Checks

### ✅ Before Calibration Starts (CLI)

1. **MS validation** (cli.py:208-222)
   - ✅ MS exists and is readable
   - ✅ MS is not empty

2. **Field validation** (cli.py:304-332)
   - ✅ Fields exist in MS
   - ✅ Field selection resolves correctly

3. **Reference antenna validation** (cli.py:360-402)
   - ✅ Refant exists in MS
   - ✅ Suggests outrigger antenna if refant invalid

4. **Fast subset validation** (cli.py:426-438)
   - ✅ Subset MS created successfully
   - ✅ Subset MS is readable and not empty

5. **MODEL_DATA population** (cli.py:479-561)
   - ✅ Hard requirement: `--model-source` must be specified
   - ✅ MODEL_DATA population success (hard error if fails)

### ✅ During K-Calibration (`solve_delay`)

1. **MODEL_DATA validation** (calibration.py:105-125)
   - ✅ MODEL_DATA exists
   - ✅ MODEL_DATA is populated (not all zeros)

2. **Field validation** (calibration.py:127-136)
   - ✅ Field selection resolves
   - ✅ Data exists for field

3. **Reference antenna validation** (calibration.py:138-155)
   - ✅ Refant exists in field

4. **Unflagged data check** (calibration.py:157-162)
   - ✅ Sufficient unflagged data available

### ✅ After K-Calibration (IMPLEMENTED)

**Post-solve validation** (calibration.py:252-254, 271-274, 295-298)
- ✅ Verify K-table exists and has solutions
- ✅ Verify refant has solutions in K-table
- ✅ Raises RuntimeError if validation fails (hard error)

### ✅ Before BP-Calibration (`solve_bandpass`)

1. **K-table validation** (calibration.py:265-283)
   - ✅ K-table exists
   - ✅ K-table is compatible with MS
   - ✅ Refant has solutions in K-table

### ✅ After BP-Calibration (IMPLEMENTED)

**Post-solve validation** (calibration.py:393-396, 419-422)
- ✅ Verify BP-amplitude table exists and has solutions (if created)
- ✅ Verify BP-phase table exists and has solutions
- ✅ Verify refant has solutions in both tables
- ✅ Raises RuntimeError if validation fails (hard error)

### ✅ Before G-Calibration (`solve_gains`)

1. **K-table + BP-table validation** (calibration.py:385-405)
   - ✅ Tables exist
   - ✅ Tables are compatible with MS
   - ✅ Refant has solutions in all tables

### ✅ After G-Calibration (IMPLEMENTED)

**Post-solve validation** (calibration.py:520-523, 544-547, 572-576)
- ✅ Verify gain-amplitude table exists and has solutions (if created)
- ✅ Verify gain-phase table exists and has solutions
- ✅ Verify short-timescale gain table exists and has solutions (if created)
- ✅ Verify refant has solutions in all tables
- ✅ Raises RuntimeError if validation fails (hard error)

### ✅ Before Applycal (`apply_to_target`)

1. **Calibration table validation** (applycal.py:30-43)
   - ✅ Tables exist
   - ✅ Tables are compatible with MS

## Implementation Summary

### ✅ Priority 1: Post-Solve Validation (COMPLETED)

**Implementation:** Added `_validate_solve_success()` function (calibration.py:18-74) and integrated it after each calibration solve:

1. **K-calibration** (`solve_delay`):
   - Validates slow delay solve (line 254)
   - Validates retry delay solve (line 274)
   - Validates fast delay solve (line 298)

2. **BP-calibration** (`solve_bandpass`):
   - Validates amplitude solve (line 396)
   - Validates phase solve (line 422)

3. **G-calibration** (`solve_gains`):
   - Validates amplitude solve (line 523)
   - Validates phase solve (line 547)
   - Validates short-timescale solve (line 576)

**Validation Checks:**
- Table exists
- Table has solutions (nrows > 0)
- Reference antenna has solutions (if provided)

**Error Handling:**
- Raises `RuntimeError` with clear error messages
- Prevents proceeding to next step if validation fails
- Provides actionable error messages (e.g., lists available antennas if refant missing)

## Remaining Considerations

### ⚠️ Medium: Post-Flagging Validation

**Issue:** After flagging completes, we don't verify that sufficient unflagged data remains for calibration.

**Risk:**
- Flagging might flag too much data
- Calibration proceeds with insufficient data
- Calibration fails or produces poor solutions

**Fix Required:**
```python
# After flagging, check unflagged data fraction
if not args.no_flagging:
    reset_flags(ms_in)
    flag_zeros(ms_in)
    flag_rfi(ms_in)
    
    # PRECONDITION CHECK: Verify sufficient unflagged data remains
    from casacore.tables import table
    import numpy as np
    with table(ms_in, readonly=True) as tb:
        flags = tb.getcol('FLAG')
        total_points = flags.size
        unflagged_points = np.sum(~flags)
        unflagged_fraction = unflagged_points / total_points if total_points > 0 else 0.0
        
        if unflagged_fraction < 0.1:  # Less than 10% unflagged
            p.error(
                f"Insufficient unflagged data after flagging: {unflagged_fraction*100:.1f}%. "
                f"Calibration requires at least 10% unflagged data."
            )
```

### ⚠️ Medium: MODEL_DATA Flux Validation

**Issue:** We validate MODEL_DATA exists and is populated, but don't verify it has reasonable flux values.

**Risk:**
- MODEL_DATA might have unrealistic flux (e.g., 1e-10 Jy or 1e10 Jy)
- Calibration proceeds with incorrect model
- Solutions are unreliable

**Fix Required:**
```python
# After MODEL_DATA population, validate flux values
with table(ms, readonly=True) as tb:
    model_sample = tb.getcol("MODEL_DATA", startrow=0, nrow=min(1000, tb.nrows()))
    model_amps = np.abs(model_sample[~np.isnan(model_sample) & (model_sample != 0)])
    if len(model_amps) > 0:
        median_flux = np.median(model_amps)
        if median_flux < 1e-6:  # Less than 1 microJy
            logger.warning(f"MODEL_DATA has very low flux: {median_flux:.2e} Jy")
        if median_flux > 1e6:  # More than 1 MJy
            logger.warning(f"MODEL_DATA has very high flux: {median_flux:.2e} Jy")
```

### ⚠️ Low: Data Coverage Validation

**Issue:** We don't verify sufficient time/frequency coverage before calibration.

**Risk:**
- Insufficient time coverage for time-dependent calibration
- Insufficient frequency coverage for bandpass calibration
- Solutions are unreliable

**Fix Required:**
```python
# Before calibration, check data coverage
with table(ms, readonly=True) as tb:
    times = tb.getcol('TIME')
    unique_times = len(np.unique(times))
    time_span = (times.max() - times.min()) * 86400  # seconds
    
    if unique_times < 3:
        raise ValueError(f"Insufficient time coverage: only {unique_times} unique times")
    
    if time_span < 60:  # Less than 1 minute
        logger.warning(f"Very short time coverage: {time_span:.1f} seconds")
```

## Summary

### ✅ Well Covered
- MS/field/refant validation before calibration
- MODEL_DATA validation before K-calibration
- Calibration table validation before use
- Calibration table compatibility checks
- **Post-solve validation after each solve** (IMPLEMENTED)

### ⚠️ Missing Medium Priority Checks
1. Post-flagging validation (verify sufficient unflagged data remains)
2. MODEL_DATA flux validation (verify reasonable flux values)

### ⚠️ Missing Low Priority Checks
3. Data coverage validation (verify sufficient time/frequency coverage)

## Recommended Next Steps

**Priority 2:**
1. Post-flagging validation (verify sufficient unflagged data)

**Priority 3:**
2. MODEL_DATA flux validation (warn on unrealistic values)
3. Data coverage validation (warn on insufficient coverage)
