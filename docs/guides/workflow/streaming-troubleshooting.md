# Moved

This content was consolidated into `docs/how-to/streaming.md` (Troubleshooting
section).

## Quick Diagnosis

### Service Status Check

```bash
# Check via API
curl http://localhost:8010/api/streaming/status

# Check via Docker
docker ps | grep contimg-stream

# Check logs
docker-compose logs stream | tail -50
```

### Common Symptoms

| Symptom                   | Likely Cause                                 | Quick Fix                             |
| ------------------------- | -------------------------------------------- | ------------------------------------- |
| Service won't start       | Configuration error, missing directories     | Check config, verify paths            |
| Service stops immediately | Python/CASA not available, permission issues | Check Python path, verify permissions |
| No files being processed  | Input directory not accessible, wrong path   | Verify input_dir, check permissions   |
| High CPU usage            | Too many workers, processing bottleneck      | Reduce max_workers                    |
| High memory usage         | Large files, memory leak                     | Check file sizes, restart service     |
| Queue not processing      | Worker stuck, database locked                | Check queue state, restart service    |

## Common Issues and Solutions

### 1. Service Won't Start

#### Symptoms

- Start button in dashboard returns error
- Service status shows "Stopped" immediately after start attempt
- Error message: "Failed to start streaming service"

#### Diagnosis Steps

**Step 1: Check API Logs**

```bash
docker-compose logs api | grep -i "streaming\|error" | tail -20
```

**Step 2: Check Configuration**

```bash
# Via API
curl http://localhost:8010/api/streaming/config

# Check config file
cat state/streaming_config.json
```

**Step 3: Verify Directories**

```bash
# Check if directories exist and are accessible
ls -la $CONTIMG_INPUT_DIR
ls -la $CONTIMG_OUTPUT_DIR
ls -la $CONTIMG_SCRATCH_DIR
```

**Step 4: Check Python Environment**

```bash
# Verify CASA6 Python exists
ls -la /opt/miniforge/envs/casa6/bin/python

# Test Python import
/opt/miniforge/envs/casa6/bin/python -c "import casatasks; print('CASA OK')"
```

#### Solutions

**Issue: Configuration Error**

```bash
# Reset to defaults via API
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{
    "input_dir": "/data/incoming",
    "output_dir": "/stage/dsa110-contimg/ms",
    "expected_subbands": 16,
    "chunk_duration": 5.0
  }'
```

**Issue: Missing Directories**

```bash
# Create missing directories
mkdir -p /data/incoming
mkdir -p /stage/dsa110-contimg/ms
mkdir -p /stage/dsa110-contimg
chmod 755 /data/incoming /stage/dsa110-contimg/ms /stage/dsa110-contimg
```

**Issue: Python Not Found**

```bash
# Verify CASA6 environment
conda activate casa6
which python
python --version

# If missing, install CASA6 environment
# (See CASA installation documentation)
```

**Issue: Permission Denied**

```bash
# Check directory permissions
ls -ld /data/incoming /stage/dsa110-contimg

# Fix permissions (adjust UID/GID as needed)
sudo chown -R $USER:$USER /data/incoming
sudo chown -R $USER:$USER /stage/dsa110-contimg
```

### 2. Service Starts But Stops Immediately

#### Symptoms

- Service appears to start successfully
- Status shows "Running" briefly, then "Stopped"
- No error message in dashboard

#### Diagnosis Steps

**Step 1: Check Container Logs**

```bash
docker-compose logs stream | tail -100
```

**Step 2: Check for Python Errors**

```bash
docker-compose logs stream | grep -i "error\|exception\|traceback" | tail -20
```

**Step 3: Check System Resources**

```bash
# Check disk space
df -h /data /scratch

# Check memory
free -h

# Check if process is being killed
dmesg | tail -20
```

#### Solutions

**Issue: Python Import Error**

```bash
# Test imports manually
docker-compose exec stream python -c "import dsa110_contimg.conversion.streaming.streaming_converter"
```

**Issue: Out of Disk Space**

```bash
# Check disk usage
df -h

# Clean up old files
find /stage/dsa110-contimg -type f -mtime +30 -delete

# Or increase disk space
```

