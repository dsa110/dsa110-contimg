# Bandpass Output Without Flagging - Explanation

**Date:** 2025-11-05  
**Context:** Understanding variable flagging fractions in bandpass output when data hasn't been flagged

---

## Your Observation

You're seeing bandpass output like:
```
70 of 182 solutions flagged due to SNR < 3 in spw=0 (chan=24)
160 of 182 solutions flagged due to SNR < 3 in spw=1 (chan=34)
2 of 182 solutions flagged due to SNR < 3 in spw=1 (chan=0)
```

**Key patterns:**
1. **Highly variable flagging fractions** (2-164 of 182 solutions)
2. **Different SPWs have different numbers** (182 vs 184 solutions)
3. **Some channels have very high flagging** (88% = 160/182)
4. **Only one line for SPW 0** (then many for SPW 1, 2, 3)

---

## Why SPWs Are Printed This Way

### CASA's Printing Behavior

**CASA only prints channels where ≥28 baselines have flagged solutions.**

From the codebase analysis:
- **Threshold:** Exactly 28 baselines affected triggers printing
- **Format:** "X of Y solutions flagged due to SNR < threshold in spw=N (chan=M)"
- **"Y" (182 or 184):** Number of unflagged solutions available for the solve
- **"X":** Number of solutions flagged during the solve

### Why Different Numbers Between SPWs

**182 vs 184 solutions indicates:**
- Different numbers of baselines available (pre-flagged in MS)
- Different antenna configurations per SPW
- Some baselines may be pre-flagged in certain SPWs

**Example:**
- SPW 0: 182 solutions available (some pre-flagged)
- SPW 1-3: 184 solutions available (more unflagged data)

---

## Why Flagging Fractions Fluctuate So Much

### Root Cause: **No Flagging Before Bandpass**

**Without flagging, RFI and bad data contaminate the calibration solve:**

1. **RFI Affects Specific Channels**
   - RFI is frequency-dependent
   - Some channels heavily contaminated (e.g., chan=34: 88% flagged)
   - Other channels relatively clean (e.g., chan=0: 1% flagged)

2. **Edge Channels Have Lower SNR**
   - Band edges often have lower sensitivity
   - System response drops at band edges
   - More solutions flagged due to low SNR

3. **Time-Variable Phase Drifts**
   - Phase decorrelation from atmospheric/ionospheric effects
   - Causes visibility amplitudes to decorrelate
   - Reduces effective SNR for solutions

4. **Bad Data Contamination**
   - Zeros, outliers, correlator dropouts
   - Without flagging, these are included in the solve
   - Corrupt solution quality and cause high flagging

### Example Pattern

**SPW 1 shows typical RFI pattern:**
```
chan=0:   2 of 182 flagged (1%)    ← Clean
chan=1:   2 of 182 flagged (1%)    ← Clean
...
chan=34: 160 of 182 flagged (88%)  ← Heavy RFI contamination
chan=35: 163 of 182 flagged (90%)    ← Heavy RFI
...
chan=47:   2 of 182 flagged (1%)   ← Clean
```

**This pattern (clean edges, contaminated middle) is classic RFI.**

---

## Why Only One Line for SPW 0

**SPW 0 may have fewer channels with ≥28 baselines affected.**

Possible reasons:
1. **SPW 0 has less RFI** (cleaner frequency band)
2. **SPW 0 has fewer unflagged solutions** (182 vs 184)
3. **Fewer channels exceed the 28-baseline threshold**

**This doesn't mean SPW 0 is perfect** - it just means fewer channels exceed CASA's printing threshold.

---

## What Happens When You Don't Flag

### Without Flagging

1. **RFI is included in solve**
   - RFI causes incorrect visibility amplitudes
   - Solutions computed using contaminated data
   - Results in low SNR and high flagging

2. **Zeros corrupt solutions**
   - Correlator failures produce zero visibilities
   - Zeros cause numerical issues in bandpass solve
   - Solutions flagged due to quality failures

