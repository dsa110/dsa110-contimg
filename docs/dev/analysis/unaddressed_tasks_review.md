# Unaddressed Tasks Review

**Date:** 2025-11-12  
**Purpose:** Review development roadmap and identify tasks not yet addressed or incompletely addressed

---

## Summary

After reviewing the development roadmap (`development_roadmap.md`) and comparing with completed work (`remaining_tasks_completion_summary.md`), the following tasks remain **unaddressed** or **incompletely addressed**:

---

## Phase 1: Complete Batch Mode Development

### ✅ Completed Tasks

1. **Stage 1: Batch Conversion API** - ✅ Complete
   - `POST /api/batch/convert` endpoint implemented
   - Batch conversion job adapter created
   - Unit tests written

2. **Stage 3: Coordinated Group Imaging** - ✅ Complete
   - Group detection logic implemented
   - Mosaic creation trigger integrated
   - Unit tests written

3. **Stage 4: Mosaic Creation API** - ✅ Complete
   - `POST /api/mosaics/create` endpoint implemented
   - Background job adapter created
   - Unit tests written

4. **Stage 5: Unified QA CLI** - ✅ Complete
   - Unified QA CLI created (`src/dsa110_contimg/qa/cli.py`)
   - All subcommands implemented (calibration, image, mosaic, report)
   - Unit tests written

5. **Stage 6: Publishing CLI** - ✅ Complete
   - Publishing CLI created (`src/dsa110_contimg/database/cli.py`)
   - `POST /api/batch/publish` endpoint implemented
   - Unit tests written

6. **Stages 4-6: Mosaic/QA/Publishing in Streaming** - ✅ Complete
   - Integrated into streaming converter
   - Configurable via command-line flags

---

## ❌ Unaddressed or Incomplete Tasks

### Phase 1: Batch Mode Development

#### 1.5 Stage 7: Photometry API Execution Endpoints (Current: 85% → Target: 100%)

**Status:** ⚠️ **PARTIALLY COMPLETE**

**What Was Planned:**
1. ✅ `POST /api/photometry/measure` - Single forced photometry (COMPLETE)
2. ✅ `POST /api/photometry/measure-batch` - Multiple coordinates (COMPLETE)
3. ❌ `POST /api/photometry/normalize` - Normalization endpoint (NOT IMPLEMENTED)
4. ❌ `POST /api/batch/photometry` - Batch photometry job endpoint (NOT IMPLEMENTED)

**Gap Analysis:**
- Single and batch measurement endpoints exist
- Normalization endpoint missing
- Batch photometry job endpoint missing (different from measure-batch - this would be for processing multiple images/sources)

**Remaining Work:**
- Add `POST /api/photometry/normalize` endpoint
- Add `POST /api/batch/photometry` endpoint for batch processing
- Create `run_batch_photometry_job()` adapter
- Unit tests for normalization and batch endpoints

**Estimated Effort:** 1-2 days

---

#### 1.6 Stage 8: ESE Detection CLI and Execution (Current: 60% → Target: 100%)

**Status:** ❌ **NOT ADDRESSED**

**What Was Planned:**
1. ❌ Create ESE Detection CLI subcommand
2. ❌ Add `POST /api/jobs/ese-detect` endpoint
3. ❌ Add `POST /api/batch/ese-detect` endpoint
4. ❌ Connect to photometry pipeline for automatic detection

**Gap Analysis:**
- No CLI subcommand for ESE detection
- No API endpoints for ESE detection execution
- No integration with photometry pipeline
- Read-only API exists (querying ESE candidates), but no execution

**Remaining Work:**
1. **Create ESE Detection CLI:**
   - File: `src/dsa110_contimg/photometry/cli.py` (add subcommand)
   - Subcommand: `ese-detect [--source-id <id>] [--min-sigma <sigma>] [--recompute]`
   - Logic:
     - Query `photometry_timeseries` table for sources
     - Compute `variability_stats` for each source
     - Flag ESE candidates (`significance >= 5.0`)
     - Insert into `ese_candidates` table

2. **Add ESE Detection API Execution:**
   - Endpoint: `POST /api/jobs/ese-detect`
   - Adapter: `run_ese_detect_job()` (wraps CLI function)
   - Batch Endpoint: `POST /api/batch/ese-detect`

