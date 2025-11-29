# Streaming Troubleshooting

Common issues and solutions for the streaming service.

---

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

| Symptom              | Likely Cause               | Quick Fix                      |
| -------------------- | -------------------------- | ------------------------------ |
| Service won't start  | Config error, missing dirs | Check config, verify paths     |
| Stops immediately    | Python/CASA unavailable    | Check Python path, permissions |
| No files processing  | Input dir inaccessible     | Verify input_dir, permissions  |
| High CPU usage       | Too many workers           | Reduce max_workers             |
| High memory usage    | Large files, memory leak   | Check file sizes, restart      |
| Queue not processing | Worker stuck, DB locked    | Check queue state, restart     |

---

## Issue 1: Service Won't Start

**Symptoms:**

- Start button returns error
- Status shows "Stopped" immediately after start
- Error: "Failed to start streaming service"

**Diagnosis:**

```bash
# Check API logs
docker-compose logs api | grep -i "streaming\|error" | tail -20

# Check configuration
curl http://localhost:8010/api/streaming/config

# Verify directories exist
ls -la $CONTIMG_INPUT_DIR
ls -la $CONTIMG_OUTPUT_DIR

# Check Python environment
ls -la /opt/miniforge/envs/casa6/bin/python
/opt/miniforge/envs/casa6/bin/python -c "import casatasks; print('CASA OK')"
```

**Solutions:**

*Configuration Error:*

```bash
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{
    "input_dir": "/data/incoming",
    "output_dir": "/stage/dsa110-contimg/ms",
    "expected_subbands": 16,
    "chunk_duration": 5.0
  }'
```

**Missing Directories:**

```bash
mkdir -p /data/incoming
mkdir -p /stage/dsa110-contimg/ms
chmod 755 /data/incoming /stage/dsa110-contimg/ms
```

**Permission Denied:**

```bash
sudo chown -R $USER:$USER /data/incoming
sudo chown -R $USER:$USER /stage/dsa110-contimg
```

---

## Issue 2: Service Starts But Stops Immediately

**Symptoms:**

- Service appears to start
- Status shows "Running" briefly, then "Stopped"
- No error in dashboard

**Diagnosis:**

```bash
# Check container logs
docker-compose logs stream | tail -100

# Check for Python errors
docker-compose logs stream | grep -i "error\|exception\|traceback" | tail -20

# Check system resources
df -h /data /stage
free -h
dmesg | tail -20
```

**Solutions:**

*Python Import Error:*

```bash
docker-compose exec stream python -c "import dsa110_contimg.conversion.streaming.streaming_converter"
```

**Out of Disk Space:**

```bash
df -h
find /stage/dsa110-contimg -type f -mtime +30 -delete
```

**Out of Memory (OOM):**

```bash
dmesg | grep -i "oom\|killed"

# Reduce workers
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{"max_workers": 2}'
```

**Database Locked:**

```bash
sqlite3 state/ingest.sqlite3 "SELECT * FROM sqlite_master WHERE type='table';"
docker-compose restart stream
```

---

## Issue 3: Not Processing Files

**Symptoms:**

- Service running but no conversions
- Queue items stuck in "pending" or "collecting"

**Diagnosis:**

```bash
# Check input directory
ls -lh /data/incoming/*.hdf5 | head -10

# Check queue status
curl http://localhost:8010/api/streaming/metrics
sqlite3 state/ingest.sqlite3 "SELECT state, COUNT(*) FROM ingest_queue GROUP BY state;"

# Check worker logs
docker-compose logs stream | grep -i "worker\|processing" | tail -20
```

**Solutions:**

*Files Not Arriving:*

```bash
# Check input directory setting
curl http://localhost:8010/api/streaming/config | jq .input_dir

# Check file naming pattern (should be *_sb??.hdf5)
ls /data/incoming/*_sb*.hdf5 | head -5
```

**Wrong Expected Subbands:**

```bash
# Update if you have different subband count
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{"expected_subbands": 8}'
```

**Queue Stuck:**

