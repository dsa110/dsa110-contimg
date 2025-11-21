# Self-Calibration Guide

**Date:** 2025-11-19  
**Type:** How-To Guide  
**Status:** ✅ Complete

---

## Overview

Self-calibration (self-cal) is an iterative process that improves image quality
by using the observed data itself to refine calibration solutions. This guide
explains how to use the DSA-110 self-calibration pipeline.

## What is Self-Calibration?

Self-calibration addresses residual calibration errors that remain after initial
calibration with a calibrator source. The process:

1. **Image** the data with current calibration
2. **Extract model** from the cleaned image
3. **Solve for gains** using the model
4. **Apply** the new calibration
5. **Repeat** until converged

### Benefits

- **Improved dynamic range**: 2-10x improvement typical
- **Better phase coherence**: Corrects atmospheric and instrumental phase errors
- **Enhanced source structure**: Reveals faint extended emission
- **Reduced artifacts**: Removes calibration-related imaging artifacts

### Limitations

- **Requires high SNR**: Initial SNR > 10 recommended
- **Can fail on weak sources**: Below ~5σ, self-cal may diverge
- **Flux scale risk**: Amplitude self-cal can change absolute flux scale
- **Time-consuming**: Multiple imaging iterations required

## Quick Start

### Basic Usage

```bash
# Self-calibrate an MS with default settings
python3 /data/dsa110-contimg/src/dsa110_contimg/src/dsa110_contimg/calibration/cli_selfcal.py \
    /path/to/data.ms \
    /path/to/output_dir \
    --initial-caltables /path/to/bpcal,/path/to/gpcal,/path/to/2gcal
```

### Python API

```python
from dsa110_contimg.calibration.selfcal import SelfCalConfig, selfcal_ms

# Configure self-calibration
config = SelfCalConfig(
    phase_solints=["60s", "inf"],  # Phase-only iterations
    do_amplitude=True,              # Include amplitude+phase iteration
    niter=10000,                    # CLEAN iterations
    threshold="0.0005Jy",          # 0.5 mJy cleaning threshold
)

# Run self-calibration
success, summary = selfcal_ms(
    ms_path="/path/to/data.ms",
    output_dir="/path/to/output",
    config=config,
    initial_caltables=["/path/to/bpcal", "/path/to/gpcal"],
)

print(f"SNR improvement: {summary['snr_improvement']:.2f}x")
```

## Configuration Parameters

### Iteration Control

| Parameter             | Default | Description                              |
| --------------------- | ------- | ---------------------------------------- |
| `max_iterations`      | 5       | Maximum number of iterations             |
| `min_snr_improvement` | 1.05    | Minimum SNR improvement (5%) to continue |
| `stop_on_divergence`  | True    | Stop if SNR decreases                    |

### Phase-Only Iterations

| Parameter       | Default                 | Description                       |
| --------------- | ----------------------- | --------------------------------- |
| `phase_solints` | `["30s", "60s", "inf"]` | Solution intervals for phase-only |
| `phase_minsnr`  | 3.0                     | Minimum SNR for phase solutions   |
| `phase_combine` | ""                      | Combine axes (e.g., "spw")        |

**Solution Interval Guidelines:**

- **30s**: Short timescale, captures rapid phase variations
- **60s**: Medium timescale, balances sensitivity and stability
- **inf**: Scan-average, most sensitive but assumes stable phases

### Amplitude+Phase Iteration

| Parameter      | Default | Description                         |
| -------------- | ------- | ----------------------------------- |
| `do_amplitude` | True    | Enable amplitude+phase iteration    |
| `amp_solint`   | "inf"   | Solution interval for amp+phase     |
| `amp_minsnr`   | 5.0     | Minimum SNR for amp+phase solutions |
| `amp_combine`  | "scan"  | Combine scans                       |

**Warning:** Amplitude self-cal can change the absolute flux scale. Use
cautiously and validate flux scale against known sources.

