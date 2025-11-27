# Absurd Workflow Manager - Quickstart Guide

Complete guide to setting up and using the Absurd durable workflow manager for
the DSA-110 continuum imaging pipeline.

## Overview

Absurd provides durable, fault-tolerant task execution with:

- **PostgreSQL-backed persistence**: Tasks survive worker crashes and restarts
- **Automatic retries**: Failed tasks retry with configurable limits
- **Priority queuing**: High-priority tasks run first
- **Real-time monitoring**: WebSocket events for task updates
- **Multi-worker support**: Horizontal scaling with concurrent workers

## Prerequisites

- PostgreSQL 12+ installed and running
- Python 3.11 (casa6 environment)
- DSA-110 pipeline installed (`/data/dsa110-contimg`)
- Access to `/data` and `/stage` volumes

## Setup

### 1. Database Setup ✅ (Complete)

The `dsa110_absurd` PostgreSQL database is already set up with:

- **Database**: `dsa110_absurd` on PostgreSQL 15 (Docker: langwatch_db)
- **Connection**: `postgresql://user:password@localhost:5432/dsa110_absurd`
- **Schema**: Applied with tables, stored procedures, and indexes
- **Tables**: `absurd.tasks` (main queue), `absurd.queues` (metadata)

**Verification**:

```bash
# Test database connection
docker exec langwatch_db psql -U user -d dsa110_absurd -c "SELECT COUNT(*) FROM absurd.tasks;"
```

### 2. Environment Configuration ✅ (Complete)

Configuration in `/data/dsa110-contimg/ops/systemd/contimg.env`:

```bash
# Absurd Workflow Manager Configuration
ABSURD_ENABLED=true
ABSURD_DATABASE_URL=postgresql://user:password@localhost:5432/dsa110_absurd
ABSURD_QUEUE_NAME=dsa110-pipeline
ABSURD_WORKER_CONCURRENCY=4
ABSURD_WORKER_POLL_INTERVAL_SEC=1.0
ABSURD_TASK_TIMEOUT_SEC=3600
ABSURD_MAX_RETRIES=3
```

### 3. Backend API ✅ (Complete)

The backend API includes:

- **Endpoint**: `GET /api/absurd/metrics` - Real-time metrics (27 fields)
- **Endpoint**: `GET /api/absurd/tasks` - List tasks
- **Endpoint**: `POST /api/absurd/tasks` - Spawn tasks
- **Endpoint**: `GET /api/absurd/tasks/{id}` - Get task details
- **Endpoint**: `DELETE /api/absurd/tasks/{id}` - Cancel task
- **Endpoint**: `GET /api/absurd/queues/{name}/stats` - Queue statistics
- **Endpoint**: `GET /api/absurd/health` - Health check

**Start API** (when ready):

```bash
cd /data/dsa110-contimg
docker compose up -d api
```

### 4. Frontend Dashboard ✅ (Complete)

The frontend includes:

- **QueueMetricsCharts**: Real-time metrics visualization (throughput, latency,
  success rates)
- **BulkTaskOperations**: Multi-select task management
- **AbsurdPage**: Integrated dashboard with metrics and task lists
- **Build**: `npm run build` completed successfully (dist/ ready)

**Serve frontend**:

```bash
cd /data/dsa110-contimg/frontend

# Option 1: Development preview server (quick testing)
npm run preview  # Serves on http://localhost:4173

# Option 2: Production web server (recommended)
# Copy built files to your web server's document root:
#   - For nginx: sudo cp -r dist/* /var/www/html/absurd/
#   - For caddy: sudo cp -r dist/* /srv/www/absurd/
#   - For Apache: sudo cp -r dist/* /var/www/html/absurd/
# Then configure your server to serve from that directory
```

### 5. Test Workflow ✅ (Verified)

Complete end-to-end workflow tested:

