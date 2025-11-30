# Remaining Work Prioritization & Roadmap

**Last Updated:** 2025-11-30  
**Status:** Post-Phase 1A Planning  
**Context:** Foundation improvements complete, planning next phases

## Completed: Phase 1A ✅

- [x] Fixed configuration caching (lazy-loaded functions)
- [x] Consolidated error handling (exceptions.py only)
- [x] Narrowed critical exception handlers (health checks)
- [x] Implemented Protocol interfaces (type-safe repositories)
- [x] Documented async migration path

**Result:** 121 tests passing, no regressions, solid foundation

---

## Priority Queue

### 🔴 P0: Critical (Do First)

#### 1. Async Migration Decision & Execution

**Status:** Decision document prepared  
**Timeline:** 3-4 days (Option A) or 1 day (Option B)  
**Owner:** TBD  
**Blocker:** Yes - blocks other async-related work

**Action Items:**

- [ ] Schedule team decision meeting (30 min)
- [ ] If Option A: Assign 1 developer for 3-4 days
- [ ] If Option B: Assign 1 developer for 1 day cleanup
- [ ] Update project status after completion

**Dependencies:** None  
**Risk:** Low (well-documented, easy rollback)  
**Value:** High (eliminates confusion, improves performance)

---

### 🟠 P1: High Priority (Next 2 Weeks)

#### 2. Narrow Remaining Exception Handlers

**Status:** 76 instances identified, 3 fixed  
**Timeline:** 2-3 days  
**Owner:** TBD  
**Blocker:** No, but improves code quality

**Breakdown:**

- `routes.py` (legacy): 25 instances - Will be removed after async migration
- `batch/qa.py`: 7 instances - Reviewed, most are legitimate fallbacks
- `batch/jobs.py`: Some instances - Need review
- `services_monitor.py`: 4 instances - Need narrowing
- `websocket.py`: 4 instances - Need narrowing
- `conversion/` modules: Multiple - Lower priority
- `calibration/` modules: Multiple - Lower priority

**Approach:**

```python
# Current (too broad)
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Failed: {e}")
    return default_value

# Better (specific)
try:
    result = risky_operation()
except (IOError, OSError, sqlite3.Error) as e:
    logger.error(f"Failed due to I/O or DB error: {e}")
    return default_value
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    raise ValidationError(str(e))
```

**Action Items:**

- [ ] Create GitHub issue tracking all 76 instances
- [ ] Categorize: must-fix vs acceptable-fallback
- [ ] Fix high-priority routes and services (2 days)
- [ ] Document decisions for each category

**Dependencies:** None  
**Risk:** Low (incremental improvements)  
**Value:** Medium (better debugging, fewer hidden bugs)

#### 3. Add Connection Pooling for Sync Code

**Status:** Only async code has pooling  
**Timeline:** 1-2 days  
**Owner:** TBD  
**Blocker:** No

**Problem:**

```python
# Current: Creates new connection every time
def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = _get_default_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)  # New conn!
    # ...
```

**Solution:**

```python
# Add connection pool
from contextlib import contextmanager

class SyncConnectionPool:
    def __init__(self, db_path: str, pool_size: int = 5):
        self._pool = queue.Queue(maxsize=pool_size)
        self._db_path = db_path
        # Pre-populate pool

    @contextmanager
    def connection(self):
        conn = self._pool.get()
        try:
            yield conn
        finally:
            self._pool.put(conn)
```

**Action Items:**

- [ ] Implement `SyncConnectionPool` class
- [ ] Add to `database.py`
- [ ] Update `get_db_connection()` to use pool
- [ ] Add pool metrics to health check
- [ ] Load test to verify improvement

**Dependencies:** None (but easier after async decision)  
**Risk:** Low (well-understood pattern)  
**Value:** Medium (reduces connection overhead)

#### 4. Remove Legacy `errors.py` Module

**Status:** No longer used after error consolidation  
**Timeline:** 2 hours  
**Owner:** Anyone  
**Blocker:** No

**Action Items:**

- [ ] Verify no imports remain: `grep -r "from .errors import" src/`
- [ ] Remove `src/dsa110_contimg/api/errors.py`
- [ ] Remove from `__init__.py` exports if present
- [ ] Update any documentation referencing it
- [ ] Commit: "Remove deprecated errors.py module"

**Dependencies:** Error consolidation complete ✅  
**Risk:** Very Low  
**Value:** Low (cleanup)

---

### 🟡 P2: Medium Priority (Next Month)

#### 5. Service Layer Refactoring

