# DSA-110 Continuum Imaging Pipeline - TODO Roadmap

**Last Updated**: November 27, 2025  
**Purpose**: Comprehensive roadmap for remaining TODOs and future enhancements  
**Status**: Living document - update as items are completed

---

## Executive Summary

This roadmap consolidates all remaining TODO items from archived documentation,
code comments, and system analysis. Items are prioritized by impact and
organized into actionable phases.

**Overall Status**: Core pipeline is production-ready. Remaining items are
enhancements, operational improvements, and future features.

---

## Priority Legend

- 🔴 **CRITICAL** - Blocks production or causes failures
- 🟠 **HIGH** - Important for operations or user experience
- 🟡 **MEDIUM** - Nice to have, improves efficiency
- 🟢 **LOW** - Future enhancement, optional

---

## Phase 1: Critical Fixes (Complete in 1-2 days)

### 1.1 CI/CD Workflow Cleanup 🔴

**Issue**: Placeholder step in GitHub Actions workflow  
**Location**: `.github/workflows/validation-tests.yml:112`  
**Current State**: Commented-out step with TODO

**Tasks**:

- [ ] **Decision**: Implement or remove the validation test step
  - Option A: Create `test_enhanced_pipeline_production.sh` script
  - Option B: Remove the placeholder step and update workflow
- [ ] If implementing: Define test scope
  - End-to-end pipeline test with synthetic data
  - Performance benchmarks (throughput, latency)
  - Resource usage validation (memory, disk)
- [ ] If removing: Clean up workflow file and artifact upload steps
- [ ] Update workflow documentation

**Estimated Effort**: 4-6 hours (implement) or 30 minutes (remove)  
**Assignee**: DevOps/Pipeline maintainer  
**Dependencies**: None

**Implementation Notes**:

```bash
# Option A: Create test script
scripts/ops/tests/test_enhanced_pipeline_production.sh
- Spawn synthetic observation (16 subbands)
- Run conversion → calibration → imaging
- Validate outputs and performance metrics
- Clean up test artifacts

# Option B: Update workflow
Remove lines 112-114 from validation-tests.yml
Update step comments
```

---

### 1.2 Archive CODE_QUALITY_IMPROVEMENTS_GUIDE.md 🟠

**Issue**: Guide lists TODOs that have been completed  
**Location**: `docs/archive/reports/CODE_QUALITY_IMPROVEMENTS_GUIDE.md`  
**Current State**: 87% of listed TODOs are complete

**Tasks**:

- [x] Verify completion status (DONE - see investigation report)
- [ ] Add completion summary to document header
- [ ] Update "Progress Tracking" section with completion dates
- [ ] Move to completed section: `docs/archive/reports/completed/`
- [ ] Create redirect or note in main docs

**Estimated Effort**: 1 hour  
**Assignee**: Documentation maintainer  
**Dependencies**: None

**Completion Summary to Add**:

```markdown
## Completion Status (Updated: 2025-11-27)

✅ **COMPLETED** - All major code quality improvements implemented

- Logging Consistency: 2/3 complete (67%)
- Error Handling: 2/2 complete (100%)
- Type Safety: 3/3 complete (100%)
- **Overall: 7/8 complete (87%)**

See: TODO_INVESTIGATION_REPORT.md for full verification details.
```

---

## Phase 2: Operational Improvements (2-3 weeks)

### 2.1 Container Health Notification System 🟠

**Issue**: Monitoring script lacks notification capabilities  
**Location**: `scripts/ops/monitor-containers.sh:102`  
**Current State**: Placeholder function logs but doesn't notify

**Tasks**:

- [ ] **Design**: Choose notification method(s)
  - Email via sendmail/SMTP
  - Slack webhook integration
  - PagerDuty/Opsgenie for critical alerts
  - System log + systemd journal
- [ ] Implement notification module
  - Create `scripts/ops/lib/notifications.sh` library
  - Support multiple backends (email, Slack, webhook)
  - Configuration via environment variables
- [ ] Update `send_notification()` function to use new module
- [ ] Add notification configuration to systemd service
- [ ] Test notification delivery
- [ ] Document notification setup in ops guide

**Estimated Effort**: 8-12 hours  
**Assignee**: Operations engineer  
**Dependencies**: Access to notification service (Slack, email server)

