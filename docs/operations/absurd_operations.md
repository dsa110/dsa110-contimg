# Absurd Worker Operations Guide

**Status:** ✅ Authoritative Reference  
**Last Updated:** November 26, 2025

Complete operations guide for the Absurd durable workflow worker in the DSA-110
continuum imaging pipeline.

> **Note:** This is the canonical Absurd operations documentation. Other guides
> in `docs/guides/workflow/` provide supplementary information for specific use
> cases.

## Overview

The Absurd worker is a PostgreSQL-backed durable task execution system that
provides:

- **Fault-tolerant execution**: Tasks survive crashes and restarts
- **Automatic retries**: Configurable retry policies with exponential backoff
- **Priority queuing**: High-priority tasks (calibrators) run first
- **Real-time monitoring**: WebSocket events and Prometheus metrics
- **Dead letter queue**: Failed operations tracked for manual intervention

## Quick Reference

### Service Management

```bash
# Start worker
sudo systemctl start contimg-absurd-worker

# Stop worker
sudo systemctl stop contimg-absurd-worker

# Restart worker
sudo systemctl restart contimg-absurd-worker


# Check status
sudo systemctl status contimg-absurd-worker

# View logs (follow mode)
sudo journalctl -u contimg-absurd-worker -f

# View recent logs
sudo journalctl -u contimg-absurd-worker --since "1 hour ago"
```

### Health Checks

```bash
# Run full health check
/data/dsa110-contimg/ops/scripts/health_check_absurd.sh

# JSON output (for monitoring systems)
/data/dsa110-contimg/ops/scripts/health_check_absurd.sh --json

# Quick API health check
curl http://localhost:8000/api/absurd/health
```

### Queue Statistics

```bash
# Via API
curl http://localhost:8000/api/absurd/queues/dsa110-pipeline/stats

# Via Python
python -c "
import asyncio
from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig

async def stats():
    config = AbsurdConfig.from_env()
    async with AbsurdClient(config.database_url) as client:
        stats = await client.get_queue_stats(config.queue_name)
        print(stats)

asyncio.run(stats())
"
```

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                     Production Environment                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Streaming  │───▶│    Absurd    │◀───│     API      │       │
│  │  Converter   │    │    Worker    │    │   (FastAPI)  │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                   │                │
│         │                   ▼                   │                │
│         │           ┌──────────────┐            │                │
│         └──────────▶│  PostgreSQL  │◀───────────┘                │
│                     │  (Absurd DB) │                             │
│                     └──────────────┘                             │
│                            │                                     │
│                            ▼                                     │
│                     ┌──────────────┐                             │
│                     │   Metrics    │──────▶ Prometheus           │
│                     │   Endpoint   │                             │
│                     └──────────────┘                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Configuration

### Environment Variables

Located in `/data/dsa110-contimg/ops/systemd/contimg.env`:

| Variable                      | Default           | Description                  |
| ----------------------------- | ----------------- | ---------------------------- |
| `ABSURD_ENABLED`              | `true`            | Enable Absurd integration    |
| `ABSURD_DATABASE_URL`         | (required)        | PostgreSQL connection string |
| `ABSURD_QUEUE_NAME`           | `dsa110-pipeline` | Default queue name           |
| `ABSURD_WORKER_CONCURRENCY`   | `4`               | Concurrent task execution    |
| `ABSURD_WORKER_POLL_INTERVAL` | `1.0`             | Poll interval in seconds     |
| `ABSURD_TASK_TIMEOUT_SEC`     | `3600`            | Task timeout (1 hour)        |
| `ABSURD_MAX_RETRIES`          | `3`               | Max retry attempts           |

### Tuning Concurrency

```bash
# For high-throughput (16+ CPU cores, 64+ GB RAM)
ABSURD_WORKER_CONCURRENCY=8

# For standard operation (8 cores, 32 GB RAM)
ABSURD_WORKER_CONCURRENCY=4

# For resource-constrained systems
ABSURD_WORKER_CONCURRENCY=2
```

## Monitoring

### Prometheus Integration

Metrics endpoint: `http://localhost:8000/api/absurd/metrics/prometheus`

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
| `absurd_wait_time_seconds`      | Summary | Task wait time percentiles |
| `absurd_execution_time_seconds` | Summary | Execution time percentiles |
| `absurd_throughput_per_minute`  | Gauge   | Tasks completed per minute |
| `absurd_success_rate`           | Gauge   | Success rate (0-1)         |
| `absurd_error_rate`             | Gauge   | Error rate (0-1)           |

### Grafana Dashboard

Import the provided dashboard from
`/docs/operations/grafana/absurd_dashboard.json` or use these queries:

```promql
# Queue depth
absurd_tasks_current{status="pending"}

# Throughput (5-minute average)
absurd_throughput_per_minute{window="5m"}

# Error rate trend
rate(absurd_tasks_total{status="failed"}[5m])

# P95 execution time
absurd_execution_time_seconds{quantile="0.95"}
```

