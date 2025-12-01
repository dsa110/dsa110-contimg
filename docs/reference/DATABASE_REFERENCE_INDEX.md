# Database Reference Documentation Index

**Locations**:

- `/data/dsa110-contimg/state/db/` - Unified pipeline database
- `/data/dsa110-contimg/state/catalogs/` - Source catalogs

---

## Overview

The DSA-110 continuum imaging pipeline uses a **unified SQLite database** for
all state management. As of Phase 2 consolidation, all pipeline tables are
stored in a single database file.

See [Database Schema](database_schema.md) for detailed table definitions and
example queries.

---

## Database Summary

### Unified Pipeline Database (`/state/db/`)

| Database           | Purpose                                      | Size    |
| ------------------ | -------------------------------------------- | ------- |
| `pipeline.sqlite3` | All pipeline state (see table groups below)  | ~45 MB  |

**Table Groups in `pipeline.sqlite3`:**

- **Products**: `ms_index`, `images`, `photometry_results` - MS and image tracking
- **Ingest**: `ingest_queue`, `performance_metrics` - Streaming queue management
- **HDF5 Index**: `hdf5_file_index` - Subband file tracking
- **Calibration**: `calibration_tables`, `calibration_source_catalog` - Cal table registry
- **Mosaics**: `mosaic_groups`, `mosaic_members` - Mosaic planning

### Other Databases (`/state/db/`)

| Database                 | Purpose                           | Size    |
| ------------------------ | --------------------------------- | ------- |
| `master_sources.sqlite3` | Source catalog (NVSS, FIRST, RAX) | ~113 MB |
| `calibrators.sqlite3`    | Calibrator source catalog         | ~106 KB |
| `docsearch.sqlite3`      | Documentation search index        | ~1 MB   |

### Catalogs (`/state/catalogs/`)

| Database                  | Purpose                      |
| ------------------------- | ---------------------------- |
| `vla_calibrators.sqlite3` | VLA calibrator catalog       |
| `nvss_dec+*.sqlite3`      | NVSS sources by declination  |
| `first_dec+*.sqlite3`     | FIRST sources by declination |

---

## Quick Access Patterns

### Check MS Conversion Status

```python
import sqlite3
import os

db_path = os.environ.get('PIPELINE_DB', '/data/dsa110-contimg/state/db/pipeline.sqlite3')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# Recent MS files
rows = conn.execute('''
    SELECT ms_path, timestamp, status
    FROM ms_index
    ORDER BY created_at DESC
    LIMIT 10
''').fetchall()

for row in rows:
    print(f"{row['timestamp']}: {row['status']}")
```

### Find Complete Subband Groups

```python
import os

db_path = os.environ.get('PIPELINE_DB', '/data/dsa110-contimg/state/db/pipeline.sqlite3')
conn = sqlite3.connect(db_path)

# Find groups with all 16 subbands
complete = conn.execute('''
    SELECT timestamp, COUNT(*) as count
    FROM hdf5_file_index
    GROUP BY timestamp
    HAVING count = 16
    ORDER BY timestamp DESC
    LIMIT 10
''').fetchall()
```

### Check Streaming Queue

```python
import os

db_path = os.environ.get('PIPELINE_DB', '/data/dsa110-contimg/state/db/pipeline.sqlite3')
conn = sqlite3.connect(db_path)

# Current queue status
status = conn.execute('''
    SELECT state, COUNT(*) as count
    FROM ingest_queue
    GROUP BY state
''').fetchall()
```

### Find Active Calibration Tables

```python
import time
import os

db_path = os.environ.get('PIPELINE_DB', '/data/dsa110-contimg/state/db/pipeline.sqlite3')
conn = sqlite3.connect(db_path)

# Active bandpass tables
now = time.time()
caltables = conn.execute('''
    SELECT path, calibrator, created_at
    FROM calibration_tables
    WHERE valid_from <= ? AND valid_until >= ?
    AND cal_type = 'bandpass'
    ORDER BY created_at DESC
''', (now, now)).fetchall()
```

---

## Connection Best Practices

```python
import sqlite3
import os

# Use PIPELINE_DB environment variable
db_path = os.environ.get('PIPELINE_DB', '/data/dsa110-contimg/state/db/pipeline.sqlite3')

# Always use WAL mode for concurrent access
conn = sqlite3.connect(db_path, timeout=30.0)
conn.execute('PRAGMA journal_mode=WAL')
conn.row_factory = sqlite3.Row  # Dict-like access
```

---

## Related Documentation

- [Database Schema](database_schema.md) - Complete schema reference
- [API Reference](api_reference.md) - Backend API endpoints
- [Streaming API](streaming-api.md) - Queue management API
