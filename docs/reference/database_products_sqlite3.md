# Database Reference: products.sqlite3

**Location**: `/data/dsa110-contimg/state/products.sqlite3`  
**Purpose**: Central database for pipeline data products (MS files, images,
mosaics)  
**Size**: ~800 KB (typical)

---

## Overview

The `products.sqlite3` database is the **main pipeline state database**,
tracking all data products from MS conversion through mosaic creation. It serves
as the source of truth for pipeline progress and data product metadata.

---

## Core Tables

### 1. `ms_index` - Measurement Set Registry

**Purpose**: Track all converted MS files and their processing status

**Schema**:

```sql
CREATE TABLE ms_index (
    path TEXT PRIMARY KEY,           -- Full path to MS file
    start_mjd REAL,                  -- Observation start time (MJD)
    end_mjd REAL,                    -- Observation end time (MJD)
    mid_mjd REAL,                    -- Mid-point time (MJD)
    processed_at REAL,               -- Timestamp when converted
    status TEXT,                     -- Current status
    stage TEXT,                      -- Pipeline stage
    stage_updated_at REAL,           -- Last stage update time
    cal_applied INTEGER DEFAULT 0,   -- Calibration applied flag (0/1)
    imagename TEXT,                  -- Associated image name
    field_name TEXT,                 -- Field name from MS
    pointing_ra_deg REAL,            -- Pointing RA (degrees)
    pointing_dec_deg REAL,           -- Pointing Dec (degrees)
    ra_deg REAL,                     -- Phase center RA (degrees)
    dec_deg REAL                     -- Phase center Dec (degrees)
);
```

**Status Values**:

- `converted` - MS created from HDF5
- `calibrated` - Calibration applied
- `imaged` - Image created
- `published` - Final published state

**Stage Values**:

- `converted` - Initial conversion complete
- `calibrated` - Calibration stage complete
- `imaged` - Imaging complete

**Common Queries**:

```sql
-- Find MS files ready for calibration
SELECT path, mid_mjd
FROM ms_index
WHERE status='converted'
ORDER BY mid_mjd;

-- Count MS files by status
SELECT status, COUNT(*)
FROM ms_index
GROUP BY status;

-- Find MS files in time range
SELECT path, start_mjd, end_mjd
FROM ms_index
WHERE mid_mjd BETWEEN 59000.0 AND 59001.0;

-- Check if MS has calibration applied
SELECT path, cal_applied, stage
FROM ms_index
WHERE path LIKE '%2025-11-18%';

-- Find MS files by pointing (within 1 degree)
SELECT path, pointing_ra_deg, pointing_dec_deg
FROM ms_index
WHERE ABS(pointing_ra_deg - 123.45) < 1.0
  AND ABS(pointing_dec_deg - 45.67) < 1.0;
```

---

### 2. `mosaic_groups` - Mosaic Group Tracking

**Purpose**: Track groups of 10 MS files processed together into mosaics

**Schema**:

```sql
CREATE TABLE mosaic_groups (
    group_id TEXT PRIMARY KEY,           -- Group identifier (timestamp)
    mosaic_id TEXT,                      -- Final mosaic ID
    ms_paths TEXT NOT NULL,              -- JSON list of MS paths
    calibration_ms_path TEXT,            -- MS used for calibration
    bpcal_solved INTEGER DEFAULT 0,      -- Bandpass cal solved flag
    created_at REAL NOT NULL,            -- Group creation time
    calibrated_at REAL,                  -- Calibration completion time
    imaged_at REAL,                      -- Imaging completion time
    mosaicked_at REAL,                   -- Mosaic creation time
    status TEXT DEFAULT 'pending'        -- Current status
);
CREATE INDEX idx_mosaic_groups_status ON mosaic_groups(status);
```

**Status Values**:

- `pending` - Group formed, awaiting processing
- `calibrating` - Calibration in progress
- `calibrated` - Calibration complete
- `imaging` - Imaging in progress
- `imaged` - All images created
- `completed` - Mosaic created
- `failed` - Processing failed

**Common Queries**:

```sql
-- Find pending mosaic groups
SELECT group_id, created_at
FROM mosaic_groups
WHERE status='pending'
ORDER BY created_at;

-- Get mosaic group details
SELECT * FROM mosaic_groups
WHERE group_id='2025-11-18T12:00:00';

-- Count groups by status
SELECT status, COUNT(*)
FROM mosaic_groups
GROUP BY status;

-- Find completed mosaics in last 24 hours
SELECT group_id, mosaic_id, mosaicked_at
FROM mosaic_groups
WHERE status='completed'
  AND mosaicked_at > (strftime('%s','now') - 86400);

-- Get MS paths for a group (parse JSON)
SELECT group_id, ms_paths
FROM mosaic_groups
WHERE group_id='2025-11-18T12:00:00';
```

