# Storage Architecture and File Organization

This guide consolidates all documentation about file handling, storage architecture, and database organization for the DSA-110 continuum imaging pipeline.

## Storage Hierarchy

The pipeline uses a tiered storage architecture optimized for different I/O patterns:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DSA-110 Storage Architecture                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   /data/ (HDD - Slow, Large Capacity)                                       │
│   ├── incoming/              ← Raw HDF5 subband files from correlator       │
│   ├── dsa110-contimg/        ← Source code, state, databases                │
│   │   ├── state/             ← Pipeline state and databases                 │
│   │   │   ├── db/            ← SQLite databases (pipeline.sqlite3)          │
│   │   │   ├── catalogs/      ← Survey catalogs (NVSS, FIRST, VLASS)         │
│   │   │   ├── logs/          ← Pipeline execution logs                      │
│   │   │   └── run/           ← PID files, status JSON                       │
│   │   └── products/ → /stage/dsa110-contimg/ (symlink)                      │
│   │                                                                         │
│   /stage/ (NVMe SSD - Fast, Working Data)                                   │
│   └── dsa110-contimg/        ← All pipeline output products                 │
│       ├── ms/                ← Measurement Sets                             │
│       ├── images/            ← FITS images (dirty, clean, residual)         │
│       ├── mosaics/           ← Combined mosaic images                       │
│       ├── thumbnails/        ← Preview images for dashboard                 │
│       ├── caltables/         ← Calibration tables                           │
│       └── scratch/           ← Temporary working files                      │
│                                                                             │
│   /scratch/ (NVMe SSD - Ephemeral, Builds)                                  │
│   └── (temporary builds, npm, mkdocs)                                       │
│                                                                             │
│   /dev/shm/ (tmpfs - RAM-backed, Ultra-fast)                                │
│   └── (in-memory staging during conversion)                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Storage Tier Summary

| Mount       | Type     | Speed   | Use Case                            |
| ----------- | -------- | ------- | ----------------------------------- |
| `/data/`    | HDD      | Slow    | Raw input, source code, databases   |
| `/stage/`   | NVMe SSD | Fast    | Output products, working data       |
| `/scratch/` | NVMe SSD | Fast    | Ephemeral builds, temp files        |
| `/dev/shm/` | tmpfs    | Fastest | In-memory staging during conversion |

> **⚠️ CRITICAL**: `/data/` is on HDD. Avoid I/O-intensive operations there.
> Use `/scratch/` or `/stage/` for builds, processing, and temporary files.

### Symlinks as Abstraction Layer

The project uses symlinks for three distinct purposes:

#### 1. Storage Tiering (`products/` → `/stage/`)

Route heavy I/O to fast NVMe storage while keeping the codebase on HDD:

```
products/caltables  →  /stage/dsa110-contimg/caltables
products/catalogs   →  /stage/dsa110-contimg/catalogs
products/images     →  /stage/dsa110-contimg/images
products/mosaics    →  /stage/dsa110-contimg/mosaics
products/ms         →  /stage/dsa110-contimg/ms
```

Code references `products/ms`, but writes actually go to SSD. This is **performance-critical infrastructure**.

#### 2. Path Convenience (`state/` internal)

Provide shorter aliases within the `state/` directory:

```
state/ms             →  data/ms
state/pointing       →  data/pointing
state/skymodels      →  data/skymodels
state/synth          →  data/synth
state/transit_cache  →  cache/transit
state/cfcache        →  cache/cf
```

Instead of `state/data/pointing`, code can use `state/pointing`. These are documented shortcuts that reduce path verbosity while maintaining a clean underlying hierarchy (`data/` for persistent, `cache/` for ephemeral).

#### 3. Root Cleanliness (config organization)

Keep configuration files organized while meeting tool requirements:

```
.husky              →  config/hooks/husky
docker-compose.yml  →  ops/docker/docker-compose.yml
```

Tools like husky and docker-compose expect files at the repo root. Symlinks satisfy this while keeping actual files in organized subdirectories.

> **Summary**: Symlinks serve as an abstraction layer between logical paths (what code references) and physical locations (where data actually lives), enabling performance optimization and organizational clarity without changing application code.

---

## Data Flow Through the Pipeline

