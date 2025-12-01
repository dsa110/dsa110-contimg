# ABSURD Workflow Manager Activation Guide

This guide covers activating the ABSURD (Asynchronous Background Service for Unified Resource Distribution) workflow manager for the DSA-110 continuum imaging pipeline.

## Current State

**What's already deployed:**

- ✅ PostgreSQL 16 container (`dsa110-postgres`) running on port 5432
- ✅ ABSURD Python package installed (`dsa110_contimg.absurd`)
- ✅ Core schema file ready (`src/dsa110_contimg/absurd/schema.sql`)
- ✅ Worker, client, scheduler, and dependency modules implemented
- ⏸️ ABSURD services **not yet activated** (requires manual enable)

**Services to activate:**

| Service            | Purpose                         | Default State |
| ------------------ | ------------------------------- | ------------- |
| `absurd-worker`    | Processes queued pipeline tasks | Disabled      |
| `absurd-scheduler` | Triggers cron-scheduled tasks   | Disabled      |

---

## Pre-Activation Checklist

Run these 5 verification commands before enabling ABSURD:

### 1. Verify PostgreSQL is Running

```bash
docker ps | grep dsa110-postgres
# Expected: Container running, healthy
```

```bash
pg_isready -h localhost -p 5432 -U dsa110
# Expected: localhost:5432 - accepting connections
```

### 2. Verify Database Connectivity

```bash
PGPASSWORD=dsa110_dev_password psql -h localhost -U dsa110 -d dsa110 -c "SELECT 1;"
# Expected: Returns 1
```

### 3. Check ABSURD Schema Exists

```bash
PGPASSWORD=dsa110_dev_password psql -h localhost -U dsa110 -d dsa110 \
  -c "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'absurd');"
# Expected: t (true) or f (false - needs initialization)
```

### 4. Check Environment Configuration

```bash
cd /data/dsa110-contimg/backend
grep -E "^ABSURD_" .env 2>/dev/null || echo "ABSURD variables not configured"
```

### 5. Verify Python Package

```bash
conda activate casa6
python -c "from dsa110_contimg.absurd import AbsurdClient, AbsurdWorker; print('OK')"
# Expected: OK
```

---

## Activation Steps

### Step 1: Initialize ABSURD Database Schema

Run the schema initialization script:

```bash
cd /data/dsa110-contimg/backend
conda activate casa6

# Initialize the ABSURD schema
python -m dsa110_contimg.absurd.setup init

# Or manually via psql:
PGPASSWORD=dsa110_dev_password psql -h localhost -U dsa110 -d dsa110 \
  -f src/dsa110_contimg/absurd/schema.sql
```

Verify schema was created:

```bash
PGPASSWORD=dsa110_dev_password psql -h localhost -U dsa110 -d dsa110 \
  -c "\dt absurd.*"
# Expected: Lists absurd.tasks table (and optionally scheduled_tasks, workflows)
```

### Step 2: Configure Environment Variables

Add ABSURD configuration to `.env`:

```bash
cat >> /data/dsa110-contimg/backend/.env << 'EOF'

# =============================================================================
# ABSURD Workflow Manager Configuration
# =============================================================================
ABSURD_ENABLED=true
ABSURD_DATABASE_URL=postgresql://dsa110:dsa110_dev_password@localhost:5432/dsa110
ABSURD_QUEUE_NAME=dsa110-pipeline
ABSURD_WORKER_CONCURRENCY=4
ABSURD_WORKER_POLL_INTERVAL=1.0
ABSURD_TASK_TIMEOUT=3600
ABSURD_MAX_RETRIES=3
ABSURD_DLQ_ENABLED=true
ABSURD_DLQ_QUEUE_NAME=dsa110-pipeline-dlq
EOF
```

Source the environment:

```bash
set -a && source /data/dsa110-contimg/backend/.env && set +a
```

### Step 3: Start ABSURD Worker

**Option A: Run in foreground (for testing)**

```bash
cd /data/dsa110-contimg/backend
conda activate casa6
set -a && source .env && set +a

python -m dsa110_contimg.absurd.worker
```

**Option B: Run as background process**