---

### 3. `images` - Image Product Registry

**Purpose**: Track all individual FITS images created from MS files

**Schema**:

```sql
CREATE TABLE images (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL,                  -- Full path to image
    ms_path TEXT NOT NULL,               -- Source MS file
    created_at REAL NOT NULL,            -- Creation timestamp
    type TEXT NOT NULL,                  -- Image type (e.g., 'fits', 'casa')
    beam_major_arcsec REAL,              -- Beam major axis (arcsec)
    noise_jy REAL,                       -- RMS noise (Jy)
    pbcor INTEGER DEFAULT 0,             -- Primary beam corrected flag
    format TEXT DEFAULT "fits",          -- Image format
    beam_minor_arcsec REAL,              -- Beam minor axis (arcsec)
    beam_pa_deg REAL,                    -- Beam position angle (deg)
    dynamic_range REAL,                  -- Peak/RMS ratio
    field_name TEXT,                     -- Field name
    center_ra_deg REAL,                  -- Center RA (degrees)
    center_dec_deg REAL,                 -- Center Dec (degrees)
    imsize_x INTEGER,                    -- Image size X (pixels)
    imsize_y INTEGER,                    -- Image size Y (pixels)
    cellsize_arcsec REAL,                -- Pixel size (arcsec)
    freq_ghz REAL,                       -- Frequency (GHz)
    bandwidth_mhz REAL,                  -- Bandwidth (MHz)
    integration_sec REAL                 -- Integration time (sec)
);
```

**Common Queries**:

```sql
-- Find images from specific MS
SELECT path, created_at, type
FROM images
WHERE ms_path LIKE '%2025-11-18T12:00:00%';

-- Get image metadata
SELECT path, beam_major_arcsec, beam_minor_arcsec, noise_jy
FROM images
WHERE id=123;

-- Find images with high dynamic range
SELECT path, dynamic_range, noise_jy
FROM images
WHERE dynamic_range > 100
ORDER BY dynamic_range DESC;

-- Count images by type
SELECT type, COUNT(*)
FROM images
GROUP BY type;

-- Find images by sky position (within 1 degree)
SELECT path, center_ra_deg, center_dec_deg
FROM images
WHERE ABS(center_ra_deg - 123.45) < 1.0
  AND ABS(center_dec_deg - 45.67) < 1.0;
```

---

### 4. `mosaics` - Mosaic Product Registry

**Purpose**: Track all created mosaics and their metadata

**Schema**:

```sql
CREATE TABLE mosaics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,           -- Full path to mosaic
    name TEXT NOT NULL,                  -- Mosaic name/ID
    created_at REAL NOT NULL,            -- Creation timestamp
    start_mjd REAL NOT NULL,             -- Start time of data (MJD)
    end_mjd REAL NOT NULL,               -- End time of data (MJD)
    integration_sec REAL,                -- Total integration (sec)
    n_images INTEGER,                    -- Number of input images
    center_ra_deg REAL,                  -- Center RA (degrees)
    center_dec_deg REAL,                 -- Center Dec (degrees)
    dec_min_deg REAL,                    -- Minimum Dec covered
    dec_max_deg REAL,                    -- Maximum Dec covered
    noise_jy REAL,                       -- RMS noise (Jy)
    beam_major_arcsec REAL,              -- Beam major axis (arcsec)
    beam_minor_arcsec REAL,              -- Beam minor axis (arcsec)
    beam_pa_deg REAL,                    -- Beam position angle (deg)
    n_sources INTEGER,                   -- Number of sources detected
    thumbnail_path TEXT,                 -- Path to thumbnail image
    status TEXT,                         -- Processing status
    method TEXT,                         -- Combination method
    tiles TEXT,                          -- JSON list of tiles used
    output_path TEXT,                    -- Output path
    validation_issues TEXT,              -- JSON validation results
    metrics_path TEXT                    -- Path to QA metrics
);
CREATE INDEX idx_mosaics_name ON mosaics(name);
```

**Common Queries**:

```sql
-- List recent mosaics
SELECT name, created_at, n_images, noise_jy
FROM mosaics
ORDER BY created_at DESC
LIMIT 10;

-- Find mosaics by name pattern
SELECT * FROM mosaics
WHERE name LIKE 'mosaic_2025-11-18%';

-- Get mosaic metadata
SELECT name, center_ra_deg, center_dec_deg, n_sources
FROM mosaics
WHERE id=456;

-- Find mosaics in time range
SELECT name, start_mjd, end_mjd, integration_sec
FROM mosaics
WHERE start_mjd >= 59000.0 AND end_mjd <= 59001.0;

-- Mosaics with validation issues
SELECT name, validation_issues
FROM mosaics
WHERE validation_issues IS NOT NULL;
```

---

### 5. `photometry` - Source Photometry Measurements

**Purpose**: Store forced photometry measurements from images

**Schema**:

```sql
CREATE TABLE photometry (
    id INTEGER PRIMARY KEY,
    image_path TEXT NOT NULL,            -- Source image
    ra_deg REAL NOT NULL,                -- Source RA (degrees)
    dec_deg REAL NOT NULL,               -- Source Dec (degrees)
    nvss_flux_mjy REAL,                  -- NVSS catalog flux (mJy)
    peak_jyb REAL NOT NULL,              -- Peak flux density (Jy/beam)
    peak_err_jyb REAL,                   -- Peak flux error (Jy/beam)
    measured_at REAL NOT NULL,           -- Measurement timestamp
    source_id TEXT,                      -- Source identifier
    snr REAL,                            -- Signal-to-noise ratio
    mjd REAL,                            -- Observation time (MJD)
    sep_from_center_deg REAL,            -- Distance from center (deg)
    flags INTEGER DEFAULT 0              -- Quality flags
);
CREATE INDEX idx_photometry_image ON photometry(image_path);
CREATE INDEX idx_photometry_source_mjd ON photometry(source_id, mjd);
```

**Common Queries**:

```sql
-- Get photometry for an image
SELECT ra_deg, dec_deg, peak_jyb, snr
FROM photometry
WHERE image_path='/stage/images/2025-11-18T12:00:00.fits';

-- Find measurements of a specific source
SELECT mjd, peak_jyb, snr
FROM photometry
WHERE source_id='J123456+789012'
ORDER BY mjd;

-- High SNR detections
SELECT image_path, ra_deg, dec_deg, peak_jyb, snr
FROM photometry
WHERE snr > 10
ORDER BY snr DESC;

-- Sources with NVSS counterparts
SELECT ra_deg, dec_deg, nvss_flux_mjy, peak_jyb
FROM photometry
WHERE nvss_flux_mjy IS NOT NULL;
```

---

## Supporting Tables

### 6. `calibrator_transits` - Calibrator Transit Times

**Purpose**: Pre-calculated transit times for fast querying

```sql
-- List transits for a calibrator
SELECT transit_mjd, has_data
FROM calibrator_transits
WHERE calibrator_name='0834+555'
  AND has_data=1
ORDER BY transit_mjd;

-- Find transits in time range
SELECT calibrator_name, transit_mjd
FROM calibrator_transits
WHERE transit_mjd BETWEEN 59000.0 AND 59001.0;
```

### 7. `data_registry` - Data Product Publishing

**Purpose**: Track data product publishing status (duplicated from
data_registry.sqlite3)

```sql
-- Find staging mosaics ready to publish
SELECT data_id, stage_path, qa_status
FROM data_registry
WHERE data_type='mosaic'
  AND status='staging'
  AND qa_status='passed';

-- Check publish status
SELECT data_id, status, published_at
FROM data_registry
WHERE data_id='mosaic_2025-11-18_12-00-00';
```

### 8. `jobs` - Batch Job Tracking

**Purpose**: Track batch processing jobs

```sql
-- List pending jobs
SELECT id, job_type, created_at
FROM jobs
WHERE status='pending';

-- Get job details
SELECT * FROM jobs WHERE id=123;
```

### 9. `calibration_qa` / `image_qa` - QA Results

**Purpose**: Store quality assessment metrics

```sql
-- Get QA results for MS
SELECT * FROM calibration_qa
WHERE ms_path='/stage/ms/2025-11-18T12:00:00.ms';

-- Failed QA checks
SELECT image_path, qa_status, issues
FROM image_qa
WHERE qa_status='failed';
```

---

## Common Workflow Queries

### Find MS Files Ready for Mosaic Creation

```sql
-- Get 10 oldest converted MS files
SELECT path, mid_mjd
FROM ms_index
WHERE status='converted'
ORDER BY mid_mjd
LIMIT 10;
```

### Check Mosaic Group Progress