**Issue: Out of Memory (OOM Killer)**

```bash
# Check if OOM killer was involved
dmesg | grep -i "oom\|killed"

# Reduce max_workers in config
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{"max_workers": 2}'
```

**Issue: Database Locked**

```bash
# Check for database locks
sqlite3 state/ingest.sqlite3 "SELECT * FROM sqlite_master WHERE type='table';"

# If locked, may need to wait or restart
docker-compose restart stream
```

### 3. Service Running But Not Processing Files

#### Symptoms

- Service status shows "Running"
- No files being converted
- Queue shows items stuck in "pending" or "collecting"

#### Diagnosis Steps

**Step 1: Check Input Directory**

```bash
# Verify files are arriving
ls -lh /data/incoming/*.hdf5 | head -10

# Check file permissions
ls -l /data/incoming/*.hdf5 | head -5
```

**Step 2: Check Queue Status**

```bash
# Via API
curl http://localhost:8010/api/streaming/metrics

# Direct database query
sqlite3 state/ingest.sqlite3 "SELECT state, COUNT(*) FROM ingest_queue GROUP BY state;"
```

**Step 3: Check Worker Status**

```bash
# Check if workers are active
docker-compose logs stream | grep -i "worker\|processing" | tail -20
```

#### Solutions

**Issue: Files Not Arriving**

```bash
# Check if input directory is correct
curl http://localhost:8010/api/streaming/config | jq .input_dir

# Verify files exist
ls -la /data/incoming/

# Check file naming pattern (should be *_sb??.hdf5)
ls /data/incoming/*_sb*.hdf5 | head -5
```

**Issue: Wrong Expected Subbands**

```bash
# Check current setting
curl http://localhost:8010/api/streaming/config | jq .expected_subbands

# Update if wrong (e.g., if you have 8 subbands instead of 16)
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{"expected_subbands": 8}'
```

**Issue: Queue Stuck**

```bash
# Check queue state
sqlite3 state/ingest.sqlite3 "SELECT group_id, state, retry_count FROM ingest_queue WHERE state='in_progress';"

# Reset stuck items (use with caution)
sqlite3 state/ingest.sqlite3 "UPDATE ingest_queue SET state='pending' WHERE state='in_progress' AND retry_count < 3;"

# Restart service to clear locks
curl -X POST http://localhost:8010/api/streaming/restart
```

**Issue: Permission Denied on Files**

```bash
# Check file ownership
ls -l /data/incoming/*.hdf5 | head -5

# Fix ownership if needed
sudo chown -R $USER:$USER /data/incoming/*.hdf5
```

### 4. High CPU Usage

#### Symptoms

- CPU usage consistently >80%
- System becomes unresponsive
- Other services slow down

#### Diagnosis Steps

**Step 1: Check Current CPU Usage**

```bash
# Via API
curl http://localhost:8010/api/streaming/status | jq .cpu_percent

# Via Docker
docker stats contimg-stream --no-stream
```

**Step 2: Check Worker Count**

```bash
curl http://localhost:8010/api/streaming/config | jq .max_workers
```

**Step 3: Check Processing Rate**

```bash
curl http://localhost:8010/api/streaming/metrics | jq .processing_rate_per_hour
```

#### Solutions

**Issue: Too Many Workers**

```bash
# Reduce worker count
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{"max_workers": 2}'

# Restart to apply
curl -X POST http://localhost:8010/api/streaming/restart
```

**Issue: Large Files**

```bash
# Check file sizes
ls -lh /data/incoming/*.hdf5 | awk '{print $5}' | sort -h | tail -5

# Consider increasing chunk_duration to process fewer files
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{"chunk_duration": 10.0}'
```

**Issue: CASA Processing Overhead**

```bash
# Check CASA thread settings
echo $OMP_NUM_THREADS
echo $MKL_NUM_THREADS

# Limit threads if too high
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
```

### 5. High Memory Usage

#### Symptoms

- Memory usage >8GB
- System swapping
- Service crashes with out-of-memory

#### Diagnosis Steps

**Step 1: Check Memory Usage**

```bash
# Via API
curl http://localhost:8010/api/streaming/status | jq .memory_mb

# Via Docker
docker stats contimg-stream --no-stream --format "{{.MemUsage}}"
```

