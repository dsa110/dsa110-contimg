# Absurd Workflow Manager Quick Start Guide

**Date:** 2025-11-18  
**Type:** Implementation Guide  
**Status:** ✅ Complete - Infrastructure Ready

---

## Overview

This guide walks you through setting up and using the Absurd durable workflow
manager with the DSA-110 continuum imaging pipeline. Absurd provides
fault-tolerant, resumable task execution backed by PostgreSQL.

## Prerequisites

- PostgreSQL 12+ running and accessible
- Python 3.11+ with casa6 environment
- DSA-110 pipeline source code at `/data/dsa110-contimg`

## Step 1: Install Absurd Schema (5 minutes)

### Option A: Using Setup Script (Recommended)

```bash
cd /data/dsa110-contimg
./scripts/absurd/setup_absurd_db.sh
```

The script will:

- Check PostgreSQL availability
- Create database `dsa110_absurd` (or use existing)
- Install Absurd schema
- Verify installation

### Option B: Manual Setup

```bash
# Create database
createdb dsa110_absurd

# Install schema (assuming Absurd is at ~/proj/absurd)
psql -d dsa110_absurd -f ~/proj/absurd/sql/absurd.sql

# Verify
psql -d dsa110_absurd -c "SELECT * FROM absurd.queues;"
```

## Step 2: Create Queue (2 minutes)

```bash
cd /data/dsa110-contimg
./scripts/absurd/create_absurd_queues.sh
```

This creates the `dsa110-pipeline` queue.

**Verify:**

```bash
psql -d dsa110_absurd -c "SELECT * FROM absurd.queues;"
```

## Step 3: Configure Environment (1 minute)

Add to your `.env` or shell environment:

```bash
# Enable Absurd
export ABSURD_ENABLED=true

# Database connection
export ABSURD_DATABASE_URL="postgresql://postgres@localhost/dsa110_absurd"

# Queue name (default)
export ABSURD_QUEUE_NAME="dsa110-pipeline"

# Optional: Worker settings
export ABSURD_WORKER_CONCURRENCY=4
export ABSURD_WORKER_POLL_INTERVAL=1.0
export ABSURD_TASK_TIMEOUT=3600
export ABSURD_MAX_RETRIES=3
```

## Step 4: Test Connection (2 minutes)

```bash
cd /data/dsa110-contimg
python scripts/absurd/test_absurd_connection.py
```

Expected output:

```
=== Absurd Connection Test ===

Configuration:
  Enabled: True
  Database URL: postgresql://postgres@localhost/dsa110_absurd
  Queue Name: dsa110-pipeline

Connecting to Absurd database...
✓ Connected

Spawning test task...
✓ Task spawned: a1b2c3d4-...

Fetching task details...
✓ Task retrieved:
  ID: a1b2c3d4-...
  Name: test-connection
  Status: pending
  Params: {'message': 'Hello from Absurd!', 'timestamp': 'now'}

...

=== All Tests Passed ===
```

## Step 5: Install Python Dependency

```bash
cd /data/dsa110-contimg
pip install asyncpg>=0.29.0
```

Or the dependency is already in `env/casa6_requirements.txt`.

## API Usage

### Python (Backend)

```python
from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig

# Load config from environment
config = AbsurdConfig.from_env()

# Create client
async with AbsurdClient(config.database_url) as client:
    # Spawn a task
    task_id = await client.spawn_task(
        queue_name=config.queue_name,
        task_name="calibrate",
        params={"ms_path": "/path/to/data.ms"},
        priority=5
    )

    # Get task status
    task = await client.get_task(task_id)
    print(f"Task status: {task['status']}")

    # List pending tasks
    tasks = await client.list_tasks(
        queue_name=config.queue_name,
        status="pending"
    )

    # Get queue stats
    stats = await client.get_queue_stats(config.queue_name)
    print(f"Pending: {stats['pending']}, "
          f"Completed: {stats['completed']}")
```

### TypeScript (Frontend)

