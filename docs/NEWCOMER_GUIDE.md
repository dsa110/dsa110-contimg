# Newcomer's Guide to DSA-110 Continuum Imaging Pipeline

**Start here if you're new to this codebase.** This guide cuts through the complexity and shows you what actually works today.

---

## ⚠️ Critical: What's Real vs What's Documentation

This codebase has evolved through multiple architectural iterations. **Not all documentation reflects current reality.**

### Trust Hierarchy

1. **Running Code** > Documentation
2. **Working Examples** > Design Docs
3. **Recent Commits** > Old READMEs

**Design documents like `COMPLEXITY_REDUCTION.md` describe the FUTURE, not the present.**

---

## Quick Decision Tree: How Do I Process HDF5 Files?

```
Need to convert HDF5 → Measurement Set?
│
├─ Processing historical/archived data?
│  └─ ✅ Use: Batch Converter
│     • Module: dsa110_contimg.conversion.hdf5_orchestrator
│     • Function: convert_subband_groups_to_ms()
│     • CLI: python -m dsa110_contimg.conversion.cli groups ...
│     • Status: PRODUCTION, STABLE
│
├─ Real-time/automated streaming ingestion?
   └─ ✅ Use: ABSURD Ingestion
     • Module: dsa110_contimg.absurd.ingestion
     • Worker: dsa110-absurd-worker@1 systemd service
│     • Database: PostgreSQL (port 5433) + SQLite
│     • Status: EXPERIMENTAL but only option for streaming
│
└─ Testing single observation?
   └─ ✅ Use: Batch Converter with narrow time window
      • See: scripts/test_0834_pipeline.py for example
```

---

## Two Working Pathways (and ONLY Two)

### 1. Batch Converter (Recommended for Historical Data)

**What it does:** Converts groups of 16 HDF5 subbands to Measurement Sets synchronously.

**When to use:**

- Processing archived observations
- One-off conversions
- Testing and development
- You want simple, predictable execution

**Example:**

```bash
conda activate casa6

# Convert all complete groups in a time window
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    "2025-10-21T00:00:00" \
    "2025-10-21T23:59:59"

# Python API
from dsa110_contimg.conversion.hdf5_orchestrator import convert_subband_groups_to_ms

convert_subband_groups_to_ms(
    input_dir="/data/incoming",
    output_dir="/stage/dsa110-contimg/ms",
    start_time="2025-10-21T00:00:00",
    end_time="2025-10-21T23:59:59",
)
```

**Key files:**

- `backend/src/dsa110_contimg/conversion/hdf5_orchestrator.py` - Main orchestrator
- `backend/src/dsa110_contimg/conversion/direct_subband.py` - MS writer
- `backend/src/dsa110_contimg/database/hdf5_index.py` - File grouping logic

### 2. ABSURD Ingestion (For Real-Time Processing)

**What it does:** PostgreSQL-backed task queue with durable execution for continuous data ingestion.

**When to use:**

- Scheduled/automated processing
- Need fault tolerance and retries
- Production streaming pipeline
- Multiple worker concurrency

**Example:**

```bash
# Check worker status (instance 1)
sudo systemctl status dsa110-absurd-worker@1

# Submit jobs via Python API
from dsa110_contimg.absurd.ingestion import submit_conversion_job

submit_conversion_job(
    input_files=subband_file_list,
    output_path="/stage/dsa110-contimg/ms/observation.ms"
)
```

**Key files:**

- `backend/src/dsa110_contimg/absurd/ingestion.py` - Job submission
- `backend/src/dsa110_contimg/absurd/worker.py` - Worker implementation
- PostgreSQL database at `localhost:5433`

---

## Critical Gotchas (Things That Will Bite You)

### 1. **Subband Grouping: NEVER Use Exact Timestamps**

❌ **WRONG:**

```bash
# This will fail silently
ls /data/incoming/2025-10-21T14:23:19_sb*.hdf5
```

The correlator writes subbands with **±60 second timestamp jitter**. A single observation's 16 subbands may have slightly different timestamps.

✅ **CORRECT:**

```python
from dsa110_contimg.database.hdf5_index import query_subband_groups

groups = query_subband_groups(
    db_path="/data/incoming/hdf5_file_index.sqlite3",
    start_time="2025-10-21T00:00:00",
    end_time="2025-10-21T23:59:59",
    cluster_tolerance_s=60.0,  # Groups files within 60s
)
```

### 2. **"Streaming Converter" References Are Stale**

If you see references to:

- `dsa110_contimg.conversion.streaming_converter`
- `streaming.streaming_converter`
- `python -m ...streaming_converter`

**These modules no longer exist.** They were replaced by ABSURD. Ignore documentation that mentions them.

### 3. **Design Docs ≠ Implementation**

Files like `COMPLEXITY_REDUCTION.md` and `EXECUTION_UNIFICATION_PLAN.md` describe **future architecture**, not current state.

Before implementing anything from a design doc:

1. Check if the module actually exists
2. Search for recent usage in code
3. Ask someone who knows the codebase

### 4. **LST ≠ Pointing Direction**

Common mistake: "Observation at LST 8.5h contains calibrator at RA 8.5h"

