# Absurd Workflow Manager Integration

Durable, fault-tolerant task execution for the DSA-110 continuum imaging
pipeline.

## Overview

This package provides integration with the
[Absurd](https://github.com/your-absurd-repo) durable workflow manager,
enabling:

- **Fault tolerance**: Tasks survive worker crashes and restarts
- **Retries**: Automatic retry with configurable limits
- **Durability**: Task state persisted in PostgreSQL
- **Observability**: Query task status, history, and queue statistics
- **Concurrency**: Multi-worker task execution

## Quick Start

```bash
# 1. Setup database
./scripts/absurd/setup_absurd_db.sh

# 2. Create queue
./scripts/absurd/create_absurd_queues.sh

# 3. Configure
export ABSURD_ENABLED=true
export ABSURD_DATABASE_URL="postgresql://postgres@localhost/dsa110_absurd"

# 4. Test connection
python scripts/absurd/test_absurd_connection.py
```

See `docs/how-to/absurd_quick_start.md` for complete instructions.

## Usage

### Client API

```python
from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig

config = AbsurdConfig.from_env()

async with AbsurdClient(config.database_url) as client:
    # Spawn a task
    task_id = await client.spawn_task(
        queue_name=config.queue_name,
        task_name="calibrate",
        params={"ms_path": "/path/to/data.ms"}
    )

    # Check status
    task = await client.get_task(task_id)
    print(f"Status: {task['status']}")
```

### Worker

```python
from dsa110_contimg.absurd import AbsurdWorker, AbsurdConfig

async def execute_task(task_name: str, params: dict) -> dict:
    """Execute pipeline task."""
    if task_name == "calibrate":
        # Run calibration
        return {"status": "success"}
    # ...

config = AbsurdConfig.from_env()
worker = AbsurdWorker(config, execute_task)
await worker.start()  # Runs until stopped
```

## Architecture

```
┌─────────────┐
│   Client    │ ← Spawns tasks, queries status
└──────┬──────┘
       │
       ↓ PostgreSQL
┌─────────────┐
│  Database   │ ← Stores task state
│  (absurd)   │
└──────┬──────┘
       │
       ↑ Claims tasks
┌─────────────┐
│   Worker    │ ← Executes tasks
└─────────────┘
```

## Components

- `config.py` - Configuration dataclass
- `client.py` - Async client for task operations
- `worker.py` - Worker harness for task execution
- `adapter.py` - (TODO) Pipeline-specific task executor

## API Endpoints

When integrated with FastAPI:

- `POST /api/absurd/tasks` - Spawn a task
- `GET /api/absurd/tasks/{task_id}` - Get task details
- `GET /api/absurd/tasks` - List tasks
- `DELETE /api/absurd/tasks/{task_id}` - Cancel a task
- `GET /api/absurd/queues/{queue_name}/stats` - Queue statistics
- `GET /api/absurd/health` - Health check

## Environment Variables

```bash
ABSURD_ENABLED=true                # Enable Absurd (default: false)
ABSURD_DATABASE_URL=postgresql://  # PostgreSQL connection URL
ABSURD_QUEUE_NAME=dsa110-pipeline  # Queue name
ABSURD_WORKER_CONCURRENCY=4        # Worker concurrency
ABSURD_WORKER_POLL_INTERVAL=1.0    # Poll interval (sec)
ABSURD_TASK_TIMEOUT=3600           # Task timeout (sec)
ABSURD_MAX_RETRIES=3               # Max retry attempts
ABSURD_DLQ_ENABLED=true            # Route exhausted tasks to dead-letter queue
ABSURD_DLQ_QUEUE_NAME=dsa110-pipeline-dlq  # Dead-letter queue name
```

## Status

:white_heavy_check_mark: **Phase 1 Complete** - Infrastructure ready  
:anticlockwise_downwards_and_upwards_open_circle_arrows: **Phase 2 Pending** - Pipeline integration  
:clipboard: **Phase 3 Planned** - UI and testing

See `docs/dev-notes/status/2025-11/absurd_implementation_status.md` for details.

## Documentation

- Quick Start: `docs/how-to/absurd_quick_start.md`
- Implementation Status:
  `docs/dev-notes/status/2025-11/absurd_implementation_status.md`
- Absurd Roadmap: `src/absurd/ABSURD_IMPLEMENTATION_ROADMAP.md`

## Dependencies

- Python: `asyncpg>=0.29.0`
- PostgreSQL: 12+

## License

Same as DSA-110 continuum imaging pipeline.