**Step 2: Check for Memory Leaks**

```bash
# Monitor memory over time
watch -n 5 'docker stats contimg-stream --no-stream --format "{{.MemUsage}}"'
```

**Step 3: Check File Sizes**

```bash
# Large files consume more memory
du -sh /data/incoming/*.hdf5 | sort -h | tail -5
```

#### Solutions

**Issue: Large Files**

```bash
# Process files in smaller batches
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{"chunk_duration": 2.0, "max_workers": 1}'
```

**Issue: Memory Leak**

```bash
# Restart service periodically
# Set up cron job or monitoring to restart every 24 hours
curl -X POST http://localhost:8010/api/streaming/restart
```

**Issue: Too Many Concurrent Operations**

```bash
# Reduce workers and processing rate
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{"max_workers": 1, "worker_poll_interval": 10.0}'
```

### 6. Queue Not Processing

#### Symptoms

- Queue shows items in "pending" state
- No progress on processing
- Workers appear idle

#### Diagnosis Steps

**Step 1: Check Queue State**

```bash
# Via API
curl http://localhost:8010/api/streaming/metrics | jq .queue_stats

# Direct query
sqlite3 state/ingest.sqlite3 <<EOF
SELECT state, COUNT(*) as count,
       MIN(last_update) as oldest,
       MAX(last_update) as newest
FROM ingest_queue
GROUP BY state;
EOF
```

**Step 2: Check for Stuck Items**

```bash
sqlite3 state/ingest.sqlite3 <<EOF
SELECT group_id, state, retry_count,
       datetime(last_update, 'unixepoch') as last_update_time
FROM ingest_queue
WHERE state IN ('in_progress', 'pending')
ORDER BY last_update
LIMIT 10;
EOF
```

**Step 3: Check Worker Logs**

```bash
docker-compose logs stream | grep -i "worker\|acquire\|pending" | tail -30
```

#### Solutions

**Issue: Database Locked**

```bash
# Check for locks
sqlite3 state/ingest.sqlite3 "PRAGMA busy_timeout;"

# Increase timeout (if using direct access)
sqlite3 state/ingest.sqlite3 "PRAGMA busy_timeout = 30000;"

# Restart service to clear locks
curl -X POST http://localhost:8010/api/streaming/restart
```

**Issue: Stuck in "in_progress"**

```bash
# Find items stuck for >1 hour
sqlite3 state/ingest.sqlite3 <<EOF
SELECT group_id, state, retry_count
FROM ingest_queue
WHERE state='in_progress'
  AND last_update < (strftime('%s', 'now') - 3600);
EOF

# Reset stuck items (use with caution)
sqlite3 state/ingest.sqlite3 <<EOF
UPDATE ingest_queue
SET state='pending', retry_count=retry_count+1
WHERE state='in_progress'
  AND last_update < (strftime('%s', 'now') - 3600)
  AND retry_count < 5;
EOF
```

**Issue: No Workers Available**

```bash
# Check worker configuration
curl http://localhost:8010/api/streaming/config | jq .max_workers

# Increase workers if needed
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{"max_workers": 4}'
```

### 7. Docker-Related Issues

#### Symptoms

- "docker-compose not found" errors
- Cannot control service from dashboard
- Container status inconsistent

#### Diagnosis Steps

**Step 1: Check Docker Availability**

```bash
# Check if Docker is running
docker ps

# Check if docker-compose is available
docker-compose --version
docker compose version
```

**Step 2: Check Docker Socket**

```bash
# Check if socket is accessible
ls -la /var/run/docker.sock

# Test Docker connection
docker info
```

**Step 3: Check Container Status**

```bash
# Check container directly
docker ps -a | grep contimg-stream

# Inspect container
docker inspect contimg-stream | jq '.[0].State'
```

#### Solutions

**Issue: Docker Compose Not Available**

```bash
# Install docker-compose if missing
sudo apt-get install docker-compose

# Or use Docker Compose V2
docker compose ps
```

**Issue: Docker Socket Not Mounted**

```bash
# Add to docker-compose.yml api service:
volumes:
  - /var/run/docker.sock:/var/run/docker.sock

# Restart API
docker-compose restart api
```

