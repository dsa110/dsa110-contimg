# Database Reference Documentation Index

**Location**: `/data/dsa110-contimg/state/`

---

## Overview

The DSA-110 continuum imaging pipeline uses SQLite databases for state
management. All databases are in `/data/dsa110-contimg/state/`.

See [Database Schema](database_schema.md) for detailed table definitions and
example queries.

---

## Database Summary

| Database | Purpose | Size |
|----------|---------|------|
| `products.sqlite3` | MS index, images, mosaics, photometry | ~800 KB |
| `hdf5.sqlite3` | HDF5 file index for subband grouping | ~33 MB |
| `ingest.sqlite3` | Streaming converter queue management | ~428 KB |
| `cal_registry.sqlite3` | Calibration table registry | ~24 KB |
| `calibrator_registry.sqlite3` | Calibrator source catalog | ~104 KB |
| `master_sources.sqlite3` | Source catalog (NVSS, FIRST, RAX) | ~86 MB |
| `data_registry.sqlite3` | Data product registry | Variable |

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
