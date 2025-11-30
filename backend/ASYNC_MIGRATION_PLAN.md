# Async Migration Plan - Phase 1 Completion

## Current State Analysis

### ✅ Completed (2/11 route files)
1. **images.py** - Fully migrated to async
2. **sources.py** - Fully migrated to async

### 🔄 Remaining Route Files (9 files)

#### High Priority - Need Async Service Methods
1. **jobs.py** - Uses JobService (needs async methods: get_job_status, build_provenance_links, read_log_tail)
2. **ms.py** - Uses MSService (needs async methods: get_pointing, get_primary_cal_table, build_provenance_links)
3. **qa.py** - Uses QAService (needs async version: build_image_qa, build_ms_qa, build_job_qa)

#### Medium Priority - Already Async or Simple
4. **stats.py** - Already uses async (StatsService.get_dashboard_stats is async)
5. **logs.py** - Uses JobService.read_log_tail (file I/O, needs async)
6. **cal.py** - Direct DB access (needs async repository pattern)

#### Low Priority - No DB Access
7. **queue.py** - Uses job_queue module (no DB, mostly sync operations)
8. **cache.py** - Uses cache_manager (Redis operations, already async-compatible)
9. **services.py** - Uses services_monitor (already async)

---

## Implementation Plan

### Step 1: Extend AsyncJobService
Add missing methods to AsyncJobService:
- `get_job_status(job)` - Sync helper, no DB access
- `build_provenance_links(job)` - Sync helper, no DB access
- `find_log_file(run_id)` - File I/O, make async
- `read_log_tail(run_id, tail)` - File I/O, make async

### Step 2: Extend AsyncMSService
Add missing methods to AsyncMSService:
- `get_pointing(ms)` - Sync helper, no DB access
- `get_primary_cal_table(ms)` - Sync helper, no DB access
- `build_provenance_links(ms)` - Sync helper, no DB access

### Step 3: Create AsyncQAService
New async service class with methods:
- `build_image_qa(image)` - Sync helper, no DB access
- `build_ms_qa(ms)` - Sync helper, no DB access
- `build_job_qa(job)` - Sync helper, no DB access

### Step 4: Create AsyncCalRepository
New repository for calibration table operations:
- `get_cal_table(path)` - Async DB query

### Step 5: Migrate Route Files

#### Priority 1: Core Routes (Jobs, MS, QA)
1. **jobs.py** (5 endpoints)
   - Update imports: AsyncJobService
   - Update dependency: get_async_job_service
   - Add await to all service calls
   - Handle async file I/O for logs

2. **ms.py** (3 endpoints)
   - Update imports: AsyncMSService
   - Update dependency: get_async_ms_service
   - Add await to all service calls

3. **qa.py** (3 endpoints)
   - Update imports: AsyncImageService, AsyncMSService, AsyncJobService, AsyncQAService
   - Update dependencies: get_async_* versions
   - Add await to all service calls

#### Priority 2: Simple Routes
4. **logs.py** (1 endpoint)
   - Update to use AsyncJobService
   - Add await to read_log_tail

5. **stats.py** (1 endpoint)
   - Already async, just verify

6. **cal.py** (1 endpoint)
   - Create AsyncCalRepository
   - Update to use async DB access

#### Priority 3: Non-DB Routes
7. **queue.py** (4 endpoints)
   - Already async handlers
   - Verify no blocking calls

8. **cache.py** (3 endpoints)
   - Already async handlers
   - Verify cache_manager is async-safe

9. **services.py** (2 endpoints)
   - Already async handlers
   - Verify services_monitor is async

### Step 6: Update Dependencies
Add to dependencies.py:
- `get_async_qa_service()`
- `get_async_cal_repository()`

### Step 7: Testing Strategy
1. **Unit Tests**: Test each async service method
2. **Integration Tests**: Test route handlers with async services
3. **Transaction Tests**: Verify async transaction management
4. **Error Handling**: Test async error propagation
5. **Performance Tests**: Verify non-blocking behavior

### Step 8: Error Handling Patterns
Ensure all async routes handle:
- `RecordNotFoundError` - 404 responses
- `DatabaseQueryError` - 500 responses
- `FileNotAccessibleError` - 403/404 responses
- Async context managers properly closed
- Transaction rollback on errors

---

## Key Patterns to Follow

### 1. Service Method Conversion
```python
# Sync (before)
def get_item(self, id: str) -> Item:
    return self.repo.get_by_id(id)

# Async (after)
async def get_item(self, id: str) -> Item:
    return await self.repo.get_by_id(id)
```

### 2. Route Handler Conversion
```python
# Before
@router.get("/{id}")
async def get_item(
    id: str,
    service: Service = Depends(get_service),
):
    item = service.get_item(id)  # Blocking!
    return item

# After
@router.get("/{id}")
async def get_item(
    id: str,
    service: AsyncService = Depends(get_async_service),
):
    item = await service.get_item(id)  # Non-blocking!
    return item
```

### 3. File I/O Conversion
```python
# Sync (before)
with open(path) as f:
    content = f.read()

# Async (after)
import aiofiles
async with aiofiles.open(path) as f:
    content = await f.read()
```

### 4. Transaction Management
```python
# Ensure proper async context manager usage
async with db_pool.products_db() as conn:
    try:
        cursor = await conn.execute(query, params)
        result = await cursor.fetchone()
        await conn.commit()
    except Exception as e:
        await conn.rollback()
        raise DatabaseQueryError("operation", str(e))
```

---

## Success Criteria

### Functional Requirements
- ✅ All 11 route files converted to async
- ✅ All service calls use await
- ✅ No blocking I/O in async handlers
- ✅ Proper error handling in async context
- ✅ Transaction management works correctly

### Performance Requirements
- ✅ Routes handle concurrent requests without blocking
- ✅ Database connections properly pooled
- ✅ No thread pool exhaustion under load

### Code Quality Requirements
- ✅ Type hints on all async methods
- ✅ Consistent error handling patterns
- ✅ Proper async context manager usage
- ✅ No Pylance/mypy errors

---

## Risk Mitigation

### Risk 1: File I/O Blocking
**Mitigation**: Use aiofiles for async file operations

### Risk 2: Transaction Deadlocks
**Mitigation**: Proper async context manager usage, short transaction scopes

### Risk 3: Error Propagation
**Mitigation**: Consistent try/except patterns, proper async exception handling

### Risk 4: Testing Gaps
**Mitigation**: Comprehensive test suite covering async scenarios

---

## Timeline Estimate

- **Step 1-3** (Extend Services): 30 minutes
- **Step 4** (Cal Repository): 15 minutes
- **Step 5** (Migrate Routes): 90 minutes (10 min per route)
- **Step 6** (Dependencies): 10 minutes
- **Step 7** (Testing): 45 minutes
- **Step 8** (Error Handling Review): 30 minutes

**Total Estimated Time**: 3.5 hours

---

## Next Actions

1. ✅ Review and approve this plan
2. Extend AsyncJobService with missing methods
3. Extend AsyncMSService with missing methods
4. Create AsyncQAService
5. Create AsyncCalRepository
6. Migrate route files one by one
7. Test each route after migration
8. Final integration testing
9. Update documentation
