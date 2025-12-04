# DSA-110 Streaming Pipeline Operations Guide

This document covers production deployment and operations for `dsa110-stream`.

## Quick Start

```bash
# Run manually (for testing)
dsa110-stream \
    --input-dir /data/incoming \
    --output-dir /data/ms \
    --queue-db /data/dsa110-contimg/state/db/pipeline.sqlite3 \
    --enable-calibration-solving \
    --enable-photometry \
    --monitoring

# Install as systemd service
sudo cp /data/dsa110-contimg/backend/ops/systemd/dsa110-stream.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable dsa110-stream
sudo systemctl start dsa110-stream
```

## Service Management

```bash
# View status
sudo systemctl status dsa110-stream

# View logs
journalctl -u dsa110-stream -f

# Or from log file
tail -f /data/dsa110-contimg/state/logs/streaming-pipeline.log

# Restart after changes
sudo systemctl restart dsa110-stream

# Stop gracefully (allows current processing to finish)
sudo systemctl stop dsa110-stream
```

## Health Monitoring

When running with `--monitoring`, an HTTP endpoint is available:

```bash
# Health check (returns JSON)
curl http://localhost:9100/health

# Prometheus metrics
curl http://localhost:9100/metrics

# Readiness probe (for k8s/container orchestration)
curl http://localhost:9100/ready
```

### Prometheus Configuration

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: "dsa110-streaming"
    static_configs:
      - targets: ["localhost:9100"]
    metrics_path: /metrics
```

### Grafana Dashboard

Available at: `ops/grafana/dsa110-pipeline-dashboard.json`

Key metrics:

- `dsa110_streaming_queue{state="collecting"}` - Groups waiting for subbands
- `dsa110_streaming_queue{state="in_progress"}` - Groups being processed
- `dsa110_streaming_queue{state="completed"}` - Successfully processed groups
- `dsa110_streaming_queue{state="failed"}` - Failed groups
- `dsa110_streaming_disk_free_gb{path="output"}` - Free disk space

## Configuration Options

| Option                         | Default                     | Description                        |
| ------------------------------ | --------------------------- | ---------------------------------- |
| `--input-dir`                  | **required**                | Watch directory for HDF5 files     |
| `--output-dir`                 | **required**                | Output directory for MS files      |
| `--queue-db`                   | `state/db/pipeline.sqlite3` | Path to unified database           |
| `--expected-subbands`          | 16                          | Number of subbands per observation |
| `--chunk-duration`             | 5.0                         | Minutes per time chunk             |
| `--enable-calibration-solving` | off                         | Enable automatic calibration       |
| `--enable-photometry`          | off                         | Enable source measurement          |
| `--monitoring`                 | off                         | Enable health HTTP endpoint        |
| `--health-port`                | 9100                        | Port for health endpoint           |

## Troubleshooting

### Pipeline not processing groups

```bash
# Check queue status
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
  "SELECT state, COUNT(*) FROM processing_queue GROUP BY state"

# Check for stuck in_progress groups
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
  "SELECT group_id, state, error FROM processing_queue WHERE state='in_progress'"
```

### Disk space warnings

The pipeline checks disk space before processing. If below 10GB, it will pause.

```bash
# Check disk space
df -h /data

# Clear old products if needed
find /data/ms -name "*.ms" -mtime +30 -type d
```

### Database locked errors

The SQLite database uses WAL mode with 30s timeout. If you see lock errors:

```bash
# Check for long-running queries
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
  "PRAGMA busy_timeout"

# Ensure only one instance running
pgrep -af dsa110-stream
```

### Corrupt HDF5 files

The pipeline validates files before processing:

```bash
# Check for invalid files in a group
python -c "
from dsa110_contimg.conversion.streaming import SubbandQueue
queue = SubbandQueue('/data/dsa110-contimg/state/db/pipeline.sqlite3')
valid, invalid = queue.validate_group_files('2025-10-02T00:12:00')
print(f'Valid: {len(valid)}, Invalid: {len(invalid)}')
if invalid:
    print('Invalid files:', invalid)
"
```

## Fallback to Legacy

If the new streaming module has issues, the legacy `streaming_converter.py` still works:

```bash
python -m dsa110_contimg.conversion.streaming_converter \
    --input-dir /data/incoming \
    --output-dir /data/ms
```

Both use the same `processing_queue` table, so data is shared.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  StreamingWatcher│────▶│  SubbandQueue   │◀────│ StreamingWorker │
│  (watchdog/poll) │     │  (processing_   │     │  (stages)       │
└─────────────────┘     │   queue table)  │     └─────────────────┘
                        └─────────────────┘              │
                                                         ▼
                                                ┌─────────────────┐
                                                │  Pipeline Stages │
                                                │  - Conversion    │
                                                │  - Calibration   │
                                                │  - Imaging       │
                                                │  - Photometry    │
                                                └─────────────────┘
```

## Related Documentation

- [Streaming Module README](../src/dsa110_contimg/conversion/streaming/README.md)
- [Database Schema](../src/dsa110_contimg/database/schema.sql)
- [Main README](../README.md)

## Dashboard / API Integration

The streaming pipeline integrates with the dashboard API, allowing on-demand
conversion alongside calibration, imaging, mosaicking, and photometry.

### API Endpoints

| Endpoint                         | Method | Description                      |
| -------------------------------- | ------ | -------------------------------- |
| `/api/v1/conversion/pending`     | GET    | List pending subband groups      |
| `/api/v1/conversion/stats`       | GET    | Get conversion statistics        |
| `/api/v1/conversion/convert`     | POST   | Trigger conversion (auth needed) |
| `/api/v1/conversion/status/{id}` | GET    | Get group conversion status      |
| `/api/v1/conversion/hdf5-index`  | GET    | Query raw HDF5 file index        |

### Example: Trigger Conversion from Dashboard

```bash
# List pending complete groups
curl http://localhost:8000/api/v1/conversion/pending?complete_only=true

# Trigger conversion for specific groups
curl -X POST http://localhost:8000/api/v1/conversion/convert \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"group_ids": ["2025-10-02T00:05:18", "2025-10-02T00:10:22"]}'

# Check conversion status
curl http://localhost:8000/api/v1/conversion/status/2025-10-02T00:05:18
```

### Integration with Other Pipeline Stages

The dashboard provides a unified interface for the full pipeline:

1. **Conversion** (`/api/v1/conversion/*`) - HDF5 → MS
2. **Calibration** (`/api/v1/cal/*`) - Apply calibration tables
3. **Imaging** (`/api/v1/imaging/*`) - Create FITS images
4. **Mosaics** (`/api/mosaic/*`) - Combine images
5. **Photometry** (`/api/v1/sources/*`) - Measure sources
6. **Light Curves** - Track source variability over time

All stages can be triggered on-demand from the web dashboard or via API calls.
