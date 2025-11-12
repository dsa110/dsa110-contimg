# CASA Bandpass Output Format Mystery

**Date:** 2025-11-05  
**Issue:** Discrepancy between CASA's printed output and actual calibration table contents

---

## The Mystery

CASA's bandpass output shows:
```
1 of 182 solutions flagged due to SNR < 3 in spw=4 (chan=47) at 2025/10/29/13:54:18.0
```

But when we check the calibration table:
- **Total solutions for chan=47:** 234 (117 antenna pairs × 2 polarizations)
- **Flagged solutions:** 53
- **Unflagged solutions:** 181

**The "182" in CASA's output doesn't match any obvious count in our table.**

---

## What We Know

### Calibration Table Structure
- **117 rows** (antenna pairs) for SPW 4
- **48 channels** per SPW
- **2 polarizations** per channel
- **Total solutions per channel:** 117 × 2 = 234

### CASA's Output
- Reports "X of 182 solutions flagged"
- Only prints certain channels (not all with flagged solutions)
- chan=46: 52/234 flagged (22.2%) - **NOT PRINTED**
- chan=47: 53/234 flagged (22.6%) - **PRINTED**

### Observations
1. **Selective printing:** Channels with similar flagging rates aren't all printed
2. **"182" doesn't match:** Not 234 (total), not 117 (baselines), not 181 (unflagged)
3. **Threshold behavior:** chan=46 (27 baselines with flags) not printed, chan=47 (28 baselines with flags) printed

---

## Possible Explanations

### 1. Per-Time Reporting
CASA might be reporting flagging per time slot, not per channel total. But we have only 1 unique time in the table.

### 2. Per-Antenna Reporting
Maybe "182" refers to antenna solutions (not baseline solutions). But we have 117 unique antennas, not 182.

### 3. Pre-Flagged Solutions Excluded
Maybe "182" is the number of solutions that were attempted AFTER excluding already-flagged data in the MS. This would explain why it's less than 234.

### 4. CASA Version-Specific Behavior
Different CASA versions might report differently. This could be a CASA 6.x behavior.

### 5. Selective Printing Logic
CASA might only print when:
- Flagging exceeds a certain threshold (e.g., ≥28 baselines affected)
- Flagging pattern changes significantly
- Channel has specific characteristics (edge channels, RFI, etc.)

---

## What We Can Verify

1. **Check MS flagging:** How many visibilities were already flagged before bandpass solve?
2. **Check CASA version:** What version of CASA is being used?
3. **Check CASA documentation:** Does it explain the "X of Y solutions" format?
4. **Check other SPWs:** Do they show the same pattern?

---

## User Observation

**"I've never encountered this type of selective printing..."**

This suggests:
- Either this is new CASA behavior (version-specific)
- Or there's something specific about this dataset/configuration
- Or the selective printing is more subtle than expected

---

## Recommendations

1. **Check CASA version:** `casatasks.version()` or `casatools.version()`
2. **Verify MS flagging:** Check how much data was flagged before bandpass solve
3. **Compare with other datasets:** See if this behavior is consistent
4. **Check CASA logs:** Look for additional context in CASA log files
5. **Use calibration table directly:** For accurate flagging statistics, query the table directly rather than relying on CASA's printed output

---

## Bottom Line

The selective printing and "182 solutions" count are mysterious. The actual calibration table shows:
- chan=46: 52/234 flagged (22.2%) - **Not printed by CASA**
- chan=47: 53/234 flagged (22.6%) - **Printed by CASA**

**The discrepancy suggests CASA's output format may not directly correspond to the table structure, or there's additional context we're missing.**