**Implementation Plan**:

```bash
# 1. Create notification library
scripts/ops/lib/notifications.sh:
  - send_email(subject, body, recipients)
  - send_slack(channel, message, severity)
  - send_webhook(url, payload)
  - send_notification_wrapper() # Dispatches to configured backends

# 2. Configuration
ops/systemd/contimg.env:
  NOTIFICATION_METHOD=slack,email
  SLACK_WEBHOOK_URL=...
  EMAIL_RECIPIENTS=ops@example.com
  ALERT_THRESHOLD=critical

# 3. Update monitor-containers.sh
Replace TODO with:
  send_notification "Container Alert" \
    "Container $container unhealthy\nStatus: $status\nHealth: $health" \
    "critical"
```

---

### 2.2 Database Location Consolidation 🟡

**Issue**: Some databases in `/stage/`, should be in `/data/`  
**Location**: Multiple (see analysis)  
**Current State**:

- Operational DBs: `/data/dsa110-contimg/state/` ✅
- Catalog DBs: `/stage/dsa110-contimg/state/` ❌

**Tasks**:

- [ ] Audit all database locations
  - List all .sqlite3 files in /stage/ and /data/
  - Identify which are active vs. archived
- [ ] Plan migration strategy
  - Stop services that access databases
  - Copy databases to new location
  - Update configuration files
  - Test access from new location
  - Remove old copies
- [ ] Update paths in code
  - Search for hardcoded `/stage/` paths
  - Update to use environment variables
  - Update ops/systemd/contimg.env
- [ ] Update documentation
  - DIRECTORY_ARCHITECTURE.md
  - Operations guide
  - Environment setup docs

**Estimated Effort**: 6-8 hours  
**Assignee**: DevOps engineer  
**Dependencies**: Service downtime window

**Migration Commands**:

```bash
# 1. Stop services
sudo systemctl stop dsa110-*.service

# 2. Migrate databases
mkdir -p /data/dsa110-contimg/state/catalogs
rsync -av --progress /stage/dsa110-contimg/state/*.sqlite3 \
  /data/dsa110-contimg/state/catalogs/

# 3. Update environment
# In ops/systemd/contimg.env:
CATALOG_DB_DIR=/data/dsa110-contimg/state/catalogs

# 4. Verify and restart
sudo systemctl start dsa110-*.service
# Monitor logs for errors
```

---

### 2.3 Data Retention Policy Implementation 🟡

**Issue**: No automatic cleanup of old data  
**Location**: `docs/architecture/architecture/DIRECTORY_ARCHITECTURE.md:445`  
**Current State**: Manual cleanup required, risk of disk space issues

**Tasks**:

- [ ] **Define retention policy**
  - Raw HDF5 files: Keep 30 days, then delete
  - Measurement Sets: Keep 90 days for calibrators, 30 days for science
  - Images (FITS): Keep 180 days, then archive to tape
  - Calibration tables: Keep indefinitely
  - Failed processing: Keep 7 days for debugging
- [ ] Implement cleanup script
  - Create `scripts/ops/cleanup_old_data.sh`
  - Query database for files older than retention period
  - Verify files are in database before deletion
  - Support dry-run mode
  - Log all deletions
- [ ] Create systemd timer for automatic cleanup
  - Daily cleanup job
  - Low priority (ionice/nice)
  - Alert if cleanup fails
- [ ] Update database on deletion
  - Mark files as archived/deleted
  - Keep metadata for audit trail
- [ ] Document retention policy

**Estimated Effort**: 12-16 hours  
**Assignee**: Pipeline engineer + Operations  
**Dependencies**: Database location consolidation (2.2)

**Implementation**:

```bash
# scripts/ops/cleanup_old_data.sh
#!/bin/bash
set -euo pipefail

RETENTION_HDF5_DAYS=30
RETENTION_MS_SCIENCE_DAYS=30
RETENTION_MS_CALIBRATOR_DAYS=90
RETENTION_IMAGES_DAYS=180
RETENTION_FAILED_DAYS=7

DRY_RUN=${DRY_RUN:-false}
PRODUCTS_DB=/data/dsa110-contimg/state/products.sqlite3

cleanup_old_files() {
  local file_type=$1
  local retention_days=$2
  local base_path=$3

  # Query database for old files
  sqlite3 "$PRODUCTS_DB" <<EOF
SELECT path FROM products
WHERE type='$file_type'
  AND created_at < datetime('now', '-$retention_days days')
  AND status NOT IN ('archived', 'deleted');
EOF

  # Delete files and update database
  # ... implementation
}

# Run cleanup for each file type
cleanup_old_files "hdf5" $RETENTION_HDF5_DAYS "/data/incoming"
cleanup_old_files "ms_science" $RETENTION_MS_SCIENCE_DAYS "/stage/dsa110-contimg/ms/science"
# ... etc
```