### Alert Rules

Recommended Prometheus alert rules:

```yaml
groups:
  - name: absurd
    rules:
      # High queue backlog
      - alert: AbsurdQueueBacklog
        expr: absurd_tasks_current{status="pending"} > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Absurd queue backlog is high"
          description: "{{ $value }} tasks pending for more than 5 minutes"

      # High error rate
      - alert: AbsurdHighErrorRate
        expr: absurd_error_rate{window="5m"} > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Absurd error rate is high"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # Worker not processing
      - alert: AbsurdWorkerStalled
        expr:
          absurd_throughput_per_minute{window="15m"} == 0 and
          absurd_tasks_current{status="pending"} > 0
        for: 15m
        labels:
          severity: critical
        annotations:
          summary: "Absurd worker appears stalled"
          description: "No tasks processed in 15 minutes with pending work"

      # Slow execution time
      - alert: AbsurdSlowExecution
        expr: absurd_execution_time_seconds{quantile="0.95"} > 1800
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Absurd tasks are executing slowly"
          description: "P95 execution time is {{ $value | humanizeDuration }}"
```

## Runbooks

### Runbook: Worker Not Starting

**Symptoms**: Service fails to start, exits immediately

**Investigation:**

```bash
# Check service status
sudo systemctl status contimg-absurd-worker

# Check recent logs
sudo journalctl -u contimg-absurd-worker -n 100

# Verify database connectivity
psql "${ABSURD_DATABASE_URL}" -c "SELECT 1"

# Check environment file
cat /data/dsa110-contimg/ops/systemd/contimg.env | grep ABSURD
```

**Common causes:**

1. **Database unreachable**: Verify PostgreSQL is running
2. **Invalid credentials**: Check `ABSURD_DATABASE_URL`
3. **Schema not installed**: Run `./scripts/absurd/setup_absurd_db.sh`
4. **Python environment issues**: Verify `casa6` environment

**Resolution:**

```bash
# Restart PostgreSQL
sudo systemctl restart postgresql

# Reinstall schema
cd /data/dsa110-contimg
./scripts/absurd/setup_absurd_db.sh

# Restart worker
sudo systemctl restart contimg-absurd-worker
```

### Runbook: High Queue Backlog

**Symptoms**: Large number of pending tasks, slow throughput

**Investigation:**

```bash
# Check queue stats
curl http://localhost:8000/api/absurd/queues/dsa110-pipeline/stats

# Check worker is running
sudo systemctl status contimg-absurd-worker

# Check for stuck tasks
psql "${ABSURD_DATABASE_URL}" -c "
SELECT task_id, task_name, claimed_at,
       NOW() - claimed_at AS claimed_duration
FROM absurd.t_tasks
WHERE status = 'claimed'
ORDER BY claimed_at
LIMIT 10;
"
```

**Common causes:**

1. **Insufficient concurrency**: Increase `ABSURD_WORKER_CONCURRENCY`
2. **Slow tasks**: Check if individual tasks are timing out
3. **External bottlenecks**: Disk I/O, memory, network

**Resolution:**

```bash
# Increase concurrency (if resources allow)
sed -i 's/ABSURD_WORKER_CONCURRENCY=4/ABSURD_WORKER_CONCURRENCY=8/' \
    /data/dsa110-contimg/ops/systemd/contimg.env
sudo systemctl restart contimg-absurd-worker

# Or add another worker instance
sudo systemctl start contimg-absurd-worker@2.service
```

### Runbook: High Failure Rate

**Symptoms**: Many tasks failing, error rate > 10%

**Investigation:**

```bash
# Check failed tasks
psql "${ABSURD_DATABASE_URL}" -c "
SELECT task_id, task_name, error, created_at
FROM absurd.t_tasks
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 20;
"

# Check DLQ
curl http://localhost:8000/api/dlq/stats

# Check worker logs for exceptions
grep -i "exception\|error\|traceback" \
    /data/dsa110-contimg/state/logs/absurd-worker.err | tail -50
```

**Common causes:**

1. **Invalid input data**: Corrupted HDF5 files, missing subbands
2. **Resource exhaustion**: Disk full, memory exhausted
3. **External service failures**: CASA crashes, database issues
4. **Configuration errors**: Invalid paths, permissions

**Resolution:**

```bash
# Check disk space
df -h /data /stage

# Clear scratch directory
rm -rf /stage/dsa110-contimg/tmp/*

# Retry failed tasks via DLQ
curl -X POST http://localhost:8000/api/dlq/items/retry-all \
    -H "Content-Type: application/json" \
    -d '{"resubmit_to_absurd": true}'
```

### Runbook: Database Connection Lost

**Symptoms**: Worker crashes with connection errors

**Investigation:**

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check connection
psql "${ABSURD_DATABASE_URL}" -c "SELECT 1"

