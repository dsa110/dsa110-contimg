# Full SPW Flagging Process in the DSA-110 Pipeline

**Date:** 2025-11-19  
**Type:** Technical Documentation  
**Status:** ✅ Complete

---

## Overview

This document describes the **complete flagging timeline** in the DSA-110
pipeline, focusing on when and how full SPWs become flagged.

**Key Point:** Most flagging happens **BEFORE calibration** (RFI, bad channels).
Full SPW flagging happens **DURING calibration application** when calibration
solutions are missing for certain SPWs.

## CASA's Automatic Flagging Behavior

From CASA's `applycal` documentation:

> **"Applycal will overwrite existing corrected data, and will flag data for
> which there is no calibration available."**

This means: **When `applycal` cannot find calibration solutions for an SPW, it
automatically flags 100% of the data in that SPW.**

---

## Complete Flagging Timeline

### Phase 1: Pre-Calibration Flagging (BEFORE Solve)

**File:** `src/dsa110_contimg/src/dsa110_contimg/pipeline/stages_impl.py`

**Location:** Lines 834-844

**What happens:**

1. **Reset flags** - Clear any existing flags

   ```python
   reset_flags(ms_path)
   ```

2. **Flag zeros** - Flag zero-valued visibilities

   ```python
   flag_zeros(ms_path)
   ```

3. **RFI flagging** - Flag radio frequency interference

   ```python
   flag_rfi(ms_path)  # Uses AOFlagger or CASA tfcrop+rflag
   ```

4. **Channel-level analysis** - Identify and flag problematic channels

   ```python
   # From cli_calibrate.py lines 1434-1441
   problematic_channels = analyze_channel_flagging_stats(ms_path, threshold=0.5)
   flag_problematic_channels(ms_path, problematic_channels, datacolumn="DATA")
   ```

5. **Optional: Flag autocorrelations**

**Result:** Individual channels are flagged across all SPWs based on RFI and
quality issues. This is **per-channel flagging**, not full SPW flagging.

**Example:** SPW 1 might have 93% of its data flagged, but it's **not** 100%
flagged yet.

### Phase 2: Calibration Solve (WHY Some SPWs Fail)

**What happens:**

- Calibration attempts to solve for **all SPWs** (0-15 in your case)
- SPWs with **too much pre-calibration flagging** fail to produce solutions
- If a reference antenna has no valid data in an SPW, that SPW fails
- No calibration table entries created for failed SPWs (e.g., 9, 14, 15)

**Why SPWs 9, 14, 15 failed (DEFINITIVE):**

After diagnostic analysis:

- **Pre-calibration flagging:** 100.0% (all data flagged before calibration)
- **Reference antenna 103:** 100% flagged in these SPWs
- **Calibration tables:** Confirmed NO SOLUTIONS for SPWs 9, 14, 15

**DEFINITIVE CAUSE:** Reference antenna 103 was fully flagged in SPWs 9, 14, 15
during pre-calibration RFI/quality flagging (Phase 1), making calibration solve
impossible.

**Result:** Calibration tables (K, BP, G) contain solutions for SPWs 0-8, 10-13
but **NOT** for SPWs 9, 14, 15.

### Phase 3: Calibration Application (WHEN Full SPW Flagging Occurs)

**File:** `src/dsa110_contimg/src/dsa110_contimg/calibration/applycal.py`

**Location:** Lines 153-155

**What happens:**

```python
from casatasks import applycal as casa_applycal
casa_applycal(vis=ms_path, gaintable=[k_table, bp_table, g_table], ...)
```

- CASA `applycal` looks for calibration solutions for each SPW
- **For SPWs 9, 14, 15:** No solutions found → CASA **automatically flags 100%
  of data**
- **For SPWs 0-8, 10-13:** Solutions applied → data calibrated (with existing
  per-channel flags preserved)

**Result:** SPWs 9, 14, 15 are now **100% flagged** (full SPW flagging).

**Warning message you saw:**

```
The following MS spws have no corresponding cal spws in 2025-10-19T14:31:45_0~23_bpcal: 9 14 15
The following MS spws have no corresponding cal spws in 2025-10-19T14:31:45_0~23_gpcal: 9 14 15
The following MS spws have no corresponding cal spws in 2025-10-19T14:31:45_0~23_2gcal: 9 14 15
```