```bash
conda activate casa6
cd /data/dsa110-contimg

python -c "
import asyncio, sys
sys.path.insert(0, 'backend/src')
from dsa110_contimg.absurd import AbsurdClient

async def test():
    client = AbsurdClient('postgresql://user:password@localhost:5432/dsa110_absurd')
    await client.connect()

    # Spawn → Claim → Complete workflow
    task_id = await client.spawn_task('test-queue', 'test-task', {}, 10)
    claimed = await client.claim_task('test-queue', 'worker-1')
    await client.complete_task(task_id, {'result': 'success'})

    stats = await client.get_queue_stats('test-queue')
    print(f'Stats: {stats}')

    await client.close()

asyncio.run(test())
"
```

Expected output:

```text
Stats: {'pending': 0, 'claimed': 0, 'completed': 1, 'failed': 0, 'cancelled': 0}
```

## Running the Worker

### Option 1: Systemd (Production)

```bash
# Install service
sudo cp ops/systemd/contimg-absurd-worker.service /etc/systemd/system/
sudo systemctl daemon-reload

# Start worker
sudo systemctl enable contimg-absurd-worker.service
sudo systemctl start contimg-absurd-worker.service

# Check status
sudo systemctl status contimg-absurd-worker.service

# View logs
sudo journalctl -u contimg-absurd-worker.service -f
```

### Option 2: Manual (Development/Testing)

```bash
# Activate casa6 environment
conda activate casa6

# Start worker
python -m dsa110_contimg.scripts.absurd.start_worker \
    --database-url postgresql://postgres:postgres@localhost:5432/dsa110_absurd \
    --queue-name dsa110-pipeline \
    --concurrency 4 \
    --log-level INFO
```

Worker output:

```text
Starting Absurd worker hostname-a1b2c3d4 on queue dsa110-pipeline
Worker polling every 1.0 seconds
Waiting for tasks...
```

## Usage Examples

### Example 1: Convert UVH5 to MS

```python
import asyncio
from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig

async def submit_conversion():
    config = AbsurdConfig.from_env()

    async with AbsurdClient(config.database_url) as client:
        task_id = await client.spawn_task(
            queue_name=config.queue_name,
            task_name="convert-uvh5-to-ms",
            params={
                "config": {"paths": {"output_dir": "/stage/dsa110-contimg/ms"}},
                "inputs": {
                    "input_path": "/data/incoming",
                    "start_time": "2025-11-25T00:00:00",
                    "end_time": "2025-11-25T01:00:00"
                }
            },
            priority=10
        )

        print(f"Task spawned: {task_id}")

        # Poll for completion
        while True:
            task = await client.get_task(task_id)
            status = task["status"]
            print(f"Status: {status}")

            if status in ("completed", "failed", "cancelled"):
                break

            await asyncio.sleep(5)

        if status == "completed":
            print(f"✓ Conversion successful")
            print(f"Result: {task['result']}")
        else:
            print(f"✗ Task {status}: {task.get('error')}")

# Run
asyncio.run(submit_conversion())
```

### Example 2: Full Calibration + Imaging Pipeline

