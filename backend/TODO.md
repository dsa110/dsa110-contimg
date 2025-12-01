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

- [ ] **Service Layer Refactoring** - Move business logic from repositories to
      services
- [ ] **PostgreSQL Testing** - Test with real PostgreSQL database
- [ ] **N+1 Query Optimization** - Profile and optimize list endpoints

### Low Priority

- [ ] **WebSocket Improvements** - Add reconnection logic, heartbeat
- [ ] **Cache Optimization** - Redis cache for expensive queries
- [ ] **Metrics Dashboard** - Grafana dashboard for Prometheus metrics

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
