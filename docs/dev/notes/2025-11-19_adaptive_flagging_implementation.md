# Adaptive Flagging Implementation Notes

**Date**: November 19, 2025  
**Feature**: Calibration-Triggered Adaptive RFI Flagging  
**Status**: ✅ Implemented

## Summary

Implemented automatic escalation from default to aggressive RFI flagging
strategies based on calibration success. The system attempts calibration with
default flagging first, and only escalates to aggressive flagging if calibration
fails.

## Files Modified

### Core Implementation

1. **`src/dsa110_contimg/calibration/flagging_adaptive.py`** (NEW)
   - `flag_rfi_adaptive()`: Main adaptive flagging function
   - `CalibrationFailure`: Custom exception for calibration failures
   - `get_flag_summary()`: Utility function for flagging statistics

2. **`src/dsa110_contimg/calibration/__init__.py`**
   - Added imports for `flag_rfi_adaptive` and `CalibrationFailure`

3. **`src/dsa110_contimg/pipeline/stages_impl.py`**
   - Modified `CalibrationSolveStage._execute_calibration_solve()`
   - Integrated adaptive flagging logic
   - Created internal `_perform_calibration_solve()` helper function
   - Added configuration parameters:
     - `use_adaptive_flagging` (default: `True`)
     - `aggressive_strategy` (default:
       `/data/dsa110-contimg/config/dsa110-aggressive.lua`)
     - `flagging_backend` (default: `"aoflagger"`)

### Configuration Files

- **`/data/dsa110-contimg/config/dsa110-default.lua`** (existing)
  - Default AOFlagger strategy (`base_threshold = 1.0`)
  - Target: 4-5% flagging
- **`/data/dsa110-contimg/config/dsa110-moderate.lua`** ✨ (NEW)
  - Moderate AOFlagger strategy (`base_threshold = 0.85`)
  - Target: 5-6% flagging (estimated)
  - Bridge between default and aggressive
- **`/data/dsa110-contimg/config/dsa110-aggressive.lua`** (modified)
  - Aggressive AOFlagger strategy (`base_threshold = 0.75`)
  - Target: 6-7% flagging (vs CASA's ~13%)
- **`/data/dsa110-contimg/config/dsa110-very-aggressive.lua`** (renamed)
  - Very aggressive strategy (`base_threshold = 0.6`)
  - Target: 50%+ flagging
  - For manual use only

### Documentation

- **`docs/how-to/ADAPTIVE_FLAGGING_PIPELINE_INTEGRATION.md`** (NEW)
  - Comprehensive user guide
  - Configuration examples
  - Troubleshooting guide

- **`docs/how-to/AOFLAGGER_STRATEGY_TUNING.md`** (existing)
  - Parameter reference
- **`docs/how-to/AOFLAGGER_TUNING_RESULTS.md`** (existing)
  - Tuning test results

## Logic Flow

### Adaptive Flagging Enabled (Default)

```
1. Reset flags → Flag zeros
2. Populate MODEL_DATA (catalog or image)
3. Apply default RFI flagging
4. Attempt calibration (delay, bandpass, gains)
   ├─ SUCCESS → Done! (strategy: "default", attempts: 1)
   └─ FAILURE → Continue to step 5
5. Reset flags → Flag zeros again
6. Apply aggressive RFI flagging
7. Retry calibration
   ├─ SUCCESS → Done! (strategy: "aggressive", attempts: 2)
   └─ FAILURE → Error (both strategies failed)
8. Flag autocorrelations
```

### Adaptive Flagging Disabled (Legacy Mode)

```
1. Reset flags → Flag zeros
2. Apply default RFI flagging
3. Flag autocorrelations
4. Populate MODEL_DATA
5. Perform calibration (no retry on failure)
```

## Configuration Examples

### Default Behavior (Adaptive Enabled)

```python
# No special configuration needed - adaptive flagging is enabled by default
context = PipelineContext(
    config=config,
    outputs={"ms_path": "/path/to/data.ms"},
    inputs={"calibration_params": {"field": "0", "refant": "103"}}
)
```

### Disable Adaptive Flagging

```python
context = PipelineContext(
    config=config,
    outputs={"ms_path": "/path/to/data.ms"},
    inputs={
        "calibration_params": {
            "use_adaptive_flagging": False,
            "field": "0",
            "refant": "103",
        }
    }
)
```

### Custom Aggressive Strategy

```python
context = PipelineContext(
    config=config,
    outputs={"ms_path": "/path/to/data.ms"},
    inputs={
        "calibration_params": {
            "aggressive_strategy": "/path/to/custom-aggressive.lua",
            "field": "0",
            "refant": "103",
        }
    }
)
```

## Performance Impact

- **Typical case** (no escalation): No overhead (~4-5 min flagging +
  calibration)
- **Worst case** (escalation required): +4-5 minutes for aggressive retry
- **Total worst case**: ~9-10 minutes

## Testing

### Baseline Testing

- ✅ Tested AOFlagger default strategy: 4.46% flagging
- ✅ Tested AOFlagger aggressive strategy: 6.19% flagging
- ✅ Tested CASA tfcrop+rflag: 13.19% flagging
- ✅ Confirmed AOFlagger is 4x faster than CASA

### Integration Testing

- ⏳ **Pending**: Full pipeline integration test
- ⏳ **Pending**: Test with real contaminated observation
- ⏳ **Pending**: Verify escalation trigger logic

## Future Improvements

1. **Expose adaptive results in context**
   - Add `adaptive_flagging_result` to pipeline outputs
   - Include strategy used, attempts, flagging stats

2. **Calibration quality metrics**
   - Add phase/amplitude RMS thresholds for triggering escalation
   - Make escalation more sensitive to calibration quality

3. **Three-tier escalation** ✨ (moderate strategy created)
   - ✅ `dsa110-moderate.lua` created (`base_threshold = 0.85`)
   - ⏳ Implement three-tier logic: default → moderate → aggressive
   - ⏳ Add configuration parameter `use_three_tier_flagging`

4. **Flagging history tracking**
   - Log adaptive decisions to database
   - Generate reports on escalation frequency

5. **Real-time monitoring**
   - Dashboard widget for adaptive flagging status
   - Alert on frequent escalations (may indicate systemic RFI)

## Related Work

- **RFI Backend Comparison**: AOFlagger vs CASA tfcrop performance testing
- **AOFlagger Strategy Tuning**: Parameter space exploration (`base_threshold`,
  `iteration_count`, etc.)
- **Temporal Flagging System**: Three-phase flagging tracking (Phase 1, 2, 3)

## Notes

- Pre-existing linter errors in `stages_impl.py` (lines 1-145) were NOT modified
- New code includes `# noqa: E501` for unavoidable long lines (logger messages,
  imports)
- Backward compatibility maintained: Legacy mode available via
  `use_adaptive_flagging=False`

---

**Implementation complete**: November 19, 2025  
**Tested**: Partially (baseline tests complete, integration tests pending)  
**Ready for production**: ⚠️ Recommend testing with real data before deploying