```python
async def run_full_pipeline(ms_path: str):
    """Execute: Calibration Solve → Apply → Imaging"""
    config = AbsurdConfig.from_env()

    async with AbsurdClient(config.database_url) as client:
        # Step 1: Solve calibration
        solve_task_id = await client.spawn_task(
            queue_name=config.queue_name,
            task_name="calibration-solve",
            params={
                "config": None,  # Use defaults
                "outputs": {"ms_path": ms_path}
            },
            priority=20
        )

        print(f"[1/3] Calibration solve: {solve_task_id}")
        solve_task = await wait_for_task(client, solve_task_id)

        if solve_task["status"] != "completed":
            print(f"✗ Calibration solve failed: {solve_task['error']}")
            return

        cal_tables = solve_task["result"]["outputs"]["calibration_tables"]
        print(f"✓ Calibration tables: {list(cal_tables.keys())}")

        # Step 2: Apply calibration
        apply_task_id = await client.spawn_task(
            queue_name=config.queue_name,
            task_name="calibration-apply",
            params={
                "config": None,
                "outputs": {
                    "ms_path": ms_path,
                    "calibration_tables": cal_tables
                }
            },
            priority=20
        )

        print(f"[2/3] Calibration apply: {apply_task_id}")
        apply_task = await wait_for_task(client, apply_task_id)

        if apply_task["status"] != "completed":
            print(f"✗ Calibration apply failed: {apply_task['error']}")
            return

        print(f"✓ Calibration applied")

        # Step 3: Image
        image_task_id = await client.spawn_task(
            queue_name=config.queue_name,
            task_name="imaging",
            params={
                "config": None,
                "outputs": {"ms_path": ms_path}
            },
            priority=15
        )

        print(f"[3/3] Imaging: {image_task_id}")
        image_task = await wait_for_task(client, image_task_id)

        if image_task["status"] != "completed":
            print(f"✗ Imaging failed: {image_task['error']}")
            return

        image_path = image_task["result"]["outputs"]["image_path"]
        print(f"✓ Pipeline complete: {image_path}")


async def wait_for_task(client, task_id):
    """Poll until task completes"""
    while True:
        task = await client.get_task(task_id)
        if task["status"] in ("completed", "failed", "cancelled"):
            return task
        await asyncio.sleep(2)

# Run
asyncio.run(run_full_pipeline("/stage/dsa110-contimg/ms/2025-11-25T00:00:00.ms"))
```

### Example 3: Using CLI Scripts

```bash
# Submit a task via CLI
python scripts/absurd/submit_test_task.py convert-uvh5-to-ms \
    --input-path /data/incoming \
    --start-time "2025-11-25T00:00:00" \
    --end-time "2025-11-25T01:00:00" \
    --priority 10

# Output:
# Task spawned: 550e8400-e29b-41d4-a716-446655440000
# Status: pending

# Check task status
python scripts/absurd/submit_test_task.py check \
    550e8400-e29b-41d4-a716-446655440000

# List recent tasks
python scripts/absurd/submit_test_task.py list --limit 10

# Get queue statistics
python scripts/absurd/submit_test_task.py stats
```

## REST API Integration

If the API server is running (`contimg-api.service`), you can use HTTP:

```bash
# Spawn task
curl -X POST http://localhost:8000/api/absurd/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "queue_name": "dsa110-pipeline",
    "task_name": "convert-uvh5-to-ms",
    "params": {
      "config": null,
      "inputs": {
        "input_path": "/data/incoming",
        "start_time": "2025-11-25T00:00:00",
        "end_time": "2025-11-25T01:00:00"
      }
    },
    "priority": 10
  }'

# Get task status
curl http://localhost:8000/api/absurd/tasks/{task_id}

# List tasks
curl http://localhost:8000/api/absurd/tasks?status=pending&limit=10

# Get queue stats
curl http://localhost:8000/api/absurd/queues/dsa110-pipeline/stats
```

## Supported Task Types

| Task Name            | Description        | Required Params                                             |
| -------------------- | ------------------ | ----------------------------------------------------------- |
| `convert-uvh5-to-ms` | Convert UVH5 → MS  | `inputs.input_path`, `inputs.start_time`, `inputs.end_time` |
| `calibration-solve`  | Solve calibration  | `outputs.ms_path`                                           |
| `calibration-apply`  | Apply calibration  | `outputs.ms_path`, `outputs.calibration_tables`             |
| `imaging`            | Create images      | `outputs.ms_path`                                           |
| `validation`         | Validate MS        | `outputs.ms_path`                                           |
| `crossmatch`         | Catalog crossmatch | `outputs.image_path`                                        |
| `photometry`         | Photometry         | `outputs.image_path`                                        |
| `catalog-setup`      | Setup catalogs     | `inputs.input_path`                                         |
| `organize-files`     | Organize MS files  | `outputs.ms_path` or `outputs.ms_paths`                     |

## Monitoring

### Queue Statistics

