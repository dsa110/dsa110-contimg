# Backend TODO

## Completed ✅

- [x] Async migration (all routes use async repositories/services)
- [x] Narrow exception handling (46 handlers across 15 files)
- [x] FITS parsing service tests (20 tests)
- [x] Transaction management (4 context managers, 12 tests)
- [x] Database migrations CLI (`scripts/ops/migrate.py`)
- [x] PostgreSQL migration prep (`db_adapters/` package, 58 tests)
- [x] TimeoutConfig centralization
- [x] Batch module tests (105 tests)
- [x] Services monitor tests (41 tests)
- [x] Remove deprecated routes.py
- [x] Implement job_queue pipeline rerun logic
- [x] **Remove Legacy errors.py** - Deleted api/errors.py and consolidated to
      exceptions.py
- [x] **Narrow API/Database Exception Handlers** - 19 handlers narrowed in
      api/ and database/ modules (api/database.py, api/routes/imaging.py,
      api/services/bokeh_sessions.py, database/products.py,
      database/calibrators.py, database/session.py)
- [x] **Connection Pooling** - Added SyncDatabasePool with connection reuse,
      get_sync_db_pool(), close_sync_db_pool(); 7 new tests
- [x] **Narrow Conversion Exception Handlers** - 35+ handlers narrowed in
      conversion/ module (helpers_telescope.py, helpers_coordinates.py,
      helpers_validation.py, helpers_model.py, merge_spws.py, ms_utils.py,
      strategies/direct_subband.py)
- [x] **Narrow Remaining Exception Handlers** - 100+ handlers narrowed across: - utils/ (~17 handlers: validation.py, time_utils.py, regions.py,
      ms_helpers.py, locking.py) - photometry/ (~15 handlers: worker.py, forced.py, aegean_fitting.py,
      adaptive_binning.py) - imaging/ (~14 handlers: worker.py, fast_imaging.py, nvss_tools.py,
      cli_utils.py, cli.py, cli_imaging.py) - calibration/ (~17 handlers: validate.py, skymodels.py, selection.py,
      model.py, flagging.py, calibration.py) - catalog/ (~17 handlers: query.py, multiwavelength.py, build_master.py) - absurd/ (2 handlers: worker.py, adapter.py) - pipeline/ (2 handlers: stages_impl.py) - streaming_converter.py (~20 handlers)
      All handlers now use specific exception types: sqlite3.Error, OSError,
      RuntimeError, ValueError, KeyError, TypeError, ImportError, IndexError,
      subprocess.SubprocessError, np.linalg.LinAlgError, json.JSONDecodeError
- [x] **Mosaicking Module** - Complete implementation of mature mosaicking system
      following architecture document (`mature-mosaicking-code.md`). Features: - Three-tier system: Quicklook (10 images, 5min), Science (100 images, 30min),
      Deep (1000 images, 120min) - ABSURD-governed pipeline: MosaicPlanningJob → MosaicBuildJob → MosaicQAJob - Unified database: 3 tables (mosaic_plans, mosaics, mosaic_qa) - FastAPI endpoints: `/api/mosaic/create`, `/api/mosaic/status/{name}` - MosaicOrchestrator for ABSURD adapter integration - Contract tests: 26 tests covering builder, QA, tiers, jobs, pipeline,
      schema, orchestrator, and API - Module: 9 files, ~2760 lines in `src/dsa110_contimg/mosaic/`

**Status**: 950 unit tests passing, 72% coverage, **0 broad exception handlers**

---

## Future Enhancements

### Medium Priority

- [x] **Service Layer Refactoring** - Move business logic from repositories to
      services. Created `api/business_logic.py` with `stage_to_qa_grade()`,
      `generate_image_qa_summary()`, `generate_ms_qa_summary()`, `generate_run_id()`.
      Removed duplicate methods from AsyncImageRepository, AsyncMSRepository,
      AsyncJobRepository. Added 28 unit tests for business logic module.
- [x] **PostgreSQL Testing** - Test with real PostgreSQL database. Verified
      PostgreSQL 16 container connectivity, adapter creation, and query execution.
      All 58 database adapter tests pass. 15 tables created via init.sql.