**Issue: Permission Denied on Socket**

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, or:
newgrp docker

# Verify
docker ps
```

### 8. Configuration Issues

#### Symptoms

- Configuration changes not taking effect
- Service uses wrong paths
- Settings reset after restart

#### Diagnosis Steps

**Step 1: Check Current Configuration**

```bash
# Via API
curl http://localhost:8010/api/streaming/config

# Check config file
cat state/streaming_config.json
```

**Step 2: Verify Configuration Persistence**

```bash
# Check file permissions
ls -la state/streaming_config.json

# Check if file is writable
test -w state/streaming_config.json && echo "Writable" || echo "Not writable"
```

#### Solutions

**Issue: Config Not Saving**

```bash
# Check directory permissions
ls -ld state/

# Fix permissions
chmod 755 state/
chmod 644 state/streaming_config.json
```

**Issue: Config Not Applied**

```bash
# Restart service after config change
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{"max_workers": 4}'

# Config update should auto-restart, but if not:
curl -X POST http://localhost:8010/api/streaming/restart
```

**Issue: Environment Variables Override Config**

```bash
# Check environment variables
docker-compose exec api env | grep CONTIMG

# Environment variables take precedence
# Update .env file or docker-compose.yml
```

## Debugging Procedures

### 1. Enable Debug Logging

```bash
# Update config to enable debug logging
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{"log_level": "DEBUG"}'

# Restart service
curl -X POST http://localhost:8010/api/streaming/restart

# Watch logs
docker-compose logs -f stream
```

### 2. Check Logs

**Streaming Service Logs**

```bash
# Recent logs
docker-compose logs stream | tail -100

# Follow logs in real-time
docker-compose logs -f stream

# Filter for errors
docker-compose logs stream | grep -i "error\|exception\|traceback"

# Filter for specific group
docker-compose logs stream | grep "2025-11-06T14:00:00"
```

**API Logs**

```bash
# Check API logs for streaming-related errors
docker-compose logs api | grep -i "streaming" | tail -50
```

**System Logs**

```bash
# Check system logs for OOM or other issues
dmesg | tail -50
journalctl -u docker -n 50
```

### 3. Database Inspection

**Check Queue State**

```bash
sqlite3 state/ingest.sqlite3 <<EOF
.mode column
.headers on
SELECT
    state,
    COUNT(*) as count,
    MIN(datetime(last_update, 'unixepoch')) as oldest,
    MAX(datetime(last_update, 'unixepoch')) as newest
FROM ingest_queue
GROUP BY state;
EOF
```

**Find Problematic Groups**

```bash
sqlite3 state/ingest.sqlite3 <<EOF
SELECT
    group_id,
    state,
    retry_count,
    error,
    datetime(last_update, 'unixepoch') as last_update
FROM ingest_queue
WHERE state = 'failed' OR retry_count > 3
ORDER BY last_update DESC
LIMIT 10;
EOF
```

**Check Processing History**

```bash
sqlite3 state/ingest.sqlite3 <<EOF
SELECT
    group_id,
    state,
    datetime(received_at, 'unixepoch') as received,
    datetime(last_update, 'unixepoch') as updated,
    (last_update - received_at) as duration_seconds
FROM ingest_queue
WHERE state = 'completed'
ORDER BY last_update DESC
LIMIT 10;
EOF
```

### 4. Performance Profiling

**Monitor Resource Usage**

```bash
# Continuous monitoring
watch -n 2 'docker stats contimg-stream --no-stream'

# Log to file
docker stats contimg-stream --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" > /tmp/docker_stats.log
```

**Check Processing Rate**

```bash
# Get current rate
curl http://localhost:8010/api/streaming/metrics | jq .processing_rate_per_hour

# Monitor over time
while true; do
  echo "$(date): $(curl -s http://localhost:8010/api/streaming/metrics | jq -r '.processing_rate_per_hour') groups/hour"
  sleep 60
done
```

**Identify Bottlenecks**

```bash
# Check queue depth
curl -s http://localhost:8010/api/streaming/metrics | jq .queue_stats

# Check disk I/O
iostat -x 1 10

