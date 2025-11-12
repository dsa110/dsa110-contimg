# Distinction: Streaming Converter vs Mosaic Orchestrator

## Overview

The DSA-110 pipeline has **two distinct automation paths** that serve different purposes:

1. **Streaming Converter** - Autonomous daemon for real-time data ingestion
2. **Mosaic Orchestrator** - Goal-driven workflow coordinator for end-to-end mosaic creation

---

## Streaming Converter

### Purpose
**Autonomous, reactive data ingestion** - watches for incoming files and processes them automatically.

### Architecture
- **Type:** Long-running daemon/service
- **Trigger:** File system events (new `*_sb??.hdf5` files arrive)
- **Operation Mode:** Continuous, reactive
- **Scope:** Individual MS file processing

### Key Characteristics

**1. File-Driven Operation**
```python
# Watches /data/incoming/ for new files
# Automatically groups by timestamp (5-minute windows, 16 subbands)
# Processes complete groups as they arrive
```

**2. Autonomous Operation**
- Runs continuously as a background service
- No user interaction required
- Automatically handles file arrivals, grouping, conversion
- State machine: `collecting` → `pending` → `in_progress` → `completed`

**3. Limited Scope**
- **Primary Function:** Convert UVH5 → MS
- **Secondary Function:** Apply calibration if available (development tier)
- **Secondary Function:** Image individual MS files (standard tier)
- **Does NOT:** Create mosaics, coordinate groups, solve calibration

### Code Location
- **File:** `src/dsa110_contimg/conversion/streaming/streaming_converter.py`
- **Entry Point:** `streaming_converter.py` CLI (runs as daemon)
- **Database:** `state/ingest.sqlite3` (queue tracking)

### Use Case
**When to use:** Real-time data ingestion during observations
- Telescope is actively observing
- UVH5 files are arriving continuously
- Need automatic conversion as data arrives
- Want minimal human intervention

### Example Usage
```bash
# Start streaming converter daemon
python -m dsa110_contimg.conversion.streaming.streaming_converter \
    --input-dir /data/incoming \
    --output-dir /stage/dsa110-contimg/ms \
    --watch
```