**Wrong!** LST tells you **when** you observed, not **where** you pointed.

The telescope can point anywhere while LST happens to equal 8.5h. Always check field RA/Dec in the MS FIELD table.

### 5. **Database Locations Are Split**

- HDF5 file index: `/data/incoming/hdf5_file_index.sqlite3`
- Pipeline state: `/data/dsa110-contimg/state/db/pipeline.sqlite3`
- ABSURD queue: PostgreSQL at `localhost:5433`

Don't assume everything is in one database.

---

## Common Tasks

### Find Complete Observation Groups

```bash
sqlite3 /data/incoming/hdf5_file_index.sqlite3 <<EOF
SELECT timestamp, COUNT(*) as count
FROM hdf5_file_index
GROUP BY timestamp
HAVING count = 16
ORDER BY timestamp DESC
LIMIT 10;
EOF
```

### Check Conversion Status

```bash
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 <<EOF
SELECT path, status, created_at
FROM ms_index
ORDER BY created_at DESC
LIMIT 10;
EOF
```

### Find Observations of Specific Calibrator

```python
from dsa110_contimg.calibration.transits import find_calibrator_transits

transits = find_calibrator_transits(
    calibrator_name="0834+555",
    start_time="2025-10-01",
    end_time="2025-10-31"
)
```

---

## Architecture Overview (Simplified)

```
Raw HDF5 Files          Conversion              Measurement Sets
(/data/incoming/)                               (/stage/dsa110-contimg/ms/)
       │                                                 │
       ├─ 16 subbands per observation                  │
       │  (timestamp ±60s jitter)                       │
       │                                                 │
       v                                                 v
┌─────────────────┐                           ┌─────────────────┐
│  HDF5 File      │                           │   MS Files      │
│  Index          │                           │   Registry      │
│  (SQLite)       │                           │   (SQLite)      │
└─────────────────┘                           └─────────────────┘
       │                                                 │
       v                                                 v
┌─────────────────────────────────────┐      ┌─────────────────┐
│     Two Conversion Pathways:        │      │  Calibration    │
│  1. Batch: hdf5_orchestrator.py     │─────>│  Imaging        │
│  2. ABSURD: absurd/ingestion.py     │      │  Photometry     │
└─────────────────────────────────────┘      └─────────────────┘
```

---

## Key Modules (What They Actually Do)

| Module                            | Purpose                    | Status          |
| --------------------------------- | -------------------------- | --------------- |
| `conversion/hdf5_orchestrator.py` | Batch HDF5→MS conversion   | ✅ Production   |
| `conversion/direct_subband.py`    | Direct MS table writer     | ✅ Production   |
| `absurd/ingestion.py`             | Real-time task queue       | ⚠️ Experimental |
| `calibration/selection.py`        | Find calibrators in fields | ✅ Production   |
| `calibration/cli.py`              | Run bandpass calibration   | ✅ Production   |
| `imaging/fast_imaging.py`         | WSClean wrapper            | ✅ Production   |
| `database/hdf5_index.py`          | Group subbands by time     | ✅ Production   |

---

## Testing Your Changes

```bash
conda activate casa6
cd /data/dsa110-contimg/backend

# Run unit tests (no CASA required)
python -m pytest tests/unit/ -v

# Run integration tests (requires CASA)
python -m pytest tests/integration/ -v

# Run specific test
python -m pytest tests/unit/conversion/test_helpers.py -v
```

**Important:** Use `python -m pytest`, not just `pytest`, to ensure you use casa6's pytest.

---

## Getting Help

1. **Check working examples:** `scripts/test_0834_pipeline.py`
2. **Search recent code:** Git history shows what's actually being used
3. **Query the database:** See what data actually exists
4. **Ask before building:** Verify the feature isn't already implemented

---

## What NOT to Trust

- ❌ References to "streaming converter" → Use ABSURD instead
- ❌ Design docs as implementation guides → Check code first
- ❌ Glob patterns for subband groups → Use query_subband_groups()
- ❌ LST for determining field position → Check FIELD table RA/Dec
- ❌ Systemd services with non-existent commands → Verify before starting

---

## Quick Reference Card

```bash
# Activate environment (ALWAYS FIRST)
conda activate casa6

# Batch convert historical data
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming /stage/dsa110-contimg/ms \
    "START_TIME" "END_TIME"

# Check ABSURD worker (instance 1)
sudo systemctl status dsa110-absurd-worker@1

# Query complete groups
sqlite3 /data/incoming/hdf5_file_index.sqlite3 \
  "SELECT timestamp, COUNT(*) FROM hdf5_file_index GROUP BY timestamp HAVING COUNT(*) = 16"

# Check conversion results
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
  "SELECT path, status FROM ms_index ORDER BY created_at DESC LIMIT 10"
```

---

## Next Steps

1. **Run the test script:** `python scripts/test_0834_pipeline.py`
2. **Read module READMEs:** Start with `conversion/README.md`
3. **Explore the database schema:** Check what data exists
4. **Look at recent commits:** See what's actively maintained

**Welcome to the DSA-110 pipeline! When in doubt, trust the code over the docs.**