```bash
cd /data/dsa110-contimg/backend
conda activate casa6
set -a && source .env && set +a

nohup python -m dsa110_contimg.absurd.worker > /data/dsa110-contimg/state/logs/absurd-worker.log 2>&1 &
echo $! > /data/dsa110-contimg/state/absurd-worker.pid
```

**Option C: Run as systemd service (production)**

```bash
# Copy service file
sudo cp /data/dsa110-contimg/backend/ops/systemd/absurd-worker.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable absurd-worker
sudo systemctl start absurd-worker

# Check status
sudo systemctl status absurd-worker
```

### Step 4: Start ABSURD Scheduler (Optional)

Only needed if you have cron-scheduled tasks:

```bash
cd /data/dsa110-contimg/backend
conda activate casa6
set -a && source .env && set +a

# Foreground (testing)
python -m dsa110_contimg.absurd.scheduler

# Background
nohup python -m dsa110_contimg.absurd.scheduler > /data/dsa110-contimg/state/logs/absurd-scheduler.log 2>&1 &
echo $! > /data/dsa110-contimg/state/absurd-scheduler.pid
```

---

## Post-Activation Verification

### 1. Check Worker is Processing

```bash
# View worker logs
tail -f /data/dsa110-contimg/state/logs/absurd-worker.log

# Or for systemd
sudo journalctl -u absurd-worker -f
```

### 2. Spawn a Test Task

```bash
cd /data/dsa110-contimg/backend
conda activate casa6
python scripts/testing/test_absurd_worker.py
```

### 3. Check Queue Statistics

```bash
PGPASSWORD=dsa110_dev_password psql -h localhost -U dsa110 -d dsa110 -c "
SELECT * FROM absurd.get_queue_stats('dsa110-pipeline');
"
```

Expected output:

```
 pending | claimed | completed | failed | cancelled | retrying | total
---------+---------+-----------+--------+-----------+----------+-------
       0 |       0 |         1 |      0 |         0 |        0 |     1
```

### 4. List Recent Tasks

```bash
PGPASSWORD=dsa110_dev_password psql -h localhost -U dsa110 -d dsa110 -c "
SELECT task_id, task_name, status, created_at
FROM absurd.tasks
ORDER BY created_at DESC
LIMIT 10;
"
```

---

## Troubleshooting

### Worker Won't Start

**Symptom:** Worker exits immediately or fails to connect

**Solution:**

```bash
# Check PostgreSQL is accessible
pg_isready -h localhost -p 5432 -U dsa110

# Check database URL is correct
echo $ABSURD_DATABASE_URL

# Test connection manually
python -c "
import asyncio
from dsa110_contimg.absurd import AbsurdClient
async def test():
    client = AbsurdClient('$ABSURD_DATABASE_URL')
    async with client:
        print('Connected!')
asyncio.run(test())
"
```

### Schema Not Found

**Symptom:** `relation "absurd.tasks" does not exist`

**Solution:**

```bash
# Re-run schema initialization
PGPASSWORD=dsa110_dev_password psql -h localhost -U dsa110 -d dsa110 \
  -f /data/dsa110-contimg/backend/src/dsa110_contimg/absurd/schema.sql
```

### Tasks Stuck in "claimed" Status

**Symptom:** Tasks remain claimed but never complete

**Solution:**

```bash
# Check for crashed workers
PGPASSWORD=dsa110_dev_password psql -h localhost -U dsa110 -d dsa110 -c "
SELECT task_id, worker_id, claimed_at
FROM absurd.tasks
WHERE status = 'claimed'
  AND claimed_at < NOW() - INTERVAL '1 hour';
"

# Reset stale claimed tasks to pending
PGPASSWORD=dsa110_dev_password psql -h localhost -U dsa110 -d dsa110 -c "
UPDATE absurd.tasks
SET status = 'pending', worker_id = NULL, claimed_at = NULL
WHERE status = 'claimed'
  AND claimed_at < NOW() - INTERVAL '1 hour';
"
```

### Dead Letter Queue Growing

**Symptom:** Many tasks in DLQ

**Solution:**

