# How to Populate `pipeline.sqlite3`

**Status**: The unified pipeline database (`pipeline.sqlite3`) is currently empty. This guide shows how to start populating it with calibration provenance data.

## Quick Diagnosis

**Check if database is empty**:

```bash
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 << 'EOF'
SELECT 'Calibration tables:', COUNT(*) FROM caltables;
SELECT 'MS files:', COUNT(*) FROM ms_index;
SELECT 'Images:', COUNT(*) FROM images;
SELECT 'Photometry:', COUNT(*) FROM photometry;
EOF
```

**Expected output for empty database**:

```
Calibration tables:|0
MS files:|0
Images:|0
Photometry:|0
```

---

## Why Is the Database Empty?

The database exists with all schemas defined, but is not being populated because:

1. **No pipeline runs yet**: No calibration, imaging, or photometry has been executed through the pipeline
2. **Manual calibration**: Direct CASA calls bypass provenance tracking
3. **Legacy code paths**: Old scripts don't use the unified database

---

## How Provenance Tracking Works

The pipeline **automatically** records calibration provenance when you use these functions:

```python
from dsa110_contimg.calibration.calibration import (
    solve_delay,        # K-type delay calibration
    solve_bandpass,     # B-type bandpass calibration
    solve_gains,        # G-type gain calibration
    apply_calibration   # Apply caltables to MS
)
```

Each function calls `_track_calibration_provenance()` which writes to `pipeline.sqlite3::caltables`.

**Verified in code**: `backend/src/dsa110_contimg/calibration/calibration.py` lines 295-360

---

## Method 1: Run Calibration Through Pipeline (Recommended)

### Prerequisites

```bash
# 1. Activate CASA environment
conda activate casa6

# 2. Verify database is initialized
python -c "from dsa110_contimg.database.unified import init_unified_db; init_unified_db()"

# 3. Check you have MS files
ls -lh /stage/dsa110-contimg/ms/*.ms 2>/dev/null || echo "No MS files found"
```

### Option A: Use Python API

```python
from pathlib import Path
from dsa110_contimg.calibration.calibration import (
    solve_bandpass,
    solve_gains,
    apply_calibration
)

# Path to your measurement set
ms_path = '/stage/dsa110-contimg/ms/observation.ms'

# Calibrate using field 0 (or appropriate calibrator field)
# This AUTOMATICALLY populates pipeline.sqlite3
bp_tables = solve_bandpass(
    ms=ms_path,
    cal_field='0',
    refant='3',
    combine_spw=True,
    combine_fields=False,
    solint='inf',
    table_prefix=None  # Auto-generates: {ms_path}.B
)

gain_tables = solve_gains(
    ms=ms_path,
    cal_field='0',
    refant='3',
    bptables=bp_tables,
    solint='int',
    table_prefix=None  # Auto-generates: {ms_path}.G
)

# Apply calibration
apply_calibration(
    ms=ms_path,
    gaintables=bp_tables + gain_tables,
    fields='all'
)

print(f"✓ Created {len(bp_tables)} bandpass + {len(gain_tables)} gain tables")
print("✓ Provenance automatically recorded in pipeline.sqlite3")
```

### Option B: Use Calibration CLI

```bash
conda activate casa6

# Full calibration workflow (auto-populates database)
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /stage/dsa110-contimg/ms/observation.ms \
  --calibrator "3C286" \
  --field 12 \
  --refant 3

# Or manual bandpass + gains
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /stage/dsa110-contimg/ms/observation.ms \
  --field 0 \
  --refant 3 \
  --solint-bp "inf" \
  --solint-gp "int"
```

### Verify Population

```python
from dsa110_contimg.database.unified import Database

db = Database()
caltables = db.query("SELECT path, table_type, source_ms_path FROM caltables ORDER BY created_at DESC LIMIT 10")

print(f"✓ Found {len(caltables)} calibration tables in database:")
for ct in caltables:
    print(f"  {ct['table_type']}: {Path(ct['path']).name}")
    print(f"    → Source MS: {ct['source_ms_path']}")
```