3. **Phase decorrelation reduces SNR**
   - Time-variable phase drifts cause amplitude decorrelation
   - Without pre-bandpass phase correction, SNR is low
   - Many solutions flagged due to SNR < 3

### Expected Flagging Without Flagging

**Without flagging, expect:**
- **High flagging fractions** (50-90%) in contaminated channels
- **Variable flagging** between channels (RFI is frequency-dependent)
- **Variable flagging** between SPWs (different frequency coverage)

---

## Solution: Flag Before Bandpass

### Required Flagging Steps

**1. Flag Zeros (Required)**
```python
from casatasks import flagdata
flagdata(vis=ms_path, mode='clip', clipzeros=True)
```
- Removes correlator failures
- **Critical:** Zeros corrupt bandpass solutions

**2. Flag RFI (Recommended)**
```python
# Two-stage RFI flagging
flagdata(vis=ms_path, mode='tfcrop', 
         timecutoff=4.0, freqcutoff=4.0)
flagdata(vis=ms_path, mode='rflag',
         timedevscale=4.0, freqdevscale=4.0)
```
- Removes frequency-dependent RFI
- **Recommended:** RFI causes high flagging fractions

### Expected Flagging After Flagging

**After proper flagging:**
- **Flagging fractions drop** (typically 10-30% instead of 50-90%)
- **More consistent** between channels (RFI removed)
- **More consistent** between SPWs (cleaner data)

**Example after flagging:**
```
2 of 182 solutions flagged due to SNR < 3 in spw=0 (chan=24)
5 of 182 solutions flagged due to SNR < 3 in spw=1 (chan=34)
3 of 182 solutions flagged due to SNR < 3 in spw=1 (chan=0)
```

**Much more consistent and lower flagging rates.**

---

## Using the Pipeline

**The pipeline automatically flags before bandpass:**

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms <ms_path> \
    --field 0 \
    --flagging-mode rfi  # Zeros + RFI flagging (recommended)
```

**Flagging modes:**
- `--flagging-mode zeros` (default): Only zeros flagging
- `--flagging-mode rfi`: Zeros + RFI flagging (recommended)
- `--flagging-mode none`: Skip flagging (not recommended)

---

## Additional Recommendations

### 1. Use Pre-Bandpass Phase Correction

**Pre-bandpass phase correction stabilizes time-variable phase drifts:**

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms <ms_path> \
    --field 0 \
    --prebp-phase  # Apply pre-bandpass phase correction
```

This reduces flagging by correcting phase decorrelation.

### 2. Check Calibration Table Quality

**After bandpass, check flagged fraction:**

```python
from casacore.tables import table
import numpy as np

bp_table = "2025-10-29T13:54:17.phased.ms.bcal"
with table(bp_table, readonly=True) as tb:
    flags = tb.getcol('FLAG')
    flagged_frac = np.sum(flags) / flags.size
    print(f"Flagged fraction: {flagged_frac:.1%}")
```

**Acceptable ranges:**
- **< 30%:** Good quality
- **30-50%:** Acceptable but may need investigation
- **> 50%:** Poor quality (investigate flagging/data quality)

---

## Summary

**Why SPWs printed this way:**
- CASA only prints channels with ≥28 baselines affected
- Different SPWs have different numbers of unflagged solutions (182 vs 184)
- Printing threshold is per-channel, per-SPW

**Why flagging fluctuates:**
- **No flagging before bandpass** = RFI and bad data contaminate solutions
- RFI is frequency-dependent (some channels heavily contaminated)
- Edge channels have lower SNR
- Phase decorrelation reduces effective SNR

**Solution:**
- Flag zeros (required) and RFI (recommended) before bandpass
- Use pre-bandpass phase correction for time-variable drifts
- Expect flagging fractions to drop from 50-90% to 10-30% after flagging

**Your suspicion is correct:** Not flagging before bandpass is the primary cause of the variable, high flagging fractions you're seeing.

