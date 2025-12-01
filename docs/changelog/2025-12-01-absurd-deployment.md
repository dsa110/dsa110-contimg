# ABSURD Workflow Manager Deployment

**Date:** 2025-12-01  
**Author:** AI Assistant (Copilot)  
**Status:** Deployed (services pending activation)

---

## Summary

Deployed the ABSURD durable workflow/task queue manager with full backend 
infrastructure, frontend integration, and systemd service definitions.

## Changes

### Phase 1: Backend Infrastructure ✅

**Migrated ABSURD Module:**
- Copied 10 core files from `legacy.backend/` to `backend/src/dsa110_contimg/absurd/`:
  - `config.py` - Configuration dataclass
  - `schema.sql` - PostgreSQL schema with stored procedures  
  - `client.py` - Async PostgreSQL client (asyncpg)
  - `worker.py` - Task executor with WebSocket events
  - `scheduling.py` - Cron scheduling support
  - `dependencies.py` - Workflow DAG management
  - `monitoring.py` - Prometheus metrics
  - `adapter.py` - Pipeline stage executors
  - `__init__.py` - Package exports

**Database Setup:**
- PostgreSQL database: `dsa110_absurd` on port 5433
- Schema: `absurd` with `tasks` table and stored procedures
- Connection: Unix socket at `/var/run/postgresql`

**Bug Fixes:**
- Fixed ambiguous column reference in `claim_task()` stored procedure
  - Changed `ORDER BY priority DESC` to use table aliases
  - Renamed return column from `priority` to `task_priority`
  - Updated client.py to use new column name

**API Integration:**
- Registered `absurd_router` in FastAPI app (`api/app.py`)
- Added lifecycle hooks for client initialization/shutdown
- Fixed websocket import path in router
- 33 ABSURD endpoints available at `/absurd/*`

### Phase 2: Frontend Integration ✅

**TypeScript Types (`frontend/src/types/absurd.ts`):**
- Task, TaskStatus, TaskListResponse
- QueueStats, Worker, WorkerState, WorkerListResponse, WorkerMetrics
- AbsurdMetrics, AbsurdHealth, Alert, AlertLevel
- Workflow, WorkflowStatus, WorkflowDetail, WorkflowTask
- SpawnTaskRequest, SpawnWorkflowRequest, CancelTaskRequest

**API Client (`frontend/src/api/absurd.ts`):**
- Task operations: spawnTask, getTask, listTasks, cancelTask, retryTask
- Queue operations: getQueueStats, listQueues
- Worker operations: listWorkers, getWorker, getWorkerMetrics
- Metrics/Health: getMetrics, getHealth
- Workflow operations: spawnWorkflow, getWorkflow, listWorkflows, cancelWorkflow
- DLQ operations: listDeadLetterTasks, replayDeadLetterTask, purgeDeadLetterQueue
- Utility: pruneTasks

**React Query Hooks (`frontend/src/hooks/useAbsurdQueries.ts`):**
- Query keys for cache invalidation
- useTasks, useTask, useSpawnTask, useCancelTask, useRetryTask
- useQueues, useQueueStats
- useWorkers, useWorker, useWorkerMetrics
- useAbsurdMetrics, useAbsurdHealth
- useWorkflows, useWorkflow, useSpawnWorkflow, useCancelWorkflow
- useDeadLetterTasks, useReplayDeadLetterTask
- usePruneTasks

**Dashboard Page (`frontend/src/pages/WorkflowsPage.tsx`):**
- HealthSection - System health status with alerts
- QueueStatsSection - Pending/processing/completed/failed counts
- WorkersSection - Worker list with state and uptime
- TasksSection - Task list with cancel/retry actions

**Navigation:**
- Added `/workflows` route to `router.tsx`
- Added "Workflows" to `NAV_ITEMS` in `constants/routes.ts`

### Phase 3: Worker Deployment ✅

**Systemd Service Files:**
- `ops/systemd/contimg-absurd-worker.service` - Single worker service
- `ops/systemd/contimg-absurd-worker@.service` - Multi-worker template
- `ops/systemd/absurd-cleanup.service` - Recovery file cleanup
- `ops/systemd/absurd-cleanup.timer` - Daily cleanup timer

**Test Script:**
- `scripts/testing/test_absurd_worker.py` - Worker validation test
- Spawns task, runs worker, verifies completion
- Test passed successfully

## Files Created

```
backend/src/dsa110_contimg/absurd/
├── __init__.py
├── adapter.py
├── client.py
├── config.py
├── dependencies.py
├── monitoring.py
├── scheduling.py
├── schema.sql
└── worker.py

frontend/src/
├── api/absurd.ts
├── hooks/useAbsurdQueries.ts
├── pages/WorkflowsPage.tsx
└── types/absurd.ts

ops/systemd/
├── absurd-cleanup.service
├── absurd-cleanup.timer
├── contimg-absurd-worker.service
└── contimg-absurd-worker@.service

scripts/testing/
└── test_absurd_worker.py
```

## Files Modified

- `backend/src/dsa110_contimg/api/app.py` - Router registration + lifecycle hooks
- `backend/src/dsa110_contimg/api/routes/absurd.py` - Fixed websocket import
- `frontend/src/router.tsx` - Added WorkflowsPage route
- `frontend/src/constants/routes.ts` - Added WORKFLOWS routes and nav item
- `frontend/src/hooks/index.ts` - Export ABSURD hooks
- `frontend/src/types/index.ts` - Export ABSURD types
- `ops/systemd/contimg.env` - Updated ABSURD_DATABASE_URL

## Pending

**Enable Services (when ready):**
```bash
# Copy service files
sudo cp /data/dsa110-contimg/ops/systemd/contimg-absurd-worker.service /etc/systemd/system/
sudo cp /data/dsa110-contimg/ops/systemd/absurd-cleanup.* /etc/systemd/system/

# Reload and enable
sudo systemctl daemon-reload
sudo systemctl enable --now contimg-absurd-worker.service
sudo systemctl enable --now absurd-cleanup.timer

# Verify
sudo systemctl status contimg-absurd-worker.service
```

## Verification

**Backend API:**
```bash
curl http://localhost:8787/absurd/health
curl http://localhost:8787/absurd/queues/dsa110-pipeline/stats
```

**Worker Test:**
```bash
cd /data/dsa110-contimg/backend
conda activate casa6
export ABSURD_DATABASE_URL="postgresql:///dsa110_absurd?host=/var/run/postgresql&port=5433"
python scripts/testing/test_absurd_worker.py
```

## Related Documents

- [ABSURD Deployment Plan](./absurd-deployment-plan.md) - Full deployment plan with appendices
- [ABSURD Quickstart](./ABSURD_QUICKSTART.md) - Getting started guide
