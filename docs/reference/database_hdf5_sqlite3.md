# Database Reference: hdf5.sqlite3

**Location**: `/data/dsa110-contimg/state/hdf5.sqlite3`  
**Purpose**: Fast indexing of incoming HDF5/UVH5 visibility files  
**Size**: ~33 MB (typical, grows with observations)

---

## Overview

The `hdf5.sqlite3` database provides fast indexing and querying of incoming HDF5
visibility files before MS conversion. It enables quick subband group queries,
time-range searches, and sky position lookups without reading HDF5 files
directly.

---

## Table: `hdf5_file_index`

**Purpose**: Index all HDF5 visibility files for fast querying

**Schema**:

```sql
CREATE TABLE hdf5_file_index (
    path TEXT PRIMARY KEY,               -- Full filesystem path
    filename TEXT NOT NULL,              -- Filename only
    group_id TEXT NOT NULL,              -- Group identifier (timestamp)
    subband_code TEXT NOT NULL,          -- Subband code (e.g., 'sb00')
    subband_num INTEGER,                 -- Subband number (0-15)
    timestamp_iso TEXT NOT NULL,         -- ISO timestamp
    timestamp_mjd REAL NOT NULL,         -- Modified Julian Date
    file_size_bytes INTEGER,             -- File size in bytes
    modified_time REAL,                  -- File modification time
    indexed_at REAL,                     -- Indexing timestamp
    stored INTEGER DEFAULT 1,            -- Storage status (1=exists)
    ra_deg REAL,                         -- RA (degrees, sb00 only)
    dec_deg REAL,                        -- Dec (degrees, sb00 only)
    obs_date TEXT,                       -- Observation date (sb00 only)
    obs_time TEXT                        -- Observation time (sb00 only)
);

CREATE INDEX idx_hdf5_group_id ON hdf5_file_index(group_id);
CREATE INDEX idx_hdf5_timestamp_mjd ON hdf5_file_index(timestamp_mjd);
CREATE INDEX idx_hdf5_group_subband ON hdf5_file_index(group_id, subband_code);
CREATE INDEX idx_hdf5_stored ON hdf5_file_index(stored);
CREATE INDEX idx_hdf5_ra_dec ON hdf5_file_index(ra_deg, dec_deg);
CREATE INDEX idx_hdf5_obs_date ON hdf5_file_index(obs_date);
CREATE INDEX idx_hdf5_subband_num ON hdf5_file_index(subband_num);
CREATE INDEX idx_hdf5_group_subband_num ON hdf5_file_index(group_id, subband_num);
```

---

## Key Concepts

### Group ID

- **Format**: `YYYY-MM-DDTHH:MM:SS` (ISO 8601)
- **Example**: `2025-11-18T12:00:00`
- **Purpose**: Identifies observation time window

### Subband Codes

- **Format**: `sb00` through `sb15` (16 subbands)
- **Mapping**: `sb00` = subband 0, `sb01` = subband 1, etc.

### Metadata Population

- **RA/Dec**: Only populated for `sb00` files (first subband)
- **Other subbands**: Use `group_id` to find metadata from `sb00`

---

## Common Queries

### Find Complete Subband Groups

```sql
-- Groups with all 16 subbands
SELECT group_id, COUNT(*) as n_subbands
FROM hdf5_file_index
WHERE stored=1
GROUP BY group_id
HAVING COUNT(*) = 16;
```

### Find Semi-Complete Groups (12-15 subbands)

```sql
-- Groups with 12-15 subbands (eligible for processing)
SELECT group_id, COUNT(*) as n_subbands
FROM hdf5_file_index
WHERE stored=1
GROUP BY group_id
HAVING COUNT(*) >= 12 AND COUNT(*) < 16;
```

### List Files in a Group

```sql
-- Get all subbands for a group
SELECT subband_code, subband_num, path, file_size_bytes
FROM hdf5_file_index
WHERE group_id='2025-11-18T12:00:00'
ORDER BY subband_num;
```