```
                              DATA FLOW
                              =========

  Correlator                                                    Dashboard
      │                                                             ▲
      │ writes                                                      │ serves
      ▼                                                             │
┌──────────────┐     ┌──────────────┐     ┌──────────────┐    ┌──────────┐
│ /data/       │     │ /stage/.../  │     │ /stage/.../  │    │ /stage/  │
│ incoming/    │────▶│ ms/          │────▶│ images/      │───▶│ thumbs/  │
│              │     │              │     │              │    │          │
│ *_sb??.hdf5  │     │ *.ms         │     │ *.fits       │    │ *.png    │
└──────────────┘     └──────────────┘     └──────────────┘    └──────────┘
      │                    │                    │                   │
      │                    │                    │                   │
      └────────────────────┴────────────────────┴───────────────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │  pipeline.sqlite3     │
                        │  (tracks everything)  │
                        └───────────────────────┘
```

### File Lifecycle

1. **Ingest**: HDF5 files arrive in `/data/incoming/`
2. **Normalize**: Filenames normalized to canonical `group_id` (see below)
3. **Convert**: 16 subbands → 1 Measurement Set in `/stage/.../ms/`
4. **Calibrate**: Apply calibration, update MS in place
5. **Image**: Create FITS images in `/stage/.../images/`
6. **Thumbnail**: Generate previews in `/stage/.../thumbnails/`
7. **Register**: All products tracked in `pipeline.sqlite3`

---

## File Naming Conventions

### HDF5 Subband Files

```
{timestamp}_sb{XX}.hdf5

Examples:
  2025-01-15T12:00:00_sb00.hdf5
  2025-01-15T12:00:00_sb01.hdf5
  ...
  2025-01-15T12:00:00_sb15.hdf5
```

- **timestamp**: ISO 8601 UTC time (YYYY-MM-DDTHH:MM:SS)
- **XX**: Zero-padded subband index (00-15)
- **16 files per observation** (one per 64 MHz subband)

#### Filename Normalization

The correlator may write subbands with slightly different timestamps due to I/O timing variations. The pipeline **normalizes filenames on ingest** so all 16 subbands share the same canonical timestamp.

**The Problem:**

```
# As correlator writes (timestamps drift by 1-2 seconds):
2025-01-15T12:00:00_sb00.hdf5   # First subband
2025-01-15T12:00:01_sb01.hdf5   # 1 second later
2025-01-15T12:00:00_sb02.hdf5   # Same as first
2025-01-15T12:00:02_sb03.hdf5   # 2 seconds later
```

Previously, the pipeline used ±60 second fuzzy clustering to group these files, which required complex SQL queries and was non-deterministic at edge cases.

**The Solution:**

When a subband arrives, if it clusters with an existing group in the database, rename the file to use the canonical `group_id` (the timestamp of the first subband that arrived):

```
BEFORE (as correlator writes):             AFTER (normalized):
2025-01-15T12:00:00_sb00.hdf5       →      2025-01-15T12:00:00_sb00.hdf5  (canonical)
2025-01-15T12:00:01_sb01.hdf5       →      2025-01-15T12:00:00_sb01.hdf5  (renamed)
2025-01-15T12:00:00_sb02.hdf5       →      2025-01-15T12:00:00_sb02.hdf5  (unchanged)
2025-01-15T12:00:02_sb03.hdf5       →      2025-01-15T12:00:00_sb03.hdf5  (renamed)
```

**How It Works:**

```
┌─────────────────────────────────────────────────────────────────┐
│  New file arrives: 2025-01-15T12:00:02_sb05.hdf5                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Parse filename → group_id="2025-01-15T12:00:02", subband_idx=5 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Query: Does a group exist within ±60s of this timestamp?       │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────────────┐
│  No existing group       │    │  Found group: canonical=T12:00:00│
│  → This becomes canonical│    │  → Rename file to match          │
└──────────────────────────┘    └──────────────────────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Result: 2025-01-15T12:00:00_sb05.hdf5                          │
│  All 16 subbands now share the same timestamp in filesystem     │
└─────────────────────────────────────────────────────────────────┘
```

**Benefits:**

| Aspect          | Before (Fuzzy Clustering)                | After (Normalization)                         |
| --------------- | ---------------------------------------- | --------------------------------------------- |
| **Grouping**    | Complex SQL with tolerance windows       | Simple `GROUP BY group_id`                    |
| **Filesystem**  | Mixed timestamps, unclear membership     | Self-documenting: same timestamp = same group |
| **Queries**     | `ABS(julianday(a) - julianday(b)) <= 60` | `WHERE group_id = ?`                          |
| **Idempotency** | N/A                                      | Safe to re-run normalizer                     |

