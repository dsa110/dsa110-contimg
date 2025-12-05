# DSA-110 Troubleshooting Guide

**Problem resolution and common issue fixes for the DSA-110 Continuum Imaging Pipeline.**

!!! note "Version"
Last updated: Phase 4 completion (complexity reduction)

---

## Quick Diagnosis

Run the comprehensive health check first:

```bash
# Full health check
python scripts/health_check.py

# JSON output (for monitoring)
python scripts/health_check.py --json

# Check specific component
python scripts/health_check.py --component disk
python scripts/health_check.py --component database
python scripts/health_check.py --component services
```

---

## Known Issues

### Docker WSClean Hang

|              |                                               |
| ------------ | --------------------------------------------- |
| **Severity** | HIGH                                          |
| **Status**   | 🟢 Fixed                                      |
| **Affects**  | NVSS seeding, Docker-based WSClean `-predict` |

**Root Cause:**

The `/data` filesystem is NTFS mounted via FUSE (`ntfs-3g`). When Docker mounts
NTFS-FUSE volumes on kernel 4.15 with the overlay2 storage driver, container
cleanup (`--rm`) hangs waiting for FUSE to release file handles. This is a known
kernel bug fixed in later kernels, but Ubuntu 18.04 is stuck on 4.15.

**Fix Applied:**

Removed `/data:/data` from default Docker volume mounts in `gpu_utils.py`.
WSClean only needs `/stage` (for MS files and images) and `/scratch` (temp files),
both of which are on ext4.

**Symptoms (historical):**

```text
Writing changed model back to /data_ms/2025-10-19T14:31:45.ms:
 0%....10%....20%....30%....40%....50%....60%....70%....80%....90%....100%
Cleaning up temporary files...
[HANGS INDEFINITELY - timeouts don't trigger]
```

**If You Still Experience Hangs:**

1. Ensure MS files are on `/stage`, not `/data`
2. Ensure output images go to `/stage` or `/scratch`
3. If you must access `/data` from Docker, mount it explicitly and accept the risk

---

### Image Metadata Not Populated

|              |                                   |
| ------------ | --------------------------------- |
| **Severity** | HIGH                              |
| **Status**   | 🟢 Fixed                          |
| **Affects**  | Image filtering, database queries |

**Root Cause:**

The `images_insert()` function in `streaming_converter.py` was called with
positional arguments in the wrong order, causing `created_at` timestamp to be
stored in the wrong field position.

**Fix Applied:**

Changed to explicit keyword arguments in `streaming_converter.py`:

```python
# Before (wrong):
images_insert(conn, p, ms_path, now_ts, "5min", pbcor)

# After (correct):
images_insert(conn, p, ms_path, "5min", created_at=now_ts, pbcor=pbcor)
```

**Impact (historical):**

- `noise_jy`, `center_ra_deg`, `center_dec_deg` were set to NULL
- Noise filtering returned no results
- Declination filtering required reading FITS files (slow)

---

## Database Issues

### Schema Mismatches / Missing Columns

**Symptoms:**

```
sqlite3.OperationalError: no such column: X
```

**Diagnosis:**

```bash
python scripts/fix_schemas.py --verbose
```

**Fix:**

```bash
python scripts/fix_schemas.py --fix
```

---

### Database Locked

**Symptoms:**

```
sqlite3.OperationalError: database is locked
```

**Diagnosis:**

```bash
# Check for lock files
ls -la /data/dsa110-contimg/state/*.lock

# Check processes holding database
lsof /data/dsa110-contimg/state/db/pipeline.sqlite3
```

**Fix:**

```bash
# Clear stale locks
python scripts/fix_schemas.py --clear-locks

# Force WAL checkpoint
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 "PRAGMA wal_checkpoint(TRUNCATE);"
```

---

### Large WAL Files

**Symptoms:**

- `.sqlite3-wal` files > 100MB
- Slow database operations

**Fix:**

```bash
# Checkpoint WAL
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 "PRAGMA wal_checkpoint(TRUNCATE);"
```

---

## Filesystem Issues

### Disk Space Exhaustion

**Symptoms:**

```
OSError: [Errno 28] No space left on device
```

**Diagnosis:**

```bash
df -h /data /stage /tmp
```

**Fix:**

```bash
# Clean old MS files (> 30 days)
find /data/dsa110-contimg/ms -name "*.ms" -mtime +30 -exec rm -rf {} \;

# Clean CASA temp files
rm -rf /stage/dsa110-contimg/tmp/casapy-*
rm -rf /tmp/casapy-*

# Truncate large log files
truncate -s 0 /data/dsa110-contimg/state/logs/*.log
```

