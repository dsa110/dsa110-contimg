# Production Readiness Roadmap

**Created:** December 4, 2025  
**Goal:** All dashboard features operational with real backend support in a production environment

This document outlines the steps needed to bring the DSA-110 continuum imaging pipeline to a production-ready state with all frontend features fully integrated with the backend.

---

## Executive Summary

The pipeline has **strong frontend coverage** (9 major features implemented) but **backend gaps** that need to be filled. Additionally, there are critical pipeline reliability issues documented in `pipeline_weaknesses.md` that must be addressed.

### Current State

| Layer              | Status                                                              |
| ------------------ | ------------------------------------------------------------------- |
| **Frontend UI**    | ✅ 9/9 features implemented with tests                              |
| **Backend API**    | ⚠️ ~70% coverage - some features lack endpoints                     |
| **Database**       | ⚠️ Schema exists for core features; missing tables for new features |
| **Pipeline Core**  | ⚠️ Functional but has reliability gaps                              |
| **Monitoring/Ops** | ✅ Prometheus + Grafana ready                                       |

---

## Phase 1: Backend API Completion (1-2 weeks)

### 1.1 Create Missing API Endpoints

| Feature                 | Current State                   | Action Required                                   |
| ----------------------- | ------------------------------- | ------------------------------------------------- |
| **Saved Queries**       | ❌ No backend                   | Create `saved_queries.py` route with CRUD         |
| **Backup/Restore**      | ⚠️ Partial (retention has flag) | Create dedicated `backup.py` route                |
| **Pipeline Triggers**   | ⚠️ Absurd has scheduling        | Expose trigger API in `triggers.py` route         |
| **Jupyter Integration** | ❌ Frontend-only                | Create `jupyter.py` route for notebook management |
| **VO Export**           | ⚠️ Sources have `/export`       | Expand to general VO export in `vo_export.py`     |

#### 1.1.1 Saved Queries Backend (`backend/src/dsa110_contimg/api/routes/saved_queries.py`)

```python
# Required endpoints:
POST   /api/saved-queries           # Create query
GET    /api/saved-queries           # List queries (with visibility filter)
GET    /api/saved-queries/{id}      # Get single query
PUT    /api/saved-queries/{id}      # Update query
DELETE /api/saved-queries/{id}      # Delete query
POST   /api/saved-queries/{id}/fork # Fork a shared query
```

**Database table:**

```sql
CREATE TABLE saved_queries (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    filters TEXT NOT NULL,  -- JSON serialized FilterState
    target_type TEXT NOT NULL,  -- 'images', 'sources', 'jobs', 'ms'
    visibility TEXT DEFAULT 'private',  -- 'private', 'team', 'public'
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX idx_saved_queries_visibility ON saved_queries(visibility);
CREATE INDEX idx_saved_queries_target ON saved_queries(target_type);
```

#### 1.1.2 Backup/Restore Backend (`backend/src/dsa110_contimg/api/routes/backup.py`)

```python
# Required endpoints:
POST   /api/backup/create           # Trigger backup
GET    /api/backup/status           # Current backup status
GET    /api/backup/history          # List past backups
POST   /api/backup/restore/{id}     # Restore from backup
POST   /api/backup/validate/{id}    # Validate backup integrity
DELETE /api/backup/{id}             # Delete backup
```

#### 1.1.3 Pipeline Triggers Backend (`backend/src/dsa110_contimg/api/routes/triggers.py`)

The Absurd scheduler already has trigger infrastructure. Expose it:

```python
# Required endpoints:
GET    /api/triggers                # List all triggers
POST   /api/triggers                # Create trigger
GET    /api/triggers/{id}           # Get trigger details
PUT    /api/triggers/{id}           # Update trigger
DELETE /api/triggers/{id}           # Delete trigger
POST   /api/triggers/{id}/execute   # Manual trigger execution
GET    /api/triggers/{id}/history   # Execution history
```

### 1.2 Database Schema Migration

Add missing tables to unified `pipeline.sqlite3`:

```sql
-- Saved queries (for shared filters feature)
CREATE TABLE IF NOT EXISTS saved_queries (...);

-- Backup metadata
CREATE TABLE IF NOT EXISTS backup_history (
    id TEXT PRIMARY KEY,
    backup_path TEXT NOT NULL,
    backup_type TEXT NOT NULL,  -- 'full', 'incremental', 'database_only'
    size_bytes INTEGER,
    created_at TEXT NOT NULL,
    created_by TEXT,
    status TEXT DEFAULT 'completed',
    validation_status TEXT,
    validated_at TEXT
);

-- Pipeline triggers (if not using Absurd tables)
CREATE TABLE IF NOT EXISTS pipeline_triggers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    trigger_type TEXT NOT NULL,  -- 'schedule', 'event', 'manual'
    schedule TEXT,  -- cron expression
    event_pattern TEXT,  -- event type to listen for
    action TEXT NOT NULL,  -- 'convert', 'calibrate', 'image', 'custom'
    action_params TEXT,  -- JSON
    enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    last_triggered_at TEXT
);
```

---

## Phase 2: Pipeline Reliability Fixes (2-3 weeks)

Address critical issues from `pipeline_weaknesses.md`:

### 2.1 Calibration System Hardening

| Issue                             | Fix                                           | Priority    |
| --------------------------------- | --------------------------------------------- | ----------- |
| **Forward-only validity**         | Implement ±12hr bidirectional windows         | 🔴 Critical |
| **No interpolation between days** | Add nearest-neighbor or linear interpolation  | 🟡 High     |
| **Single calibrator fragility**   | Add fallback calibrator selection             | 🟡 High     |
| **No calibration QA**             | Implement SNR/flag checks before registration | 🔴 Critical |

**Implementation:**

```python
# backend/src/dsa110_contimg/calibration/registry.py

def find_best_calibration(target_mjd: float, dec_deg: float) -> Optional[CalibrationSet]:
    """Find calibration with bidirectional validity and quality checks."""
    # 1. Look for calibrations within ±12 hours
    candidates = query_calibrations_in_window(
        center_mjd=target_mjd,
        half_window_hours=12.0,
        min_snr=10.0,  # Quality gate
        max_flagged_fraction=0.3
    )

    # 2. Prefer closest in time
    if candidates:
        return min(candidates, key=lambda c: abs(c.mjd - target_mjd))

    # 3. Fallback to nearest available (with warning)
    return find_nearest_calibration(target_mjd, max_age_hours=48.0)
```

### 2.2 Transactional Processing

Implement proper state machine for MS processing:

```python
# States: pending → converting → converted → calibrating → calibrated → imaging → complete
#                  ↓             ↓              ↓             ↓
#               failed        failed         failed        failed

class MSProcessingState(Enum):
    PENDING = "pending"
    CONVERTING = "converting"
    CONVERTED = "converted"
    CALIBRATING = "calibrating"
    CALIBRATED = "calibrated"
    IMAGING = "imaging"
    COMPLETE = "complete"
    FAILED = "failed"

def transition_state(ms_id: str, from_state: MSProcessingState, to_state: MSProcessingState):
    """Atomic state transition with rollback on failure."""
    with database.transaction():
        current = get_ms_state(ms_id)
        if current != from_state:
            raise StateError(f"Expected {from_state}, got {current}")
        update_ms_state(ms_id, to_state)
```

### 2.3 Automatic Retry Logic

```python
@retry(
    max_attempts=3,
    backoff=exponential(base=30, max=300),
    retry_on=(CalibrationError, ImagingError)
)
async def process_ms_with_retry(ms_path: Path):
    """Process MS with automatic retry on transient failures."""
    ...
```

---

## Phase 3: Integration & Testing (1-2 weeks)

### 3.1 Frontend-Backend Integration

1. **Update API clients** to use real endpoints instead of mocks:

   - `frontend/src/api/savedQueries.ts` → real `/api/saved-queries`
   - `frontend/src/api/backup.ts` → real `/api/backup`
   - `frontend/src/api/triggers.ts` → real `/api/triggers`

2. **Add error boundaries** for API failures

3. **Implement optimistic updates** with rollback

### 3.2 Contract Tests

Create contract tests validating frontend-backend agreement:

```typescript
// frontend/src/api/__contracts__/savedQueries.contract.test.ts
describe("SavedQueries API Contract", () => {
  it("POST /saved-queries returns expected shape", async () => {
    const response = await api.post("/saved-queries", mockQuery);
    expect(response).toMatchSchema(SavedQuerySchema);
  });
});
```

```python
# backend/tests/contracts/test_saved_queries_contract.py
def test_create_saved_query_returns_expected_shape():
    response = client.post("/api/saved-queries", json=mock_query)
    assert response.status_code == 201
    assert_matches_schema(response.json(), SavedQuerySchema)
```

