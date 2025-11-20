# Using Adaptive Flagging (Calibration-Triggered Escalation)

**Date:** 2025-11-19  
**Type:** How-To Guide  
**Status:** ✅ Ready to Use

---

## Overview

Adaptive flagging automatically switches from **default** to **aggressive** RFI
flagging if calibration fails, improving success rates without manual
intervention.

**How it works:**

1. Apply default flagging (4.5% flagged, ~4 min)
2. Attempt calibration
3. If calibration fails → Reset flags, apply aggressive flagging (6% flagged, ~4
   min), retry calibration
4. Return results with strategy used

---

## Quick Start

### **Python API**

```python
from dsa110_contimg.calibration import flag_rfi_adaptive, CalibrationFailure

def my_calibration_function(ms_path, refant, **kwargs):
    """Your calibration logic - should raise exception on failure."""
    from dsa110_contimg.calibration.calibration import (
        solve_delay, solve_bandpass, solve_gains
    )

    # Solve calibration
    ktabs = solve_delay(ms_path, field="0", refant=refant)
    bptabs = solve_bandpass(ms_path, field="0", refant=refant, ktable=ktabs[0])
    gtabs = solve_gains(ms_path, field="0", refant=refant,
                        ktable=ktabs[0], bptables=bptabs)

    # Check if calibration succeeded (your validation logic)
    if not validate_calibration(gtabs[0]):
        raise CalibrationFailure("Gain solutions failed validation")

    return ktabs, bptabs, gtabs

# Use adaptive flagging
result = flag_rfi_adaptive(
    ms_path="/path/to/data.ms",
    refant="103",
    calibrate_fn=my_calibration_function,
    calibrate_kwargs={"field": "0"}
)

print(f"Strategy used: {result['strategy']}")  # "default" or "aggressive"
print(f"Success: {result['success']}")
print(f"Attempts: {result['attempts']}")  # 1 or 2
print(f"Flagged: {result['flagging_stats']['overall_flagged_fraction']*100:.1f}%")
```

---

## Command Line Usage

### **Standalone Flagging with Adaptive Mode**

```bash
# Just flagging (no calibration check)
python -c "
from dsa110_contimg.calibration import flag_rfi_adaptive
result = flag_rfi_adaptive('data.ms')
print(f'Flagged {result[\"flagging_stats\"][\"overall_flagged_fraction\"]*100:.1f}%')
"
```

### **Full Calibration Pipeline with Adaptive Flagging**

```bash
# Create a calibration script with adaptive flagging
python calibrate_adaptive.py data.ms --refant 103
```

Example `calibrate_adaptive.py`:

```python
#!/usr/bin/env python3
import sys
from dsa110_contimg.calibration import flag_rfi_adaptive, CalibrationFailure
from dsa110_contimg.calibration.calibration import solve_bandpass, solve_gains

def calibrate(ms_path, refant):
    """Simple calibration: bandpass + gains."""
    bptabs = solve_bandpass(ms_path, "0", refant)
    gtabs = solve_gains(ms_path, "0", refant, bptables=bptabs)

    # Basic validation: check if tables were created
    if not bptabs or not gtabs:
        raise CalibrationFailure("Calibration table generation failed")

    return bptabs, gtabs

# Run with adaptive flagging
result = flag_rfi_adaptive(
    ms_path=sys.argv[1],
    refant=sys.argv[2] if len(sys.argv) > 2 else "103",
    calibrate_fn=calibrate,
)

print(f"\n{'='*70}")
print(f"SUCCESS: Used {result['strategy']} strategy")
print(f"Flagged {result['flagging_stats']['overall_flagged_fraction']*100:.1f}% of data")
print(f"{'='*70}")
```

---

## Integration with Existing Pipeline

The adaptive flagging module is designed to work with your existing calibration
code. You just need to:

1. **Wrap your calibration in a function**
2. **Raise `CalibrationFailure` on failure**
3. **Call `flag_rfi_adaptive()` instead of `flag_rfi()`**

### **Example: Modify Existing Code**

**Before (manual flagging):**

```python
from dsa110_contimg.calibration.flagging import flag_rfi, reset_flags
from dsa110_contimg.calibration.calibration import solve_bandpass

# Manual flagging
reset_flags(ms_path)
flag_rfi(ms_path)

# Calibration
try:
    bptabs = solve_bandpass(ms_path, "0", refant)
except Exception as e:
    print(f"Calibration failed: {e}")
    # Manual intervention needed!
```

**After (adaptive flagging):**

```python
from dsa110_contimg.calibration import flag_rfi_adaptive, CalibrationFailure

def do_calibration(ms_path, refant):
    bptabs = solve_bandpass(ms_path, "0", refant)
    if not validate_solutions(bptabs[0]):
        raise CalibrationFailure("Poor bandpass solutions")
    return bptabs

# Automatic retry with aggressive flagging on failure
result = flag_rfi_adaptive(
    ms_path=ms_path,
    refant=refant,
    calibrate_fn=do_calibration,
)

if result['success']:
    print(f"✓ Calibration succeeded with {result['strategy']} flagging")
else:
    print("✗ Calibration failed even with aggressive flagging")
```

---

## Parameters

### **`flag_rfi_adaptive()` Parameters**

