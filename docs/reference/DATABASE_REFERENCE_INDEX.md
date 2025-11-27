# Database Reference Documentation Index

**Generated**: 2025-11-18  
**Location**: `/data/dsa110-contimg/docs/reference/`

---

## Overview

Complete reference documentation for all SQLite databases in
`/data/dsa110-contimg/state/`. Each document provides schema details, common
queries, Python access examples, and maintenance procedures.

---

## Reference Documents

### 1. [Database Quick Reference](database_quick_reference.md)

**Master index and quick access guide**

- Quick access patterns for all databases
- Common workflow queries
- Python access examples
- Maintenance commands
- Troubleshooting tips

**Start here** for quick lookups and common operations.

---

### 2. [products.sqlite3](database_products_sqlite3.md)

**Main pipeline state database** (~800 KB)

**Key Tables**:

- `ms_index` - Measurement Set registry
- `mosaic_groups` - Mosaic group tracking
- `images` - Image product registry
- `mosaics` - Mosaic metadata
- `photometry` - Source photometry measurements

**Use For**:

- Track MS conversion status
- Monitor mosaic group progress
- Query image metadata
- Access photometry measurements

---

### 3. [hdf5.sqlite3](database_hdf5_sqlite3.md)

**HDF5 file indexing** (~33 MB)

**Key Tables**:

- `hdf5_file_index` - Fast HDF5 file queries

**Use For**:

- Find complete subband groups (16/16)
- Find semi-complete groups (12-15/16)
- Query by time range (MJD)
- Query by sky position (RA/Dec)

---

### 4. [ingest.sqlite3](database_ingest_sqlite3.md)

**Ingestion queue management** (~428 KB)

**Key Tables**:

- `ingest_queue` - Conversion queue
- `subband_files` - Subband file tracking
- `pointing_history` - Telescope pointing log
- `performance_metrics` - Conversion performance

**Use For**:

- Monitor conversion queue
- Track pending groups
- Check conversion failures
- Query pointing history

---

### 5. [cal_registry.sqlite3](database_cal_registry_sqlite3.md)

**Calibration registry** (~24 KB)

**Key Tables**:

- `caltables` - Calibration table registry with validity windows

**Use For**:

- Find active calibration tables for time window
- Track bandpass solutions (24-hour validity)
- Track gain solutions (1-hour validity)
- Query by calibrator source
- Get ordered apply list

---

### 6. [calibrators.sqlite3](database_calibrators_sqlite3.md)

**Calibrator source catalog** (~104 KB)

**Key Tables**:

- `bandpass_calibrators` - BP calibrator registry
- `gain_calibrators` - Gain calibrator registry
- `vla_calibrators` - Full VLA catalog
- `skymodel_metadata` - Sky model files

**Use For**:

- Find calibrators by declination range
- Select calibrators for observations
- Query flux densities
- Link to sky model files

---

### 7. [data_registry.sqlite3](database_data_registry_sqlite3.md)

**Publishing and QA tracking** (~64 KB)

**Key Tables**:

- `data_registry` - Product lifecycle tracking
- `data_relationships` - Product dependencies
- `data_tags` - Product tags

**Use For**:

- Track data product publishing
- Monitor QA status
- Check auto-publish criteria
- Retry failed publishes
- Query photometry status

---

### 8. [master_sources.sqlite3](database_master_sources_sqlite3.md)

**Radio source catalog** (~108 MB)

**Key Tables**:

- `sources` - Master source catalog (NVSS/VLASS cross-match)
- `final_references` - Reference sources
- `good_references` - Quality-filtered sources

**Use For**:

- Cone searches around positions
- Cross-match detections to catalog
- Query by flux density
- Find variable source candidates
- Spectral index queries

---

## Quick Comparison

