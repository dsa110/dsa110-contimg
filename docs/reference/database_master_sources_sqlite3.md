# Database Reference: master_sources.sqlite3

**Location**: `/data/dsa110-contimg/state/master_sources.sqlite3`  
**Purpose**: Master catalog of cross-matched radio sources  
**Size**: ~108 MB (typical, large catalog)

---

## Overview

The `master_sources.sqlite3` database contains a master catalog of radio sources
cross-matched from multiple surveys (NVSS, VLASS, etc.). It provides fast
lookups for source identification, flux measurements, and variability tracking.

---

## Tables

### 1. `sources` - Master Source Catalog

**Purpose**: Unified catalog of radio sources with multi-survey cross-matching

**Schema**:

```sql
CREATE TABLE sources (
    source_id INTEGER PRIMARY KEY,       -- Unique source identifier
    ra_deg REAL NOT NULL,                -- RA (degrees, J2000)
    dec_deg REAL NOT NULL,               -- Dec (degrees, J2000)
    s_nvss REAL,                         -- NVSS flux density (Jy)
    snr_nvss REAL,                       -- NVSS SNR
    s_vlass REAL,                        -- VLASS flux density (Jy)
    alpha REAL,                          -- Spectral index
    resolved_flag INTEGER NOT NULL,      -- Source resolved flag (0/1)
    confusion_flag INTEGER NOT NULL      -- Confusion flag (0/1)
);

CREATE INDEX idx_sources_radec ON sources(ra_deg, dec_deg);
```

---

### 2. `final_references` / `final_references_table` - Reference Catalog

**Purpose**: High-quality reference sources for astrometry and flux calibration

---

### 3. `good_references` - Good Quality Sources

**Purpose**: Subset of sources passing quality criteria

---

### 4. `meta` - Catalog Metadata

**Purpose**: Store catalog version, build date, and provenance information

---

## Source Flags

### Resolved Flag

- `0` - Point source (unresolved)
- `1` - Extended/resolved source

### Confusion Flag

- `0` - Isolated source (no confusion)
- `1` - Source in confused region (multiple nearby sources)

---

## Common Queries

### Find Sources by Position

```sql
-- Sources within 1 arcmin of position
SELECT source_id, ra_deg, dec_deg, s_nvss, s_vlass
FROM sources
WHERE ABS(ra_deg - 123.45) < 0.0167
  AND ABS(dec_deg - 45.67) < 0.0167;

-- Nearest source to position
SELECT source_id, ra_deg, dec_deg, s_nvss,
       SQRT(POW((ra_deg - 123.45) * COS(RADIANS(45.67)), 2) +
            POW(dec_deg - 45.67, 2)) * 3600 as sep_arcsec
FROM sources
ORDER BY sep_arcsec
LIMIT 1;

-- Sources in RA/Dec box
SELECT source_id, ra_deg, dec_deg, s_nvss
FROM sources
WHERE ra_deg BETWEEN 120.0 AND 125.0
  AND dec_deg BETWEEN 44.0 AND 46.0;
```

### Flux-Based Queries

```sql
-- Bright sources (NVSS > 100 mJy)
SELECT source_id, ra_deg, dec_deg, s_nvss
FROM sources
WHERE s_nvss > 0.1
ORDER BY s_nvss DESC;

-- Sources with NVSS and VLASS measurements
SELECT source_id, ra_deg, dec_deg, s_nvss, s_vlass,
       s_vlass / s_nvss as flux_ratio
FROM sources
WHERE s_nvss IS NOT NULL
  AND s_vlass IS NOT NULL;

-- Variable source candidates (flux ratio > 2 or < 0.5)
SELECT source_id, ra_deg, dec_deg, s_nvss, s_vlass,
       s_vlass / s_nvss as flux_ratio
FROM sources
WHERE s_nvss IS NOT NULL
  AND s_vlass IS NOT NULL
  AND (s_vlass / s_nvss > 2.0 OR s_vlass / s_nvss < 0.5);
```

### Spectral Index Queries

```sql
-- Flat-spectrum sources (|alpha| < 0.5)
SELECT source_id, ra_deg, dec_deg, s_nvss, alpha
FROM sources
WHERE alpha IS NOT NULL
  AND ABS(alpha) < 0.5;

-- Steep-spectrum sources (alpha < -0.7)
SELECT source_id, ra_deg, dec_deg, s_nvss, alpha
FROM sources
WHERE alpha IS NOT NULL
  AND alpha < -0.7;
```

### Quality Filtering

