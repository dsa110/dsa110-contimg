# SQLite Database Quick Reference

**Location**: `/data/dsa110-contimg/state/`  
**Last Updated**: 2025-11-18

---

## Overview

The DSA-110 pipeline uses **7 primary SQLite databases** in
`/data/dsa110-contimg/state/` for state management, data tracking, and catalog
services. All databases use **WAL mode** for concurrent access where
appropriate.

---

## Database Summary

| Database                   | Size    | Purpose                | Key Tables                                    |
| -------------------------- | ------- | ---------------------- | --------------------------------------------- |
| **products.sqlite3**       | ~800 KB | Pipeline data products | ms_index, mosaic_groups, images, mosaics      |
| **hdf5.sqlite3**           | ~33 MB  | HDF5 file indexing     | hdf5_file_index                               |
| **ingest.sqlite3**         | ~428 KB | Ingestion queue        | ingest_queue, subband_files, pointing_history |
| **cal_registry.sqlite3**   | ~24 KB  | Calibration registry   | caltables                                     |
| **calibrators.sqlite3**    | ~104 KB | Calibrator catalog     | bandpass_calibrators, vla_calibrators         |
| **data_registry.sqlite3**  | ~64 KB  | Publishing & QA        | data_registry                                 |
| **master_sources.sqlite3** | ~108 MB | Radio source catalog   | sources                                       |

---

## Quick Access Patterns

### Check MS Files Ready for Processing

```bash
sqlite3 state/products.sqlite3 \
  "SELECT path, status FROM ms_index WHERE status='converted' LIMIT 10"
```

### Check Pending Mosaic Groups

```bash
sqlite3 state/products.sqlite3 \
  "SELECT group_id, status FROM mosaic_groups WHERE status='pending'"
```

### Find Complete HDF5 Groups

```bash
sqlite3 state/hdf5.sqlite3 \
  "SELECT group_id, COUNT(*) FROM hdf5_file_index
   GROUP BY group_id HAVING COUNT(*) >= 12"
```

### Check Ingestion Queue

```bash
sqlite3 state/ingest.sqlite3 \
  "SELECT state, COUNT(*) FROM ingest_queue GROUP BY state"
```

### Find Active Calibration Tables

```bash
sqlite3 state/cal_registry.sqlite3 \
  "SELECT set_name, table_type, path FROM caltables
   WHERE status='active' ORDER BY valid_start_mjd DESC LIMIT 10"
```

### Check Publishing Status

```bash
sqlite3 state/data_registry.sqlite3 \
  "SELECT status, COUNT(*) FROM data_registry GROUP BY status"
```

### Find Sources Near Position

```bash
sqlite3 state/master_sources.sqlite3 \
  "SELECT source_id, ra_deg, dec_deg, s_nvss FROM sources
   WHERE ABS(ra_deg - 123.45) < 0.1 AND ABS(dec_deg - 45.67) < 0.1"
```

---

## Python Quick Access

```python
from pathlib import Path

# Products database
from dsa110_contimg.database.products import ensure_products_db
conn = ensure_products_db(Path("state/products.sqlite3"))

# HDF5 index
from dsa110_contimg.database.hdf5_db import ensure_hdf5_db
conn = ensure_hdf5_db(Path("state/hdf5.sqlite3"))

# Ingest database
from dsa110_contimg.database.products import ensure_ingest_db
conn = ensure_ingest_db(Path("state/ingest.sqlite3"))

# Cal registry
from dsa110_contimg.database.registry import ensure_cal_registry_db
conn = ensure_cal_registry_db(Path("state/cal_registry.sqlite3"))

# Calibrators
from dsa110_contimg.database.calibrators import ensure_calibrators_db
conn = ensure_calibrators_db(Path("state/calibrators.sqlite3"))

# Data registry
from dsa110_contimg.database.data_registry import ensure_data_registry_db
conn = ensure_data_registry_db(Path("state/data_registry.sqlite3"))

# Master sources (direct sqlite3)
import sqlite3
conn = sqlite3.connect("state/master_sources.sqlite3")
```

---

## Common Workflow Queries

### Complete Pipeline Status

```sql
-- MS status from products.sqlite3
SELECT status, COUNT(*) FROM ms_index GROUP BY status;

-- Mosaic group status
SELECT status, COUNT(*) FROM mosaic_groups GROUP BY status;

-- Publishing status from data_registry.sqlite3
SELECT status, COUNT(*) FROM data_registry GROUP BY status;
```

### Find Data for Time Range

```sql
-- MS files (products.sqlite3)
SELECT path, mid_mjd FROM ms_index
WHERE mid_mjd BETWEEN 59000.0 AND 59001.0;

-- HDF5 groups (hdf5.sqlite3)
SELECT group_id, timestamp_mjd FROM hdf5_file_index
WHERE timestamp_mjd BETWEEN 59000.0 AND 59001.0
GROUP BY group_id;
```

### Calibration Status

