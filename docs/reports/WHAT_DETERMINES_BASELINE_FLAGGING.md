# What Determines if a Baseline is "Affected" in Bandpass Calibration?

**Date:** 2025-11-05  
**Question:** What determines if a baseline is "affected" (has flagged solutions)? Is this flagged before the bandpass() run?

---

## Answer: Baseline Flagging is Determined DURING the Bandpass Solve

**A baseline is "affected" if the bandpass solve flags at least one solution (across both polarizations) for that baseline.**

**This flagging happens DURING the solve, not before.**

---

## The Two Types of Flagging

### 1. MS Flagging (Before Bandpass Solve)

**What it is:**
- Flags in the Measurement Set (MS) mark bad data
- These are set before calibration (RFI, zeros, data quality issues)
- Example: 5.1% of visibilities flagged in MS before bandpass solve

**Impact:**
- Reduces the amount of data available for the bandpass solve
- CASA skips flagged data when computing solutions
- But doesn't directly cause baseline flagging in the calibration table

**Example (SPW 4, chan 47):**
- MS has 4656 rows (many time samples)
- 285 baselines have some flags in the MS
- 5.1% of visibilities are flagged

### 2. Calibration Table Flagging (During Bandpass Solve)

**What it is:**
- Flags in the calibration table mark bad **solutions**
- These are set DURING the bandpass solve
- Causes: Low SNR, insufficient unflagged data, quality issues during solve

**Impact:**
- A baseline is "affected" if ≥1 solution is flagged for that baseline
- This is what determines CASA's printing threshold (28 baselines)

**Example (SPW 4, chan 47):**
- Calibration table has 117 baselines (one solution per baseline, after combining across time)
- 28 baselines have flagged solutions (22.6% flagging rate)
- 89 baselines have no flagged solutions

---

## How Bandpass Solve Works

### Data Aggregation

1. **MS has many time samples per baseline:**
   - Example: 4656 rows for SPW 4, field 0
   - Each row is a time sample for a baseline
   - Multiple time samples per baseline (due to `solint='inf'`, combines all times)

2. **Bandpass solve combines across time:**
   - Uses all unflagged time samples for each baseline
   - Produces one solution per baseline per channel per polarization
   - Combines across time using `solint='inf'`

3. **Calibration table stores one solution per baseline:**
   - 117 antenna pairs (baselines)
   - 48 channels × 2 polarizations = 234 solutions per channel
   - Each solution represents the combined result from all unflagged time samples

### When Solutions Get Flagged

Solutions are flagged during the solve if:

1. **Low SNR** (`minsnr` threshold, default 5.0)
   - Solution SNR < threshold
   - CASA reports: "X of Y solutions flagged due to SNR < threshold"

2. **Insufficient unflagged data**
   - Not enough unflagged visibilities to compute a reliable solution
   - CASA reports: "Found no unflagged data at: (time=..., field=..., spw=..., chan=...)"

3. **Quality issues**
   - Solution fails quality checks (amplitude/phase outliers)
   - Numerical issues during solve

---

## What "Baselines Affected" Means

**A baseline is "affected" if at least one solution (across both polarizations) is flagged in the calibration table.**

**Example (SPW 4, chan 47):**
- 28 baselines have flags (24% of baselines)
- 89 baselines have no flags (76% of baselines)
- Flag distribution:
  - 89 baselines: 0 flags (both polarizations good)
  - 3 baselines: 1 flag (one polarization flagged)
  - 25 baselines: 2 flags (both polarizations flagged)

**The "28 baselines affected" is what determines CASA's printing threshold.**

---

## Relationship Between MS Flags and Calibration Table Flags

### Pre-existing MS Flags Reduce Data, But Don't Directly Cause Baseline Flagging

**MS flagging (before solve):**
- 285 baselines have some flags in the MS (for chan 47)
- 5.1% of visibilities flagged
- These flags reduce the amount of data available for the solve

**Calibration table flagging (during solve):**
- 28 baselines have flagged solutions
- 22.6% of solutions flagged in the calibration table
- This is determined by the solve quality, not just pre-existing MS flags

### Why More Solutions Are Flagged Than MS Flags

**The calibration table has more flagging (22.6%) than the MS (5.1%) because:**

1. **MS flags reduce available data:**
   - With 5.1% flagged, 94.9% of data is available
   - But if SNR is low due to phase decorrelation, poor weather, etc., solutions still fail

2. **Bandpass solve has stricter quality requirements:**
   - Needs sufficient SNR (default `minsnr=5.0`)
   - Needs sufficient unflagged data
   - Phase decorrelation, RFI, or data quality issues can cause solutions to fail even if some unflagged data exists

3. **Combining across time amplifies issues:**
   - One bad time sample can affect the combined solution
   - Phase drifts cause decorrelation, reducing effective SNR

---

## Summary

**What determines if a baseline is "affected":**
- ✓ Flagged DURING the bandpass solve (not before)
- ✓ At least one solution (across both polarizations) is flagged
- ✓ Causes: Low SNR, insufficient data, quality issues during solve

**Pre-existing MS flags:**
- ✓ Reduce the amount of data available for the solve
- ✓ Don't directly cause baseline flagging in the calibration table
- ✓ But can indirectly cause flagging if insufficient unflagged data remains

**The "28 baselines affected" threshold:**
- ✓ Determines CASA's printing behavior
- ✓ Based on calibration table flags (during solve), not MS flags (before solve)
- ✓ A baseline is "affected" if ≥1 solution is flagged for that baseline

---

## Diagnostic Script

Use `scripts/analyze_baseline_flagging.py` to compare MS flags vs calibration table flags:

```bash
python3 scripts/analyze_baseline_flagging.py <ms_path> <bp_table> --spw 4 --field 0
```

This shows:
- MS flagging before bandpass solve
- Calibration table flagging after bandpass solve
- Comparison and interpretation