| Database                   | Primary Use          | Query Speed | Update Frequency |
| -------------------------- | -------------------- | ----------- | ---------------- |
| **products.sqlite3**       | Pipeline state       | <10ms       | Continuous       |
| **hdf5.sqlite3**           | File indexing        | <50ms       | Per file arrival |
| **ingest.sqlite3**         | Conversion queue     | <10ms       | Continuous       |
| **cal_registry.sqlite3**   | Cal table lookup     | <5ms        | Hourly/daily     |
| **calibrators.sqlite3**    | Calibrator selection | <5ms        | Rarely           |
| **data_registry.sqlite3**  | Publishing status    | <10ms       | Per mosaic       |
| **master_sources.sqlite3** | Source crossmatch    | <100ms      | Rarely           |

---

## Database Workflow

```
1. HDF5 files arrive → hdf5.sqlite3 (indexing)
2. Groups detected → ingest.sqlite3 (queue)
3. Conversion to MS → products.sqlite3 (ms_index)
4. Group formation → products.sqlite3 (mosaic_groups)
5. Calibration lookup → cal_registry.sqlite3 + calibrators.sqlite3
6. Imaging → products.sqlite3 (images)
7. Mosaic creation → products.sqlite3 (mosaics)
8. QA & Publishing → data_registry.sqlite3
9. Source crossmatch → master_sources.sqlite3
```

---

## Access Patterns by Use Case

### I want to...

**...check conversion status** → Read `products.sqlite3` (`ms_index` table)

**...find groups ready for conversion** → Read `hdf5.sqlite3` + `ingest.sqlite3`

**...monitor mosaic progress** → Read `products.sqlite3` (`mosaic_groups` table)

**...find calibration tables** → Read `cal_registry.sqlite3` (by MJD range)

**...select a calibrator** → Read `calibrators.sqlite3` (by Dec range)

**...check publishing status** → Read `data_registry.sqlite3`

**...crossmatch sources** → Read `master_sources.sqlite3` (cone search)

**...track telescope pointing** → Read `ingest.sqlite3` (`pointing_history`)

---

## Common Operations

### Check Pipeline Health

```bash
# MS status
sqlite3 state/products.sqlite3 \
  "SELECT status, COUNT(*) FROM ms_index GROUP BY status"

# Queue status
sqlite3 state/ingest.sqlite3 \
  "SELECT state, COUNT(*) FROM ingest_queue GROUP BY state"

# Publishing status
sqlite3 state/data_registry.sqlite3 \
  "SELECT status, COUNT(*) FROM data_registry GROUP BY status"
```

### Find Data for Time Window

```bash
# MS files for MJD range
sqlite3 state/products.sqlite3 \
  "SELECT path FROM ms_index
   WHERE mid_mjd BETWEEN 59000.0 AND 59001.0"

# Mosaics for time range
sqlite3 state/products.sqlite3 \
  "SELECT name, start_mjd, end_mjd FROM mosaics
   WHERE start_mjd <= 59001.0 AND end_mjd >= 59000.0"
```

### Calibration Workflow

```bash
# Find calibrator for Dec
sqlite3 state/calibrators.sqlite3 \
  "SELECT calibrator_name, ra_deg, dec_deg FROM bandpass_calibrators
   WHERE dec_range_min <= 45.0 AND dec_range_max >= 45.0"

# Find active cal tables for time
sqlite3 state/cal_registry.sqlite3 \
  "SELECT path, table_type FROM caltables
   WHERE status='active'
     AND valid_start_mjd <= 59000.5
     AND valid_end_mjd >= 59000.5
   ORDER BY order_index"
```

---

## Maintenance Tasks

### Daily

```bash
# Check database sizes
ls -lh state/*.sqlite3

# Verify integrity
for db in state/*.sqlite3; do
    sqlite3 "$db" "PRAGMA integrity_check;"
done
```

### Weekly

```bash
# Backup databases
for db in products.sqlite3 hdf5.sqlite3 cal_registry.sqlite3; do
    sqlite3 "state/$db" ".backup state/backups/${db}.backup"
done
```

