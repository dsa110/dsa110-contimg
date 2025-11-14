# Pointing Monitor Deployment Guide

**Date:** 2025-11-12  
**Status:** Production Ready  
**Purpose:** Guide for deploying and monitoring the DSA-110 pointing monitor
service

---

## Overview

The pointing monitor automatically extracts telescope pointing information from
incoming UVH5 visibility files and stores it in the products database. This
enables:

- Real-time tracking of telescope pointing
- Historical pointing analysis
- Cross-matching observations with calibrator transits
- Sky coverage visualization

---

## Architecture

### Components

1. **File System Watcher**: Monitors `/data/incoming/` for new `*_sb00.hdf5`
   files
2. **Pointing Extractor**: Reads pointing metadata from UVH5 headers
3. **Database Writer**: Stores pointing data in `pointing_history` table
4. **Health Monitor**: Performs periodic health checks and writes status JSON

### Data Flow

```
UVH5 Files (*_sb00.hdf5) → File Watcher → Pointing Extraction → SQLite Database
                                                      ↓
                                            Status JSON File
```

---

## Installation

### Prerequisites

1. **Python Environment**: Requires `casa6` conda environment
2. **Dependencies**: `watchdog`, `h5py`, `astropy`, `casacore`
3. **Directory Access**: Read access to `/data/incoming/`, write access to state
   directory
4. **Database**: Products database must exist (created automatically)

### Step 1: Verify Environment

```bash
# Check Python environment
/opt/miniforge/envs/casa6/bin/python --version

# Verify dependencies
/opt/miniforge/envs/casa6/bin/python -c "import watchdog, h5py, astropy"
```

### Step 2: Install Systemd Service

```bash
# Copy service file
sudo cp /data/dsa110-contimg/ops/systemd/contimg-pointing-monitor.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable contimg-pointing-monitor.service

# Start service
sudo systemctl start contimg-pointing-monitor.service

# Check status
sudo systemctl status contimg-pointing-monitor.service
```

### Step 3: Verify Installation

```bash
# Check service is running
sudo systemctl is-active contimg-pointing-monitor.service

# View logs
sudo journalctl -u contimg-pointing-monitor.service -f

# Check status file
cat /data/dsa110-contimg/state/pointing-monitor-status.json | jq

# Check database entries
sqlite3 /data/dsa110-contimg/state/products.sqlite3 \
  "SELECT COUNT(*) FROM pointing_history;"
```

---

## Configuration

### Environment Variables

The service uses variables from `/data/dsa110-contimg/ops/systemd/contimg.env`:

- `CONTIMG_INPUT_DIR`: Directory to watch (default: `/data/incoming`)
- `PIPELINE_PRODUCTS_DB`: Products database path
- `PIPELINE_STATE_DIR`: State directory for status file
- `CONTIMG_LOG_LEVEL`: Logging level (INFO, DEBUG, WARNING, ERROR)

### Service File Parameters

Edit `/etc/systemd/system/contimg-pointing-monitor.service` to customize:

- `--health-check-interval`: Health check frequency in seconds (default: 300)
- `--status-file`: Path to status JSON file (default:
  `${PIPELINE_STATE_DIR}/pointing-monitor-status.json`)
- `--log-level`: Logging verbosity

---

## Monitoring

### Status File

The monitor writes a JSON status file every 30 seconds:

```bash
# View current status
cat /data/dsa110-contimg/state/pointing-monitor-status.json | jq

# Monitor status changes
watch -n 5 'cat /data/dsa110-contimg/state/pointing-monitor-status.json | jq .metrics'

# Check health
cat /data/dsa110-contimg/state/pointing-monitor-status.json | jq .healthy
```

**Status File Structure:**

