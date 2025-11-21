# Database Reference: calibrators.sqlite3

**Location**: `/data/dsa110-contimg/state/calibrators.sqlite3`  
**Purpose**: Calibrator source catalog and flux information  
**Size**: ~104 KB (typical)

---

## Overview

The `calibrators.sqlite3` database stores calibrator source information
including positions, flux densities, and sky model metadata. It enables fast
calibrator selection based on declination range and observing schedule.

---

## Tables

### 1. `bandpass_calibrators` - Bandpass Calibrator Registry

**Purpose**: Track calibrators suitable for bandpass calibration

**Schema**:

```sql
CREATE TABLE bandpass_calibrators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calibrator_name TEXT NOT NULL,       -- Calibrator name (e.g., '0834+555')
    ra_deg REAL NOT NULL,                -- RA (degrees)
    dec_deg REAL NOT NULL,               -- Dec (degrees)
    dec_range_min REAL,                  -- Min Dec for validity (degrees)
    dec_range_max REAL,                  -- Max Dec for validity (degrees)
    source_catalog TEXT,                 -- Source catalog (VLA, NVSS, etc.)
    flux_jy REAL,                        -- Flux density (Jy)
    registered_at REAL NOT NULL,         -- Registration timestamp
    registered_by TEXT,                  -- Who registered it
    status TEXT DEFAULT 'active',        -- Status (active/retired)
    notes TEXT,                          -- Free-form notes
    UNIQUE(calibrator_name)
);

CREATE INDEX idx_bp_dec_range ON bandpass_calibrators(dec_range_min, dec_range_max);
CREATE INDEX idx_bp_status ON bandpass_calibrators(status);
CREATE INDEX idx_bp_name ON bandpass_calibrators(calibrator_name);
```

---

### 2. `gain_calibrators` - Gain Calibrator Registry

**Purpose**: Track calibrators suitable for gain calibration

**Schema**: Similar to `bandpass_calibrators`

---

### 3. `vla_calibrators` - VLA Calibrator Catalog

**Purpose**: Full VLA calibrator database import

**Schema**:

```sql
CREATE TABLE vla_calibrators (
    name TEXT PRIMARY KEY,               -- Calibrator name
    ra_deg REAL NOT NULL,                -- RA (degrees)
    dec_deg REAL NOT NULL,               -- Dec (degrees)
    flux_jy REAL,                        -- Flux density (Jy)
    spectral_index REAL,                 -- Spectral index
    catalog_version TEXT,                -- Catalog version
    notes TEXT                           -- Additional information
);
```

---

### 4. `catalog_sources` - General Catalog Sources

**Purpose**: Additional catalog sources (NVSS, FIRST, etc.)

---

### 5. `vla_flux_info` - VLA Flux Measurements

**Purpose**: Detailed flux information for VLA calibrators

---

### 6. `skymodel_metadata` - Sky Model Files

**Purpose**: Track sky model files for calibrators

**Schema**:

```sql
CREATE TABLE skymodel_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calibrator_name TEXT NOT NULL,
    model_path TEXT NOT NULL UNIQUE,
    format TEXT,                         -- 'tigger', 'casa', 'wsclean'
    created_at REAL,
    valid_freq_mhz REAL,
    n_components INTEGER,
    notes TEXT
);
```

---

## Common Queries

### Find Calibrators by Declination

```sql
-- Calibrators for specific Dec range
SELECT calibrator_name, ra_deg, dec_deg, flux_jy
FROM bandpass_calibrators
WHERE status='active'
  AND dec_range_min <= 45.0
  AND dec_range_max >= 45.0;

-- Nearest calibrator to target Dec
SELECT calibrator_name, dec_deg,
       ABS(dec_deg - 45.67) as dec_diff
FROM bandpass_calibrators
WHERE status='active'
ORDER BY dec_diff
LIMIT 1;
```

### Calibrator Lookup by Name

