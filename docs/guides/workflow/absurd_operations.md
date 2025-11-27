# Absurd Operations Guide

> **⚠️ CONSOLIDATION NOTICE:** This document overlaps significantly with the
> canonical operations guide at
> [`docs/operations/absurd_operations.md`](../../operations/absurd_operations.md).
> Please use that document for authoritative operations procedures. This file is
> retained for additional detail and may be archived in a future cleanup.

**Author:** DSA-110 Team  
**Date:** 2025-11-18  
**Status:** Production Ready

---

## Overview

This guide provides operational procedures for managing the **Absurd workflow
manager** in production. Absurd provides fault-tolerant, durable task execution
for the DSA-110 continuum imaging pipeline.

**Key Features:**

- ✅ **Fault Tolerance**: Tasks survive worker crashes
- ✅ **Automatic Retries**: Configurable retry with exponential backoff
- ✅ **Durability**: PostgreSQL-backed task persistence
- ✅ **Observability**: Rich metrics and health monitoring
- ✅ **Scalability**: Multi-worker concurrent execution

---

## Quick Reference

### Essential Commands

```bash
# Check Absurd health status
curl http://localhost:8000/api/absurd/health

# View queue statistics
curl http://localhost:8000/api/absurd/queues/dsa110-pipeline/stats

# List recent tasks
curl http://localhost:8000/api/absurd/tasks?limit=10

# Cancel a task
curl -X DELETE http://localhost:8000/api/absurd/tasks/{task_id}

# Run benchmarks
python scripts/benchmark_absurd.py --quick

# Monitor queue health
python -c "
from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig
import asyncio

async def main():
    client = AbsurdClient('postgresql://...')
    await client.connect()
    stats = await client.get_queue_stats('dsa110-pipeline')
    print(stats)
    await client.close()

asyncio.run(main())
"
```

---

## Architecture

```
┌──────────────┐
│   Frontend   │  (React Dashboard)
└──────┬───────┘
       │ HTTP REST API
       ↓
┌──────────────┐
│   FastAPI    │  (API Server)
│   Backend    │
└──────┬───────┘
       │ AbsurdClient
       ↓
┌──────────────┐
│ PostgreSQL   │  (Task Queue)
│   Database   │
└──────┬───────┘
       │ Task Claims
       ↓
┌──────────────┐
│   Absurd     │  (Worker Pool)
│   Workers    │
└──────┬───────┘
       │ Adapter Layer
       ↓
┌──────────────┐
│   Pipeline   │  (Conversion, Calibration, Imaging)
│   Stages     │
└──────────────┘
```

---

## Configuration

### Environment Variables

```bash
# Required
export ABSURD_ENABLED=true
export ABSURD_DATABASE_URL="postgresql://user:pass@localhost:5432/absurd"
export ABSURD_QUEUE_NAME="dsa110-pipeline"

# Optional (with defaults)
export ABSURD_WORKER_CONCURRENCY=4        # Tasks per worker
export ABSURD_WORKER_POLL_INTERVAL=1.0    # Poll interval (seconds)
export ABSURD_TASK_TIMEOUT=3600           # Task timeout (seconds)
export ABSURD_MAX_RETRIES=3               # Max retry attempts
```

### Database Setup

```bash
# Create database
createdb absurd

# Create tables (automatic on first run)
python -c "
from dsa110_contimg.absurd import AbsurdClient
import asyncio

async def init():
    client = AbsurdClient('postgresql://localhost/absurd')
    await client.connect()
    await client.close()

asyncio.run(init())
"
```

---

## Starting and Stopping

### Start API Server (with Absurd)

```bash
# Development
export ABSURD_ENABLED=true
export ABSURD_DATABASE_URL="postgresql://localhost/absurd"
uvicorn dsa110_contimg.api.app:app --reload

# Production (systemd)
sudo systemctl start dsa110-contimg-api
```

### Start Worker Pool

```bash
# Single worker (development)
python scripts/run_absurd_worker.py \
  --database-url postgresql://localhost/absurd \
  --queue-name dsa110-pipeline \
  --concurrency 4

# Multiple workers (production)
for i in {1..4}; do
  python scripts/run_absurd_worker.py \
    --database-url postgresql://localhost/absurd \
    --queue-name dsa110-pipeline \
    --concurrency 2 \
    --worker-id worker-$i &
done
```

