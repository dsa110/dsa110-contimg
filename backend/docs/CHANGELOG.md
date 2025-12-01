# Development Changelog

This document tracks all major architectural improvements, enhancements, and
milestones for the DSA-110 backend.

---

## December 1, 2025 - ABSURD Workflow Manager Activated

### ABSURD Task Queue System ✅

PostgreSQL-backed durable task queue fully activated for pipeline processing:

- **Schema initialized**: 3 tables (tasks, workflows, scheduled_tasks), 11 functions
- **Worker running**: 4 concurrent task slots, 1-second poll interval
- **Dead Letter Queue**: Enabled for failed task handling
- **Entry points created**: `python -m dsa110_contimg.absurd` and `scheduler`

**Components Implemented**:

| Component       | Purpose                         | Status    |
| --------------- | ------------------------------- | --------- |
| AbsurdClient    | Database operations, task spawn | ✅ Active |
| AbsurdWorker    | Task execution loop             | ✅ Active |
| AbsurdConfig    | Environment configuration       | ✅ Active |
| TaskScheduler   | Cron-like scheduling            | ✅ Ready  |
| Pipeline Chains | DAG task dependencies           | ✅ Ready  |

**Files Created**:

```
src/dsa110_contimg/absurd/
├── __main__.py          # Worker entry point
├── scheduler_main.py    # Scheduler entry point
├── setup.py             # Database initialization
└── README.md            # API documentation

docs/ops/
└── absurd-service-activation.md  # Full activation guide

ops/systemd/
├── absurd-worker.service    # Systemd unit file
└── absurd-scheduler.service # Systemd unit file
```

**Configuration Added** (`.env`):

```bash
ABSURD_ENABLED=true
ABSURD_DATABASE_URL=postgresql://dsa110:***@localhost:5432/dsa110
ABSURD_QUEUE_NAME=dsa110-pipeline
ABSURD_WORKER_CONCURRENCY=4
ABSURD_DLQ_ENABLED=true
```

See [ABSURD Activation Guide](./ops/absurd-service-activation.md) for full
documentation.

---

## November 30, 2025 - Major Refactoring Complete

### Async Migration ✅

All API routes migrated to use async repositories and services:

- **Routes migrated**: 11 files (images, sources, jobs, ms, qa, cal, stats,
  logs, queue, cache, services)
- **Async services created**: AsyncImageService, AsyncSourceService,
  AsyncJobService, AsyncMSService
- **Tests passing**: 782 tests
- **Coverage**: 72%

**Performance Results**:

| Metric         | Result  | Notes                         |
| -------------- | ------- | ----------------------------- |
| CPU-bound      | +26%    | Health endpoint               |
| Database-heavy | -5-11%  | aiosqlite overhead (expected) |
| P99 Latencies  | +10-33% | More consistent under load    |

### Enhancements Completed

1. **Narrow Exception Handling** - 46 handlers across 15 files narrowed from
   broad `except Exception` to specific types

2. **FITS Parsing Service Tests** - 20 tests added for `fits_service.py`

3. **Transaction Management** - 4 async context managers with proper
   commit/rollback, 12 tests

4. **Database Migrations CLI** - `scripts/ops/migrate.py` for Alembic operations

5. **PostgreSQL Migration Prep** - `db_adapters/` package with:

   - DatabaseBackend Protocol
   - SQLiteAdapter and PostgreSQLAdapter
   - QueryBuilder for cross-database queries
   - 58 tests

6. **TimeoutConfig Centralization** - All hardcoded timeouts moved to
   `config.py`:

   ```python
   @dataclass
   class TimeoutConfig:
       db_connection: float = 30.0
       websocket_ping: float = 30.0
       health_check: float = 2.0
       redis_socket: float = 2.0
   ```

7. **Batch Module Tests** - 105 tests for `batch/jobs.py`, `batch/qa.py`,
   `batch/thumbnails.py`

8. **Services Monitor Tests** - 41 tests for `services_monitor.py` (0% → 96%
   coverage)

9. **Deprecated Routes Removed** - Legacy `routes.py` (1339 lines) deleted

10. **Pipeline Rerun Implementation** - `job_queue.py` rerun logic fully
    implemented with:
    - Job config loading from database
    - Config override support
    - PIPELINE_CMD_TEMPLATE subprocess execution
    - Database job tracking
    - Error handling and status updates

### Architecture Improvements

1. **Routes Module Split** - Single 1320-line `routes.py` split into 13 focused
   modules under `routes/`

2. **Service Layer** - Business logic extracted to `services/` package

3. **Dependency Injection** - FastAPI `Depends()` factories in `dependencies.py`

4. **Repository Interfaces** - Protocol-based interfaces in `interfaces.py`

5. **Database Module** - `DatabasePool` class for connection management

6. **Configuration Centralization** - All paths from environment variables

7. **Batch Jobs Split** - 782-line `batch_jobs.py` split into `batch/` package

8. **Custom Exceptions** - Full exception hierarchy in `exceptions.py`

### Files Created

```
src/dsa110_contimg/api/
├── db_adapters/
│   ├── __init__.py
│   ├── backend.py
│   ├── query_builder.py
│   └── adapters/
│       ├── sqlite_adapter.py
│       └── postgresql_adapter.py
├── services/
│   └── async_services.py
├── batch/
│   ├── jobs.py
│   ├── qa.py
│   └── thumbnails.py
└── routes/
    ├── images.py
    ├── sources.py
    ├── jobs.py
    ├── ms.py
    ├── qa.py
    ├── cal.py
    ├── stats.py
    ├── logs.py
    ├── queue.py
    ├── cache.py
    └── services.py

tests/unit/
├── test_batch_jobs.py       # 49 tests
├── test_batch_qa.py         # 27 tests
├── test_batch_thumbnails.py # 29 tests
├── test_services_monitor.py # 41 tests
├── test_db_adapters.py      # 58 tests
└── test_transactions.py     # 12 tests

scripts/ops/
└── migrate.py               # Alembic CLI wrapper
```

### Files Removed

- `src/dsa110_contimg/api/routes.py` (1339 lines, deprecated)

---

## Test Coverage Summary

| Module                | Coverage | Tests   |
| --------------------- | -------- | ------- |
| `batch/jobs.py`       | 96%      | 49      |
| `batch/qa.py`         | 41%      | 27      |
| `batch/thumbnails.py` | 53%      | 29      |
| `services_monitor.py` | 96%      | 41      |
| `db_adapters/`        | 89-100%  | 58      |
| `config.py`           | 82%      | 15      |
| `schemas.py`          | 100%     | 12      |
| `dependencies.py`     | 100%     | -       |
| `errors.py`           | 100%     | -       |
| `interfaces.py`       | 100%     | -       |
| **Total**             | **72%**  | **782** |

---

## Backwards Compatibility

- Old import paths maintained via re-exports where needed
- Deprecation warnings guide migration to new imports
- All existing tests continue to pass