**Status:** Services too thin, repositories have business logic  
**Timeline:** 1 week  
**Owner:** TBD  
**Blocker:** No

**Problem:**

```python
# Current: Service just passes through
class ImageService:
    def get_image(self, image_id: str):
        return self.repo.get_by_id(image_id)  # Just forwarding!
```

**Better:**

```python
# Repository: Just data access
class ImageRepository:
    def get_by_id(self, image_id: str) -> Optional[ImageRecord]:
        # SQL query only

# Service: Business logic
class ImageService:
    def get_image_with_enrichment(self, image_id: str) -> EnrichedImage:
        image = self.repo.get_by_id(image_id)
        if not image:
            raise RecordNotFoundError("Image", image_id)

        # Business logic here
        qa_data = self._enrich_qa(image)
        provenance = self._build_provenance(image)
        return EnrichedImage(image, qa_data, provenance)
```

**Action Items:**

- [ ] Audit repositories for business logic (1 day)
- [ ] Move QA calculations to services (2 days)
- [ ] Move provenance building to services (1 day)
- [ ] Update tests (1 day)
- [ ] Document service responsibilities (0.5 day)

**Dependencies:** Async migration helpful but not required  
**Risk:** Medium (changes many files)  
**Value:** High (better separation of concerns)

#### 6. Implement Transaction Management

**Status:** No multi-table transaction support  
**Timeline:** 2-3 days  
**Owner:** TBD  
**Blocker:** No

**Problem:**

```python
# Current: Two separate operations (not atomic)
conn1 = get_db_connection()
conn1.execute("INSERT INTO images ...")
conn1.commit()

conn2 = get_db_connection()
conn2.execute("INSERT INTO qa_metrics ...")
conn2.commit()  # If this fails, image is orphaned!
```

**Solution:**

```python
# Sync version
with transaction(get_db_connection()) as conn:
    conn.execute("INSERT INTO images ...")
    conn.execute("INSERT INTO qa_metrics ...")
    # Auto-commit if no exception, auto-rollback if exception

# Async version (already exists!)
async with AsyncTransaction(db_path) as conn:
    await conn.execute("INSERT INTO images ...")
    await conn.execute("INSERT INTO qa_metrics ...")
```

**Action Items:**

- [ ] Implement sync `Transaction` context manager
- [ ] Identify operations needing transactions (batch jobs!)
- [ ] Update batch job creation to use transactions
- [ ] Add transaction tests
- [ ] Document transaction patterns

**Dependencies:** None  
**Risk:** Medium (requires careful testing)  
**Value:** High (data integrity)

#### 7. N+1 Query Optimization

**Status:** Multiple queries in loops  
**Timeline:** 2-3 days  
**Owner:** TBD  
**Blocker:** No

**Problem:**

```python
# Current: N+1 queries
images = repo.list_all(limit=100)  # 1 query
for image in images:
    ms_data = ms_repo.get_metadata(image.ms_path)  # N queries!
    qa_data = qa_repo.get_qa(image.id)  # N more queries!
```

**Solution:**

```python
# Better: JOIN or batch query
images_with_data = repo.list_all_with_joins(
    limit=100,
    include_ms=True,
    include_qa=True
)  # 1 query with JOINs
```

**Action Items:**

- [ ] Profile endpoints to find N+1 patterns (1 day)
- [ ] Add JOIN-based query methods (1 day)
- [ ] Update routes to use new methods (0.5 day)
- [ ] Verify performance improvement (0.5 day)

**Dependencies:** None  
**Risk:** Low  
**Value:** High (significant performance improvement)

---

### 🟢 P3: Nice to Have (Future)

#### 8. Comprehensive Integration Tests

**Current:** Minimal integration test coverage  
**Timeline:** 1 week  
**Value:** Medium (catch issues early)

#### 9. Circuit Breakers for External Services

**Current:** No failure protection for Redis, databases  
**Timeline:** 2-3 days  
**Value:** Medium (resilience)

#### 10. Database Migration Strategy

**Current:** Alembic configured but not used  
**Timeline:** 1 week (initial setup)  
**Value:** High (controlled schema evolution)

#### 11. API Versioning Strategy

**Current:** `/api/v1` prefix but no version control  
**Timeline:** 3-4 days  
**Value:** Low (not needed yet)

#### 12. Observability Improvements

- Structured logging (JSON format)
- Distributed tracing (OpenTelemetry)
- Complete Prometheus metrics
- Grafana dashboards

**Timeline:** 2 weeks  
**Value:** High (for production operations)

---

## Recommended 30-Day Roadmap