### 3.3 End-to-End Tests

```typescript
// frontend/e2e/saved-queries.spec.ts
test("user can save and load a query", async ({ page }) => {
  await page.goto("/images");
  await page.click('[data-testid="save-query-btn"]');
  await page.fill('[data-testid="query-name"]', "My Filter");
  await page.click('[data-testid="save-btn"]');

  // Reload and verify
  await page.reload();
  await page.click('[data-testid="load-query-btn"]');
  await expect(page.locator("text=My Filter")).toBeVisible();
});
```

---

## Phase 4: Operational Readiness (1 week)

### 4.1 Monitoring & Alerting

| Component   | Metric                    | Alert Threshold |
| ----------- | ------------------------- | --------------- |
| Calibration | Time since last valid cal | > 24 hours      |
| Conversion  | Queue depth               | > 100 pending   |
| Imaging     | Failure rate              | > 10% in 1hr    |
| Storage     | Disk usage                | > 85%           |
| API         | Response time p95         | > 2 seconds     |

**Prometheus rules:**

```yaml
# ops/monitoring/alerts/pipeline.yml
groups:
  - name: pipeline
    rules:
      - alert: StaleCalibration
        expr: time() - calibration_last_valid_timestamp > 86400
        for: 30m
        labels:
          severity: critical
        annotations:
          summary: "No valid calibration in 24+ hours"
```

### 4.2 Backup Strategy

| Data Type          | Frequency | Retention | Location                       |
| ------------------ | --------- | --------- | ------------------------------ |
| SQLite databases   | Hourly    | 7 days    | `/stage/backups/db/`           |
| Configuration      | On change | 30 days   | Git + `/stage/backups/config/` |
| Calibration tables | Daily     | 90 days   | `/stage/backups/caltables/`    |
| Full system        | Weekly    | 4 weeks   | Off-site NAS                   |

### 4.3 Documentation

- [ ] Runbook for common failure scenarios
- [ ] Architecture diagram updates
- [ ] API documentation (OpenAPI spec)
- [ ] User guide for new dashboard features

---

## Phase 5: Future Development (Ongoing)

### 5.1 Features on Backburner

| Feature                     | Description                        | Complexity |
| --------------------------- | ---------------------------------- | ---------- |
| **QA Rating Consensus**     | Multi-user rating aggregation      | Medium     |
| **Comments/Annotations**    | Threaded comments on data products | Medium     |
| **Real-time Collaboration** | WebSocket-based live updates       | High       |

### 5.2 Technical Debt Reduction

Per `dsa110-contimg-complexity-reduction-guide.md`:

1. **Configuration consolidation** → Single Pydantic Settings class
2. **Database unification** → Already on `pipeline.sqlite3`
3. **Dead code removal** → Remove unused writers/strategies
4. **Test overhaul** → Contract tests over mock-heavy unit tests

---

## Implementation Timeline

```
Week 1-2:  Phase 1 - Backend API completion
Week 3-4:  Phase 2 - Pipeline reliability fixes
Week 5:    Phase 3 - Integration & contract tests
Week 6:    Phase 4 - Operational readiness
Week 7+:   Phase 5 - Future development & debt reduction
```

---

## Success Criteria

### Minimum Viable Production (MVP)

- [ ] All 9 frontend features have working backend APIs
- [ ] Calibration validity is bidirectional (±12hr)
- [ ] Processing state machine prevents stuck jobs
- [ ] Automated retries for transient failures
- [ ] Alerting for critical failures
- [ ] Daily database backups

### Full Production Ready

- [ ] Contract tests for all API endpoints
- [ ] E2E tests for critical user workflows
- [ ] <1% job failure rate
- [ ] <5s p99 API response time
- [ ] Zero data loss in 30-day period
- [ ] Runbook covers 90% of failure scenarios

---

## Quick Start: First Steps

1. **Create `saved_queries.py` route** - Lowest-hanging fruit, frontend ready
2. **Add saved_queries table** to `pipeline.sqlite3` schema
3. **Wire frontend** to real API (remove mock adapter)
4. **Add contract test** for saved queries
5. **Repeat** for backup, triggers, etc.

---

## References

- `frontend/TODO.md` - Frontend feature status
- `pipeline_weaknesses.md` - Critical pipeline issues
- `dsa110-contimg-complexity-reduction-guide.md` - Technical debt roadmap
- `docs/DEVELOPMENT_ROADMAP.md` - High-level timeline