# Check for max connection issues
psql "${ABSURD_DATABASE_URL}" -c "
SELECT count(*) FROM pg_stat_activity
WHERE datname = 'dsa110_absurd';
"
```

**Resolution:**

```bash
# Restart PostgreSQL
sudo systemctl restart postgresql

# Restart worker (will reconnect automatically)
sudo systemctl restart contimg-absurd-worker
```

### Runbook: Task Timeout

**Symptoms**: Tasks stuck in "claimed" state, eventual timeout

**Investigation:**

```bash
# Find long-running tasks
psql "${ABSURD_DATABASE_URL}" -c "
SELECT task_id, task_name, claimed_at,
       EXTRACT(EPOCH FROM (NOW() - claimed_at)) AS seconds_running
FROM absurd.t_tasks
WHERE status = 'claimed'
AND claimed_at < NOW() - INTERVAL '30 minutes'
ORDER BY claimed_at;
"

# Check what worker is doing
ps aux | grep python | grep absurd

# Check system resources
htop
```

**Common causes:**

1. **CASA hanging**: wsclean or tclean stuck
2. **I/O bottleneck**: Slow disk read/write
3. **Memory pressure**: OOM killer, swap thrashing

**Resolution:**

```bash
# Kill stuck CASA processes
pkill -f wsclean
pkill -f tclean

# Restart worker (will retry timed-out tasks)
sudo systemctl restart contimg-absurd-worker

# Increase timeout if tasks legitimately need more time
sed -i 's/ABSURD_TASK_TIMEOUT_SEC=3600/ABSURD_TASK_TIMEOUT_SEC=7200/' \
    /data/dsa110-contimg/ops/systemd/contimg.env
sudo systemctl restart contimg-absurd-worker
```

## Maintenance

### Daily Tasks

```bash
# Check service status
sudo systemctl status contimg-absurd-worker

# Review queue statistics
curl http://localhost:8000/api/absurd/queues/dsa110-pipeline/stats

# Check for failed tasks
curl "http://localhost:8000/api/absurd/tasks?status=failed&limit=10"
```

### Weekly Tasks

```bash
# Check DLQ for accumulated failures
curl http://localhost:8000/api/dlq/stats

# Review error logs
grep -c "ERROR\|EXCEPTION" /data/dsa110-contimg/state/logs/absurd-worker.err

# Vacuum Absurd tables
psql "${ABSURD_DATABASE_URL}" -c "VACUUM ANALYZE absurd.t_tasks;"
```

### Monthly Tasks

```bash
# Archive old completed tasks
psql "${ABSURD_DATABASE_URL}" -c "
DELETE FROM absurd.t_tasks
WHERE status = 'completed'
AND completed_at < NOW() - INTERVAL '30 days';
"

# Review and rotate logs
sudo logrotate -f /etc/logrotate.d/absurd-worker

# Check disk space trends
du -sh /data/dsa110-contimg/state/logs/
```

## Disaster Recovery

### Complete Worker Failure

If the worker fails completely and cannot be restarted:

```bash
# 1. Stop the service
sudo systemctl stop contimg-absurd-worker

# 2. Check database integrity
psql "${ABSURD_DATABASE_URL}" -c "
SELECT status, COUNT(*) FROM absurd.t_tasks GROUP BY status;
"

# 3. Reset stuck tasks to pending
psql "${ABSURD_DATABASE_URL}" -c "
UPDATE absurd.t_tasks
SET status = 'pending', claimed_at = NULL, worker_id = NULL
WHERE status = 'claimed';
"

# 4. Restart worker
sudo systemctl start contimg-absurd-worker
```

### Database Recovery

If the Absurd database becomes corrupted:

```bash
# 1. Stop all workers
sudo systemctl stop contimg-absurd-worker

# 2. Backup current state
pg_dump dsa110_absurd > /tmp/absurd_backup_$(date +%Y%m%d).sql

# 3. Reinstall schema (preserves data)
cd /data/dsa110-contimg
./scripts/absurd/setup_absurd_db.sh --repair

# 4. Verify integrity
psql "${ABSURD_DATABASE_URL}" -c "SELECT COUNT(*) FROM absurd.t_tasks;"

# 5. Restart workers
sudo systemctl start contimg-absurd-worker
```

## Security Considerations

1. **Database credentials**: Store `ABSURD_DATABASE_URL` securely, not in
   version control
2. **Network isolation**: Keep PostgreSQL on internal network only
3. **Log rotation**: Ensure logs don't accumulate sensitive data
4. **API access**: Consider API authentication for production

## References

- [Absurd Quickstart Guide](../guides/ABSURD_QUICKSTART.md)
- [API Endpoints Reference](../reference/api-endpoints.md)
- [Pipeline Architecture](../architecture/pipeline/pipeline_stage_architecture.md)
- Troubleshooting Guide
