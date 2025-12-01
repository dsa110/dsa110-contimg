# ABSURD Service Activation Guide

**Document Version:** 1.0  
**Last Updated:** 2025-12-01  
**Prerequisites:** ABSURD deployment completed (see `docs/changelog/2025-12-01-absurd-deployment.md`)

---

## Overview

This guide covers enabling the ABSURD workflow manager services for production use.
The deployment is complete - this document covers only the final activation step.

## Current State

| Component | Status | Location |
|-----------|--------|----------|
| PostgreSQL database | ✅ Running | `dsa110_absurd` on port 5433 |
| Schema & procedures | ✅ Applied | `absurd` schema with stored functions |
| Backend API | ✅ Running | `/absurd/*` endpoints on port 8787 |
| Frontend code | ✅ Deployed | `/workflows` route ready |
| Worker service files | ✅ Created | `ops/systemd/` (not yet enabled) |

## Pre-Activation Checklist

Before enabling services, verify the infrastructure is ready:

```bash
# 1. Verify PostgreSQL is running
pg_isready -h /var/run/postgresql -p 5433
# Expected: /var/run/postgresql:5433 - accepting connections

# 2. Verify database exists
psql -h /var/run/postgresql -p 5433 -d dsa110_absurd -c "SELECT 1;"
# Expected: Returns 1 row

# 3. Verify schema is applied
psql -h /var/run/postgresql -p 5433 -d dsa110_absurd \
  -c "SELECT routine_name FROM information_schema.routines WHERE routine_schema = 'absurd';"
# Expected: spawn_task, claim_task, complete_task, fail_task, heartbeat_task

# 4. Verify API is responding
curl -s http://localhost:8787/absurd/health | jq .status
# Expected: "healthy" or "degraded" (not an error)

# 5. Verify service files exist
ls -la /data/dsa110-contimg/ops/systemd/contimg-absurd-worker.service
ls -la /data/dsa110-contimg/ops/systemd/absurd-cleanup.service
ls -la /data/dsa110-contimg/ops/systemd/absurd-cleanup.timer
# Expected: All files exist
```

## Activation Steps

### Step 1: Copy Service Files to Systemd

```bash
sudo cp /data/dsa110-contimg/ops/systemd/contimg-absurd-worker.service /etc/systemd/system/
sudo cp /data/dsa110-contimg/ops/systemd/absurd-cleanup.service /etc/systemd/system/
sudo cp /data/dsa110-contimg/ops/systemd/absurd-cleanup.timer /etc/systemd/system/
```

### Step 2: Verify Environment File

The worker reads configuration from `/data/dsa110-contimg/ops/systemd/contimg.env`.
Verify it contains the correct database URL:

```bash
grep ABSURD /data/dsa110-contimg/ops/systemd/contimg.env
```

Expected output:
```
ABSURD_DATABASE_URL=postgresql:///dsa110_absurd?host=/var/run/postgresql&port=5433
ABSURD_QUEUE_NAME=dsa110-pipeline
ABSURD_ENABLED=true
```

If missing, add:
```bash
cat >> /data/dsa110-contimg/ops/systemd/contimg.env << 'ENVEOF'
ABSURD_DATABASE_URL=postgresql:///dsa110_absurd?host=/var/run/postgresql&port=5433
ABSURD_QUEUE_NAME=dsa110-pipeline
ABSURD_ENABLED=true
ENVEOF
```

### Step 3: Reload Systemd and Enable Services

```bash
# Reload systemd to pick up new service files
sudo systemctl daemon-reload

# Enable and start the worker service
sudo systemctl enable contimg-absurd-worker.service
sudo systemctl start contimg-absurd-worker.service

# Enable and start the cleanup timer
sudo systemctl enable absurd-cleanup.timer
sudo systemctl start absurd-cleanup.timer
```

### Step 4: Verify Services Are Running

```bash
# Check worker status
sudo systemctl status contimg-absurd-worker.service

# Check timer status
sudo systemctl status absurd-cleanup.timer

# View worker logs
sudo journalctl -u contimg-absurd-worker.service -f --no-pager -n 50
```

Expected worker output:
```
Starting Absurd worker lxd110h17-XXXXXXXX on queue dsa110-pipeline
Connected to Absurd database
```

## Post-Activation Verification

### Test Task Execution

