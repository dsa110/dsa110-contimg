# CASA Table Open Messages Explained

**Date:** 2025-11-05  
**Context:** Understanding "Successful readonly open" messages in calibration output

---

## Message Format

```
Successful readonly open of default-locked table /data/ms/2025-10-29T13:54:17.ms: 27 columns, 1787904 rows
```

This message is printed by **CASA's `casacore.tables`** library whenever a Measurement Set table is opened with `readonly=True`. It's a standard CASA diagnostic message, not an error.

---

## Origins in Calibration Pipeline

When you see **4 identical messages** (lines 957-960), they come from these **precondition checks** in the calibration pipeline:

### 1. Post-Flagging Validation (Line 1043)
**File:** `src/dsa110_contimg/calibration/cli.py`  
**Location:** After flagging completes, before calibration solves  
**Purpose:** Verify sufficient unflagged data remains after flagging  
**Code:**
```python
with table(ms_in, readonly=True) as tb:
    flags_sample = tb.getcol('FLAG', startrow=0, nrow=sample_size)
    # Check unflagged fraction
```

### 2. MODEL_DATA Flux Validation (Line 1492)
**File:** `src/dsa110_contimg/calibration/cli.py`  
**Location:** After MODEL_DATA population, before calibration  
**Purpose:** Verify MODEL_DATA has reasonable flux values  
**Code:**
```python
with table(ms_in, readonly=True) as tb:
    model_sample = tb.getcol("MODEL_DATA", startrow=0, nrow=sample_size)
    # Check median flux values
```

### 3. MODEL_DATA Precondition Check in `solve_gains` (Line 704)
**File:** `src/dsa110_contimg/calibration/calibration.py`  
**Location:** At start of `solve_gains()` function  
**Purpose:** Verify MODEL_DATA exists and is populated before gain solve  
**Code:**
```python
with table(ms) as tb:
    if "MODEL_DATA" not in tb.colnames():
        raise ValueError(...)
    model_sample = tb.getcol("MODEL_DATA", startrow=0, nrow=min(100, tb.nrows()))
```

### 4. Possible Additional Validation
**Potential sources:**
- `validate_caltables_for_use()` (line 732 in `calibration.py`) - validates bandpass tables
  - This calls `validate_caltable_compatibility()` which opens MS **subtables** (ANTENNA, SPECTRAL_WINDOW, DATA_DESCRIPTION), not the main MS table
- Another precondition check in the calibration flow

---

## Why These Messages Appear

These messages are part of CASA's **"measure twice, cut once"** philosophy implemented in the pipeline:

1. **Precondition Checks:** Verify data quality before expensive operations
2. **Early Failure:** Catch issues before calibration solves (saves time)
3. **Validation:** Ensure MODEL_DATA is correct before using it

---

## Are These Messages a Problem?

**No.** These are normal, expected diagnostic messages. They indicate:
- ✅ The MS is being read correctly
- ✅ Precondition checks are running
- ✅ The pipeline is validating data quality

**The messages show:**
- `27 columns`: The MS has 27 data columns (DATA, MODEL_DATA, CORRECTED_DATA, FLAG, etc.)
- `1787904 rows`: The MS has ~1.8 million visibility rows
- `default-locked`: CASA's table locking mechanism (read-only access)

---

## Can These Messages Be Suppressed?

**Yes**, but not recommended. These messages help with:
- Debugging: Confirming which validation steps ran
- Diagnostics: Understanding when the MS is accessed
- Troubleshooting: Identifying if validation is running

If you want to suppress them, you can:
1. Set `ack=False` when opening tables (suppresses CASA messages)
2. Redirect CASA log output
3. Use CASA's logging configuration

**However**, suppressing these messages makes debugging harder, so it's generally better to leave them enabled.

---

## Related Code Locations

### Main MS Table Opens (readonly=True)
- `src/dsa110_contimg/calibration/cli.py:978` - Dry-run flagging estimate
- `src/dsa110_contimg/calibration/cli.py:1043` - Post-flagging validation
- `src/dsa110_contimg/calibration/cli.py:1492` - MODEL_DATA flux validation
- `src/dsa110_contimg/calibration/calibration.py:704` - MODEL_DATA precondition in `solve_gains`

### MS Subtable Opens (readonly=True)
- `src/dsa110_contimg/calibration/validate.py:94` - ANTENNA table
- `src/dsa110_contimg/calibration/validate.py:107` - SPECTRAL_WINDOW table
- `src/dsa110_contimg/calibration/validate.py:116` - DATA_DESCRIPTION table
- `src/dsa110_contimg/calibration/cli.py:1162` - FIELD table (rephasing check)
- `src/dsa110_contimg/calibration/cli.py:1324` - FIELD table (after rephasing)

---

## Summary

The 4 identical "Successful readonly open" messages come from:
1. ✅ Post-flagging data quality validation
2. ✅ MODEL_DATA flux validation
3. ✅ MODEL_DATA precondition check in `solve_gains`
4. ✅ Possibly another validation step

These are **normal, expected diagnostic messages** indicating the pipeline is correctly validating data quality before proceeding with calibration. They are not errors and do not indicate any problems.

