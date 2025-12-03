# Mosaic Module

The DSA-110 mosaicking system provides automated, quality-controlled image combination with three simple tiers: **Quicklook**, **Science**, and **Deep**.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Event Sources                          │
│  • Cron (nightly)  • API request  • ESE detection   │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│           ABSURD Pipeline Scheduler                 │
│    Selects tier, creates job graph, monitors        │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│           Job Execution (3 steps)                   │
│                                                     │
│  1. MosaicPlanningJob                               │
│     └─> Query images, select tier, validate         │
│                                                     │
│  2. MosaicBuildJob (depends on #1)                  │
│     └─> Run reprojection, combine, write FITS       │
│                                                     │
│  3. MosaicQAJob (depends on #2)                     │
│     └─> Astrometry, photometry, artifact detection  │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│           Unified Database Update                   │
│  • mosaic_plans   • mosaics   • mosaic_qa           │
└─────────────────────────────────────────────────────┘
```

## Three Tiers

| Tier          | Purpose              | Max Images | RMS Threshold | Timeout |
| ------------- | -------------------- | ---------- | ------------- | ------- |
| **Quicklook** | Real-time monitoring | 10         | 0.01 Jy       | 5 min   |
| **Science**   | Publication-quality  | 100        | 0.001 Jy      | 30 min  |
| **Deep**      | Targeted integration | 1000       | 0.0005 Jy     | 120 min |

## Quick Start

### Python API

```python
from pathlib import Path
from dsa110_contimg.mosaic.builder import build_mosaic

# Build a mosaic from images
result = build_mosaic(
    image_paths=[Path("img1.fits"), Path("img2.fits"), Path("img3.fits")],
    output_path=Path("mosaic.fits"),
    alignment_order=3,  # 1=fast, 5=accurate
    write_weight_map=True,  # Also write uncertainty map
)

print(f"Created mosaic with {result.n_images} images")
print(f"Effective noise: {result.effective_noise_jy:.6f} Jy")
print(f"Weight map: {result.weight_map_path}")
```

### REST API

```bash
# Create a mosaic
curl -X POST http://localhost:8000/api/mosaic/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "nightly_20250101",
    "start_time": 1735689600,
    "end_time": 1735776000,
    "tier": "science"
  }'

# Check status
curl http://localhost:8000/api/mosaic/status/nightly_20250101
```

### Using Jobs Directly

```python
from dsa110_contimg.mosaic.jobs import MosaicPlanningJob, MosaicBuildJob, MosaicQAJob
from dsa110_contimg.mosaic.jobs import MosaicJobConfig

config = MosaicJobConfig(
    database_path=Path("/data/dsa110-contimg/state/db/pipeline.sqlite3"),
    mosaic_dir=Path("/stage/dsa110-contimg/mosaics"),
)

# 1. Plan
plan_job = MosaicPlanningJob(
    start_time=start_ts,
    end_time=end_ts,
    tier="science",
    mosaic_name="my_mosaic",
    config=config,
)
plan_result = plan_job.execute()

# 2. Build
build_job = MosaicBuildJob(plan_id=plan_result.outputs["plan_id"], config=config)
build_result = build_job.execute()

# 3. QA
qa_job = MosaicQAJob(mosaic_id=build_result.outputs["mosaic_id"], config=config)
qa_result = qa_job.execute()
print(f"QA status: {qa_result.outputs['qa_status']}")
```

## Module Structure

```
mosaic/
├── __init__.py      # Package exports
├── tiers.py         # MosaicTier enum, TierConfig, tier selection
├── builder.py       # Core build_mosaic() function with reproject
├── qa.py            # Quality assessment (astrometry, photometry, artifacts)
├── jobs.py          # ABSURD jobs: Planning, Build, QA
├── schema.py        # Database table definitions
├── pipeline.py      # NightlyMosaicPipeline, OnDemandMosaicPipeline
├── orchestrator.py  # MosaicOrchestrator for ABSURD integration
└── api.py           # FastAPI endpoints
```

## Key Features

### WCS Astrometric Alignment

Uses [`reproject`](https://reproject.readthedocs.io/) for proper WCS-aware reprojection:

- Configurable interpolation order (1=nearest-neighbor, 3=bilinear, 5=biquadratic)
- Handles non-coplanar fields through TAN projection
- Automatic output grid computation to cover all inputs

### Inverse-Variance Weighting

Images are combined with proper inverse-variance weighting:

```python
weight_i = 1 / RMS_i²
combined = Σ(weight_i × image_i) / Σ(weight_i)
```

### Uncertainty Propagation

Weight maps are output alongside mosaics for uncertainty estimation:

- `mosaic.fits` - Combined image
- `mosaic.weights.fits` - Weight map (inverse-variance)
- Per-pixel noise: `σ = 1 / √(weight)`
- Effective noise stored in `EFFNOISE` header keyword

### Quality-Based Rejection

The `MosaicPlanningJob` filters images by RMS threshold per tier:

- Only images with `noise_jy < rms_threshold_jy` are included
- Images sorted by RMS (best first)
- Limited by `max_images` per tier

### Quality Assessment

`MosaicQAJob` runs three checks:

1. **Astrometry**: Cross-match with NVSS/FIRST radio catalog
2. **Photometry**: Dynamic range and noise level
3. **Artifacts**: Edge discontinuities, ringing, banding detection

## Database Schema

Three tables in `pipeline.sqlite3`:

- **mosaic_plans**: Planning metadata (tier, time range, selected images)
- **mosaics**: Product registry (path, n_images, median_rms, qa_status)
- **mosaic_qa**: Quality metrics (astrometry_rms, dynamic_range, artifact_score)

## Primary Beam Correction

Primary beam correction for DSA-110 is typically applied at the imaging stage
(WSClean with beam model). The mosaicking module supports an optional
`apply_pb_correction` flag, but this is generally not needed if individual
images are already PB-corrected.

## Testing

```bash
cd /data/dsa110-contimg/backend
python -m pytest tests/contract/test_mosaic_contracts.py -v
```

42 contract tests verify:

- Builder creates valid FITS with WCS
- QA checks detect issues
- Jobs execute correctly
- Pipeline integration works end-to-end

## See Also

- [mature-mosaicking-code.md](../../../docs/mature-mosaicking-code.md) - Design document
- [API Reference](../../../docs/API_REFERENCE.md) - Full API documentation
