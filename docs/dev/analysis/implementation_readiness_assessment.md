# Implementation Readiness Assessment

**Date:** 2025-11-12  
**Purpose:** Categorize roadmap tasks by implementation readiness - what can be
done directly vs what requires investigation

---

## Assessment Criteria

**✅ KNOW HOW TO IMPLEMENT:** Clear patterns exist in codebase, similar
implementations present, straightforward integration  
**⚠️ NEEDS INVESTIGATION:** Domain knowledge required, complex integration,
unclear patterns, or dependencies need exploration

---

## Phase 1: Complete Batch Mode Development

### Priority 1: Critical Gaps

#### 1.1 Stage 4: Mosaic Creation API Exposure

**Status:** ✅ **KNOW HOW TO IMPLEMENT** (with minor investigation)

**Confidence:** High (90%)

**What I Know:**

- FastAPI router pattern exists (`src/dsa110_contimg/api/routers/mosaics.py`)
- Job adapter pattern exists (`src/dsa110_contimg/api/job_adapters.py`)
- `MosaicOrchestrator.create_mosaic_centered_on_calibrator()` exists and works
- Job database schema exists (`database/jobs.py`)
- SSE log streaming pattern exists (seen in other endpoints)

**Implementation Pattern:**

```python
# Follow existing job adapter pattern:
# 1. Create endpoint in routers/mosaics.py
# 2. Create job adapter function in job_adapters.py
# 3. Use existing job creation/status tracking
# 4. Wrap orchestrator call with error handling
```

**What Needs Investigation:**

- ⚠️ **Job status tracking details:** Need to verify how job status updates work
  during long-running orchestrator workflows
- ⚠️ **SSE log streaming:** Need to check if orchestrator supports log streaming
  or if we need to wrap it
- ⚠️ **Error propagation:** Need to understand how orchestrator errors should be
  reported to API

**Estimated Investigation Time:** 2-4 hours  
**Estimated Implementation Time:** 1.5-2 days

---

#### 1.2 Stage 1: Batch Conversion API

**Status:** ✅ **KNOW HOW TO IMPLEMENT**

**Confidence:** Very High (95%)

**What I Know:**

- Batch job pattern exists (`src/dsa110_contimg/api/batch_jobs.py`)
- Conversion job adapter exists (`run_convert_job()` in `job_adapters.py`)
- Batch endpoints exist for calibration/imaging
- Time window handling is straightforward

**Implementation Pattern:**

```python
# Follow existing batch job pattern:
# 1. Create POST /api/batch/convert endpoint
# 2. Create batch job record
# 3. Create individual conversion jobs for each time window
# 4. Track batch status
```

**What Needs Investigation:**

- ✅ **Minimal** - Pattern is clear from existing batch implementations

**Estimated Investigation Time:** 1 hour  
**Estimated Implementation Time:** 1 day

---

#### 1.3 Stage 6: Publishing CLI

**Status:** ✅ **KNOW HOW TO IMPLEMENT**

**Confidence:** High (85%)

**What I Know:**

- CLI pattern exists (`calibration/cli.py`, `conversion/cli.py`)
- `data_registry.py` has functions: `publish_data_manual()`, `get_data()`,
  `trigger_auto_publish()`
- Database schema is clear (`data_registry` table)
- argparse pattern is standard

**Implementation Pattern:**

```python
# Follow existing CLI pattern:
# 1. Create database/cli.py with argparse subcommands
# 2. Import data_registry functions
# 3. Add subcommands: publish, status, retry, list
# 4. Use existing database connection patterns
```

**What Needs Investigation:**

- ⚠️ **Error handling:** Need to understand what errors `publish_data_manual()`
  can raise
- ⚠️ **Retry logic:** Need to understand what "retry" means in context of
  publishing (re-attempt move operation?)

**Estimated Investigation Time:** 2-3 hours  
**Estimated Implementation Time:** 1 day

---

### Priority 2: Quality of Life Improvements

#### 1.4 Stage 5: Unified QA CLI

**Status:** ✅ **KNOW HOW TO IMPLEMENT** (with investigation)

**Confidence:** Medium-High (75%)

**What I Know:**

- CLI pattern exists
- QA functions exist in multiple modules (`calibration/cli_qa.py`,
  `imaging/cli.py`, `mosaic/cli.py`)
- argparse subcommand pattern is standard

**What Needs Investigation:**

- ⚠️ **QA function locations:** Need to find all QA functions across modules
- ⚠️ **QA function signatures:** Need to understand input/output formats
- ⚠️ **QA report format:** Need to understand what "comprehensive QA report"
  means

**Estimated Investigation Time:** 4-6 hours  
**Estimated Implementation Time:** 1.5 days

