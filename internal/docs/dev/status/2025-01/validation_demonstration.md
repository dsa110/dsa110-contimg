# TIME Validation Demonstration

**Example MS File:** `/scratch/ms/2025-10-29T13:38:49.ms`

This document demonstrates how each validation check works using a real MS file.

---

## 1. TIME Extraction

**What it does:** Extracts the time range from the MS file using the standardized `extract_ms_time_range()` function.

**Results:**
```
Start: 2025-10-29T13:33:41.088
End:   2025-10-29T13:38:37.441
Mid:   2025-10-29T13:36:09.265
Duration: 4.94 minutes
```

**Why this matters:** This is the foundation - we need to extract the time correctly before we can validate it.

---

## 2. Raw TIME Column Analysis

**What it shows:** The actual values stored in the MS file's TIME column.

**Results:**
```
TIME column statistics:
Min:   5268461621.088441 seconds
Max:   5268461917.441209 seconds
Mean:  5268461769.264827 seconds
Unique values: 24
Total rows: 1787904
```

**Format Detection:**
```
TIME value: 5268461769.264827 seconds

As seconds since MJD 0:     60977.56677390 MJD = 2025-10-29T13:36:09.265 ✓ CORRECT
As seconds since MJD 51544: 112521.56677390 MJD = 2166-12-13T13:36:09.265 ✗ WRONG

→ Detected format: MJD 0
→ Correct MJD: 60977.56677390 = 2025-10-29T13:36:09.265
```

**Why this matters:** This demonstrates that:
1. The TIME column uses seconds since MJD 0 (not MJD 51544.0)
2. Format detection correctly identifies the format
3. The resulting date (2025-10-29) is correct, not a future date (2166)

---

## 3. OBSERVATION Table TIME_RANGE

**What it shows:** The TIME_RANGE stored in the OBSERVATION table.

**Results:**
```
TIME_RANGE shape: (2, 1)
TIME_RANGE values: [5268461621.088441, 5268461917.441209] seconds
TIME_RANGE as dates:
Start: 2025-10-29T13:33:41.088
End:   2025-10-29T13:38:37.441
✓ TIME column matches TIME_RANGE
```

**Why this matters:** 
- TIME_RANGE should match the TIME column min/max values
- This confirms the OBSERVATION table was correctly fixed by `_fix_observation_time_range()`
- Both use the same format (seconds since MJD 0)

---

## 4. Filename Timestamp Validation

**What it does:** Compares the extracted TIME with the timestamp embedded in the filename.

**Filename:** `2025-10-29T13:38:49.ms`  
**Extracted TIME:** `2025-10-29T13:36:09.265`  
**Difference:** `0.044 hours (2.7 minutes)`

**Result:** ✓ PASS - Excellent match (within 6 minutes)

**Why this matters:**
- Filename timestamps are set at data creation and should match observation time
- Small differences (< 6 minutes) are expected due to:
  - Integration windows (observation spans multiple seconds)
  - Filename precision (may only have second precision)
- Large differences (> 30 minutes) indicate a data quality issue

**What would fail:**
- If TIME was off by 1 hour → difference would be ~1.0 hours → FAIL
- If TIME was off by 1 day → difference would be ~24 hours → FAIL

---

## 5. Time Ordering Validation

**What it does:** Verifies that TIME values are logically consistent.

**Checks:**
1. TIME values are monotonically increasing (or constant within integration)
2. OBSERVATION TIME_RANGE start < end
3. TIME values fall within TIME_RANGE

**Results:**
```
✓ PASS: TIME values are correctly ordered
→ All TIME values are monotonically increasing
→ TIME values fall within OBSERVATION TIME_RANGE
```

**Why this matters:**
- Time should never go backwards
- TIME_RANGE should encompass all TIME values
- This catches corrupted or incorrectly processed MS files

**What would fail:**
- If TIME values decreased: `[100, 200, 150]` → FAIL
- If TIME_RANGE was `[0, 0]`: → FAIL (invalid range)
- If TIME values outside TIME_RANGE: → FAIL

---

## 6. Observation Duration Validation

**What it does:** Verifies that the observation duration is reasonable.

**Results:**
```
Duration: 4.94 minutes
→ Short observation (4.9 minutes)
```

**Why this matters:**
- Duration should match expected observation parameters
- Very short durations (< 1 minute) may indicate data issues
- Very long durations may indicate incorrect time extraction

**What would fail:**
- If duration was negative: → FAIL (time ordering issue)
- If duration was 0: → FAIL (no time span)
- If duration was > 24 hours: → WARNING (unusually long)

---

## 7. Comprehensive Validation Summary

**All checks combined:**

```
Overall Status: ✓ ALL CHECKS PASSED

Individual Checks:
  ✓ time_ordering
  ✓ filename_validation (Time difference: 0.044 hours)
  ✓ duration (Duration: 4.94 minutes)
```

**What this tells us:**
1. ✓ TIME extraction is working correctly
2. ✓ TIME format detection is working correctly
3. ✓ TIME values are consistent with filename
4. ✓ TIME values are logically ordered
5. ✓ Observation duration is reasonable

---

## Example: What a Failure Looks Like

If TIME was incorrectly extracted (e.g., using wrong epoch), we'd see:

```
✗ FAIL: TIME mismatch
  MS TIME column indicates 2166-12-13T13:36:09.265
  but filename suggests 2025-10-29T13:38:49
  (difference: 141.0 years)
```

Or if TIME was off by 1 hour:

```
✗ FAIL: TIME mismatch
  MS TIME column indicates 2025-10-29T14:36:09.265
  but filename suggests 2025-10-29T13:38:49
  (difference: 0.96 hours)
```

---

## Key Insights from This Example

1. **Format Detection Works:**
   - Correctly identified MJD 0 format
   - Produced correct 2025 date (not 2166)

2. **TIME is Consistent:**
   - TIME column matches TIME_RANGE
   - TIME matches filename timestamp (within tolerance)
   - TIME values are correctly ordered

3. **Extraction is Correct:**
   - `extract_ms_time_range()` produces correct dates
   - All validation checks pass
   - Time is suitable for astronomical calculations

---

## How to Use This for Your MS Files

**Quick validation:**
```bash
python scripts/validate_ms_timing.py /scratch/ms/your_file.ms
```

**With UVH5 source (strongest validation):**
```bash
python scripts/validate_ms_timing.py /scratch/ms/your_file.ms \
  --uvh5 /data/incoming/source.uvh5
```

**With pointing RA (astronomical validation):**
```bash
python scripts/validate_ms_timing.py /scratch/ms/your_file.ms \
  --pointing-ra 123.45
```

**All checks:**
```bash
python scripts/validate_ms_timing.py /scratch/ms/your_file.ms \
  --uvh5 /data/incoming/source.uvh5 \
  --pointing-ra 123.45 \
  --expected-duration 5.0
```

---

## Conclusion

The validation checks provide multiple independent ways to verify TIME correctness:

1. **Filename validation** - Cross-references with data creation time
2. **Time ordering** - Ensures logical consistency
3. **Duration validation** - Verifies reasonable observation length
4. **UVH5 validation** (when available) - Cross-validates with source
5. **LST validation** (when RA available) - Astronomical consistency check

Together, these checks give confidence that TIME extraction is not just consistent, but actually correct.

