# Database Reference: ingest.sqlite3

**Location**: `/data/dsa110-contimg/state/ingest.sqlite3`  
**Purpose**: HDF5 ingestion queue and pointing history tracking  
**Size**: ~428 KB (typical)

---

## Overview

The `ingest.sqlite3` database manages the ingestion queue for incoming HDF5
files and tracks telescope pointing history. It coordinates the conversion
workflow from file arrival through MS creation.

---

## Tables

### 1. `ingest_queue` - Conversion Queue Management

**Purpose**: Track subband groups through the conversion process

**Schema**:

```sql
CREATE TABLE ingest_queue (
    group_id TEXT PRIMARY KEY,           -- Group identifier (timestamp)
    state TEXT NOT NULL,                 -- Current state
    received_at REAL NOT NULL,           -- First file received time
    last_update REAL NOT NULL,           -- Last status update time
    expected_subbands INTEGER,           -- Expected subband count (16)
    retry_count INTEGER DEFAULT 0,       -- Number of retry attempts
    error TEXT,                          -- Error message (if failed)
    checkpoint_path TEXT,                -- Conversion checkpoint path
    processing_stage TEXT DEFAULT 'collecting',  -- Current stage
    chunk_minutes REAL,                  -- Chunk duration (minutes)
    has_calibrator INTEGER DEFAULT NULL, -- Has calibrator flag
    calibrators TEXT,                    -- JSON list of calibrators
    error_message TEXT                   -- Detailed error message
);
```

**State Values**:

- `pending` - Group formed, awaiting conversion
- `processing` - Conversion in progress
- `completed` - Conversion successful
- `failed` - Conversion failed
- `collecting` - Still receiving files

**Processing Stage Values**:

- `collecting` - Waiting for all subbands
- `queued` - Ready for conversion
- `converting` - Conversion in progress
- `finalizing` - MS finalization
- `done` - Conversion complete

---

### 2. `subband_files` - Subband File Tracking

**Purpose**: Track individual subband files within each group

**Schema**:

```sql
CREATE TABLE subband_files (
    group_id TEXT NOT NULL,              -- Group identifier
    subband_idx INTEGER NOT NULL,        -- Subband index (0-15)
    path TEXT NOT NULL,                  -- Full filesystem path
    PRIMARY KEY (group_id, subband_idx)
);
```

---

### 3. `pointing_history` - Telescope Pointing Log

**Purpose**: Track telescope pointing over time

**Schema**:

```sql
CREATE TABLE pointing_history (
    timestamp REAL PRIMARY KEY,          -- Unix timestamp
    ra_deg REAL,                         -- RA (degrees)
    dec_deg REAL                         -- Dec (degrees)
);
CREATE INDEX idx_pointing_timestamp ON pointing_history(timestamp);
```

---

### 4. `performance_metrics` - Conversion Performance

**Purpose**: Track conversion performance metrics

**Schema**:

```sql
CREATE TABLE performance_metrics (
    group_id TEXT PRIMARY KEY,
    conversion_start REAL,
    conversion_end REAL,
    duration_sec REAL,
    n_subbands INTEGER,
    total_size_bytes INTEGER,
    throughput_mbps REAL
);
```

---

## Common Queries

### Ingestion Queue Status

```sql
-- Count groups by state
SELECT state, COUNT(*) as n_groups
FROM ingest_queue
GROUP BY state;

-- Pending groups (ready for conversion)
SELECT group_id, received_at, expected_subbands
FROM ingest_queue
WHERE state='pending'
ORDER BY received_at;

-- Failed groups
SELECT group_id, error_message, retry_count
FROM ingest_queue
WHERE state='failed';

-- Groups in progress
SELECT group_id, processing_stage, last_update
FROM ingest_queue
WHERE state='processing';
```

### Subband File Queries