Run the test script to verify end-to-end functionality:

```bash
cd /data/dsa110-contimg/backend
conda activate casa6
export ABSURD_DATABASE_URL="postgresql:///dsa110_absurd?host=/var/run/postgresql&port=5433"
python scripts/testing/test_absurd_worker.py
```

Expected output:
```
✅ Worker test PASSED!
```

### Verify via API

```bash
# Check queue stats
curl -s http://localhost:8787/absurd/queues/dsa110-pipeline/stats | jq

# Check workers
curl -s http://localhost:8787/absurd/workers | jq '.workers | length'
# Expected: 1 or more workers
```

### Verify via Frontend

1. Open browser to `http://<host>:3000/workflows` (or production URL)
2. Verify "System Health" shows status "healthy"
3. Verify "Queue: dsa110-pipeline" shows statistics
4. Verify "Workers" section shows at least one active worker

## Troubleshooting

### Worker Won't Start

**Check logs:**
```bash
sudo journalctl -u contimg-absurd-worker.service -n 100 --no-pager
```

**Common issues:**

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection refused` | PostgreSQL not running | `sudo systemctl start postgresql@16-absurd` |
| `database "dsa110_absurd" does not exist` | DB not created | See database setup in deployment plan |
| `role "ubuntu" does not exist` | Missing DB user | `createuser -h /var/run/postgresql -p 5433 ubuntu` |
| `ABSURD_DATABASE_URL not set` | Missing env var | Check `contimg.env` file |

### Worker Starts But No Tasks Process

**Check task status:**
```bash
psql -h /var/run/postgresql -p 5433 -d dsa110_absurd \
  -c "SELECT status, COUNT(*) FROM absurd.tasks GROUP BY status;"
```

**Check for stale claims:**
```bash
psql -h /var/run/postgresql -p 5433 -d dsa110_absurd \
  -c "SELECT * FROM absurd.tasks WHERE status = 'claimed' AND claimed_at < NOW() - INTERVAL '10 minutes';"
```

**Reset stale tasks:**
```bash
psql -h /var/run/postgresql -p 5433 -d dsa110_absurd \
  -c "UPDATE absurd.tasks SET status = 'pending', worker_id = NULL, claimed_at = NULL WHERE status = 'claimed' AND claimed_at < NOW() - INTERVAL '10 minutes';"
```

### Cleanup Timer Not Running

```bash
# Check timer status
systemctl list-timers | grep absurd

# Manually trigger cleanup
sudo systemctl start absurd-cleanup.service
```

## Scaling Workers

To run multiple workers, use the template service:

```bash
# Copy template (if not already done)
sudo cp /data/dsa110-contimg/ops/systemd/contimg-absurd-worker@.service /etc/systemd/system/
sudo systemctl daemon-reload

# Start 3 worker instances
sudo systemctl enable --now contimg-absurd-worker@1.service
sudo systemctl enable --now contimg-absurd-worker@2.service
sudo systemctl enable --now contimg-absurd-worker@3.service

# Check all instances
systemctl list-units 'contimg-absurd-worker@*'
```

## Stopping Services

```bash
# Stop worker (gracefully finishes current task)
sudo systemctl stop contimg-absurd-worker.service

# Disable services (won't start on boot)
sudo systemctl disable contimg-absurd-worker.service
sudo systemctl disable absurd-cleanup.timer
```

## Service File Locations

| File | Purpose |
|------|---------|
| `/etc/systemd/system/contimg-absurd-worker.service` | Main worker service |
| `/etc/systemd/system/contimg-absurd-worker@.service` | Multi-worker template |
| `/etc/systemd/system/absurd-cleanup.service` | Recovery cleanup oneshot |
| `/etc/systemd/system/absurd-cleanup.timer` | Daily cleanup trigger |
| `/data/dsa110-contimg/ops/systemd/contimg.env` | Environment variables |

## Related Documentation

- [Deployment Changelog](../changelog/2025-12-01-absurd-deployment.md) - What was deployed
- [Deployment Plan](../guides/absurd-deployment-plan.md) - Full technical details
- [ABSURD Quickstart](../guides/ABSURD_QUICKSTART.md) - API usage examples

## Contact

If issues persist after following this guide, check:
1. The deployment changelog for any known issues
2. Worker logs via `journalctl`
3. Database state via `psql`
