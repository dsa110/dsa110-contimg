# Absurd Performance Tuning Guide

**Author:** DSA-110 Team  
**Date:** 2025-11-18  
**Status:** Production Ready

---

## Overview

This guide provides performance tuning recommendations for optimizing Absurd
workflow manager throughput, latency, and resource utilization.

---

## Key Performance Metrics

### Throughput

- **Target**: 10-20 tasks/sec sustained
- **Peak**: 50+ tasks/sec burst
- **Measured**: Tasks completed per second

### Latency

- **Spawn latency**: < 50ms (P95)
- **Claim latency**: < 100ms (P95)
- **End-to-end**: < 200ms (P95)
- **Task execution**: Depends on task type

### Resource Usage

- **CPU**: 50-70% average per worker
- **Memory**: < 500MB per worker
- **Database connections**: 5-10 per worker
- **Disk I/O**: Minimal (database only)

---

## Database Optimization

### 1. Connection Pooling

**Problem**: Too many connections saturate PostgreSQL.

**Solution**:

```python
# Configure connection pool per worker
client = AbsurdClient(
    database_url,
    pool_min_size=2,  # Minimum idle connections
    pool_max_size=10  # Maximum connections per worker
)
```

**Tuning Guide**:

- **Small workload** (< 100 tasks/hour): `pool_max_size=5`
- **Medium workload** (100-1000 tasks/hour): `pool_max_size=10`
- **Large workload** (> 1000 tasks/hour): `pool_max_size=20`

**Formula**:

```
max_connections = (num_workers * pool_max_size) + buffer(20)
```

### 2. Index Optimization

**Critical Indexes**:

```sql
-- Task claiming (priority queue)
CREATE INDEX idx_tasks_claim ON tasks(queue_name, status, priority DESC, created_at)
  WHERE status = 'pending';

-- Status filtering
CREATE INDEX idx_tasks_status ON tasks(status, queue_name, completed_at);

-- Task lookup
CREATE INDEX idx_tasks_task_id ON tasks(task_id);

-- Queue statistics
CREATE INDEX idx_tasks_queue_stats ON tasks(queue_name, status);
```

**Verify index usage**:

```sql
EXPLAIN ANALYZE
SELECT * FROM tasks
WHERE queue_name = 'dsa110-pipeline'
  AND status = 'pending'
ORDER BY priority DESC, created_at
LIMIT 10;
```

### 3. Vacuum and Maintenance

```sql
-- Auto-vacuum settings
ALTER TABLE tasks SET (
  autovacuum_vacuum_scale_factor = 0.1,
  autovacuum_analyze_scale_factor = 0.05
);

-- Manual vacuum (weekly)
VACUUM ANALYZE tasks;

-- Check bloat
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
WHERE tablename = 'tasks';
```

### 4. Archival Strategy

**Problem**: Large `tasks` table degrades performance.

**Solution**:

```sql
-- Archive completed tasks older than 30 days
CREATE TABLE tasks_archive (LIKE tasks INCLUDING ALL);

INSERT INTO tasks_archive
SELECT * FROM tasks
WHERE status IN ('completed', 'failed', 'cancelled')
  AND completed_at < NOW() - INTERVAL '30 days';

DELETE FROM tasks
WHERE status IN ('completed', 'failed', 'cancelled')
  AND completed_at < NOW() - INTERVAL '30 days';

VACUUM FULL tasks;
```

**Automated archival**:

```bash
# Cron job (daily at 2 AM)
0 2 * * * psql absurd -c "
  INSERT INTO tasks_archive SELECT * FROM tasks
  WHERE status IN ('completed', 'failed', 'cancelled')
  AND completed_at < NOW() - INTERVAL '30 days';
  DELETE FROM tasks WHERE task_id IN (SELECT task_id FROM tasks_archive);
  VACUUM ANALYZE tasks;
"
```

---

## Worker Pool Tuning

### 1. Worker Count

**Workload-based sizing**:

```bash
# CPU-bound tasks (imaging, CASA operations)
num_workers = num_cpus * 0.75

# I/O-bound tasks (database, file operations)
num_workers = num_cpus * 1.5

# Mixed workload
num_workers = num_cpus
```

**Example (16-core server)**:

```bash
# Option 1: 16 workers @ concurrency=1
for i in {1..16}; do
  python scripts/run_absurd_worker.py --concurrency 1 --worker-id w$i &
done

# Option 2: 8 workers @ concurrency=2
for i in {1..8}; do
  python scripts/run_absurd_worker.py --concurrency 2 --worker-id w$i &
done

# Option 3: 4 workers @ concurrency=4 (recommended)
for i in {1..4}; do
  python scripts/run_absurd_worker.py --concurrency 4 --worker-id w$i &
done
```

### 2. Concurrency Per Worker

**Tuning Guide**:

