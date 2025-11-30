# Troubleshooting Common Scenarios

This runbook covers common failure scenarios and their resolutions for the
DSA-110 Continuum Imaging Pipeline.

## Quick Diagnosis

Run the comprehensive health check:

```bash
python scripts/health_check.py
```

For JSON output (suitable for monitoring systems):

```bash
python scripts/health_check.py --json
```

## Database Issues

### Schema Mismatches / Missing Columns

**Symptoms:**

- `sqlite3.OperationalError: no such column: X`
- API returns 500 errors for database operations
- Pipeline stages fail with database errors

**Diagnosis:**

```bash
python scripts/fix_schemas.py --verbose
```

**Fix:**

```bash
python scripts/fix_schemas.py --fix
```

### Locked Database

**Symptoms:**

- `sqlite3.OperationalError: database is locked`
- Operations hang indefinitely
- API endpoints timeout

**Diagnosis:**

```bash
# Check for lock files
ls -la /data/dsa110-contimg/state/*.lock

# Check for processes holding the database
lsof /data/dsa110-contimg/state/products.sqlite3
```

**Fix:**

```bash
# Clear stale locks (checks if holding process is dead)
python scripts/fix_schemas.py --clear-locks

# Manual: If process is dead, remove lock
rm /data/dsa110-contimg/state/products.lock

# Force WAL checkpoint
sqlite3 /data/dsa110-contimg/state/products.sqlite3 "PRAGMA wal_checkpoint(TRUNCATE);"
```

### Large WAL Files

**Symptoms:**

- Database directory growing unexpectedly
- `.sqlite3-wal` files > 100MB
- Slow database operations

**Diagnosis:**

```bash
ls -lh /data/dsa110-contimg/state/*.sqlite3-wal
```

**Fix:**

```bash
# Checkpoint the WAL
sqlite3 /data/dsa110-contimg/state/products.sqlite3 "PRAGMA wal_checkpoint(TRUNCATE);"

# Or run fix_schemas which includes this
python scripts/fix_schemas.py --fix
```

## Filesystem Issues

### Disk Space Exhaustion

**Symptoms:**

- `OSError: [Errno 28] No space left on device`
- Image creation fails
- Database writes fail

**Diagnosis:**

```bash
df -h /data /stage /tmp
python scripts/health_check.py --component disk
```

**Fix:**

```bash
# Clean up old MS files (> 30 days)
find /data/dsa110-contimg/ms -name "*.ms" -mtime +30 -exec rm -rf {} \;

# Clean up CASA temp files
rm -rf /stage/dsa110-contimg/tmp/casapy-*
rm -rf /tmp/casapy-*

# Clean up old images (keep recent)
find /data/dsa110-contimg/images -name "*.fits" -mtime +30 -delete

# Truncate large log files
truncate -s 0 /data/dsa110-contimg/state/logs/*.log
```

### Permission Denied

**Symptoms:**

- `PermissionError: [Errno 13] Permission denied`
- Cannot write to data directories
- Cannot read configuration files

**Diagnosis:**

```bash
ls -la /data/dsa110-contimg/
python scripts/health_check.py --component filesystem
```

**Fix:**

```bash
# Fix ownership (run as root)
sudo chown -R ubuntu:ubuntu /data/dsa110-contimg/
sudo chmod -R 755 /data/dsa110-contimg/state/
sudo chmod -R 755 /data/dsa110-contimg/ms/
```

### Missing Directories

**Symptoms:**

- `FileNotFoundError: [Errno 2] No such file or directory`
- Pipeline stages fail at startup

**Fix:**

```bash
# Create required directories
mkdir -p /data/dsa110-contimg/{state,ms,images,mosaics,caltables,logs}
mkdir -p /stage/dsa110-contimg/{tmp,ms}
```

## Data Validation Issues

### NaN/Inf Values

**Symptoms:**

- `ValueError: Input contains NaN`
- Fitting operations fail
- Photometry returns invalid results

**Diagnosis:**

```python
import numpy as np
from astropy.io import fits

with fits.open('problem_image.fits') as hdu:
    data = hdu[0].data
    print(f"NaN count: {np.sum(np.isnan(data))}")
    print(f"Inf count: {np.sum(np.isinf(data))}")
```

**Fix:**

- NaN/Inf values are typically indicators of upstream issues
- Check the imaging log for RFI flagging or calibration issues
- Rerun calibration with stricter flagging
- Check the input MS for data quality

### Shape Mismatches

**Symptoms:**

- `ValueError: shapes do not match`
- Array dimension errors in photometry/fitting

**Diagnosis:**

```python
# Check image dimensions
from astropy.io import fits
with fits.open('image.fits') as hdu:
    print(f"Shape: {hdu[0].data.shape}")
```

**Resolution:**

- Ensure consistent image sizes across pipeline
- Check if mask dimensions match image dimensions
- Review imaging parameters (imsize, cell)

### Pipeline Config Errors

**Symptoms:**

- `KeyError: 'old_parameter_name'`
- Configuration parsing failures

**Fix:**

- Check for deprecated parameter names
- Update configuration files to new schema
- Common renames:
  - `spw` :arrow_right: `spectral_windows`
  - `refant` :arrow_right: `reference_antenna`

## Parallel Processing Issues

### Worker Failures

**Symptoms:**

- `A subband writer process failed`
- Incomplete conversions
- Missing subbands

**Diagnosis:**