### Measurement Sets

```
{timestamp}.ms

Example:
  2025-01-15T12:00:00.ms
```

- Named after the canonical `group_id`
- Contains all 16 subbands combined (16,384 channels)
- ~5 minutes of observation time (24 fields × 12.88s each)

### FITS Images

```
{ms_name}-{field}-{type}.fits

Examples:
  2025-01-15T12:00:00-3C286_t17-image.fits    # Clean image
  2025-01-15T12:00:00-3C286_t17-residual.fits # Residual
  2025-01-15T12:00:00-3C286_t17-model.fits    # Model
  2025-01-15T12:00:00-3C286_t17-psf.fits      # PSF/beam
```

---

## The `group_id` Concept

The `group_id` is the **canonical timestamp** that uniquely identifies an observation:

| Property        | Value                                |
| --------------- | ------------------------------------ |
| **Format**      | `YYYY-MM-DDTHH:MM:SS` (ISO 8601 UTC) |
| **Source**      | First subband filename to arrive     |
| **Immutable**   | Once set, never changes              |
| **Primary Key** | Used across all database tables      |

### How `group_id` Links Everything

```sql
-- All products trace back to group_id:
processing_queue.group_id  -- Ingest queue entry
subband_files.group_id     -- Individual HDF5 files
ms_index.group_id          -- Converted Measurement Set
images.ms_path → ms_index  -- FITS images (via MS)
```

### Example Query: Full Observation Chain

```sql
-- Find all products for an observation
SELECT
    q.group_id,
    q.state AS queue_state,
    COUNT(sf.subband_idx) AS subbands,
    m.path AS ms_path,
    m.status AS ms_status,
    i.path AS image_path
FROM processing_queue q
LEFT JOIN subband_files sf ON sf.group_id = q.group_id
LEFT JOIN ms_index m ON m.group_id = q.group_id
LEFT JOIN images i ON i.ms_path = m.path
WHERE q.group_id = '2025-01-15T12:00:00'
GROUP BY q.group_id;
```

---

## Database Architecture

### Primary Database: `pipeline.sqlite3`

Located at `/data/dsa110-contimg/state/db/pipeline.sqlite3`

This is the **single source of truth** for all pipeline state. It uses SQLite with WAL mode for concurrent access.

#### Core Tables

| Table                | Purpose                               | Primary Key               |
| -------------------- | ------------------------------------- | ------------------------- |
| `processing_queue`   | Ingest queue (collecting → completed) | `group_id`                |
| `subband_files`      | Individual HDF5 file paths            | `(group_id, subband_idx)` |
| `ms_index`           | Measurement Set registry              | `path`                    |
| `images`             | FITS image registry                   | `id` (auto)               |
| `calibration_tables` | Calibration table registry            | `path`                    |
| `photometry`         | Source measurements                   | `id` (auto)               |
| `mosaics`            | Combined mosaic images                | `id` (auto)               |

#### Queue States

```
collecting → pending → in_progress → completed
                  ↘                 ↗
                    → failed (retry up to 3x)
```

| State         | Meaning                                |
| ------------- | -------------------------------------- |
| `collecting`  | Waiting for all 16 subbands            |
| `pending`     | Complete, queued for conversion        |
| `in_progress` | Currently being converted              |
| `completed`   | Successfully converted to MS           |
| `failed`      | Conversion failed (see `error` column) |

#### Schema: `processing_queue`

```sql
CREATE TABLE processing_queue (
    group_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,              -- collecting/pending/in_progress/completed/failed
    received_at REAL NOT NULL,        -- Unix timestamp of first subband
    last_update REAL NOT NULL,        -- Unix timestamp of last update
    expected_subbands INTEGER,        -- Usually 16
    retry_count INTEGER DEFAULT 0,    -- Retry attempts (max 3)
    error TEXT,                       -- Error type if failed
    error_message TEXT,               -- Full error message
    processing_stage TEXT,            -- Current pipeline stage
    has_calibrator INTEGER,           -- 1 if calibrator detected
    calibrators TEXT                  -- JSON list of calibrator names
);
```