**Systemd Timer**:

```ini
# ops/systemd/data-retention-cleanup.timer
[Unit]
Description=Data Retention Cleanup Timer
After=network.target

[Timer]
OnCalendar=daily
OnBootSec=1h
Persistent=true

[Install]
WantedBy=timers.target
```

---

### 2.4 Archive Mechanism for Cold Storage 🟡

**Issue**: No workflow for archiving to tape/cold storage  
**Location**: `docs/architecture/architecture/DIRECTORY_ARCHITECTURE.md:449`  
**Current State**: Data accumulates indefinitely

**Tasks**:

- [ ] **Define archive strategy**
  - What to archive: Science images > 180 days, calibrated MS > 90 days
  - Archive format: TAR with compression (gzip/zstd)
  - Archive location: Tape library or S3 Glacier
  - Restore process: How to retrieve archived data
- [ ] Implement archive script
  - Create `scripts/ops/archive_to_cold_storage.sh`
  - Bundle files by observation date
  - Generate archive manifest
  - Verify archive integrity (checksums)
  - Update database with archive location
- [ ] Create archive index
  - New table in products.sqlite3: `archived_bundles`
  - Track: archive_id, bundle_path, file_list, created_at
  - Support archive search/restore
- [ ] Document archive/restore procedures
- [ ] Test archive and restore workflow

**Estimated Effort**: 16-24 hours  
**Assignee**: Storage engineer + Pipeline maintainer  
**Dependencies**:

- Archive storage availability (tape/S3)
- Retention policy (2.3) for identifying candidates

**Implementation**:

```bash
# scripts/ops/archive_to_cold_storage.sh

# 1. Query files eligible for archiving
SELECT path, observation_id, type
FROM products
WHERE created_at < datetime('now', '-180 days')
  AND status = 'completed'
  AND archived_at IS NULL
GROUP BY observation_id;

# 2. Create archive bundle
tar -czf archive_${observation_id}_${date}.tar.gz \
  --files-from=file_list.txt

# 3. Compute checksum
sha256sum archive_${observation_id}_${date}.tar.gz > archive.sha256

# 4. Copy to tape/S3
if [[ "$ARCHIVE_METHOD" == "tape" ]]; then
  mt -f /dev/st0 write archive_*.tar.gz
elif [[ "$ARCHIVE_METHOD" == "s3" ]]; then
  aws s3 cp archive_*.tar.gz s3://dsa110-archive/
fi

# 5. Update database
sqlite3 "$PRODUCTS_DB" <<EOF
INSERT INTO archived_bundles (bundle_id, archive_path, file_count, size_bytes)
VALUES ('$observation_id', '$archive_path', $file_count, $size_bytes);

UPDATE products
SET archived_at=datetime('now'), status='archived'
WHERE observation_id='$observation_id';
EOF

# 6. Delete local files (after verification)
```

---

## Phase 3: Test Coverage & Quality (1 week)

### 3.1 Implement Empty API Test Stubs 🟢

**Issue**: Placeholder test files with no implementation  
**Location**:

- `backend/tests/unit/api/test_api_hook_success_test.py`
- `backend/tests/unit/api/test_api_hook_verified_test.py`
- `backend/tests/unit/api/test_api_test_validation.py`

**Tasks**:

- [ ] **Understand API endpoint behavior**
  - Review routes.py for hook endpoints
  - Identify success/failure cases
  - Document expected behavior
- [ ] Implement test_api_hook_success_test.py
  - Test successful hook submission
  - Test hook validation
  - Test hook response format
- [ ] Implement test_api_hook_verified_test.py
  - Test verified hook state transitions
  - Test authentication if required
- [ ] Implement test_api_test_validation.py
  - Test input validation
  - Test error handling
  - Test edge cases
