# TIME Validation Strategy

**Date:** 2025-11-06  
**Purpose:** Verify that TIME extraction is not just consistent, but actually correct

---

## Overview

We've standardized TIME extraction across the codebase, but we need to verify that the extracted times are **correct**, not just consistent. This document outlines validation strategies and tools.

---

## Validation Approaches

### 1. Cross-Reference Validation

#### A. Filename Timestamp Validation
**What:** Compare MS TIME column with timestamp embedded in filename  
**Why:** Filename timestamps are set at data creation and should match observation time  
**Tolerance:** ±0.5 hours (accounts for integration time and filename precision)  
**Implementation:** `validate_ms_time_against_filename()`

**Example:**
```python
ms_path = "2025-10-29T13:32:03.ms"
# Filename suggests: 2025-10-29T13:32:03
# MS TIME should be: ~2025-10-29T13:32:03 (within integration window)
```

#### B. UVH5 Source Validation
**What:** Compare MS TIME with source UVH5 file time_array  
**Why:** Validates that conversion preserved correct time information  
**Tolerance:** ±1.0 seconds (accounts for rounding/precision)  
**Implementation:** `validate_ms_time_against_uvh5()`

**Example:**
```python
# UVH5 time_array (JD): 2460312.065
# MS TIME (seconds since MJD 0): 5268461621.088
# Should convert to same MJD: 60977.565
```

#### C. OBSERVATION Table Validation
**What:** Verify TIME column values fall within OBSERVATION TIME_RANGE  
**Why:** TIME_RANGE should encompass all TIME values  
**Tolerance:** Exact match (no tolerance needed)  
**Implementation:** `validate_time_ordering()`

---

### 2. Astronomical Consistency Validation

#### A. LST Consistency Check
**What:** For meridian-tracking observations, verify RA = LST(time)  
**Why:** If TIME is correct, calculated LST should match pointing RA  
**Tolerance:** ±1.0 degrees (accounts for pointing accuracy)  
**Implementation:** `validate_lst_consistency()`

**Example:**
```python
# Pointing RA: 123.45° (from FIELD table)
# Observation time: 2025-10-29T13:32:03
# Calculated LST: 123.45° (should match)
# If TIME is wrong by 1 hour, LST would be off by ~15°
```

#### B. Calibrator Transit Validation
**What:** Verify that calibrator transit times match expected values  
**Why:** Transit calculations depend on correct observation time  
**Tolerance:** ±5 minutes (accounts for observation window)  
**Implementation:** Can be added to validation suite

**Example:**
```python
# Calibrator 0834+555 RA: 129.0°
# Expected transit: 2025-10-29T13:54:00 (LST = 129.0°)
# MS observation time: 2025-10-29T13:54:17
# Difference: 17 minutes (acceptable)
```

---

### 3. Temporal Consistency Validation

#### A. Time Ordering Check
**What:** Verify TIME values are monotonically increasing  
**Why:** Time should never go backwards  
**Tolerance:** None (must be strictly increasing or constant within integration)  
**Implementation:** `validate_time_ordering()`

#### B. Duration Validation
**What:** Verify observation duration matches expected value  
**Why:** Duration should match known observation parameters  
**Tolerance:** ±10% (accounts for integration windows)  
**Implementation:** `validate_observation_duration()`

**Example:**
```python
# Expected: 5-minute observation
# Actual: 4.8 minutes (within 10% tolerance)
```

---

### 4. Format Detection Validation

#### A. Format Detection Test
**What:** Verify that format detection correctly identifies MJD 0 vs MJD 51544.0  
**Why:** Ensures format detection is working correctly  
**Tolerance:** Must produce valid dates (2000-2100)  
**Implementation:** Built into `extract_ms_time_range()`

**Test Cases:**
- TIME = 5268461621 seconds → Should detect MJD 0 → 2025-10-29 ✓
- TIME = 815059923 seconds → Should detect MJD 51544 → 2025-10-29 ✓
- TIME = 0 seconds → Should detect MJD 0 → 1858-11-17 ✗ (too old, invalid)

---

## Validation Tools

### 1. Python API

**Module:** `dsa110_contimg.utils.time_validation`

**Functions:**
- `validate_ms_time_against_filename()` - Filename timestamp validation
- `validate_ms_time_against_uvh5()` - UVH5 cross-validation
- `validate_lst_consistency()` - LST/RA consistency check
- `validate_time_ordering()` - Time ordering validation
- `validate_observation_duration()` - Duration validation
- `comprehensive_time_validation()` - Run all checks

**Usage:**
```python
from dsa110_contimg.utils.time_validation import comprehensive_time_validation

results = comprehensive_time_validation(
    ms_path="/scratch/ms/2025-10-29T13:32:03.ms",
    uvh5_path="/data/incoming/2025-10-29T13:32:03.uvh5",
    pointing_ra_deg=123.45,
    expected_duration_minutes=5.0
)

if results['all_valid']:
    print("✓ All checks passed")
else:
    print("✗ Validation failed:")
    for error in results['errors']:
        print(f"  - {error}")
```

### 2. Command-Line Tool

**Script:** `scripts/validate_ms_timing.py`

