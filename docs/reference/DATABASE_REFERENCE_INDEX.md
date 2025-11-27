# Database Reference Documentation Index

**Locations**:

- `/data/dsa110-contimg/state/` - Primary databases
- `/data/dsa110-contimg/state/db/` - Additional databases
- `/data/dsa110-contimg/state/catalogs/` - Source catalogs

---

## Overview

The DSA-110 continuum imaging pipeline uses SQLite databases for state
management.

See [Database Schema](database_schema.md) for detailed table definitions and
example queries.

---

## Database Summary

### Primary (`/state/`)

| Database                | Purpose                               | Size    |
| ----------------------- | ------------------------------------- | ------- |
| `products.sqlite3`      | MS index, images, mosaics, photometry | ~500 KB |
| `hdf5.sqlite3`          | HDF5 file index for subband grouping  | ~65 KB  |
| `ingest.sqlite3`        | Streaming converter queue management  | ~16 KB  |
| `cal_registry.sqlite3`  | Calibration table registry            | ~24 KB  |
| `data_registry.sqlite3` | Data product registry                 | ~65 KB  |

### Secondary (`/state/db/`)

| Database                 | Purpose                           | Size    |
| ------------------------ | --------------------------------- | ------- |
| `master_sources.sqlite3` | Source catalog (NVSS, FIRST, RAX) | ~113 MB |
| `calibrators.sqlite3`    | Calibrator source catalog         | ~106 KB |
| `ingest_queue.sqlite3`   | Legacy ingest queue               | ~32 KB  |

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

conn = sqlite3.connect('/data/dsa110-contimg/state/products.sqlite3')
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
conn = sqlite3.connect('/data/dsa110-contimg/state/hdf5.sqlite3')

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
conn = sqlite3.connect('/data/dsa110-contimg/state/ingest.sqlite3')

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
conn = sqlite3.connect('/data/dsa110-contimg/state/cal_registry.sqlite3')

# Active bandpass tables
now = time.time()
caltables = conn.execute('''
    SELECT path, calibrator, created_at
    FROM caltables
    WHERE valid_from <= ? AND valid_until >= ?
    AND cal_type = 'bandpass'
    ORDER BY created_at DESC
''', (now, now)).fetchall()
```

---

## Connection Best Practices

```python
import sqlite3

# Always use WAL mode for concurrent access
conn = sqlite3.connect(
    '/data/dsa110-contimg/state/products.sqlite3',
    timeout=30.0
)
conn.execute('PRAGMA journal_mode=WAL')
conn.row_factory = sqlite3.Row  # Dict-like access
```

---

## Related Documentation

- [Database Schema](database_schema.md) - Complete schema reference
- [API Reference](api_reference.md) - Backend API endpoints
- [Streaming API](streaming-api.md) - Queue management API