```sql
-- List all subbands for a group
SELECT subband_idx, path
FROM subband_files
WHERE group_id='2025-11-18T12:00:00'
ORDER BY subband_idx;

-- Check group completeness
SELECT group_id, COUNT(*) as n_subbands
FROM subband_files
GROUP BY group_id
HAVING COUNT(*) >= 12;

-- Find missing subbands
WITH RECURSIVE cnt(n) AS (
    SELECT 0
    UNION ALL
    SELECT n+1 FROM cnt WHERE n < 15
)
SELECT n as missing_subband
FROM cnt
WHERE n NOT IN (
    SELECT subband_idx
    FROM subband_files
    WHERE group_id='2025-11-18T12:00:00'
);
```

### Pointing History Queries

```sql
-- Get pointing at specific time
SELECT ra_deg, dec_deg
FROM pointing_history
WHERE timestamp <= 1731964800.0
ORDER BY timestamp DESC
LIMIT 1;

-- Pointing changes over time
SELECT timestamp, ra_deg, dec_deg
FROM pointing_history
WHERE timestamp BETWEEN 1731964800.0 AND 1732051200.0
ORDER BY timestamp;

-- Find observations near a position
SELECT timestamp, ra_deg, dec_deg
FROM pointing_history
WHERE ABS(ra_deg - 123.45) < 1.0
  AND ABS(dec_deg - 45.67) < 1.0;
```

### Performance Metrics

```sql
-- Average conversion time
SELECT AVG(duration_sec) as avg_duration_sec,
       AVG(throughput_mbps) as avg_throughput_mbps
FROM performance_metrics;

-- Slowest conversions
SELECT group_id, duration_sec, throughput_mbps
FROM performance_metrics
ORDER BY duration_sec DESC
LIMIT 10;

-- Conversion throughput by group size
SELECT n_subbands,
       AVG(duration_sec) as avg_duration,
       AVG(throughput_mbps) as avg_throughput
FROM performance_metrics
GROUP BY n_subbands;
```

---

## Python Access Examples

### Using Ingest Queue

```python
from pathlib import Path
from dsa110_contimg.database.products import ensure_ingest_db

# Open database
conn = ensure_ingest_db(Path("state/ingest.sqlite3"))

# Add file to queue
conn.execute("""
    INSERT OR IGNORE INTO ingest_queue
    (group_id, state, received_at, last_update, expected_subbands)
    VALUES (?, 'collecting', ?, ?, 16)
""", (group_id, time.time(), time.time()))

# Register subband file
conn.execute("""
    INSERT OR REPLACE INTO subband_files
    (group_id, subband_idx, path)
    VALUES (?, ?, ?)
""", (group_id, subband_idx, file_path))

conn.commit()
conn.close()
```

### Check Queue Status

```python
import sqlite3

conn = sqlite3.connect("state/ingest.sqlite3")
conn.row_factory = sqlite3.Row

# Get pending groups
cursor = conn.cursor()
cursor.execute("""
    SELECT q.group_id, q.received_at, COUNT(s.subband_idx) as n_subbands
    FROM ingest_queue q
    LEFT JOIN subband_files s ON q.group_id = s.group_id
    WHERE q.state='pending'
    GROUP BY q.group_id
""")

for row in cursor.fetchall():
    print(f"{row['group_id']}: {row['n_subbands']} subbands")

conn.close()
```

### Update Pointing

```python
from dsa110_contimg.database.products import ensure_ingest_db

conn = ensure_ingest_db(Path("state/ingest.sqlite3"))

# Record pointing
conn.execute("""
    INSERT OR REPLACE INTO pointing_history
    (timestamp, ra_deg, dec_deg)
    VALUES (?, ?, ?)
""", (timestamp, ra_deg, dec_deg))

conn.commit()
conn.close()
```

---

## Workflow Integration

### 1. File Arrival

```python
# When HDF5 file arrives
group_id = parse_group_id(filename)
subband_idx = parse_subband_idx(filename)

# Create/update queue entry
conn.execute("""
    INSERT OR IGNORE INTO ingest_queue
    (group_id, state, received_at, last_update, expected_subbands)
    VALUES (?, 'collecting', ?, ?, 16)
""", (group_id, time.time(), time.time()))

# Register file
conn.execute("""
    INSERT OR REPLACE INTO subband_files
    (group_id, subband_idx, path)
    VALUES (?, ?, ?)
""", (group_id, subband_idx, file_path))

conn.commit()
```

