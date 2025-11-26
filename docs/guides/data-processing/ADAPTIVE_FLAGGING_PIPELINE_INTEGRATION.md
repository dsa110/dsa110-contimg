# Adaptive RFI Flagging in the Pipeline

## Overview

The DSA-110 continuum imaging pipeline now includes **adaptive RFI flagging**
with automatic escalation from default to aggressive strategies based on
calibration success.

## Quick Reference: Flagging Strategies

| Strategy            | `base_threshold` | Iterations | Flagging % | Use Case                       |
| ------------------- | ---------------- | ---------- | ---------- | ------------------------------ |
| **Default**         | 1.0              | 2          | 4-5%       | Clean observations (default)   |
| **Moderate** ✨     | 0.85             | 2          | 5-6%       | Noticeable RFI (manual/future) |
| **Aggressive**      | 0.75             | 3          | 6-7%       | Heavy RFI (auto-triggered)     |
| **Very Aggressive** | 0.6              | 4          | 50%+       | Extreme RFI (manual only)      |

**Current adaptive behavior**: Default → Aggressive (two-tier)  
**Future**: Default → Moderate → Aggressive (three-tier)

## How It Works

### Calibration-Triggered Escalation Strategy

1. **Pass 1: Default Flagging**
   - Applies standard AOFlagger strategy (`dsa110-default.lua`)
   - Attempts calibration (delay, bandpass, gain solving)
   - If calibration succeeds → Done! ✓

2. **Pass 2: Aggressive Flagging** (only if Pass 1 fails)
   - Resets flags
   - Applies aggressive AOFlagger strategy (`dsa110-aggressive.lua`)
   - Retries calibration
   - Reports success or failure

### Key Features

- **Automatic**: No manual intervention required
- **Conservative by default**: Only escalates when necessary
- **Robust**: Handles contaminated observations automatically
- **Transparent**: Logs which strategy was used and why

## Configuration

### Enabling/Disabling Adaptive Flagging

Adaptive flagging is **enabled by default**. To disable it:

```python
from dsa110_contimg.pipeline.stages_impl import CalibrationSolveStage
from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.context import PipelineContext

config = PipelineConfig(...)
stage = CalibrationSolveStage(config)

context = PipelineContext(
    config=config,
    outputs={"ms_path": "/path/to/data.ms"},
    inputs={
        "calibration_params": {
            "use_adaptive_flagging": False,  # Disable adaptive flagging
            "field": "0",
            "refant": "103",
        }
    }
)

result = stage.execute(context)
```

### Customizing the Aggressive Strategy

By default, the aggressive strategy is
`/data/dsa110-contimg/config/dsa110-aggressive.lua`. To use a custom strategy:

```python
context = PipelineContext(
    config=config,
    outputs={"ms_path": "/path/to/data.ms"},
    inputs={
        "calibration_params": {
            "aggressive_strategy": "/path/to/custom-aggressive.lua",
            "field": "0",
            "refant": "103",
        }
    }
)
```

### Choosing Flagging Backend

You can choose between AOFlagger (default) and CASA tfcrop:

```python
context = PipelineContext(
    config=config,
    outputs={"ms_path": "/path/to/data.ms"},
    inputs={
        "calibration_params": {
            "flagging_backend": "casa",  # or "aoflagger" (default)
            "field": "0",
            "refant": "103",
        }
    }
)
```

## Flagging Strategies

### Default Strategy: `dsa110-default.lua`

- **Target use case**: Clean observations with minimal RFI
- **Parameters**:
  - `base_threshold = 1.0` (standard sensitivity)
  - `iteration_count = 2`
  - SIR operator = 0.2
- **Typical flagging**: 4-5%
- **Performance**: ~4-5 minutes

### Moderate Strategy: `dsa110-moderate.lua` ✨ NEW

- **Target use case**: Observations with noticeable but not severe RFI
- **Parameters**:
  - `base_threshold = 0.85` (intermediate sensitivity)
  - `iteration_count = 2`
  - SIR operator = 0.2
- **Typical flagging**: 5-6% (estimated)
- **Performance**: ~4-5 minutes
- **Use**: Manual override or future three-tier adaptive flagging

### Aggressive Strategy: `dsa110-aggressive.lua`

- **Target use case**: Contaminated observations requiring more aggressive
  flagging
