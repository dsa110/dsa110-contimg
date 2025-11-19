# Self-Calibration Implementation Summary

**Date:** 2025-11-19  
**Type:** Implementation Summary  
**Status:** 🔄 Testing In Progress

---

## Overview

Implemented a complete self-calibration module for the DSA-110 continuum imaging
pipeline. Self-calibration iteratively improves image quality by using the
observed data itself to refine calibration solutions.

## Files Created

### Core Module

**`src/dsa110_contimg/src/dsa110_contimg/calibration/selfcal.py`** (610 lines)

- `SelfCalIteration`: Dataclass for iteration results
- `SelfCalConfig`: Configuration dataclass with sensible defaults
- `SelfCalibrator`: Main class implementing iterative self-cal
- `selfcal_ms()`: Convenience function for quick self-cal

**Key Features:**

- Progressive solution intervals (30s → 60s → inf)
- Phase-only and amplitude+phase calibration modes
- Automatic convergence detection (min SNR improvement threshold)
- Divergence protection (stops if SNR decreases)
- Quality control checks (min initial SNR, max flagged fraction)
- Integration with WSClean imaging backend
- NVSS model seeding support
- Comprehensive JSON summary output

### CLI Interface

**`src/dsa110_contimg/src/dsa110_contimg/calibration/cli_selfcal.py`** (306
lines)

- Complete argparse CLI with all configuration options
- JSON summary output
- Formatted terminal output
- Verbose mode for debugging

### Test Script

**`scripts/test_selfcal.py`** (157 lines)

- Test self-calibration on calibrated 0834+555 data
- Conservative configuration for initial testing
- Comprehensive logging and output

### Documentation

**`docs/how-to/self_calibration.md`** (537 lines)

- Complete user guide with examples
- Configuration parameter reference
- Best practices and troubleshooting
- Integration examples for pipeline
- Performance considerations

## Implementation Details

### Architecture

```
SelfCalibrator
├── _run_initial_imaging()
│   ├── Apply initial caltables (BP, GP, 2G)
│   ├── Image with current calibration
│   └── Extract metrics (SNR, peak, RMS)
├── _run_selfcal_iteration()  (repeated)
│   ├── Solve for gains (gaincal)
│   ├── Validate calibration quality
│   ├── Apply calibration (applycal)
│   ├── Image with new calibration
│   └── Extract metrics
├── _check_continue()
│   ├── Check SNR improvement
│   ├── Detect divergence
│   └── Assess convergence
└── get_summary()
    └── Return JSON summary
```

### Self-Calibration Workflow

1. **Initial Imaging** (Iteration 0)
   - Apply existing BP/GP/2G calibration
   - Clean image to establish baseline
   - Measure initial SNR, peak flux, RMS

2. **Phase-Only Iterations** (configurable solints)
   - Extract model from previous image
   - Solve for phase gains (`calmode='p'`)
   - Apply gains to CORRECTED_DATA
   - Re-image and measure metrics
   - Check for improvement/convergence

3. **Amplitude+Phase Iteration** (optional, final)
   - Solve for amp+phase gains (`calmode='ap'`)
   - Apply gains
   - Final imaging
   - Measure final metrics

4. **Convergence Criteria**
   - Stop if SNR < previous (divergence)
   - Stop if SNR improvement < threshold (converged)
   - Stop if max iterations reached
   - Stop if excessive flagging

### Default Configuration

```python
SelfCalConfig(
    # Iteration control
    max_iterations=5,
    min_snr_improvement=1.05,  # 5% improvement required
    stop_on_divergence=True,

    # Phase-only iterations
    phase_solints=["30s", "60s", "inf"],
    phase_minsnr=3.0,

    # Amplitude+phase (final)
    do_amplitude=True,
    amp_solint="inf",
    amp_minsnr=5.0,

    # Imaging
    imsize=1024,
    niter=10000,
    threshold="0.0005Jy",  # 0.5 mJy
    backend="wsclean",

    # Quality control
    min_initial_snr=10.0,
    max_flagged_fraction=0.5,
)
```