- **Concurrency = 1**: Safest, no task interference, lower throughput
- **Concurrency = 2-4**: Balanced, good for mixed workloads
- **Concurrency = 8+**: High throughput, risk of resource contention

**Test concurrency**:

```bash
# Benchmark different concurrency levels
for c in 1 2 4 8; do
  echo "Testing concurrency=$c"
  python scripts/benchmark_absurd.py --concurrency $c --quick
done
```

### 3. Poll Interval

**Trade-offs**:

- **Short interval (0.5s)**: Low latency, higher DB load
- **Medium interval (1.0s)**: Balanced (recommended)
- **Long interval (5.0s)**: Low DB load, higher latency

**Tuning**:

```bash
# Low-latency mode (real-time detection)
python scripts/run_absurd_worker.py --poll-interval 0.5

# Batch processing mode (archival)
python scripts/run_absurd_worker.py --poll-interval 5.0
```

### 4. Task Timeout

**Per-task-type recommendations**:

```python
timeouts = {
    "catalog-setup": 300,        # 5 minutes
    "convert-uvh5-to-ms": 900,   # 15 minutes
    "calibration-solve": 1800,   # 30 minutes
    "calibration-apply": 600,    # 10 minutes
    "imaging": 1800,             # 30 minutes
    "validation": 300,           # 5 minutes
    "crossmatch": 600,           # 10 minutes
    "photometry": 600,           # 10 minutes
}
```

**Set per-task timeout**:

```python
await client.spawn_task(
    queue_name="dsa110-pipeline",
    task_name="imaging",
    params={...},
    timeout_sec=1800  # Override default
)
```

---

## Task Execution Optimization

### 1. Pipeline Stage Performance

**Conversion (UVH5 → MS)**:

```python
# Fast conversion settings
config = {
    "writer": "parallel-subband",  # Fastest
    "stage_to_tmpfs": True,        # Use /dev/shm (3-5x speedup)
    "max_workers": 16,             # Parallel subband writes
}
```

**Calibration**:

```python
# Fast calibration settings
config = {
    "fast_mode": True,             # Binned solutions
    "solve_delay": False,          # Skip K-cal (not needed for DSA-110)
    "prebandpass_phase": True,     # Fast phase-only pre-solve
    "gain_solint": "int",          # Per-integration gains
}
```

**Imaging**:

```python
# Quick-look imaging
config = {
    "backend": "wsclean",          # Faster than tclean
    "quality_tier": "development", # Small image, fewer iterations
    "imsize": 1024,                # Smaller image
    "niter": 100,                  # Fewer iterations
    "skip_fits_export": True,      # Skip FITS conversion
}
```

### 2. Task Batching

**Problem**: Too many small tasks create overhead.

**Solution**: Batch related tasks.

```python
# Bad: 100 individual photometry tasks
for source in sources:
    await client.spawn_task("photometry", {"source": source})

# Good: 1 batch photometry task
await client.spawn_task("photometry-batch", {"sources": sources})
```

### 3. Task Dependencies

**Use priority to enforce ordering**:

```python
# High priority: Conversion (must happen first)
convert_task = await client.spawn_task(
    "convert-uvh5-to-ms", params, priority=15
)

# Medium priority: Calibration (after conversion)
cal_task = await client.spawn_task(
    "calibration-solve", params, priority=10
)

# Low priority: Imaging (after calibration)
img_task = await client.spawn_task(
    "imaging", params, priority=5
)
```

---

## Network and I/O Optimization

### 1. Database Latency

**Problem**: High database latency.

**Solutions**:

- **Co-locate database**: Run PostgreSQL on same host or LAN
- **Use SSD**: PostgreSQL data directory on SSD
- **Increase shared buffers**: `shared_buffers = 4GB` in postgresql.conf
- **Tune checkpoint settings**:
  ```ini
  checkpoint_completion_target = 0.9
  max_wal_size = 2GB
  min_wal_size = 512MB
  ```

### 2. File I/O (MS/Image Access)

**Use tmpfs for temporary files**:

```bash
# Mount tmpfs for staging
sudo mkdir -p /dev/shm/dsa110-contimg
sudo chown pipeline:pipeline /dev/shm/dsa110-contimg

# Configure pipeline to use tmpfs
export CONTIMG_TMPFS_DIR=/dev/shm/dsa110-contimg
```

**Separate HDD (slow) from SSD (fast)**:

```
/data/incoming/     # Incoming data (HDD)
/stage/ms/          # Active MS files (SSD)
/dev/shm/           # Temporary staging (tmpfs)
```

### 3. Network Bottlenecks

**Monitor network usage**:

```bash
# Check network throughput
iftop -i eth0

# Check database connection latency
psql absurd -c "SELECT NOW()" -q
```

---

## Monitoring and Profiling

### 1. Real-time Monitoring

```bash
# Dashboard monitoring
python scripts/monitor_absurd.py --interval 5

# Continuous metrics logging
python scripts/monitor_absurd.py --interval 30 >> absurd_metrics.log
```