---

## Where It Happens in the Pipeline

### 1. Calibration Table Validation (Detection Phase)

**File:** `src/dsa110_contimg/src/dsa110_contimg/calibration/validate.py`

**Function:** `validate_caltable_compatibility()` (lines 57-242)

**What happens:**

- Pipeline checks if all MS SPWs have corresponding solutions in calibration
  tables
- If missing SPWs are detected, it logs a **warning** but does NOT fail
- Warning message:
  ```
  MS has N SPWs not in calibration table: [9, 14, 15]
  ```

**Code location:**

```python
# validate.py lines 208-227
missing_spws = ms_spw_ids - cal_spw_ids
if missing_spws:
    if len(cal_spw_ids) == 0:
        # No SPWs in caltable - this is critical
        raise ValueError(
            f"Calibration table has no SPW solutions: {caltable_path}"
        )
    elif len(missing_spws) == len(ms_spw_ids):
        # All MS SPWs missing - this is critical
        raise ValueError(
            f"Calibration table has no solutions for any MS SPWs. "
            f"MS SPWs: {sorted(ms_spw_ids)}, "
            f"Cal table SPWs: {sorted(cal_spw_ids)}"
        )
    else:
        # Partial coverage - warn but allow
        warnings.append(
            f"MS has {len(missing_spws)} SPWs not in calibration table: "
            f"{sorted(missing_spws)}"
        )
```

### 2. Calibration Application (Flagging Phase)

**File:** `src/dsa110_contimg/src/dsa110_contimg/calibration/applycal.py`

**Function:** `apply_to_target()` (lines 83-162)

**What happens:**

- CASA's `applycal` is called with calibration tables
- For SPWs without calibration solutions, CASA **automatically flags 100% of the
  data**
- No explicit flagging command needed—this is CASA's built-in behavior

**Code location:**

```python
# applycal.py lines 153-155
from casatasks import applycal as casa_applycal

casa_applycal(**kwargs)
```

**Key parameters passed:**

- `vis`: Measurement Set path
- `field`: Field selection
- `gaintable`: List of calibration tables (K, BP, G)
- `interp`: Interpolation method per table
- `spwmap`: SPW mapping (if using combine_spw)

### 3. Result Verification

After `applycal`, the pipeline verifies `CORRECTED_DATA` was populated:

```python
# applycal.py lines 157-161
if verify:
    _verify_corrected_data_populated(ms_target)
```

This ensures calibration was applied successfully to SPWs with solutions.

---

## Conditions That Trigger Full SPW Flagging

### Condition 1: Missing Calibration Solutions

**Cause:** Calibration failed or was incomplete for certain SPWs

**Examples:**

- Reference antenna (e.g., antenna 103) had no valid data for SPW 9, 14, 15
- SPW was entirely flagged before calibration (100% RFI)
- Calibration solve failed due to insufficient S/N

**Result:** SPWs 9, 14, 15 have NO entries in calibration tables

### Condition 2: SPW Mapping Mismatch

**Cause:** When using `combine_spw=True` in bandpass calibration, all SPWs are
combined into SPW 0

**Handling:** Pipeline uses `spwmap` parameter to map MS SPWs → calibration SPW
0

**Code:** `src/dsa110_contimg/src/dsa110_contimg/calibration/calibration.py`
(lines 257-298)

### Condition 3: Intentional Exclusion

**Cause:** User or pipeline explicitly excludes SPWs from calibration

**Methods:**

- **Pre-calibration flagging:** Flag entire SPWs before solve
- **SPW selection in calibrate tasks:** Only calibrate specific SPWs
- **Manual flagging:** Use `flag_manual(spw='9,14,15')`

---

## Two Levels of Flagging

The DSA-110 pipeline uses **channel-level flagging** (happens BEFORE
calibration) and **SPW-level flagging** (happens DURING calibration application
as fallback):

### Level 1: Per-Channel Flagging (BEFORE Calibration - Preferred)

**File:** `src/dsa110_contimg/src/dsa110_contimg/calibration/flagging.py`

**Functions:**

- `analyze_channel_flagging_stats()` (lines 730-798)
- `flag_problematic_channels()` (lines 801-856)

