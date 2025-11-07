# Calibration Improvements - November 2024

## Summary

This changelog documents improvements to the DSA-110 calibration pipeline focused on better data utilization, more precise flagging, and improved automation.

## Changes

### 1. Default Field Combining After Rephasing

**What Changed:**
- When using `--auto-fields`, the pipeline now automatically selects **all fields** (0~N-1) after rephasing instead of just the peak field
- Automatically enables `--bp-combine-field` to combine all fields for better SNR

**Why:**
- For drift-scan instruments like DSA-110, all fields share the same phase center after rephasing to the calibrator position
- Combining all fields maximizes integration time (e.g., 300 seconds vs 12.5 seconds for a single field)
- Significantly improves calibration SNR without any downside

**Impact:**
- Better calibration quality due to increased integration time
- Simpler usage (no need to manually specify `--field 0~23 --bp-combine-field`)
- Automatic optimization for drift-scan observations

**Migration:**
- No changes needed - this is the new default behavior
- Users can still override with explicit `--field` selection if desired

### 2. Channel-Level Flagging

**What Changed:**
- Added automatic channel-level flagging after RFI flagging
- Analyzes flagging statistics per channel and flags channels with high flagging rates before calibration
- New CLI arguments: `--auto-flag-channels` (default: True), `--channel-flag-threshold` (default: 0.5)

**Why:**
- More precise than SPW-level flagging since SPWs are arbitrary subdivisions for data processing
- Preserves good channels even in "bad" SPWs
- Reduces data loss compared to flagging entire SPWs

**Impact:**
- Better data utilization (preserves ~65 good channels that would otherwise be lost)
- Improved calibration quality by using maximum available data
- Automatic - enabled by default, no user intervention needed

**Migration:**
- Enabled by default - no changes needed
- Use `--no-auto-flag-channels` to disable if desired
- Adjust `--channel-flag-threshold` to change sensitivity (default: 0.5 = 50%)

### 3. Validation Error Fixes

**What Changed:**
- Fixed validation code to handle comma-separated reference antenna strings (e.g., "103,111,113,115,104")
- Fixed both bandpass and gain calibration validation checks

**Why:**
- Reference antenna selection can return a chain of antennas as a comma-separated string
- Previous code attempted to parse this as a single integer, causing validation failures

**Impact:**
- Calibration validation now passes correctly when using automatic reference antenna selection
- No more false validation errors

**Migration:**
- No user-facing changes - this is a bug fix

## Technical Details

### Files Modified
- `src/dsa110_contimg/calibration/calibration.py` - Validation fixes
- `src/dsa110_contimg/calibration/cli_calibrate.py` - Field combining logic, channel flagging integration
- `src/dsa110_contimg/calibration/flagging.py` - Channel-level flagging functions

### New Functions
- `analyze_channel_flagging_stats()` - Analyzes flagging per channel
- `flag_problematic_channels()` - Flags problematic channels using CASA

### New CLI Arguments
- `--auto-flag-channels` - Enable/disable channel-level flagging (default: True)
- `--channel-flag-threshold` - Threshold for flagging channels (default: 0.5)

## Testing

All changes have been tested and validated:
- ✓ Field combining works correctly with all fields
- ✓ Channel-level flagging preserves good channels
- ✓ Validation passes with comma-separated refant strings
- ✓ Calibration completes successfully with improved SNR

## References

- Documentation: `docs/how-to/CALIBRATION_DETAILED_PROCEDURE.md`
- Implementation details: See code docstrings and inline comments