```bash
# Check system logs for OOM kills
dmesg | grep -i "killed process"

# Check worker logs
tail -100 /data/dsa110-contimg/state/logs/conversion.log
```

**Fix:**

```bash
# Reduce parallelism
export CONTIMG_MAX_WORKERS=2  # Default is 4

# Increase memory limits (if using container)
# Or reduce batch size
```

### Stale Processes

**Symptoms:**

- Resources locked by dead processes
- Worker processes orphaned

**Diagnosis:**

```bash
# Find stuck python processes
ps aux | grep python | grep dsa110

# Check for zombie processes
ps aux | grep -E "Z|defunct"
```

**Fix:**

```bash
# Kill stuck processes
pkill -f "streaming_converter"
pkill -f "worker_loop"

# Clear stale locks
python scripts/fix_schemas.py --clear-locks
```

## Docker/Container Issues

### Volume Mount Issues

**Symptoms:**

- Imaging hangs indefinitely
- File operations very slow
- `Permission denied` in containers

**Diagnosis:**

```bash
docker logs dsa110-imaging 2>&1 | tail -100
docker inspect dsa110-imaging | jq '.[0].Mounts'
```

**Fix:**

```bash
# Ensure correct volume permissions
docker run --user $(id -u):$(id -g) ...

# Check SELinux (if applicable)
sudo setenforce 0  # Temporarily disable

# Verify mount options
docker run -v /data/dsa110-contimg:/data/dsa110-contimg:rw ...
```

### Container Resource Limits

**Symptoms:**

- Container exits unexpectedly
- OOMKilled status

**Diagnosis:**

```bash
docker inspect dsa110-imaging | jq '.[0].State'
docker stats dsa110-imaging
```

**Fix:**

```bash
# Increase memory limit
docker run --memory=32g ...

# Or in docker-compose.yml
# services:
#   imaging:
#     deploy:
#       resources:
#         limits:
#           memory: 32G
```

## Service Issues

### API Not Responding

**Symptoms:**

- `Connection refused` on port 8000
- Health check failing

**Diagnosis:**

```bash
systemctl status dsa110-api
curl -v http://localhost:8000/api/health
```

**Fix:**

```bash
# Restart the service
sudo systemctl restart dsa110-api

# Check logs
journalctl -u dsa110-api -n 100

# Check port availability
sudo lsof -i :8000
```

### Redis Connection Failed

**Symptoms:**

- Caching not working
- `ConnectionRefusedError: Redis`

**Diagnosis:**

```bash
systemctl status redis-server
redis-cli ping
```

**Fix:**

```bash
sudo systemctl restart redis-server
```

### Prometheus Metrics Missing

**Symptoms:**

- Grafana dashboards empty
- `/metrics` endpoint not responding

**Diagnosis:**

```bash
curl http://localhost:8000/metrics
systemctl status prometheus
```

**Fix:**

```bash
sudo systemctl restart prometheus
# Check scrape config
cat /etc/prometheus/prometheus.yml
```

## Recovery Procedures

### Full System Recovery

If the system is in an unknown state:

```bash
#!/bin/bash
set -e

echo "=== DSA-110 Pipeline Recovery ==="

# 1. Stop services
sudo systemctl stop dsa110-api prometheus grafana-simple

# 2. Clear stale locks
python scripts/fix_schemas.py --clear-locks

# 3. Fix database schemas
python scripts/fix_schemas.py --fix

# 4. Checkpoint databases
for db in /data/dsa110-contimg/state/*.sqlite3; do
    echo "Checkpointing $db..."
    sqlite3 "$db" "PRAGMA wal_checkpoint(TRUNCATE);" 2>/dev/null || true
done

# 5. Clear temp files
rm -rf /stage/dsa110-contimg/tmp/*
rm -rf /tmp/casapy-*

# 6. Restart services
sudo systemctl start redis-server
sudo systemctl start dsa110-api
sudo systemctl start prometheus grafana-simple

# 7. Verify health
sleep 5
curl -s http://localhost:8000/api/health?detailed=true | python -m json.tool

echo "=== Recovery Complete ==="
```

### Database Backup/Restore

```bash
# Backup
sqlite3 /data/dsa110-contimg/state/products.sqlite3 ".backup /backup/products_$(date +%Y%m%d).sqlite3"

# Restore
sqlite3 /data/dsa110-contimg/state/products.sqlite3 ".restore /backup/products_20251129.sqlite3"
```

## Monitoring

### Set Up Alerts

Add these alert rules to Prometheus:

```yaml
# /etc/prometheus/alert.rules.yml
groups:
  - name: dsa110_alerts
    rules:
      - alert: DiskSpaceLow
        expr:
          node_filesystem_avail_bytes{mountpoint="/data"} /
          node_filesystem_size_bytes < 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Low disk space on /data"

      - alert: APIDown
        expr: up{job="dsa110-api"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "DSA-110 API is down"
```

### Log Locations

| Component  | Log Location                                     |
| ---------- | ------------------------------------------------ |
| API        | `/data/dsa110-contimg/state/logs/api.log`        |
| Conversion | `/data/dsa110-contimg/state/logs/conversion.log` |
| Imaging    | `/data/dsa110-contimg/state/logs/imaging.log`    |
| Systemd    | `journalctl -u dsa110-api`                       |

## Contact

For issues not covered here, check:

1. GitHub Issues: https://github.com/dsa110/dsa110-contimg/issues
2. Pipeline logs in `/data/dsa110-contimg/state/logs/`
3. System metrics in Grafana: http://localhost:3030
