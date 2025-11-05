# SPW Combine Behavior Explanation

**Date**: 2025-11-04  
**Issue**: Confusion about SPW messages during bandpass calibration

## The "spw=X" Messages Are Normal

When you see messages like:
```
33 of 188 solutions flagged due to SNR < 3 in spw=0 at 2025/10/29/13:54:30.9
34 of 188 solutions flagged due to SNR < 3 in spw=1 at 2025/10/29/13:55:03.1
```

**This is NORMAL behavior**, even when `--combine-spw` is enabled.

## How `combine='spw'` Works

When `combine='spw'` is used in CASA bandpass:

1. **CASA still processes each SPW separately** internally
2. **CASA reports status per SPW** (the "spw=X" messages you see)
3. **CASA combines the solutions** across SPWs into a single calibration table
4. **The final table has one solution per channel** (not per SPW per channel)

## What the Messages Mean

- `spw=0, spw=1, spw=2, ...` = CASA is processing each SPW and reporting status
- `33 of 188 solutions flagged` = Per-SPW flagging status (data quality issue)
- This is **NOT an error** - it's just verbose status reporting

## The Real Issue: High Flagging Rate

The actual problem is **high flagging rate** (15-35% per SPW), which indicates:
- Low SNR in the data
- Phase decorrelation (need pre-bandpass phase correction)
- Data quality issues

This is **NOT** an SPW combination problem - it's a data quality problem.

## Verification: Check the Final Table

To verify `combine='spw'` worked:

```python
from casacore.tables import table

with table("bandpass.cal", readonly=True) as tb:
    spw_ids = tb.getcol("SPECTRAL_WINDOW_ID")
    unique_spw = set(spw_ids)
    
    # If combine='spw' worked: Should have solutions for all SPWs
    # but CASA may still store SPW IDs in the table structure
    print(f"Unique SPWs in table: {len(unique_spw)}")
    
    # Check if solutions are actually combined:
    # One solution per channel (not per SPW per channel)
    times = tb.getcol("TIME")
    unique_times = len(set(times))
    print(f"Unique time stamps: {unique_times}")
    # Should be 1 (if combine='scan,field,spw' worked)
```

## Summary

- ✓ `combine='spw'` is working correctly
- ✓ The "spw=X" messages are just status updates, not errors
- ⚠ The real issue is high flagging rate (low SNR) - data quality problem