### Imaging Parameters

| Parameter     | Default    | Description                    |
| ------------- | ---------- | ------------------------------ |
| `imsize`      | 1024       | Image size in pixels           |
| `cell_arcsec` | None       | Pixel size (auto if None)      |
| `niter`       | 10000      | CLEAN iterations               |
| `threshold`   | "0.0005Jy" | Cleaning threshold (0.5 mJy)   |
| `robust`      | 0.0        | Briggs robust parameter        |
| `backend`     | "wsclean"  | Imaging backend (wsclean/casa) |

### Quality Control

| Parameter              | Default | Description                             |
| ---------------------- | ------- | --------------------------------------- |
| `min_initial_snr`      | 10.0    | Minimum initial SNR to attempt self-cal |
| `max_flagged_fraction` | 0.5     | Stop if > 50% data flagged              |

## Workflow Examples

### Conservative Self-Calibration

For initial testing or uncertain source strength:

```python
config = SelfCalConfig(
    phase_solints=["inf"],  # Single phase-only iteration
    do_amplitude=False,     # Phase-only (preserves flux scale)
    min_snr_improvement=1.1,  # Require 10% improvement
)
```

### Aggressive Self-Calibration

For strong sources (SNR > 50):

```python
config = SelfCalConfig(
    phase_solints=["30s", "60s", "120s", "inf"],  # Progressive solints
    do_amplitude=True,
    amp_solint="inf",
    min_snr_improvement=1.03,  # Continue with 3% improvement
    niter=20000,  # Deep cleaning
)
```

### Calibrator Self-Calibration

For known calibrators with model:

```python
config = SelfCalConfig(
    phase_solints=["60s", "inf"],
    do_amplitude=True,
    calib_ra_deg=128.728,  # Calibrator position
    calib_dec_deg=55.382,
    calib_flux_jy=0.050,   # Known flux
    use_nvss_seeding=True,
)
```

## CLI Reference

### Required Arguments

```
ms                  Path to Measurement Set
output_dir          Output directory for self-cal products
```

### Optional Arguments

#### Initial Calibration

```
--initial-caltables CALTABLES
                    Comma-separated list of calibration tables
                    Example: --initial-caltables bp.cal,gp.cal,2g.cal
```

#### Iteration Control

```
--max-iterations N          Maximum iterations (default: 5)
--min-snr-improvement RATIO Minimum SNR improvement (default: 1.05)
--min-initial-snr SNR       Minimum initial SNR (default: 10.0)
```

#### Phase-Only Iterations

```
--phase-solints SOLINTS     Comma-separated solints (default: 30s,60s,inf)
--phase-minsnr SNR          Minimum SNR for phase (default: 3.0)
```

#### Amplitude+Phase

```
--no-amplitude              Skip amplitude+phase iteration
--amp-solint SOLINT         Amp+phase solint (default: inf)
--amp-minsnr SNR            Minimum SNR for amp+phase (default: 5.0)
```

#### Imaging

```
--imsize PIXELS             Image size (default: 1024)
--cell-arcsec ARCSEC        Pixel size (default: auto)
--niter N                   CLEAN iterations (default: 10000)
--threshold THRESH          Cleaning threshold (default: 0.0005Jy)
--robust VALUE              Briggs robust (default: 0.0)
--backend {wsclean,casa}    Imaging backend (default: wsclean)
```

#### Model Seeding

```
--no-nvss-seeding           Disable NVSS model seeding
--nvss-min-mjy MJY          Minimum NVSS flux (default: 10.0)
--calib-ra-deg RA           Calibrator RA in degrees
--calib-dec-deg DEC         Calibrator Dec in degrees
--calib-flux-jy FLUX        Calibrator flux in Jy
```

## Output Files

Self-calibration produces the following outputs:

### Calibration Tables

