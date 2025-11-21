# Database Reference: cal_registry.sqlite3

**Location**: `/data/dsa110-contimg/state/cal_registry.sqlite3`  
**Purpose**: Registry of calibration tables with validity windows  
**Size**: ~24 KB (typical)

---

## Overview

The `cal_registry.sqlite3` database tracks all generated calibration tables (K,
BP, GP, 2G) with their validity time windows. Workers query this registry to
find active calibration solutions for a given observation time, ensuring
consistent calibration across the pipeline.

---

## Table: `caltables`

**Purpose**: Track calibration table files and their validity windows

**Schema**:

```sql
CREATE TABLE caltables (
    id INTEGER PRIMARY KEY,
    set_name TEXT NOT NULL,              -- Logical set/group name
    path TEXT NOT NULL UNIQUE,           -- Filesystem path to cal table
    table_type TEXT NOT NULL,            -- K, BA, BP, GA, GP, 2G, FLUX
    order_index INTEGER NOT NULL,        -- Apply order within set
    cal_field TEXT,                      -- Source/field used to solve
    refant TEXT,                         -- Reference antenna
    created_at REAL NOT NULL,            -- time.time() when registered
    valid_start_mjd REAL,                -- Start of validity window (MJD)
    valid_end_mjd REAL,                  -- End of validity window (MJD)
    status TEXT NOT NULL,                -- active|retired|failed
    notes TEXT,                          -- Free-form notes
    source_ms_path TEXT,                 -- Input MS that generated this
    solver_command TEXT,                 -- Full CASA command executed
    solver_version TEXT,                 -- CASA version used
    solver_params TEXT,                  -- JSON: calibration parameters
    quality_metrics TEXT                 -- JSON: SNR, flagged_fraction, etc.
);

CREATE INDEX idx_caltables_set ON caltables(set_name);
CREATE INDEX idx_caltables_valid ON caltables(valid_start_mjd, valid_end_mjd);
CREATE INDEX idx_caltables_source ON caltables(source_ms_path);
```

---

## Calibration Table Types

| Type   | Description        | Apply Order  | Frequency       |
| ------ | ------------------ | ------------ | --------------- |
| `K`    | Delay (K-cal)      | 1 (first)    | Per observation |
| `BA`   | Bandpass amplitude | 2            | Every 24 hours  |
| `BP`   | Bandpass phase     | 2            | Every 24 hours  |
| `GA`   | Gain amplitude     | 3            | Every hour      |
| `GP`   | Gain phase         | 3            | Every hour      |
| `2G`   | 2nd-order gain     | 4 (last)     | Every hour      |
| `FLUX` | Flux scale         | 5 (optional) | Per observation |

---

## Status Values

- `active` - Available for use
- `retired` - Superseded by newer solution
- `failed` - Quality checks failed

---

## Common Queries

### Find Active Calibration Tables for Time Window

```sql
-- Get all active tables valid at a specific MJD
SELECT set_name, table_type, path, order_index
FROM caltables
WHERE status='active'
  AND valid_start_mjd <= 59000.5
  AND (valid_end_mjd IS NULL OR valid_end_mjd >= 59000.5)
ORDER BY order_index;
```

### Get Ordered Apply List

```sql
-- Get tables to apply for a given time (ordered)
SELECT path, table_type
FROM caltables
WHERE status='active'
  AND set_name='bp_20251118'
ORDER BY order_index;
```

### Find Bandpass Solutions

```sql
-- List all active bandpass calibrations
SELECT set_name, path, cal_field, refant,
       valid_start_mjd, valid_end_mjd
FROM caltables
WHERE table_type IN ('BP', 'BA')
  AND status='active'
ORDER BY valid_start_mjd DESC;
```

### Find Gain Solutions

```sql
-- Recent gain calibrations
SELECT set_name, path, cal_field,
       valid_start_mjd, valid_end_mjd
FROM caltables
WHERE table_type IN ('GP', 'GA', '2G')
  AND status='active'
ORDER BY created_at DESC
LIMIT 10;
```

### Check Table Quality

```sql
-- Get quality metrics for a table
SELECT path, quality_metrics, notes
FROM caltables
WHERE set_name='bp_20251118';
```

### List Tables by Calibrator

```sql
-- Find tables solved from specific calibrator
SELECT set_name, table_type, path, valid_start_mjd
FROM caltables
WHERE cal_field='0834+555'
  AND status='active';
```

### Find Expired Tables

```sql
-- Tables that are no longer valid
SELECT set_name, path, valid_end_mjd
FROM caltables
WHERE valid_end_mjd < (SELECT julianday('now') - 2400000.5)
  AND status='active';
```

---

## Maintenance Queries

### Retire Old Table

```sql
-- Mark table as retired
UPDATE caltables
SET status='retired', notes='Superseded by bp_20251119'
WHERE set_name='bp_20251118';
```

### Register New Calibration Set

```sql
-- Register bandpass table
INSERT INTO caltables (
    set_name, path, table_type, order_index,
    cal_field, refant, created_at,
    valid_start_mjd, valid_end_mjd, status
) VALUES (
    'bp_20251118',
    '/stage/caltables/bp_20251118.bcal',
    'BP', 2,
    '0834+555', 'ea01', 1731964800.0,
    59000.0, 59001.0, 'active'
);

-- Register gain table
INSERT INTO caltables (
    set_name, path, table_type, order_index,
    cal_field, refant, created_at,
    valid_start_mjd, valid_end_mjd, status
) VALUES (
    'gain_20251118_12h',
    '/stage/caltables/gain_20251118_12h.gcal',
    'GP', 3,
    '0834+555', 'ea01', 1731964800.0,
    59000.5, 59000.54, 'active'
);
```