## Integration with Existing Pipeline

### CASA Tasks Used

- `gaincal`: Solve for gain solutions using MODEL_DATA
- `applycal`: Apply calibration tables to CORRECTED_DATA

### Imaging Integration

- Uses `image_ms()` from `imaging/cli_imaging.py`
- Supports WSClean backend (default)
- NVSS model seeding for known calibrators
- Exports model image for next iteration

### QA Integration

- Uses `validate_caltable_quality()` for calibration QA
- Checks flagging fraction
- Validates solution SNR

## Output Products

### Per Iteration

- `selfcal_iter0-image.fits`: Initial image
- `selfcal_iter0-residual.fits`: Initial residual
- `selfcal_iter0-model.fits`: Initial model
- `selfcal_iter1_p.gcal`: Phase gains (iteration 1)
- `selfcal_iter1-image.fits`: Image after iteration 1
- `selfcal_iter1-residual.fits`: Residual after iteration 1
- `selfcal_iterN_ap.gcal`: Amp+phase gains (final)
- `selfcal_iterN-image.fits`: Final image

### Summary

- `selfcal_summary.json`: Complete JSON summary

**JSON Structure:**

```json
{
  "status": "success",
  "iterations_completed": 4,
  "initial_snr": 321.2,
  "final_snr": 1245.7,
  "best_snr": 1245.7,
  "snr_improvement": 3.88,
  "best_iteration": 3,
  "message": "Self-cal successful: SNR 321.2 → 1245.7",
  "iterations": [
    {
      "iteration": 0,
      "calmode": "initial",
      "solint": "N/A",
      "snr": 321.2,
      "peak_flux_mjy": 32.0,
      "rms_noise_mjy": 0.1,
      "success": true
    }
  ]
}
```

## Usage Examples

### Basic CLI Usage

```bash
python3 /data/dsa110-contimg/src/dsa110_contimg/src/dsa110_contimg/calibration/cli_selfcal.py \
    /stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms \
    /stage/dsa110-contimg/test_data/selfcal_output \
    --initial-caltables /stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_bpcal,/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_gpcal,/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_2gcal \
    --phase-solints "60s,inf" \
    --niter 10000
```

### Python API Usage

```python
from dsa110_contimg.calibration.selfcal import SelfCalConfig, selfcal_ms

config = SelfCalConfig(
    phase_solints=["60s", "inf"],
    do_amplitude=True,
    niter=10000,
    threshold="0.0005Jy",
)

success, summary = selfcal_ms(
    ms_path="/path/to/data.ms",
    output_dir="/path/to/output",
    config=config,
    initial_caltables=[
        "/path/to/bpcal",
        "/path/to/gpcal",
        "/path/to/2gcal",
    ],
)

print(f"SNR improvement: {summary['snr_improvement']:.2f}x")
```

## Testing Status

### Test Data

- **MS**: `/stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms`
- **Calibrator**: 0834+555 (RA=128.729°, Dec=55.382°)
- **Initial Calibration**: BP, GP, 2G tables from external calibrator
- **Initial SNR**: Expected ~321 (from previous cleaned imaging)

### Test Configuration

```python
SelfCalConfig(
    phase_solints=["60s", "inf"],  # Conservative: only 2 iterations
    do_amplitude=True,
    niter=10000,
    threshold="0.0005Jy",
    min_initial_snr=10.0,
    calib_ra_deg=128.728752927042,
    calib_dec_deg=55.38156866948,
    calib_flux_jy=0.050,
)
```

### Expected Results

- **Initial SNR**: ~321
- **After phase self-cal**: SNR improvement 1.2-2x
- **After amp+phase self-cal**: SNR improvement 2-4x total
- **Typical**: SNR 321 → 400-800 (1.2-2.5x)
- **Best case**: SNR 321 → 1000+ (3x+)

## Performance Characteristics

### Timing (1024x1024 image)

