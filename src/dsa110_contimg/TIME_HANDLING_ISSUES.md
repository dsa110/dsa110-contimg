# TIME Handling Issues in MS Generation Procedures

## Executive Summary

Investigation reveals **critical inconsistencies** in how TIME is handled throughout the MS generation pipeline, particularly in:
1. CASA TIME format conversion (epoch offset handling)
2. Multiple implementations of `_ms_time_range()` with different assumptions
3. RA calculations that depend on correct TIME conversion

These inconsistencies can lead to **incorrect RA calculations** and **time-dependent phase center errors** in generated MS files.

---

## Issue 1: Inconsistent CASA TIME Epoch Handling

### Problem

The codebase uses **multiple different assumptions** about CASA TIME format:

1. **CASA TIME = seconds since MJD 51544.0** (2000-01-01):
   - Used in: `conversion/ms_utils.py:280`, `pointing/utils.py:35`, `api/routes.py:1468`
   - Conversion: `mjd = 51544.0 + time_sec / 86400.0`

2. **CASA TIME = seconds since MJD 0**:
   - Used in: `database/products.py:371-372`, `calibration/apply_service.py:81-82`, `imaging/worker.py:70-71`
   - Conversion: `mjd = time_sec / 86400.0`

3. **CASA TIME = already in MJD days**:
   - Used in: `msmetadata.timerangeforobs()` returns (assumed to be MJD days directly)

4. **Unused constant**:
   - `utils/constants.py:31`: `CASA_TIME_OFFSET = 2400000.5` (defined but never used)

### Impact

- **Incorrect time extraction**: MS files may have times off by ~51544 days (141 years)
- **RA calculation errors**: Since RA = LST(time), wrong time → wrong RA
- **Phase center misalignment**: Time-dependent phase centers use incorrect times

### Evidence

**File: `database/products.py:370-373`**
```python
# TIME is in seconds (MJD seconds)
t0 = float(times.min()) / 86400.0
t1 = float(times.max()) / 86400.0
return t0, t1, 0.5 * (t0 + t1)
```
**Problem**: No epoch offset applied. If CASA TIME uses 51544.0 epoch, this is wrong.

**File: `conversion/ms_utils.py:279-280`**
```python
# CASA TIME = (MJD - 51544.0) * 86400.0 (MJD epoch is 2000-01-01)
time_mjd = 51544.0 + time_sec / 86400.0
```
**Correct**: Uses epoch offset 51544.0.

**File: `calibration/apply_service.py:81-82`**
```python
t0 = _obs.getcol("TIME_RANGE")[0][0] / 86400.0
t1 = _obs.getcol("TIME_RANGE")[0][1] / 86400.0
```
**Problem**: No epoch offset. TIME_RANGE from OBSERVATION table may also need offset.

---

## Issue 2: Inconsistent `_ms_time_range()` Implementations

### Problem

There are **three different implementations** of `_ms_time_range()` with different fallback strategies:

1. **`database/products.py:324-377`**:
   - Method 1: `msmetadata.timerangeforobs()` (returns MJD days)
   - Method 2: `msmetadata.timesforscans()` → divide by 86400.0 (no offset)
   - Method 3: Main table TIME column → divide by 86400.0 (no offset)

2. **`calibration/apply_service.py:45-87`**:
   - Method 1: `msmetadata.timerangeforobs()` (returns MJD days)
   - Method 2: `msmetadata.timesforscans()` → divide by 86400.0 (no offset)
   - Method 3: OBSERVATION table TIME_RANGE → divide by 86400.0 (no offset)

3. **`imaging/worker.py:39-78`**:
   - Method 1: `msmetadata.timerangeforobs()` (returns MJD days)
   - Method 2: `msmetadata.timesforscans()` → divide by 86400.0 (no offset)
   - Method 3: **Missing** (no fallback to main table TIME column)

### Impact

- **Different results** from different code paths
- **Missing fallback** in `imaging/worker.py` may fail when msmetadata methods don't work
- **Inconsistent behavior** across the pipeline

### Evidence

**File: `database/products.py:344-356`**
```python
# Fallback: derive from timesforscans() (seconds, MJD seconds offset)
try:
    tmap = msmd.timesforscans()
    msmd.close()
    if isinstance(tmap, dict) and tmap:
        all_ts = [t for arr in tmap.values() for t in arr]
        if all_ts:
            t0 = min(all_ts)
            t1 = max(all_ts)
            # Convert seconds to MJD days if needed
            start_mjd = float(t0) / 86400.0  # NO OFFSET
            end_mjd = float(t1) / 86400.0    # NO OFFSET
```
**Problem**: Comment says "MJD seconds offset" but code doesn't apply offset.

---

## Issue 3: TIME Format Detection Logic

### Problem

**File: `calibration/cli.py:343-362`** has detection logic but it's **incomplete**:

```python
# CASA TIME format detection:
# Some MS files use seconds since MJD 0, others use seconds since MJD 51544
# Detect by checking if adding 51544 gives a reasonable date (2000-2100)
test_mjd_with_offset = 51544.0 + mid_time / 86400.0
test_mjd_without_offset = mid_time / 86400.0
```

**Issues**:
1. Only used in one place (`calibration/cli.py`), not in other `_ms_time_range()` implementations
2. Detection logic may fail for edge cases (e.g., dates near year 2000)
3. Doesn't handle case where TIME might already be in MJD days

### Impact

- **Inconsistent detection** across codebase
- **Potential false positives** in format detection
- **No standardization** of TIME format handling

---

