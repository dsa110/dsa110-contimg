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

## Test Coverage Goals

| Module                | Current | Target |
| --------------------- | ------- | ------ |
| `batch/qa.py`         | 41%     | 80%    |
| `batch/thumbnails.py` | 53%     | 80%    |
| `websocket.py`        | 49%     | 70%    |
| `cache.py`            | 28%     | 60%    |
| `metrics.py`          | 33%     | 60%    |

---

## Documentation

See `docs/` for:

- `ARCHITECTURE.md` - System architecture and design patterns
- `CHANGELOG.md` - Development history and milestones
- `ASYNC_PERFORMANCE_REPORT.md` - Async migration benchmarks
- `database-adapters.md` - Multi-database abstraction layer
