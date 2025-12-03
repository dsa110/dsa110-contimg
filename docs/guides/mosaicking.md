# Mosaicking Guide

This guide explains how to create mosaics from DSA-110 continuum images using the automated mosaicking system.

## Overview

The DSA-110 mosaicking system combines multiple images into a single, deeper mosaic with:

- **Proper WCS alignment** using reprojection
- **Inverse-variance weighting** for optimal signal-to-noise
- **Quality control** through automated QA checks
- **Three simple tiers** for different use cases

## Quick Start

### Using the API

The simplest way to create a mosaic is via the REST API:

```bash
# Create a science-tier mosaic from the last 24 hours
curl -X POST http://localhost:8000/api/mosaic/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "daily_mosaic_20250101",
    "start_time": 1735689600,
    "end_time": 1735776000,
    "tier": "science"
  }'

# Response:
# {"status": "accepted", "execution_id": "daily_mosaic_20250101", "message": "..."}

# Check status
curl http://localhost:8000/api/mosaic/status/daily_mosaic_20250101

# When complete:
# {
#   "name": "daily_mosaic_20250101",
#   "status": "completed",
#   "tier": "science",
#   "n_images": 47,
#   "mosaic_path": "/stage/dsa110-contimg/mosaics/daily_mosaic_20250101.fits",
#   "qa_status": "PASS"
# }
```

### Using Python

```python
from pathlib import Path
from dsa110_contimg.mosaic.builder import build_mosaic

# Direct mosaic building (bypasses database)
result = build_mosaic(
    image_paths=[
        Path("/stage/dsa110-contimg/images/obs001.fits"),
        Path("/stage/dsa110-contimg/images/obs002.fits"),
        Path("/stage/dsa110-contimg/images/obs003.fits"),
    ],
    output_path=Path("/stage/dsa110-contimg/mosaics/custom_mosaic.fits"),
    alignment_order=3,
    write_weight_map=True,
    apply_pb_correction=True,  # Apply primary beam correction
)

print(f"Mosaic created: {result.output_path}")
print(f"Combined {result.n_images} images")
print(f"Coverage: {result.coverage_sq_deg:.4f} sq deg")
print(f"Effective noise: {result.effective_noise_jy * 1e6:.1f} µJy")
```

### Primary Beam Correction

The `apply_pb_correction=True` option applies primary beam correction using
the DSA-110 Airy disk model:

- **Dish diameter**: 4.7 m
- **Frequency**: 1.405 GHz (L-band center)
- **Model**: `PB(θ) = (2·J₁(x)/x)²` where `x = π·D·θ/λ`
- **Cutoff**: Pixels with PB < 0.1 are masked to avoid edge noise amplification

```python
# Without PB correction (default) - faster, good for quicklook
result = build_mosaic(image_paths, output_path)

# With PB correction - recommended for science-tier and deep mosaics
result = build_mosaic(image_paths, output_path, apply_pb_correction=True)
```

## Understanding Tiers

Choose the right tier for your use case:

| Tier          | When to Use                                    | Time    | Quality     |
| ------------- | ---------------------------------------------- | ------- | ----------- |
| **Quicklook** | Real-time monitoring, checking observations    | ~5 min  | Good enough |
| **Science**   | Nightly products, analysis, publications       | ~30 min | High        |
| **Deep**      | Targeted deep fields, stacking multiple nights | ~2 hr   | Best        |

### Tier Selection Logic

```python
from dsa110_contimg.mosaic.tiers import select_tier_for_request

# Automatic selection based on time range
tier = select_tier_for_request(time_range_hours=0.5)  # → QUICKLOOK
tier = select_tier_for_request(time_range_hours=24)   # → SCIENCE
tier = select_tier_for_request(time_range_hours=72)   # → DEEP

# Explicit quality request
tier = select_tier_for_request(time_range_hours=24, target_quality="deep")  # → DEEP
```

## Interpreting Results

### Output Files

For each mosaic, two files are produced:

1. **`mosaic_name.fits`** - The combined image
2. **`mosaic_name.weights.fits`** - Weight map for uncertainty

### FITS Header Keywords

```
NIMAGES  = 47                  / Number of images combined
MEDRMS   = 0.000342            / Median RMS of inputs (Jy)
EFFNOISE = 0.000051            / Effective noise from weights (Jy)
COVERAGE = 0.0234              / Sky coverage (sq deg)
BUNIT    = 'Jy/beam'           / Image units
PBCORR   = T                   / Primary beam correction applied
PBCUT    = 0.1                 / PB cutoff threshold
```

### Effective Noise Calculation

The `effective_noise_jy` (stored as `EFFNOISE` in FITS header and in the database)
represents the theoretical noise improvement from inverse-variance weighting:

```
σ_eff = 1 / √(Σ wᵢ)  where wᵢ = 1/σᵢ²
```

For N images with equal noise σ₀, this gives σ_eff = σ₀/√N (the √N improvement).
The actual improvement may be less due to:

- Non-uniform coverage (edge pixels have fewer images)
- Variable noise across input images
- Systematic errors not captured by weights

### Using the Weight Map

The weight map enables per-pixel uncertainty estimation:

```python
from astropy.io import fits
import numpy as np

# Load mosaic and weights
with fits.open("mosaic.fits") as hdul:
    data = hdul[0].data

with fits.open("mosaic.weights.fits") as hdul:
    weights = hdul[0].data

# Compute per-pixel noise (σ = 1/√weight)
noise_map = np.where(weights > 0, 1.0 / np.sqrt(weights), np.nan)

# Signal-to-noise ratio
snr = data / noise_map
```

## Quality Assessment

Every mosaic undergoes automated QA checks:

### Astrometry Check

- Cross-matches sources with NVSS/FIRST radio catalogs
- Reports RMS positional offset in arcseconds
- Threshold: < 0.5" (science), < 1.0" (quicklook)

### Photometry Check

- Measures dynamic range (peak / noise)
- Reports median noise level
- Threshold: DR > 100 (science), > 50 (quicklook)

### Artifact Detection

- Detects edge discontinuities, ringing, banding
- Reports artifact score (0 = clean, 1 = severe)
- Warning threshold: > 0.3

### QA Status

- **PASS**: All checks passed
- **WARN**: Minor issues detected (warnings)
- **FAIL**: Critical issues (see `critical_failures`)

```python
from dsa110_contimg.mosaic.qa import run_qa_checks
from pathlib import Path

qa = run_qa_checks(Path("mosaic.fits"), tier="science")

print(f"Status: {qa.status}")
print(f"Astrometry RMS: {qa.astrometry_rms:.2f} arcsec")
print(f"Dynamic range: {qa.dynamic_range:.0f}")
print(f"Artifact score: {qa.artifact_score:.2f}")

if qa.warnings:
    print(f"Warnings: {qa.warnings}")
if qa.critical_failures:
    print(f"Failures: {qa.critical_failures}")
```

## Automated Pipelines

### Nightly Mosaic

The nightly pipeline runs automatically at 03:00 UTC:

```python
from dsa110_contimg.mosaic.pipeline import NightlyMosaicPipeline

pipeline = NightlyMosaicPipeline(config)
# Automatically:
# 1. Selects science tier
# 2. Queries last 24h of images
# 3. Filters by RMS threshold
# 4. Builds mosaic
# 5. Runs QA
# 6. Updates database
```

### On-Demand Mosaic

For custom time ranges or deep integrations:

```python
from dsa110_contimg.mosaic.pipeline import OnDemandMosaicPipeline

pipeline = OnDemandMosaicPipeline(
    config,
    request_params={
        "name": "deep_field_A",
        "start_time": start_ts,
        "end_time": end_ts,
        "tier": "deep",
    }
)
pipeline.run()
```

## Troubleshooting

### "No images found in time range"

- Check that images exist in the database for the specified time range
- Verify the RMS threshold isn't too strict (try quicklook tier first)
- Ensure images have valid `noise_jy` values

### Low Dynamic Range

- May indicate calibration issues in input images
- Check individual image quality before mosaicking
- Consider using a stricter RMS threshold

### High Artifact Score

- Could indicate bright source sidelobes
- Check for edge effects from incomplete u-v coverage
- Consider excluding problematic images manually

### Astrometry Warnings

- Verify WCS headers in input images
- Check for proper field center coordinates
- May need to re-image with updated calibration

## Advanced Usage

### Custom Image Selection

```python
import sqlite3
from pathlib import Path

# Query images directly
conn = sqlite3.connect("/data/dsa110-contimg/state/db/pipeline.sqlite3")
cursor = conn.execute("""
    SELECT path FROM images
    WHERE noise_jy < 0.0005
      AND center_dec_deg BETWEEN 30 AND 35
    ORDER BY noise_jy ASC
    LIMIT 50
""")

image_paths = [Path(row[0]) for row in cursor.fetchall()]
conn.close()

# Build custom mosaic
from dsa110_contimg.mosaic.builder import build_mosaic

result = build_mosaic(
    image_paths=image_paths,
    output_path=Path("custom_dec_strip.fits"),
    alignment_order=5,  # High accuracy for deep mosaic
)
```

### Batch Processing

```python
from dsa110_contimg.mosaic.jobs import MosaicPlanningJob, MosaicBuildJob, MosaicQAJob
from dsa110_contimg.mosaic.jobs import MosaicJobConfig
from pathlib import Path

config = MosaicJobConfig(
    database_path=Path("/data/dsa110-contimg/state/db/pipeline.sqlite3"),
    mosaic_dir=Path("/stage/dsa110-contimg/mosaics"),
)

# Process multiple time windows
for day in range(1, 8):  # One week
    start_ts = base_ts + (day - 1) * 86400
    end_ts = base_ts + day * 86400

    plan_job = MosaicPlanningJob(
        start_time=start_ts,
        end_time=end_ts,
        tier="science",
        mosaic_name=f"week1_day{day}",
        config=config,
    )
    plan_result = plan_job.execute()

    if plan_result.success:
        build_job = MosaicBuildJob(
            plan_id=plan_result.outputs["plan_id"],
            config=config,
        )
        build_job.execute()
```

## See Also

- [Module README](../backend/src/dsa110_contimg/mosaic/README.md) - Technical details
- [API Reference](API_REFERENCE.md) - Complete API documentation
- [Design Document](mature-mosaicking-code.md) - Architecture decisions