---

## Method 2: Register Existing Calibration Tables

If you have **pre-existing calibration tables** that were created before provenance tracking:

```python
from pathlib import Path
from dsa110_contimg.database.unified import register_caltable_set_from_prefix

# Example: You have these existing files:
# /stage/caltables/obs1_field0.B
# /stage/caltables/obs1_field0.G

result = register_caltable_set_from_prefix(
    db_path='/data/dsa110-contimg/state/db/pipeline.sqlite3',
    set_name='obs1_field0_20251205',  # Unique identifier
    prefix=Path('/stage/caltables/obs1_field0'),
    cal_field='0',
    refant='3',
    valid_start_mjd=60000.5,  # MJD validity range
    valid_end_mjd=60000.7,
    status='active'
)

print(f"✓ Registered {len(result)} existing calibration tables")
for caltable in result:
    print(f"  {caltable.table_type}: {caltable.path}")
```

**Bulk registration example**:

```python
from pathlib import Path
from dsa110_contimg.database.unified import register_caltable_set_from_prefix

# Find all calibration sets in a directory
cal_dir = Path('/stage/dsa110-contimg/caltables')
prefixes = set(f.stem.rsplit('.', 1)[0] for f in cal_dir.glob('*.B'))

for prefix_str in sorted(prefixes):
    prefix = cal_dir / prefix_str
    try:
        result = register_caltable_set_from_prefix(
            db_path='/data/dsa110-contimg/state/db/pipeline.sqlite3',
            set_name=f"{prefix.name}_backfill",
            prefix=prefix,
            cal_field='0',  # Adjust based on your data
            refant='3',
            valid_start_mjd=60000.0,
            valid_end_mjd=60001.0,
            status='active'
        )
        print(f"✓ Registered {len(result)} tables for {prefix.name}")
    except Exception as e:
        print(f"✗ Failed {prefix.name}: {e}")
```

---

## Method 3: Backfill from Real Data

If you have **existing MS files** with embedded caltables, extract and register them:

```python
from pathlib import Path
from casacore import tables
from dsa110_contimg.database.unified import Database

def find_caltables_in_ms(ms_path):
    """Find all caltables referenced in MS HISTORY."""
    with tables.table(f"{ms_path}/HISTORY", readonly=True, ack=False) as tb:
        messages = tb.getcol("MESSAGE")
        app_params = tb.getcol("APP_PARAMS")

    caltables = set()
    for msg, params in zip(messages, app_params):
        # Look for applycal, bandpass, gaincal commands
        if any(x in msg.lower() for x in ['applycal', 'bandpass', 'gaincal']):
            # Extract caltable paths from parameters
            for param in params:
                if 'caltable=' in param or 'gaintable=' in param:
                    # Parse out the path
                    caltable = param.split('=')[1].strip("'\"")
                    if Path(caltable).exists():
                        caltables.add(caltable)

    return list(caltables)

# Usage
ms_files = Path('/stage/dsa110-contimg/ms').glob('*.ms')
for ms_path in ms_files:
    caltables = find_caltables_in_ms(str(ms_path))
    print(f"{ms_path.name}: {len(caltables)} caltables found")
    # Register each using Method 2
```

---

## Verification

### Check Database Contents

```bash
# Count entries by type
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 << 'EOF'
SELECT table_type, COUNT(*) as count
FROM caltables
GROUP BY table_type
ORDER BY table_type;
EOF
```

**Expected output after calibration**:

```
B|1    (bandpass)
G|1    (gains)
```

### Show Recent Calibrations

```python
from dsa110_contimg.database.unified import Database
import time

db = Database()

# Get last 24 hours of activity
recent = db.query("""
    SELECT path, table_type, source_ms_path, created_at
    FROM caltables
    WHERE created_at > ?
    ORDER BY created_at DESC
""", (time.time() - 86400,))

print(f"Calibration activity (last 24h): {len(recent)} tables")
for r in recent:
    age_min = (time.time() - r['created_at']) / 60
    print(f"  {r['table_type']}: {Path(r['path']).name} ({age_min:.0f}m ago)")
```