# Check network I/O (if reading from network storage)
iftop -i eth0
```

## Recovery Procedures

### 1. Service Won't Start

**Full Reset Procedure**

```bash
# 1. Stop service
curl -X POST http://localhost:8010/api/streaming/stop

# 2. Clear PID file
rm -f state/streaming.pid

# 3. Reset config to defaults
rm -f state/streaming_config.json

# 4. Verify directories
mkdir -p /data/incoming /stage/dsa110-contimg/ms /stage/dsa110-contimg

# 5. Start with defaults
curl -X POST http://localhost:8010/api/streaming/start
```

### 2. Queue Stuck

**Queue Recovery Procedure**

```bash
# 1. Stop service
curl -X POST http://localhost:8010/api/streaming/stop

# 2. Reset stuck items
sqlite3 state/ingest.sqlite3 <<EOF
-- Reset items stuck in_progress for >1 hour
UPDATE ingest_queue
SET state='pending', retry_count=retry_count+1
WHERE state='in_progress'
  AND last_update < (strftime('%s', 'now') - 3600);

-- Reset failed items with low retry count
UPDATE ingest_queue
SET state='pending', retry_count=0
WHERE state='failed'
  AND retry_count < 3;
EOF

# 3. Restart service
curl -X POST http://localhost:8010/api/streaming/start
```

### 3. Database Corruption

**Database Recovery**

```bash
# 1. Stop service
curl -X POST http://localhost:8010/api/streaming/stop

# 2. Backup database
cp state/ingest.sqlite3 state/ingest.sqlite3.backup

# 3. Check integrity
sqlite3 state/ingest.sqlite3 "PRAGMA integrity_check;"

# 4. If corrupted, try to recover
sqlite3 state/ingest.sqlite3.backup ".dump" | sqlite3 state/ingest.sqlite3.recovered

# 5. If recovery fails, reset queue (data loss)
mv state/ingest.sqlite3 state/ingest.sqlite3.corrupted
# Queue will be recreated on next start

# 6. Restart service
curl -X POST http://localhost:8010/api/streaming/start
```

### 4. Complete Service Reset

**Nuclear Option (Use with Caution)**

```bash
# 1. Stop service
curl -X POST http://localhost:8010/api/streaming/stop

# 2. Remove state files
rm -f state/streaming.pid
rm -f state/streaming_config.json

# 3. Backup and reset queue (optional - causes data loss)
mv state/ingest.sqlite3 state/ingest.sqlite3.backup.$(date +%Y%m%d)

# 4. Verify environment
/opt/miniforge/envs/casa6/bin/python -c "import casatasks; print('OK')"

# 5. Start fresh
curl -X POST http://localhost:8010/api/streaming/start
```

## Performance Tuning

### 1. Optimize Worker Count

**Rule of Thumb:**

- 1 worker per CPU core (if CPU-bound)
- 1-2 workers if I/O-bound
- Monitor CPU usage and adjust

**Procedure:**

```bash
# Start with 2 workers
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{"max_workers": 2}'

# Monitor for 10 minutes
watch -n 60 'curl -s http://localhost:8010/api/streaming/status | jq .cpu_percent'

# Adjust based on CPU usage:
# - If CPU < 50%: Increase workers
# - If CPU > 80%: Decrease workers
```

### 2. Optimize Polling Intervals

**For High-Frequency Data:**

```bash
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{
    "poll_interval": 2.0,
    "worker_poll_interval": 3.0
  }'
```

**For Low-Frequency Data:**

```bash
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{
    "poll_interval": 10.0,
    "worker_poll_interval": 15.0
  }'
