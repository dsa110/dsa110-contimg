# ABSURD - Asynchronous Background Service for Unified Resource Distribution

ABSURD is a PostgreSQL-backed durable task queue system for the DSA-110
continuum imaging pipeline. It provides reliable, distributed task processing
with automatic retries, dead letter queues, and DAG-based dependencies.

## Features

- **Durable Tasks** - Tasks survive worker crashes, stored in PostgreSQL
- **Atomic Claims** - SKIP LOCKED ensures exactly-once processing
- **DAG Dependencies** - Complex task workflows with `depends_on`
- **Cron Scheduling** - Time-based task triggers
- **Dead Letter Queue** - Failed tasks go to DLQ after max retries
- **WebSocket Events** - Real-time task status updates
- **Heartbeat Monitoring** - Detect stalled workers

## Quick Start

```bash
# Initialize schema (one-time)
python -m dsa110_contimg.absurd.setup init

# Start worker
python -m dsa110_contimg.absurd

# Check status
python -m dsa110_contimg.absurd.setup status
```

## Module Structure

```
absurd/
├── __init__.py          # Package exports
├── __main__.py          # Worker entry point
├── client.py            # AbsurdClient - database operations
├── worker.py            # AbsurdWorker - task execution loop
├── config.py            # AbsurdConfig - environment configuration
├── adapter.py           # Pipeline task executors (convert, calibrate, image)
├── dependencies.py      # DAG dependency management
├── scheduling.py        # Cron-like task scheduling
├── monitoring.py        # Health checks and metrics
├── schema.sql           # PostgreSQL schema definition
├── setup.py             # Database initialization utilities
└── scheduler_main.py    # Scheduler daemon entry point
```

## Configuration

Set via environment variables:

| Variable                      | Default           | Description                   |
| ----------------------------- | ----------------- | ----------------------------- |
| `ABSURD_ENABLED`              | `false`           | Enable ABSURD                 |
| `ABSURD_DATABASE_URL`         | (required)        | PostgreSQL connection URL     |
| `ABSURD_QUEUE_NAME`           | `dsa110-pipeline` | Queue name                    |
| `ABSURD_WORKER_CONCURRENCY`   | `4`               | Concurrent tasks per worker   |
| `ABSURD_WORKER_POLL_INTERVAL` | `1.0`             | Seconds between queue polls   |
| `ABSURD_TASK_TIMEOUT`         | `3600`            | Task timeout in seconds       |
| `ABSURD_MAX_RETRIES`          | `3`               | Max retry attempts before DLQ |
| `ABSURD_DLQ_ENABLED`          | `true`            | Enable dead letter queue      |

## Usage

### Spawning Tasks

```python
import asyncio
from dsa110_contimg.absurd import AbsurdClient

async def main():
    client = AbsurdClient.from_env()
    await client.connect()

    # Simple task
    task_id = await client.spawn("convert_uvh5", {
        "ms_path": "/stage/dsa110-contimg/ms/2025-01-01T00:00:00.ms"
    })

    # Task with priority
    task_id = await client.spawn("calibrate", params, priority=10)

    # Task with dependencies (runs after parent completes)
    child_id = await client.spawn("image", params, depends_on=[parent_id])

    await client.close()

asyncio.run(main())
```

### Task Chains

Pre-defined chains for common workflows:

```python
from dsa110_contimg.absurd.dependencies import (
    STANDARD_PIPELINE_CHAIN,  # convert → calibrate → image → extract → catalog
    QUICK_IMAGING_CHAIN,      # convert → image
    CALIBRATOR_CHAIN,         # convert → calibrate (saves cal tables)
    TARGET_CHAIN,             # apply cal → image → extract
)

# Spawn a complete pipeline
task_ids = await client.spawn_chain(STANDARD_PIPELINE_CHAIN, base_params)
```

### Checking Task Status

```python
task = await client.get_task(task_id)
print(task["status"])  # pending, claimed, completed, failed, cancelled

# Queue statistics
stats = await client.get_queue_stats("dsa110-pipeline")
print(f"Pending: {stats['pending']}, Completed: {stats['completed']}")
```

### Running the Worker

```python
from dsa110_contimg.absurd import AbsurdWorker, AbsurdConfig
from dsa110_contimg.absurd.adapter import execute_pipeline_task

config = AbsurdConfig.from_env()
worker = AbsurdWorker(config, execute_pipeline_task)
await worker.run()
```

## Database Schema

The schema creates:

**Tables:**

- `absurd.tasks` - Task queue with status, params, retry tracking
- `absurd.workflows` - Workflow groupings (optional)
- `absurd.scheduled_tasks` - Cron schedule definitions

**Key Functions:**

- `absurd.spawn_task()` - Create new task
- `absurd.claim_task()` - Atomically claim pending task
- `absurd.complete_task()` - Mark task completed
- `absurd.fail_task()` - Handle task failure with retry logic
- `absurd.get_queue_stats()` - Queue statistics

## Task Lifecycle

```
spawn() → pending → claim() → claimed → complete() → completed
                                    ↓
                               fail() → retry → pending (if retries remain)
                                    ↓
                               fail() → failed → DLQ (if max retries exceeded)
```

## Monitoring

### Check Queue Health

```bash
# Via setup module
python -m dsa110_contimg.absurd.setup status

# Via SQL
psql -c "SELECT * FROM absurd.get_queue_stats('dsa110-pipeline');"
```

### Worker Health

Workers send heartbeats every 30 seconds. Stale workers (no heartbeat > 2
minutes) indicate problems.

```sql
SELECT task_id, worker_id, heartbeat_at
FROM absurd.tasks
WHERE status = 'claimed'
  AND heartbeat_at < NOW() - INTERVAL '2 minutes';
```

## Related Documentation

- [Activation Guide](../../../docs/ops/absurd-service-activation.md) - Full setup instructions
- [PostgreSQL Deployment](../../../docs/postgresql-deployment.md) - Database setup
- [Architecture](../../../docs/ARCHITECTURE.md) - System design overview