- **Parameters**:
  - `base_threshold = 0.75` (increased sensitivity)
  - `iteration_count = 3`
  - SIR operator = 0.2
- **Typical flagging**: 6-7%
- **Performance**: ~4-5 minutes

### Very Aggressive Strategy: `dsa110-very-aggressive.lua`

- **Target use case**: Severely contaminated observations (manual use only)
- **Parameters**:
  - `base_threshold = 0.6` (very high sensitivity)
  - `iteration_count = 4`
  - Enhanced RMS thresholds
- **Typical flagging**: 50%+
- **Performance**: ~4-5 minutes
- **⚠️ WARNING**: May over-flag clean data. Use with caution.

## Monitoring and Debugging

### Log Output

When adaptive flagging runs, you'll see log messages like:

```
======================================================================
ADAPTIVE FLAGGING: Pass 1 - Default strategy
======================================================================
Default flagging complete: 4.46% flagged
Attempting calibration with default flagging...
✓ Calibration successful with default flagging
Adaptive flagging complete: Used default strategy
Flagging success: True, Attempts: 1
```

Or, if escalation is triggered:

```
======================================================================
ADAPTIVE FLAGGING: Pass 1 - Default strategy
======================================================================
Default flagging complete: 4.46% flagged
Attempting calibration with default flagging...
Calibration failed with default flagging: Bandpass calibration failed: ...
======================================================================
ADAPTIVE FLAGGING: Pass 2 - Aggressive strategy
======================================================================
Resetting flags for aggressive retry...
Applying aggressive flagging strategy: /data/dsa110-contimg/config/dsa110-aggressive.lua
Aggressive flagging complete: 6.19% flagged
Retrying calibration with aggressive flagging...
✓ Calibration successful with aggressive flagging
Adaptive flagging complete: Used aggressive strategy
Flagging success: True, Attempts: 2
```

### Accessing Results Programmatically

The adaptive flagging results are logged but not currently exposed in the
pipeline context. To access detailed flagging statistics, use the
`get_flag_summary` utility:

```python
from dsa110_contimg.calibration.flagging_adaptive import get_flag_summary

stats = get_flag_summary("/path/to/data.ms")
print(f"Overall flagging: {stats['overall_flagged_fraction'] * 100:.2f}%")
print(f"Per-SPW flagging: {stats['per_spw_flagging']}")
print(f"Fully flagged SPWs: {stats['fully_flagged_spws']}")
```

## Calibration Failure Detection

The pipeline detects calibration failure based on exceptions raised during:

1. **Delay (K) solving** (`solve_delay`)
2. **Pre-bandpass phase solving** (`solve_prebandpass_phase`)
3. **Bandpass (BP) solving** (`solve_bandpass`)
4. **Gain (G) solving** (`solve_gains`)

Any exception raised by these functions triggers the escalation to aggressive
flagging.

### Common Calibration Failure Causes

- **Insufficient unflagged data**: Too much data flagged in Pass 1
- **Poor SNR**: Weak calibrator or heavy RFI contamination
- **Phase wraps**: Severe ionospheric or instrumental effects
- **Non-convergence**: Solver fails to find stable solutions

## Best Practices

### When to Use Adaptive Flagging

✅ **Use adaptive flagging (default behavior)** when:

- Processing observations with unknown RFI levels
- Running automated pipelines
- Dealing with time-variable RFI environments
- Processing large batches of data

### When to Disable Adaptive Flagging

❌ **Disable adaptive flagging** when:

- You know the data is clean (saves processing time)
- You want to manually control flagging strategy
- You're testing specific flagging parameters
- You need deterministic behavior for benchmarking

### Manual Strategy Selection

For manual control without adaptive behavior, disable adaptive flagging and
specify a strategy directly:

```python
# Example: Use moderate strategy manually
from dsa110_contimg.calibration.flagging import flag_rfi

flag_rfi(
    "/path/to/data.ms",
    backend="aoflagger",
    strategy="/data/dsa110-contimg/config/dsa110-moderate.lua"
)

# Then run calibration normally with adaptive flagging disabled
context = PipelineContext(
    config=config,
    outputs={"ms_path": "/path/to/data.ms"},
    inputs={
        "calibration_params": {
            "use_adaptive_flagging": False,  # Don't re-flag
            "do_flagging": False,             # Skip flagging entirely
            "field": "0",
            "refant": "103",
        }
    }
)
```

