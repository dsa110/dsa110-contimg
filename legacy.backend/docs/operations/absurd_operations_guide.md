# Absurd Pipeline Operations Guide

> **:warning_sign::variation_selector-16: CONSOLIDATION NOTICE:** The canonical Absurd operations documentation is
> at
> [`docs/operations/absurd_operations.md`](/data/dsa110-contimg/docs/operations/absurd_operations.md).
> This file in `backend/docs/` provides supplementary context and may be merged
> or archived in a future documentation cleanup.

## Overview

The DSA-110 continuum imaging pipeline now uses **Absurd**, a durable task queue
system, for fault-tolerant distributed processing. This guide covers operational
procedures for production use.

## Architecture

```text
┌─────────────────┐
│  UVH5 Data      │
│  /data/incoming │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Mosaic Daemon                  │
│  (AbsurdStreamingMosaicManager) │
│  - Detects new data groups      │
│  - Spawns tasks to queue        │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  PostgreSQL Queue               │
│  dsa110_absurd database         │
│  - Task persistence             │
│  - State management             │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Worker Pool (1-N instances)    │
│  - Claim tasks                  │
│  - Execute pipeline stages      │
│  - Report results               │
└─────────────────────────────────┘
```

## Services

### 1. `dsa110-mosaic-daemon.service`

**Producer/Orchestrator**

- Monitors for new observation groups
- Submits tasks to Absurd queue
- Waits for completion asynchronously
- Handles errors and retries

### 2. `dsa110-absurd-worker@N.service`

**Consumer/Executor**

- Polls queue for pending tasks
- Executes pipeline stages (conversion, calibration, imaging, etc.)
- Writes results to shared storage
- Updates task status in database

## Quick Start

### Check System Status

```bash
# Run the monitoring dashboard
cd /data/dsa110-contimg/src/dsa110_contimg
./scripts/absurd/monitor_absurd.sh
```

### Start Services

```bash
# Start the orchestrator
sudo systemctl start dsa110-mosaic-daemon

# Start worker(s)
sudo systemctl start dsa110-absurd-worker@1

# Scale to 4 workers
sudo systemctl start dsa110-absurd-worker@{2..4}
```

### Monitor Live Logs

```bash
# Watch worker logs
sudo journalctl -u dsa110-absurd-worker@1 -f

# Watch daemon logs
sudo journalctl -u dsa110-mosaic-daemon -f

# Watch all Absurd services
sudo journalctl -u 'dsa110-absurd-*' -u dsa110-mosaic-daemon -f
```

## Data Ingestion

### Input Data Location

The pipeline expects UVH5/HDF5 files in:

```
/data/incoming/
```

### Supported Formats

- `.uvh5` - UVH5 format (preferred)
- `.hdf5` - HDF5 format

### Ingestion Process

1. **Place files** in `/data/incoming/`
2. **Daemon detects** new files automatically (60-second poll interval)
3. **Groups formed** when sufficient files available (10 MS per group with
   sliding window)
4. **Tasks spawned** to worker queue
5. **Workers execute** pipeline stages in parallel
6. **Results written** to `/stage/dsa110-contimg/`

### Directory Structure

```
/data/incoming/               # Input UVH5 files
/stage/dsa110-contimg/
  ├── raw/ms/                 # Converted Measurement Sets
  │   ├── science/YYYY-MM-DD/
  │   └── calibrators/YYYY-MM-DD/
  ├── images/                 # Individual field images
  └── mosaics/                # Combined mosaic images
```

## Operations

### Scaling Workers

Add more workers for increased throughput:

```bash
# Start workers 2-8
sudo systemctl start dsa110-absurd-worker@{2..8}

# Check worker status
systemctl list-units 'dsa110-absurd-worker@*'
```

**Recommended scaling:**

- **1-2 workers**: Light processing, testing
- **4 workers**: Normal operations
- **8+ workers**: High-throughput mode

### Restart Services