- [ ] Run tests and verify coverage
- [ ] Update test documentation

**Estimated Effort**: 8-12 hours  
**Assignee**: Backend developer  
**Dependencies**: None

**Test Structure Template**:

```python
# test_api_hook_success_test.py
import pytest
from fastapi.testclient import TestClient
from dsa110_contimg.api.routes import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

@pytest.mark.unit
def test_hook_success_returns_200(client):
    """Test hook endpoint returns 200 on success."""
    response = client.post("/api/hook/success", json={
        "observation_id": "test_obs_001",
        "status": "success"
    })
    assert response.status_code == 200
    assert "message" in response.json()

@pytest.mark.unit
def test_hook_success_validates_input(client):
    """Test hook endpoint validates required fields."""
    response = client.post("/api/hook/success", json={})
    assert response.status_code == 422  # Validation error
```

---

### 3.2 Logging Consistency Audit (Remaining Files) 🟢

**Issue**: 27 files need logging consistency check  
**Location**: Various modules  
**Current State**: 2/3 files checked, 1 remaining

**Tasks**:

- [ ] Generate list of all Python files in src/
- [ ] Filter for files without logger instances
- [ ] For each file, verify:
  - Has `logger = logging.getLogger(__name__)` or `structlog.get_logger()`
  - Uses logger instead of print statements
  - Logs at appropriate levels (DEBUG, INFO, WARNING, ERROR)
  - Includes context in log messages
- [ ] Create checklist and assign reviews
- [ ] Fix files without proper logging
- [ ] Update CODE_QUALITY_IMPROVEMENTS_GUIDE.md

**Estimated Effort**: 12-16 hours (depends on file count)  
**Assignee**: Code quality team  
**Dependencies**: None

**Audit Script**:

```bash
# scripts/ops/audit_logging.sh
#!/bin/bash

echo "Files without logger instance:"
find backend/src/dsa110_contimg -name "*.py" -type f | while read file; do
  if ! grep -q "logger = \|logger=" "$file"; then
    echo "❌ $file"
  fi
done

echo -e "\nFiles with print statements:"
find backend/src/dsa110_contimg -name "*.py" -type f | while read file; do
  if grep -q "print(" "$file"; then
    echo "⚠️  $file"
    grep -n "print(" "$file"
  fi
done
```

---

## Phase 4: Absurd Enhancements (4-6 weeks)

### 4.1 React Observability Dashboard (Phase D1) 🟠

**Goal**: Real-time web dashboard for Absurd task monitoring  
**Estimated Total Effort**: 25-30 hours

#### 4.1.1 Frontend Scaffolding (HIGH Priority)

- [ ] Set up React + TypeScript project in `frontend/absurd-dashboard/`
- [ ] Configure build system (Vite or Create React App)
- [ ] Set up routing (React Router)
- [ ] Create base layout components (Header, Sidebar, Content)
- [ ] Configure state management (Zustand or Redux)
- [ ] Set up API client (axios/fetch wrapper)

**Estimated Effort**: 4-6 hours

#### 4.1.2 Real-time WebSocket Connection (HIGH Priority)

- [ ] Add WebSocket endpoint to FastAPI backend
- [ ] Implement WebSocket manager for task events
- [ ] Create frontend WebSocket client
- [ ] Handle connection/reconnection logic
- [ ] Implement event streaming (task state changes)

**Estimated Effort**: 3-4 hours

**Backend WebSocket**:

```python
# backend/src/dsa110_contimg/api/websocket.py
from fastapi import WebSocket
import asyncio

class TaskEventManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def broadcast(self, event: dict):
        for connection in self.connections:
            await connection.send_json(event)

@app.websocket("/ws/tasks")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    manager.connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    finally:
        manager.connections.remove(websocket)
```

#### 4.1.3 Task Visualization (HIGH Priority)

- [ ] Create task list component (table/cards)
- [ ] Implement task state badges (pending/claimed/complete/failed)
- [ ] Add task detail modal
- [ ] Show task progress indicators
- [ ] Filter/search tasks by state, worker, queue
- [ ] Real-time task updates via WebSocket

**Estimated Effort**: 5-6 hours

#### 4.1.4 Metrics Charts (MEDIUM Priority)