```python
async def monitor_queue():
    config = AbsurdConfig.from_env()

    async with AbsurdClient(config.database_url) as client:
        stats = await client.get_queue_stats(config.queue_name)
        print(f"Queue: {config.queue_name}")
        print(f"  Pending: {stats['pending']}")
        print(f"  Claimed: {stats['claimed']}")
        print(f"  Completed: {stats['completed']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Cancelled: {stats['cancelled']}")

asyncio.run(monitor_queue())
```

### Worker Health

```bash
# Check worker is running
sudo systemctl status contimg-absurd-worker.service

# View real-time logs
sudo journalctl -u contimg-absurd-worker.service -f

# Check worker is processing tasks
grep "Processing task" /data/dsa110-contimg/state/logs/absurd-worker.out | tail -20
```

### Database Queries

```sql
-- Connect to database
psql -U postgres -d dsa110_absurd

-- Show recent tasks
SELECT task_id, task_name, status, created_at, completed_at
FROM absurd.t_tasks
ORDER BY created_at DESC
LIMIT 10;

-- Queue depth
SELECT status, COUNT(*) FROM absurd.t_tasks
WHERE queue_name = 'dsa110-pipeline'
GROUP BY status;

-- Average execution time
SELECT
    task_name,
    COUNT(*) as total,
    AVG(EXTRACT(EPOCH FROM (completed_at - claimed_at))) as avg_sec
FROM absurd.t_tasks
WHERE status = 'completed'
GROUP BY task_name;
```

## Troubleshooting

### Worker not starting

```bash
# Check environment file
cat /data/dsa110-contimg/ops/systemd/contimg.env | grep ABSURD

# Check PostgreSQL is running
systemctl status postgresql

# Test database connection
psql -U postgres -d dsa110_absurd -c "SELECT version();"

# Check logs
sudo journalctl -u contimg-absurd-worker.service -n 50
```

### Tasks stuck in "pending"

```bash
# Verify worker is running
systemctl status contimg-absurd-worker.service

# Check if worker is polling
tail -f /data/dsa110-contimg/state/logs/absurd-worker.out

# Check database connectivity
python scripts/absurd/test_absurd_connection.py
```

### Tasks failing repeatedly

```sql
-- Check error messages
SELECT task_id, task_name, error, retry_count
FROM absurd.t_tasks
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 10;
```

```bash
# Check worker logs for exceptions
grep -A 10 "exception" /data/dsa110-contimg/state/logs/absurd-worker.err
```

### Performance issues

```bash
# Check worker concurrency
grep ABSURD_WORKER_CONCURRENCY /data/dsa110-contimg/ops/systemd/contimg.env

# Monitor system resources
htop

# Check database performance
psql -U postgres -d dsa110_absurd -c "
    SELECT schemaname, tablename, n_live_tup, n_dead_tup
    FROM pg_stat_user_tables
    WHERE schemaname = 'absurd';
"
```

## Best Practices

1. **Use appropriate priorities**: High-priority (20+) for calibrators, medium
   (10-15) for science targets
2. **Monitor queue depth**: Keep pending tasks < 100 for best performance
3. **Scale workers**: Add workers (`ABSURD_WORKER_CONCURRENCY`) for high
   throughput
4. **Regular cleanup**: Archive completed tasks older than 30 days
5. **Database maintenance**: Run `VACUUM ANALYZE` weekly on Absurd tables
6. **Logging**: Keep worker logs rotated (logrotate recommended)

## Troubleshooting Guide

### Docker Credentials Timeout Error

If you see:
`Error calling StartServiceByName for org.freedesktop.secrets: Timeout was reached`

**Solution Options**:

```bash
# Option 1: Restart Docker daemon (simplest)
sudo systemctl restart docker
docker compose up -d api

# Option 2: Disable credential store temporarily
mkdir -p ~/.docker
echo '{"credsStore":""}' > ~/.docker/config.json
docker compose up -d api

# Option 3: Install credential helpers
sudo apt-get install -y gnome-keyring pass
# Then restart your session or reboot

# Option 4: Use podman instead of docker (alternative)
sudo apt-get install -y podman podman-compose
podman-compose up -d api
```