**Process (BEFORE calibration solve):**

1. RFI flagging identifies problematic channels within SPWs
2. Only flag individual channels (e.g., channel 5 in SPW 1)
3. Preserves good channels within partially-affected SPWs

**Threshold:** Default 50% flagging → channel marked problematic

**Timing:** This happens in **Phase 1** (Pre-Calibration Flagging)

**Example output:**

```
SPW 1: Channel 0 is 98.2% flagged
SPW 1: Channel 1 is 87.7% flagged
SPW 12: Channel 0 is 12.1% flagged
SPW 12: Channel 1 is 26.5% flagged
```

### Level 2: Full SPW Flagging (DURING Calibration Application - Automatic

Fallback)

**Trigger:** Missing calibration solutions (from failed Phase 2 solve)

**Method:** CASA `applycal` automatically flags

**Timing:** This happens in **Phase 3** (Calibration Application)

**Result:** 100% flagging of all channels in SPW

**Example output (warning during Phase 3):**

```
The following MS spws have no corresponding cal spws in 2025-10-19T14:31:45_0~23_bpcal: 9 14 15
The following MS spws have no corresponding cal spws in 2025-10-19T14:31:45_0~23_gpcal: 9 14 15
The following MS spws have no corresponding cal spws in 2025-10-19T14:31:45_0~23_2gcal: 9 14 15
```

**What this means:** SPWs 9, 14, 15 were likely already heavily flagged in Phase
1, causing Phase 2 calibration to fail for these SPWs, resulting in Phase 3
automatically flagging them 100%.

---

## Verification Example

### Command to Check Flagging

```bash
cd /data/dsa110-contimg
python -u << 'EOF'
import numpy as np
from casacore.tables import table

ms_path = "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms"

with table(ms_path, readonly=True) as tb:
    ddid = tb.getcol("DATA_DESC_ID")
    flags = tb.getcol("FLAG")  # Shape: (rows, pol, chan)

    with table(f"{ms_path}/DATA_DESCRIPTION", readonly=True) as ddtb:
        spw_ids = ddtb.getcol("SPECTRAL_WINDOW_ID")

    for spw in range(16):
        rows_for_spw = np.where(spw_ids[ddid] == spw)[0]
        if len(rows_for_spw) == 0:
            continue

        spw_flags = flags[rows_for_spw, :, :]
        pct_flagged = 100.0 * np.sum(spw_flags) / spw_flags.size

        status = "ALL CHANNELS 100% FLAGGED" if pct_flagged == 100.0 else f"{pct_flagged:.1f}% flagged"
        print(f"SPW {spw}: {status}")
EOF
```

### Expected Output

```
SPW 0: 6.8% flagged
SPW 1: 93.0% flagged
SPW 2: 10.7% flagged
...
SPW 9: ALL CHANNELS 100% FLAGGED
...
SPW 14: ALL CHANNELS 100% FLAGGED
SPW 15: ALL CHANNELS 100% FLAGGED
```

---

## How to Diagnose SPW Failures With Certainty

### Why I Used "Likely" Before

I initially hedged with "likely" because I was **inferring** from indirect
evidence (the warning message) rather than directly examining the data.

### What Information is Needed for Certainty

To state **DEFINITIVELY** why specific SPWs failed calibration, you need:

1. **Pre-calibration flagging percentages** for each SPW
   - From FLAG column AFTER Phase 1, BEFORE Phase 2
   - Shows what % of data was flagged before calibration solve

2. **Reference antenna flagging percentages** for each SPW
   - Specifically for the reference antenna (e.g., antenna 103)
   - Shows if refant has any valid data in that SPW

3. **Calibration table inspection**
   - Verify which SPWs have solutions in K, BP, G tables
   - Confirms that missing SPWs have NO solutions

4. **Optional: CASA calibration logs**
   - Logs from gaincal/bandpass showing solve failures
   - Provides additional context on why solves failed

### Diagnostic Script

A diagnostic script is available at `/tmp/spw_failure_diagnosis.py` (created
above) that performs all these checks:

```bash
# Usage
python /tmp/spw_failure_diagnosis.py \
  <ms_path> \
  <calibration_table_prefix> \
  <refant_id>

# Example
python /tmp/spw_failure_diagnosis.py \
  /stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms \
  /stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23 \
  103
```

