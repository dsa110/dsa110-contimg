# DSA-110 Continuum Pipeline: Database Schema

## Overview

The pipeline uses SQLite databases for state management and product tracking. This document details the schema for all databases with a focus on frontend requirements.

---

## Database Files

| Database | Location | Purpose |
|----------|----------|---------|
| `ingest.sqlite3` | `/data/dsa110-contimg/state/` | Queue management, subband tracking |
| `cal_registry.sqlite3` | `/data/dsa110-contimg/state/` | Calibration table registry |
| `products.sqlite3` | `/data/dsa110-contimg/state/` | Images, photometry, MS index |
| `master_sources.sqlite3` | `/data/dsa110-contimg/state/catalogs/` | NVSS/VLASS/FIRST crossmatch |

---

## 1. Ingest Queue Database (`ingest.sqlite3`)

### Table: `ingest_queue`
Tracks observation groups through the pipeline.

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

### Table: `subband_files`
Tracks individual subband files per group.

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

### Table: `performance_metrics`
Processing performance per group.

```sql
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id TEXT NOT NULL UNIQUE,
    writer_type TEXT,                      -- 'direct-subband' | 'pyuvdata' | 'auto'
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

## 2. Calibration Registry (`cal_registry.sqlite3`)

### Table: `caltables`
Tracks calibration tables and their validity ranges.

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

## 3. Products Database (`products.sqlite3`)

### Table: `ms_index`
Tracks Measurement Sets through processing stages.

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

### Table: `images`
Catalog of image products.

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

### Table: `photometry`
Forced photometry measurements on sources.

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

### Table: `variability_stats`
Pre-computed variability statistics per source (updated periodically).

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
    last_measured_at REAL,                 -- Unix timestamp of last measurement
    last_mjd REAL,
    updated_at REAL NOT NULL               -- When stats were computed
);

CREATE INDEX IF NOT EXISTS idx_variability_chi2 ON variability_stats(chi2_nu);
CREATE INDEX IF NOT EXISTS idx_variability_sigma ON variability_stats(sigma_deviation);
CREATE INDEX IF NOT EXISTS idx_variability_last_mjd ON variability_stats(last_mjd);
```

### Table: `ese_candidates`
Flagged ESE candidates (auto-flagged or user-flagged).

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

### Table: `mosaics`
Metadata for mosaic images (pre-generated, not user-initiated).

```sql
CREATE TABLE IF NOT EXISTS mosaics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,             -- Full path to mosaic FITS
    name TEXT NOT NULL,                    -- Descriptive name (e.g., '2025-10-24_hourly_12-13UTC')
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

### Table: `qa_artifacts`
Quality assurance plots and diagnostics.

```sql
CREATE TABLE IF NOT EXISTS qa_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id TEXT NOT NULL,                -- Observation group
    name TEXT NOT NULL,                    -- Filename (e.g., 'amplitude_vs_time.png')
    path TEXT NOT NULL,                    -- Full path
    type TEXT,                             -- 'plot' | 'table' | 'report'
    category TEXT,                         -- 'calibration' | 'imaging' | 'system'
    created_at REAL NOT NULL,
    UNIQUE(group_id, name)
);

CREATE INDEX IF NOT EXISTS idx_qa_group ON qa_artifacts(group_id);
CREATE INDEX IF NOT EXISTS idx_qa_created ON qa_artifacts(created_at);
```

### Table: `pointing_history`
Telescope pointing history for sky coverage visualization.

```sql
CREATE TABLE IF NOT EXISTS pointing_history (
    timestamp REAL PRIMARY KEY,            -- Unix timestamp
    mjd REAL,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    alt_deg REAL,                          -- Elevation
    az_deg REAL,                           -- Azimuth
    lst_hours REAL,                        -- Local sidereal time
    field_name TEXT                        -- Associated field ID
);

CREATE INDEX IF NOT EXISTS idx_pointing_mjd ON pointing_history(mjd);
CREATE INDEX IF NOT EXISTS idx_pointing_dec ON pointing_history(dec_deg);
```

### Table: `alert_history`
Log of Slack alerts sent.

```sql
CREATE TABLE IF NOT EXISTS alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    alert_type TEXT NOT NULL,              -- 'ese_candidate' | 'calibrator_missing' | 'system_error'
    severity TEXT NOT NULL,                -- 'info' | 'warning' | 'critical'
    message TEXT NOT NULL,
    sent_at REAL NOT NULL,                 -- Unix timestamp
    channel TEXT,                          -- Slack channel (e.g., '#ese-alerts')
    success INTEGER DEFAULT 1,             -- Boolean: delivery success
    error_msg TEXT                         -- Error if delivery failed
);

