# DSA-110 Dashboard: Data Models & Database Schema

**Date:** 2025-11-12  
**Status:** Consolidated data models and database schema documentation  
**Audience:** Backend developers, frontend developers, database administrators

---

## Table of Contents

1. [Database Architecture](#database-architecture)
2. [Ingest Queue Database](#ingest-queue-database)
3. [Products Database](#products-database)
4. [Calibration Registry](#calibration-registry)
5. [Master Sources Catalog](#master-sources-catalog)
6. [Data Models (Pydantic/TypeScript)](#data-models-pydantictypescript)
7. [Query Patterns](#query-patterns)
8. [Migration & Schema Evolution](#migration--schema-evolution)

---

## Database Architecture

### Overview

The pipeline uses **4 SQLite databases** for state management and product
tracking:

| Database                 | Location                         | Purpose                                     |
| ------------------------ | -------------------------------- | ------------------------------------------- |
| `ingest.sqlite3`         | `/data/dsa110-contimg/state/`    | Queue management, subband tracking          |
| `cal_registry.sqlite3`   | `/data/dsa110-contimg/state/`    | Calibration table registry                  |
| `products.sqlite3`       | `/data/dsa110-contimg/state/`    | Images, photometry, MS index                |
| `master_sources.sqlite3` | `/data/dsa110-contimg/state/db/` | NVSS/VLASS/FIRST crossmatch (1.6M+ sources) |

### Design Principles

- **Separation of Concerns**: Each database handles a specific domain
- **SQLite for Simplicity**: No external database server required
- **Indexed for Performance**: Strategic indices for common queries
- **Schema Versioning**: Migration scripts for schema evolution

---

## Ingest Queue Database

### Table: `ingest_queue`

Tracks observation groups through the pipeline.

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS ingest_queue (
    group_id TEXT PRIMARY KEY,              -- YYYY-MM-DDTHH:MM:SS format
    state TEXT NOT NULL,                    -- collecting|pending|in_progress|completed|failed
    received_at REAL NOT NULL,              -- Unix timestamp
    last_update REAL NOT NULL,              -- Unix timestamp
    expected_subbands INTEGER DEFAULT 16,   -- Usually 16
    has_calibrator INTEGER,                 -- 0/1 boolean (NULL if not checked yet)
    calibrators TEXT,                       -- JSON array of matched calibrators
    retry_count INTEGER DEFAULT 0,          -- Number of retry attempts
    error_message TEXT                      -- Error details if failed
);

CREATE INDEX IF NOT EXISTS idx_ingest_state ON ingest_queue(state);
CREATE INDEX IF NOT EXISTS idx_ingest_received ON ingest_queue(received_at);
```

**Pipeline States:**

- `collecting` :arrow_right: `pending` :arrow_right: `in_progress` :arrow_right: `processing_fresh` :arrow_right: `completed`
- `failed` - Error state with retry capability

---

### Table: `subband_files`

Tracks individual subband files per group.

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS subband_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id TEXT NOT NULL,
    subband_idx INTEGER NOT NULL,          -- 0-15
    file_path TEXT NOT NULL,
    file_size INTEGER,
    discovered_at REAL NOT NULL,
    FOREIGN KEY (group_id) REFERENCES ingest_queue(group_id),
    UNIQUE(group_id, subband_idx)
);

CREATE INDEX IF NOT EXISTS idx_subband_group ON subband_files(group_id);
```

---

### Table: `performance_metrics`

Processing performance per group.

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id TEXT NOT NULL UNIQUE,
    writer_type TEXT,                      -- 'parallel-subband' | 'pyuvdata' | 'auto'
    conversion_time REAL,                  -- Seconds
    concat_time REAL,
    k_solve_time REAL,
    bp_solve_time REAL,
    g_solve_time REAL,
    imaging_time REAL,
    photometry_time REAL,
    total_time REAL,
    recorded_at REAL NOT NULL,
    FOREIGN KEY (group_id) REFERENCES ingest_queue(group_id)
);

CREATE INDEX IF NOT EXISTS idx_perf_group ON performance_metrics(group_id);
```

---

## Products Database

### Table: `ms_index`

Tracks Measurement Sets through processing stages.

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS ms_index (
    path TEXT PRIMARY KEY,                 -- Full path to MS
    start_mjd REAL,
    end_mjd REAL,
    mid_mjd REAL,                          -- For time-based queries
    processed_at REAL,                     -- Unix timestamp
    status TEXT,                           -- 'ok' | 'failed' | 'flagged'
    stage TEXT,                            -- 'converted' | 'calibrated' | 'imaged' | 'photometry_complete'
    stage_updated_at REAL,                 -- Unix timestamp
    cal_applied INTEGER DEFAULT 0,         -- Boolean: calibration applied
    imagename TEXT,                        -- Path to primary image (if imaged)
    field_name TEXT,                       -- Field ID (e.g., 'J1234+42')
    pointing_ra_deg REAL,                  -- Pointing center RA
    pointing_dec_deg REAL                  -- Pointing center Dec
);

CREATE INDEX IF NOT EXISTS idx_ms_index_stage_path ON ms_index(stage, path);
CREATE INDEX IF NOT EXISTS idx_ms_index_status ON ms_index(status);
CREATE INDEX IF NOT EXISTS idx_ms_index_mjd ON ms_index(mid_mjd);
CREATE INDEX IF NOT EXISTS idx_ms_index_field ON ms_index(field_name);
```

**MS Processing Stages:**

- `converted` :arrow_right: `calibrated` :arrow_right: `imaged` :arrow_right: `photometry_complete`

---

### Table: `images`

Catalog of image products.

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,             -- Full path to image file
    ms_path TEXT NOT NULL,                 -- Source MS
    created_at REAL NOT NULL,              -- Unix timestamp
    type TEXT NOT NULL,                    -- 'image' | 'pbcor' | 'residual' | 'mosaic'
    format TEXT DEFAULT 'fits',            -- 'fits' | 'casa'
    beam_major_arcsec REAL,                -- Restoring beam major axis
    beam_minor_arcsec REAL,
    beam_pa_deg REAL,
    noise_jy REAL,                         -- Image RMS noise (Jy/beam)
    dynamic_range REAL,                    -- Peak / RMS
    pbcor INTEGER DEFAULT 0,               -- Boolean: primary beam corrected
    field_name TEXT,
    center_ra_deg REAL,
    center_dec_deg REAL,
    imsize_x INTEGER,
    imsize_y INTEGER,
    cellsize_arcsec REAL,
    freq_ghz REAL,
    bandwidth_mhz REAL,
    integration_sec REAL,                  -- Total integration time
    FOREIGN KEY (ms_path) REFERENCES ms_index(path)
);

CREATE INDEX IF NOT EXISTS idx_images_ms_path ON images(ms_path);
CREATE INDEX IF NOT EXISTS idx_images_type ON images(type);
CREATE INDEX IF NOT EXISTS idx_images_created ON images(created_at);
CREATE INDEX IF NOT EXISTS idx_images_field ON images(field_name);
```

---

### Table: `photometry`

Forced photometry measurements on sources.

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS photometry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path TEXT NOT NULL,              -- Which image
    source_id TEXT NOT NULL,               -- NVSS ID (e.g., 'NVSS J123456.7+420312')
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    nvss_flux_mjy REAL,                    -- Reference NVSS flux
    peak_jyb REAL NOT NULL,                -- Measured peak (Jy/beam)
    peak_err_jyb REAL,                     -- Uncertainty
    snr REAL,                              -- S/N ratio
    measured_at REAL NOT NULL,             -- Unix timestamp
    mjd REAL,                              -- MJD of observation (for timeseries)
    sep_from_center_deg REAL,              -- Distance from image center
    flags INTEGER DEFAULT 0,               -- Bit flags for quality issues
    FOREIGN KEY (image_path) REFERENCES images(path)
);

CREATE INDEX IF NOT EXISTS idx_photometry_image ON photometry(image_path);
CREATE INDEX IF NOT EXISTS idx_photometry_source ON photometry(source_id);
CREATE INDEX IF NOT EXISTS idx_photometry_mjd ON photometry(mjd);
CREATE INDEX IF NOT EXISTS idx_photometry_source_mjd ON photometry(source_id, mjd);
```

---

### Table: `variability_stats`

Pre-computed variability statistics per source.

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS variability_stats (
    source_id TEXT PRIMARY KEY,            -- NVSS ID
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    nvss_flux_mjy REAL,
    n_obs INTEGER DEFAULT 0,               -- Number of measurements
    mean_flux_mjy REAL,                    -- Mean measured flux
    std_flux_mjy REAL,                     -- Standard deviation
    min_flux_mjy REAL,
    max_flux_mjy REAL,
    chi2_nu REAL,                          -- Reduced chi-square for constant model
    sigma_deviation REAL,                  -- Max deviation in sigma units
    eta_metric REAL,                       -- Weighted variance metric (η)
    last_measured_at REAL,                 -- Unix timestamp of last measurement
    last_mjd REAL,
    updated_at REAL NOT NULL               -- When stats were computed
);

CREATE INDEX IF NOT EXISTS idx_variability_chi2 ON variability_stats(chi2_nu);
CREATE INDEX IF NOT EXISTS idx_variability_sigma ON variability_stats(sigma_deviation);
CREATE INDEX IF NOT EXISTS idx_variability_eta ON variability_stats(eta_metric);
CREATE INDEX IF NOT EXISTS idx_variability_last_mjd ON variability_stats(last_mjd);
```

---

### Table: `ese_candidates`

Flagged ESE candidates (auto-flagged or user-flagged).

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS ese_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,               -- NVSS ID
    flagged_at REAL NOT NULL,              -- Unix timestamp
    flagged_by TEXT DEFAULT 'auto',        -- 'auto' | user email/ID
    significance REAL NOT NULL,            -- Chi-square or sigma value
    flag_type TEXT NOT NULL,               -- 'variability' | 'rapid_change' | 'user'
    notes TEXT,                            -- User notes
    status TEXT DEFAULT 'active',          -- 'active' | 'investigated' | 'dismissed'
    investigated_at REAL,                  -- When marked as investigated
    dismissed_at REAL,
    FOREIGN KEY (source_id) REFERENCES variability_stats(source_id)
);

CREATE INDEX IF NOT EXISTS idx_ese_source ON ese_candidates(source_id);
CREATE INDEX IF NOT EXISTS idx_ese_status ON ese_candidates(status);
CREATE INDEX IF NOT EXISTS idx_ese_flagged ON ese_candidates(flagged_at);
```

---

### Table: `mosaics`

Metadata for mosaic images.

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS mosaics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,             -- Full path to mosaic FITS
    name TEXT NOT NULL,                    -- Descriptive name
    created_at REAL NOT NULL,              -- Unix timestamp
    start_mjd REAL NOT NULL,               -- Time range covered
    end_mjd REAL NOT NULL,
    integration_sec REAL,                  -- Total integration time
    n_images INTEGER,                      -- Number of input images
    center_ra_deg REAL,
    center_dec_deg REAL,
    dec_min_deg REAL,                      -- Coverage bounds
    dec_max_deg REAL,
    noise_jy REAL,                         -- Mosaic RMS noise
    beam_major_arcsec REAL,
    beam_minor_arcsec REAL,
    beam_pa_deg REAL,
    n_sources INTEGER,                     -- Source count
    thumbnail_path TEXT                    -- Path to PNG preview
);

CREATE INDEX IF NOT EXISTS idx_mosaics_created ON mosaics(created_at);
CREATE INDEX IF NOT EXISTS idx_mosaics_mjd ON mosaics(start_mjd, end_mjd);
```

---

## Calibration Registry

### Table: `caltables`

Tracks calibration tables and their validity ranges.

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS caltables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    set_name TEXT NOT NULL,                -- e.g., 'bp_3c286_60238'
    path TEXT NOT NULL UNIQUE,             -- Full path to caltable
    table_type TEXT NOT NULL,              -- 'K' | 'BP' | 'G'
    order_index INTEGER NOT NULL,          -- Application order (K=0, BP=1, G=2)
    valid_start_mjd REAL NOT NULL,         -- Start of validity window
    valid_end_mjd REAL NOT NULL,           -- End of validity window
    created_at REAL NOT NULL,              -- Unix timestamp
    active INTEGER DEFAULT 1               -- 0/1 boolean
);

CREATE INDEX IF NOT EXISTS idx_caltables_set ON caltables(set_name);
CREATE INDEX IF NOT EXISTS idx_caltables_valid ON caltables(valid_start_mjd, valid_end_mjd);
CREATE INDEX IF NOT EXISTS idx_caltables_active ON caltables(active);
```

---

## Master Sources Catalog

### Table: `sources`

Crossmatched catalog (NVSS + VLASS + FIRST).

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,            -- NVSS ID
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    s_nvss REAL,                           -- NVSS flux (Jy)
    snr_nvss REAL,                         -- NVSS S/N
    s_vlass REAL,                          -- VLASS flux (Jy)
    alpha REAL,                            -- Spectral index (NVSS:arrow_right:VLASS)
    resolved_flag INTEGER DEFAULT 0,       -- From FIRST deconvolved size
    confusion_flag INTEGER DEFAULT 0,      -- Multiple matches within radius
    first_size_maj_arcsec REAL,           -- FIRST major axis
    first_size_min_arcsec REAL,           -- FIRST minor axis
    first_size_pa_deg REAL                 -- FIRST position angle
);

CREATE INDEX IF NOT EXISTS idx_sources_ra_dec ON sources(ra_deg, dec_deg);
CREATE INDEX IF NOT EXISTS idx_sources_flux ON sources(s_nvss);
CREATE INDEX IF NOT EXISTS idx_sources_alpha ON sources(alpha);
```

### Views

**`good_references`** - Basic quality cuts:

```sql
CREATE VIEW IF NOT EXISTS good_references AS
SELECT * FROM sources
WHERE s_nvss IS NOT NULL
  AND snr_nvss >= 7.0
  AND (alpha BETWEEN -1.5 AND 0.5 OR alpha IS NULL)
  AND resolved_flag = 0
  AND confusion_flag = 0;
```

**`final_references`** - Stricter cuts:

```sql
CREATE VIEW IF NOT EXISTS final_references AS
SELECT * FROM good_references
WHERE snr_nvss >= 10.0;
```

---

## Data Models (Pydantic/TypeScript)

### Pipeline Status Models

**Python (Pydantic):**

```python
class QueueStats(BaseModel):
    total: int
    pending: int
    in_progress: int
    completed: int
    failed: int
    collecting: int

class PipelineStatus(BaseModel):
    queue: QueueStats
    calibration_sets: List[CalibrationSet]
    recent_groups: List[RecentGroup]
```

**TypeScript:**

```typescript
export interface QueueStats {
  total: number;
  pending: number;
  in_progress: number;
  completed: number;
  failed: number;
  collecting: number;
}

export interface PipelineStatus {
  queue: QueueStats;
  calibration_sets: CalibrationSet[];
  recent_groups: RecentGroup[];
}
```

---

### ESE Candidate Models

**Python:**

```python
class ESECandidate(BaseModel):
    id: int
    source_id: str
    ra_deg: float
    dec_deg: float
    first_detection_at: datetime
    last_detection_at: datetime
    max_sigma_dev: float
    baseline_flux_jy: float
    peak_flux_jy: float
    status: str  # 'active' | 'resolved' | 'false_positive'
    notes: Optional[str]
```

**TypeScript:**

```typescript
export interface ESECandidate {
  id: number;
  source_id: string;
  ra_deg: number;
  dec_deg: number;
  first_detection_at: string;
  last_detection_at: string;
  max_sigma_dev: number;
  baseline_flux_jy: number;
  peak_flux_jy: number;
  status: "active" | "resolved" | "false_positive";
  notes?: string;
}
```

---

### Source Models

**Python:**

```python
class SourceVariabilityStats(BaseModel):
    source_id: str
    ra_deg: float
    dec_deg: float
    nvss_flux_mjy: float
    n_obs: int
    mean_flux_mjy: float
    std_flux_mjy: float
    chi2_nu: float
    sigma_deviation: float
    last_measured_at: datetime
```

**TypeScript:**

```typescript
export interface SourceVariabilityStats {
  source_id: string;
  ra_deg: number;
  dec_deg: number;
  nvss_flux_mjy: number;
  n_obs: number;
  mean_flux_mjy: number;
  std_flux_mjy: number;
  chi2_nu: number;
  sigma_deviation: number;
  last_measured_at: string;
}
```

---

## Query Patterns

### Get ESE Candidates with Source Details

```sql
SELECT
    e.source_id,
    v.ra_deg,
    v.dec_deg,
    v.mean_flux_mjy,
    v.nvss_flux_mjy,
    v.chi2_nu,
    v.sigma_deviation,
    v.n_obs,
    e.flagged_at,
    e.significance,
    e.status
FROM ese_candidates e
JOIN variability_stats v ON e.source_id = v.source_id
WHERE e.status = 'active'
ORDER BY e.significance DESC
LIMIT 50;
```

### Get Flux Timeseries for Source

```sql
SELECT
    mjd,
    peak_jyb * 1000 as flux_mjy,
    peak_err_jyb * 1000 as error_mjy,
    snr,
    i.field_name,
    i.noise_jy * 1000 as image_noise_mjy
FROM photometry p
JOIN images i ON p.image_path = i.path
WHERE p.source_id = 'NVSS J123456.7+420312'
ORDER BY mjd ASC;
```

### Get Recent Mosaics

```sql
SELECT
    name,
    path,
    start_mjd,
    end_mjd,
    integration_sec / 3600.0 as hours,
    n_images,
    n_sources,
    noise_jy * 1000 as noise_mjy,
    thumbnail_path
FROM mosaics
ORDER BY created_at DESC
LIMIT 20;
```

---

## Migration & Schema Evolution

### Migration Script Pattern

```python
def migrate_products_db(db_path: Path):
    """Add new tables to products.sqlite3."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Add new table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS new_table (
            id INTEGER PRIMARY KEY,
            ...
        )
    """)

    # Create indices
    cur.execute("CREATE INDEX IF NOT EXISTS idx_new_table_field ON new_table(field)")

    conn.commit()
    conn.close()
```

### Schema Versioning

- Track schema version in database metadata table
- Migration scripts check current version before applying
- Rollback scripts for failed migrations

---

## See Also

- [Database Schema Reference](../../reference/database_schema.md) - Complete
  schema documentation
- [Backend API & Integration](../../reference/dashboard_backend_api.md) - API
  endpoints using these models
- [Frontend Architecture](./dashboard_frontend_architecture.md) - Frontend
  TypeScript types
