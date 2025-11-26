# Two Execution Themes: Streaming vs. Batch

## Overview

The DSA-110 imaging pipeline supports two fundamentally different execution
models for processing data end-to-end. Understanding these themes is critical
for choosing how to run the pipeline in your context.

---

## Theme 1: Continuous Streaming (Daemon Architecture)

### Pattern

Long-running background processes that **continuously poll** for data and
process it automatically through all 9 stages without human intervention.

### Entry Points

```bash
# Terminal 1: HDF5 conversion daemon
dsa110-contimg-convert-stream \
  --input-dir /data/incoming/ \
  --output-dir /stage/dsa110-contimg/ms/

# Terminal 2: Mosaic orchestration daemon
dsa110-contimg-streaming-mosaic --loop
```

### Key Characteristics

| Aspect                | Behavior                                                 |
| --------------------- | -------------------------------------------------------- |
| **Statefulness**      | Maintains internal state machines + database persistence |
| **Polling**           | Checks every N seconds for new data (default: 5-60 sec)  |
| **Progression**       | Data automatically flows through all 9 stages            |
| **Fault handling**    | Errors logged; retried on next polling cycle             |
| **Human interaction** | Start processes once, then completely hands-off          |
| **Lifetime**          | Runs indefinitely until interrupted (Ctrl+C)             |

### Execution Flow

```
HDF5 Files Arrive
    ↓ [5 sec poll interval]
Polling Loop Detects Files
    ↓
Convert to MS (5-min chunks)
    ↓ [Database persists progress]
Groups Accumulate (10 MS files)
    ↓ [60 sec poll interval]
Streaming Mosaic Daemon Detects Complete Group
    ↓
Calibrate → Image → Mosaic → Validate → Register → Publish
    ↓ [Automatic, no human intervention]
Mosaic in /data/dsa110-contimg/products/mosaics/
    ↓
Loop back to polling
```

### Default Behavior (No Flags Required)

```bash
# Just run with defaults - everything else automatic
dsa110-contimg-streaming-mosaic --loop

# Defaults applied:
# - Check for new groups every 60 seconds
# - Calibrate using 5th MS as reference
# - Image with 1024×1024 pixels, Briggs weighting
# - Combine mosaics with mean stacking
# - Validate and auto-publish if QA passes
```

### Use Cases

- **Production observatory** - Continuous observations arriving in real-time
- **Long-term monitoring** - Repeated observations of same fields over time
- **Automated pipelines** - Zero-touch processing of data
- **System integration** - Other systems depend on regular output

### Key Classes

- `StreamingConverter` - Monitors `/data/incoming/`, converts HDF5 → MS
- `StreamingMosaicManager` - Detects groups, orchestrates stages 2-9

### When to Use

✓ You have a continuous data stream ✓ You want fully automatic processing ✓ You
need production-grade reliability ✓ You can tolerate eventual consistency
(groups processed when complete)

---

## Theme 2: Explicit Batch Processing (CLI/API Job Submission)

### Pattern

User submits **explicit jobs** with specific parameters via CLI or REST API.
Pipeline executes deterministically once per job submission, then exits.

### Entry Points

#### CLI - Mosaic Builder

```bash
# Plan: User selects tiles, method, time range
dsa110-contimg-mosaic plan \
  --name my_custom_mosaic \
  --since 1700000000 \
  --until 1700100000 \
  --method weighted

# Build: User specifies output location and options
dsa110-contimg-mosaic build \
  --name my_custom_mosaic \
  --output /data/my_output.image \
  --dry-run
```

#### API - Job Submission

```bash
# Submit batch job via REST API
curl -X POST http://localhost:8000/api/jobs/ \
  -H "Content-Type: application/json" \
  -d '{
    "type": "mosaic",
    "params": {
      "name": "my_mosaic",
      "method": "pbweighted",
      "since": 1700000000
    }
  }'

# Check job status
curl http://localhost:8000/api/jobs/12345/status
```

#### Pipeline Framework - Multi-Stage Orchestration

```python
from dsa110_contimg.pipeline.orchestrator import PipelineOrchestrator

stages = [
    StageDefinition("convert", ConversionStage(), []),
    StageDefinition("calibrate", CalibrationStage(), ["convert"]),
    StageDefinition("image", ImagingStage(), ["calibrate"]),
    StageDefinition("mosaic", MosaicStage(), ["image"]),
]

orchestrator = PipelineOrchestrator(stages)
result = orchestrator.run(context)
```

### Key Characteristics

| Aspect                | Behavior                                                |
| --------------------- | ------------------------------------------------------- |
| **Statefulness**      | Stateless per execution - all parameters explicit       |
| **Specification**     | User fully specifies inputs, outputs, parameters        |
| **Progression**       | Executes once deterministically, exits with status code |
| **Fault handling**    | Fails immediately with error code (no retry)            |
| **Human interaction** | Submit job, monitor status, analyze results             |
| **Lifetime**          | Finite - starts, completes, exits                       |