Or use the aggressive strategy with custom parameters:

```python
# Example: Use custom aggressive strategy path
context = PipelineContext(
    config=config,
    outputs={"ms_path": "/path/to/data.ms"},
    inputs={
        "calibration_params": {
            "aggressive_strategy": "/data/dsa110-contimg/config/dsa110-moderate.lua",
            "field": "0",
            "refant": "103",
        }
    }
)
```

## Performance Considerations

- **Pass 1 (default)**: ~4-5 minutes for typical observation
- **Pass 2 (aggressive)**: Additional ~4-5 minutes if triggered
- **Total worst case**: ~9-10 minutes for observations requiring escalation
- **Typical case**: ~4-5 minutes (no escalation needed)

## Troubleshooting

### Problem: Both strategies fail calibration

**Symptoms**: Log shows "Calibration failed even with aggressive flagging"

**Possible causes**:

1. Data quality is too poor for any calibration
2. Wrong calibrator source model
3. Antenna or hardware issues
4. Extreme RFI beyond flagging capability

**Solutions**:

- Check calibrator flux and position
- Inspect data manually with CASA
- Try very aggressive strategy manually
- Consider excluding bad antennas

### Problem: Over-flagging with aggressive strategy

**Symptoms**: >20% of data flagged, poor imaging results

**Possible causes**:

- Aggressive strategy too sensitive for this observation
- Data genuinely contaminated

**Solutions**:

- Create custom intermediate strategy (e.g., `base_threshold = 0.80`)
- Review flagging statistics per SPW
- Inspect data manually to confirm RFI presence

### Problem: Adaptive flagging not triggering when expected

**Symptoms**: Calibration succeeds with default strategy despite visible RFI

**Possible causes**:

- RFI not severe enough to cause calibration failure
- Calibration solver is robust to moderate RFI

**Solutions**:

- This is expected behavior - default strategy is working!
- If you need more aggressive flagging, disable adaptive mode and use aggressive
  strategy manually
- Review calibration quality metrics (phase/amplitude RMS)

## Related Documentation

- [RFI Backend Comparison Testing](RFI_BACKEND_COMPARISON_QUICK_REFERENCE.md)
- [AOFlagger Strategy Tuning](AOFLAGGER_STRATEGY_TUNING.md)
- [Automatic Flagging Strategy Selection](AUTOMATIC_FLAGGING_STRATEGY_SELECTION.md)
- [Temporal Flagging System](temporal_flagging_system.md)

## Implementation Details

### File Structure

- **Core logic**: `dsa110_contimg/calibration/flagging_adaptive.py`
  - `flag_rfi_adaptive()`: Main adaptive flagging function
  - `CalibrationFailure`: Exception for calibration failures
  - `get_flag_summary()`: Utility for flagging statistics

- **Pipeline integration**: `dsa110_contimg/pipeline/stages_impl.py`
  - `CalibrationSolveStage._execute_calibration_solve()`: Modified to use
    adaptive flagging

- **Strategies**:
  - `/data/dsa110-contimg/config/dsa110-default.lua`
  - `/data/dsa110-contimg/config/dsa110-aggressive.lua`
  - `/data/dsa110-contimg/config/dsa110-very-aggressive.lua`

### API Example

For standalone use outside the pipeline:

```python
from dsa110_contimg.calibration.flagging_adaptive import (
    flag_rfi_adaptive,
    CalibrationFailure,
)

def my_calibration_function(ms_path, refant, **kwargs):
    """Your calibration logic here."""
    # Raise CalibrationFailure if calibration fails
    if calibration_fails:
        raise CalibrationFailure("Calibration failed: poor SNR")

result = flag_rfi_adaptive(
    ms_path="/path/to/data.ms",
    refant="103",
    calibrate_fn=my_calibration_function,
    calibrate_kwargs={},
    aggressive_strategy="/data/dsa110-contimg/config/dsa110-aggressive.lua",
    backend="aoflagger",
)

print(f"Strategy used: {result['strategy']}")
print(f"Success: {result['success']}")
print(f"Attempts: {result['attempts']}")
print(f"Flagging stats: {result['flagging_stats']}")
```

---

**Last Updated**: November 19, 2025 **Version**: 1.0 **Author**: DSA-110
Pipeline Team
