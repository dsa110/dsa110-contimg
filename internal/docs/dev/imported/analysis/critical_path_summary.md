# Critical Path Summary: Pre-Flight Checklist for `create_mosaic_centered.py`

**Date:** 2025-11-12  
**Purpose:** Identify what must be completed before `create_mosaic_centered.py`
can reliably accomplish its goal

---

## Executive Summary

**Current Status:** `create_mosaic_centered.py` relies on `MosaicOrchestrator`,
which internally uses Stages 1-6. While the orchestrator logic exists, several
gaps prevent reliable production use.

**Critical Blockers:**

1. **No API exposure** - Orchestrator only accessible via CLI scripts
2. **No error recovery** - Failures require manual intervention
3. **No monitoring** - Limited visibility into orchestrator workflow status
4. **Incomplete automation** - Stages 7-8 (photometry, ESE detection) not
   integrated

**Recommendation:** Complete Phase 1 Priority 1 items before production use.

---

## Critical Path Items (Must Complete Before Production)

### 1. Mosaic Creation API Exposure ⚠️ **BLOCKER**

**Why Critical:**

- `create_mosaic_centered.py` is CLI-only, limiting programmatic access
- No way to monitor or manage orchestrator workflows via API
- Cannot integrate with frontend dashboard or other automation systems

**What's Needed:**

- `POST /api/mosaics/create` endpoint
- Background job adapter for orchestrator
- Job status tracking and SSE log streaming

**Impact if Missing:** High - Blocks programmatic access, limits observability

**Estimated Effort:** 2-3 days

---

### 2. Error Handling and Recovery ⚠️ **BLOCKER**

**Why Critical:**

- Orchestrator workflows can fail at any stage (conversion, calibration,
  imaging, mosaic)
- No retry logic or recovery mechanisms
- Failures require manual investigation and restart

**What's Needed:**

- Retry logic with exponential backoff
- State tracking in `mosaic_groups` table (error messages, retry counts)
- Recovery mechanisms (resume from last successful stage)
- Error reporting and alerting

**Impact if Missing:** High - Production workflows will fail silently or require
constant manual intervention

**Estimated Effort:** 3-4 days

---

### 3. Monitoring and Observability ⚠️ **HIGH PRIORITY**

**Why Critical:**

- No visibility into orchestrator workflow progress
- Cannot track success/failure rates
- Difficult to debug issues in production

**What's Needed:**

- Workflow status endpoints (`GET /api/mosaics/{group_id}/status`)
- Progress tracking (which stage is currently executing)
- Log aggregation and search
- Metrics collection (time per stage, success rates)

**Impact if Missing:** Medium-High - Limits operational visibility and debugging
capability

**Estimated Effort:** 2-3 days

---

## Important but Not Blocking

### 4. Batch Conversion API

**Why Important:**

- Enables efficient processing of multiple time windows
- Complements orchestrator workflow

**Impact if Missing:** Medium - Can work around with individual jobs

**Estimated Effort:** 1-2 days

---

### 5. Publishing CLI

**Why Important:**

- Enables manual control and debugging
- Useful for troubleshooting failed publishes

**Impact if Missing:** Low - API endpoints exist, CLI is convenience

**Estimated Effort:** 1-2 days

---

## Pre-Flight Checklist

Before using `create_mosaic_centered.py` in production:

### Must Have (Blockers):

- [ ] **Mosaic Creation API exposed** (`POST /api/mosaics/create`)
- [ ] **Error handling and recovery** (retry logic, state tracking)
- [ ] **Monitoring endpoints** (workflow status, progress tracking)
- [ ] **Integration tests** (end-to-end workflow validation)

### Should Have (High Priority):

- [ ] **Batch conversion API** (efficiency)
- [ ] **Publishing CLI** (debugging)
- [ ] **Error alerting** (notifications on failures)

### Nice to Have (Quality of Life):

- [ ] **Unified QA CLI** (convenience)
- [ ] **Photometry API execution** (programmatic access)
- [ ] **ESE Detection automation** (science pipeline)

---

## Recommended Implementation Order

### Week 1: Critical Blockers

1. **Day 1-2:** Mosaic Creation API Exposure
2. **Day 3-4:** Error Handling and Recovery
3. **Day 5:** Monitoring Endpoints
4. **Day 6-7:** Integration Testing

### Week 2: High Priority Items

1. **Day 8-9:** Batch Conversion API
2. **Day 10:** Publishing CLI
3. **Day 11-12:** Error Alerting
4. **Day 13-14:** Testing and Validation

**Total:** 2 weeks to production-ready state

---

## Risk Assessment

### High Risk:

- **Orchestrator failures in production** - Mitigated by error handling and
  monitoring
- **Database concurrency issues** - Mitigated by proper locking and WAL mode

### Medium Risk:

- **API performance** - Mitigated by async processing and progress tracking
- **Integration complexity** - Mitigated by incremental testing

---

## Success Criteria

**Production-Ready When:**

1. ✅ Mosaic Creation API functional and tested
2. ✅ Error handling prevents silent failures
3. ✅ Monitoring provides visibility into workflow status
4. ✅ Integration tests pass for end-to-end workflow
5. ✅ `create_mosaic_centered.py` can be called via API with confidence

---

## Next Steps

1. **Review this checklist** with stakeholders
2. **Prioritize blockers** based on business needs
3. **Begin implementation** with Week 1 items
4. **Track progress** using issue tracker
5. **Validate** with integration tests before production deployment

---

## Related Documents

- **Full Roadmap:** `docs/dev/analysis/development_roadmap.md`
- **Batch Mode Assessment:**
  `docs/dev/analysis/batch_mode_development_assessment.md`
- **Automation Assessment:**
  `docs/dev/analysis/automation_assessment_justification.md`
- **Architecture:** `docs/concepts/streaming_vs_orchestrator.md`
