# Backend Enhancement Implementation TODO

This file tracks the progress of implementing the enhancements outlined in `ENHANCEMENT_IMPLEMENTATION_PLAN.md`.

## Phase 1: Complete Async Migration ⏳

### 1.1 Update Dependencies ✅
- [x] Fix AsyncImageRepository constructor to not require db_pool
- [x] Fix AsyncSourceRepository constructor to not require db_pool  
- [x] Fix AsyncJobRepository constructor to not require db_pool
- [x] Update dependencies.py to properly inject async repositories
- [x] Add async MS repository dependency

### 1.2 Create Async Service Layer ✅
- [x] Create AsyncImageService
- [x] Create AsyncSourceService
- [x] Create AsyncJobService
- [x] Create AsyncMSService
- [x] Update services/__init__.py to export async services

### 1.3 Migrate Route Handlers to Async
- [ ] routes/images.py - Convert all handlers to async
- [ ] routes/sources.py - Convert all handlers to async
- [ ] routes/jobs.py - Convert all handlers to async
- [ ] routes/ms.py - Convert all handlers to async
- [ ] routes/qa.py - Convert all handlers to async
- [ ] routes/cal.py - Convert all handlers to async
- [ ] routes/stats.py - Convert all handlers to async
- [ ] routes/logs.py - Convert all handlers to async
- [ ] routes/queue.py - Convert all handlers to async
- [ ] routes/cache.py - Convert all handlers to async
- [ ] routes/services.py - Convert all handlers to async

### 1.4 Update Tests
- [ ] Update test fixtures for async
- [ ] Update unit tests for async repositories
- [ ] Update integration tests for async routes
- [ ] Add async transaction tests

### 1.5 Documentation
- [ ] Update API documentation for async patterns
- [ ] Add async best practices guide
- [ ] Update troubleshooting guide

---

## Phase 2: Enhanced Connection Pooling ⏳

### 2.1 Enhance DatabasePool Class
- [ ] Add connection pool size configuration
- [ ] Implement connection health checks
- [ ] Add connection recycling logic
- [ ] Implement pool exhaustion handling
- [ ] Add connection timeout configuration

### 2.2 Add Pool Monitoring
- [ ] Add Prometheus metrics for pool
  - [ ] Active connections gauge
  - [ ] Wait time histogram
  - [ ] Pool exhaustion counter
  - [ ] Connection errors counter
- [ ] Add pool status endpoint
- [ ] Add pool health check

### 2.3 Configuration
- [ ] Add pool config to config.py
- [ ] Add environment variables for pool settings
- [ ] Document pool configuration

### 2.4 Testing
- [ ] Add pool stress tests
- [ ] Test pool exhaustion scenarios
- [ ] Test connection recycling
- [ ] Test health checks

---

## Phase 3: FITS Parsing Service Integration ⏳

### 3.1 Complete FITSParsingService
- [ ] Review existing fits_service.py
- [ ] Add missing FITS parsing methods
- [ ] Add FITS validation
- [ ] Add error handling with FITSParsingError

### 3.2 Add FITS Metadata Caching
- [ ] Implement cache key generation
- [ ] Add cache TTL configuration
- [ ] Integrate with existing cache.py
- [ ] Add cache invalidation logic

### 3.3 Extract FITS Logic from Repositories
- [ ] Remove FITS parsing from ImageRepository
- [ ] Update routes to use FITSParsingService
- [ ] Update services to use FITSParsingService

### 3.4 Testing
- [ ] Add FITS parsing unit tests
- [ ] Add FITS caching tests
- [ ] Test error scenarios
- [ ] Performance benchmarks

### 3.5 Documentation
- [ ] Document FITS service API
- [ ] Add usage examples
- [ ] Document caching strategy

---

## Phase 4: Narrow Exception Handling ⏳

### 4.1 Audit Exception Handlers
- [ ] Review all 86 `except Exception:` instances
- [ ] Categorize: keep vs narrow
- [ ] Document decision for each

### 4.2 Narrow Route Exception Handlers
- [ ] routes/images.py
- [ ] routes/sources.py
- [ ] routes/jobs.py
- [ ] routes/ms.py
- [ ] routes/qa.py
- [ ] routes/cal.py
- [ ] routes/stats.py
- [ ] routes/logs.py
- [ ] routes/queue.py
- [ ] routes/cache.py
- [ ] routes/services.py