### 2. Group Completion Check

```python
# Check if group is ready
cursor.execute("""
    SELECT COUNT(*) as n_subbands
    FROM subband_files
    WHERE group_id=?
""", (group_id,))

n_subbands = cursor.fetchone()[0]

if n_subbands >= 12:  # Accept semi-complete groups
    # Mark as pending
    conn.execute("""
        UPDATE ingest_queue
        SET state='pending', processing_stage='queued'
        WHERE group_id=?
    """, (group_id,))
    conn.commit()
```

### 3. Conversion Processing

```python
# Start conversion
conn.execute("""
    UPDATE ingest_queue
    SET state='processing',
        processing_stage='converting',
        last_update=?
    WHERE group_id=?
""", (time.time(), group_id))
conn.commit()

# ... conversion happens ...

# Mark complete
conn.execute("""
    UPDATE ingest_queue
    SET state='completed',
        processing_stage='done',
        last_update=?
    WHERE group_id=?
""", (time.time(), group_id))
conn.commit()
```

### 4. Error Handling

```python
# On conversion failure
conn.execute("""
    UPDATE ingest_queue
    SET state='failed',
        error_message=?,
        retry_count=retry_count+1,
        last_update=?
    WHERE group_id=?
""", (error_msg, time.time(), group_id))
conn.commit()
```

---

## Maintenance Queries

### Retry Failed Conversions

```sql
-- Reset failed groups for retry (if retry_count < 3)
UPDATE ingest_queue
SET state='pending',
    processing_stage='queued',
    retry_count=retry_count+1
WHERE state='failed'
  AND retry_count < 3;
```

### Clean Up Old Entries

```sql
-- Remove completed groups older than 30 days
DELETE FROM ingest_queue
WHERE state='completed'
  AND last_update < (strftime('%s','now') - 30*86400);

-- Clean up orphaned subband entries
DELETE FROM subband_files
WHERE group_id NOT IN (SELECT group_id FROM ingest_queue);
```

### Database Statistics

```sql
-- Queue statistics
SELECT
    COUNT(*) as total_groups,
    SUM(CASE WHEN state='pending' THEN 1 ELSE 0 END) as pending,
    SUM(CASE WHEN state='processing' THEN 1 ELSE 0 END) as processing,
    SUM(CASE WHEN state='completed' THEN 1 ELSE 0 END) as completed,
    SUM(CASE WHEN state='failed' THEN 1 ELSE 0 END) as failed
FROM ingest_queue;

-- Subband file count
SELECT COUNT(*) as total_files,
       COUNT(DISTINCT group_id) as n_groups
FROM subband_files;
```

---

## CLI Commands

### List Queue Status

```bash
# Show queue statistics
sqlite3 state/ingest.sqlite3 \
  "SELECT state, COUNT(*) FROM ingest_queue GROUP BY state"
```

### Retry Failed Group

```bash
# Reset failed group
sqlite3 state/ingest.sqlite3 \
  "UPDATE ingest_queue SET state='pending', retry_count=retry_count+1
   WHERE group_id='2025-11-18T12:00:00'"
```

---

## Performance Notes

- **WAL Mode**: Enabled for concurrent access
- **Indexes**: Optimized for time-based queries
- **Typical Size**: <1 MB for active queue
- **Query Speed**: <10ms for queue status checks

---

## Related Files

- **Code**: `dsa110_contimg/database/products.py` (`ensure_ingest_db`)
- **Conversion**: `dsa110_contimg/conversion/streaming/streaming_converter.py`
- **Pointing**: `dsa110_contimg/pointing/monitor.py`

---

## See Also

- **HDF5 Index**: `docs/reference/database_hdf5_sqlite3.md`
- **Products Database**: `docs/reference/database_products_sqlite3.md`
- **Conversion Guide**: `dsa110_contimg/conversion/README.md`