### Stop Gracefully

```bash
# API server
sudo systemctl stop dsa110-contimg-api

# Workers (graceful shutdown)
pkill -SIGTERM -f run_absurd_worker.py

# Workers (force kill if unresponsive)
pkill -SIGKILL -f run_absurd_worker.py
```

---

## WebSocket Events

The Absurd API emits WebSocket events for real-time updates:

### Task Update Events

**Event Type:** `task_update`

**Emitted When:**

- Task is spawned
- Task status changes (pending → claimed → completed/failed)
- Task is cancelled

**Event Format:**

```json
{
  "type": "task_update",
  "queue_name": "dsa110-pipeline",
  "task_id": "a1b2c3d4-...",
  "update": {
    "status": "completed",
    "completed_at": "2025-11-18T14:30:00Z",
    "result": {...}
  }
}
```

### Queue Stats Update Events

**Event Type:** `queue_stats_update`

**Emitted When:**

- Task is spawned
- Task status changes
- Task is cancelled

**Event Format:**

```json
{
  "type": "queue_stats_update",
  "queue_name": "dsa110-pipeline"
}
```

**Note:** Frontend should refetch queue stats when this event is received.

### WebSocket Endpoint

**URL:** `ws://your-server:8000/ws/status`

**Connection:**

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/status");
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === "task_update") {
    // Handle task update
  }
};
```

---

## Monitoring

### Health Checks

```bash
# API health endpoint
curl http://localhost:8000/api/absurd/health

# Expected response:
{
  "status": "healthy",
  "message": "Absurd is operational",
  "queue": "dsa110-pipeline"
}
```

### Queue Statistics

```bash
# Get queue stats
curl http://localhost:8000/api/absurd/queues/dsa110-pipeline/stats

# Expected response:
{
  "queue_name": "dsa110-pipeline",
  "pending": 12,
  "claimed": 4,
  "completed": 1247,
  "failed": 3,
  "cancelled": 0,
  "total": 1266
}
```

### Task Monitoring

```bash
# List tasks by status
curl "http://localhost:8000/api/absurd/tasks?status=pending&limit=10"
curl "http://localhost:8000/api/absurd/tasks?status=failed&limit=10"

# Get specific task details
curl http://localhost:8000/api/absurd/tasks/{task_id}

# Expected response:
{
  "task_id": "a1b2c3d4-...",
  "queue_name": "dsa110-pipeline",
  "task_name": "calibration-solve",
  "status": "completed",
  "retry_count": 1,
  "created_at": "2025-11-18T10:30:00",
  "claimed_at": "2025-11-18T10:30:02",
  "completed_at": "2025-11-18T10:32:15",
  "result": {"caltables": [...]}
}
```

### Metrics Dashboard

```bash
# Run monitoring script
python scripts/monitor_absurd.py \
  --database-url postgresql://localhost/absurd \
  --queue-name dsa110-pipeline \
  --interval 30

# Output:
# [2025-11-18 10:30:00] Queue Health: healthy
# [2025-11-18 10:30:00] Throughput: 2.5 tasks/sec
# [2025-11-18 10:30:00] Queue Depth: 8 tasks
# [2025-11-18 10:30:00] Workers: 4/4 active
```

---

## Troubleshooting

### Issue: No Workers Active

**Symptoms:**

- Tasks stuck in "pending" status
- Health check shows "No active workers"

**Diagnosis:**

```bash
# Check worker processes
ps aux | grep run_absurd_worker

# Check worker logs
journalctl -u dsa110-absurd-worker -f
```

**Resolution:**

```bash
# Start workers
python scripts/run_absurd_worker.py \
  --database-url postgresql://localhost/absurd \
  --queue-name dsa110-pipeline \
  --concurrency 4
```

---

### Issue: Tasks Failing Repeatedly

**Symptoms:**

- High failure rate in queue stats
- Tasks reaching max retry limit

**Diagnosis:**

```bash
# List failed tasks
curl "http://localhost:8000/api/absurd/tasks?status=failed&limit=20"