### Cleanup Failed Tables

```sql
-- Remove failed calibration attempts
DELETE FROM caltables
WHERE status='failed'
  AND created_at < (strftime('%s','now') - 7*86400);
```

---

## Python Access Examples

### Using Registry Module

```python
from pathlib import Path
from dsa110_contimg.database.registry import (
    ensure_cal_registry_db,
    register_caltable,
    get_active_applylist,
    retire_caltable
)

# Open registry
conn = ensure_cal_registry_db(Path("state/cal_registry.sqlite3"))

# Register a new calibration table
register_caltable(
    conn,
    set_name="bp_20251118",
    path="/stage/caltables/bp_20251118.bcal",
    table_type="BP",
    order_index=2,
    cal_field="0834+555",
    refant="ea01",
    valid_start_mjd=59000.0,
    valid_end_mjd=59001.0,
    status="active"
)

# Get active tables for observation time
tables = get_active_applylist(conn, mjd=59000.5)
for table in tables:
    print(f"{table['type']}: {table['path']}")

# Retire old table
retire_caltable(conn, set_name="bp_20251117")

conn.close()
```

### Direct SQL Access

```python
import sqlite3
from pathlib import Path

conn = sqlite3.connect("state/cal_registry.sqlite3")
conn.row_factory = sqlite3.Row

# Find active calibrations
cursor = conn.cursor()
cursor.execute("""
    SELECT path, table_type, cal_field
    FROM caltables
    WHERE status='active'
      AND valid_start_mjd <= ?
      AND (valid_end_mjd IS NULL OR valid_end_mjd >= ?)
    ORDER BY order_index
""", (59000.5, 59000.5))

for row in cursor.fetchall():
    print(f"{row['table_type']}: {row['path']}")

conn.close()
```

---

## Validity Window Guidelines

### Bandpass Calibration

- **Duration**: 24 hours (86400 seconds)
- **Update Frequency**: Once per day
- **Trigger**: Pointing declination change >1-2 degrees

```python
# Example validity window for bandpass
start_mjd = 59000.0  # 2025-11-18 00:00 UTC
end_mjd = 59001.0    # 2025-11-19 00:00 UTC (24 hours later)
```

### Gain Calibration

- **Duration**: 1 hour (3600 seconds)
- **Update Frequency**: Hourly
- **Trigger**: Atmospheric conditions, time variability

```python
# Example validity window for gains
start_mjd = 59000.5      # 2025-11-18 12:00 UTC
end_mjd = 59000.541667   # 2025-11-18 13:00 UTC (1 hour later)
```

---

## Workflow Integration

### 1. Calibration Solving

```python
# After solving calibration
from dsa110_contimg.database.registry import register_caltable

# Register bandpass
register_caltable(
    conn,
    set_name=f"bp_{obs_date}",
    path=bp_table_path,
    table_type="BP",
    order_index=2,
    cal_field=calibrator_name,
    valid_start_mjd=obs_start_mjd,
    valid_end_mjd=obs_start_mjd + 1.0,  # 24 hours
    status="active"
)
```

### 2. Calibration Application

```python
# Before applying calibration
from dsa110_contimg.database.registry import get_active_applylist

# Get tables to apply
tables = get_active_applylist(conn, mjd=target_mjd)

# Apply in order
for table in tables:
    apply_caltable(ms_path, table['path'])
```

### 3. Calibration Validation

```python
# After validation
if qa_passed:
    # Keep as active
    pass
else:
    # Mark as failed
    retire_caltable(conn, set_name=set_name, status="failed")
```

---

## CLI Commands

### List Active Tables

```bash
# Using calibration CLI
python -m dsa110_contimg.calibration.cli list-tables \
  --cal-registry-db state/cal_registry.sqlite3
```

### Register Table from CLI

```bash
python -m dsa110_contimg.calibration.cli register-table \
  --cal-registry-db state/cal_registry.sqlite3 \
  --set-name bp_20251118 \
  --path /stage/caltables/bp_20251118.bcal \
  --table-type BP \
  --cal-field 0834+555 \
  --valid-start 59000.0 \
  --valid-end 59001.0
```

### Retire Table

```bash
python -m dsa110_contimg.calibration.cli retire-table \
  --cal-registry-db state/cal_registry.sqlite3 \
  --set-name bp_20251117
```

---

## Performance Notes

- **Indexes**: Optimized for time-window queries
- **Typical Size**: <100 KB with months of calibrations
- **Query Speed**: <10ms for active table lookup
- **Concurrency**: WAL mode not needed (mostly read operations)

---

## Related Files

- **Code**: `dsa110_contimg/database/registry.py`
- **CLI**: `dsa110_contimg/calibration/cli.py`
- **Streaming**: `dsa110_contimg/calibration/streaming.py`

---

## See Also

- **Calibration Guide**: `dsa110_contimg/calibration/README.md`
- **Products Database**: `docs/reference/database_products_sqlite3.md`
- **Calibrators Database**: `docs/reference/database_calibrators_sqlite3.md`