### Execution Flow

```
User Submits Job (CLI or API)
    ↓ [Specifies exact parameters]
Parse Job Definition
    ↓ [Create PipelineContext]
Execute Stage 1: [Convert or Custom]
    ↓ [Check dependencies - if not met, fail]
Execute Stage 2: [Calibrate]
    ↓
Execute Stage 3: [Image]
    ↓
... (all specified stages)
    ↓
Write Results to User-Specified Output
    ↓
Exit with Status Code (0 = success, 1 = failure)
```

### Default Behavior (CLI Example)

```bash
# Minimal batch job - defaults applied
dsa110-contimg-mosaic plan --name my_mosaic

# Defaults:
# - Source: state/products.sqlite3
# - Method: mean stacking
# - Time range: all tiles from history
# - Include only: PB-corrected tiles

# User must specify output location
dsa110-contimg-mosaic build \
  --name my_mosaic \
  --output /data/output.image
```

### Use Cases

- **Historical reprocessing** - Reprocess old observations with new calibration
- **Custom mosaics** - Combine specific time range or subset of tiles
- **Research analysis** - Run one-off analyses with specific parameters
- **Quality control** - Manual verification before publishing
- **Comparison studies** - Same data with different parameters to compare
  results
- **Debugging** - `--dry-run` to validate before executing

### Key Classes

- `PipelineOrchestrator` - Generic multi-stage executor with dependency
  resolution
- `StageDefinition` - Defines stages and their dependencies
- `PipelineContext` - Encapsulates job parameters and state
- Batch job system in `api/batch_jobs.py` - Job submission, tracking, status
  queries

### When to Use

✓ You need fine-grained control over inputs/outputs ✓ You want reproducible
results (same input → same output) ✓ You're doing research or reprocessing ✓ You
need to verify before publishing ✓ You want detailed error messages ✓ You need
to track job history

---

## Comparison Matrix

| Dimension              | **Streaming**                              | **Batch**                                |
| ---------------------- | ------------------------------------------ | ---------------------------------------- |
| **Startup**            | `--loop` flag enables infinite polling     | Job submission via CLI/API               |
| **Data selection**     | Automatic: next 10 MS files                | Explicit: user chooses tiles/time range  |
| **State persistence**  | Database tracks all progress               | Stateless per execution                  |
| **Execution duration** | Indefinite (daemon, until Ctrl+C)          | Single run to completion                 |
| **User interaction**   | Minimal: start and monitor logs            | Active: submit → check status → analyze  |
| **Error handling**     | Log error, retry next cycle                | Fail immediately with error code         |
| **Reproducibility**    | Non-deterministic (timing-based)           | Deterministic (same input → same output) |
| **Concurrency**        | Process many groups in parallel            | One job at a time (can submit many)      |
| **Primary use**        | Production observatory operations          | Research, reprocessing, QA               |
| **Typical volume**     | Continuous high-volume stream              | Ad-hoc or batch submissions              |
| **Failure recovery**   | Automatic (next cycle)                     | Manual resubmission                      |
| **Output naming**      | Automatic: `mosaic_<group_id>_<timestamp>` | User-specified: `--output` path          |

---

## Architectural Overlap

### Stages 1-9: Identical Code Path

Both themes use the exact same underlying processing code for:

1. MS conversion
2. Calibration solving
3. Calibration application
4. Imaging
5. Mosaic creation
6. Validation
7. Registration
8. Publishing
9. (Optional) Cross-matching

### Critical Difference: Stage 3 (Group Formation)

**Streaming**:

```python
# Automatic: Take next 10 chronologically-ordered MS files
groups = get_next_complete_groups(n_ms=10, sliding_window=True)
```

**Batch**:

```python
# Manual: User specifies exactly which tiles to include
selected_tiles = query_tiles(
    time_range=(since, until),
    method=combination_method,
    pb_corrected_only=True
)
```

### Orchestration Levels

**Streaming**:

- `StreamingConverter` - Specialized for HDF5 → MS ingestion
- `StreamingMosaicManager` - Specialized for continuous group processing
- Fixed workflow: Ingestion → Group → Calibrate → Image → Mosaic → Publish

**Batch**:

- `PipelineOrchestrator` - Generic multi-stage framework
- Flexible workflow: User composes any sequence of stages with dependencies
- Supports custom stages and pipelines

---

## Coexistence: Running Both Themes Simultaneously

Both themes can run at the same time in the same system:

```bash
# Terminal 1: Streaming converter (continuous ingestion)
dsa110-contimg-convert-stream --input-dir /data/incoming/ --output-dir /stage/...

# Terminal 2: Streaming mosaic daemon (automatic processing)
dsa110-contimg-streaming-mosaic --loop

# Terminal 3+: User can submit batch jobs on demand
dsa110-contimg-mosaic plan --name custom_analysis
dsa110-contimg-mosaic build --name custom_analysis --output /data/analysis.image

# Or via API while everything runs
curl -X POST http://localhost:8000/api/jobs/ -d '...'
```

### Typical Architecture

```
Production System
├── Streaming Converter (continuous HDF5 ingestion)
├── Streaming Mosaic Daemon (automatic group processing)
├── REST API (batch job submission)
├── Dashboard (monitoring)
└── User Tools (manual reprocessing, QA, research)

Typical Flow:
1. Real-time observations → Streaming theme → Automatic mosaics
2. Historical data → Batch theme (via API) → Custom analysis
3. Production QA → Streaming theme → Published products
4. Research needs → Batch theme (via CLI) → Research outputs
```

---

## Decision Tree: Which Theme to Use?

```
Do you have continuous data arriving?
├─ YES: Use STREAMING
│       └─ Start converter with --input-dir
│       └─ Start mosaic daemon with --loop
│       └─ Sit back and watch mosaics appear
│
└─ NO: Use BATCH
        ├─ Need to reprocess old data?
        │  └─ dsa110-contimg-mosaic plan/build
        ├─ Need custom time range?
        │  └─ dsa110-contimg-mosaic plan --since --until
        ├─ Need to compare methods?
        │  └─ Submit multiple batch jobs with different --method
        └─ Need to integrate with external system?
           └─ Use REST API: POST /api/jobs/
```

---

## Combining Themes: Hybrid Approach

Many installations use both themes in a hybrid setup:

### Scenario: Production + Research

**Production (Streaming)**:

```bash
# Automatically process all observations
dsa110-contimg-convert-stream --input-dir /data/incoming/ ...
dsa110-contimg-streaming-mosaic --loop
```

Output: `/data/dsa110-contimg/products/mosaics/mosaic_*.fits` (auto-published)

**Research (Batch)**:

```bash
# Manually analyze subset with different parameters
dsa110-contimg-mosaic plan --name research_custom \
  --since 1700000000 --until 1700100000 --method pbweighted

dsa110-contimg-mosaic build --name research_custom \
  --output /data/research/custom_analysis.image
```

Output: `/data/research/custom_analysis.image` (user-controlled location)

**Benefits**:

- Production gets all data automatically
- Researchers can explore subset in parallel
- No interference between workflows
- Both use same underlying code (consistency)

---

## Summary: Key Differences

| **Streaming**                                        | **Batch**                          |
| ---------------------------------------------------- | ---------------------------------- |
| "Process everything continuously"                    | "Process this specific thing once" |
| Automatic group formation                            | Manual group selection             |
| Deterministic per stage, non-deterministic per group | Deterministic end-to-end           |
| Daemon/background                                    | Task/foreground                    |
| Fire and forget                                      | Submit and monitor                 |
| Production operations                                | Research/reprocessing              |
| High throughput, eventual consistency                | Low latency, exact reproducibility |

---

## Implementation Details

### Streaming Entry Point

File: `conversion/streaming/streaming_converter.py`,
`mosaic/streaming_mosaic.py`

Key pattern:

```python
while True:  # Infinite polling loop
    try:
        process_next_batch()
    except Exception as e:
        logger.error(f"Error in cycle: {e}")
    time.sleep(poll_interval)
```

### Batch Entry Point

File: `mosaic/cli.py`, `pipeline/orchestrator.py`

Key pattern:

```python
def main(args):
    # Parse exact user specification
    context = build_context_from_args(args)

    # Execute deterministically
    result = orchestrator.run(context)

    # Exit with status
    return 0 if result.success else 1
```

---

## Recommended Defaults

### For Production (Observatory)

```bash
# Start in background/screen/tmux
dsa110-contimg-convert-stream \
  --input-dir /data/incoming/ \
  --output-dir /stage/dsa110-contimg/ms/ \
  &

dsa110-contimg-streaming-mosaic --loop \
  &
```

### For Research/Reprocessing

```bash
# Interactive, one-shot analysis
dsa110-contimg-mosaic plan --name my_analysis --since <ts> --until <ts>
dsa110-contimg-mosaic build --name my_analysis --output /data/output.image --dry-run

# Review then execute
dsa110-contimg-mosaic build --name my_analysis --output /data/output.image
```

### For Automated Integration

```bash
# Use API for job submission
POST /api/jobs/
Content-Type: application/json
{
  "type": "mosaic",
  "params": {...}
}

# Poll for completion
GET /api/jobs/12345/status
```
