# How to Get All Bandpass Channel Output

**Date:** 2025-11-05  
**Issue:** CASA only prints channels with ≥28 baselines affected, missing channels with 27 baselines (22.2% flagging)

---

## The Problem

CASA's `bandpass` task has **hardcoded selective printing**:
- Only prints channels with ≥28 baselines affected
- Channels with 27 baselines (22.2% flagging) are **not printed**
- No verbosity parameter exists to control this behavior

**CASA's output is incomplete and misleading.**

---

## Solution: Post-Process the Calibration Table

Since CASA doesn't provide a way to print all channels, we must inspect the calibration table directly.

### Option 1: Use the Diagnostic Script

**Print all channels immediately after bandpass solve:**

```bash
python3 scripts/print_all_bandpass_channels.py <bandpass_table> [--spw N]
```

**Example:**
```bash
# After bandpass solve completes
python3 scripts/print_all_bandpass_channels.py \
    /scratch/dsa110-contimg/ms/2025-10-29T13:54:17_0_bpcal \
    --spw 4
```

**Output shows:**
- All channels (not just printed ones)
- Flagging statistics per channel
- Baselines affected
- Status: "PRINTED" vs "NOT PRINTED" (based on CASA's threshold)

---

### Option 2: Use the Detailed Diagnostic Script

**For more detailed analysis:**

```bash
python3 scripts/diagnose_bandpass_output.py <bandpass_table> [--spw N]
```

This provides:
- Complete channel-by-channel statistics
- Baselines affected per channel
- Channels matching CASA's "182" count
- Comparison with CASA's printed output

---

### Option 3: Integrate into Calibration Pipeline

**Modify `solve_bandpass()` to automatically print all channels:**

Add this to `src/dsa110_contimg/calibration/calibration.py` after the bandpass solve:

```python
# After casa_bandpass(**kwargs)
# Print all channels (what CASA doesn't show)
from dsa110_contimg.scripts.print_all_bandpass_channels import print_all_channels
print_all_channels(f"{table_prefix}_bpcal", spw=None)  # or specific SPW
```

**Or add as a CLI option:**

```bash
# Add --verbose-bandpass flag
python -m dsa110_contimg.calibration.cli calibrate \
    --ms MS.ms \
    --field 0 \
    --refant 106 \
    --verbose-bandpass  # Print all channels after solve
```

---

## Why CASA Doesn't Print Everything

CASA's selective printing is likely intentional to:
1. **Reduce output volume** - 48 channels × 16 SPWs = 768 potential messages
2. **Focus on problems** - Only show channels with significant flagging
3. **Performance** - Avoid flooding the console

**However, the threshold (28 baselines) is too strict:**
- Channels with 27 baselines affected (22.2% flagging) are not printed
- This is still significant flagging that users need to know about

---

## Recommended Workflow

### During Calibration

1. **Run bandpass solve normally**
   ```bash
   python -m dsa110_contimg.calibration.cli calibrate --ms MS.ms --field 0 --refant 106
   ```

2. **Immediately check all channels**
   ```bash
   python3 scripts/print_all_bandpass_channels.py <bandpass_table> --spw 4
   ```

3. **Review flagged channels**
   - Focus on channels with high flagging (>50%)
   - Note channels with 27 baselines affected (CASA didn't print these)

### For Production

**Integrate the diagnostic into the calibration pipeline:**

```python
# In calibration.py, after bandpass solve
def solve_bandpass(...):
    # ... existing bandpass solve code ...
    casa_bandpass(**kwargs)
    
    # Print all channels (what CASA doesn't show)
    print("\n" + "=" * 80)
    print("COMPLETE BANDPASS CHANNEL REPORT (all channels)")
    print("=" * 80)
    print_all_channels(f"{table_prefix}_bpcal", spw=None)
```

---

## Alternative: Capture CASA Log File

CASA writes detailed logs to `casa.log`. However:
- The selective printing behavior is in the **task output**, not the log file
- Log files may contain more detail, but won't solve the selective printing issue

**To capture CASA's log:**
```bash
# CASA log is written to CWD or configured location
export CASALOGFILE=/path/to/casa.log
python -m dsa110_contimg.calibration.cli calibrate --ms MS.ms ...
```

**Then check the log:**
```bash
grep "solutions flagged" casa.log
```

But this still won't show channels that weren't printed.

---

## Bottom Line

**CASA's selective printing cannot be disabled.** The solution is to:

1. ✅ **Use `scripts/print_all_bandpass_channels.py`** after bandpass solve
2. ✅ **Integrate into calibration pipeline** for automatic reporting
3. ✅ **Don't rely on CASA's printed output** - always check the table directly

**The diagnostic scripts provide the complete picture that CASA doesn't.**