```sql
-- Point sources only (unresolved)
SELECT source_id, ra_deg, dec_deg, s_nvss
FROM sources
WHERE resolved_flag=0;

-- Isolated sources (no confusion)
SELECT source_id, ra_deg, dec_deg, s_nvss
FROM sources
WHERE confusion_flag=0;

-- High-quality sources (point + isolated + bright)
SELECT source_id, ra_deg, dec_deg, s_nvss, snr_nvss
FROM sources
WHERE resolved_flag=0
  AND confusion_flag=0
  AND s_nvss > 0.01
  AND snr_nvss > 10;
```

---

## Python Access Examples

### Cone Search

```python
import sqlite3
import numpy as np

def cone_search(conn, ra_deg, dec_deg, radius_arcsec):
    """Search for sources within radius of position."""
    radius_deg = radius_arcsec / 3600.0

    cursor = conn.cursor()
    cursor.execute("""
        SELECT source_id, ra_deg, dec_deg, s_nvss, s_vlass
        FROM sources
        WHERE ABS(ra_deg - ?) < ?
          AND ABS(dec_deg - ?) < ?
    """, (ra_deg, radius_deg, dec_deg, radius_deg))

    results = []
    for row in cursor.fetchall():
        # Calculate exact separation
        dra = (row[1] - ra_deg) * np.cos(np.radians(dec_deg))
        ddec = row[2] - dec_deg
        sep = np.sqrt(dra**2 + ddec**2) * 3600  # arcsec

        if sep <= radius_arcsec:
            results.append({
                'source_id': row[0],
                'ra_deg': row[1],
                'dec_deg': row[2],
                's_nvss': row[3],
                's_vlass': row[4],
                'separation_arcsec': sep
            })

    return sorted(results, key=lambda x: x['separation_arcsec'])

# Usage
conn = sqlite3.connect("state/master_sources.sqlite3")
sources = cone_search(conn, ra_deg=123.45, dec_deg=45.67, radius_arcsec=60.0)

for src in sources:
    print(f"Source {src['source_id']}: {src['separation_arcsec']:.1f}\" away")
```

### Cross-Match Detection

```python
def find_counterpart(conn, ra_deg, dec_deg, max_sep_arcsec=10.0):
    """Find closest source within max_sep."""
    cursor = conn.cursor()

    # Search in box first (fast)
    search_radius_deg = max_sep_arcsec / 3600.0 * 2.0
    cursor.execute("""
        SELECT source_id, ra_deg, dec_deg, s_nvss
        FROM sources
        WHERE ABS(ra_deg - ?) < ?
          AND ABS(dec_deg - ?) < ?
    """, (ra_deg, search_radius_deg, dec_deg, search_radius_deg))

    # Calculate exact separations
    min_sep = float('inf')
    best_match = None

    for row in cursor.fetchall():
        dra = (row[1] - ra_deg) * np.cos(np.radians(dec_deg))
        ddec = row[2] - dec_deg
        sep = np.sqrt(dra**2 + ddec**2) * 3600  # arcsec

        if sep < min_sep and sep <= max_sep_arcsec:
            min_sep = sep
            best_match = {
                'source_id': row[0],
                'ra_deg': row[1],
                'dec_deg': row[2],
                's_nvss': row[3],
                'separation_arcsec': sep
            }

    return best_match

# Usage
match = find_counterpart(conn, ra_deg=123.45, dec_deg=45.67)
if match:
    print(f"Match: Source {match['source_id']}, {match['separation_arcsec']:.1f}\" away")
else:
    print("No match found")
```

### Batch Cross-Matching

```python
def batch_crossmatch(conn, detections, max_sep_arcsec=10.0):
    """Cross-match list of detections to catalog."""
    matches = []

    for det in detections:
        match = find_counterpart(
            conn,
            det['ra_deg'],
            det['dec_deg'],
            max_sep_arcsec
        )

        matches.append({
            'detection': det,
            'catalog_match': match,
            'is_new': match is None
        })

    return matches

# Usage
detections = [
    {'ra_deg': 123.45, 'dec_deg': 45.67, 'flux_jy': 0.05},
    {'ra_deg': 124.56, 'dec_deg': 46.78, 'flux_jy': 0.12},
]

results = batch_crossmatch(conn, detections)
for r in results:
    if r['is_new']:
        print(f"New source at {r['detection']['ra_deg']:.4f}, {r['detection']['dec_deg']:.4f}")
```

---

## Catalog Integration

### Add New Sources

```python
def add_source(conn, ra_deg, dec_deg, s_nvss=None, s_vlass=None,
               resolved=False, confused=False):
    """Add new source to catalog."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sources (
            ra_deg, dec_deg, s_nvss, s_vlass,
            resolved_flag, confusion_flag
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (ra_deg, dec_deg, s_nvss, s_vlass,
          int(resolved), int(confused)))

    conn.commit()
    return cursor.lastrowid
```