## Issue 4: RA Calculation Dependencies on TIME

### Problem

RA calculations in `_fix_field_phase_centers_from_times()` depend on correct TIME conversion:

**File: `conversion/ms_utils.py:275-286`**
```python
# Get time for this field (CASA TIME is seconds since MJD epoch)
if field_idx in field_times:
    time_sec = field_times[field_idx]
    # Convert CASA TIME to MJD
    # CASA TIME = (MJD - 51544.0) * 86400.0 (MJD epoch is 2000-01-01)
    time_mjd = 51544.0 + time_sec / 86400.0
else:
    # Fallback: use mean time from main table
    time_mjd = 51544.0 + _np.mean(times) / 86400.0

# Calculate correct RA = LST(time) at meridian
phase_ra, phase_dec = get_meridian_coords(pt_dec, time_mjd)
```

**Issues**:
1. Uses correct epoch offset (51544.0) **only in this function**
2. If `field_times` was populated using incorrect TIME conversion elsewhere, RA will be wrong
3. The function that populates `field_times` (lines 228-230) reads TIME from main table but doesn't specify epoch handling

### Impact

- **RA errors**: If TIME is wrong, RA = LST(time) will be wrong
- **Phase center misalignment**: Fields get incorrect phase centers
- **Imaging artifacts**: Phase errors accumulate over long observations

---

## Issue 5: `timesforscans()` Return Format Ambiguity

### Problem

The comment in multiple files says `timesforscans()` returns "seconds, MJD seconds offset", but the code treats it as "seconds since MJD 0":

**File: `database/products.py:344`**
```python
# Fallback: derive from timesforscans() (seconds, MJD seconds offset)
```

But then:
```python
start_mjd = float(t0) / 86400.0  # No offset applied
```

**Question**: Does `timesforscans()` return:
- Seconds since MJD 0? (current code assumption)
- Seconds since MJD 51544.0? (comment suggests this)
- Something else?

### Impact

- **Uncertainty** about correct conversion
- **Potential systematic errors** if assumption is wrong

---

## Root Cause Analysis

1. **Lack of standardization**: No single source of truth for CASA TIME format
2. **Code duplication**: Multiple implementations of `_ms_time_range()` instead of shared utility
3. **Inconsistent documentation**: Comments don't match code behavior
4. **Missing validation**: No checks to verify TIME conversions are correct

---

## Recommended Fixes

### Solution: Use Astropy Time for Robust TIME Handling

**IMPLEMENTED**: A new utility module `utils/time_utils.py` has been created that leverages `astropy.Time` for all TIME conversions and validation. This provides:

1. **Robust conversion functions** using astropy:
   - `casa_time_to_mjd()` - Converts CASA TIME to MJD using astropy
   - `mjd_to_casa_time()` - Converts MJD to CASA TIME
   - `casa_time_to_astropy_time()` - Direct conversion to astropy Time objects

2. **Automatic format detection**:
   - `detect_casa_time_format()` - Uses astropy to validate and detect correct format
   - Handles both standard CASA format (with epoch offset) and legacy formats

3. **Built-in validation**:
   - `validate_time_mjd()` - Uses astropy Time to validate dates are in reasonable range
   - All extraction functions validate results automatically

4. **Standardized extraction**:
   - `extract_ms_time_range()` - Single, robust implementation replacing all `_ms_time_range()` variants
   - Uses astropy for validation at each step
   - Handles all fallback methods consistently

### Benefits of Using Astropy

- **Robust validation**: Astropy Time handles edge cases, leap seconds, time scales
- **Automatic format detection**: Can validate dates to detect correct format
- **Consistent API**: Single source of truth for all TIME operations
- **Error handling**: Astropy provides clear error messages for invalid times
- **Future-proof**: Astropy is actively maintained and handles astronomical time complexities

### Migration Path

Replace all existing `_ms_time_range()` implementations with:

```python
from dsa110_contimg.utils.time_utils import extract_ms_time_range

start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_path)
```

Replace manual TIME conversions with:

```python
from dsa110_contimg.utils.time_utils import casa_time_to_mjd, casa_time_to_astropy_time

# Convert CASA TIME to MJD
mjd = casa_time_to_mjd(time_sec)

# Or directly to astropy Time object
t = casa_time_to_astropy_time(time_sec)
```

### Fix 4: Update All TIME Conversions

Replace all TIME conversion code with calls to standardized functions:
- `database/products.py:371-372`
- `calibration/apply_service.py:68-69, 81-82`
- `imaging/worker.py:70-71`
- `calibration/cli.py:346-362` (use standardized detection)

### Fix 5: Document CASA TIME Format

Add clear documentation about CASA TIME format:
- CASA TIME is in **seconds since MJD 51544.0** (2000-01-01 00:00:00 UTC)
- Conversion: `mjd = 51544.0 + casa_time_sec / 86400.0`
- `msmetadata.timerangeforobs()` returns MJD days directly (no conversion needed)
- `msmetadata.timesforscans()` returns seconds (needs conversion with epoch offset)
- Main table TIME column is in seconds (needs conversion with epoch offset)
- OBSERVATION table TIME_RANGE is in seconds (needs conversion with epoch offset)

---

## Testing Recommendations

1. **Unit tests** for TIME conversion functions
2. **Integration tests** comparing TIME extraction from real MS files
3. **Validation tests** checking RA calculations match expected LST values
4. **Regression tests** ensuring fixes don't break existing functionality

---

## Priority

**CRITICAL**: These issues directly affect RA calculations and phase center accuracy, which are fundamental to interferometric imaging quality.