```bash
# Check DLQ contents
PGPASSWORD=dsa110_dev_password psql -h localhost -U dsa110 -d dsa110 -c "
SELECT task_id, params->>'original_task_name' as task, params->>'error' as error
FROM absurd.tasks
WHERE queue_name = 'dsa110-pipeline-dlq'
ORDER BY created_at DESC
LIMIT 10;
"

# Retry a DLQ task
python -c "
import asyncio
from dsa110_contimg.absurd import AbsurdClient
async def retry():
    client = AbsurdClient('$ABSURD_DATABASE_URL')
    async with client:
        # Get task details and respawn
        pass
asyncio.run(retry())
"
```

---

## Scaling Workers

### Running Multiple Worker Instances

For higher throughput, run multiple workers:

```bash
# Worker 1
ABSURD_WORKER_CONCURRENCY=4 python -m dsa110_contimg.absurd.worker &

# Worker 2
ABSURD_WORKER_CONCURRENCY=4 python -m dsa110_contimg.absurd.worker &

# Worker 3
ABSURD_WORKER_CONCURRENCY=4 python -m dsa110_contimg.absurd.worker &
```

Each worker gets a unique ID and competes for tasks atomically.

### Tuning Concurrency

| Setting                       | Low Load | Medium Load | High Load |
| ----------------------------- | -------- | ----------- | --------- |
| `ABSURD_WORKER_CONCURRENCY`   | 2        | 4           | 8         |
| `ABSURD_WORKER_POLL_INTERVAL` | 5.0      | 1.0         | 0.5       |
| Number of Workers             | 1        | 2-3         | 4+        |

---

## Stopping Services

### Graceful Shutdown

**Background process:**

```bash
# Stop worker
kill $(cat /data/dsa110-contimg/state/absurd-worker.pid)

# Stop scheduler
kill $(cat /data/dsa110-contimg/state/absurd-scheduler.pid)
```

**Systemd service:**

```bash
sudo systemctl stop absurd-worker
sudo systemctl stop absurd-scheduler
```

### Emergency Stop

```bash
# Kill all ABSURD processes
pkill -f "dsa110_contimg.absurd"
```

### Drain Queue Before Shutdown

```bash
# Pause new task acceptance (set ABSURD_ENABLED=false)
# Wait for pending tasks to complete
PGPASSWORD=dsa110_dev_password psql -h localhost -U dsa110 -d dsa110 -c "
SELECT COUNT(*) FROM absurd.tasks WHERE status IN ('pending', 'claimed');
"
# Once count is 0, proceed with shutdown
```

---

## Related Documentation

- [CHANGELOG](../CHANGELOG.md) - Version history and feature additions
- [PostgreSQL Deployment](../postgresql-deployment.md) - Database setup details
- [Architecture](../ARCHITECTURE.md) - System design overview
- [ABSURD Module README](../../src/dsa110_contimg/absurd/README.md) - API documentation

---

## Quick Reference

### Environment Variables

| Variable                      | Default            | Description                    |
| ----------------------------- | ------------------ | ------------------------------ |
| `ABSURD_ENABLED`              | `false`            | Enable ABSURD workflow manager |
| `ABSURD_DATABASE_URL`         | `postgresql://...` | PostgreSQL connection URL      |
| `ABSURD_QUEUE_NAME`           | `dsa110-pipeline`  | Default queue name             |
| `ABSURD_WORKER_CONCURRENCY`   | `4`                | Tasks per worker               |
| `ABSURD_WORKER_POLL_INTERVAL` | `1.0`              | Seconds between polls          |
| `ABSURD_TASK_TIMEOUT`         | `3600`             | Task timeout (seconds)         |
| `ABSURD_MAX_RETRIES`          | `3`                | Max retry attempts             |
| `ABSURD_DLQ_ENABLED`          | `true`             | Enable dead letter queue       |
| `ABSURD_DLQ_QUEUE_NAME`       | `<queue>-dlq`      | DLQ name                       |

### Key Commands

```bash
# Start worker
python -m dsa110_contimg.absurd.worker

# Start scheduler
python -m dsa110_contimg.absurd.scheduler

# Test worker
python scripts/testing/test_absurd_worker.py

# Check queue stats
psql -c "SELECT * FROM absurd.get_queue_stats('dsa110-pipeline');"

# List tasks
psql -c "SELECT task_id, task_name, status FROM absurd.tasks ORDER BY created_at DESC LIMIT 10;"
```
