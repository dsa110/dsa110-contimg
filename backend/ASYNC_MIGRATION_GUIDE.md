# Async Migration Guide

## Current State

The codebase currently has **dual sync/async implementations** which creates
maintenance burden and confusion:

- ✅ **Sync repositories** (`repositories.py`) - Currently used by routes
- ✅ **Async repositories** (`async_repositories.py`) - Fully implemented but
  not used
- ✅ **Async services** (`services/async_services.py`) - Implemented but not
  integrated
- ⚠️ **Routes** - Using sync repositories with async route handlers (blocks
  threads)
- ⚠️ **Dependencies** - Injecting sync repositories

## Problem

FastAPI supports async natively, but we're using synchronous database calls
which **blocks the event loop**. This means:

- Poor concurrency under load
- Wasted resources (each request blocks a thread)
- No advantage from FastAPI's async capabilities

## Decision Required

The team needs to make a **strategic decision**:

### Option A: Complete Async Migration (Recommended)

**Pros:**

- True non-blocking I/O
- Better performance under load
- Consistent with FastAPI best practices
- Enables future async features (streaming, websockets)

**Cons:**

- Requires updating all routes (mechanical work)
- Need to test thoroughly
- Learning curve for team unfamiliar with async

**Effort:** ~3-4 days **Risk:** Medium (well-understood patterns)

### Option B: Remove Async Code Entirely

**Pros:**

- Simpler codebase (one way to do things)
- Easier for teams unfamiliar with async
- Still works fine for current load

**Cons:**

- SQLite is blocking regardless
- Loses async benefits for other I/O (Redis, file system)
- May need to revisit if scale increases

**Effort:** ~1 day (delete async files, update docs) **Risk:** Low

### Option C: Hybrid (Current State - Not Recommended)

**Pros:**

- No immediate work required

**Cons:**

- Confusing for developers
- Double maintenance burden
- Async code exists but provides no benefit
- Tech debt accumulates

**Effort:** 0 days **Risk:** High (confusion, maintenance burden)

## Recommendation: Option A - Complete Migration

The async infrastructure is already built. Completing the migration will:

1. Realize the investment already made
2. Position the codebase for future scale
3. Eliminate confusion from dual implementations

## Migration Path (Option A)

### Phase 1: Update Dependencies (1 day)

```python
# dependencies.py
from .async_repositories import (
    AsyncImageRepository,
    AsyncMSRepository,
    AsyncSourceRepository,
    AsyncJobRepository,
)

async def get_async_image_repository() -> AsyncImageRepository:
    return AsyncImageRepository()

# Same for other repositories...
```

### Phase 2: Migrate Route Handlers (2 days)

All routes are already `async def`, just need to update to use async
repositories:

**Before:**

```python
@router.get("/{image_id}")
async def get_image(
    image_id: str,
    service: ImageService = Depends(get_image_service),  # sync service
):
    image = service.get_image(image_id)  # blocks thread!
    ...
```

**After:**

```python
@router.get("/{image_id}")
async def get_image(
    image_id: str,
    service: AsyncImageService = Depends(get_async_image_service),
):
    image = await service.get_image(image_id)  # truly async
    ...
```

**Files to Update:**

- `routes/images.py` (5 endpoints)
- `routes/sources.py` (4 endpoints)
- `routes/jobs.py` (3 endpoints)
- `routes/ms.py` (3 endpoints)
- `routes/qa.py` (3 endpoints)
- `routes/stats.py` (2 endpoints)

### Phase 3: Testing (1 day)

- Update test fixtures to use async repos
- Run full test suite
- Load test to verify async benefits
- Smoke test in staging

### Phase 4: Cleanup (0.5 days)

- Remove sync repositories from `repositories.py` (keep record types)
- Remove sync services
- Update documentation

## Migration Path (Option B)

If choosing to remove async:

1. Delete `async_repositories.py`
2. Delete `services/async_services.py`
3. Keep current sync implementation
4. Update this document to reflect decision
5. Add note to `ARCHITECTURE_REFACTORING.md`

## Testing Strategy

### Unit Tests

```python
@pytest.mark.asyncio
async def test_async_repository():
    repo = AsyncImageRepository()
    image = await repo.get_by_id("1")
    assert image is not None
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_async_endpoint(async_client):
    response = await async_client.get("/api/v1/images/1")
    assert response.status_code == 200
```

### Load Tests

Compare before/after with concurrent requests:

```bash
# Before: sync (should see thread blocking)
wrk -t12 -c400 -d30s http://localhost:8000/api/v1/images

# After: async (should see better throughput)
wrk -t12 -c400 -d30s http://localhost:8000/api/v1/images
```

## Rollback Plan

If issues arise:

1. Revert `dependencies.py` to inject sync repos
2. Revert route changes
3. Investigate issues
4. Re-attempt with fixes

Git branch strategy:

```bash
git checkout -b feat/complete-async-migration
# Make changes...
git push origin feat/complete-async-migration
# Create PR, test in CI
# Merge if tests pass, revert if issues
```

## Performance Expectations

### Sync (Current)

- Single request: 10-50ms (database query time)
- 100 concurrent requests: ~2-5s (sequential processing)
- CPU usage: Low
- Memory: Higher (thread per request)

### Async (Target)

- Single request: 10-50ms (same, database is bottleneck)
- 100 concurrent requests: ~100-500ms (concurrent processing)
- CPU usage: Higher (more work per second)
- Memory: Lower (event loop vs threads)

**Note:** SQLite is still blocking at the file level, but async allows other
requests to proceed while waiting for I/O.

## FAQ

### Q: Won't SQLite block anyway since it's file-based?

A: Yes, individual queries block, but with async we can handle multiple
concurrent requests efficiently. While one request waits for SQLite, others can
proceed with their queries.

### Q: Can we do a gradual migration?

A: Yes! Routes can be migrated one at a time. Both sync and async repos can
coexist temporarily.

### Q: What about database transactions?

A: `AsyncTransaction` context manager is already implemented in
`async_repositories.py`.

### Q: How does this affect our ORM/database choice?

A: This is independent of the ORM choice. Whether using SQLAlchemy or raw SQL,
async is supported.

## Action Items

- [ ] **Team Decision**: Choose Option A, B, or C (schedule meeting)
- [ ] **If Option A**: Assign developer(s), create tracking issue
- [ ] **If Option B**: Schedule cleanup, update architecture docs
- [ ] **If Option C**: Document rationale and accept tech debt

## References

- FastAPI Async SQL: https://fastapi.tiangolo.com/advanced/async-sql-databases/
- aiosqlite docs: https://aiosqlite.omnilib.dev/
- Python async/await: https://docs.python.org/3/library/asyncio.html
- Current implementations:
  - `src/dsa110_contimg/api/repositories.py` (sync)
  - `src/dsa110_contimg/api/async_repositories.py` (async)
  - `src/dsa110_contimg/api/services/async_services.py` (async)

---

**Last Updated:** 2025-11-30  
**Status:** Awaiting Team Decision  
**Owner:** TBD
