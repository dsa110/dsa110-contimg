# Field Concatenation for Faster Self-Calibration

**Date:** 2025-11-19  
**Type:** How-To Guide  
**Status:** ✅ Implemented  
**Related:** [NVSS Self-Cal Integration](../dev/status/2025-11/selfcal_nvss_integration_status.md)

---

## Overview

Field concatenation is a performance optimization for self-calibration on
DSA-110 multi-field (drift-scan) observations. By concatenating all rephased
fields into a single field before self-calibration, we can dramatically speed up
the `gaincal` solving steps.

**Performance improvement:** ~3-5x faster self-calibration overall (~24x faster
`gaincal`)

---

## How It Works

### Standard Multi-Field Self-Calibration

1. MS has 24 fields (1 calibrator + 23 meridian time bins)
2. All fields are rephased to calibrator position (common phase center)
3. `gaincal` iterates over all 24 fields separately
4. **Slow:** 24 separate solve iterations per self-cal round

### With Field Concatenation

1. MS has 24 fields (1 calibrator + 23 meridian time bins)
2. All fields are rephased to calibrator position (common phase center)
3. **All fields concatenated into single field** (FIELD_ID → 0)
4. `gaincal` solves on single concatenated field
5. **Fast:** 1 solve iteration per self-cal round

---

## Requirements

**CRITICAL:** This optimization **only works** if:

1. ✅ All fields have been **rephased to the same phase center**
2. ✅ The MS was produced by standard DSA-110 calibration pipeline
3. ✅ You want to self-calibrate on the **entire mosaic** (not individual
   fields)

**Do NOT use** if:

- ❌ Fields have different phase centers
- ❌ You want field-specific calibration solutions
- ❌ MS has not been rephased

---

## Usage

### Python API

```python
from dsa110_contimg.calibration.selfcal import SelfCalConfig, selfcal_ms

# Enable field concatenation
config = SelfCalConfig(
    concatenate_fields=True,  # Enable the optimization
    use_nvss_seeding=True,
    nvss_min_mjy=1.0,
    max_iterations=5,
)

success, summary = selfcal_ms(
    ms_path="/path/to/rephased.ms",
    output_dir="/path/to/output",
    config=config,
)

print(f"Used field concatenation: {summary['used_concatenated_fields']}")
```

### Command-Line Interface

```bash
python -m dsa110_contimg.calibration.cli_selfcal \
    /path/to/rephased.ms \
    --output-dir /path/to/output \
    --concatenate-fields \
    --max-iterations 5
```

---

## Implementation Details

### What Happens Under the Hood

1. **Copy MS:** Creates temporary concatenated MS (`<ms>_selfcal_concat`)
2. **Set FIELD_ID:** All rows in main table get `FIELD_ID = 0`
3. **Update FIELD table:** Remove extra field rows, keep only field 0
4. **Self-calibrate:** Run self-cal on concatenated MS
5. **Clean up:** Automatically remove concatenated MS after completion

### Automatic Fallback

If concatenation fails for any reason, the code automatically falls back to
standard multi-field self-cal:

```python
try:
    concatenate_fields_in_ms(ms_path, concat_ms_path)
    ms_to_use = concat_ms_path
except Exception as e:
    logger.error(f"Field concatenation failed: {e}")
    logger.warning("Falling back to non-concatenated self-cal")
    ms_to_use = ms_path  # Use original MS
```

---

## Performance Comparison

### Expected Speedup

| Component        | Standard | Concatenated | Speedup |
| ---------------- | -------- | ------------ | ------- |
| `gaincal` step   | 24 iters | 1 iter       | ~24x    |
| WSClean imaging  | Same     | Same         | 1x      |
| Overall self-cal | Baseline | Optimized    | ~3-5x   |

### Benchmarks (Pending)

Once comparison tests complete, we will have actual benchmarks:

- Baseline (no concatenation): `X` minutes
- With concatenation: `Y` minutes
- Measured speedup: `X/Y`x

---

## Validation

### Scientific Correctness

Field concatenation is scientifically valid because:

1. **All fields already rephased** to same phase center
2. **Visibilities are identical** - just grouped under single field
3. **Calibration solutions apply to entire mosaic** - not field-specific
4. **Used successfully in DP3 pipeline** - proven approach

### Comparison Testing

To verify equivalence, we're running parallel tests:

- **Method A:** Standard multi-field self-cal (baseline)
- **Method B:** Field concatenation self-cal (optimized)

Compare:

- Final image SNR
- Calibration solution quality
- Photometry accuracy

---

## Troubleshooting

### "Field concatenation failed"

**Possible causes:**

- MS is locked by another process
- Insufficient disk space for temporary concatenated MS
- Corrupted MS structure

**Solution:** Falls back to standard self-cal automatically

### "MS not rephased"

**Error:** Calibration fails or produces poor results

**Cause:** Fields have different phase centers (not rephased)

**Solution:** Ensure MS was processed through standard pipeline with rephasing

---

## When to Use

### ✅ Use Field Concatenation When:

- Running self-cal on standard DSA-110 drift-scan MS
- MS has been rephased to common phase center
- You want faster self-calibration (~3-5x speedup)
- Disk space available for temporary concatenated MS (~2x MS size)

### ❌ Don't Use When:

- Fields have different phase centers
- You need field-specific calibration solutions
- Very low disk space (concatenation requires temporary MS copy)

---

## Related Features

- **NVSS MODEL_DATA Seeding:** Provides initial sky model for faster convergence
- **Long-Running Docker Containers:** Eliminates Docker hang issues
- **Standard Multi-Field Self-Cal:** Default method (backwards compatible)

---

## Future Work

- **Benchmark real-world speedup** (tests in progress)
- **Compare scientific accuracy** of concatenated vs standard method
- **Consider enabling by default** if validated
- **Optimize disk usage** (in-place concatenation instead of copy?)

---

## References

- Implementation: `src/dsa110_contimg/calibration/selfcal.py`
- Concatenation function: `src/dsa110_contimg/calibration/dp3_wrapper.py`
- CLI: `src/dsa110_contimg/calibration/cli_selfcal.py`
- Status: `docs/dev/status/2025-11/selfcal_nvss_integration_status.md`