---

#### 1.5 Stage 7: Photometry API Execution Endpoints

**Status:** ✅ **KNOW HOW TO IMPLEMENT**

**Confidence:** High (85%)

**What I Know:**

- Photometry CLI exists (`photometry/cli.py`)
- Functions: `cmd_peak()`, `cmd_peak_many()`, normalization functions exist
- API router pattern exists (`api/routers/photometry.py`)
- Job adapter pattern exists

**Implementation Pattern:**

```python
# Wrap CLI functions:
# 1. Create POST /api/photometry/measure endpoint
# 2. Extract parameters from request
# 3. Call cmd_peak() or cmd_peak_many()
# 4. Return results as JSON
```

**What Needs Investigation:**

- ⚠️ **Normalization API:** Need to understand normalization function signature
- ⚠️ **Batch photometry:** Need to understand how to batch multiple measurements

**Estimated Investigation Time:** 2-3 hours  
**Estimated Implementation Time:** 1.5-2 days

---

#### 1.6 Stage 8: ESE Detection CLI and Execution

**Status:** ⚠️ **NEEDS INVESTIGATION**

**Confidence:** Medium (60%)

**What I Know:**

- Variability stats computation exists
  (`photometry/source.py::calc_variability_metrics()`)
- `ese_candidates` table exists in database schema
- `variability_stats` table exists
- Photometry timeseries table exists

**What Needs Investigation:**

- ⚠️ **ESE Detection Logic:** Need to understand exact criteria for flagging ESE
  candidates
- ⚠️ **Variability Stats Computation:** Need to understand how
  `calc_variability_metrics()` works and when to call it
- ⚠️ **Pipeline Integration:** Need to understand how to connect photometry →
  variability stats → ESE detection
- ⚠️ **Database Schema:** Need to verify exact schema of `ese_candidates` and
  `variability_stats` tables
- ⚠️ **Significance Threshold:** Need to understand what "significance >= 5.0"
  means (sigma? chi-squared? custom metric?)

**Critical Questions:**

1. What exactly is the ESE detection algorithm?
2. How is variability_stats computed? Per-source? Per-epoch?
3. What triggers ESE detection? After each photometry measurement? Batch?
4. What are the exact database fields and types?

**Estimated Investigation Time:** 1-2 days  
**Estimated Implementation Time:** 2-3 days

---

## Phase 2: Enhance Automation

### Priority 1: Streaming Converter Enhancements

#### 2.1 Stage 2: Calibration Solving in Streaming Converter

**Status:** ⚠️ **NEEDS INVESTIGATION**

**Confidence:** Medium (65%)

**What I Know:**

- Calibration solving exists in orchestrator
  (`StreamingMosaicManager.solve_calibration_for_group()`)
- Calibration functions exist (`calibration/calibration.py`: `solve_bandpass()`,
  `solve_gains()`)
- Streaming converter structure exists
  (`conversion/streaming/streaming_converter.py`)
- Calibration application logic exists (Lines 850-890)

**What Needs Investigation:**

- ⚠️ **Calibrator Detection:** Need to understand how to detect if MS contains
  calibrator
- ⚠️ **Single MS Calibration:** Orchestrator solves for groups, need to adapt
  for single MS
- ⚠️ **BP Calibrator Selection:** Need to understand how
  `get_bandpass_calibrator_for_dec()` works
- ⚠️ **Calibration Registry:** Need to understand how calibration tables are
  registered and retrieved
- ⚠️ **Error Handling:** Need to understand what happens if calibration solving
  fails mid-stream

**Critical Questions:**

1. How do we detect if an MS file contains a calibrator?
2. Can we solve calibration for a single MS, or do we need multiple MS files?
3. What's the relationship between BP calibrator and gain calibrator?
4. How do we handle calibration solving failures in streaming mode?

**Estimated Investigation Time:** 1-2 days  
**Estimated Implementation Time:** 2-3 days

---

#### 2.2 Stage 3: Coordinated Group Imaging in Streaming Converter

**Status:** ✅ **KNOW HOW TO IMPLEMENT** (with investigation)

**Confidence:** Medium-High (75%)

**What I Know:**

- Group detection logic exists in orchestrator
  (`find_transit_centered_window()`)
- `ms_index` table tracks MS files with timestamps
- Imaging logic exists (`imaging/cli.py`)
- Mosaic creation logic exists (`mosaic/streaming_mosaic.py`)

**What Needs Investigation:**

- ⚠️ **Group Detection Query:** Need to understand exact query for finding
  complete groups
- ⚠️ **Time Window Logic:** Need to understand how to determine "same time
  window" (±25 minutes?)