#### Schema: `subband_files`

```sql
CREATE TABLE subband_files (
    group_id TEXT NOT NULL,
    subband_idx INTEGER NOT NULL,     -- 0-15
    path TEXT NOT NULL UNIQUE,        -- Full path to HDF5 file
    PRIMARY KEY (group_id, subband_idx),
    FOREIGN KEY (group_id) REFERENCES processing_queue(group_id)
);
```

#### Schema: `ms_index`

```sql
CREATE TABLE ms_index (
    path TEXT PRIMARY KEY,            -- Full path to .ms directory
    group_id TEXT,                    -- Links to processing_queue
    start_mjd REAL,                   -- Observation start (MJD)
    end_mjd REAL,                     -- Observation end (MJD)
    mid_mjd REAL,                     -- Midpoint (MJD)
    status TEXT,                      -- Processing status
    stage TEXT,                       -- Pipeline stage
    cal_applied INTEGER DEFAULT 0,    -- Calibration applied flag
    field_name TEXT,                  -- Primary field (may be calibrator)
    pointing_ra_deg REAL,             -- Pointing center RA
    pointing_dec_deg REAL,            -- Pointing center Dec
    created_at REAL                   -- Registration timestamp
);
```

### Other Databases

| Database                  | Location    | Purpose                    |
| ------------------------- | ----------- | -------------------------- |
| `hdf5.sqlite3`            | `state/db/` | Fast HDF5 metadata cache   |
| `docsearch.sqlite3`       | `state/db/` | Documentation search index |
| `embedding_cache.sqlite3` | `state/db/` | OpenAI embedding cache     |

### Catalog Databases

Located in `state/catalogs/`:

| Database                  | Content                             |
| ------------------------- | ----------------------------------- |
| `nvss_dec+XX.X.sqlite3`   | NVSS sources by declination strip   |
| `first_dec+XX.X.sqlite3`  | FIRST survey sources                |
| `vlass_dec+XX.X.sqlite3`  | VLASS sources                       |
| `vla_calibrators.sqlite3` | VLA calibrator catalog              |
| `master_sources.sqlite3`  | Combined crossmatch (~1.6M sources) |

---

## Directory Reference

### Input Directories

| Path              | Contents               | Retention                |
| ----------------- | ---------------------- | ------------------------ |
| `/data/incoming/` | Raw HDF5 subband files | Cleared after conversion |

### Output Directories

| Path                                | Contents           | Retention   |
| ----------------------------------- | ------------------ | ----------- |
| `/stage/dsa110-contimg/ms/`         | Measurement Sets   | Permanent   |
| `/stage/dsa110-contimg/images/`     | FITS images        | Permanent   |
| `/stage/dsa110-contimg/mosaics/`    | Mosaic images      | Permanent   |
| `/stage/dsa110-contimg/thumbnails/` | Preview PNGs       | Regenerable |
| `/stage/dsa110-contimg/caltables/`  | Calibration tables | Permanent   |

### State Directories

| Path                                   | Contents          |
| -------------------------------------- | ----------------- |
| `/data/dsa110-contimg/state/db/`       | SQLite databases  |
| `/data/dsa110-contimg/state/catalogs/` | Survey catalogs   |
| `/data/dsa110-contimg/state/logs/`     | Pipeline logs     |
| `/data/dsa110-contimg/state/run/`      | PID files, status |

### Temporary Directories

| Path                             | Contents              | Cleanup        |
| -------------------------------- | --------------------- | -------------- |
| `/stage/dsa110-contimg/scratch/` | Conversion temp files | Auto-cleanup   |
| `/scratch/`                      | Build artifacts       | Manual cleanup |
| `/dev/shm/`                      | In-memory staging     | Auto-cleanup   |

---

## Environment Variables

| Variable               | Default                     | Description              |
| ---------------------- | --------------------------- | ------------------------ |
| `PIPELINE_INPUT_DIR`   | `/data/incoming`            | HDF5 input directory     |
| `PIPELINE_OUTPUT_DIR`  | `/stage/dsa110-contimg/ms`  | MS output directory      |
| `PIPELINE_SCRATCH_DIR` | `/stage/dsa110-contimg`     | Fast scratch storage     |
| `PIPELINE_STATE_DIR`   | `state`                     | State/database directory |
| `PIPELINE_DB`          | `state/db/pipeline.sqlite3` | Primary database path    |