# Check task error details
curl http://localhost:8000/api/absurd/tasks/{task_id} | jq '.error'
```

**Resolution:**

```bash
# Common causes:
# 1. Invalid parameters → Fix task spawning logic
# 2. Resource exhaustion → Add more workers or increase timeout
# 3. CASA errors → Check CASA environment and MS file validity

# Re-run failed task with corrected params
curl -X POST http://localhost:8000/api/absurd/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "queue_name": "dsa110-pipeline",
    "task_name": "calibration-solve",
    "params": {...},
    "priority": 10
  }'
```

---

### Issue: Queue Depth Growing

**Symptoms:**

- `pending` count increasing over time
- Tasks not being processed

**Diagnosis:**

```bash
# Check queue depth trend
watch -n 5 'curl -s http://localhost:8000/api/absurd/queues/dsa110-pipeline/stats | jq ".pending"'

# Check worker concurrency
ps aux | grep run_absurd_worker | wc -l
```

**Resolution:**

```bash
# Option 1: Increase worker concurrency
# Edit worker config to increase concurrency per worker

# Option 2: Add more workers
for i in {5..8}; do
  python scripts/run_absurd_worker.py \
    --database-url postgresql://localhost/absurd \
    --queue-name dsa110-pipeline \
    --concurrency 2 \
    --worker-id worker-$i &
done

# Option 3: Increase task priority for urgent tasks
curl -X POST http://localhost:8000/api/absurd/tasks/{task_id}/priority \
  -H "Content-Type: application/json" \
  -d '{"priority": 15}'
```

---

### Issue: Database Connection Errors

**Symptoms:**

- Health check shows "Database unavailable"
- Workers crashing with connection errors

**Diagnosis:**

```bash
# Test database connectivity
psql postgresql://localhost/absurd -c "SELECT 1"

# Check PostgreSQL status
sudo systemctl status postgresql

# Check connection limits
psql -c "SHOW max_connections"
psql -c "SELECT count(*) FROM pg_stat_activity"
```

**Resolution:**

```bash
# Option 1: Restart PostgreSQL
sudo systemctl restart postgresql

# Option 2: Increase connection pool size
export ABSURD_POOL_MAX_SIZE=20

# Option 3: Reduce worker concurrency
# (Each worker uses pool_max_size connections)
```

---

### Issue: Tasks Timing Out

**Symptoms:**

- Tasks marked as "failed" with timeout errors
- `retry_count` incrementing

**Diagnosis:**

```bash
# Check task timeout settings
echo $ABSURD_TASK_TIMEOUT

# Check task execution times
curl http://localhost:8000/api/absurd/tasks | jq '.tasks[] | select(.status=="completed") | {task_name, duration: (.completed_at - .claimed_at)}'
```

**Resolution:**

```bash
# Option 1: Increase timeout for slow tasks
export ABSURD_TASK_TIMEOUT=7200  # 2 hours

# Option 2: Optimize task execution
# - Use tmpfs for MS conversion (faster I/O)
# - Reduce image size for quick-look imaging
# - Use parallel calibration solvers

# Option 3: Set per-task timeout
curl -X POST http://localhost:8000/api/absurd/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "queue_name": "dsa110-pipeline",
    "task_name": "imaging",
    "params": {...},
    "timeout_sec": 7200
  }'
```

---

## Performance Tuning

### Worker Pool Sizing

**Rule of Thumb:**

- **CPU-bound tasks** (imaging): 1 worker per CPU core
- **I/O-bound tasks** (conversion): 2-4 workers per core
- **Database-heavy tasks** (queries): Limit to avoid connection saturation

**Example Configuration:**

```bash
# 16-core machine, mixed workload
# Run 8 workers with concurrency=2 (total 16 tasks)

for i in {1..8}; do
  python scripts/run_absurd_worker.py \
    --concurrency 2 \
    --worker-id worker-$i &
done
```

### Task Prioritization

**Priority Levels:**

- **15-20**: Critical (real-time detection)
- **10-14**: High (active observations)
- **5-9**: Normal (routine processing)
- **1-4**: Low (backfill, reprocessing)

**Example:**

```bash
# Spawn high-priority calibration task
curl -X POST http://localhost:8000/api/absurd/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "queue_name": "dsa110-pipeline",
    "task_name": "calibration-solve",
    "params": {"ms_path": "/stage/urgent.ms"},
    "priority": 15
  }'