- `selfcal_iter1_p.gcal`: Phase-only gains (iteration 1)
- `selfcal_iter2_p.gcal`: Phase-only gains (iteration 2)
- `selfcal_iterN_ap.gcal`: Amplitude+phase gains (final iteration)

### Images

- `selfcal_iter0-image.fits`: Initial image (before self-cal)
- `selfcal_iter0-residual.fits`: Initial residual
- `selfcal_iterN-image.fits`: Images from each iteration
- `selfcal_iterN-residual.fits`: Residuals from each iteration
- `selfcal_iterN-model.fits`: Sky models from each iteration

### Summary

- `selfcal_summary.json`: JSON summary with metrics

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
    },
    {
      "iteration": 1,
      "calmode": "p",
      "solint": "60s",
      "snr": 456.3,
      "peak_flux_mjy": 33.5,
      "rms_noise_mjy": 0.073,
      "success": true
    }
  ]
}
```

## Best Practices

### When to Use Self-Calibration

✅ **Use self-cal when:**

- Initial SNR > 10
- Strong, isolated source in field
- Want to maximize dynamic range
- Have identified calibration-related artifacts

❌ **Avoid self-cal when:**

- Initial SNR < 5
- Multiple sources of similar brightness (confusion)
- Short observation (< 5 min)
- Goal is absolute flux measurement (amplitude self-cal changes flux scale)

### Iteration Strategy

1. **Start conservative**: Single `phase_solint=["inf"]`
2. **Check improvement**: Verify SNR increases
3. **Add iterations**: Gradually add shorter solints
4. **Add amplitude**: Only if phase-only converges well

### Validation

After self-calibration, validate:

1. **SNR improved**: Check `summary['snr_improvement']`
2. **No divergence**: SNR should increase monotonically
3. **Model reasonable**: Check model images for artifacts
4. **Flux scale**: Compare to catalog (if amplitude self-cal used)

### Troubleshooting

#### Self-cal Diverges (SNR Decreases)

**Causes:**

- Initial model too poor (low SNR)
- Solution interval too short (underconstraining)
- Multiple unresolved sources (model ambiguity)

**Solutions:**

- Start with longer solint (`"inf"`)
- Increase `phase_minsnr`
- Improve initial cleaning (higher `niter`, better threshold)

#### Self-cal Stalls (No Improvement)

**Causes:**

- Already at optimal calibration
- Noise-dominated regime
- Hitting dynamic range limits

**Solutions:**

- Accept current results (already converged)
- Check for systematic errors (RFI, baseline errors)
- Use multiscale clean for extended sources

#### Flux Scale Changes

**Cause:**

- Amplitude self-cal without absolute flux constraint

**Solution:**

- Use phase-only self-cal to preserve flux scale
- If amplitude self-cal needed, validate against catalog sources

## Integration with Pipeline

### In Mosaic Pipeline

Self-calibration can be integrated into the mosaic pipeline after initial
calibration:

```python
from dsa110_contimg.calibration.selfcal import SelfCalConfig, selfcal_ms

# After standard BP/GP/2G calibration
config = SelfCalConfig(
    phase_solints=["60s", "inf"],
    do_amplitude=False,  # Preserve flux scale for mosaicking
)

success, summary = selfcal_ms(
    ms_path=ms_path,
    output_dir=output_dir,
    config=config,
    initial_caltables=[bp_table, gp_table, phase_table],
)

if success:
    # Use self-calibrated MS for final imaging
    final_image = image_ms(ms_path, ...)
```

### In Streaming Pipeline

For real-time processing, consider:

```python
# Check if source is bright enough
if peak_snr > 20:
    # Quick phase-only self-cal
    config = SelfCalConfig(
        phase_solints=["inf"],  # Single iteration
        do_amplitude=False,
        niter=5000,  # Faster cleaning
    )
    selfcal_ms(ms_path, output_dir, config)
else:
    # Skip self-cal for faint sources
    pass