---

## Common Operations

### Query Processing Status

```bash
# Count by state
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
  "SELECT state, COUNT(*) FROM processing_queue GROUP BY state;"

# Recent completions
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
  "SELECT group_id, datetime(last_update, 'unixepoch')
   FROM processing_queue
   WHERE state='completed'
   ORDER BY last_update DESC LIMIT 10;"
```

### Find Products for Observation

```bash
# Find MS and images for a group_id
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
  "SELECT m.path, i.path
   FROM ms_index m
   LEFT JOIN images i ON i.ms_path = m.path
   WHERE m.group_id = '2025-01-15T12:00:00';"
```

### Normalize Historical Files

If you have historical files with mixed timestamps, normalize them using the batch CLI:

```bash
# Preview what would be renamed (safe - no changes made)
python -m dsa110_contimg.conversion.streaming.normalize_cli \
    --dry-run --verbose /data/incoming

# Actually perform renames
python -m dsa110_contimg.conversion.streaming.normalize_cli /data/incoming

# Custom tolerance (default is 60 seconds)
python -m dsa110_contimg.conversion.streaming.normalize_cli \
    --tolerance 30 /data/incoming
```

**Python API:**

```python
from dsa110_contimg.conversion.streaming import (
    normalize_subband_path,      # Rename single file
    normalize_subband_on_ingest, # Entry point for streaming
    normalize_directory,         # Batch normalize historical files
)

# Batch normalize with preview
stats = normalize_directory(
    directory=Path("/data/incoming"),
    cluster_tolerance_s=60.0,
    dry_run=True,
)
print(f"Would rename {stats['files_renamed']} of {stats['files_scanned']} files")

# Apply renames
stats = normalize_directory(Path("/data/incoming"), dry_run=False)
```

### Disk Usage

```bash
# Check storage usage
du -sh /data/incoming/
du -sh /stage/dsa110-contimg/ms/
du -sh /stage/dsa110-contimg/images/
```

---

## Quick Reference

### Port Assignments

| Port | Service                | Environment |
| ---- | ---------------------- | ----------- |
| 3210 | Dashboard (production) | Production  |
| 5173 | Vite dev server        | Development |
| 6006 | Storybook              | Development |
| 8000 | FastAPI backend        | Both        |
| 8001 | MkDocs                 | Development |
| 3030 | Grafana                | Production  |
| 9090 | Prometheus             | Production  |
| 9002 | CARTA                  | Both        |

### CLI Commands

| Command                                           | Description     |
| ------------------------------------------------- | --------------- |
| `python -m dsa110_contimg.conversion.cli --help`  | Conversion CLI  |
| `python -m dsa110_contimg.calibration.cli --help` | Calibration CLI |
| `python -m dsa110_contimg.imaging.cli --help`     | Imaging CLI     |
| `python -m dsa110_contimg.mosaic.cli --help`      | Mosaic CLI      |
| `python -m dsa110_contimg.photometry.cli --help`  | Photometry CLI  |

### API Endpoints

| Endpoint                    | Method | Description            |
| --------------------------- | ------ | ---------------------- |
| `/api/status`               | GET    | Pipeline status        |
| `/api/streaming/status`     | GET    | Streaming queue status |
| `/api/streaming/start`      | POST   | Start streaming        |
| `/api/streaming/stop`       | POST   | Stop streaming         |
| `/api/data/observations`    | GET    | List observations      |
| `/api/data/images`          | GET    | List images            |
| `/api/mosaic/create`        | POST   | Create mosaic          |
| `/api/mosaic/status/{name}` | GET    | Mosaic status          |

---

## Getting Help

- **Local Docs Search**: `python -m dsa110_contimg.docsearch.cli search "your query"`
- **API Docs**: http://localhost:8000/api/docs
- **GitHub Issues**: https://github.com/dsa110/dsa110-contimg/issues
- **Troubleshooting Guide**: [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)

---

## Related Documentation

- Streaming Pipeline Operations (`backend/docs/ops/streaming-pipeline.md`) - Streaming converter guide
- [Dashboard Guide](dashboard.md) - Web dashboard documentation
- [Calibration Guide](calibration.md) - Calibration workflows
- [Imaging Guide](imaging.md) - Image creation
- [Mosaicking Guide](mosaicking.md) - Mosaic creation
