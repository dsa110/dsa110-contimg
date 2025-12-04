# DSA-110 Continuum Imaging Pipeline - Operations Runbook

This runbook provides procedures for operating and troubleshooting the DSA-110 continuum imaging pipeline.

## Table of Contents

- [Quick Reference](#quick-reference)
- [Service Management](#service-management)
- [Alert Response Procedures](#alert-response-procedures)
- [Backup and Recovery](#backup-and-recovery)
- [Common Issues](#common-issues)
- [Health Checks](#health-checks)

---

## Quick Reference

### Key Paths

| Path                                             | Description                    |
| ------------------------------------------------ | ------------------------------ |
| `/data/dsa110-contimg/`                          | Source code and state          |
| `/data/dsa110-contimg/state/db/pipeline.sqlite3` | Main pipeline database         |
| `/data/dsa110-contimg/state/logs/`               | Application logs               |
| `/stage/dsa110-contimg/ms/`                      | Output Measurement Sets        |
| `/stage/backups/`                                | Backup storage                 |
| `/data/incoming/`                                | Raw HDF5 files from correlator |

### Service Commands

```bash
# Check status
sudo systemctl status contimg-api contimg-stream

# Restart services
sudo systemctl restart contimg-api
sudo systemctl restart contimg-stream

# View logs
journalctl -u contimg-api -f
journalctl -u contimg-stream -f
```

### API Health Check

```bash
curl -s http://localhost:8000/health | jq .
curl -s http://localhost:8000/metrics
```

---

## Service Management

### Starting Services

```bash
# Activate environment first
conda activate casa6

# Start in order
sudo systemctl start contimg-api
sudo systemctl start contimg-stream
```

### Stopping Services

```bash
# Stop streaming first (graceful shutdown)
sudo systemctl stop contimg-stream
sudo systemctl stop contimg-api
```

### Service Configuration

Configuration via environment file: `/data/dsa110-contimg/ops/env/production.env`

Key variables:

- `PIPELINE_DB` - Database path
- `DSA110_AUTH_DISABLED` - Set `false` in production
- `LOG_LEVEL` - DEBUG, INFO, WARNING, ERROR

---

## Alert Response Procedures

### StaleCalibration

**Severity:** Critical  
**Meaning:** No valid calibration in 24+ hours

**Steps:**

1. Check calibration table registry:

   ```bash
   sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
     "SELECT * FROM calibration_tables ORDER BY created_at DESC LIMIT 5;"
   ```

2. Verify calibrator transits occurred:

   ```bash
   python -m dsa110_contimg.calibration.cli status
   ```

3. Check for failed calibration jobs:

   ```bash
   sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
     "SELECT * FROM ingest_queue WHERE state='failed' AND processing_stage='calibration';"
   ```

4. Manually trigger calibration if needed:
   ```bash
   python -m dsa110_contimg.calibration.cli run --calibrator 3C286
   ```

### ConversionQueueBacklog

**Severity:** Warning  
**Meaning:** Queue depth > 100 pending observations

**Steps:**

1. Check current queue status:

   ```bash
   sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
     "SELECT state, COUNT(*) FROM ingest_queue GROUP BY state;"
   ```

2. Check streaming service health:

   ```bash
   sudo systemctl status contimg-stream
   journalctl -u contimg-stream --since "1 hour ago" | grep -i error
   ```

3. Check disk space:

   ```bash
   df -h /data /stage /scratch
   ```

4. If stuck jobs exist, reset them:
   ```bash
   sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
     "UPDATE ingest_queue SET state='pending', retry_count=0
      WHERE state='in_progress' AND updated_at < datetime('now', '-1 hour');"
   ```

### PipelineFailureRate

**Severity:** Critical  
**Meaning:** >10% of pipeline runs failing

**Steps:**

1. Identify failing jobs:

   ```bash
   sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
     "SELECT group_id, error_message, failed_at
      FROM ingest_queue WHERE state='failed'
      ORDER BY failed_at DESC LIMIT 10;"
   ```

2. Check for common patterns:

   - Missing subbands (incomplete observation)
   - I/O errors (disk full or NFS issues)
   - Memory errors (OOM)

3. Review streaming service logs:

   ```bash
   journalctl -u contimg-stream --since "1 hour ago" | grep -E "ERROR|CRITICAL"
   ```

4. Check system resources:
   ```bash
   free -h
   top -b -n1 | head -20
   ```

### DiskSpaceCritical

**Severity:** Critical  
**Meaning:** Disk <15% free on /data or /stage

**Steps:**

1. Identify space usage:

   ```bash
   du -sh /data/incoming/* | sort -rh | head -10
   du -sh /stage/dsa110-contimg/* | sort -rh | head -10
   ```

2. Clean up old MS files (>30 days):

   ```bash
   find /stage/dsa110-contimg/ms -name "*.ms" -mtime +30 -exec rm -rf {} \;
   ```

3. Archive or delete old HDF5 files:

   ```bash
   # List files older than 7 days
   find /data/incoming -name "*.hdf5" -mtime +7 | wc -l
   ```

4. Check backup storage:
   ```bash
   du -sh /stage/backups/*
   ```

### ProcessingStuck

**Severity:** Warning  
**Meaning:** Jobs in-progress with no completions for 30 min

**Steps:**

1. Find stuck jobs:

   ```bash
   sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
     "SELECT group_id, processing_stage, started_at
      FROM ingest_queue WHERE state='in_progress';"
   ```

2. Check if conversion process is running:

   ```bash
   ps aux | grep -E "dsa110_contimg|casapy"
   ```

3. Check for zombie processes:

   ```bash
   ps aux | awk '$8=="Z" {print}'
   ```

4. Reset stuck jobs if needed:
   ```bash
   # Reset specific job
   sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
     "UPDATE ingest_queue SET state='pending', retry_count=retry_count+1
      WHERE group_id='<GROUP_ID>';"
   ```

---

## Backup and Recovery

### Automated Backups

Backups are scheduled via cron:

- **Hourly:** Database snapshots to `/stage/backups/hourly/`
- **Daily:** Calibration tables to `/stage/backups/daily/`

Verify cron is running:

```bash
crontab -l | grep backup-cron
```

### Manual Backup

```bash
# Database only
/data/dsa110-contimg/scripts/backup-cron.sh hourly

# Full backup including caltables
/data/dsa110-contimg/scripts/backup-cron.sh daily
```

### Database Restore

```bash
# Stop services first
sudo systemctl stop contimg-stream contimg-api

# Decompress backup
gunzip /stage/backups/hourly/pipeline_YYYYMMDD_HHMMSS.sqlite3.gz

# Replace database
cp /stage/backups/hourly/pipeline_YYYYMMDD_HHMMSS.sqlite3 \
   /data/dsa110-contimg/state/db/pipeline.sqlite3

# Restart services
sudo systemctl start contimg-api contimg-stream
```

### Calibration Table Restore

```bash
# List available backups
ls -la /stage/backups/daily/caltables_*.tar.gz

# Extract specific backup
tar -xzf /stage/backups/daily/caltables_YYYYMMDD_030000.tar.gz \
    -C /products/
```

---

## Common Issues

### Issue: API returns 500 errors

**Diagnosis:**

```bash
journalctl -u contimg-api --since "10 min ago" | grep -i error
```

**Common causes:**

1. Database locked - check for long-running queries
2. Memory exhaustion
3. Missing dependencies

**Fix:**

```bash
sudo systemctl restart contimg-api
```

### Issue: MS files not appearing

**Diagnosis:**

```bash
# Check queue status
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
  "SELECT state, COUNT(*) FROM ingest_queue GROUP BY state;"

# Check for recent completions
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
  "SELECT group_id, completed_at FROM ingest_queue
   WHERE state='completed' ORDER BY completed_at DESC LIMIT 5;"
```

**Common causes:**

1. Incomplete subband groups (need all 16 subbands)
2. Streaming service not running
3. Output directory permissions

### Issue: Slow dashboard loading

**Diagnosis:**

```bash
# Check API response times
curl -w "@/dev/stdin" -s http://localhost:8000/api/v1/images?limit=10 <<< \
  "time_total: %{time_total}s\n" > /dev/null

# Check database size
du -h /data/dsa110-contimg/state/db/pipeline.sqlite3
```

**Fix options:**

1. Run VACUUM on database:
   ```bash
   sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 "VACUUM;"
   ```
2. Check for missing indexes
3. Increase API workers if CPU-bound

---

## Health Checks

### Daily Checklist

- [ ] Services running: `systemctl status contimg-api contimg-stream`
- [ ] Queue not backed up: `< 50 pending`
- [ ] Disk space: `> 20% free on /data and /stage`
- [ ] Recent calibration: Within last 24 hours
- [ ] Backups completing: Check `/stage/backups/hourly/`

### Weekly Checklist

- [ ] Review alert history in Prometheus
- [ ] Check backup retention (old backups cleaned up)
- [ ] Review failed jobs and error patterns
- [ ] Verify calibration quality trending

### Monitoring URLs

| Service    | URL                           |
| ---------- | ----------------------------- |
| API Health | http://localhost:8000/health  |
| Metrics    | http://localhost:8000/metrics |
| Prometheus | http://localhost:9090         |
| Grafana    | http://localhost:3000         |

---

## Emergency Procedures

### Complete Pipeline Restart

```bash
# 1. Stop all services
sudo systemctl stop contimg-stream contimg-api

# 2. Clear stuck jobs (optional)
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
  "UPDATE ingest_queue SET state='pending' WHERE state='in_progress';"

# 3. Restart services
sudo systemctl start contimg-api
sleep 5
sudo systemctl start contimg-stream

# 4. Verify health
curl -s http://localhost:8000/health | jq .
```

### Database Corruption Recovery

If the database becomes corrupted:

```bash
# 1. Stop services
sudo systemctl stop contimg-stream contimg-api

# 2. Attempt recovery
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 ".recover" | \
  sqlite3 /data/dsa110-contimg/state/db/pipeline_recovered.sqlite3

# 3. If recovery succeeds, replace
mv /data/dsa110-contimg/state/db/pipeline.sqlite3 \
   /data/dsa110-contimg/state/db/pipeline.sqlite3.corrupt
mv /data/dsa110-contimg/state/db/pipeline_recovered.sqlite3 \
   /data/dsa110-contimg/state/db/pipeline.sqlite3

# 4. If recovery fails, restore from backup
gunzip -k /stage/backups/hourly/pipeline_latest.sqlite3.gz
cp /stage/backups/hourly/pipeline_latest.sqlite3 \
   /data/dsa110-contimg/state/db/pipeline.sqlite3

# 5. Restart services
sudo systemctl start contimg-api contimg-stream
```

---

## Contact

For issues not covered in this runbook:

- Slack: `#dsa110-pipeline`
- Email: pipeline-ops@ovro.caltech.edu