```json
{
  "running": true,
  "healthy": true,
  "issues": [],
  "watch_dir": "/data/incoming",
  "products_db": "/data/dsa110-contimg/state/products.sqlite3",
  "metrics": {
    "files_processed": 1234,
    "files_succeeded": 1230,
    "files_failed": 4,
    "success_rate_percent": 99.68,
    "uptime_seconds": 86400.0,
    "last_processed_time": 1704067200.0,
    "last_success_time": 1704067200.0,
    "last_error_time": null,
    "last_error_message": null,
    "recent_error_count": 0
  },
  "timestamp": 1704067200.0,
  "timestamp_iso": "2024-01-01T00:00:00Z"
}
```

### API Endpoint

Query status via the API:

```bash
# Get status
curl http://localhost:8000/api/pointing-monitor/status | jq

# Check health
curl http://localhost:8000/api/pointing-monitor/status | jq .healthy
```

### Logs

```bash
# Follow logs
sudo journalctl -u contimg-pointing-monitor.service -f

# View recent logs
sudo journalctl -u contimg-pointing-monitor.service -n 100

# View log files directly
tail -f /data/dsa110-contimg/state/logs/pointing-monitor.out
tail -f /data/dsa110-contimg/state/logs/pointing-monitor.err
```

### Database Queries

```bash
# Count total pointing entries
sqlite3 /data/dsa110-contimg/state/products.sqlite3 \
  "SELECT COUNT(*) FROM pointing_history;"

# Recent pointing entries
sqlite3 /data/dsa110-contimg/state/products.sqlite3 \
  "SELECT timestamp, ra_deg, dec_deg FROM pointing_history \
   ORDER BY timestamp DESC LIMIT 10;"

# Pointing coverage by declination
sqlite3 /data/dsa110-contimg/state/products.sqlite3 \
  "SELECT dec_deg, COUNT(*) as count FROM pointing_history \
   GROUP BY ROUND(dec_deg, 1) ORDER BY dec_deg;"
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status contimg-pointing-monitor.service

# View detailed logs
sudo journalctl -u contimg-pointing-monitor.service -n 50 --no-pager

# Check Python environment
ls -la /opt/miniforge/envs/casa6/bin/python

# Test manual execution
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.pointing.monitor \
  /data/incoming \
  /data/dsa110-contimg/state/products.sqlite3 \
  --status-file /tmp/test-status.json
```

### Common Issues

**1. Status file not updating**

- Check service is running:
  `sudo systemctl is-active contimg-pointing-monitor.service`
- Check write permissions: `ls -la /data/dsa110-contimg/state/`
- Check disk space: `df -h /data/dsa110-contimg/state/`

**2. No files being processed**

- Verify watch directory exists: `ls -la /data/incoming/`
- Check for `*_sb00.hdf5` files:
  `find /data/incoming -name "*_sb00.hdf5" | head -5`
- Check file permissions: `ls -la /data/incoming/*_sb00.hdf5 | head -1`

**3. Database errors**

- Check database exists: `ls -la /data/dsa110-contimg/state/products.sqlite3`
- Check database permissions:
  `ls -la /data/dsa110-contimg/state/products.sqlite3`
- Test database access:
  `sqlite3 /data/dsa110-contimg/state/products.sqlite3 "SELECT 1;"`

**4. High error rate**

- Check recent errors in status file:
  `jq .metrics.recent_error_count /data/dsa110-contimg/state/pointing-monitor-status.json`
- View error messages:
  `jq .metrics.last_error_message /data/dsa110-contimg/state/pointing-monitor-status.json`
- Check UVH5 file format:
  `h5dump -H /data/incoming/<file>_sb00.hdf5 | grep -i "phase_center"`

### Health Check Failures

The monitor performs health checks every 5 minutes. Common failures:

- **Watch directory not accessible**: Check permissions and existence
- **Database connection lost**: Database may be locked or corrupted
- **Status file write failure**: Check disk space and permissions

Health check failures are logged but don't stop the monitor. Check logs for
details.

---

## Manual Operations

### Start/Stop Service

```bash
# Start
sudo systemctl start contimg-pointing-monitor.service

# Stop
sudo systemctl stop contimg-pointing-monitor.service

# Restart
sudo systemctl restart contimg-pointing-monitor.service

# Enable on boot
sudo systemctl enable contimg-pointing-monitor.service

# Disable on boot
sudo systemctl disable contimg-pointing-monitor.service
```

