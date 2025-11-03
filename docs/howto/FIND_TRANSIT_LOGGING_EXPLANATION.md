# Why Transit Finding Only Shows Failed Days

## Problem

When searching for calibrator transits, the logs only show days where **no data was found**:

```
2025-11-03 00:50:33 - INFO - No subband files found between 2025-10-27 13:33:18 and 2025-10-27 14:33:18
2025-11-03 00:50:36 - INFO - No subband files found between 2025-10-23 13:49:01 and 2025-10-23 14:49:01
...
2025-11-03 00:50:47 - ERROR - Failed to find calibrator transit: No transit found
```

**Days with data are completely missing from the logs.**

## Root Cause

The `find_transit()` method in `CalibratorMSGenerator` was **silently skipping successful cases**:

1. **When no groups found**: `find_subband_groups()` logs "No subband files found" → we see this
2. **When groups found**: `find_transit()` silently continues → we don't see this
3. **When groups incomplete**: `find_transit()` silently continues → we don't see this
4. **When complete group found**: `find_transit()` returns → success logged only in caller

So you only see:
- ❌ Days with no data (from `find_subband_groups`)
- ✅ Days with data (missing! - logged only if complete group found)

## Fix

Added logging in `find_transit()` to show:

1. **When groups ARE found**: 
   ```
   INFO - Found 2 group(s) for transit 2025-10-30T13:39:42 (search window: ...)
   ```

2. **When groups are incomplete**:
   ```
   INFO - Skipping transit 2025-10-30T13:39:42: found group with 8 subbands (need 16 complete)
   ```

3. **When complete group is found**:
   ```
   INFO - ✓ Found complete 16-subband group for transit 2025-10-30T13:39:42: 2025-10-30T13:34:54 (2.3 min from transit)
   ```

Now you'll see **all transit attempts**, not just failed ones.

## Example Output After Fix

```
INFO - Finding transit for calibrator: 0834+555
INFO - No subband files found between 2025-10-27 13:33:18 and 2025-10-27 14:33:18
INFO - No subband files found between 2025-10-23 13:49:01 and 2025-10-23 14:49:01
INFO - Found 1 group(s) for transit 2025-10-30T13:39:42 (search window: ...)
INFO - ✓ Found complete 16-subband group for transit 2025-10-30T13:39:42: 2025-10-30T13:34:54 (2.3 min from transit)
INFO - Calibrator transit found:
INFO -   Transit time: 2025-10-30T13:39:42
INFO -   Group ID: 2025-10-30T13:34:54
INFO -   Files: 16 subband files
```

Now you can see:
- Which days had no data (expected)
- Which days had data but incomplete groups (useful for debugging)
- Which transit was successfully found (the outcome)