---

## Common Issues

### Issue 1: Database File Not Found

```bash
# Create database if missing
python -c "from dsa110_contimg.database.unified import init_unified_db; init_unified_db()"
```

### Issue 2: Permission Denied

```bash
# Fix permissions
sudo chown -R $USER:$USER /data/dsa110-contimg/state/db
chmod 755 /data/dsa110-contimg/state/db
chmod 644 /data/dsa110-contimg/state/db/pipeline.sqlite3
```

### Issue 3: Provenance Not Recording

**Symptom**: You run calibration but database stays empty

**Diagnosis**:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run calibration - you should see provenance logs
from dsa110_contimg.calibration.calibration import solve_bandpass
# ... run calibration ...
# Look for: "DEBUG:dsa110_contimg.database.provenance: ..."
```

**Common causes**:

- Using direct CASA calls instead of pipeline functions
- Environment variable `PIPELINE_DB` pointing to wrong location
- Import errors in provenance module

### Issue 4: No MS Files to Calibrate

If you don't have real data yet, follow the tutorial to convert UVH5 files:

```bash
# Check for raw HDF5 data
sqlite3 /data/incoming/hdf5_file_index.sqlite3 \
  "SELECT COUNT(*) FROM hdf5_file_index"

# If data exists, convert to MS
python -m dsa110_contimg.execution.cli convert \
  --input-dir /data/incoming \
  --output-dir /stage/dsa110-contimg/ms \
  --start-time "2025-11-18T00:00:00" \
  --end-time "2025-11-18T01:00:00"
```

---

## Testing Script

Save this as `test_database_population.py`:

```python
#!/usr/bin/env python3
"""Test that pipeline.sqlite3 is being populated correctly."""

from pathlib import Path
from dsa110_contimg.database.unified import Database, get_pipeline_db_path

def test_population():
    db_path = get_pipeline_db_path()
    print(f"Testing database: {db_path}")

    if not Path(db_path).exists():
        print("✗ Database file does not exist")
        print(f"  Run: python -c 'from dsa110_contimg.database.unified import init_unified_db; init_unified_db()'")
        return False

    db = Database()

    # Check tables
    tables = db.query("SELECT name FROM sqlite_master WHERE type='table'")
    print(f"✓ Found {len(tables)} tables")

    # Check data
    counts = {
        'caltables': db.query_val("SELECT COUNT(*) FROM caltables"),
        'ms_index': db.query_val("SELECT COUNT(*) FROM ms_index"),
        'images': db.query_val("SELECT COUNT(*) FROM images"),
        'photometry': db.query_val("SELECT COUNT(*) FROM photometry"),
    }

    for table, count in counts.items():
        status = "✓" if count > 0 else "⚠"
        print(f"{status} {table}: {count} entries")

    if counts['caltables'] == 0:
        print("\n⚠ Database is empty. To populate:")
        print("  1. Run calibration with pipeline functions (see guide)")
        print("  2. Register existing caltables with register_caltable_set_from_prefix()")

    return True

if __name__ == '__main__':
    test_population()
```

Run with:

```bash
conda activate casa6
python test_database_population.py
```

---

## Summary

**To populate `pipeline.sqlite3`**:

1. **Use pipeline calibration functions** - They automatically track provenance:

   ```python
   from dsa110_contimg.calibration.calibration import solve_bandpass, solve_gains
   bp_tables = solve_bandpass(ms='data.ms', ...)  # ← Writes to database
   ```

2. **Or use the CLI**:

   ```bash
   python -m dsa110_contimg.calibration.cli calibrate --ms data.ms ...
   ```

3. **For existing tables**, register them:
   ```python
   from dsa110_contimg.database.unified import register_caltable_set_from_prefix
   register_caltable_set_from_prefix(prefix=Path('old_cal'), ...)
   ```

**Do NOT** call CASA directly (`gaincal()`, `bandpass()`) - use the pipeline wrappers which add provenance tracking.

The database will automatically populate once you start using the pipeline's calibration workflow.
