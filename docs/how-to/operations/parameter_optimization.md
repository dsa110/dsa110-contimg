# AOFlagger Parameter Optimization Guide

## Overview

This guide describes the systematic methodology for determining optimal
thresholds and parameters for the DSA-110 AOFlagger Lua strategy. The process is
iterative, data-driven, and uses statistical validation to ensure both effective
RFI removal and minimal data loss.

## Optimization Algorithm

### Phase 1: Baseline Establishment

**Goal:** Establish baseline measurements with current/default parameters

1. **Select representative test dataset**
   - Use a known-good calibrator observation (bright, stable source)
   - Should represent typical observation conditions
   - Ideally 5-10 minutes of data

2. **Run baseline flagging**

   ```bash
   # Current default strategy
   python -m dsa110_contimg.calibration.cli flag \
     --ms test_ms.ms --mode rfi --rfi-backend aoflagger \
     --aoflagger-strategy docs/aoflagger/dsa110-default.lua
   ```

3. **Record baseline metrics**
   - Flagging percentage
   - Flagging statistics per antenna/polarization
   - Calibration quality (SNR, solution residuals)
   - Image quality (noise level, dynamic range)

4. **Compare with CASA results**
   - Run equivalent CASA `tfcrop+rflag` flagging
   - Compare flagging percentages and calibration quality
   - Note any systematic differences

### Phase 2: Single-Parameter Sweep

**Goal:** Understand individual parameter impact

For each parameter, perform a systematic sweep:

#### 2.1 Base Threshold (`base_threshold`)

**Sweep range:** 0.5 to 2.0 (step: 0.2)

```lua
local base_threshold = 0.5  -- Test value
```

**Metrics to track:**

- Flagging percentage vs threshold
- Calibration SNR vs threshold
- Image noise vs threshold

**Expected behavior:**

- Lower threshold → more flags, lower noise, risk of false positives
- Higher threshold → fewer flags, higher noise, risk of missed RFI

**Optimal selection criteria:**

- Find threshold where flagging percentage plateaus (diminishing returns)
- Ensure calibration SNR ≥ 50 (for bright calibrators)
- Ensure image noise is within 10% of CASA results

#### 2.2 Transient Threshold Factor (`transient_threshold_factor`)

**Sweep range:** 0.5 to 2.0 (step: 0.25)

```lua
local transient_threshold_factor = 0.5  -- Test value
```

**Metrics to track:**

- Transient RFI detection rate
- Time-variable flagging patterns
- Impact on satellite RFI (GPS, etc.)

**Optimal selection:**

- Lower if transient RFI is common (satellites, sporadic interference)
- Higher if RFI is mostly static/persistent

#### 2.3 Iteration Count (`iteration_count`)

**Sweep range:** 2 to 5 (step: 1)

```lua
local iteration_count = 2  -- Test value
```

**Metrics to track:**

- Processing time vs iteration count
- Flagging completeness (does more iterations catch more RFI?)
- Diminishing returns analysis

**Optimal selection:**

- Typically 3 iterations is optimal (good balance)
- More iterations only if RFI is very subtle
- Fewer iterations if processing time is critical

#### 2.4 Frequency Resize Factor (`frequency_resize_factor`)

**Sweep range:** 0.5 to 2.0 (step: 0.5)

```lua
local frequency_resize_factor = 0.5  -- Test value
```

**Metrics to track:**

- Broadband RFI detection
- Impact on narrow-band RFI (may be suppressed)
- Bandpass shape preservation

**Optimal selection:**

- Higher if RFI is broadband
- Lower if RFI is narrow-band (specific channels)

### Phase 3: Multi-Parameter Optimization

**Goal:** Find optimal combination of parameters

**Method:** Grid search or coordinate descent

1. **Start with best single-parameter values** from Phase 2

2. **Grid search approach:**
   - Test combinations of 2-3 key parameters simultaneously
   - Example: `base_threshold` × `transient_threshold_factor` grid
   - Evaluate each combination using metrics below

3. **Coordinate descent approach:**
   - Optimize one parameter at a time, keeping others fixed
   - Iterate until convergence (no improvement)

### Phase 4: Validation

**Goal:** Verify optimal parameters on independent datasets

1. **Validation dataset**
   - Different calibrator
   - Different time/date
   - Different observing conditions

2. **Metrics for validation:**
   - Flagging percentage (should be consistent ±5%)
   - Calibration quality (SNR, solution stability)
   - Image quality (noise, dynamic range, artifacts)
   - Comparison with CASA results

3. **Cross-validation:**
   - Test on 5-10 different observations
   - Ensure parameters are robust across conditions

## Evaluation Metrics

### Primary Metrics

1. **Flagging Percentage**

   ```python
   flagged_fraction = flagged_points / total_points
   ```

   - **Target range:** 2-10% (depends on RFI environment)
   - **Too high (>20%):** Over-flagging, losing data
   - **Too low (<1%):** Under-flagging, RFI may remain

2. **Calibration Quality**
   - **Bandpass SNR:** Should be ≥ 50 for bright calibrators
   - **Gain solution stability:** RMS phase should be < 10°
   - **Solution flags:** < 10% of solutions should be flagged

3. **Image Quality**
   - **Noise level:** Should match CASA results within 10%
   - **Dynamic range:** Should not degrade significantly
   - **Artifacts:** Should not introduce new imaging artifacts

### Secondary Metrics

4. **Flagging Distribution**
   - Flags per antenna (should be roughly uniform)
   - Flags per polarization (should be roughly uniform)
   - Flags per time (identify problematic time ranges)
   - Flags per frequency (identify problematic channels)

5. **Processing Time**
   - Should be acceptable for pipeline operations
   - Compare with CASA flagging time