### Update Source Measurements

```python
def update_flux(conn, source_id, survey='vlass', flux_jy=None):
    """Update flux measurement for a source."""
    if survey == 'vlass':
        conn.execute("""
            UPDATE sources
            SET s_vlass=?
            WHERE source_id=?
        """, (flux_jy, source_id))
    elif survey == 'nvss':
        conn.execute("""
            UPDATE sources
            SET s_nvss=?
            WHERE source_id=?
        """, (flux_jy, source_id))

    conn.commit()
```

---

## Catalog Statistics

### Source Count

```sql
-- Total sources
SELECT COUNT(*) as total_sources FROM sources;

-- Sources by flags
SELECT
    SUM(CASE WHEN resolved_flag=0 THEN 1 ELSE 0 END) as point_sources,
    SUM(CASE WHEN resolved_flag=1 THEN 1 ELSE 0 END) as resolved,
    SUM(CASE WHEN confusion_flag=0 THEN 1 ELSE 0 END) as isolated,
    SUM(CASE WHEN confusion_flag=1 THEN 1 ELSE 0 END) as confused
FROM sources;
```

### Flux Distribution

```sql
-- NVSS flux histogram (bins of 0.01 Jy)
SELECT
    ROUND(s_nvss * 100) / 100.0 as flux_bin_jy,
    COUNT(*) as n_sources
FROM sources
WHERE s_nvss IS NOT NULL
GROUP BY flux_bin_jy
ORDER BY flux_bin_jy;

-- Flux statistics
SELECT
    MIN(s_nvss) as min_flux,
    MAX(s_nvss) as max_flux,
    AVG(s_nvss) as mean_flux,
    MEDIAN(s_nvss) as median_flux  -- Not standard SQL, may not work
FROM sources
WHERE s_nvss IS NOT NULL;
```

### Sky Coverage

```sql
-- RA/Dec coverage
SELECT
    MIN(ra_deg) as min_ra,
    MAX(ra_deg) as max_ra,
    MIN(dec_deg) as min_dec,
    MAX(dec_deg) as max_dec
FROM sources;

-- Source density by Dec band
SELECT
    ROUND(dec_deg / 5) * 5 as dec_band_deg,
    COUNT(*) as n_sources
FROM sources
GROUP BY dec_band_deg
ORDER BY dec_band_deg;
```

---

## Maintenance Queries

### Remove Duplicate Sources

```sql
-- Find potential duplicates (within 1 arcsec)
-- (Complex query, run with caution)
```

### Update Spectral Indices

```sql
-- Calculate spectral index where both NVSS and VLASS available
-- α = log(S1/S2) / log(ν1/ν2)
-- Assuming NVSS @ 1.4 GHz, VLASS @ 3.0 GHz

UPDATE sources
SET alpha = LOG10(s_vlass / s_nvss) / LOG10(3.0 / 1.4)
WHERE s_nvss IS NOT NULL
  AND s_vlass IS NOT NULL
  AND s_nvss > 0
  AND s_vlass > 0;
```

### Vacuum Database

```sql
-- Reclaim space after deletions
VACUUM;
```

---

## CLI Commands

### Query Sources

```bash
# Cone search
python -m dsa110_contimg.catalog.query cone \
  --ra 123.45 \
  --dec 45.67 \
  --radius 60.0 \
  --db state/master_sources.sqlite3
```

### Build Catalog

```bash
# Build from NVSS/VLASS catalogs
python -m dsa110_contimg.catalog.build_master build \
  --nvss nvss_catalog.fits \
  --vlass vlass_catalog.fits \
  --output state/master_sources.sqlite3
```

---

## Performance Notes

- **Indexes**: Spatial index on (ra_deg, dec_deg) for fast cone searches
- **Typical Size**: 1-2 KB per source entry
- **Query Speed**: <100ms for cone search within 1 degree
- **Large Catalog**: Can contain millions of sources
- **Optimization**: Consider spatial indexing extensions (R-tree) for very large
  catalogs

---

## Related Files

- **Code**: `dsa110_contimg/catalog/builders.py`, `query.py`
- **Crossmatch**: `dsa110_contimg/database/catalog_crossmatch_astropy.py`
- **Documentation**: `dsa110_contimg/catalog/README.md`

---

## See Also

- **Products Database**: `docs/reference/database_products_sqlite3.md`
- **Photometry**: `docs/reference/photometry_guide.md`
- **Catalog Building**: `docs/how-to/catalog_management.md`