- [ ] Install charting library (Recharts or Chart.js)
- [ ] Create throughput chart component
- [ ] Create queue depth chart
- [ ] Create success rate chart
- [ ] Add time range selector (1h, 6h, 24h, 7d)
- [ ] Implement chart data fetching from API

**Estimated Effort**: 4-5 hours

#### 4.1.5 Alert Display (MEDIUM Priority)

- [ ] Create alert notification component
- [ ] Fetch active alerts from API
- [ ] Display alert severity (info/warning/critical)
- [ ] Add alert acknowledge action
- [ ] Show alert history
- [ ] Desktop notifications for critical alerts

**Estimated Effort**: 3-4 hours

#### 4.1.6 Worker Management UI (LOW Priority)

- [ ] Create worker list component
- [ ] Show worker status (active/idle/stale/crashed)
- [ ] Display worker metrics (tasks completed, uptime)
- [ ] Add worker actions (pause, resume, stop)
- [ ] Show current task per worker
- [ ] Worker health indicators

**Estimated Effort**: 4-5 hours

**Tech Stack Decision Matrix**:

```
Frontend Framework: React 18 + TypeScript ✅
  - Already used in main dashboard
  - Good TypeScript support
  - Large ecosystem

State Management: Zustand ✅
  - Simpler than Redux for small app
  - Better TypeScript inference
  - Minimal boilerplate

Charts: Recharts ✅
  - React-native charting
  - Good documentation
  - Responsive

WebSocket: Native WebSocket API ✅
  - No extra dependencies
  - Built into browsers
  - FastAPI has native support
```

---

### 4.2 Distributed Mosaic Executor (Phase D2) 🟡

**Goal**: Parallelize mosaic creation across workers  
**Estimated Total Effort**: 16-20 hours

#### 4.2.1 Create Mosaic Task Adapter (MEDIUM Priority)

- [ ] Analyze existing mosaic daemon code
- [ ] Create `MosaicTaskAdapter` in absurd/adapter.py
- [ ] Define mosaic task parameters
  - Input images list
  - Mosaic configuration (overlap, weights)
  - Output path
- [ ] Implement execute() method
- [ ] Handle mosaic-specific errors
- [ ] Test adapter in isolation

**Estimated Effort**: 6-8 hours

**Implementation Outline**:

```python
# backend/src/dsa110_contimg/absurd/adapter.py

class MosaicTaskAdapter(TaskAdapter):
    """Adapter for create-mosaic tasks."""

    task_name = "create-mosaic"

    def execute(self, params: dict) -> dict:
        """
        Execute mosaic creation.

        Args:
            params: {
                "input_images": ["/path/img1.fits", ...],
                "mosaic_config": {...},
                "output_path": "/path/output.fits"
            }

        Returns:
            {"mosaic_path": str, "stats": dict}
        """
        from dsa110_contimg.mosaic.orchestrator import create_mosaic

        input_images = params["input_images"]
        config = params["mosaic_config"]
        output_path = params["output_path"]

        # Create mosaic
        result = create_mosaic(
            input_images=input_images,
            output_path=output_path,
            **config
        )

        return {
            "mosaic_path": str(output_path),
            "stats": result.stats
        }
```

#### 4.2.2 Parallel Mosaic Processing (MEDIUM Priority)

- [ ] Update mosaic manager to spawn multiple tasks
- [ ] Implement mosaic task queue
- [ ] Add mosaic priority logic (urgent vs. batch)
- [ ] Handle task dependencies (wait for all tiles)
- [ ] Implement result aggregation

**Estimated Effort**: 4-6 hours

#### 4.2.3 Update AbsurdStreamingMosaicManager (MEDIUM Priority)

- [ ] Locate current streaming mosaic manager
- [ ] Replace daemon pattern with task spawning
- [ ] Update to use Absurd task queue
- [ ] Maintain backward compatibility
- [ ] Add configuration for max parallel mosaics

**Estimated Effort**: 4-6 hours

#### 4.2.4 Test Mosaic Distribution (MEDIUM Priority)

- [ ] Create test dataset (multiple tiles)
- [ ] Spawn mosaic tasks across workers
- [ ] Verify parallel execution
- [ ] Check output quality
- [ ] Measure performance improvement

**Estimated Effort**: 2-4 hours

---

### 4.3 Advanced Workflow Features (Phase D3) 🟢

