# RFI Flagging Parameters Justification

**Date:** 2025-11-05  
**Parameters:** `timecutoff=4.0`, `freqcutoff=4.0` for `tfcrop` mode

---

## Current Implementation

```python
flagdata(
    vis=ms,
    mode="tfcrop",
    timecutoff=4.0,    # 4σ threshold in time
    freqcutoff=4.0,    # 4σ threshold in frequency
    timefit="line",
    freqfit="poly",
    maxnpieces=5,
    winsize=3,
    extendflags=False,
)
```

---

## Parameter Definitions

**`timecutoff` and `freqcutoff` are thresholds in units of standard deviation (N-σ):**
- Data points deviating more than N standard deviations from the fitted model are flagged
- The algorithm fits models (line in time, polynomial in frequency) and flags statistical outliers

---

## CASA Default Values

According to CASA documentation:
- **`timecutoff` default:** 4.0 σ
- **`freqcutoff` default:** 3.0 σ

**Our implementation uses:**
- `timecutoff=4.0` (matches CASA default)
- `freqcutoff=4.0` (more conservative than CASA default of 3.0)

---

## Justification for `timecutoff=4.0`

### 1. **Matches CASA Default (Standard Practice)**
- CASA's default of 4.0 σ is well-tested across many radio astronomy observations
- Widely used in VLA, ALMA, and other observatories
- Balances sensitivity to outliers with data preservation

### 2. **Statistical Significance**
- 4σ corresponds to ~0.006% probability (assuming Gaussian noise)
- For a typical MS with millions of data points, this flags only genuine outliers
- Preserves legitimate astronomical signals while catching strong RFI

### 3. **Time-Variable RFI Detection**
- RFI often appears as transient spikes in time
- 4σ threshold catches strong, isolated RFI spikes
- Less aggressive than 3σ (which would flag ~0.3% of data even in pure noise)

---

## Justification for `freqcutoff=4.0` (More Conservative Than Default)

### 1. **Frequency-Dependent RFI is Common**
- Many RFI sources are narrow-band (affect specific channels)
- Stronger threshold (4σ vs 3σ default) prevents flagging legitimate frequency structure
- Preserves bandpass shape, calibration artifacts, and source structure

### 2. **Calibrator Data Quality**
- For calibrators, we want to preserve as much data as possible for calibration
- Over-flagging reduces SNR for calibration solutions
- 4σ is more conservative: flags only the strongest RFI, preserving legitimate data

### 3. **Two-Stage Flagging Strategy**
- **Stage 1 (tfcrop):** Conservative threshold (4σ) catches obvious outliers
- **Stage 2 (rflag):** Follows with residual-based flagging to catch subtler RFI
- Two-stage approach allows conservative first stage without missing RFI

### 4. **DSA-110 Specific Considerations**
- DSA-110 operates at 1.4 GHz (L-band), which has significant RFI
- However, calibrators are typically bright (2-5 Jy), so we can afford to be conservative
- Better to slightly under-flag than over-flag and lose calibration SNR

---

## Comparison: 3.0 vs 4.0 σ

| Threshold | Approx. False Positive Rate (Gaussian) | Flagging Behavior | Use Case |
|-----------|----------------------------------------|-------------------|----------|
| **3.0 σ** | ~0.3% | More aggressive | General RFI flagging, weaker sources |
| **4.0 σ** | ~0.006% | More conservative | Calibrators, preserving data |

**Our choice (4.0 σ for both):**
- Conservative approach suitable for bright calibrators
- Preserves calibration SNR
- Two-stage flagging (tfcrop + rflag) catches subtler RFI

---

## When to Adjust These Values

### Increase (e.g., 5.0 σ) if:
- Too much data is being flagged (losing >30% of data)
- Calibrator is weak (<1 Jy)
- Need to preserve edge channels

### Decrease (e.g., 3.0 σ) if:
- RFI is still present after flagging
- Very strong RFI environment
- Non-calibrator science targets (can afford more aggressive flagging)

---

## Two-Stage Flagging Strategy

Our RFI flagging uses two stages:

1. **tfcrop (timecutoff=4.0, freqcutoff=4.0):**
   - Fits models to time/frequency
   - Flags 4σ outliers
   - **Purpose:** Catch obvious, strong RFI

2. **rflag (timedevscale=4.0, freqdevscale=4.0):**
   - Analyzes residuals after tfcrop
   - Flags residual outliers
   - **Purpose:** Catch subtler RFI that survived first stage

**Why this works:**
- First stage (tfcrop) uses conservative 4σ threshold to preserve data
- Second stage (rflag) catches RFI that wasn't obvious in first pass
- Two-stage approach is more effective than single aggressive stage

---

## References

- **CASA Documentation:** `timecutoff` default is 4.0, `freqcutoff` default is 3.0
- **VLA/ALMA Practices:** Typically use 4σ for calibrator flagging
- **Statistical Basis:** 4σ corresponds to ~0.006% false positive rate (Gaussian)

---

## Summary

**Justification for `timecutoff=4.0` and `freqcutoff=4.0`:**
1. ✓ `timecutoff=4.0` matches CASA default (standard practice)
2. ✓ `freqcutoff=4.0` is more conservative than CASA default (3.0), appropriate for:
   - Calibrator data (preserve SNR)
   - Two-stage flagging strategy
   - DSA-110 bright calibrator observations
3. ✓ Two-stage approach (tfcrop + rflag) ensures RFI is caught despite conservative first stage
4. ✓ Balances RFI removal with data preservation for calibration quality

**These values are reasonable defaults for calibrator flagging, but may need adjustment based on specific observational conditions.**

