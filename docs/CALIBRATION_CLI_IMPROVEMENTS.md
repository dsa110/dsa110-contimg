# Calibration CLI Improvements - Implementation Summary

**Date:** 2025-11-04  
**File:** `src/dsa110_contimg/calibration/cli.py`  
**Status:** Key improvements implemented

---

## Improvements Implemented

### 1. ✅ Moved CASA Environment Setup from Import Time

**Before:**
```python
# Line 26 - Called at module import time
setup_casa_environment()
```

**After:**
```python
# Line 71-78 - Called inside main() function
def main():
    # Set CASA log directory BEFORE any CASA operations (not at import time)
    # This avoids global side effects when module is imported
    try:
        setup_casa_environment()
    except Exception:
        pass  # Best-effort; continue if setup fails
```

**Impact:**
- No longer changes CWD when module is imported
- Side effects only occur when CLI is actually executed
- Better for testing and importing the module

---

### 2. ✅ Added Preset System

**New Flag:**
```python
--preset {fast|standard|production|test}
```

**Presets:**
- **fast**: Fast subset mode (timebin=30s, chanbin=4, phase-only gains, uvrange cuts)
- **standard**: Full MS, amp+phase gains, no subset (recommended for production)
- **production**: Full MS, optimized for quality (per-integration gains)
- **test**: Minimal mode for quick tests

**Usage:**
```bash
# Instead of many flags:
python -m dsa110_contimg.calibration.cli calibrate \
  --ms MS.ms --field 0 --refant 103 \
  --fast --timebin 30s --chanbin 4 --uvrange '>1klambda' --gain-calmode p

# Now just:
python -m dsa110_contimg.calibration.cli calibrate \
  --ms MS.ms --field 0 --refant 103 \
  --preset fast
```

**Implementation:**
- Presets apply defaults but can be overridden with individual flags
- Presets are applied early in the calibrate subcommand handler
- Clear logging shows which preset is applied

---

### 3. ✅ Improved Subset Creation Warnings

**Before:**
- Subset MS files created silently
- User might not realize new files were created
- No cleanup option

**After:**
- **Prominent warnings** when subset MS is created:
  ```
  ======================================================================
  FAST MODE: Creating subset MS for faster calibration
    - Creates: /path/to/MS.fast.ms
    - Original MS unchanged
    - Uses time/channel binning: timebin=30s, chanbin=4
    - Use --cleanup-subset to remove after calibration
  ======================================================================
  ```
- **Cleanup option**: `--cleanup-subset` flag removes subset MS after calibration
- **Disable option**: `--no-subset` flag prevents subset creation even with `--fast` or `--minimal`

---

### 4. ✅ Improved K-Calibration Message

**Before:**
```python
print("Skipping delay (K) calibration by default...")
```

**After:**
```python
logger.info(
    "K-calibration skipped by default for DSA-110 "
    "(short baselines <2.6 km, delays <0.5 ns absorbed into gains). "
    "Use --do-k to enable if needed."
)
```

**Impact:**
- More informative message explaining why K-cal is skipped
- Clearer guidance on when to enable it

---

### 5. ✅ Added Subset Cleanup Logic

**New Feature:**
- `--cleanup-subset` flag automatically removes subset MS files after calibration
- Tracks which subset MS was created (`ms_minimal` or `ms_fast`)
- Only cleans up if calibration succeeds

**Implementation:**
```python
# Store original MS path for cleanup later
original_ms = args.ms
subset_ms_created = None

# ... calibration logic ...

# Cleanup subset MS if requested
if args.cleanup_subset and subset_ms_created:
    import shutil
    try:
        logger.info(f"Cleaning up subset MS: {subset_ms_created}")
        shutil.rmtree(subset_ms_created, ignore_errors=True)
        logger.info("✓ Subset MS removed")
    except Exception as e:
        logger.warning(f"Failed to remove subset MS {subset_ms_created}: {e}")
```

---

## Usage Examples

### Example 1: Fast Calibration with Preset

```bash
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /data/ms/0834_2025-10-30.ms \
  --field 0 --refant 103 \
  --preset fast \
  --cleanup-subset
```

**Result:**
- Applies fast preset (timebin=30s, chanbin=4, phase-only gains)
- Creates subset MS with warning
- Removes subset MS after calibration completes

### Example 2: Standard Production Calibration

```bash
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /data/ms/0834_2025-10-30.ms \
  --field 0 --refant 103 \
  --preset standard \
  --auto-fields
```

**Result:**
- Uses full MS (no subset)
- Amp+phase gains
- Auto-selects fields from catalog

### Example 3: Fast Mode with Override

```bash
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /data/ms/0834_2025-10-30.ms \
  --field 0 --refant 103 \
  --preset fast \
  --gain-calmode ap  # Override preset to use amp+phase instead of phase-only
```

**Result:**
- Fast preset applied (timebin, chanbin, uvrange)
- Gain mode overridden to amp+phase (instead of phase-only from preset)

---

## Backward Compatibility

All changes are **backward compatible**:
- Existing flags continue to work
- Presets are optional (can still use individual flags)
- Default behavior unchanged (just better messages)
- No breaking changes to CLI interface

---

## Remaining Work (Future Improvements)

### Medium Priority

1. **Simplify field selection** - Add `--field-mode` flag
2. **Add output control** - `--output-dir` and `--prefix` for caltables
3. **Improve error messages** - Add actionable suggestions

### Low Priority

1. **Split large file** - Break into subcommand modules
2. **Extract shared logic** - Field selection, model population helpers
3. **Add error code system** - Better debugging

---

## Testing Recommendations

1. **Test preset system:**
   ```bash
   python -m dsa110_contimg.calibration.cli calibrate --help | grep preset
   python -m dsa110_contimg.calibration.cli calibrate --preset fast --ms ... --dry-run
   ```

2. **Test subset warnings:**
   ```bash
   python -m dsa110_contimg.calibration.cli calibrate --fast --ms ... --dry-run
   # Should show warning about subset creation
   ```

3. **Test cleanup:**
   ```bash
   python -m dsa110_contimg.calibration.cli calibrate --preset fast --ms ... --cleanup-subset
   # Should remove subset MS after calibration
   ```

---

## Files Modified

- `src/dsa110_contimg/calibration/cli.py` - Main implementation
- `docs/CALIBRATION_CLI_CONFUSION_ANALYSIS.md` - Analysis document (created)

---

**Next Steps:**
- Test improvements with real data
- Gather user feedback
- Consider implementing medium-priority improvements

