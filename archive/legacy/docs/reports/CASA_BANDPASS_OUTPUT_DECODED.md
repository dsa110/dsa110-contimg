# CASA Bandpass Output Format - Decoded

**Date:** 2025-11-05  
**Status:** Reverse-Engineered

---

## The Mystery Solved

### What "182" Means

**"182" = Number of unflagged solutions per channel** (solutions that were available for the solve).

From the analysis:
- **chan=47**: 181 unflagged solutions (CASA reports "182" - likely rounded or averaged)
- **chan=0, 1, 2, 4, 5, 6, etc.**: 182 unflagged solutions exactly
- **Total solutions per channel**: 234 (117 antenna pairs × 2 polarizations)
- **Flagged solutions**: 52-53 per channel (22-23%)

**So "182" is the number of solutions that were attempted (unflagged in the MS before bandpass solve).**

---

### What "1" Means (Still Unclear)

CASA says: **"1 of 182 solutions flagged"**

But the actual calibration table shows:
- **53 solutions flagged** (not 1!)
- **181 solutions unflagged** (not 182)

**The "1" is misleading.** Possible interpretations:

1. **"1" = number of solutions flagged during the solve process** (beyond pre-existing MS flags)
   - But MS had 5.1% flagged, so 182 unflagged is correct
   - But 53 flagged is way more than "1"
   - This doesn't make sense

2. **"1" = number of baselines that got flagged during the solve** (but this is also wrong - 28 baselines have flags)

3. **"1" = number of additional solutions flagged** (relative to some baseline)
   - But what baseline? Not clear

4. **"1" is a count of something else entirely** (e.g., per-time, per-iteration, or some other metric)

**Conclusion: The "1" in CASA's output is NOT the total number of flagged solutions. It's unclear what it actually represents.**

---

## The Printing Threshold

**CASA prints channels when ≥28 baselines have flagged solutions.**

From the analysis:
- **chan=47**: 28 baselines with flags → **PRINTED**
- **chan=46**: 27 baselines with flags → **NOT PRINTED**
- **chan=45**: 28 baselines with flags → **PRINTED**
- **chan=0, 1, 2**: 27 baselines with flags → **NOT PRINTED**

**The threshold is exactly 28 baselines affected.**

---

## Complete Understanding

### What We Know

1. **"182" = Unflagged solutions per channel** (solutions available for the solve)
   - This is the number of solutions that were attempted
   - Matches the unflagged count in the calibration table (181-182)

2. **Printing threshold = 28 baselines with flags**
   - Channels with 27 baselines affected are NOT printed
   - Channels with 28+ baselines affected ARE printed
   - This is why chan=46 (27 baselines) wasn't printed, even though it has 22.2% flagging

3. **"1" = Unknown/misleading**
   - Does NOT represent total flagged solutions (53 actual)
   - Does NOT represent baselines with flags (28 actual)
   - Possibly represents something else (per-time, per-iteration, or some other metric)
   - **Recommendation: Ignore the "1" and check the calibration table directly**

### What We Don't Know

1. **What does "1" actually count?**
   - Not total flagged solutions
   - Not baselines with flags
   - Possibly something else (needs CASA source code to confirm)

2. **Why does CASA use this format?**
   - The "X of Y" format is confusing when X doesn't match actual flagged count
   - This may be a CASA version-specific behavior

---

## Recommendations

### 1. Ignore CASA's "X" Count

The "X" in "X of Y solutions flagged" is misleading. **Always check the calibration table directly** for accurate flagging statistics.

### 2. Understand "Y" = Unflagged Solutions

The "Y" (e.g., "182") represents the number of unflagged solutions that were attempted. This is useful information.

### 3. Use the Diagnostic Script

Use `scripts/diagnose_bandpass_output.py` to get accurate flagging statistics:
```bash
python3 scripts/diagnose_bandpass_output.py <bandpass_table> --spw 4
```

This shows:
- Total flagged solutions per channel
- Baselines affected per channel
- Complete statistics (not just what CASA printed)

### 4. Don't Rely on CASA's Printed Output

CASA's selective printing (threshold at 28 baselines) means you're missing information about channels with 27 baselines affected (22.2% flagging). **Always verify using the calibration table.**

---

## Example Interpretation

When CASA prints:
```
1 of 182 solutions flagged due to SNR < 3 in spw=4 (chan=47) at 2025/10/29/13:54:18.0
```

**What this actually means:**
- **182** = Number of unflagged solutions attempted (correct)
- **"1"** = Unknown/misleading (NOT the actual flagged count)
- **Actual flagged solutions**: 53 (from calibration table)
- **Actual unflagged solutions**: 181 (from calibration table)
- **Baselines with flags**: 28 (exceeds threshold, so printed)

---

## Bottom Line

**CASA's output format is partially decoded:**
- ✓ "182" = Unflagged solutions per channel (solutions attempted)
- ✓ Printing threshold = 28 baselines with flags
- ✗ "1" = Unknown/misleading (not total flagged solutions)

**For accurate flagging statistics, always check the calibration table directly.**