```sql
-- Get calibrator details
SELECT * FROM bandpass_calibrators
WHERE calibrator_name='0834+555';

-- Check if calibrator exists in VLA catalog
SELECT name, ra_deg, dec_deg, flux_jy
FROM vla_calibrators
WHERE name='0834+555';
```

### List All Active Calibrators

```sql
-- All bandpass calibrators
SELECT calibrator_name, ra_deg, dec_deg, flux_jy
FROM bandpass_calibrators
WHERE status='active'
ORDER BY dec_deg;

-- By flux (brightest first)
SELECT calibrator_name, dec_deg, flux_jy
FROM bandpass_calibrators
WHERE status='active'
ORDER BY flux_jy DESC;
```

### Sky Position Queries

```sql
-- Calibrators near RA/Dec position
SELECT calibrator_name, ra_deg, dec_deg,
       SQRT(POW(ra_deg - 123.45, 2) + POW(dec_deg - 45.67, 2)) as dist_deg
FROM bandpass_calibrators
WHERE status='active'
ORDER BY dist_deg
LIMIT 5;
```

### Flux Information

```sql
-- High flux calibrators (>10 Jy)
SELECT calibrator_name, flux_jy, dec_deg
FROM bandpass_calibrators
WHERE flux_jy > 10.0
  AND status='active';

-- Calibrators with unknown flux
SELECT calibrator_name, ra_deg, dec_deg
FROM bandpass_calibrators
WHERE flux_jy IS NULL
  AND status='active';
```

---

## Python Access Examples

### Using Calibrators Module

```python
from pathlib import Path
from dsa110_contimg.database.calibrators import (
    ensure_calibrators_db,
    find_calibrator_by_dec,
    register_bandpass_calibrator
)

# Open database
conn = ensure_calibrators_db(Path("state/calibrators.sqlite3"))

# Find calibrator for declination
calibrator = find_calibrator_by_dec(conn, dec_deg=45.67)
print(f"Calibrator: {calibrator['name']}")
print(f"Position: RA={calibrator['ra_deg']}, Dec={calibrator['dec_deg']}")

# Register new calibrator
register_bandpass_calibrator(
    conn,
    calibrator_name="J1234+5678",
    ra_deg=123.45,
    dec_deg=56.78,
    dec_range_min=55.0,
    dec_range_max=58.0,
    flux_jy=15.0,
    source_catalog="VLA"
)

conn.close()
```

### Direct SQL Access

```python
import sqlite3

conn = sqlite3.connect("state/calibrators.sqlite3")
conn.row_factory = sqlite3.Row

# Find calibrators in Dec range
cursor = conn.cursor()
cursor.execute("""
    SELECT calibrator_name, ra_deg, dec_deg, flux_jy
    FROM bandpass_calibrators
    WHERE status='active'
      AND dec_range_min <= ?
      AND dec_range_max >= ?
    ORDER BY flux_jy DESC
""", (target_dec, target_dec))

for row in cursor.fetchall():
    print(f"{row['calibrator_name']}: {row['flux_jy']} Jy")

conn.close()
```

### Query VLA Catalog

```python
# Search VLA calibrator catalog
cursor.execute("""
    SELECT name, ra_deg, dec_deg, flux_jy
    FROM vla_calibrators
    WHERE ABS(dec_deg - ?) < 5.0
    ORDER BY flux_jy DESC
    LIMIT 10
""", (target_dec,))

calibrators = cursor.fetchall()
```

---

## Calibrator Selection Workflow

### 1. Declination-Based Selection

```python
from dsa110_contimg.calibration.catalogs import select_calibrator

# Get current pointing Dec
pointing_dec = get_current_pointing_dec()

# Find suitable calibrator
calibrator = select_calibrator(
    conn,
    dec_deg=pointing_dec,
    min_flux_jy=5.0  # Require >5 Jy
)
```

### 2. Transit-Based Selection

```python
from dsa110_contimg.pointing.crossmatch import find_transiting_calibrators

# Find calibrators transiting soon
calibrators = find_transiting_calibrators(
    conn,
    time_window_hours=2.0,
    min_elevation_deg=30.0
)
```