- **Initial imaging**: 2-5 minutes
- **Gain solve**: 30-60 seconds per iteration
- **Apply calibration**: 10-20 seconds
- **Imaging per iteration**: 2-5 minutes

**Total**: 10-30 minutes for 3-4 iterations

### Resource Usage

- **Memory**: 5-8 GB RAM (peak)
- **Disk**: 500 MB - 2 GB per run
- **CPU**: Single-threaded CASA gaincal, multi-threaded WSClean imaging

## Known Limitations

1. **Requires HIGH SNR**: Initial SNR > 10 recommended, > 20 ideal
2. **Single bright source**: Works best with isolated calibrator
3. **Flux scale risk**: Amplitude self-cal can change absolute flux scale
4. **Computationally expensive**: Multiple full imaging iterations
5. **CASA dependency**: Requires casatasks for gaincal/applycal

## Future Enhancements

### Potential Improvements

1. **Multi-scale support**: Add multi-scale cleaning for extended sources
2. **Parallel imaging**: Run multiple tiers in parallel
3. **Smart convergence**: Use dynamic range instead of just SNR
4. **Adaptive solint**: Automatically adjust solution interval
5. **Flux bootstrapping**: Constrain flux scale with catalog
6. **GPU acceleration**: Use GPU WSClean for faster imaging
7. **Incremental gains**: Save intermediate gain tables for restart
8. **Visualization**: Generate SNR progression plots

### Integration Points

1. **Mosaic pipeline**: Add self-cal option after initial calibration
2. **Streaming pipeline**: Conditional self-cal for bright sources (SNR > 20)
3. **QA system**: Track self-cal convergence metrics
4. **Dashboard**: Display self-cal progress and results
5. **API**: Expose self-cal endpoint for manual triggering

## Technical Notes

### MODEL_DATA Requirements

CASA's `gaincal` requires `MODEL_DATA` column to be populated. This is handled
automatically by:

- `image_ms()` with `export_model_image=True`
- WSClean's `-predict` mode (via our two-step workflow)

### CORRECTED_DATA Management

- Initial calibration is applied to `CORRECTED_DATA`
- Each self-cal iteration updates `CORRECTED_DATA`
- Final imaging uses `CORRECTED_DATA` automatically

### Calibration Table Chain

Self-cal maintains a chain of calibration tables:

1. Initial: `[BP, GP, 2G]`
2. Iteration 1: `[BP, GP, 2G, selfcal_iter1_p.gcal]`
3. Iteration 2: `[BP, GP, 2G, selfcal_iter1_p.gcal, selfcal_iter2_p.gcal]`
4. Final: `[BP, GP, 2G, ..., selfcal_iterN_ap.gcal]`

Each iteration applies the full chain to get cumulative improvement.

## References

### Radio Astronomy

- Cornwell & Wilkinson (1981): "A new method for making maps with unstable radio
  interferometers"
- Pearson & Readhead (1984): "Image formation by self-calibration in radio
  astronomy"
- NRAO Self-Calibration Guide:
  https://casaguides.nrao.edu/index.php/Self-Calibration

### DSA-110 Documentation

- Self-Calibration Guide: `docs/how-to/self_calibration.md`
- Calibration Guide: `docs/how-to/calibration.md`
- Imaging Guide: `docs/how-to/imaging.md`

---

## Current Status

**Implementation**: ✅ Complete  
**Testing**: 🔄 In Progress  
**Documentation**: ✅ Complete  
**Integration**: 📋 Planned

**Test Command Running:**

```bash
export PYTHONPATH=/data/dsa110-contimg/src/dsa110_contimg/src:$PYTHONPATH
timeout 1800 python3 /data/dsa110-contimg/scripts/test_selfcal.py 2>&1 | tee /stage/dsa110-contimg/test_data/test_selfcal.log
```

**Next Steps:**

1. Monitor test execution
2. Validate SNR improvement
3. Review output products
4. Optimize parameters if needed
5. Integrate into main pipeline

---

**Last Updated:** 2025-11-19  
**Author:** DSA-110 Continuum Imaging Team