- [x] **N+1 Query Optimization** - Optimized `AsyncImageRepository.list_all()`
      to batch fetch QA grades from ms_index in a single query instead of N+1
      queries per image. Added 8 optimization tests in `test_query_optimization.py`.

### Low Priority

- [x] **WebSocket Improvements** - Added heartbeat tracking, reconnection tokens,
      and disconnect reasons. Added `DisconnectReason` enum, `ConnectionState` enum,
      `record_heartbeat()`, `check_heartbeat()`, `generate_reconnect_token()` methods.
      Updated `/ws/jobs` and `/ws/pipeline` endpoints with heartbeat monitoring.
      Added 14 new WebSocket tests (39 total).
- [x] **Cache Optimization** - Redis cache for expensive queries. Added comprehensive
      test suite for cache module with 41 tests covering: CacheManager, cache key
      generation, @cached decorator, TTL configuration, blacklist handling, error
      handling, and singleton pattern.
- [x] **Metrics Dashboard** - Grafana dashboard for Prometheus metrics. Added
      `ops/grafana/dsa110-pipeline-dashboard.json` with 20 panels covering pipeline
      overview, processing throughput, data quality, and pipeline stages. Added
      39 unit tests for the metrics module.

---

## Monitoring Implementation ✅ COMPLETE

**Status:** All monitoring capabilities implemented

### 1. Unified Health Dashboard API

- **`api/routes/health.py`** - Comprehensive health monitoring endpoints:
  - `GET /health/system` - Full system health report (Docker, systemd, HTTP)
  - `GET /health/docker/{container}` - Individual container health
  - `GET /health/systemd/{service}` - Individual service health
  - `GET /health/databases` - Database connectivity checks
  - `GET /health/validity-windows` - Active calibration validity windows
  - `GET /health/flux-monitoring` - Calibrator flux monitoring status
  - `GET /health/alerts` - Recent monitoring alerts

### 2. Flux Monitoring Scheduler (ABSURD Integration)

- **`monitoring/tasks.py`** - ABSURD task definitions:
  - `monitoring.flux_check` - Run flux monitoring check (hourly)
  - `monitoring.health_check` - System health check (5 minutes)
  - `monitoring.validity_check` - Validity window expiration check (15 minutes)
  - `monitoring.send_alert` - Send alerts via webhook/email/slack
- **Integration**: `register_monitoring_tasks()` and `setup_monitoring_schedules()`

### 3. Validity Window Visualization

- **API Endpoints**:
  - `GET /health/validity-windows` - Active windows by MJD
  - `GET /health/validity-windows/timeline` - Timeline view for visualization
- **Features**:
  - Query by MJD or ISO timestamp
  - Shows overlapping sets
  - Expiration warnings

### 4. Calibrator Monitoring Dashboard

- **Grafana panels** added to `ops/grafana/dsa110-pipeline-dashboard.json`:
  - Calibrator flux ratio over time
  - Flux stability alerts
  - Calibrator-specific metrics

### 5. Pointing Monitor Service

- **`pointing/monitor.py`** - Complete pointing module:
  - `calculate_lst()` - Current Local Sidereal Time
  - `predict_calibrator_transit()` - Transit time predictions
  - `get_active_calibrator()` - Currently transiting calibrator
  - `get_upcoming_transits()` - Future transit schedule
  - `PointingMonitor` class - Full monitoring daemon
- **`ops/systemd/contimg-pointing.service`** - Systemd service file

---

## Test Coverage Goals ✅ COMPLETE

**Status:** 1143 unit tests passing

All coverage targets have been achieved:

| Module                | Previous | Current | Target | Status |
| --------------------- | -------- | ------- | ------ | ------ |
| `batch/qa.py`         | 41%      | 97%     | 80%    | ✅     |
| `batch/thumbnails.py` | 53%      | 97%     | 80%    | ✅     |
| `websocket.py`        | 49%      | 84%     | 70%    | ✅     |
| `cache.py`            | 28%      | 89%     | 60%    | ✅     |
| `metrics.py`          | 33%      | 93%     | 60%    | ✅     |

---

## Documentation

See `docs/` for:

- `ARCHITECTURE.md` - System architecture and design patterns
- `CHANGELOG.md` - Development history and milestones
- `ASYNC_PERFORMANCE_REPORT.md` - Async migration benchmarks
- `database-adapters.md` - Multi-database abstraction layer