**Goal**: Enterprise-grade workflow orchestration  
**Estimated Total Effort**: 60-80 hours (HIGH complexity)

#### 4.3.1 DAG-based Dependencies (LOW Priority, HIGH Complexity)

- [ ] Design DAG representation (JSON/YAML)
- [ ] Implement dependency graph parser
- [ ] Create task dependency tracker
- [ ] Add dependency validation (no cycles)
- [ ] Implement dependency resolution
- [ ] Update worker to check dependencies before claiming
- [ ] Add visualization of DAG in dashboard

**Estimated Effort**: 20-24 hours

**DAG Example**:

```yaml
# workflow.yaml
name: science_observation_pipeline
version: 1.0

tasks:
  - id: convert
    type: convert-hdf5-to-ms
    params: { ... }

  - id: calibrate
    type: calibrate-ms
    depends_on: [convert]
    params: { ... }

  - id: image_field1
    type: image-field
    depends_on: [calibrate]
    params: { field_id: 1 }

  - id: image_field2
    type: image-field
    depends_on: [calibrate]
    params: { field_id: 2 }

  - id: mosaic
    type: create-mosaic
    depends_on: [image_field1, image_field2]
    params: { ... }
```

#### 4.3.2 Dynamic Task Prioritization (MEDIUM Priority, MEDIUM Complexity)

- [ ] Design priority scoring algorithm
- [ ] Add priority field to tasks table
- [ ] Implement priority calculation factors:
  - Task age (older = higher priority)
  - Queue depth (urgent if queue is full)
  - Resource availability
  - User-defined priority
- [ ] Update worker claim logic to prefer high priority
- [ ] Add priority boost for stalled tasks
- [ ] Monitor priority effectiveness

**Estimated Effort**: 8-12 hours

#### 4.3.3 Multi-queue Support (LOW Priority, LOW Complexity)

- [ ] Design queue schema (name, priority, max_workers)
- [ ] Add queue_name to tasks table (already exists!)
- [ ] Update worker to claim from specific queues
- [ ] Add queue management API endpoints
- [ ] Support queue-specific configuration
- [ ] Add queue monitoring to dashboard

**Estimated Effort**: 6-8 hours

#### 4.3.4 Web API for Task Submission (LOW Priority, MEDIUM Complexity)

- [ ] Design REST API for task submission
- [ ] Add authentication/authorization
- [ ] Implement POST /api/tasks endpoint
- [ ] Add task validation
- [ ] Return task ID and tracking URL
- [ ] Add bulk task submission endpoint
- [ ] Document API with OpenAPI/Swagger

**Estimated Effort**: 8-12 hours

**API Design**:

```python
@app.post("/api/v1/tasks")
async def submit_task(
    task: TaskSubmission,
    auth: Auth = Depends(get_auth)
):
    """
    Submit a new task to the queue.

    POST /api/v1/tasks
    {
        "task_name": "convert-hdf5-to-ms",
        "params": {...},
        "priority": 5,
        "queue_name": "dsa110-pipeline"
    }

    Returns:
    {
        "task_id": "uuid",
        "status": "pending",
        "tracking_url": "/api/v1/tasks/uuid"
    }
    """
    task_id = await absurd.spawn_task(
        task_name=task.task_name,
        params=task.params,
        priority=task.priority,
        queue_name=task.queue_name
    )
    return {"task_id": task_id, "status": "pending"}
```

#### 4.3.5 Task Scheduling (cron-like) (LOW Priority, MEDIUM Complexity)

- [ ] Design schedule schema (cron expression, task template)
- [ ] Implement cron parser and validator
- [ ] Create scheduler service
- [ ] Add schedule CRUD API endpoints
- [ ] Implement schedule execution logic
- [ ] Add schedule management UI
- [ ] Monitor scheduled task execution

**Estimated Effort**: 12-16 hours

**Note**: Some scheduling functionality may already exist - verify with
`backend/src/dsa110_contimg/absurd/` code.

#### 4.3.6 Workflow Templates (LOW Priority, HIGH Complexity)

- [ ] Design template schema (parameterized workflows)
- [ ] Implement template parser
- [ ] Add template validation
- [ ] Create template library/registry
- [ ] Add template instantiation API
- [ ] Build template editor UI
- [ ] Add template versioning