```bash
# Restart orchestrator
sudo systemctl restart dsa110-mosaic-daemon

# Restart specific worker
sudo systemctl restart dsa110-absurd-worker@1

# Restart all workers
sudo systemctl restart 'dsa110-absurd-worker@*'
```

### Stop Services

```bash
# Stop orchestrator (stops spawning new tasks)
sudo systemctl stop dsa110-mosaic-daemon

# Stop all workers (in-flight tasks will be requeued)
sudo systemctl stop 'dsa110-absurd-worker@*'
```

### View Task Queue

Query the database directly:

```bash
export PGPASSWORD="password"

# Task statistics
psql -h localhost -U user -d dsa110_absurd -c "
  SELECT status, COUNT(*)
  FROM absurd.t_tasks
  GROUP BY status;
"

# Recent tasks
psql -h localhost -U user -d dsa110_absurd -c "
  SELECT task_id, task_name, status, created_at
  FROM absurd.t_tasks
  ORDER BY created_at DESC
  LIMIT 20;
"

# Failed tasks
psql -h localhost -U user -d dsa110_absurd -c "
  SELECT task_id, task_name, error, created_at
  FROM absurd.t_tasks
  WHERE status = 'failed'
  ORDER BY created_at DESC;
"
```

## Troubleshooting

### Worker Not Processing Tasks

**Symptom:** Tasks stuck in `pending` status

**Check:**

1. Is the worker running? `systemctl status dsa110-absurd-worker@1`
2. Can worker connect to DB? Check logs for connection errors
3. Are there import errors? Check `PYTHONPATH` in service file

**Fix:**

```bash
# Restart worker
sudo systemctl restart dsa110-absurd-worker@1

# Check detailed logs
sudo journalctl -u dsa110-absurd-worker@1 -n 100
```

### Daemon Not Creating Groups

**Symptom:** No tasks being spawned

**Check:**

1. Are there MS files in the database?
   `sqlite3 /data/dsa110-contimg/state/products.sqlite3 "SELECT COUNT(*) FROM ms_index;"`
2. Do the MS files exist on disk?
3. Is the daemon running? `systemctl status dsa110-mosaic-daemon`

**Fix:**

```bash
# Check daemon logs for errors
sudo journalctl -u dsa110-mosaic-daemon -n 50

# Restart daemon
sudo systemctl restart dsa110-mosaic-daemon
```

### Tasks Failing

**Symptom:** Tasks marked as `failed` in queue

**Check:**

1. View error in database:
   `psql ... -c "SELECT error FROM absurd.t_tasks WHERE status='failed';"`
2. Check worker logs: `sudo journalctl -u dsa110-absurd-worker@1 -n 100`
3. Verify environment variables in worker service

**Common Causes:**

- Missing `PIPELINE_INPUT_DIR` or `PIPELINE_OUTPUT_DIR`
- Incorrect `PYTHONPATH`
- Missing calibrator registration
- Disk full

### Database Issues

**Symptom:** "Unable to connect to database"

**Check:**

```bash
# Verify PostgreSQL container
docker ps | grep langwatch

# Test connection
psql -h localhost -U user -d dsa110_absurd -c "SELECT 1;"
```

### Disk Space

Monitor disk usage:

```bash
# Check space
df -h /data /stage

# Clean up old files if needed
# (Be careful! Verify files are backed up first)
```

## Configuration

### Environment Variables

Defined in service files:

**Worker (`dsa110-absurd-worker@.service`):**

- `ABSURD_DATABASE_URL`: PostgreSQL connection string
- `ABSURD_QUEUE_NAME`: Queue to poll (`dsa110-pipeline`)
- `PYTHONPATH`: Python module path
- `PIPELINE_INPUT_DIR`: Input data directory
- `PIPELINE_OUTPUT_DIR`: Output data directory

**Daemon (`dsa110-mosaic-daemon.service`):**

- Same as worker, plus:
- `PIPELINE_PRODUCTS_DB`: Products database path
- `CAL_REGISTRY_DB`: Calibration registry path
- `CONTIMG_OUTPUT_DIR`: MS output directory
- `CONTIMG_IMAGES_DIR`: Images output directory
- `CONTIMG_MOSAIC_DIR`: Mosaics output directory

