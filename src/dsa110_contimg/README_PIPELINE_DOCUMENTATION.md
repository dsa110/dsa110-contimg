# DSA-110 Pipeline Documentation Index

This directory contains comprehensive documentation of the DSA-110 imaging
pipeline architecture, workflow, execution models, and design patterns.

---

## Documentation Files

### 1. WORKFLOW_THOUGHT_EXPERIMENT.md

**Purpose**: Identifies all architectural issues and design challenges

**Content**:

- Complete workflow trace through all 9 stages
- **24 identified icebergs** (hidden assumptions and failures)
- Issues and icebergs organized by stage
- Fixes applied to each issue
- Summary of critical vs. secondary concerns

**Start here if**: You want to understand what problems the pipeline solves or
what went wrong historically.

**Key sections**:

- Stage 1: File ingestion & registration
- Stage 2: MS conversion
- Stage 3: Group formation
- Stage 4: Calibration solving
- Stage 5: Calibration application
- Stage 6: Imaging
- Stage 7: Mosaic creation
- Stage 8: Cross-matching
- Stage 9: Registration & publishing
- Additional icebergs #15-24 (path resolution, transactions, metadata, error
  recovery, concurrency)

---

### 2. FINAL_WORKFLOW_VERIFICATION.md

**Purpose**: Confirms all identified issues are fixed and working correctly

**Content**:

- Complete end-to-end trace verification
- All 24 icebergs marked as fixed
- Edge case handling (validation warnings, deleted files, disk full, concurrent
  access, etc.)
- Database consistency checks
- Transaction safety verification
- State transition verification
- Final status: **Ready for production**

**Start here if**: You want to verify the pipeline is correct and safe to
deploy.

**Key sections**:

- Critical path verification (mosaic creation → registration → publishing)
- Edge case verification (6 scenarios)
- Database consistency checks
- Remaining non-critical considerations (intentional design choices)
- Conclusion: All icebergs fixed, production-ready

---

### 3. DEFAULTS_AND_MINIMAL_INPUT.md

**Purpose**: Describes what the pipeline does with zero or minimal user input

**Content**:

- Default parameters for all pipeline stages
- Calibration defaults (bandpass, gain, K-calibration, flagging)
- Imaging defaults (image size, weighting, deconvolver, iterations)
- Mosaic combination defaults (method, tile selection, validation)
- Database defaults (paths, environment variables)
- Service port defaults (API, dashboard, frontend, Redis)
- Minimal production setup (two-command startup)
- Environment override examples

**Start here if**: You want to get the pipeline running with sensible defaults,
or you need to understand what each parameter does.

**Key sections**:

- Stage 1: Streaming HDF5 conversion (required input: directories only)
- Stage 2-9: Streaming mosaic orchestration (required input: none)
- Calibration defaults (BP/GP/K/flagging/model)
- Imaging defaults (size/weighting/deconvolver/iterations)
- Typical minimal production setup

---

### 4. EXECUTION_THEMES.md (NEW)

**Purpose**: Explains the two fundamental ways to run the pipeline end-to-end

**Content**:

- **Theme 1: Continuous Streaming** (daemon architecture)
  - Long-running background processes
  - Automatic data flow with polling
  - Hands-off operation
  - Production use case
- **Theme 2: Explicit Batch Processing** (CLI/API job submission)
  - User-submitted explicit jobs
  - Deterministic execution
  - Fine-grained control
  - Research/reprocessing use case

- Detailed comparison matrix
- Architectural overlap and key differences
- When to use each theme
- Hybrid approaches (running both simultaneously)
- Implementation details

**Start here if**: You need to decide how to integrate the pipeline into your
system, or you want to understand the operational model.

**Key sections**:

- Pattern comparison: streaming vs. batch
- Characteristics and use cases
- Entry points and command-line examples
- Comparison matrix (15 dimensions)
- Coexistence and hybrid approaches
- Decision tree for choosing theme

---

## Quick Navigation

### I want to...

**...get the pipeline running quickly** → Read `DEFAULTS_AND_MINIMAL_INPUT.md` +
`EXECUTION_THEMES.md` (Theme 1: Streaming)

**...understand the complete workflow** → Read `WORKFLOW_THOUGHT_EXPERIMENT.md`
(ordered 9-stage trace)

**...verify the pipeline is correct** → Read `FINAL_WORKFLOW_VERIFICATION.md`
(all icebergs fixed)

**...integrate the pipeline into my system** → Read `EXECUTION_THEMES.md`
(choose streaming vs. batch)

**...set up for production operations** → Read `DEFAULTS_AND_MINIMAL_INPUT.md`
(minimal setup) + `EXECUTION_THEMES.md` (Theme 1)

**...do research or reprocessing** → Read `EXECUTION_THEMES.md` (Theme 2:
Batch) + `DEFAULTS_AND_MINIMAL_INPUT.md` (CLI parameters)

**...understand design decisions** → Read `WORKFLOW_THOUGHT_EXPERIMENT.md`
(icebergs) + `FINAL_WORKFLOW_VERIFICATION.md` (mitigations)

---

## The Complete Story

### Act 1: Design & Challenges

**File**: `WORKFLOW_THOUGHT_EXPERIMENT.md`

The pipeline was designed to handle complex data flow from raw HDF5 through
calibration, imaging, and publishing. Early design identified 24 potential
failure points ("icebergs"):

- **Stages 1-7**: 10 icebergs (file handling, idempotence, state management)
- **Stage 9**: 4 critical icebergs (publishing failures)
- **General**: 10 secondary icebergs (transactions, concurrency, metadata, error
  recovery)