### Manual Execution

For testing or troubleshooting:

```bash
# Basic execution
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.pointing.monitor \
  /data/incoming \
  /data/dsa110-contimg/state/products.sqlite3

# With status file
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.pointing.monitor \
  /data/incoming \
  /data/dsa110-contimg/state/products.sqlite3 \
  --status-file /tmp/pointing-monitor-status.json

# Debug mode
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.pointing.monitor \
  /data/incoming \
  /data/dsa110-contimg/state/products.sqlite3 \
  --log-level DEBUG
```

### Backfill Historical Data

To process historical files:

```bash
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.pointing.backfill_pointing \
  /data/incoming \
  /data/dsa110-contimg/state/products.sqlite3 \
  --start-date 2025-10-01 \
  --end-date 2025-10-23
```

---

## Integration

### API Integration

The pointing monitor status is available via the API:

```python
import requests

# Get status
response = requests.get("http://localhost:8000/api/pointing-monitor/status")
status = response.json()

if status["healthy"]:
    print(f"Monitor is healthy: {status['metrics']['files_processed']} files processed")
else:
    print(f"Issues: {status['issues']}")
```

### Dashboard Integration

The frontend can query pointing monitor status:

```typescript
const response = await fetch("/api/pointing-monitor/status");
const status = await response.json();
```

### Alerting Integration

Monitor the status file for alerting:

```bash
#!/bin/bash
# Check pointing monitor health
STATUS_FILE="/data/dsa110-contimg/state/pointing-monitor-status.json"

if [ ! -f "$STATUS_FILE" ]; then
    echo "ALERT: Pointing monitor status file not found"
    exit 1
fi

HEALTHY=$(jq -r .healthy "$STATUS_FILE")
if [ "$HEALTHY" != "true" ]; then
    ISSUES=$(jq -r '.issues | join(", ")' "$STATUS_FILE")
    echo "ALERT: Pointing monitor unhealthy - $ISSUES"
    exit 1
fi
```

---

## Performance

### Resource Usage

- **CPU**: < 1% (idle), spikes during file processing
- **Memory**: ~50-100 MB
- **Disk I/O**: Minimal (header-only reads)
- **Database**: Small writes (~100 bytes per file)

### Scalability

- Handles hundreds of files per hour
- Database grows ~1 KB per observation
- Status file updates every 30 seconds
- Health checks every 5 minutes

### Optimization

- Only processes `_sb00.hdf5` files (one per observation)
- Header-only reads (no full file load)
- Batch database commits
- Efficient file watching (watchdog library)

---

## Maintenance

### Regular Checks

- **Daily**: Verify service is running and healthy
- **Weekly**: Check error rates and database growth
- **Monthly**: Review pointing coverage and gaps

### Database Maintenance

```bash
# Check database size
du -h /data/dsa110-contimg/state/products.sqlite3

# Vacuum database (reclaim space)
sqlite3 /data/dsa110-contimg/state/products.sqlite3 "VACUUM;"

# Analyze database (update statistics)
sqlite3 /data/dsa110-contimg/state/products.sqlite3 "ANALYZE pointing_history;"
```

### Log Rotation

Logs are written to:

- `/data/dsa110-contimg/state/logs/pointing-monitor.out`
- `/data/dsa110-contimg/state/logs/pointing-monitor.err`

Configure logrotate if needed:

```bash
# /etc/logrotate.d/pointing-monitor
/data/dsa110-contimg/state/logs/pointing-monitor.* {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

---

## References

- **Monitor Script**: `src/dsa110_contimg/pointing/monitor.py`
- **Pointing Utilities**: `src/dsa110_contimg/pointing/utils.py`
- **Service File**: `ops/systemd/contimg-pointing-monitor.service`
- **API Endpoint**: `/api/pointing-monitor/status`
- **Review Document**: `docs/archive/reports/POINTING_MONITORING_REVIEW.md`