### Example Output (Definitive Diagnosis)

```
================================================================================
DEFINITIVE DIAGNOSIS
================================================================================

SPW 9:
  Pre-calibration flagging: 100.0%
  Reference antenna 103: 100% flagged
  → DEFINITIVE CAUSE: Reference antenna 103 fully flagged in SPW 9
  Calibration tables: NO SOLUTIONS (confirmed)

SPW 14:
  Pre-calibration flagging: 100.0%
  Reference antenna 103: 100% flagged
  → DEFINITIVE CAUSE: Reference antenna 103 fully flagged in SPW 14
  Calibration tables: NO SOLUTIONS (confirmed)

SPW 15:
  Pre-calibration flagging: 100.0%
  Reference antenna 103: 100% flagged
  → DEFINITIVE CAUSE: Reference antenna 103 fully flagged in SPW 15
  Calibration tables: NO SOLUTIONS (confirmed)
```

### Integration Into Pipeline

To enable **automatic** definitive diagnosis in the future, the pipeline could:

1. **Log pre-calibration flagging stats** after Phase 1
   - Per-SPW flagging percentages
   - Per-antenna, per-SPW flagging percentages for reference antenna
   - Store in calibration QA database or log files

2. **Log calibration solve failures** during Phase 2
   - Which SPWs failed to produce solutions
   - CASA error messages from gaincal/bandpass
   - Store solve failure reasons

3. **Display in frontend** CalibrationSPWPanel
   - Show pre-calibration vs post-calibration flagging
   - Highlight SPWs with 100% refant flagging
   - Link to diagnostic information

4. **Alert on problematic SPWs**
   - Warn if refant is heavily flagged (>90%) in any SPW
   - Suggest checking RFI patterns in specific frequency ranges
   - Recommend refant selection strategy

---

## Frontend Visualization

**Component:** `frontend/src/components/CalibrationSPWPanel.tsx`

**Purpose:** Display per-SPW flagging statistics for QA

**Note from code (lines 7-9):**

> **"This is primarily a DIAGNOSTIC tool. The pipeline uses per-channel flagging
> before calibration (preserves good channels). Flagging entire SPWs should be a
> last resort if per-channel flagging is insufficient."**

**Display:**

- Table of SPW flagging rates
- Warning for "problematic" SPWs (high flagging)
- Visualization via bandpass plots

---

## Summary

### Complete Flagging Process

**BEFORE Calibration (Phase 1):**

1. **RFI flagging** - Flag bad channels across all SPWs (per-channel)
2. **Quality flagging** - Flag zeros, autocorrelations, problematic channels
3. **Result:** All SPWs have some per-channel flags (e.g., SPW 1: 93% flagged)

**DURING Calibration Solve (Phase 2):**

4. **Calibration attempts** - Try to solve for all SPWs
5. **Some SPWs fail** - SPWs 9, 14, 15 have too much flagging or insufficient
   S/N
6. **Result:** No calibration solutions created for failed SPWs

**DURING Calibration Application (Phase 3):**

7. **Validation step** - Detects missing SPWs and logs warning
8. **`applycal` runs** - Automatically flags SPWs without calibration (CASA
   behavior)
9. **Result:** SPWs 9, 14, 15 are now **100% flagged** (full SPW flagging)

### Key Insight

**You DO have both:**

- ✅ **Full SPW flagging** for SPWs 9, 14, 15 (no calibration)
- ✅ **Individual channel flagging** in other SPWs (RFI, quality issues)

This is **by design** and **automatic**—CASA handles it during `applycal`.

---

## References

- **CASA applycal docs:** CASA will "flag data for which there is no calibration
  available"
- **Validation code:**
  `src/dsa110_contimg/src/dsa110_contimg/calibration/validate.py`
- **Apply code:**
  `src/dsa110_contimg/src/dsa110_contimg/calibration/applycal.py`
- **Flagging code:**
  `src/dsa110_contimg/src/dsa110_contimg/calibration/flagging.py`
- **Frontend display:** `frontend/src/components/CalibrationSPWPanel.tsx`

---

## Related Documentation

- Calibration Workflow
- RFI Flagging Strategy
- QA Procedures