3. **Connect to Photometry Pipeline:**
   - File: `src/dsa110_contimg/photometry/pipeline.py` (may need creation)
   - Logic: After photometry measurement, automatically compute variability stats and check for ESE candidates

**Estimated Effort:** 3-4 days

---

### Phase 2: Enhance Automation

#### 2.1 Stage 2: Calibration Solving in Streaming Converter (Current: 50% → Target: 100%)

**Status:** ⚠️ **PARTIALLY COMPLETE**

**What Was Planned:**
1. ✅ Calibration application exists (applies existing calibration tables)
2. ❌ Calibration solving logic missing (doesn't solve new calibration)
3. ❌ Calibrator detection missing (`has_calibrator()` function)
4. ❌ Calibration solving function missing (`solve_calibration_for_ms()`)

**Gap Analysis:**
- Streaming converter can apply calibration from registry
- Cannot solve new calibration if registry is empty
- No logic to detect calibrator transits
- No logic to solve calibration for individual MS files

**Remaining Work:**
1. **Add Calibration Solving to Streaming Converter:**
   - File: `src/dsa110_contimg/conversion/streaming/streaming_converter.py`
   - Location: After MS conversion, before calibration application
   - Logic:
     ```python
     # Check if calibration tables exist
     applylist = get_active_applylist(...)
     if not applylist:
         # Solve calibration if calibrator present
         if has_calibrator(ms_path):
             bpcal_solved, gaincal_solved = solve_calibration_for_ms(ms_path)
             if bpcal_solved and gaincal_solved:
                 applylist = get_active_applylist(...)  # Refresh
     ```

2. **Add Calibration MS Detection:**
   - Function: `has_calibrator(ms_path: str) -> bool`
   - Logic: Query MS for calibrator field, check if transit window matches

3. **Add Calibration Solving Function:**
   - Function: `solve_calibration_for_ms(ms_path: str) -> Tuple[bool, bool]`
   - Logic: Wrap calibration CLI functions (`solve_bpcal()`, `solve_gaincal()`)

**Estimated Effort:** 2-3 days

---

#### 2.4 Stage 7: Automated Photometry Pipeline (Current: 0% → Target: 100%)

**Status:** ❌ **NOT ADDRESSED**

**What Was Planned:**
1. ❌ Automatic photometry after imaging/mosaic creation
2. ❌ Integration with data registry for triggering
3. ❌ Batch photometry processing

**Gap Analysis:**
- Photometry can be executed manually via CLI/API
- No automatic triggering after imaging or mosaic creation
- No integration with data registry pipeline
- No batch processing automation

**Remaining Work:**
1. **Add Automatic Photometry Trigger:**
   - File: `src/dsa110_contimg/database/data_registry.py` or `src/dsa110_contimg/qa/validation.py`
   - Logic: After image/mosaic QA passes, trigger photometry measurement
   - Integration: Use existing photometry API endpoints

2. **Add Photometry Pipeline Integration:**
   - File: `src/dsa110_contimg/photometry/pipeline.py` (may need creation)
   - Logic:
     - Query data registry for published images/mosaics
     - Extract source coordinates from catalog
     - Run forced photometry on all sources
     - Store results in `photometry_timeseries` table

3. **Add Batch Photometry Processing:**
   - Integration with batch job system
   - Process multiple images/mosaics in parallel

**Estimated Effort:** 3-4 days

---

#### 2.5 Stage 8: Automated ESE Detection Pipeline (Current: 0% → Target: 100%)

**Status:** ❌ **NOT ADDRESSED**

**What Was Planned:**
1. ❌ Automatic ESE detection after photometry
2. ❌ Integration with photometry pipeline
3. ❌ Automated candidate flagging

**Gap Analysis:**
- ESE detection requires photometry pipeline (not yet automated)
- No automatic triggering after photometry completion
- No integration with data registry

**Remaining Work:**
1. **Add Automatic ESE Detection Trigger:**
   - File: `src/dsa110_contimg/photometry/pipeline.py`
   - Logic: After photometry measurement, automatically compute variability stats and check for ESE candidates

2. **Add ESE Detection Pipeline Integration:**
   - Connect to photometry pipeline completion
   - Automatically run ESE detection on new photometry data
   - Flag candidates in `ese_candidates` table

3. **Add Monitoring and Alerting:**
   - Track ESE detection success/failure rates
   - Alert on new ESE candidates

**Estimated Effort:** 2-3 days (depends on 2.4 completion)

---

### Phase 3: Validation and Robustness

#### 3.1 Error Handling and Recovery

**Status:** ❌ **NOT ADDRESSED**

**What Was Planned:**
1. ❌ Retry logic in orchestrator
2. ❌ Error recovery in streaming converter
3. ❌ Monitoring and alerting

**Gap Analysis:**
- Basic error handling exists (try/except blocks)
- No retry logic with exponential backoff
- No recovery from partial failures
- No monitoring/alerting infrastructure

**Remaining Work:**
1. **Add Retry Logic to Orchestrator:**
   - File: `src/dsa110_contimg/mosaic/orchestrator.py`
   - Logic: Retry failed stages with exponential backoff
   - Configuration: Max retries, backoff multiplier

2. **Add Error Recovery to Streaming Converter:**
   - File: `src/dsa110_contimg/conversion/streaming/streaming_converter.py`
   - Logic: Handle partial failures, resume from last successful stage
   - State Tracking: Enhanced `mosaic_groups` table with error tracking

3. **Add Monitoring and Alerting:**
   - File: `src/dsa110_contimg/monitoring/` (may need creation)
   - Logic: Track orchestrator workflow success/failure rates
   - Integration: Connect to existing monitoring endpoints

**Estimated Effort:** 4-5 days

---

#### 3.2 End-to-End Integration Testing

**Status:** ⚠️ **PARTIALLY COMPLETE**

**What Was Planned:**
1. ✅ Integration test suite created (`test_end_to_end_batch_workflow.py`)
2. ❌ Performance benchmarks missing
3. ❌ Partial failure recovery tests missing
4. ❌ Streaming converter integration tests incomplete

**Gap Analysis:**
- Basic integration tests exist
- No performance benchmarks
- No failure injection tests
- Limited streaming converter integration coverage

**Remaining Work:**
1. **Create Performance Benchmarks:**
   - File: `tests/performance/benchmark_orchestrator.py`
   - Metrics: Time per stage, resource usage, throughput

2. **Add Failure Injection Tests:**
   - Test partial failure recovery
   - Test retry logic
   - Test error handling paths

3. **Enhance Streaming Converter Integration Tests:**
   - Test group detection with various scenarios
   - Test mosaic creation workflow
   - Test QA and publishing integration

**Estimated Effort:** 2-3 days

---

## Priority Summary

### High Priority (Blocks Production Use)

1. **Stage 8: ESE Detection CLI and Execution** (3-4 days)
   - Required for automated ESE detection pipeline
   - Blocks Phase 2 automation completion

2. **Stage 2: Calibration Solving in Streaming** (2-3 days)
   - Required for fully autonomous streaming operation
   - Currently requires pre-existing calibration tables

### Medium Priority (Quality of Life)

3. **Stage 7: Photometry API Normalization** (1-2 days)
   - Completes photometry API functionality
   - Low effort, high value

4. **Stage 7: Automated Photometry Pipeline** (3-4 days)
   - Required for automated ESE detection
   - Depends on photometry API completion

5. **Stage 8: Automated ESE Detection Pipeline** (2-3 days)
   - Depends on automated photometry pipeline
   - Final piece of automation puzzle

### Lower Priority (Robustness)

6. **Error Handling and Recovery** (4-5 days)
   - Improves production reliability
   - Can be done incrementally

7. **Performance Benchmarks** (2-3 days)
   - Useful for optimization
   - Not blocking production use

---

## Recommendations

1. **Immediate Next Steps:**
   - Complete Stage 7 photometry API (normalization endpoint)
   - Implement Stage 8 ESE Detection CLI and API endpoints
   - Add calibration solving to streaming converter

2. **Short-Term Goals:**
   - Implement automated photometry pipeline
   - Implement automated ESE detection pipeline
   - Add basic error handling and retry logic

3. **Long-Term Goals:**
   - Comprehensive error recovery mechanisms
   - Performance optimization based on benchmarks
   - Enhanced monitoring and alerting

---

## Related Documents

- [Development Roadmap](development_roadmap.md) - Original implementation plan
- [Remaining Tasks Completion Summary](remaining_tasks_completion_summary.md) - Completed work summary
- [Batch Mode Development Assessment](batch_mode_development_assessment.md) - Feature assessment