6. **False Positive Rate**
   - Inspect flagged data visually (if possible)
   - Check for legitimate signal being flagged
   - Compare with CASA results

## Automated Optimization Script

Here's a template for automated parameter optimization:

```python
#!/usr/bin/env python3
"""
AOFlagger Parameter Optimization Script

Sweeps through parameter space and evaluates each combination.
"""

import subprocess
import numpy as np
from casacore.tables import table

def evaluate_flagging(ms_path, strategy_path, params):
    """Run flagging and return metrics."""
    # Run AOFlagger with strategy
    subprocess.run([
        'docker', 'run', '--rm',
        '-v', '/scratch:/scratch', '-v', '/data:/data',
        'aoflagger:latest', 'aoflagger',
        '-strategy', strategy_path,
        ms_path
    ], check=True)

    # Calculate metrics
    with table(ms_path, readonly=True) as tb:
        flags = tb.getcol('FLAG')
        total = flags.size
        flagged = np.sum(flags)
        flag_pct = flagged / total * 100

    # Run calibration to get SNR
    # ... calibration code ...
    # bp_snr = get_bandpass_snr(ms_path)

    return {
        'flag_pct': flag_pct,
        # 'bp_snr': bp_snr,
        # ... other metrics ...
    }

def optimize_parameters(test_ms, strategy_template):
    """Grid search for optimal parameters."""
    # Parameter ranges
    base_thresholds = np.arange(0.5, 2.1, 0.2)
    transient_factors = np.arange(0.5, 2.1, 0.25)

    best_score = -np.inf
    best_params = None
    results = []

    for base_thr in base_thresholds:
        for trans_fac in transient_factors:
            # Create strategy with these parameters
            params = {
                'base_threshold': base_thr,
                'transient_threshold_factor': trans_fac
            }
            strategy_path = create_strategy(strategy_template, params)

            # Evaluate
            metrics = evaluate_flagging(test_ms, strategy_path, params)

            # Score (example: maximize calibration SNR, minimize flagging)
            score = metrics.get('bp_snr', 0) - metrics['flag_pct'] * 0.1

            results.append({
                'params': params,
                'metrics': metrics,
                'score': score
            })

            if score > best_score:
                best_score = score
                best_params = params

    return best_params, results

if __name__ == '__main__':
    # Run optimization
    best_params, all_results = optimize_parameters(
        test_ms='/scratch/test_ms.ms',
        strategy_template='docs/aoflagger/dsa110-default.lua'
    )
    print(f"Best parameters: {best_params}")
```

## Reference Comparisons

### Similar Telescopes

Compare with strategies from similar telescopes:

1. **JVLA (L-band, interferometer)**
   - `jvla-default.lua` - Good starting point
   - Similar frequency range (~1.4 GHz)
   - Similar baseline lengths

2. **ATCA L-band**
   - `atca-l-band.lua` - L-band specific
   - May have similar RFI environment

3. **LOFAR**
   - Lower frequency but similar RFI challenges
   - More aggressive flagging typically needed

### CASA Baseline

Always compare final results with CASA `tfcrop+rflag`:

- **Flagging percentage:** Should be within ±2% of CASA
- **Calibration quality:** Should match or exceed CASA
- **Image quality:** Should match or exceed CASA

## Iterative Refinement Process

```
1. Start with default parameters
   ↓
2. Test on single observation
   ↓
3. Evaluate metrics (flagging %, calibration SNR, image quality)
   ↓
4. Adjust one parameter
   ↓
5. Re-test and compare
   ↓
6. If improved → keep, if not → revert
   ↓
7. Test on validation dataset
   ↓
8. If robust → finalize, if not → refine further
```

## Common Optimization Patterns

### Pattern 1: High RFI Environment

**Symptoms:**

- Flagging < 5% but RFI still visible
- Calibration solutions have high scatter

**Optimization:**

- Lower `base_threshold` (0.7-0.8)
- Lower `transient_threshold_factor` (0.7-0.8)
- Increase `iteration_count` (4-5)

### Pattern 2: Low RFI Environment

**Symptoms:**

- Flagging > 10% but little visible RFI
- Calibration SNR is low (too much data flagged)

**Optimization:**

- Raise `base_threshold` (1.2-1.5)
- Raise `transient_threshold_factor` (1.2-1.5)
- Decrease `iteration_count` (2)

### Pattern 3: Transient RFI (Satellites)

**Symptoms:**

- Time-variable flagging patterns
- Brief spikes in flagging percentage

**Optimization:**

- Lower `transient_threshold_factor` (0.5-0.7)
- Keep `base_threshold` moderate (1.0-1.2)

### Pattern 4: Broadband RFI

**Symptoms:**

- Flags clustered in frequency ranges
- Multiple adjacent channels flagged

**Optimization:**

- Increase `frequency_resize_factor` (1.5-2.0)
- May need custom frequency-dependent thresholds

## Best Practices

1. **Start conservative:** Better to slightly under-flag than over-flag
2. **Validate on multiple datasets:** Don't optimize on single observation
3. **Document changes:** Keep track of parameter changes and their effects
4. **Compare with CASA:** Always validate against CASA results
5. **Monitor over time:** RFI environment may change seasonally
6. **Telescope-specific tuning:** Different telescopes may need different
   parameters

## Summary

The optimization algorithm follows this systematic approach:

1. **Baseline:** Establish current performance
2. **Single-parameter sweep:** Understand individual parameter impact
3. **Multi-parameter optimization:** Find optimal combinations
4. **Validation:** Verify on independent datasets
5. **Iteration:** Refine based on results

**Key principle:** Balance between RFI removal (high flagging) and data
preservation (low flagging) while maintaining calibration and image quality.