### 2. Performance Benchmarking

```bash
# Quick benchmark (1 minute)
python scripts/benchmark_absurd.py --quick

# Full benchmark (10 minutes)
python scripts/benchmark_absurd.py

# Compare configurations
for c in 1 2 4 8; do
  python scripts/benchmark_absurd.py \
    --concurrency $c \
    --output benchmark_c${c}.json
done
```

### 3. Database Query Profiling

```sql
-- Enable slow query logging
ALTER DATABASE absurd SET log_min_duration_statement = 100;

-- Check slow queries
SELECT query, calls, mean_exec_time, max_exec_time
FROM pg_stat_statements
WHERE query LIKE '%tasks%'
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Reset stats
SELECT pg_stat_statements_reset();
```

### 4. Python Profiling

```python
import cProfile
import pstats

# Profile task execution
profiler = cProfile.Profile()
profiler.enable()

# Execute task
await execute_pipeline_task(task_name, params)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

---

## Load Testing

### 1. Synthetic Load Generation

```python
import asyncio
from dsa110_contimg.absurd import AbsurdClient

async def load_test(num_tasks=1000, rate=10):
    """Generate synthetic load."""
    client = AbsurdClient("postgresql://localhost/absurd")
    await client.connect()

    interval = 1.0 / rate  # Tasks per second

    for i in range(num_tasks):
        await client.spawn_task(
            queue_name="dsa110-pipeline",
            task_name="test-task",
            params={"index": i},
        )
        await asyncio.sleep(interval)

    await client.close()

# Run load test
asyncio.run(load_test(num_tasks=1000, rate=20))
```

### 2. Sustained Load Test

```bash
# Generate sustained load (10 tasks/sec for 1 hour)
python -c "
import asyncio
from dsa110_contimg.absurd import AbsurdClient

async def sustained_load():
    client = AbsurdClient('postgresql://localhost/absurd')
    await client.connect()

    for hour in range(1):
        for minute in range(60):
            for second in range(60):
                for _ in range(10):
                    await client.spawn_task('dsa110-pipeline', 'test', {})
                await asyncio.sleep(1)

    await client.close()

asyncio.run(sustained_load())
" &

# Monitor during load test
python scripts/monitor_absurd.py
```

---

## Troubleshooting Performance Issues

### Issue: Low Throughput

**Symptoms**: < 5 tasks/sec sustained

**Diagnosis**:

1. Check worker count: `ps aux | grep run_absurd_worker | wc -l`
2. Check database latency: `python scripts/monitor_absurd.py --once`
3. Check task execution time: Review P95 execution time

**Solutions**:

- Add more workers if CPU < 70%
- Increase concurrency if I/O-bound
- Optimize database (indexes, vacuum)

### Issue: High Latency

**Symptoms**: P95 latency > 500ms

**Diagnosis**:

1. Check database query performance
2. Check network latency
3. Check queue depth

**Solutions**:

- Reduce poll interval
- Optimize database indexes
- Add database connection pooling

### Issue: Task Timeouts

**Symptoms**: Many tasks timing out

**Diagnosis**:

1. Check actual execution times
2. Check resource contention
3. Check CASA performance

**Solutions**:

- Increase timeout for slow tasks
- Reduce concurrency to avoid contention
- Use tmpfs for faster I/O

---

## Best Practices Summary

1. ✅ **Size worker pool appropriately**: 0.75-1.5x CPU cores
2. ✅ **Use connection pooling**: 5-10 connections per worker
3. ✅ **Archive old tasks**: Keep last 30 days only
4. ✅ **Monitor continuously**: Use `monitor_absurd.py`
5. ✅ **Benchmark regularly**: Test after configuration changes
6. ✅ **Optimize database**: Create indexes, vacuum regularly
7. ✅ **Use tmpfs**: Stage conversion in `/dev/shm` for 3-5x speedup
8. ✅ **Set appropriate timeouts**: Per-task-type timeouts
9. ✅ **Profile slow tasks**: Use cProfile to identify bottlenecks
10. ✅ **Load test before production**: Validate under realistic load

---

## Performance Targets

| Metric         | Development | Production   | High-Performance |
| -------------- | ----------- | ------------ | ---------------- |
| Throughput     | 5 tasks/sec | 15 tasks/sec | 30 tasks/sec     |
| P50 Latency    | < 100ms     | < 50ms       | < 20ms           |
| P95 Latency    | < 500ms     | < 200ms      | < 100ms          |
| Queue Depth    | < 100       | < 50         | < 20             |
| Worker Count   | 1-2         | 4-8          | 8-16             |
| DB Connections | 5-10        | 20-40        | 40-80            |
| Success Rate   | > 95%       | > 99%        | > 99.9%          |

---

## Changelog

| Date       | Version | Changes                          |
| ---------- | ------- | -------------------------------- |
| 2025-11-18 | 1.0     | Initial performance tuning guide |