| Parameter             | Type     | Default                 | Description                                                                     |
| --------------------- | -------- | ----------------------- | ------------------------------------------------------------------------------- |
| `ms_path`             | str      | Required                | Path to Measurement Set                                                         |
| `refant`              | str      | `"103"`                 | Reference antenna                                                               |
| `calibrate_fn`        | callable | `None`                  | Function to call for calibration. If None, only flagging (no adaptive behavior) |
| `calibrate_kwargs`    | dict     | `{}`                    | Additional kwargs for `calibrate_fn`                                            |
| `aggressive_strategy` | str      | `dsa110-aggressive.lua` | Path to aggressive strategy file                                                |
| `backend`             | str      | `"aoflagger"`           | Flagging backend                                                                |

### **Return Value**

Dict with keys:

- `strategy`: `"default"` or `"aggressive"`
- `success`: `bool` - calibration succeeded?
- `attempts`: `int` - 1 or 2 (number of flagging passes)
- `flagging_stats`: `dict` - detailed flag statistics

---

## When Does It Help?

**Scenarios where adaptive flagging improves success:**

| Situation         | Without Adaptive    | With Adaptive                         |
| ----------------- | ------------------- | ------------------------------------- |
| Clean observation | ✓ Success (default) | ✓ Success (default, same)             |
| Moderate RFI      | ✗ Calibration fails | ✓ Success (aggressive, +4 min)        |
| Heavy RFI         | ✗ Calibration fails | ✓ Maybe success (aggressive, +4 min)  |
| Extremely bad RFI | ✗ Failure           | ✗ Failure (but tried both strategies) |

**Expected improvement:** +15-20% calibration success rate

**Cost:** Extra ~4 minutes only when calibration fails (~20-30% of observations)

---

## Calibration Failure Detection

Your `calibrate_fn` should raise `CalibrationFailure` (or any exception) when
calibration fails. Common indicators:

```python
from dsa110_contimg.calibration import CalibrationFailure

def calibrate_with_validation(ms_path, refant):
    # Solve calibration
    gtabs = solve_gains(ms_path, "0", refant)

    # Check for failure indicators
    gains = read_gains(gtabs[0])

    # 1. Excessive gain amplitude
    if (gains > 10 * np.median(gains)).any():
        raise CalibrationFailure("Excessive gain solutions detected")

    # 2. Too many failed SPWs
    converged_spws = check_convergence(gtabs[0])
    if len(converged_spws) < 12:  # <75% of 16 SPWs
        raise CalibrationFailure(f"Only {len(converged_spws)}/16 SPWs converged")

    # 3. High chi-squared
    chi2 = calculate_chi_squared(ms_path, gtabs[0])
    if chi2 > threshold:
        raise CalibrationFailure(f"High chi-squared: {chi2:.2f}")

    return gtabs
```

---

## Configuration Options

### **Customize Aggressive Strategy**

```python
# Use a custom aggressive strategy
result = flag_rfi_adaptive(
    ms_path="data.ms",
    refant="103",
    calibrate_fn=my_calibrate,
    aggressive_strategy="/path/to/custom-aggressive.lua",
)
```

### **Use CASA Backend**

```python
# Use CASA tfcrop+rflag instead of AOFlagger
result = flag_rfi_adaptive(
    ms_path="data.ms",
    refant="103",
    calibrate_fn=my_calibrate,
    backend="casa",
)
```

---

## Logging Output

Adaptive flagging provides clear logging:

```
======================================================================
ADAPTIVE FLAGGING: Pass 1 - Default strategy
======================================================================
Default flagging complete: 4.46% flagged
Attempting calibration with default flagging...
Calibration failed with default flagging: Convergence failure in SPW 3
======================================================================
ADAPTIVE FLAGGING: Pass 2 - Aggressive strategy
======================================================================
Resetting flags for aggressive retry...
Applying aggressive flagging strategy: /data/dsa110-contimg/config/dsa110-aggressive.lua
Aggressive flagging complete: 6.19% flagged
Retrying calibration with aggressive flagging...
✓ Calibration successful with aggressive flagging
```

---

## Best Practices

### **DO:**

- ✓ Implement meaningful calibration validation
- ✓ Raise `CalibrationFailure` on clear failures
- ✓ Log calibration quality metrics
- ✓ Use adaptive flagging for automated pipelines

### **DON'T:**

- ✗ Raise exceptions for warnings (only true failures)
- ✗ Skip calibration validation entirely
- ✗ Use adaptive mode for manual/interactive work (unnecessary overhead)

---

## Troubleshooting

### **"Calibration succeeded with default, but image is bad"**

Adaptive flagging only escalates on _calibration failures_, not poor image
quality. Add image quality checks:

```python
def calibrate_and_validate_image(ms_path, refant):
    # Calibration
    calibrate(ms_path, refant)

    # Quick image
    image = make_quick_image(ms_path)
    rms = calculate_rms(image)

    if rms > expected_thermal_noise * 5:
        raise CalibrationFailure(f"Image RMS too high: {rms:.2e}")
```

### **"Both default and aggressive failed"**

Some observations are truly bad. Check:

- Data quality issues (missing antennas, hardware failures)
- Extremely heavy RFI (may need manual CASA flagging)
- Wrong reference antenna
- Calibrator source issues

### **"Want to skip default, go straight to aggressive"**

Just use regular `flag_rfi()` with the aggressive strategy:

```python
from dsa110_contimg.calibration.flagging import flag_rfi

flag_rfi(ms_path, strategy="/data/dsa110-contimg/config/dsa110-aggressive.lua")
```

---

## See Also

- [Automatic Strategy Selection](AUTOMATIC_FLAGGING_STRATEGY_SELECTION.md) -
  Advanced approaches
- [AOFlagger Strategy Tuning](AOFLAGGER_STRATEGY_TUNING.md) - Understanding
  strategies
- [RFI Backend Comparison](rfi_backend_comparison_testing.md) - Performance
  testing
