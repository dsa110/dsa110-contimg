# Calibration Guide

The DSA-110 pipeline performs bandpass (BP) and gain (G) calibration. K-calibration (delay) is skipped by default as it's not needed for DSA-110.

## Running Calibration

### Basic Calibration

```bash
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /path/to/observation.ms \
  --field 0 \
  --refant 103
```

### Calibration Options

| Flag            | Description            | Default  |
| --------------- | ---------------------- | -------- |
| `--do-k`        | Enable K-calibration   | Disabled |
| `--skip-bp`     | Skip bandpass          | Enabled  |
| `--skip-g`      | Skip gain              | Enabled  |
| `--bp-minsnr`   | Bandpass min SNR       | 3.0      |
| `--gain-solint` | Gain solution interval | inf      |
| `--refant`      | Reference antenna      | 103      |

### Applying Existing Calibration

```bash
python -m dsa110_contimg.calibration.cli apply \
  --ms /path/to/observation.ms \
  --caltable /path/to/calibration.bcal
```

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

## CLI Reference

```bash
# Full help
python -m dsa110_contimg.calibration.cli --help

# Subcommand help
python -m dsa110_contimg.calibration.cli calibrate --help
python -m dsa110_contimg.calibration.cli apply --help
```

## Related Documentation

- [Imaging Guide](imaging.md) - Apply calibration then image
- [Storage & File Organization](storage-and-file-organization.md) - Database paths
- Streaming Pipeline (`backend/docs/ops/streaming-pipeline.md`) - Automatic calibration in streaming mode