---

### Permission Denied

**Symptoms:**

```
PermissionError: [Errno 13] Permission denied
```

**Fix:**

```bash
# Fix ownership
sudo chown -R ubuntu:ubuntu /data/dsa110-contimg/
sudo chmod -R 755 /data/dsa110-contimg/state/
```

---

### Missing Directories

**Fix:**

```bash
mkdir -p /data/dsa110-contimg/{state,ms,images,mosaics,caltables,logs}
mkdir -p /data/dsa110-contimg/state/db
mkdir -p /stage/dsa110-contimg/{tmp,ms}
```

---

## Service Issues

### Streaming Converter Not Running

**Diagnosis:**

```bash
# Check systemd status
sudo systemctl status contimg-stream.service

# View logs
journalctl -u contimg-stream -f --since "1 hour ago"
```

**Fix:**

```bash
# Restart service
sudo systemctl restart contimg-stream.service

# Check configuration
cat /data/dsa110-contimg/ops/systemd/contimg.env
```

---

### API Server Errors

**Diagnosis:**

```bash
# Check health endpoint
curl http://localhost:8000/api/status

# View API logs
tail -f /data/dsa110-contimg/state/logs/api.log
```

**Fix:**

```bash
# Restart API service
sudo systemctl restart contimg-api.service

# Or manually
cd /data/dsa110-contimg/backend
conda activate casa6
uvicorn dsa110_contimg.api.app:app --reload --port 8000
```

---

### Dashboard Not Loading

**Diagnosis:**

```bash
# Check frontend process
ps aux | grep npm

# Check port
lsof -i :3210
```

**Fix:**

```bash
# Restart frontend
cd /data/dsa110-contimg/frontend
npm run dev:unsafe
```

---

## Pipeline Issues

### Incomplete Subband Groups

**Symptoms:**

- Less than 16 subbands found for a group
- Groups stuck in "collecting" state

**Diagnosis:**

```bash
# Check queue state
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
  "SELECT group_id, state, subband_count FROM ingest_queue WHERE state='collecting';"
```

**Fix:**

```bash
# Force process incomplete groups (if files are missing permanently)
python -m dsa110_contimg.conversion.cli force-process --group-id "2025-01-15T12:30:00"

# Or wait for timeout (default: 5 minutes)
```

---

### Conversion Failures

**Symptoms:**

```
ConversionError: Failed to convert group
```

**Diagnosis:**

```bash
# Check conversion logs
tail -f /data/dsa110-contimg/state/logs/conversion.log

# Check input files
ls -la /data/incoming/2025-01-15T12:30:00_sb*.hdf5
```

**Common Causes:**

| Cause             | Solution                          |
| ----------------- | --------------------------------- |
| Corrupt UVH5 file | Check file integrity, re-download |
| Memory exhaustion | Reduce batch size, increase RAM   |
| Disk full         | Clean temp files, expand storage  |

---

### Calibration Failures

**Symptoms:**

```
CalibrationError: Failed to solve calibration
```

**Diagnosis:**

```bash
# Check caltable existence
ls -la /data/dsa110-contimg/caltables/

# View calibration logs
tail -f /data/dsa110-contimg/state/logs/calibration.log
```

**Common Causes:**

| Cause                | Solution                                   |
| -------------------- | ------------------------------------------ |
| No calibrator in FOV | Check transit time, use different MS       |
| Too much RFI         | Increase flagging, use different timerange |
| Insufficient SNR     | Use longer integration                     |

---

### Imaging Failures

**Symptoms:**

```
ImagingError: WSClean failed with exit code 1
```

**Diagnosis:**

```bash
# Check WSClean output
tail -f /data/dsa110-contimg/state/logs/imaging.log

# Check MS validity
python -c "from casacore.tables import table; t = table('problem.ms'); print(t.nrows())"
```

**Common Causes:**

| Cause             | Solution                             |
| ----------------- | ------------------------------------ |
| Memory exhaustion | Reduce image size, use gridding      |
| Bad data          | Rerun calibration, increase flagging |
| WSClean version   | Check WSClean installation           |

---

## Testing Issues

### Tests Hang or Timeout

**Symptoms:**

- Tests don't complete
- pytest hangs after tests pass

**Diagnosis:**

```bash
# Run with verbose output
python -m pytest tests/contract/ -v --tb=short -x
```

**Fix:**

```bash
# Use casa6's pytest explicitly
conda activate casa6
python -m pytest tests/ -v

# NOT this (may use system pytest):
pytest tests/ -v
```