```bash
# Check stuck items
sqlite3 state/ingest.sqlite3 "SELECT group_id, state, retry_count FROM ingest_queue WHERE state='in_progress';"

# Reset stuck items (use with caution)
sqlite3 state/ingest.sqlite3 "UPDATE ingest_queue SET state='pending' WHERE state='in_progress' AND retry_count < 3;"

# Restart service
curl -X POST http://localhost:8010/api/streaming/restart
```

---

## Issue 4: High CPU Usage

**Symptoms:**

- CPU usage >80%
- System unresponsive

**Diagnosis:**

```bash
curl http://localhost:8010/api/streaming/status | jq .cpu_percent
curl http://localhost:8010/api/streaming/config | jq .max_workers
docker stats contimg-stream --no-stream
```

**Solutions:**

*Reduce Workers:*

```bash
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{"max_workers": 2}'

curl -X POST http://localhost:8010/api/streaming/restart
```

**Limit CASA Threads:**

```bash
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
```

---

## Issue 5: High Memory Usage

**Symptoms:**

- Memory >8GB
- System swapping
- OOM crashes

**Diagnosis:**

```bash
curl http://localhost:8010/api/streaming/status | jq .memory_mb
docker stats contimg-stream --no-stream
du -sh /data/incoming/*.hdf5 | sort -h | tail -5
```

**Solutions:**

*Reduce Workers:*

```bash
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{"max_workers": 2}'
```

**Enable tmpfs (if sufficient RAM):**

```bash
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{"stage_to_tmpfs": true, "tmpfs_path": "/dev/shm"}'
```

---

## Issue 6: Dashboard Shows Stale Status

**Symptoms:**

- Status doesn't update
- Old data displayed

**Solutions:**

1. Refresh browser (Ctrl+F5)
2. Check API is reachable: `curl http://localhost:8010/api/streaming/status`
3. Check CORS settings if browser console shows errors
4. Restart API service: `docker-compose restart api`

---

## Log Analysis

### Key Log Patterns

```bash
# Errors
docker-compose logs stream | grep -i "error\|exception\|failed"

# Successful conversions
docker-compose logs stream | grep -i "completed\|success"

# Queue activity
docker-compose logs stream | grep -i "processing\|pending\|collecting"

# Worker activity
docker-compose logs stream | grep -i "worker"
```

### Log Locations

| Deployment | Location                                        |
| ---------- | ----------------------------------------------- |
| Docker     | `docker-compose logs stream`                    |
| systemd    | `journalctl -u contimg-stream`                  |
| File       | `/data/dsa110-contimg/state/logs/streaming.log` |

---

## Recovery Procedures

### Full Service Reset

```bash
# Stop service
curl -X POST http://localhost:8010/api/streaming/stop

# Clear queue (WARNING: loses pending work)
sqlite3 state/ingest.sqlite3 "DELETE FROM ingest_queue WHERE state != 'completed';"

# Reset configuration
curl -X POST http://localhost:8010/api/streaming/config \
  -H "Content-Type: application/json" \
  -d '{
    "input_dir": "/data/incoming",
    "output_dir": "/stage/dsa110-contimg/ms",
    "expected_subbands": 16,
    "chunk_duration": 5.0,
    "max_workers": 4
  }'

# Start fresh
curl -X POST http://localhost:8010/api/streaming/start
```

### Database Recovery

```bash
# Backup current database
cp state/ingest.sqlite3 state/ingest.sqlite3.bak

# Check integrity
sqlite3 state/ingest.sqlite3 "PRAGMA integrity_check;"

# If corrupt, recreate (loses history)
rm state/ingest.sqlite3
curl -X POST http://localhost:8010/api/streaming/start
```

---

## Getting Help

If issues persist:

1. Collect logs: `docker-compose logs stream > streaming_logs.txt`
2. Collect config:
   `curl http://localhost:8010/api/streaming/config > config.json`
3. Check system resources: `free -h; df -h; top -bn1 | head -20`
4. Review recent changes to configuration or environment