### Modifying Configuration

1. Edit service file:

   ```bash
   sudo nano /etc/systemd/system/dsa110-absurd-worker@.service
   ```

2. Reload and restart:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart dsa110-absurd-worker@1
   ```

## Performance Tuning

### Worker Count

- **CPU-bound tasks**: Set workers = number of CPU cores
- **I/O-bound tasks**: Can exceed CPU count (1.5x - 2x cores)
- Monitor system load with `htop` or `top`

### Database Connection Pool

Edit `AbsurdConfig` in code to adjust:

- `pool_min_size`: Minimum connections (default: 2)
- `pool_max_size`: Maximum connections (default: 10)

### Task Timeout

Default: 3600 seconds (1 hour)

Adjust in service file:

```ini
Environment="ABSURD_TASK_TIMEOUT=7200"
```

## Maintenance

### Regular Tasks

**Daily:**

- Check monitoring dashboard
- Verify services are running
- Review failed tasks

**Weekly:**

- Clean up old log files
- Archive completed data
- Review disk space

**Monthly:**

- Database maintenance (VACUUM)
- Performance review
- Update documentation

### Database Maintenance

```bash
export PGPASSWORD="password"

# Vacuum database
psql -h localhost -U user -d dsa110_absurd -c "VACUUM ANALYZE;"

# Clean up old completed tasks (optional, keep for audit trail)
psql -h localhost -U user -d dsa110_absurd -c "
  DELETE FROM absurd.t_tasks
  WHERE status = 'completed'
    AND completed_at < NOW() - INTERVAL '30 days';
"
```

## Monitoring and Alerting

### Key Metrics

1. **Task Queue Depth**: Number of pending tasks
2. **Task Success Rate**: Completed / (Completed + Failed)
3. **Worker Utilization**: Active workers / Total workers
4. **Processing Latency**: Time from task creation to completion
5. **Disk Usage**: `/data` and `/stage` utilization

### Monitoring Script

Run periodically:

```bash
watch -n 30 /data/dsa110-contimg/src/dsa110_contimg/scripts/absurd/monitor_absurd.sh
```

### Log Aggregation

Logs are in systemd journal. Export to external system:

```bash
# Export logs to file
journalctl -u 'dsa110-absurd-*' --since today > /tmp/absurd-logs.txt
```

## Emergency Procedures

### Emergency Stop

```bash
# Stop all processing immediately
sudo systemctl stop dsa110-mosaic-daemon
sudo systemctl stop 'dsa110-absurd-worker@*'
```

### Clear Task Queue

**:warning_sign::variation_selector-16: Warning: This will lose all queued work!**

```bash
export PGPASSWORD="password"

# Cancel all pending tasks
psql -h localhost -U user -d dsa110_absurd -c "
  UPDATE absurd.t_tasks
  SET status = 'cancelled'
  WHERE status IN ('pending', 'claimed');
"
```

### Reset System

**:warning_sign::variation_selector-16: Warning: Complete reset!**

```bash
# Stop services
sudo systemctl stop dsa110-mosaic-daemon 'dsa110-absurd-worker@*'

# Clear queue
psql -h localhost -U user -d dsa110_absurd -c "TRUNCATE absurd.t_tasks;"

# Restart services
sudo systemctl start dsa110-mosaic-daemon dsa110-absurd-worker@{1..4}
```

## Support

For issues or questions:

1. Check logs: `sudo journalctl -u 'dsa110-absurd-*' -n 200`
2. Run monitoring script: `./scripts/absurd/monitor_absurd.sh`
3. Review this documentation
4. Contact pipeline team

## References

- [Absurd Architecture](../concepts/absurd_architecture.md)
- [Pipeline Stages](../reference/pipeline_stages.md)
- [Configuration Reference](../reference/configuration.md)
- [Troubleshooting Guide](troubleshooting.md)