### Find Missing Subbands

```sql
-- Find which subbands are missing from a group
WITH RECURSIVE cnt(n) AS (
    SELECT 0
    UNION ALL
    SELECT n+1 FROM cnt WHERE n < 15
)
SELECT n as missing_subband
FROM cnt
WHERE n NOT IN (
    SELECT subband_num
    FROM hdf5_file_index
    WHERE group_id='2025-11-18T12:00:00'
);
```

### Time Range Queries

```sql
-- Files in MJD range
SELECT group_id, subband_code, timestamp_mjd
FROM hdf5_file_index
WHERE timestamp_mjd BETWEEN 59000.0 AND 59001.0
ORDER BY timestamp_mjd, subband_num;

-- Files in date range
SELECT group_id, obs_date, COUNT(*) as n_files
FROM hdf5_file_index
WHERE obs_date BETWEEN '2025-11-18' AND '2025-11-19'
GROUP BY group_id, obs_date;
```

### Sky Position Queries

```sql
-- Files near a sky position (RA/Dec in degrees)
SELECT DISTINCT group_id, ra_deg, dec_deg
FROM hdf5_file_index
WHERE ABS(ra_deg - 123.45) < 1.0
  AND ABS(dec_deg - 45.67) < 1.0
  AND ra_deg IS NOT NULL;
```

### Storage Status

```sql
-- Check if files still exist on disk
SELECT group_id, COUNT(*) as n_stored
FROM hdf5_file_index
WHERE stored=1
GROUP BY group_id;

-- Find archived/deleted files
SELECT group_id, subband_code, path
FROM hdf5_file_index
WHERE stored=0;
```

---

## Python Access Examples

### Using `hdf5_index` Module

```python
from pathlib import Path
from dsa110_contimg.database.hdf5_index import (
    query_complete_groups,
    query_group_files,
    SubbandGroupInfo
)

# Find complete groups in time range
groups = query_complete_groups(
    db_path=Path("state/hdf5.sqlite3"),
    start_mjd=59000.0,
    end_mjd=59001.0,
    min_subbands=12  # Accept semi-complete groups
)

for group in groups:
    print(f"Group: {group.group_id}, Subbands: {group.n_subbands}")

# Get files for a specific group
files = query_group_files(
    db_path=Path("state/hdf5.sqlite3"),
    group_id="2025-11-18T12:00:00"
)

for f in files:
    print(f"Subband {f.subband_num}: {f.path}")
```

### Direct SQL Access

```python
import sqlite3

conn = sqlite3.connect("state/hdf5.sqlite3")
conn.row_factory = sqlite3.Row

# Find groups ready for conversion
cursor = conn.cursor()
cursor.execute("""
    SELECT group_id, COUNT(*) as n_subbands,
           MIN(timestamp_mjd) as start_mjd,
           MAX(timestamp_mjd) as end_mjd
    FROM hdf5_file_index
    WHERE stored=1
    GROUP BY group_id
    HAVING COUNT(*) >= 12
""")

for row in cursor.fetchall():
    print(f"{row['group_id']}: {row['n_subbands']} subbands")

conn.close()
```

---

## Indexing Workflow

### 1. File Arrival

```python
from dsa110_contimg.database.hdf5_db import index_hdf5_file

# Index new HDF5 file
index_hdf5_file(
    conn,
    path="/data/incoming/2025-11-18T12:00:00_sb00.hdf5",
    group_id="2025-11-18T12:00:00",
    subband_code="sb00",
    subband_num=0,
    timestamp_mjd=59000.5,
    ra_deg=123.45,
    dec_deg=45.67
)
```

### 2. Group Detection

```python
# Check if group is complete
cursor.execute("""
    SELECT COUNT(*) as n_subbands
    FROM hdf5_file_index
    WHERE group_id=?
""", (group_id,))

n_subbands = cursor.fetchone()[0]
is_complete = n_subbands == 16
is_semi_complete = 12 <= n_subbands < 16
```

### 3. Conversion Trigger

