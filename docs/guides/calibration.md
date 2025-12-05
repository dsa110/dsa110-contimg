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

## Calibration Options

| Parameter         | Description            | Default  |
| ----------------- | ---------------------- | -------- |
| `do_k`            | Enable K-calibration   | `False`  |
| `do_flagging`     | Pre-calibration RFI flagging | `True` |
| `refant`          | Reference antenna      | `"103"`  |
| `calibrator_name` | Calibrator for catalog lookup | `None` |

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
