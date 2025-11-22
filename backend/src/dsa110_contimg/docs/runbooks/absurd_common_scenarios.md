# Absurd Pipeline Runbooks - Common Scenarios

## Table of Contents

1. [Service Startup](#service-startup)
2. [Service Shutdown](#service-shutdown)
3. [Worker Scaling](#worker-scaling)
4. [Handling Failed Tasks](#handling-failed-tasks)
5. [Queue Backup/Overflow](#queue-backupoverflow)
6. [Database Issues](#database-issues)
7. [Disk Space Emergency](#disk-space-emergency)
8. [Worker Stuck/Hung](#worker-stuckhung)
9. [Data Ingestion Start](#data-ingestion-start)
10. [System Upgrade/Maintenance](#system-upgrademaintenance)

---

## Service Startup

### Scenario

Starting the Absurd pipeline from a stopped state.

### Prerequisites

- PostgreSQL database running
- Database schema applied
- Queue created

### Procedure

```bash
# 1. Check database connectivity
export PGPASSWORD="password"
psql -h localhost -U user -d dsa110_absurd -c "SELECT 1;"

# 2. Start daemon
sudo systemctl start dsa110-mosaic-daemon

# 3. Verify daemon started
sudo systemctl status dsa110-mosaic-daemon
sudo journalctl -u dsa110-mosaic-daemon -n 20

# 4. Start workers (adjust count as needed)
sudo systemctl start dsa110-absurd-worker@{1..4}

# 5. Verify workers
systemctl list-units 'dsa110-absurd-worker@*'

# 6. Monitor startup
cd /data/dsa110-contimg/src/dsa110_contimg
./scripts/absurd/monitor_absurd.sh
```

### Expected Result

- Daemon shows "Checking for next group..."
- Workers show "Polling for tasks on queue dsa110-pipeline"
- No critical errors in logs

### Troubleshooting

- **Database connection failed**: Check PostgreSQL container is running
- **Worker import errors**: Verify PYTHONPATH in service files
- **Daemon file not found**: Check WorkingDirectory in service file

---

## Service Shutdown

### Scenario

Gracefully stopping the pipeline for maintenance.

### Procedure

```bash
# 1. Stop daemon (prevents new tasks from being spawned)
sudo systemctl stop dsa110-mosaic-daemon

# 2. Wait for running tasks to complete (optional)
watch 'psql -h localhost -U user -d dsa110_absurd -t -c \
  "SELECT COUNT(*) FROM absurd.t_tasks WHERE status='\''claimed'\'';"'

# 3. Stop workers
sudo systemctl stop 'dsa110-absurd-worker@*'

# 4. Verify all stopped
systemctl list-units 'dsa110-absurd-*' 'dsa110-mosaic-*'
```

### Expected Result

- All services show "inactive (dead)"
- Tasks in claimed state become pending (will be retried on restart)

### Notes

- In-flight tasks are returned to pending after timeout
- Completed tasks remain in completed state
- Data on disk is preserved

---

## Worker Scaling

### Scenario A: Scale Up (Add Workers)

#### When to Scale Up

- Queue depth > 20 pending tasks
- High data ingestion rate
- Long-running tasks

#### Procedure

```bash
# Add workers 5-8
sudo systemctl start dsa110-absurd-worker@{5..8}

# Verify
systemctl list-units 'dsa110-absurd-worker@*'

# Monitor load
htop  # Watch CPU usage
```

### Scenario B: Scale Down (Remove Workers)

#### When to Scale Down

- Queue consistently empty
- Low data rate
- Resource constraints

#### Procedure

```bash
# Stop workers 5-8
sudo systemctl stop dsa110-absurd-worker@{5..8}

# Verify
systemctl list-units 'dsa110-absurd-worker@*' --state=active
```

### Optimal Worker Count

- **Light load**: 1-2 workers
- **Normal ops**: 4 workers
- **High throughput**: 8+ workers
- **Rule of thumb**: 1 worker per 2 CPU cores for I/O-bound tasks

---

## Handling Failed Tasks

### Scenario

Tasks are failing and need investigation.

### Diagnosis

```bash
# 1. View failed tasks
export PGPASSWORD="password"
psql -h localhost -U user -d dsa110_absurd -c "
  SELECT task_id, task_name, error, created_at
  FROM absurd.t_tasks
  WHERE status = 'failed'
  ORDER BY created_at DESC
  LIMIT 10;
"

# 2. View detailed error for specific task
psql -h localhost -U user -d dsa110_absurd -c "
  SELECT task_id, task_name, params, error, retry_count
  FROM absurd.t_tasks
  WHERE task_id = 'TASK_ID_HERE';
"

# 3. Check worker logs for stack traces
sudo journalctl -u 'dsa110-absurd-worker@*' --since "1 hour ago" | grep -A 20 "ERROR"
```

### Common Failure Causes & Solutions

#### 1. Missing Input Files

**Error**: `FileNotFoundError: /path/to/file.uvh5`  
**Solution**: Verify data in `/data/incoming/`, check file permissions

#### 2. Calibrator Not Found

**Error**: `No calibrator registered for Dec`  
**Solution**: Add calibrator to registry:

```bash
cd /data/dsa110-contimg
python -m dsa110_contimg.calibration.register_calibrator \
  --name "3C286" --ra 202.78 --dec 30.51
```

#### 3. Disk Full

**Error**: `OSError: [Errno 28] No space left on device`  
**Solution**: See [Disk Space Emergency](#disk-space-emergency)

#### 4. CASA Errors

**Error**: `SEVERE msmetadata_cmpt.cc::open Exception Reported`  
**Solution**: Check MS file integrity, verify CASA environment

### Retry Failed Tasks

```bash
# Mark failed tasks as pending for retry
psql -h localhost -U user -d dsa110_absurd -c "
  UPDATE absurd.t_tasks
  SET status = 'pending', error = NULL, claimed_at = NULL, worker_id = NULL
  WHERE status = 'failed' AND task_name = 'TASK_NAME_HERE';
"
```

---

## Queue Backup/Overflow

### Scenario

Queue depth is growing faster than workers can process.

### Diagnosis

```bash
# Check queue depth
psql -h localhost -U user -d dsa110_absurd -c "
  SELECT status, COUNT(*)
  FROM absurd.t_tasks
  GROUP BY status;
"

# Monitor rate
watch -n 5 'psql -h localhost -U user -d dsa110_absurd -t -c \
  "SELECT COUNT(*) FROM absurd.t_tasks WHERE status='\''pending'\'';"'
```

### Solutions

#### 1. Scale Up Workers

```bash
sudo systemctl start dsa110-absurd-worker@{5..12}
```

#### 2. Prioritize Critical Tasks

```sql
UPDATE absurd.t_tasks
SET priority = 100
WHERE task_name = 'calibration-solve' AND status = 'pending';
```

#### 3. Pause Data Ingestion

```bash
# Stop daemon temporarily
sudo systemctl stop dsa110-mosaic-daemon

# Let workers drain queue
# Restart when queue < 20
sudo systemctl start dsa110-mosaic-daemon
```

#### 4. Cancel Low-Priority Tasks (Last Resort)

```sql
UPDATE absurd.t_tasks
SET status = 'cancelled'
WHERE task_name = 'validation' AND status = 'pending';
```

---

## Database Issues

### Scenario A: Cannot Connect to Database

#### Symptoms

- Workers log "Unable to connect"
- Daemon cannot spawn tasks

#### Diagnosis & Fix

```bash
# 1. Check PostgreSQL container
docker ps | grep langwatch

# 2. If not running, start it
docker start CONTAINER_ID

# 3. Test connection
psql -h localhost -U user -d dsa110_absurd -c "SELECT 1;"

# 4. Restart services
sudo systemctl restart dsa110-absurd-worker@* dsa110-mosaic-daemon
```

### Scenario B: Database Performance Degradation

#### Symptoms

- Slow task claiming
- High database CPU

#### Fix

```bash
# Run VACUUM ANALYZE
psql -h localhost -U user -d dsa110_absurd -c "VACUUM ANALYZE;"

# Check connection count
psql -h localhost -U user -d dsa110_absurd -c "
  SELECT count(*) FROM pg_stat_activity;
"

# If too many connections, reduce worker pool size
# Edit service file: pool_max_size=5
```

---

## Disk Space Emergency

### Scenario

Disk usage > 95%, system cannot write new data.

### Immediate Actions

```bash
# 1. Check usage
df -h /data /stage

# 2. Stop data ingestion
sudo systemctl stop dsa110-mosaic-daemon

# 3. Find large files
du -sh /stage/dsa110-contimg/* | sort -rh | head -10

# 4. Archive or delete old data
# CAUTION: Verify files are backed up!

# Archive old mosaics (older than 30 days)
find /stage/dsa110-contimg/mosaics -name "*.fits" -mtime +30 -exec tar -czf /backup/mosaics_archive.tar.gz {} +
find /stage/dsa110-contimg/mosaics -name "*.fits" -mtime +30 -delete

# Delete intermediate MS files (if images exist)
find /stage/dsa110-contimg/raw/ms -name "*.ms" -mtime +7 -exec rm -rf {} +

# 5. Clean up temp files
rm -rf /dev/shm/casa_*
rm -rf /tmp/absurd_*

# 6. Restart ingestion
sudo systemctl start dsa110-mosaic-daemon
```

### Prevention

```bash
# Set up daily cleanup cron job
crontab -e

# Add:
0 2 * * * /data/dsa110-contimg/scripts/cleanup_old_data.sh >> /var/log/cleanup.log 2>&1
```

---

## Worker Stuck/Hung

### Scenario

Worker has claimed a task but is not making progress.

### Diagnosis

```bash
# 1. Find stuck tasks
psql -h localhost -U user -d dsa110_absurd -c "
  SELECT task_id, task_name, worker_id, claimed_at, last_heartbeat
  FROM absurd.t_tasks
  WHERE status = 'claimed'
    AND claimed_at < NOW() - INTERVAL '2 hours'
  ORDER BY claimed_at;
"

# 2. Identify worker
WORKER_ID="worker-id-here"

# 3. Check worker logs
sudo journalctl -u dsa110-absurd-worker@* | grep "$WORKER_ID" | tail -50

# 4. Check if process is actually running
ps aux | grep start_worker.py

# 5. Check system resources
top -u ubuntu
```

### Fix

```bash
# 1. Restart the specific worker
# If worker@1 is stuck:
sudo systemctl restart dsa110-absurd-worker@1

# 2. Task will timeout and be retried by another worker

# 3. If problem persists, check for deadlock
sudo journalctl -u dsa110-absurd-worker@1 -n 200 | grep -i "lock\|hang\|timeout"
```

---

## Data Ingestion Start

### Scenario

Beginning observations, new data arriving.

### Pre-flight Checklist

```bash
# 1. Services running
systemctl is-active dsa110-mosaic-daemon dsa110-absurd-worker@1

# 2. Disk space available
df -h /data /stage | grep -E "9[0-9]%" && echo "WARNING: Disk nearly full"

# 3. Workers available
systemctl list-units 'dsa110-absurd-worker@*' --state=active | wc -l

# 4. Database accessible
psql -h localhost -U user -d dsa110_absurd -c "SELECT 1;"

# 5. Calibrators registered
sqlite3 /data/dsa110-contimg/state/cal_registry.sqlite3 \
  "SELECT name, dec_deg FROM calibrators;"
```

### Start Ingestion

```bash
# 1. Place UVH5 files in incoming directory
# (or start data streaming process)
ls -lh /data/incoming/*.uvh5

# 2. Monitor daemon detecting files
sudo journalctl -u dsa110-mosaic-daemon -f

# 3. Watch tasks being created
watch -n 2 './scripts/absurd/monitor_absurd.sh'

# 4. Monitor first task execution
sudo journalctl -u 'dsa110-absurd-worker@*' -f
```

### Expected Timeline

1. **T+0s**: Files appear in `/data/incoming/`
2. **T+60s**: Daemon detects files, converts to MS
3. **T+5min**: First group forms (10 MS files)
4. **T+6min**: Calibration solve task spawned
5. **T+15min**: Calibration complete, imaging starts
6. **T+30min**: First mosaic complete

---

## System Upgrade/Maintenance

### Scenario

Updating code or performing system maintenance.

### Procedure

```bash
# 1. Notify users (if applicable)
echo "Absurd pipeline maintenance starting" | wall

# 2. Stop services gracefully
sudo systemctl stop dsa110-mosaic-daemon
sleep 30  # Let in-flight tasks finish
sudo systemctl stop 'dsa110-absurd-worker@*'

# 3. Backup database
pg_dump -h localhost -U user dsa110_absurd > /backup/absurd_db_$(date +%Y%m%d).sql

# 4. Backup state databases
cp /data/dsa110-contimg/state/*.sqlite3 /backup/

# 5. Perform updates
cd /data/dsa110-contimg
git pull origin main
# or: install new package, etc.

# 6. Reload systemd (if service files changed)
sudo systemctl daemon-reload

# 7. Test in dry-run mode (if available)
# python scripts/test_pipeline.py --dry-run

# 8. Restart services
sudo systemctl start dsa110-mosaic-daemon
sudo systemctl start dsa110-absurd-worker@{1..4}

# 9. Verify startup
./scripts/absurd/monitor_absurd.sh

# 10. Monitor for 10 minutes
sudo journalctl -u 'dsa110-absurd-*' -u dsa110-mosaic-daemon -f
```

### Rollback Procedure (if issues occur)

```bash
# 1. Stop services
sudo systemctl stop dsa110-mosaic-daemon 'dsa110-absurd-worker@*'

# 2. Revert code
cd /data/dsa110-contimg
git reset --hard PREVIOUS_COMMIT_HASH

# 3. Restore database (if changed)
psql -h localhost -U user dsa110_absurd < /backup/absurd_db_YYYYMMDD.sql

# 4. Restart services
sudo systemctl start dsa110-mosaic-daemon dsa110-absurd-worker@{1..4}
```

---

## Quick Reference

### Status Checks

```bash
# One-line status
./scripts/absurd/monitor_absurd.sh | head -20

# Service status
systemctl status dsa110-mosaic-daemon dsa110-absurd-worker@1

# Queue depth
psql -h localhost -U user -d dsa110_absurd -t -c \
  "SELECT COUNT(*) FROM absurd.t_tasks WHERE status='pending';"
```

### Common Commands

```bash
# Restart everything
sudo systemctl restart dsa110-mosaic-daemon 'dsa110-absurd-worker@*'

# View logs
sudo journalctl -u 'dsa110-absurd-*' -u dsa110-mosaic-daemon -f

# Check disk
df -h /data /stage

# Database query
psql -h localhost -U user -d dsa110_absurd
```

### Emergency Contacts

- Pipeline Team: [contact-info]
- On-Call: [pager-number]
- Documentation: `/data/dsa110-contimg/docs/operations/`

---

**Version**: 1.0  
**Last Updated**: 2025-11-19  
**Maintainer**: DSA-110 Pipeline Team