### Automation Level
- **Conversion:** 100% automated
- **Calibration:** 50% automated (applies if available, doesn't solve)
- **Imaging:** 50% automated (per-MS, not coordinated)
- **Mosaic Creation:** 0% automated
- **QA/Publishing:** 0% automated

---

## Mosaic Orchestrator

### Purpose
**Goal-driven workflow coordination** - orchestrates complete end-to-end pipeline from HDF5 to published mosaic.

### Architecture
- **Type:** On-demand workflow coordinator
- **Trigger:** User command or script invocation
- **Operation Mode:** Episodic, proactive
- **Scope:** Complete mosaic creation workflow

### Key Characteristics

**1. Goal-Driven Operation**
```python
# User specifies goal: "Create mosaic centered on calibrator 0834+555"
# Orchestrator:
#   1. Finds transit window
#   2. Ensures MS files exist (triggers conversion if needed)
#   3. Forms group
#   4. Solves calibration
#   5. Applies calibration
#   6. Images all MS files
#   7. Creates mosaic
#   8. Validates and publishes
```

**2. Intelligent Coordination**
- **Auto-inference:** Dec from data → BP calibrator → validity windows → skymodels
- **Transit Discovery:** Automatically finds calibrator transit times
- **Workflow Management:** Coordinates multiple pipeline stages
- **State Tracking:** Manages group formation, calibration, imaging, mosaic creation

**3. Complete Scope**
- **Primary Function:** End-to-end mosaic creation
- **Includes:** Conversion (if needed), calibration solving, imaging, mosaic creation, QA, publishing
- **Hands-off Operation:** Single trigger → wait until published

### Code Location
- **File:** `src/dsa110_contimg/mosaic/orchestrator.py`
- **Manager:** `src/dsa110_contimg/mosaic/streaming_mosaic.py` (StreamingMosaicManager)
- **Entry Point:** `scripts/create_mosaic_centered.py` (example script)
- **Database:** `state/products.sqlite3`, `state/cal_registry.sqlite3`, `state/data_registry.sqlite3`

### Use Case
**When to use:** On-demand mosaic creation for science analysis
- Need a complete mosaic for a specific time window
- Want to process historical data
- Need coordinated group processing (10 MS files → 1 mosaic)
- Want full automation with minimal user input

### Example Usage
```bash
# Create mosaic centered on calibrator transit
python scripts/create_mosaic_centered.py \
    --calibrator 0834+555 \
    --timespan-minutes 50

# Orchestrator automatically:
# - Finds transit window
# - Converts HDF5 if needed
# - Solves calibration
# - Images all MS files
# - Creates mosaic
# - Validates and publishes
```

### Automation Level
- **Conversion:** 100% automated (triggers if needed)
- **Calibration:** 100% automated (solves + applies)
- **Imaging:** 100% automated (coordinated group imaging)
- **Mosaic Creation:** 100% automated
- **QA/Publishing:** 100% automated

---

## Key Differences

| Aspect | Streaming Converter | Mosaic Orchestrator |
|--------|---------------------|-------------------|
| **Operation Mode** | Continuous daemon | On-demand workflow |
| **Trigger** | File system events | User command/goal |
| **Scope** | Individual MS files | Complete mosaics |
| **Calibration** | Applies if available | Solves + applies |
| **Imaging** | Per-MS, independent | Coordinated group |
| **Mosaic Creation** | Not implemented | Fully automated |
| **QA/Publishing** | Not implemented | Fully automated |
| **Use Case** | Real-time ingestion | Science analysis |
| **User Interaction** | Minimal (start daemon) | Single command |

---

## Relationship Between Them

### Complementary Roles

**Streaming Converter:**
- Handles **real-time data ingestion** during observations
- Processes files as they arrive
- Provides **foundation** (MS files) for downstream processing

**Mosaic Orchestrator:**
- Uses **existing MS files** (from streaming converter or batch conversion)
- Coordinates **complete workflows** for science products
- Provides **end-to-end automation** for mosaic creation

### Workflow Integration

```
┌─────────────────────────────────────────────────────────────┐
│                    Observation Period                        │
│                                                              │
│  UVH5 Files → [Streaming Converter] → MS Files              │
│     (arriving)    (autonomous)      (staging)               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Science Analysis                          │
│                                                              │
│  MS Files → [Mosaic Orchestrator] → Published Mosaic        │
│  (staging)    (on-demand)        (products)                 │
└─────────────────────────────────────────────────────────────┘
```

### When They Work Together

1. **Streaming Converter** runs continuously during observations
   - Converts UVH5 → MS automatically
   - Applies calibration if available
   - Images individual MS files

2. **Mosaic Orchestrator** runs on-demand for science analysis
   - Uses MS files created by streaming converter
   - Solves calibration if needed (more complete than streaming converter)
   - Creates coordinated mosaics from groups of MS files
   - Validates and publishes science-ready products

---

## Summary

**Streaming Converter:**
- **What:** Autonomous daemon for real-time data ingestion
- **When:** During observations (continuous operation)
- **How:** Reactive (responds to file arrivals)
- **Output:** Individual MS files (and optionally images)

**Mosaic Orchestrator:**
- **What:** Goal-driven workflow coordinator
- **When:** On-demand for science analysis
- **How:** Proactive (coordinates complete workflows)
- **Output:** Published science-ready mosaics

**Key Insight:** They serve different purposes in the pipeline lifecycle:
- **Streaming Converter** = Data ingestion layer (foundation)
- **Mosaic Orchestrator** = Science product layer (analysis)

Both are needed for a complete pipeline, but they operate at different levels and serve different use cases.