```sql
-- Get complete group status
SELECT
    mg.group_id,
    mg.status,
    mg.created_at,
    mg.calibrated_at,
    mg.imaged_at,
    mg.mosaicked_at,
    mg.mosaic_id
FROM mosaic_groups mg
WHERE mg.group_id='2025-11-18T12:00:00';
```

### Find All Products for a Time Window

```sql
-- MS files
SELECT 'MS' as type, path, mid_mjd
FROM ms_index
WHERE mid_mjd BETWEEN 59000.0 AND 59001.0

UNION ALL

-- Mosaics
SELECT 'Mosaic' as type, path, (start_mjd + end_mjd)/2 as mid_mjd
FROM mosaics
WHERE start_mjd <= 59001.0 AND end_mjd >= 59000.0

ORDER BY mid_mjd;
```

### Get Full Mosaic Pipeline Status

```sql
SELECT
    COUNT(CASE WHEN status='converted' THEN 1 END) as ms_converted,
    COUNT(CASE WHEN status='calibrated' THEN 1 END) as ms_calibrated,
    COUNT(CASE WHEN status='imaged' THEN 1 END) as ms_imaged
FROM ms_index

UNION ALL

SELECT
    COUNT(CASE WHEN status='pending' THEN 1 END) as groups_pending,
    COUNT(CASE WHEN status='calibrated' THEN 1 END) as groups_calibrated,
    COUNT(CASE WHEN status='completed' THEN 1 END) as groups_completed
FROM mosaic_groups;
```

---

## Maintenance Queries

### Clean Up Old Entries

```sql
-- Archive old MS entries (older than 30 days)
DELETE FROM ms_index
WHERE processed_at < (strftime('%s','now') - 30*86400);

-- Remove orphaned images (MS no longer exists)
DELETE FROM images
WHERE ms_path NOT IN (SELECT path FROM ms_index);
```

### Database Statistics

```sql
-- Table sizes
SELECT
    'ms_index' as table_name, COUNT(*) as row_count
FROM ms_index
UNION ALL
SELECT 'mosaic_groups', COUNT(*) FROM mosaic_groups
UNION ALL
SELECT 'images', COUNT(*) FROM images
UNION ALL
SELECT 'mosaics', COUNT(*) FROM mosaics
UNION ALL
SELECT 'photometry', COUNT(*) FROM photometry;

-- Disk usage by status
SELECT status, COUNT(*),
       GROUP_CONCAT(path, CHAR(10)) as paths
FROM ms_index
GROUP BY status;
```

---

## Python Access Examples

### Using `ensure_products_db()`

```python
from pathlib import Path
from dsa110_contimg.database.products import ensure_products_db

# Open database
conn = ensure_products_db(Path("state/products.sqlite3"))

# Query MS index
cursor = conn.cursor()
cursor.execute("SELECT path, status FROM ms_index WHERE status='converted'")
ms_files = cursor.fetchall()

# Close connection
conn.close()
```

### Using Helper Functions

```python
from dsa110_contimg.database.products import (
    ms_index_upsert,
    image_insert,
    discover_ms_files
)

# Update MS status
ms_index_upsert(
    conn,
    path="/stage/ms/2025-11-18T12:00:00.ms",
    start_mjd=59000.5,
    end_mjd=59000.6,
    status="calibrated",
    stage="calibrated"
)

# Insert image record
image_insert(
    conn,
    path="/stage/images/2025-11-18T12:00:00.fits",
    ms_path="/stage/ms/2025-11-18T12:00:00.ms",
    type="fits",
    beam_major_arcsec=15.0,
    noise_jy=0.001
)

# Discover MS files in directory
ms_files = discover_ms_files(
    db_path=Path("state/products.sqlite3"),
    scan_dir="/stage/dsa110-contimg/ms",
    recursive=True
)
```

---

## Performance Notes

- **WAL Mode**: Enabled for concurrent read/write access
- **Indexes**: Key fields indexed for fast queries (status, time ranges, paths)
- **Transaction Safety**: Use transactions for multi-step operations
- **Vacuum**: Run `VACUUM` periodically to reclaim space after deletions

---

## Related Databases

- **`hdf5.sqlite3`** - HDF5 input file tracking (before conversion)
- **`ingest.sqlite3`** - Ingestion queue management
- **`data_registry.sqlite3`** - Data publishing & QA tracking (separate
  instance)
- **`cal_registry.sqlite3`** - Calibration table validity tracking

---

## See Also

- **Code**: `dsa110_contimg/database/products.py`
- **Schema Evolution**: `dsa110_contimg/database/schema_evolution.py`
- **Documentation**: `docs/reference/database_*.md`
