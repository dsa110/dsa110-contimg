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

**Status**: 782 tests passing, 72% coverage

---

## Future Enhancements

### High Priority

- [ ] **Connection Pooling** - Add sync connection pool for better resource
      usage
- [ ] **Remove Legacy errors.py** - No longer needed after exception
      consolidation
- [ ] **Narrow More Exception Handlers** - ~76 remaining `except Exception:`
      instances

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