### 4.3 Narrow Service Exception Handlers
- [ ] services/image_service.py
- [ ] services/source_service.py
- [ ] services/job_service.py
- [ ] services/ms_service.py
- [ ] services/stats_service.py
- [ ] services/qa_service.py
- [ ] services/fits_service.py

### 4.4 Narrow Repository Exception Handlers
- [ ] repositories.py
- [ ] async_repositories.py

### 4.5 Narrow Batch Job Exception Handlers
- [ ] batch/jobs.py
- [ ] batch/qa.py
- [ ] batch/thumbnails.py

### 4.6 Other Files
- [ ] app.py
- [ ] database.py
- [ ] cache.py
- [ ] job_queue.py
- [ ] metrics.py
- [ ] websocket.py
- [ ] auth.py
- [ ] logging_config.py
- [ ] services_monitor.py

### 4.7 Testing
- [ ] Add tests for specific exception types
- [ ] Test error messages
- [ ] Test exception propagation

### 4.8 Documentation
- [ ] Document exception handling patterns
- [ ] Add exception handling guide
- [ ] Update API error documentation

---

## Phase 5: Enhanced Alembic Migrations ⏳

### 5.1 Migration Scripts
- [ ] Create migration generation script
- [ ] Add migration runner script (scripts/ops/migrate_db.py)
- [ ] Add migration rollback script
- [ ] Add migration status script

### 5.2 Multi-Database Migrations
- [ ] Add migrations for cal_registry.sqlite3
- [ ] Add migrations for hdf5.sqlite3
- [ ] Add migrations for ingest.sqlite3
- [ ] Add migrations for data_registry.sqlite3

### 5.3 Migration Testing
- [ ] Create migration test framework
- [ ] Test forward migrations
- [ ] Test rollback migrations
- [ ] Test migration idempotency

### 5.4 Documentation
- [ ] Create docs/ops/database-migrations.md
- [ ] Document migration workflow
- [ ] Document rollback procedures
- [ ] Add migration best practices

### 5.5 CI/CD Integration
- [ ] Add migration checks to CI
- [ ] Add migration validation
- [ ] Document deployment process

---

## Testing Checklist

### Unit Tests
- [ ] All new functions have unit tests
- [ ] Edge cases covered
- [ ] Error scenarios tested
- [ ] Mocks used appropriately

### Integration Tests
- [ ] Database interactions tested
- [ ] Service integration tested
- [ ] API endpoints tested
- [ ] End-to-end workflows tested

### Performance Tests
- [ ] Async vs sync benchmarks
- [ ] Connection pool load tests
- [ ] FITS parsing benchmarks
- [ ] API response time tests

### Regression Tests
- [ ] All existing tests pass
- [ ] API compatibility verified
- [ ] No breaking changes
- [ ] Backwards compatibility maintained

---

## Documentation Checklist

- [ ] API documentation updated
- [ ] Architecture diagrams updated
- [ ] README.md updated
- [ ] ARCHITECTURE_REFACTORING.md updated
- [ ] Inline code documentation complete
- [ ] Usage examples provided
- [ ] Troubleshooting guide updated

---

## Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Code review completed
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Database backup created

### Deployment
- [ ] Deploy to staging
- [ ] Run integration tests on staging
- [ ] Performance testing on staging
- [ ] Monitor staging for issues
- [ ] Deploy to production
- [ ] Monitor production metrics

### Post-Deployment
- [ ] Verify all endpoints working
- [ ] Check error rates
- [ ] Monitor performance metrics
- [ ] Check database connections
- [ ] Verify logging working

---

## Progress Summary

- **Phase 1**: 0% complete (0/5 tasks)
- **Phase 2**: 0% complete (0/4 tasks)
- **Phase 3**: 0% complete (0/5 tasks)
- **Phase 4**: 0% complete (0/8 tasks)
- **Phase 5**: 0% complete (0/5 tasks)

**Overall Progress**: 0% complete (0/27 major tasks)

---

## Notes

- Each checkbox represents a completed task
- Update progress summary after completing each major task
- Add notes for any blockers or issues encountered
- Link to relevant PRs or commits for each completed task