```

### Database Optimization

```sql
-- Create indexes for performance
CREATE INDEX idx_tasks_queue_priority ON tasks(queue_name, priority DESC, created_at);
CREATE INDEX idx_tasks_status ON tasks(status, queue_name);

-- Vacuum and analyze
VACUUM ANALYZE tasks;

-- Check table size
SELECT pg_size_pretty(pg_total_relation_size('tasks'));

-- Archive old completed tasks (>30 days)
DELETE FROM tasks WHERE status='completed' AND completed_at < NOW() - INTERVAL '30 days';
```

---

## Backup and Recovery

### Database Backup

```bash
# Daily backup
pg_dump absurd | gzip > /backups/absurd_$(date +%Y%m%d).sql.gz

# Restore from backup
gunzip -c /backups/absurd_20251118.sql.gz | psql absurd
```

### Task Recovery After Crash

```bash
# Absurd automatically recovers tasks after worker crashes
# No manual intervention needed!

# To manually reset stuck tasks:
psql absurd -c "
  UPDATE tasks
  SET status='pending', claimed_at=NULL
  WHERE status='claimed' AND claimed_at < NOW() - INTERVAL '1 hour'
"
```

---

## Security

### Database Access Control

```sql
-- Create dedicated Absurd user
CREATE USER absurd_app WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE absurd TO absurd_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON tasks TO absurd_app;
GRANT USAGE ON SEQUENCE tasks_id_seq TO absurd_app;
```

### API Authentication

```bash
# Add API key authentication (future)
export ABSURD_API_KEY="secure_random_key"

# Use in requests
curl -H "X-API-Key: secure_random_key" \
  http://localhost:8000/api/absurd/health
```

---

## Best Practices

### 1. Monitor Queue Depth

```bash
# Alert if queue depth > 500
curl -s http://localhost:8000/api/absurd/queues/dsa110-pipeline/stats | jq '.pending' | \
  awk '{if ($1 > 500) print "ALERT: Queue depth is", $1}'
```

### 2. Use Task Priorities

- Set high priority for time-sensitive tasks
- Use low priority for backfill/reprocessing
- Avoid setting all tasks to max priority

### 3. Configure Appropriate Timeouts

- **Conversion**: 10-15 minutes (depends on MS size)
- **Calibration**: 30-60 minutes
- **Imaging**: 15-30 minutes (depends on imsize)
- **Photometry**: 5-10 minutes

### 4. Scale Workers Dynamically

```bash
# Add workers during peak hours
# Remove workers during off-peak to save resources
```

### 5. Archive Old Tasks

```sql
-- Keep last 30 days of completed tasks
-- Archive to separate table or file
CREATE TABLE tasks_archive AS
  SELECT * FROM tasks WHERE status='completed' AND completed_at < NOW() - INTERVAL '30 days';

DELETE FROM tasks WHERE status='completed' AND completed_at < NOW() - INTERVAL '30 days';
```

---

## Emergency Procedures

### Emergency Stop

```bash
# Stop all workers immediately
pkill -SIGKILL -f run_absurd_worker

# Stop API server
sudo systemctl stop dsa110-contimg-api

# Prevent new tasks from being spawned
psql absurd -c "UPDATE tasks SET status='cancelled' WHERE status='pending'"
```

### Emergency Recovery

```bash
# 1. Identify the issue
journalctl -u dsa110-contimg-api -n 100
journalctl -u dsa110-absurd-worker -n 100

# 2. Fix the root cause

# 3. Reset failed tasks
psql absurd -c "UPDATE tasks SET status='pending', retry_count=0 WHERE status='failed'"

# 4. Restart services
sudo systemctl start dsa110-contimg-api
python scripts/run_absurd_worker.py --queue-name dsa110-pipeline --concurrency 4
```

---

## Contact and Support

**For operational issues:**

- Check logs: `journalctl -u dsa110-contimg-api -f`
- Review monitoring dashboard
- Contact DSA-110 operations team

**For bugs or feature requests:**

- Create issue in GitHub repository
- Include logs, task IDs, and error messages

---

## Changelog

| Date       | Version | Changes                  |
| ---------- | ------- | ------------------------ |
| 2025-11-18 | 1.0     | Initial operations guide |