- ⚠️ **Group Size:** Need to verify what "complete group" means (10 MS files?
  configurable?)

**Estimated Investigation Time:** 3-4 hours  
**Estimated Implementation Time:** 1.5-2 days

---

#### 2.3 Stages 4-6: Mosaic Creation, QA, Publishing in Streaming Converter

**Status:** ✅ **KNOW HOW TO IMPLEMENT** (with investigation)

**Confidence:** Medium-High (80%)

**What I Know:**

- Mosaic creation logic exists (`MosaicOrchestrator`, `StreamingMosaicManager`)
- QA/validation logic exists (`data_registry.finalize_data()`)
- Publishing logic exists (`data_registry.trigger_auto_publish()`)
- Streaming converter structure exists

**What Needs Investigation:**

- ⚠️ **Integration Points:** Need to understand where exactly to trigger mosaic
  creation in streaming converter
- ⚠️ **Error Handling:** Need to understand how to handle failures in mosaic
  creation during streaming
- ⚠️ **State Management:** Need to understand how to track mosaic creation
  status in streaming mode
- ⚠️ **Configuration:** Need to understand how to make this configurable (flags,
  settings)

**Estimated Investigation Time:** 4-6 hours  
**Estimated Implementation Time:** 2-3 days

---

### Priority 2: Photometry and ESE Detection Automation

#### 2.4 Stage 7: Automated Photometry Pipeline

**Status:** ⚠️ **NEEDS INVESTIGATION**

**Confidence:** Medium (65%)

**What I Know:**

- Photometry CLI exists (`photometry/cli.py`)
- Source catalog exists (`master_sources.sqlite3`)
- Image creation triggers exist (after imaging stage)

**What Needs Investigation:**

- ⚠️ **Source Selection:** Need to understand how to query
  `master_sources.sqlite3` for sources in image field
- ⚠️ **Field Coverage:** Need to understand how to determine which sources are
  in image field (WCS? radius?)
- ⚠️ **Trigger Points:** Need to understand exactly when to trigger photometry
  (after each image? after mosaic?)
- ⚠️ **Normalization Logic:** Need to understand when normalization should be
  triggered (always? conditional?)
- ⚠️ **Performance:** Need to understand if photometry on all sources is
  feasible (may be slow)

**Critical Questions:**

1. How do we query sources in image field? WCS-based? Catalog query?
2. Should photometry run after every image or only after mosaics?
3. What's the performance impact of photometry on all sources?
4. When should normalization run? After every photometry? Batch?

**Estimated Investigation Time:** 1-2 days  
**Estimated Implementation Time:** 2-3 days

---

#### 2.5 Stage 8: Automated ESE Detection Pipeline

**Status:** ⚠️ **NEEDS INVESTIGATION**

**Confidence:** Low-Medium (50%)

**What I Know:**

- Variability stats computation exists
  (`photometry/source.py::calc_variability_metrics()`)
- ESE candidate flagging logic needs to be created
- Database tables exist (`ese_candidates`, `variability_stats`)

**What Needs Investigation:**

- ⚠️ **Variability Stats Computation:** Need to understand exactly how
  `calc_variability_metrics()` works
- ⚠️ **ESE Detection Algorithm:** Need to understand exact criteria for flagging
  ESE candidates
- ⚠️ **Trigger Logic:** Need to understand when to compute variability stats
  (after each photometry? batch?)
- ⚠️ **Database Schema:** Need to verify exact schema and understand
  relationships
- ⚠️ **Performance:** Need to understand if computing variability stats for all
  sources is feasible

**Critical Questions:**

1. What exactly is the ESE detection algorithm? (significance >= 5.0 - but what
   metric?)
2. How is variability_stats computed? Per-source? Per-epoch? Batch?
3. When should variability stats be computed? After each photometry measurement?
   Periodic batch?
4. What's the performance impact of computing variability stats for all sources?

**Estimated Investigation Time:** 2-3 days  
**Estimated Implementation Time:** 3-4 days

---

## Phase 3: Validation and Robustness

### 3.1 Error Handling and Recovery

**Status:** ⚠️ **NEEDS INVESTIGATION**

**Confidence:** Medium (60%)

**What I Know:**

- Orchestrator structure exists (`mosaic/orchestrator.py`)
- Database schema exists (`mosaic_groups` table)
- Error handling patterns exist in codebase

**What Needs Investigation:**

- ⚠️ **Failure Modes:** Need to understand all possible failure modes in
  orchestrator
- ⚠️ **State Tracking:** Need to understand how to track partial failures in
  `mosaic_groups` table
- ⚠️ **Retry Logic:** Need to understand what "retry" means for each stage
  (re-run? resume?)