```

### 3. Optimize Chunk Duration

**For Large Files:**

```bash
# Increase chunk duration to process fewer files at once
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{"chunk_duration": 10.0}'
```

**For Small Files:**

```bash
# Decrease chunk duration for faster processing
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{"chunk_duration": 2.0}'
```

## Log Analysis

### Understanding Log Messages

**Common Log Patterns:**

```
INFO: Worker acquired group 2025-11-06T14:00:00
```

→ Worker picked up a group for processing

```
ERROR: Failed to process group 2025-11-06T14:00:00: Permission denied
```

→ File permission issue

```
WARNING: Group 2025-11-06T14:00:00 incomplete: 12/16 subbands
```

→ Missing subbands, waiting for more

```
INFO: Group 2025-11-06T14:00:00 completed in 125.3s
```

→ Successful processing

### Log Filtering

**Find Errors:**

```bash
docker-compose logs stream | grep -E "ERROR|Exception|Traceback" | tail -50
```

**Find Specific Group:**

```bash
docker-compose logs stream | grep "2025-11-06T14:00:00"
```

**Find Performance Issues:**

```bash
docker-compose logs stream | grep -E "slow|timeout|took.*[0-9]{3,}s"
```

**Find Worker Activity:**

```bash
docker-compose logs stream | grep -E "worker|acquire|process"
```

## Getting Help

### Information to Collect

When reporting issues, collect:

1. **Service Status**

   ```bash
   curl http://localhost:8010/api/streaming/status > status.json
   ```

2. **Configuration**

   ```bash
   curl http://localhost:8010/api/streaming/config > config.json
   ```

3. **Metrics**

   ```bash
   curl http://localhost:8010/api/streaming/metrics > metrics.json
   ```

4. **Recent Logs**

   ```bash
   docker-compose logs stream --tail 200 > stream_logs.txt
   ```

5. **Queue State**

   ```bash
   sqlite3 state/ingest.sqlite3 "SELECT * FROM ingest_queue WHERE state != 'completed' LIMIT 20;" > queue_state.txt
   ```

6. **System Information**
   ```bash
   docker info > docker_info.txt
   df -h > disk_usage.txt
   free -h > memory_usage.txt
   ```

### Diagnostic Script

```bash
#!/bin/bash
# Collect diagnostic information

OUTPUT_DIR="diagnostics_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"

echo "Collecting diagnostic information..."

# Service status
curl -s http://localhost:8010/api/streaming/status > "$OUTPUT_DIR/status.json"
curl -s http://localhost:8010/api/streaming/config > "$OUTPUT_DIR/config.json"
curl -s http://localhost:8010/api/streaming/metrics > "$OUTPUT_DIR/metrics.json"
curl -s http://localhost:8010/api/streaming/health > "$OUTPUT_DIR/health.json"

# Logs
docker-compose logs stream --tail 500 > "$OUTPUT_DIR/stream_logs.txt"
docker-compose logs api --tail 200 | grep -i streaming > "$OUTPUT_DIR/api_streaming_logs.txt"

# Queue state
sqlite3 state/ingest.sqlite3 <<EOF > "$OUTPUT_DIR/queue_state.txt"
.mode column
.headers on
SELECT * FROM ingest_queue ORDER BY last_update DESC LIMIT 50;
EOF

# System info
docker info > "$OUTPUT_DIR/docker_info.txt"
df -h > "$OUTPUT_DIR/disk_usage.txt"
free -h > "$OUTPUT_DIR/memory_usage.txt"
docker stats contimg-stream --no-stream > "$OUTPUT_DIR/container_stats.txt" 2>&1 || true

# Package info
tar -czf "${OUTPUT_DIR}.tar.gz" "$OUTPUT_DIR"
echo "Diagnostics saved to ${OUTPUT_DIR}.tar.gz"
```

## Prevention

### Best Practices

1. **Monitor Regularly**
   - Set up monitoring for service health
   - Alert on high CPU/memory usage
   - Alert on processing rate drops

2. **Maintain Disk Space**
   - Monitor disk usage
   - Clean up old files regularly
   - Set up alerts for low disk space

3. **Regular Restarts**
   - Restart service weekly to prevent memory leaks
   - Use cron or monitoring system

4. **Backup Configuration**
   - Backup `state/streaming_config.json` regularly
   - Version control configuration changes

5. **Test Changes**
   - Test configuration changes in development first
   - Verify after each change

## See Also

- [Streaming Control Guide](./streaming.md) - Basic usage
- [Streaming API Reference](../../reference/streaming-api.md) - API documentation
- [Streaming Architecture](../../architecture/pipeline/streaming-architecture.md) - System
  design
- [Docker Deployment](../../../dashboard/dashboard_deployment.md) - Deployment guide