```sql
-- Active calibrations (cal_registry.sqlite3)
SELECT table_type, COUNT(*) FROM caltables
WHERE status='active'
GROUP BY table_type;

-- Calibrators in Dec range (calibrators.sqlite3)
SELECT calibrator_name, dec_deg FROM bandpass_calibrators
WHERE dec_range_min <= 45.0 AND dec_range_max >= 45.0;
```

---

## Database Maintenance

### Check Database Sizes

```bash
cd /data/dsa110-contimg/state
ls -lh *.sqlite3 | awk '{print $9, $5}'
```

### Backup Databases

```bash
# Backup critical databases
for db in products.sqlite3 hdf5.sqlite3 cal_registry.sqlite3 data_registry.sqlite3; do
    sqlite3 "state/$db" ".backup state/backups/${db}.backup"
done
```

### Vacuum Databases

```bash
# Reclaim space after deletions
for db in *.sqlite3; do
    echo "Vacuuming $db..."
    sqlite3 "$db" "VACUUM;"
done
```

### Check Database Integrity

```bash
# Check for corruption
for db in *.sqlite3; do
    echo "Checking $db..."
    sqlite3 "$db" "PRAGMA integrity_check;"
done
```

---

## Detailed Documentation

Each database has comprehensive reference documentation:

- **[products.sqlite3](database_products_sqlite3.md)** - Main pipeline state
  database
  - MS index, images, mosaics, photometry
- **[hdf5.sqlite3](database_hdf5_sqlite3.md)** - HDF5 file indexing
  - Fast subband group queries
- **[ingest.sqlite3](database_ingest_sqlite3.md)** - Ingestion queue management
  - Conversion workflow tracking
- **[cal_registry.sqlite3](database_cal_registry_sqlite3.md)** - Calibration
  registry
  - Cal table validity windows
- **[calibrators.sqlite3](database_calibrators_sqlite3.md)** - Calibrator
  catalog
  - Source selection by declination
- **[data_registry.sqlite3](database_data_registry_sqlite3.md)** - Publishing &
  QA
  - Auto-publish workflow
- **[master_sources.sqlite3](database_master_sources_sqlite3.md)** - Radio
  source catalog
  - Cross-matched NVSS/VLASS sources

---

## Database Relationships

```
HDF5 Files (hdf5.sqlite3)
    ↓ (complete groups)
Ingestion Queue (ingest.sqlite3)
    ↓ (conversion)
MS Index (products.sqlite3)
    ↓ (grouping)
Mosaic Groups (products.sqlite3)
    ↓ (calibration)
Cal Registry (cal_registry.sqlite3) + Calibrators (calibrators.sqlite3)
    ↓ (imaging)
Images (products.sqlite3)
    ↓ (mosaic creation)
Mosaics (products.sqlite3)
    ↓ (publishing)
Data Registry (data_registry.sqlite3)
    ↓ (crossmatch)
Master Sources (master_sources.sqlite3)
```

---

## Performance Tips

1. **Use WAL mode**: Already enabled where appropriate
2. **Use transactions**: Batch writes in transactions
3. **Use prepared statements**: Reuse queries with parameters
4. **Add indexes**: Create indexes for frequently queried columns
5. **Vacuum regularly**: Reclaim space after deletions
6. **Monitor size**: Track database growth over time

---

## Troubleshooting

### Database Locked

```bash
# Check for open connections
lsof state/products.sqlite3

# Force checkpoint (if safe)
sqlite3 state/products.sqlite3 "PRAGMA wal_checkpoint(TRUNCATE);"
```

### Slow Queries

```bash
# Analyze query performance
sqlite3 state/products.sqlite3
> EXPLAIN QUERY PLAN SELECT * FROM ms_index WHERE status='converted';
```

### Corruption

```bash
# Check integrity
sqlite3 state/products.sqlite3 "PRAGMA integrity_check;"

# Recover if possible
sqlite3 state/products.sqlite3 ".recover" | sqlite3 state/products_recovered.sqlite3
```

---

## Environment Variables

```bash
# Override default database locations
export PIPELINE_STATE_DIR="/data/dsa110-contimg/state"
export CAL_REGISTRY_DB="/data/dsa110-contimg/state/cal_registry.sqlite3"
export PRODUCTS_DB="/data/dsa110-contimg/state/products.sqlite3"
```

---

## CLI Tools

### Database CLI

```bash
# Products database
python -m dsa110_contimg.database.registry_cli discover \
  --scan-dir /stage/dsa110-contimg/ms

# Publishing CLI
python -m dsa110_contimg.database.cli publish \
  --db state/data_registry.sqlite3 \
  --data-id mosaic_2025-11-18_12-00-00

# Calibration CLI
python -m dsa110_contimg.calibration.cli list-tables \
  --cal-registry-db state/cal_registry.sqlite3
```

---

## Related Documentation

- **[Comprehensive Workspace Study](../dev/analysis/workspace_comprehensive_study.md)**
- **[Pipeline Documentation](../../dsa110_contimg/README_PIPELINE_DOCUMENTATION.md)**
- **[Data Directory Architecture](../concepts/DIRECTORY_ARCHITECTURE.md)**

---

**Quick Reference Version**: 1.0  
**Generated**: 2025-11-18