```python
if is_complete or is_semi_complete:
    # Trigger conversion
    trigger_conversion(group_id)
```

---

## Subband Group Management

### SubbandGroupInfo Dataclass

```python
from dataclasses import dataclass

@dataclass
class SubbandGroupInfo:
    group_id: str
    n_subbands: int
    n_expected: int = 16
    is_complete: bool
    is_semi_complete: bool
    missing_subbands: list
    has_synthetic: bool = False
    synthetic_subbands: list = None
```

### Query Group Status

```python
from dsa110_contimg.database.hdf5_index import get_group_info

group_info = get_group_info(
    conn,
    group_id="2025-11-18T12:00:00"
)

print(f"Complete: {group_info.is_complete}")
print(f"Semi-complete: {group_info.is_semi_complete}")
print(f"Missing: {group_info.missing_subbands}")
```

---

## Maintenance Queries

### Update Storage Status

```sql
-- Mark file as archived
UPDATE hdf5_file_index
SET stored=0
WHERE path='/data/incoming/old_file.hdf5';

-- Restore storage status
UPDATE hdf5_file_index
SET stored=1
WHERE group_id='2025-11-18T12:00:00';
```

### Remove Old Entries

```sql
-- Delete entries older than 90 days
DELETE FROM hdf5_file_index
WHERE indexed_at < (strftime('%s','now') - 90*86400);
```

### Database Statistics

```sql
-- Count files by date
SELECT obs_date, COUNT(*) as n_files
FROM hdf5_file_index
GROUP BY obs_date
ORDER BY obs_date DESC;

-- Storage usage by date
SELECT obs_date,
       COUNT(*) as n_files,
       SUM(file_size_bytes)/1024.0/1024.0/1024.0 as size_gb
FROM hdf5_file_index
WHERE stored=1
GROUP BY obs_date;

-- Group completeness statistics
SELECT
    CASE
        WHEN cnt=16 THEN 'complete'
        WHEN cnt>=12 THEN 'semi-complete'
        ELSE 'incomplete'
    END as status,
    COUNT(*) as n_groups
FROM (
    SELECT group_id, COUNT(*) as cnt
    FROM hdf5_file_index
    GROUP BY group_id
)
GROUP BY status;
```

---

## CLI Commands

### Index Directory

```bash
# Index all HDF5 files in a directory
python -m dsa110_contimg.database.hdf5_index index \
  --directory /data/incoming \
  --db-path state/hdf5.sqlite3
```

### Query Groups

```bash
# List complete groups
python -m dsa110_contimg.database.hdf5_index list-groups \
  --db-path state/hdf5.sqlite3 \
  --min-subbands 16

# List semi-complete groups
python -m dsa110_contimg.database.hdf5_index list-groups \
  --db-path state/hdf5.sqlite3 \
  --min-subbands 12 \
  --max-subbands 15
```

### Verify Storage

```bash
# Verify files still exist on disk
python -m dsa110_contimg.database.hdf5_index verify \
  --db-path state/hdf5.sqlite3 \
  --update-status
```

---

## Performance Notes

- **Indexes**: Optimized for group queries, time ranges, sky positions
- **Typical Size**: ~2 KB per HDF5 file entry
- **Query Speed**: <50ms for group completeness checks
- **WAL Mode**: Enabled for concurrent read/write access

---

## Related Files

- **Code**: `dsa110_contimg/database/hdf5_db.py`, `hdf5_index.py`
- **Conversion**: `dsa110_contimg/conversion/strategies/hdf5_orchestrator.py`
- **Documentation**: `dsa110_contimg/conversion/SEMI_COMPLETE_SUBBAND_GROUPS.md`

---

## See Also

- **Ingest Database**: `docs/reference/database_ingest_sqlite3.md`
- **Products Database**: `docs/reference/database_products_sqlite3.md`
- **Semi-Complete Groups**:
  `dsa110_contimg/conversion/SEMI_COMPLETE_SUBBAND_GROUPS.md`