### Week 1: Async & Critical Cleanup

- **Days 1-4:** Execute async migration (Option A)
- **Day 5:** Remove legacy `errors.py`, celebrate wins

**Deliverables:**

- [ ] All routes using async repositories
- [ ] Sync implementations removed
- [ ] Clean test suite
- [ ] Updated documentation

**Success Metrics:**

- 5-10x better throughput under load
- Zero breaking changes
- All tests passing

### Week 2: Exception Handling & Pooling

- **Days 1-2:** Narrow exception handlers in critical paths
- **Day 3:** Implement connection pooling for sync code
- **Days 4-5:** Testing and documentation

**Deliverables:**

- [ ] 20-30 exception handlers narrowed
- [ ] Connection pool implemented
- [ ] Health check shows pool metrics

**Success Metrics:**

- Better error messages
- Reduced connection overhead
- Clearer debugging

### Week 3: Service Layer & Transactions

- **Days 1-3:** Refactor service layer
- **Days 4-5:** Implement transaction management

**Deliverables:**

- [ ] Business logic in services (not repositories)
- [ ] Transaction support for batch operations
- [ ] Updated tests

**Success Metrics:**

- Clear separation of concerns
- Data integrity guarantees
- Easier to test

### Week 4: Performance & Testing

- **Days 1-2:** N+1 query optimization
- **Days 3-4:** Integration test expansion
- **Day 5:** Load testing and performance validation

**Deliverables:**

- [ ] Optimized queries
- [ ] 20+ new integration tests
- [ ] Performance benchmarks

**Success Metrics:**

- 2-3x faster list endpoints
- 80%+ test coverage
- Documented performance baselines

---

## Success Metrics (Overall)

### Code Quality

- [ ] < 10 broad exception handlers remaining
- [ ] 80%+ test coverage
- [ ] All repositories implement Protocols
- [ ] Zero TODO/FIXME/HACK comments in critical paths

### Performance

- [ ] < 100ms p95 response time for GET endpoints
- [ ] 1000+ req/sec sustained throughput
- [ ] < 5% error rate under load

### Architecture

- [ ] Single error handling system (exceptions.py)
- [ ] Single repository pattern (async or sync, not both)
- [ ] Clear service layer responsibilities
- [ ] Documented transaction patterns

### Operations

- [ ] Health checks cover all dependencies
- [ ] Metrics exported to Prometheus
- [ ] Structured logging enabled
- [ ] Runbooks for common issues

---

## Resource Requirements

### Developer Time

- **P0 (Async):** 3-4 days × 1 developer
- **P1 (Week 2-3):** 10 days × 1 developer
- **P2 (Month 2):** 20 days × 1 developer
- **Total (30 days):** ~37 developer-days

### Infrastructure

- Staging environment for testing
- Load testing tools (wrk, locust)
- Monitoring (Prometheus + Grafana)

### Risk Buffer

- Add 20% buffer for unexpected issues
- Keep sync code available for 1 sprint (rollback option)

---

## Decision Points

### Decision 1: Async Migration (NOW)

- [ ] Option A: Complete migration (recommended)
- [ ] Option B: Remove async code
- [ ] Option C: Status quo

**Required by:** End of this week  
**Blocks:** Connection pooling decisions

### Decision 2: Service Refactoring Scope (Week 2)

- [ ] Full refactor (move all business logic)
- [ ] Partial refactor (just QA/provenance)
- [ ] Defer to later

**Required by:** End of week 2  
**Blocks:** Transaction implementation

### Decision 3: PostgreSQL Migration (Month 2)

- [ ] Plan for PostgreSQL (affects pooling strategy)
- [ ] Stay with SQLite (simpler pooling)

**Required by:** End of month 1  
**Blocks:** Advanced pooling features

---

## Communication Plan

### Weekly Updates

- Monday: Review progress, blockers
- Wednesday: Mid-week sync
- Friday: Demo completed work

### Stakeholders

- Engineering team: Daily standup
- Product: Weekly summary
- DevOps: As needed for deployment

### Documentation

- Update `ARCHITECTURE_REFACTORING.md` after each phase
- Keep `TODO.md` current
- Add runbooks as issues are discovered

---

**Next Actions:**

1. ✅ Schedule async decision meeting
2. ⏳ Assign P0 work (async migration)
3. ⏳ Create GitHub issues for P1 work
4. ⏳ Set up monitoring for new metrics
5. ⏳ Schedule 30-day review meeting

**Questions?** See individual sections above or `IMPLEMENTATION_SUMMARY.md`