**Why this happens**: Docker tries to access the system keyring for registry
authentication, but the D-Bus service is unavailable or timed out. This is
common on headless servers or LXD containers.

### API Not Starting

Check logs:

```bash
docker compose logs api
# Or if using systemd:
sudo journalctl -u contimg-api.service -f
```

Common issues:

- **Port 8000 already in use**: Change `API_PORT` in `ops/systemd/contimg.env`
- **Database connection failed**: Verify PostgreSQL is running:
  `docker ps | grep langwatch_db`
- **Import errors**: Ensure `casa6` conda environment has all dependencies

### Frontend Not Loading

```bash
# Check if Vite dev server is running
ps aux | grep vite

# Check build output
ls -lh frontend/dist/

# Verify API connectivity
curl http://localhost:8000/api/absurd/health
```

## Phase 2 Features: Pipeline Integration

### Task Chaining

Task chains define sequences of dependent operations that execute automatically:

```python
from dsa110_contimg.absurd import (
    TaskChain,
    execute_chained_task,
    STANDARD_PIPELINE_CHAIN,
    QUICK_IMAGING_CHAIN,
)

# Pre-defined chains:
# - STANDARD_PIPELINE_CHAIN: conversion → calibration-solve → calibration-apply → imaging → validation → photometry → crossmatch
# - QUICK_IMAGING_CHAIN: conversion → calibration-apply → imaging
# - CALIBRATOR_CHAIN: conversion → calibration-solve → imaging → validation
# - TARGET_CHAIN: conversion → calibration-apply → imaging → photometry → crossmatch

# Execute a task with automatic follow-up spawning
result = await execute_chained_task(
    client=absurd_client,
    chain=STANDARD_PIPELINE_CHAIN,
    task_name="conversion",
    params={"inputs": {"group_id": "2025-11-25T12:00:00"}},
)
# After conversion completes, calibration-solve is automatically spawned
```

### Housekeeping Tasks

Automated maintenance tasks for cleanup and recovery:

```python
from dsa110_contimg.absurd import execute_housekeeping

# Execute housekeeping (cleans scratch, recovers stuck groups, prunes old tasks)
result = await execute_housekeeping(
    client=absurd_client,
    queue_name="dsa110-pipeline",
    task_name="housekeeping",
    params={},
)
# Returns: {"cleaned_scratch": 12, "recovered_groups": 3, "pruned_tasks": 45}
```

### Streaming Converter Bridge

Submit discovered subband groups to Absurd instead of local SQLite:

```python
from dsa110_contimg.absurd import AbsurdStreamingBridge

# Initialize bridge to Absurd queue
bridge = AbsurdStreamingBridge(
    database_url="postgresql://user:password@localhost:5432/dsa110_absurd",
    queue_name="dsa110-pipeline",
)

# Submit a complete subband group (16 files)
task_id = await bridge.submit_group(
    group_id="2025-11-25T12:00:00",
    file_paths=["/data/incoming/2025-11-25T12:00:00_sb00.hdf5", ...],
)
```

### Dead Letter Queue API

Manage failed operations via REST API:

```bash
# List DLQ items
curl http://localhost:8000/api/dlq/items?status=pending

# Get specific item
curl http://localhost:8000/api/dlq/items/123

# Retry a failed operation
curl -X POST http://localhost:8000/api/dlq/items/123/retry \
  -H "Content-Type: application/json" \
  -d '{"resubmit_to_absurd": true}'

# Mark as resolved
curl -X POST http://localhost:8000/api/dlq/items/123/resolve \
  -d '{"note": "Fixed manually"}'

# Get DLQ statistics
curl http://localhost:8000/api/dlq/stats
# Returns: {"pending": 5, "retrying": 2, "resolved": 10, "failed": 1, "by_component": {...}}

# Delete item permanently
curl -X DELETE http://localhost:8000/api/dlq/items/123
```