### 3. Schedule Integration

```python
# Check calibrator visibility
from dsa110_contimg.calibration.schedule import is_calibrator_visible

is_visible = is_calibrator_visible(
    calibrator_name="0834+555",
    obs_time_mjd=59000.5,
    min_elevation=30.0
)
```

---

## Maintenance Queries

### Add New Calibrator

```sql
INSERT INTO bandpass_calibrators (
    calibrator_name, ra_deg, dec_deg,
    dec_range_min, dec_range_max,
    flux_jy, registered_at, status
) VALUES (
    'J1234+5678', 123.45, 56.78,
    55.0, 58.0,
    15.0, strftime('%s','now'), 'active'
);
```

### Update Calibrator Information

```sql
-- Update flux measurement
UPDATE bandpass_calibrators
SET flux_jy=12.5,
    notes='Updated from latest VLA obs'
WHERE calibrator_name='0834+555';

-- Retire calibrator
UPDATE bandpass_calibrators
SET status='retired',
    notes='Source became variable'
WHERE calibrator_name='J1234+5678';
```

### Import VLA Catalog

```sql
-- Bulk import from CSV
.mode csv
.import vla_calibrators.csv vla_calibrators
```

### Database Statistics

```sql
-- Count calibrators by status
SELECT status, COUNT(*)
FROM bandpass_calibrators
GROUP BY status;

-- Dec coverage
SELECT
    MIN(dec_deg) as min_dec,
    MAX(dec_deg) as max_dec,
    COUNT(*) as n_calibrators
FROM bandpass_calibrators
WHERE status='active';

-- Flux distribution
SELECT
    COUNT(CASE WHEN flux_jy < 5 THEN 1 END) as weak,
    COUNT(CASE WHEN flux_jy BETWEEN 5 AND 10 THEN 1 END) as medium,
    COUNT(CASE WHEN flux_jy > 10 THEN 1 END) as strong
FROM bandpass_calibrators
WHERE flux_jy IS NOT NULL;
```

---

## CLI Commands

### List Calibrators

```bash
# All active bandpass calibrators
python -m dsa110_contimg.calibration.catalog_cli list \
  --type bandpass \
  --status active

# Find by Dec
python -m dsa110_contimg.calibration.catalog_cli find \
  --dec 45.67 \
  --min-flux 5.0
```

### Register Calibrator

```bash
python -m dsa110_contimg.calibration.catalog_cli register \
  --name J1234+5678 \
  --ra 123.45 \
  --dec 56.78 \
  --flux 15.0 \
  --dec-range 55.0 58.0
```

### Import Catalog

```bash
# Import VLA calibrator catalog
python -m dsa110_contimg.catalog.build_master build-vla \
  --output state/calibrators.sqlite3
```

---

## Sky Model Integration

### Link Calibrator to Sky Model

```sql
INSERT INTO skymodel_metadata (
    calibrator_name, model_path, format,
    created_at, valid_freq_mhz, n_components
) VALUES (
    '0834+555',
    '/state/skymodels/0834+555.skymodel',
    'tigger',
    strftime('%s','now'),
    1400.0,
    1
);
```

### Query Sky Models

```sql
-- Get sky model for calibrator
SELECT model_path, format
FROM skymodel_metadata
WHERE calibrator_name='0834+555';
```

---

## Performance Notes

- **Indexes**: Optimized for Dec-range and name lookups
- **Typical Size**: <500 KB with full VLA catalog
- **Query Speed**: <5ms for calibrator selection
- **No WAL needed**: Mostly read-only operations

---

## Related Files

- **Code**: `dsa110_contimg/database/calibrators.py`
- **Catalogs**: `dsa110_contimg/calibration/catalogs.py`
- **Catalog Building**: `dsa110_contimg/catalog/builders.py`

---

## See Also

- **Cal Registry**: `docs/reference/database_cal_registry_sqlite3.md`
- **Calibration Guide**: `dsa110_contimg/calibration/README.md`
- **Catalog README**: `dsa110_contimg/catalog/README.md`