### Act 2: Solutions

**File**: `FINAL_WORKFLOW_VERIFICATION.md`

All 24 icebergs were fixed through careful design:

- Database-backed persistence prevents re-processing
- Idempotent operations allow safe retries
- Atomic transactions prevent partial state
- Path validation prevents data loss
- Auto-publish triggers on QA pass
- Error handling with manual recovery options

**Result**: Production-ready pipeline with comprehensive error handling.

### Act 3: Deployment

**File**: `DEFAULTS_AND_MINIMAL_INPUT.md`

The complexity is hidden behind sensible defaults:

- Start converter: `dsa110-contimg-convert-stream --input-dir X --output-dir Y`
- Start mosaic daemon: `dsa110-contimg-streaming-mosaic --loop`
- Everything else: automatic

### Act 4: Operations

**File**: `EXECUTION_THEMES.md`

Two operational modes support different use cases:

- **Streaming**: Production observatory with continuous observations
- **Batch**: Research and reprocessing with explicit control

Both themes coexist in the same system, sharing the same underlying code.

---

## Key Concepts

### The 9 Pipeline Stages

1. **File Ingestion** - HDF5 files detected and registered
2. **MS Conversion** - HDF5 → CASA MeasurementSet format
3. **Group Formation** - 10 MS files grouped chronologically
4. **Calibration Solving** - Bandpass & gain calibration derived from calibrator
5. **Calibration Application** - Calibration corrections applied to all MS
6. **Imaging** - Individual images created from each MS
7. **Mosaic Creation** - Images combined into single mosaic
8. **Cross-Matching** - (Optional) Sources matched to astronomical catalogs
9. **Registration & Publishing** - Mosaic registered and moved to public
   location

### The Two Execution Themes

**Streaming (Daemon)**: Continuous polling for new data, automatic processing,
hands-off operation.

**Batch (Job)**: User submits explicit job with parameters, deterministic
execution, fine-grained control.

### Default Behavior

- **Conversion**: 5-minute chunks, 16 subbands, 4 workers, 5-second polling
- **Calibration**: SNR threshold 3.0, solve over entire scan, catalog-based
  model
- **Imaging**: 1024×1024 pixels, Briggs weighting, 1000 iterations, Hogbom
  deconvolver
- **Mosaicing**: Mean stacking, no PB correction, strict validation
- **Publishing**: Auto-publish on QA pass, move to `/data/` staging area

---

## Production Checklist

Before running in production, verify:

- [ ] Read `EXECUTION_THEMES.md` - Decided on streaming vs. batch
- [ ] Read `DEFAULTS_AND_MINIMAL_INPUT.md` - Understand default parameters
- [ ] Configure paths:
  - [ ] Input directory: `/data/incoming/` (or custom)
  - [ ] Output directory: `/stage/dsa110-contimg/ms/` (or custom)
  - [ ] Staging mosaic output: `/stage/dsa110-contimg/mosaics/`
  - [ ] Published mosaic output: `/data/dsa110-contimg/products/mosaics/`
- [ ] Check database locations:
  - [ ] `state/products.sqlite3` writable
  - [ ] `state/cal_registry.sqlite3` writable
  - [ ] `state/ingest.sqlite3` writable
- [ ] Read `FINAL_WORKFLOW_VERIFICATION.md` - Confirm error handling is adequate
- [ ] Start converter:
      `dsa110-contimg-convert-stream --input-dir X --output-dir Y`
- [ ] Start mosaic daemon: `dsa110-contimg-streaming-mosaic --loop` (in separate
      screen/tmux)
- [ ] Monitor logs and verify automatic processing

---

## File Sizes & Scope

| Document                       | Size    | Lines    | Focus                      |
| ------------------------------ | ------- | -------- | -------------------------- |
| WORKFLOW_THOUGHT_EXPERIMENT.md | 8.8K    | 228      | Issues & icebergs          |
| FINAL_WORKFLOW_VERIFICATION.md | 8.2K    | 214      | Verification & mitigations |
| DEFAULTS_AND_MINIMAL_INPUT.md  | 12K     | 326      | Defaults & startup         |
| EXECUTION_THEMES.md            | 14K     | 467      | Operational models         |
| **TOTAL**                      | **43K** | **1235** | Complete reference         |

---

## Related Code Directories

- `conversion/` - HDF5 → MS conversion
- `mosaic/` - Mosaic orchestration & creation
- `calibration/` - Calibration solving & application
- `imaging/` - CASA imaging
- `database/` - Data registry & publishing
- `pipeline/` - Generic multi-stage orchestrator
- `api/` - REST API & batch job submission
- `utils/` - Shared utilities & defaults

---

## Quick Reference: Most Common Commands

### Start production pipeline

```bash
dsa110-contimg-convert-stream --input-dir /data/incoming/ --output-dir /stage/...
dsa110-contimg-streaming-mosaic --loop
```

### Create custom mosaic

```bash
dsa110-contimg-mosaic plan --name analysis --since 1700000000 --until 1700100000
dsa110-contimg-mosaic build --name analysis --output /data/output.image
```

### Submit batch job via API

```bash
curl -X POST http://localhost:8000/api/jobs/ \
  -d '{"type": "mosaic", "params": {...}}'
```

### Monitor pipeline

```bash
curl http://localhost:8000/api/status
```

---

## Version & Status

- **Pipeline Status**: ✓ Production-ready
- **All Icebergs**: ✓ Fixed (24/24)
- **Documentation**: ✓ Complete (4 documents)
- **Last Updated**: 2025-11-14
