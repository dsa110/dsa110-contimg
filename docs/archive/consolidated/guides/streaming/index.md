# Streaming Service Guide

**Last Updated:** November 29, 2025

The streaming service watches incoming UVH5 subband files and converts them into
CASA Measurement Sets (MS), optionally triggering calibration and imaging.

---

## Quick Links

| Document                                                              | Description                           |
| --------------------------------------------------------------------- | ------------------------------------- |
| [Quick Start](quickstart.md)                                          | Get streaming running in 5 minutes    |
| [Deployment](deployment.md)                                           | Docker Compose and systemd deployment |
| [Troubleshooting](troubleshooting.md)                                 | Common issues and solutions           |
| [API Reference](api.md)                                               | REST API endpoints                    |
| [Architecture](../../architecture/pipeline/streaming-architecture.md) | System design                         |

---

## Overview

### What It Does

1. **Ingest** - Watch for incoming UVH5 subband files
2. **Group** - Collect all 16 subbands for a timestamp
3. **Convert** - Transform to CASA Measurement Set
4. **Process** - (Optional) Calibrate/apply and quick image

### Where It Runs

- **Docker Compose** - Recommended for full stack
- **systemd** - For production host services

### Where to View Results

- **Products DB** - `ms_index`, `images` tables
- **Dashboard** - `/streaming` page

---

## Dashboard Control

**Page:** Dashboard :arrow_right: Streaming (`/streaming`)

**Controls:**

- Start, Stop, Restart service
- Edit configuration
- View status, metrics, queue

**Health Indicators:**

- Service uptime
- CPU/memory usage
- Error indicators
- Link to logs

---

## Standalone Converter (CLI)

For one-off or batch conversion without the daemon:

```bash
# Quick look convert (RAM staging recommended)
scripts/run_conversion.sh /path/to/uvh5_dir /stage/dsa110-contimg/ms \
  2025-10-13T13:25:00 2025-10-13T13:30:00
```

---

## Output Organization

```text
/stage/dsa110-contimg/ms/
├── science/           # Science observations
│   └── YYYY-MM-DD/
│       └── <timestamp>.ms/
├── calibrators/       # Calibrator observations
│   └── YYYY-MM-DD/
│       └── <timestamp>.ms/
└── failed/            # Failed conversions
    └── YYYY-MM-DD/
        └── <timestamp>.ms/
```

---

## Queue States

The `ingest_queue` table uses this state machine:

| State              | Description                 |
| ------------------ | --------------------------- |
| `collecting`       | Waiting for all 16 subbands |
| `pending`          | Ready for processing        |
| `in_progress`      | Claimed by a worker         |
| `processing_fresh` | First-pass conversion       |
| `resuming`         | Recovery from checkpoint    |
| `failed`           | Exceeded retry budget       |
| `completed`        | MS written successfully     |

---

## Quick Start Warnings

- Always use casa6 Python (`/opt/miniforge/envs/casa6/bin/python`)
- Verify env vars and directory permissions before enabling
- Use tmpfs (`/dev/shm`) for faster staging when memory allows
- Confirm HDF5 locking (`HDF5_USE_FILE_LOCKING=FALSE`) on NFS

---

## Configuration

Key parameters:

| Parameter           | Default                    | Description                      |
| ------------------- | -------------------------- | -------------------------------- |
| `input_dir`         | `/data/incoming`           | Watch directory for UVH5 files   |
| `output_dir`        | `/stage/dsa110-contimg/ms` | Output directory for MS          |
| `expected_subbands` | 16                         | Number of subbands per timestamp |
| `chunk_duration`    | 5.0                        | Time chunk in seconds            |
| `max_workers`       | 4                          | Parallel conversion workers      |
| `stage_to_tmpfs`    | false                      | Use RAM for staging              |

---

## Related Documentation

- [CLI Reference](../../reference/cli.md)
- [Pipeline Architecture](../../architecture/pipeline/pipeline_overview.md)
- [Products Database](../../reference/database_schema.md)
