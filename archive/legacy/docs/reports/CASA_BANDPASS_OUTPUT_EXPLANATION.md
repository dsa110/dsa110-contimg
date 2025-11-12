# CASA Bandpass Output Explanation

**Date:** 2025-11-05  
**Question:** Why are only certain channels printed during bandpass solve?

---

## Answer: CASA Only Prints Channels with Flagged Solutions

CASA's `bandpass` task **only prints messages for channels where solutions were flagged** due to low SNR or other issues. This is by design to keep the output manageable.

### What You See

```
1 of 182 solutions flagged due to SNR < 3 in spw=4 (chan=47) at 2025/10/29/13:54:18.0
1 of 182 solutions flagged due to SNR < 3 in spw=4 (chan=45) at 2025/10/29/13:54:18.0
...
94 of 182 solutions flagged due to SNR < 3 in spw=4 (chan=7) at 2025/10/29/13:54:18.0
```

### What This Means

- **Channels listed:** Have some flagged solutions (SNR < threshold)
- **Channels NOT listed:** All solutions passed SNR threshold (no flagging needed)
- **This is GOOD** - channels not listed are working correctly!

### Example from Your Output

For SPW 4 (typically 48 channels), you see messages for:
- chan=47, 45, 44, 43, 42, 41, 39, 36, 35, 32, 31, 30, 29, 28, 27, 25, 24, 23, 22, 21, 20, 19, 18, 17, 15, 14, 8, 7, 3

**Channels NOT listed** (e.g., 0, 1, 2, 4, 5, 6, 9, 10, 11, 12, 13, 16, 26, 33, 34, 37, 38, 40, 46, ...) have:
- **All solutions passing SNR** (no flagging needed)
- **No messages printed** (CASA default behavior)

---

## Why CASA Does This

If CASA printed a message for every channel:
- **48 channels × 16 SPWs = 768 messages** (even if all good)
- Output would be thousands of lines for a single solve
- Makes it hard to spot actual problems

**CASA's philosophy:** Only report what's wrong, not what's right.

---

## How to See All Channels

If you want to see ALL channels (including good ones), you have a few options:

### Option 1: Check the Calibration Table Directly

```python
from casacore.tables import table
import numpy as np

bp_table = "2025-10-29T13:54:17_0_bpcal"

with table(bp_table, readonly=True) as tb:
    # Get all channels per SPW
    spw_ids = tb.getcol("SPECTRAL_WINDOW_ID")
    channel_ids = tb.getcol("CHAN")  # Channel indices
    flags = tb.getcol("FLAG")
    
    # Group by SPW and channel
    for spw in np.unique(spw_ids):
        spw_mask = spw_ids == spw
        channels = np.unique(channel_ids[spw_mask])
        
        print(f"SPW {spw}: {len(channels)} channels with solutions")
        print(f"  Channels: {channels}")
        
        # Check flagging per channel
        for chan in channels:
            chan_mask = (spw_ids == spw) & (channel_ids == chan)
            n_flagged = np.sum(flags[chan_mask])
            n_total = np.sum(chan_mask)
            if n_flagged > 0:
                print(f"    chan={chan}: {n_flagged}/{n_total} flagged")
            else:
                print(f"    chan={chan}: {n_total}/{n_total} unflagged (all good!)")
```

### Option 2: Use CASA's `plotcal` Task

```python
from casatasks import plotcal

plotcal(
    caltable="2025-10-29T13:54:17_0_bpcal",
    xaxis="chan",
    yaxis="amp",  # or "phase"
    spw="4",
    plotsymbol="o",
    plotrange=[0, 48, 0, 2]  # Shows all channels
)
```

### Option 3: Increase CASA Logging Verbosity

CASA doesn't provide a direct way to print all channels, but you can check the calibration table after solve to see all channels.

---

## Update: Mystery Solved?

Upon closer inspection, there's a discrepancy:
- CASA reports "1 of 182 solutions flagged" for chan=47
- Table shows 53 flagged out of 234 total (181 unflagged)
- **"182" might refer to unflagged solutions evaluated**

However, **selective printing behavior is unusual** - chan=46 (52/234 flagged, 182 unflagged) wasn't printed, while chan=47 (53/234 flagged, 181 unflagged) was printed.

**This suggests CASA has additional logic for when to print** that isn't fully understood.

---

## Summary

**Question:** Why are only certain channels printed?

**Answer:** CASA's selective printing behavior is not fully understood. It may depend on:
- Number of baselines affected (threshold ~28 baselines)
- Pattern of flagging (not just count)
- CASA version-specific behavior

**To see all channels:** Check the calibration table directly or use `plotcal` for accurate statistics.

**Bottom line:** The selective printing is mysterious. Always verify flagging statistics from the calibration table directly rather than relying solely on CASA's printed output.