```

## Performance Considerations

### Timing

Typical self-calibration timing (1024x1024 image):

- **Initial imaging**: 2-5 minutes
- **Gain solve**: 30-60 seconds per iteration
- **Apply calibration**: 10-20 seconds
- **Imaging**: 2-5 minutes per iteration

**Total**: 10-30 minutes for 3-4 iterations

### Memory

- **WSClean imaging**: ~2-4 GB RAM per 1024x1024 image
- **CASA gain solve**: ~1-2 GB RAM
- **Peak usage**: ~5-8 GB RAM

### Disk Space

Per iteration:

- Calibration table: ~10-50 MB
- Images (image+residual+model): ~100-300 MB

**Total**: ~500 MB - 2 GB for complete self-cal run

## References

### Radio Astronomy Self-Calibration

- Cornwell & Wilkinson (1981): "A new method for making maps with unstable radio
  interferometers"
- Pearson & Readhead (1984): "Image formation by self-calibration in radio
  astronomy"
- NRAO Self-Calibration Guide:
  https://casaguides.nrao.edu/index.php/Self-Calibration

### DSA-110 Documentation

- Calibration Guide: `/data/dsa110-contimg/docs/how-to/calibration.md`
- Imaging Guide: `/data/dsa110-contimg/docs/how-to/imaging.md`
- Pipeline Architecture:
  `/data/dsa110-contimg/docs/concepts/DIRECTORY_ARCHITECTURE.md`

## Examples

### Example 1: Basic Self-Calibration

```bash
#!/bin/bash
# Basic self-calibration for a calibrator observation

MS="/stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms"
OUT="/stage/dsa110-contimg/test_data/selfcal_output"
CALTABLES="/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_bpcal,\
/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_gpcal,\
/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_2gcal"

python3 /data/dsa110-contimg/src/dsa110_contimg/src/dsa110_contimg/calibration/cli_selfcal.py \
    "$MS" "$OUT" \
    --initial-caltables "$CALTABLES" \
    --phase-solints "60s,inf" \
    --niter 10000 \
    --threshold "0.0005Jy"
```

### Example 2: Phase-Only Self-Calibration

```python
from dsa110_contimg.calibration.selfcal import SelfCalConfig, selfcal_ms

# Phase-only (preserves flux scale)
config = SelfCalConfig(
    phase_solints=["60s", "inf"],
    do_amplitude=False,  # Phase-only
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

print(f"Initial SNR: {summary['initial_snr']:.1f}")
print(f"Final SNR: {summary['final_snr']:.1f}")
print(f"Improvement: {summary['snr_improvement']:.2f}x")
```

### Example 3: Full Amplitude+Phase Self-Calibration

```python
from dsa110_contimg.calibration.selfcal import SelfCalConfig, selfcal_ms

# Full self-cal (phase + amplitude)
config = SelfCalConfig(
    phase_solints=["30s", "60s", "inf"],  # Progressive
    do_amplitude=True,
    amp_solint="inf",
    amp_minsnr=5.0,
    niter=15000,
    threshold="0.0003Jy",  # 0.3 mJy
)

success, summary = selfcal_ms(
    ms_path="/path/to/data.ms",
    output_dir="/path/to/output",
    config=config,
    initial_caltables=[
        "/path/to/bpcal",
        "/path/to/gpcal",
    ],
)

# Plot SNR progression
import matplotlib.pyplot as plt

iterations = [it['iteration'] for it in summary['iterations']]
snrs = [it['snr'] for it in summary['iterations']]

plt.figure(figsize=(8, 6))
plt.plot(iterations, snrs, 'o-')
plt.xlabel('Iteration')
plt.ylabel('SNR')
plt.title('Self-Calibration SNR Progression')
plt.grid(True)
plt.savefig('selfcal_snr_progression.png')
```

---

**Last Updated:** 2025-11-19  
**Author:** DSA-110 Continuum Imaging Team