### Real-time WebSocket Events

Connect to WebSocket for live updates:

```javascript
// Frontend WebSocket connection
const ws = new WebSocket("ws://localhost:8000/ws/status");

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case "task_update":
      console.log(`Task ${data.task_id}: ${data.update.status}`);
      break;
    case "queue_stats_update":
      console.log(`Queue ${data.queue_name} stats changed`);
      break;
    case "dlq_update":
      console.log(`DLQ item ${data.item_id}: ${data.action}`);
      break;
  }
};
```

## Phase 3 Features: Production Deployment & Operations

### Deployment Script

Use the deployment script for easy service management:

```bash
# Install and enable the Absurd worker service
./ops/scripts/deploy_absurd.sh install

# Start the service
./ops/scripts/deploy_absurd.sh start

# Check status and queue statistics
./ops/scripts/deploy_absurd.sh status

# View logs
./ops/scripts/deploy_absurd.sh logs

# Restart after configuration changes
./ops/scripts/deploy_absurd.sh restart

# Uninstall (removes systemd service)
./ops/scripts/deploy_absurd.sh uninstall
```

### Health Checks

Run health checks for monitoring integration:

```bash
# Human-readable output
./ops/scripts/health_check_absurd.sh

# JSON output for monitoring systems (Prometheus, Nagios, etc.)
./ops/scripts/health_check_absurd.sh --json

# Quiet mode (exit code only)
./ops/scripts/health_check_absurd.sh --quiet
```

Exit codes: `0` = healthy, `1` = unhealthy, `2` = critical

### Prometheus Metrics

Scrape metrics at `/api/absurd/metrics/prometheus`:

```bash
# Check Prometheus metrics
curl http://localhost:8000/api/absurd/metrics/prometheus
```

**Prometheus scrape config:**

```yaml
scrape_configs:
  - job_name: "absurd"
    static_configs:
      - targets: ["localhost:8000"]
    metrics_path: "/api/absurd/metrics/prometheus"
    scrape_interval: 15s
```

**Available metrics:**

| Metric                          | Type    | Description                |
| ------------------------------- | ------- | -------------------------- |
| `absurd_tasks_total`            | Counter | Total tasks by status      |
| `absurd_tasks_current`          | Gauge   | Current tasks by status    |
| `absurd_wait_time_seconds`      | Summary | Wait time percentiles      |
| `absurd_execution_time_seconds` | Summary | Execution time percentiles |
| `absurd_throughput_per_minute`  | Gauge   | Tasks/min by window        |
| `absurd_success_rate`           | Gauge   | Success rate (0-1)         |
| `absurd_error_rate`             | Gauge   | Error rate (0-1)           |

### Log Rotation

Log rotation is configured for 14-day retention:

```bash
# Install logrotate config
sudo cp ops/logrotate.d/absurd-worker /etc/logrotate.d/

# Test rotation
sudo logrotate -d /etc/logrotate.d/absurd-worker

# Force rotation
sudo logrotate -f /etc/logrotate.d/absurd-worker
```

### Operations Documentation

For runbooks, alert configurations, and disaster recovery procedures, see:

- [Absurd Operations Guide](../workflow/absurd_quick_start.md)

## Next Steps

- **Frontend Integration**: View tasks in dashboard at
  `http://localhost:5173/absurd` (dev) or your configured production URL
- **Advanced Workflows**: Chain multiple tasks with dependency management
- **Custom Executors**: Add new task types in `absurd/adapter.py`
- **Monitoring**: Set up Grafana dashboards for metrics visualization

## References

- [Absurd Operations Guide](../workflow/absurd_quick_start.md)
- [Pipeline Stage Architecture](../architecture/pipeline/pipeline_stage_architecture.md)
- [Implementing Task Executors](workflow/streaming_converter_guide.md)
- [API Documentation](../reference/api-endpoints.md)