---

### CASA C++ Shutdown Error (Resolved)

**Symptoms:**

```
casatools::get_state() called after shutdown initiated
```

**Solution:** This is handled automatically. Tests use `os._exit(0)` to skip Python's shutdown when CASA was imported.

---

## Environment Issues

### Wrong Python Environment

**Symptoms:**

- Import errors for `casatools` or `pyuvdata`
- Version mismatches

**Diagnosis:**

```bash
which python
python --version
conda info --envs
```

**Fix:**

```bash
# Always activate casa6 first
conda activate casa6

# Verify
python -c "import casatools; print('OK')"
```

---

### Module Not Found

**Symptoms:**

```
ModuleNotFoundError: No module named 'dsa110_contimg'
```

**Fix:**

```bash
# Install in development mode
cd /data/dsa110-contimg/backend
conda activate casa6
pip install -e .

# Or set PYTHONPATH
export PYTHONPATH=/data/dsa110-contimg/backend/src:$PYTHONPATH
```

---

## Performance Issues

### Slow Conversion

**Diagnosis:**

```bash
# Check performance metrics
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
  "SELECT group_id, total_time, load_time, write_time FROM performance_metrics ORDER BY recorded_at DESC LIMIT 10;"
```

**Optimizations:**

- Use tmpfs staging (`/dev/shm/`)
- Reduce batch size
- Use NVMe scratch space (`/scratch/`)

---

### Slow API Responses

**Diagnosis:**

```bash
# Time API calls
time curl http://localhost:8000/api/v1/images
```

**Optimizations:**

- Check database indexes
- Enable connection pooling
- Use pagination for large results

---

## Logs and Monitoring

### Log Locations

| Log         | Location                                          |
| ----------- | ------------------------------------------------- |
| Pipeline    | `/data/dsa110-contimg/state/logs/pipeline.log`    |
| API         | `/data/dsa110-contimg/state/logs/api.log`         |
| Conversion  | `/data/dsa110-contimg/state/logs/conversion.log`  |
| Calibration | `/data/dsa110-contimg/state/logs/calibration.log` |
| Imaging     | `/data/dsa110-contimg/state/logs/imaging.log`     |
| Systemd     | `journalctl -u contimg-stream`                    |

### Viewing Logs

```bash
# Real-time pipeline logs
tail -f /data/dsa110-contimg/state/logs/pipeline.log

# Filter for errors
grep -i error /data/dsa110-contimg/state/logs/*.log

# Last hour of systemd logs
journalctl -u contimg-stream --since "1 hour ago"
```

---

## Getting Help

1. **Search documentation:**

   ```bash
   python -m dsa110_contimg.docsearch.cli search "your issue"
   ```

2. **Check this guide** for common scenarios

3. **Run health check** for automated diagnosis:

   ```bash
   python scripts/health_check.py
   ```

4. **Review logs** for error messages:
   ```bash
   grep -i "error\|exception\|failed" /data/dsa110-contimg/state/logs/*.log | tail -50
   ```

---

## Exception Reference

### Exception Hierarchy

```
PipelineError (base)
├── SubbandGroupingError
│   └── IncompleteSubbandGroupError
├── ConversionError
│   ├── UVH5ReadError
│   └── MSWriteError
├── DatabaseError
│   ├── DatabaseMigrationError
│   ├── DatabaseConnectionError
│   └── DatabaseLockError
├── CalibrationError
│   ├── CalibrationTableNotFoundError
│   └── CalibratorNotFoundError
├── ImagingError
│   └── ImageNotFoundError
└── ValidationError
    ├── MissingParameterError
    └── InvalidPathError
```

### Recoverable vs Fatal

```python
from dsa110_contimg.utils.exceptions import is_recoverable

if is_recoverable(e):
    logger.warning(f"Recoverable: {e}")
else:
    logger.error(f"Fatal: {e}")
    raise
```

Recoverable errors (automatic retry):

- `DatabaseLockError`
- Network timeouts
- Temporary disk issues

Fatal errors (require intervention):

- `CalibrationTableNotFoundError`
- Schema mismatches
- Corrupt input files

---

## Related Documentation

- **[Quick Start](QUICKSTART.md)**: Initial setup
- **[Storage & Files](guides/storage-and-file-organization.md)**: File organization and database paths
- **[Dashboard Guide](guides/dashboard.md)**: Web interface
- **[Developer Guide](DEVELOPER_GUIDE.md)**: Development
- **[Architecture](ARCHITECTURE.md)**: System design