- ⚠️ **Recovery Mechanisms:** Need to understand how to resume from last
  successful stage
- ⚠️ **Error Reporting:** Need to understand how errors should be reported and
  logged

**Critical Questions:**

1. What are all possible failure modes in orchestrator workflow?
2. How do we track partial failures? What state information do we need?
3. What does "retry" mean for each stage? Re-run from scratch? Resume?
4. How do we determine "last successful stage" for recovery?

**Estimated Investigation Time:** 1-2 days  
**Estimated Implementation Time:** 3-4 days

---

### 3.2 End-to-End Integration Testing

**Status:** ✅ **KNOW HOW TO IMPLEMENT** (with investigation)

**Confidence:** Medium-High (75%)

**What I Know:**

- Test infrastructure exists (`tests/integration/`)
- Synthetic data generation exists
  (`tests/integration/test_forced_photometry_simulation.py`)
- pytest patterns exist

**What Needs Investigation:**

- ⚠️ **Test Data:** Need to understand how to generate synthetic HDF5/MS files
  for testing
- ⚠️ **Test Scenarios:** Need to understand what scenarios to test (success,
  partial failure, etc.)
- ⚠️ **Performance Benchmarks:** Need to understand what metrics to track

**Estimated Investigation Time:** 1 day  
**Estimated Implementation Time:** 2-3 days

---

## Summary by Readiness

### ✅ Ready to Implement (High Confidence)

1. **Stage 1: Batch Conversion API** (95% confidence)
2. **Stage 4: Mosaic Creation API** (90% confidence)
3. **Stage 6: Publishing CLI** (85% confidence)
4. **Stage 7: Photometry API Execution** (85% confidence)
5. **Stage 3: Coordinated Group Imaging** (75% confidence)
6. **Stage 5: Unified QA CLI** (75% confidence)
7. **Stages 4-6: Mosaic/QA/Publishing in Streaming** (80% confidence)
8. **End-to-End Integration Testing** (75% confidence)

**Total:** 8 tasks, ~12-15 days implementation

---

### ⚠️ Needs Investigation (Medium-Low Confidence)

1. **Stage 8: ESE Detection CLI and Execution** (60% confidence)
2. **Stage 2: Calibration Solving in Streaming** (65% confidence)
3. **Stage 7: Automated Photometry Pipeline** (65% confidence)
4. **Stage 8: Automated ESE Detection Pipeline** (50% confidence)
5. **Error Handling and Recovery** (60% confidence)

**Total:** 5 tasks, ~8-12 days investigation + ~10-15 days implementation

---

## Recommended Investigation Order

### Week 1: Critical Path Investigation

1. **ESE Detection Algorithm** (2-3 days)
   - Understand variability stats computation
   - Understand ESE detection criteria
   - Understand database schema
   - **Blocking:** Stage 8 implementation

2. **Calibration Solving in Streaming** (1-2 days)
   - Understand calibrator detection
   - Understand single MS calibration
   - Understand calibration registry
   - **Blocking:** Stage 2 automation

### Week 2: Supporting Investigation

3. **Automated Photometry Pipeline** (1-2 days)
   - Understand source selection
   - Understand trigger points
   - Understand performance implications
   - **Blocking:** Stage 7 automation

4. **Error Handling Patterns** (1-2 days)
   - Understand failure modes
   - Understand state tracking
   - Understand retry logic
   - **Blocking:** Phase 3 implementation

---

## Risk Assessment

### High Risk (Needs Investigation Before Implementation)

- **ESE Detection:** Complex domain logic, unclear algorithm
- **Calibration Solving:** Complex integration, domain knowledge required
- **Error Handling:** Complex state management, unclear recovery patterns

### Medium Risk (Can Start with Investigation)

- **Automated Photometry:** Performance concerns, integration complexity
- **End-to-End Testing:** Test data generation complexity

### Low Risk (Ready to Implement)

- **API Endpoints:** Clear patterns, straightforward integration
- **CLI Tools:** Standard patterns, clear requirements

---

## Next Steps

1. **Start with High-Confidence Tasks:** Implement Stage 1, 4, 6, 7 API
   endpoints while investigating ESE detection
2. **Parallel Investigation:** Run ESE detection and calibration solving
   investigations in parallel
3. **Incremental Implementation:** Implement as investigation completes
4. **Test Early:** Create integration tests as features are implemented

---

## Conclusion

**Ready to Implement:** ~60% of roadmap tasks (8 of 13 major tasks)  
**Needs Investigation:** ~40% of roadmap tasks (5 of 13 major tasks)

**Recommendation:** Start with high-confidence tasks (API endpoints, CLI tools)
while running investigations in parallel for complex domain logic (ESE
detection, calibration solving, error handling).
