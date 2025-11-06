# CASA Bandpass Output - Resolved

**Date:** 2025-11-05  
**Status:** Pattern Identified

---

## The Pattern

After analyzing the calibration table, we found a clear threshold:

**CASA prints channels when ≥28 baselines have flagged solutions:**

| Baselines Affected | Flagged | Unflagged | Printed? | Examples |
|-------------------|---------|-----------|----------|----------|
| **28** | 53/234 | 181/234 | **YES** | chan=3, 14, 15, 17, 18, 24, 25, 28, 29, 30, 31, 32, 35, 36, 39, 41, 42, 43, 44, 45, 47 |
| **27** | 52/234 | 182/234 | **NO** | chan=0, 1, 2, 4, 5, 6, 9, 10, 11, 12, 13, 16, 26, 33, 34, 37, 38, 40, 46 |
| **29** | 54/234 | 180/234 | **YES** | chan=20, 23, 27 |
| **30** | 55/234 | 179/234 | **YES** | chan=19, 21, 22 |

**The threshold is exactly 28 baselines.**

---

## What "182 solutions" Means

CASA's "1 of 182 solutions flagged" format:
- **182** = Number of **unflagged solutions** that were evaluated
- **1** = Number that got flagged during the solve (but this is misleading - it's actually 53 total flagged)

**The "1" in the output is misleading** - it's not 1 solution flagged, but rather 1 additional solution that failed during the solve process (or CASA's counting is different).

---

## Why This Matters

**Channels with 27 baselines affected (52/234 flagged) are NOT printed**, even though they have:
- 22.2% flagging rate (significant!)
- Only 1 fewer baseline affected than printed channels

**This means you're missing information about channels with substantial flagging.**

---

## Recommendations

### 1. Use the Diagnostic Script

Run the diagnostic script to see ALL channels:
```bash
python3 scripts/diagnose_bandpass_output.py <bandpass_table> [--spw N]
```

This shows:
- Complete flagging statistics for ALL channels
- Baselines affected per channel
- Which channels match CASA's "182" count
- Channels with significant flagging (regardless of whether CASA printed them)

### 2. Don't Rely on CASA's Printed Output

**Always check the calibration table directly** for accurate flagging statistics. CASA's selective printing (threshold at 28 baselines) means you're missing information about channels with 27 baselines affected.

### 3. Interpret the Output Correctly

When CASA says "1 of 182 solutions flagged":
- This refers to unflagged solutions evaluated (182)
- The "1" doesn't mean only 1 solution was flagged total
- Check the table for actual flagging counts

### 4. Quality Assessment

**For your calibration:**
- Channels with 27 baselines affected (22.2% flagging) are still problematic
- Don't ignore channels just because CASA didn't print them
- Use the diagnostic script to see the complete picture

---

## Diagnostic Script Usage

```bash
# Analyze all SPWs
python3 scripts/diagnose_bandpass_output.py /path/to/bpcal

# Analyze specific SPW
python3 scripts/diagnose_bandpass_output.py /path/to/bpcal --spw 4
```

The script provides:
- Complete channel-by-channel flagging statistics
- Baselines affected per channel
- Identification of channels matching CASA's "182" count
- Clear summary of which channels have significant flagging

---

## Bottom Line

**CASA's selective printing has a threshold at 28 baselines affected.** Channels with 27 baselines affected (22.2% flagging) are not printed, even though they have substantial flagging.

**Always verify flagging statistics from the calibration table directly** rather than relying on CASA's printed output.