**Usage:**
```bash
# Basic validation
python scripts/validate_ms_timing.py /scratch/ms/2025-10-29T13:32:03.ms

# With UVH5 source
python scripts/validate_ms_timing.py /scratch/ms/2025-10-29T13:32:03.ms \
  --uvh5 /data/incoming/2025-10-29T13:32:03.uvh5

# With pointing RA
python scripts/validate_ms_timing.py /scratch/ms/2025-10-29T13:32:03.ms \
  --pointing-ra 123.45

# JSON output
python scripts/validate_ms_timing.py /scratch/ms/2025-10-29T13:32:03.ms --json
```

---

## Validation Workflow

### For New MS Files

1. **Immediate Validation:**
   ```bash
   python scripts/validate_ms_timing.py <ms_path> --uvh5 <uvh5_path>
   ```
   - Validates against source UVH5
   - Checks filename timestamp
   - Verifies time ordering

2. **Pointing Validation:**
   ```bash
   python scripts/validate_ms_timing.py <ms_path> --pointing-ra <ra_deg>
   ```
   - Validates LST consistency
   - Ensures TIME is correct for coordinate calculations

3. **Duration Validation:**
   ```bash
   python scripts/validate_ms_timing.py <ms_path> --expected-duration <minutes>
   ```
   - Verifies observation duration matches expected

### For Existing MS Files

1. **Filename Validation:**
   - Quick check: Does TIME match filename timestamp?
   - Flags files with >0.5 hour differences

2. **LST Validation:**
   - If pointing RA is known, verify LST consistency
   - Flags files where LST doesn't match pointing

3. **Bulk Validation:**
   ```python
   from pathlib import Path
   from dsa110_contimg.utils.time_validation import validate_ms_time_against_filename
   
   ms_dir = Path("/scratch/ms")
   for ms_file in ms_dir.glob("*.ms"):
       is_valid, error, diff = validate_ms_time_against_filename(ms_file)
       if not is_valid:
           print(f"{ms_file.name}: {error}")
   ```

---

## Expected Results

### Correct MS Files

**All checks should pass:**
- ✓ Time ordering: Valid
- ✓ Filename validation: Valid (difference < 0.1 hours)
- ✓ UVH5 validation: Valid (difference < 1.0 seconds)
- ✓ LST consistency: Valid (difference < 1.0 degrees)
- ✓ Duration: Valid (within 10% of expected)

### Problematic MS Files

**Common issues:**
1. **Filename mismatch (>0.5 hours):**
   - Indicates TIME column was set incorrectly
   - May indicate data quality issue

2. **UVH5 mismatch (>1.0 seconds):**
   - Indicates conversion error
   - May indicate format detection failure

3. **LST inconsistency (>1.0 degrees):**
   - Indicates TIME is incorrect
   - May cause coordinate calculation errors

4. **Time ordering failure:**
   - Indicates corrupted MS file
   - May indicate data processing error

---

## Integration with Pipeline

### Automated Validation

**Add to MS generation pipeline:**
```python
from dsa110_contimg.utils.time_validation import comprehensive_time_validation

# After MS file creation
results = comprehensive_time_validation(
    ms_path=ms_path,
    uvh5_path=uvh5_path,
    pointing_ra_deg=pointing_ra_deg
)

if not results['all_valid']:
    logger.error(f"TIME validation failed for {ms_path}")
    for error in results['errors']:
        logger.error(f"  - {error}")
    # Optionally: fail pipeline or flag for review
```

### CI/CD Integration

**Add validation to test suite:**
```python
def test_ms_time_validation():
    """Test that MS files pass time validation."""
    ms_path = "test_data/test.ms"
    uvh5_path = "test_data/test.uvh5"
    
    results = comprehensive_time_validation(
        ms_path=ms_path,
        uvh5_path=uvh5_path,
        pointing_ra_deg=123.45
    )
    
    assert results['all_valid'], f"Validation failed: {results['errors']}"
```

---

## Limitations and Considerations

### 1. Filename Timestamp Precision
- Filenames may only have second precision
- Integration windows may span multiple seconds
- Tolerance accounts for this (±0.5 hours)

### 2. Pointing RA Accuracy
- Pointing database may have limited precision
- Meridian tracking may have small offsets
- Tolerance accounts for this (±1.0 degrees)

### 3. UVH5 Time Precision
- UVH5 time_array is in JD (high precision)
- MS TIME is in seconds (lower precision)
- Tolerance accounts for rounding (±1.0 seconds)

### 4. Format Detection Edge Cases
- Very old dates (< 2000) may fail validation
- Very future dates (> 2100) may fail validation
- Format detection uses year range (2000-2100) to validate

---

## Next Steps

1. **Run validation on existing MS files:**
   - Identify files with timing issues
   - Document common problems
   - Prioritize fixes

2. **Integrate into pipeline:**
   - Add validation to MS generation
   - Add validation to CI/CD
   - Create alerts for validation failures

3. **Expand validation:**
   - Add calibrator transit validation
   - Add ephemeris cross-validation
   - Add telescope pointing database validation

4. **Monitor and track:**
   - Track validation results over time
   - Identify patterns in failures
   - Improve validation based on findings

---

## Conclusion

The validation strategy provides multiple independent checks to verify TIME correctness:

1. **Cross-reference validation** ensures consistency with known sources
2. **Astronomical validation** ensures correctness for coordinate calculations
3. **Temporal validation** ensures logical consistency
4. **Format validation** ensures proper format detection

Together, these checks provide confidence that TIME extraction is not just consistent, but actually correct.