```typescript
import {
  spawnTask,
  getTask,
  listTasks,
  getQueueStats,
  getHealthStatus,
} from "@/api/absurd";

// Spawn a task
const taskId = await spawnTask({
  queue_name: "dsa110-pipeline",
  task_name: "calibrate",
  params: { ms_path: "/path/to/data.ms" },
  priority: 5,
});

// Get task status
const task = await getTask(taskId);
console.log(`Task status: ${task.status}`);

// List pending tasks
const taskList = await listTasks("dsa110-pipeline", "pending");

// Get queue stats
const stats = await getQueueStats("dsa110-pipeline");

// Check health
const health = await getHealthStatus();
```

### REST API

```bash
# Spawn task
curl -X POST http://localhost:8000/api/absurd/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "queue_name": "dsa110-pipeline",
    "task_name": "calibrate",
    "params": {"ms_path": "/path/to/data.ms"},
    "priority": 5
  }'

# Get task
curl http://localhost:8000/api/absurd/tasks/<task-id>

# List tasks
curl "http://localhost:8000/api/absurd/tasks?queue_name=dsa110-pipeline&status=pending"

# Queue stats
curl http://localhost:8000/api/absurd/queues/dsa110-pipeline/stats

# Health check
curl http://localhost:8000/api/absurd/health
```

## Architecture

```
┌─────────────────┐
│  Dashboard UI   │ ← Frontend client (absurd.ts)
└────────┬────────┘
         │
         ↓ REST API
┌─────────────────┐
│   FastAPI App   │ ← Router (routers/absurd.py)
└────────┬────────┘
         │
         ↓ AbsurdClient
┌─────────────────┐
│  PostgreSQL DB  │ ← Absurd schema
│  (dsa110_absurd)│
└─────────────────┘
         ↑
         │ AbsurdWorker
┌─────────────────┐
│  Worker Process │ ← Claims and executes tasks
└─────────────────┘
```

## Components Created

### Python Modules

- `backend/src/dsa110_contimg/absurd/config.py` - Configuration
- `backend/src/dsa110_contimg/absurd/client.py` - Async client
- `backend/src/dsa110_contimg/absurd/worker.py` - Worker harness
- `backend/src/dsa110_contimg/absurd/__init__.py` - Package exports

### Scripts

- `scripts/absurd/setup_absurd_db.sh` - Database setup
- `scripts/absurd/create_absurd_queues.sh` - Queue creation
- `scripts/absurd/test_absurd_connection.py` - Connection test

### API

- `backend/src/dsa110_contimg/api/routers/absurd.py` - FastAPI router

### Frontend

- `frontend/src/api/absurd.ts` - TypeScript client

## Next Steps

### Phase 1: Complete (Infrastructure)

✅ Database schema installed  
✅ Python SDK created  
✅ Worker harness implemented  
✅ API endpoints exposed  
✅ Frontend client ready  
✅ Documentation complete

### Phase 2: Integration (To Do)

1. **Register API Router** - Add Absurd router to main FastAPI app
2. **Add to PipelineConfig** - Include Absurd settings in pipeline config
3. **Create Worker Executor** - Implement task execution logic for pipeline
   stages
4. **Add UI Page** - Create dashboard page for monitoring Absurd tasks

### Phase 3: Testing

1. Run integration tests
2. Test task spawning from UI
3. Test worker execution
4. Test failure/retry logic

## Troubleshooting

### Connection Errors

**Problem:** `Cannot connect to PostgreSQL`  
**Solution:** Ensure PostgreSQL is running and credentials are correct

```bash
psql -h localhost -U postgres -c '\q'
```

### Schema Not Found

**Problem:** `schema "absurd" does not exist`  
**Solution:** Re-run schema installation

```bash
./scripts/absurd/setup_absurd_db.sh
```

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'asyncpg'`  
**Solution:** Install asyncpg

```bash
pip install asyncpg>=0.29.0
```

## References

- Absurd Implementation Roadmap:
  `/data/dsa110-contimg/src/absurd/ABSURD_IMPLEMENTATION_ROADMAP.md`
- Absurd Source: `~/proj/absurd/`
- DSA-110 Pipeline: `/data/dsa110-contimg/src/dsa110_contimg/pipeline/`

---

**Last Updated:** 2025-11-18  
**Status:** Infrastructure Ready