CREATE INDEX IF NOT EXISTS idx_alert_source ON alert_history(source_id);
CREATE INDEX IF NOT EXISTS idx_alert_sent ON alert_history(sent_at);
CREATE INDEX IF NOT EXISTS idx_alert_type ON alert_history(alert_type);
```

---

## 4. Master Sources Catalog (`master_sources.sqlite3`)

### Table: `sources`
Crossmatched catalog (NVSS + VLASS + FIRST).

```sql
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,            -- NVSS ID
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    s_nvss REAL,                           -- NVSS flux (Jy)
    snr_nvss REAL,                         -- NVSS S/N
    s_vlass REAL,                          -- VLASS flux (Jy)
    alpha REAL,                            -- Spectral index (NVSS→VLASS)
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

### Views: `good_references` and `final_references`
Pre-filtered source lists for forced photometry.

```sql
-- Good references: basic quality cuts
CREATE VIEW IF NOT EXISTS good_references AS
SELECT * FROM sources
WHERE s_nvss IS NOT NULL
  AND snr_nvss >= 7.0
  AND (alpha BETWEEN -1.5 AND 0.5 OR alpha IS NULL)
  AND resolved_flag = 0
  AND confusion_flag = 0;

-- Final references: stricter cuts
CREATE VIEW IF NOT EXISTS final_references AS
SELECT * FROM good_references
WHERE snr_nvss >= 10.0;
```

---

## Schema Migration Scripts

### Add New Tables to Existing Database

**Python helper** (`src/dsa110_contimg/database/migrations.py`):

```python
"""Database schema migrations."""
import sqlite3
from pathlib import Path

def migrate_products_db(db_path: Path):
    """Add frontend tables to products.sqlite3."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Add variability_stats table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS variability_stats (
            source_id TEXT PRIMARY KEY,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            nvss_flux_mjy REAL,
            n_obs INTEGER DEFAULT 0,
            mean_flux_mjy REAL,
            std_flux_mjy REAL,
            min_flux_mjy REAL,
            max_flux_mjy REAL,
            chi2_nu REAL,
            sigma_deviation REAL,
            last_measured_at REAL,
            last_mjd REAL,
            updated_at REAL NOT NULL
        )
    """)
    
    # Add ese_candidates table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ese_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            flagged_at REAL NOT NULL,
            flagged_by TEXT DEFAULT 'auto',
            significance REAL NOT NULL,
            flag_type TEXT NOT NULL,
            notes TEXT,
            status TEXT DEFAULT 'active',
            investigated_at REAL,
            dismissed_at REAL,
            FOREIGN KEY (source_id) REFERENCES variability_stats(source_id)
        )
    """)
    
    # Add mosaics table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mosaics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            created_at REAL NOT NULL,
            start_mjd REAL NOT NULL,
            end_mjd REAL NOT NULL,
            integration_sec REAL,
            n_images INTEGER,
            center_ra_deg REAL,
            center_dec_deg REAL,
            dec_min_deg REAL,
            dec_max_deg REAL,
            noise_jy REAL,
            beam_major_arcsec REAL,
            beam_minor_arcsec REAL,
            beam_pa_deg REAL,
            n_sources INTEGER,
            thumbnail_path TEXT
        )
    """)
    
    # Add alert_history table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alert_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            sent_at REAL NOT NULL,
            channel TEXT,
            success INTEGER DEFAULT 1,
            error_msg TEXT
        )
    """)
    
    # Create indices
    cur.execute("CREATE INDEX IF NOT EXISTS idx_variability_chi2 ON variability_stats(chi2_nu)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_variability_sigma ON variability_stats(sigma_deviation)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ese_source ON ese_candidates(source_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ese_status ON ese_candidates(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_mosaics_mjd ON mosaics(start_mjd, end_mjd)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_alert_sent ON alert_history(sent_at)")
    
    conn.commit()
    conn.close()
    print(f"✓ Migrated {db_path}")

if __name__ == "__main__":
    migrate_products_db(Path("/data/dsa110-contimg/state/products.sqlite3"))
```

---

## Query Examples

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
    peak_jyb * 1000 as flux_mjy,  -- Convert Jy/beam to mJy
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

**Document Version**: 1.0  
**Last Updated**: 2025-10-24  
**Status**: Schema Specification