### Monthly

```bash
# Vacuum databases (reclaim space)
for db in state/*.sqlite3; do
    sqlite3 "$db" "VACUUM;"
done

# Archive old entries (products.sqlite3)
sqlite3 state/products.sqlite3 \
  "DELETE FROM ms_index
   WHERE processed_at < (strftime('%s','now') - 90*86400)"
```

---

## Python Integration

### Import Database Modules

```python
# Products database
from dsa110_contimg.database.products import (
    ensure_products_db, ms_index_upsert, image_insert
)

# HDF5 database
from dsa110_contimg.database.hdf5_db import ensure_hdf5_db
from dsa110_contimg.database.hdf5_index import query_complete_groups

# Calibration registry
from dsa110_contimg.database.registry import (
    ensure_cal_registry_db, register_caltable, get_active_applylist
)

# Calibrators
from dsa110_contimg.database.calibrators import (
    ensure_calibrators_db, find_calibrator_by_dec
)

# Data registry
from dsa110_contimg.database.data_registry import (
    ensure_data_registry_db, register_data_instance, finalize_data
)
```

### Example Workflow

```python
from pathlib import Path

# 1. Check for complete HDF5 groups
from dsa110_contimg.database.hdf5_index import query_complete_groups
groups = query_complete_groups(
    db_path=Path("state/hdf5.sqlite3"),
    start_mjd=59000.0,
    end_mjd=59001.0,
    min_subbands=12
)

# 2. Convert and register MS
from dsa110_contimg.database.products import ensure_products_db, ms_index_upsert
conn = ensure_products_db(Path("state/products.sqlite3"))
ms_index_upsert(
    conn,
    path="/stage/ms/2025-11-18T12:00:00.ms",
    start_mjd=59000.5,
    status="converted"
)

# 3. Find calibration tables
from dsa110_contimg.database.registry import get_active_applylist
cal_conn = ensure_cal_registry_db(Path("state/cal_registry.sqlite3"))
tables = get_active_applylist(cal_conn, mjd=59000.5)

# 4. Register mosaic for publishing
from dsa110_contimg.database.data_registry import register_data_instance
reg_conn = ensure_data_registry_db(Path("state/data_registry.sqlite3"))
register_data_instance(
    reg_conn,
    data_type="mosaic",
    data_id="mosaic_2025-11-18_12-00-00",
    stage_path="/stage/mosaics/mosaic_2025-11-18_12-00-00.fits"
)
```

---

## Troubleshooting

### Database Locked

```bash
# Check for open connections
lsof state/products.sqlite3

# Force WAL checkpoint
sqlite3 state/products.sqlite3 "PRAGMA wal_checkpoint(TRUNCATE);"
```

### Slow Queries

```bash
# Analyze query plan
sqlite3 state/products.sqlite3
> EXPLAIN QUERY PLAN SELECT * FROM ms_index WHERE status='converted';

# Add missing indexes
> CREATE INDEX idx_ms_status ON ms_index(status);
```

### Corruption

```bash
# Check integrity
sqlite3 state/products.sqlite3 "PRAGMA integrity_check;"

# Attempt recovery
sqlite3 state/products.sqlite3 ".recover" | \
  sqlite3 state/products_recovered.sqlite3
```

---

## Related Documentation

- **[Workspace Study](../archive/progress-logs/analysis/workspace_comprehensive_study.md)** -
  Complete workspace overview
- **Pipeline Documentation** -
  Pipeline architecture
- **[Directory Architecture](../architecture/architecture/DIRECTORY_ARCHITECTURE.md)** -
  Filesystem organization

---

## Document History

- **2025-11-18**: Initial creation of all database reference documents
  - 8 comprehensive reference documents
  - Schema details, query examples, Python access
  - Maintenance procedures and troubleshooting

---

**Index Version**: 1.0  
**Total Documents**: 8  
**Total Pages**: ~150
