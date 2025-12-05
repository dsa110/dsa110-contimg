# Calibration Guide

The DSA-110 pipeline performs bandpass (BP) and gain (G) calibration. K-calibration (delay) is skipped by default as it's not needed for DSA-110.

## Running Calibration

### Via ABSURD Task Queue (Recommended)

Calibration is typically run as part of the automated pipeline via ABSURD tasks:

```python
from dsa110_contimg.absurd import AbsurdClient
from dsa110_contimg.absurd.config import AbsurdConfig
import asyncio

async def run_calibration(ms_path: str):
    config = AbsurdConfig.from_env()
    async with AbsurdClient(config.database_url) as client:
        await client.spawn_task(
            queue_name="dsa110-calibration",
            task_name="calibration-solve",
            params={
                "inputs": {"ms_path": ms_path},
                "config": {
                    "calibration": {
                        "refant": "103",
                        "do_k": False,
                    }
                }
            },
        )

asyncio.run(run_calibration("/stage/dsa110-contimg/ms/2025-01-15T12:00:00.ms"))
```

### Python API

For direct Python usage:

```python
from dsa110_contimg.calibration.cli import run_calibrator

# Run full calibration sequence (model → bandpass → gains)
caltables = run_calibrator(
    ms_path="/path/to/observation.ms",
    cal_field="0",           # Field selection
    refant="103",            # Reference antenna
    do_flagging=True,        # Pre-calibration flagging
    do_k=False,              # Skip K (delay) calibration
    calibrator_name="3C286", # For catalog lookup
)

print(f"Created tables: {caltables}")
```

### Applying Calibration

```python
from dsa110_contimg.calibration.applycal import apply_interpolated_calibration

apply_interpolated_calibration(
    ms_path="/path/to/observation.ms",
    caltables={
        "B": "/path/to/bandpass.bcal",
        "G": "/path/to/gains.gcal",
    },
)
```

## Phase Coherence: Phaseshifting for DSA-110

**CRITICAL for DSA-110**: DSA-110 drift-scan observations produce 24 fields over ~5 minutes, each phased to its own meridian position (RA = LST at that time). This creates geometric phase gradients that must be corrected before calibration or imaging.

### Phaseshift Modes

The pipeline provides unified phaseshifting via `phaseshift_ms()` with three modes:

#### 1. Calibrator Mode (for Calibration MS)
Phaseshifts calibrator field(s) to the calibrator's true position, placing the point source at phase center. This ensures all baselines see constant phase (zero geometric offset), which is required for stable bandpass calibration.

```python
from dsa110_contimg.calibration.runner import phaseshift_ms

# Phaseshift calibrator field to 0834+555 position
cal_ms, phasecenter = phaseshift_ms(
    ms_path="observation.ms",
    field="12",                    # Field containing calibrator
    mode="calibrator",
    calibrator_name="0834+555"
)
# Output: observation_cal.ms with calibrator at phase center
```

**When to use**: Before solving bandpass calibration on a calibrator MS.

**Effect**: Removes geometric phase gradient → enables field combination with `combine_fields=True` → higher SNR.

#### 2. Median Meridian Mode (for Science MS)
Phaseshifts all fields to the median meridian position across the 24 fields. This minimizes the maximum phase offset across fields, reducing phase variability when imaging.

```python
# Phaseshift science MS to median meridian
science_ms, phasecenter = phaseshift_ms(
    ms_path="observation.ms",
    field="",                      # All fields
    mode="median_meridian"
)
# Output: observation_meridian.ms centered on median RA/Dec
```

**When to use**: Before imaging science observations with all 24 fields.

**Effect**: Minimizes phase offsets → reduces phase noise → cleaner images.

#### 3. Manual Mode (for Custom Targets)
Phaseshifts to explicitly specified RA/Dec coordinates.

```python
# Phaseshift to custom position
custom_ms, phasecenter = phaseshift_ms(
    ms_path="observation.ms",
    mode="manual",
    target_ra_deg=128.7287,
    target_dec_deg=55.5725
)
```

### Automatic Phaseshifting in Pipeline

The `CalibrationSolveStage` automatically phaseshifts calibrator MS when `do_phaseshift=True` (default):

```python
context = PipelineContext(
    config=config,
    outputs={"ms_path": "calibrator.ms"},
    inputs={
        "calibration_params": {
            "do_phaseshift": True,           # Default: enabled
            "calibrator_name": "0834+555",   # Required for phaseshift
            "field": "0~23",                 # All 24 fields (new default)
            "combine_fields": True,          # Combine fields (new default)
            "combine_spw": True,             # Combine SPWs (new default)
        }
    }
)
result = calibration_solve_stage.execute(context)
```

### Phase Variability Reduction Strategy

The pipeline reduces phase variability through three mechanisms:

1. **Phaseshift to phase center** → Removes geometric phase gradients
2. **Combine all 24 fields** (`field='0~23'`, `combine_fields=True`) → Increases SNR by 24×
3. **Combine spectral windows** (`combine_spw=True`) → Further increases SNR

**Result**: Stable, high-SNR bandpass solutions with minimal phase scatter.

## Calibration Options

| Parameter         | Description            | Default  |
| ----------------- | ---------------------- | -------- |
| `field`           | Field selection        | `"0~23"` (all 24 fields) |
| `combine_fields`  | Combine fields for SNR | `True`   |
| `combine_spw`     | Combine spectral windows | `True` |
| `do_phaseshift`   | Phaseshift before calibration | `True` |
| `do_k`            | Enable K-calibration   | `False`  |
| `do_flagging`     | Pre-calibration RFI flagging | `True` |
| `refant`          | Reference antenna      | `"103"`  |
| `calibrator_name` | Calibrator for catalog lookup | `None` (required if `do_phaseshift=True`) |

## Environment Configuration

Calibration settings can be configured via environment variables:

| Variable                   | Description            | Default |
| -------------------------- | ---------------------- | ------- |
| `PIPELINE_CAL_BP_MINSNR`   | Bandpass minimum SNR   | `3.0`   |
| `PIPELINE_CAL_GAIN_SOLINT` | Gain solution interval | `inf`   |
| `PIPELINE_DEFAULT_REFANT`  | Reference antenna      | `103`   |

## Calibration Tables

Calibration tables are stored in the unified pipeline database and can be queried:

```bash
# List recent calibration tables
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
  "SELECT * FROM calibration_tables ORDER BY created_at DESC LIMIT 10;"
```

## Calibration Pipeline Stages

The calibration pipeline consists of these stages:

1. **CalibrationSolveStage** - Solve for bandpass, gains, and optionally delays
2. **CalibrationApplyStage** - Apply calibration solutions to target data
3. **CalibrationValidateStage** - QA validation of calibration quality

## Operations Scripts

Useful calibration-related scripts in `scripts/ops/calibration/`:

| Script | Description |
| ------ | ----------- |
| `solve_bandpass_only.py` | Solve bandpass without other calibrations |
| `recommend_refant.py` | Recommend reference antenna for an MS |
| `check_refant_data.py` | Check reference antenna data quality |
| `diagnose_bandpass_output.py` | Diagnose bandpass calibration issues |
| `clear_all_calibration_artifacts.py` | Clean up calibration tables |

## Related Documentation

- [Imaging Guide](imaging.md) - Apply calibration then image
- [Storage & File Organization](storage-and-file-organization.md) - Database paths
- [API Reference](../API_REFERENCE.md) - Calibration API endpoints