**Estimated Effort**: 16-20 hours

---

## Phase 5: Documentation & Polish (1 week)

### 5.1 Complete Absurd Documentation 🟢

**Missing Documentation**:

- [ ] Calibrator registration guide
  - How to add new calibrators
  - Calibrator catalog format
  - Testing calibrator configuration
- [ ] Performance tuning guide
  - Worker count optimization
  - Database connection pooling
  - Memory/CPU tuning
  - Disk I/O optimization
  - Benchmark methodology

**Estimated Effort**: 8-12 hours  
**Assignee**: Technical writer + Pipeline engineer

---

### 5.2 Update System Architecture Diagrams 🟢

- [ ] Update DIRECTORY_ARCHITECTURE.md with current state
- [ ] Create data flow diagrams for new features
- [ ] Document Absurd task lifecycle
- [ ] Add troubleshooting decision trees
- [ ] Update deployment diagrams

**Estimated Effort**: 6-8 hours

---

## Implementation Timeline

### Sprint 1 (Week 1-2): Critical Fixes

- Phase 1: Complete all critical items
- Start Phase 2.1 (Notification system)

### Sprint 2 (Week 3-4): Operational Improvements

- Complete Phase 2 (Ops improvements)
- Start Phase 3.1 (Test stubs)

### Sprint 3 (Week 5-6): Test Coverage

- Complete Phase 3 (Test coverage)
- Start Phase 4.1 (React dashboard)

### Sprint 4-6 (Week 7-12): Absurd Enhancements

- Phase 4.1: React Dashboard (Sprint 4)
- Phase 4.2: Mosaic Executor (Sprint 5)
- Phase 4.3: Advanced Features (Sprint 6)

### Sprint 7 (Week 13): Documentation

- Phase 5: Complete all documentation

---

## Success Metrics

### Phase 1 Success Criteria

- ✅ CI workflow has no placeholder steps
- ✅ All archived docs have completion status

### Phase 2 Success Criteria

- ✅ Alerts are delivered reliably (test with mock failure)
- ✅ All databases in `/data/dsa110-contimg/state/`
- ✅ Old data automatically cleaned up (verify logs)
- ✅ Archive mechanism tested with sample data

### Phase 3 Success Criteria

- ✅ Test coverage > 80% for API module
- ✅ All source files have proper logging
- ✅ CI passes all unit tests

### Phase 4 Success Criteria

- ✅ Dashboard shows real-time task updates
- ✅ Multiple mosaics process in parallel
- ✅ DAG workflows execute correctly
- ✅ Performance meets benchmarks

---

## Risks and Mitigations

### High Risk Items

1. **Database migration (2.2)** - Could cause service disruption
   - Mitigation: Test in staging first, have rollback plan
2. **DAG implementation (4.3.1)** - High complexity, potential bugs
   - Mitigation: Start with simple cases, extensive testing
3. **Archive mechanism (2.4)** - Data loss risk
   - Mitigation: Verify checksums, test restore before production

### Medium Risk Items

1. **Notification system (2.1)** - External dependencies
   - Mitigation: Support multiple backends, graceful degradation
2. **React dashboard (4.1)** - Scope creep potential
   - Mitigation: MVP first, iterate based on feedback

---

## Appendix: Quick Reference

### File Locations

- CI Workflow: `.github/workflows/validation-tests.yml`
- Monitor Script: `scripts/ops/monitor-containers.sh`
- Architecture Doc: `docs/architecture/architecture/DIRECTORY_ARCHITECTURE.md`
- Absurd Status: `backend/docs/reports/ABSURD_IMPLEMENTATION_STATUS.md`
- Test Stubs: `backend/tests/unit/api/test_api_*.py`

### Key Commands

```bash
# Check test stubs
pytest backend/tests/unit/api/ -v

# Audit logging
./scripts/ops/audit_logging.sh

# Monitor database locations
find /data /stage -name "*.sqlite3" 2>/dev/null

# Check CI workflow
gh workflow view validation-tests
```

### Contact/Ownership

- CI/CD: DevOps team
- Operations: Ops engineer
- Backend: Pipeline maintainers
- Frontend: Dashboard team
- Documentation: Technical writers

---

**End of Roadmap**

_This is a living document. Update as tasks are completed or priorities change._
