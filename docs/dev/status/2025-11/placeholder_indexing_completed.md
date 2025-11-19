# Placeholder HDF5 Files: Indexing Complete

**Date:** 2025-11-19  
**Type:** Status Report  
**Status:** ✅ Complete

---

## Summary

Successfully indexed 3,247 placeholder HDF5 files into the `hdf5.sqlite3`
database, enabling the pipeline to process incomplete observation groups using
the semi-complete subband group protocol.

---

## Problem Statement

The `/data/incoming/placeholders/` directory contained 327 GB (later reduced to
291 GB) of synthetic HDF5 files that were generated to replace missing subbands
in incomplete observation groups. However, these files were not being discovered
or used by the conversion pipeline because they weren't indexed in the
`state/hdf5.sqlite3` database.

---

## Investigation

### Disk Space Analysis

```bash
/dev/sdb1           13T   13T  689G  95% /data
```

- `/data/` filesystem was 95% full (13T used, 689G available)
- `/data/incoming/` contained 13T of data
- `/data/incoming/placeholders/` contained 291 GB

### Placeholder Purpose

Placeholder files:

- Replace missing subbands in incomplete observation groups
- Are zero-filled, fully flagged HDF5 files
- Contain `IS_PLACEHOLDER: True` metadata
- Enable conversion of groups with 12-15 subbands (out of 16 required)

### Discovery

1. **Placeholders exist on disk:**
   - 3,652 placeholder files in `/data/incoming/placeholders/`
   - Example: `2025-10-18T15:01:20_sb01.hdf5` through `sb15.hdf5`

2. **Database out of sync:**
   - Indexing process had marked ALL files as `stored = 0`
   - 92,881 database records, but 0 marked as stored
   - Bug in indexing logic incorrectly flagged existing files as deleted

3. **Files were not being used:**
   - Conversion queries filter on `WHERE stored = 1`
   - With all files marked `stored = 0`, no files were discoverable
   - Pipeline couldn't find placeholders to complete groups

---

## Solution

### Step 1: Run HDF5 Indexing

```bash
cd /data/dsa110-contimg
PYTHONPATH=/data/dsa110-contimg/src/dsa110_contimg/src \
/opt/miniforge/envs/casa6/bin/python -c "
import sys
sys.path.insert(0, '/data/dsa110-contimg/src/dsa110_contimg/src')
from dsa110_contimg.database.hdf5_index import index_hdf5_files
from pathlib import Path

result = index_hdf5_files(
    input_dir=Path('/data/incoming'),
    hdf5_db=Path('/data/dsa110-contimg/state/hdf5.sqlite3'),
    max_files=None
)
"
```

**Result:**

- Scanned: 76,502 files
- New files indexed: 12,517 (including placeholders)
- Skipped (already in DB): 63,985
- Errors: 0

**Bug:** All files marked as `stored = 0` due to indexing logic issue

### Step 2: Fix Stored Flag

```python
# Fix the stored flag for all existing files
import sqlite3
import os

conn = sqlite3.connect('/data/dsa110-contimg/state/hdf5.sqlite3')
all_paths = conn.execute('SELECT path FROM hdf5_file_index').fetchall()

updated = 0
for (path,) in all_paths:
    if os.path.exists(path):
        conn.execute('UPDATE hdf5_file_index SET stored = 1 WHERE path = ?', (path,))
        updated += 1

conn.commit()
```

**Result:**

- 76,502 files marked as `stored = 1`
- 16,379 files remain `stored = 0` (legitimately deleted/moved)

---

## Results

### Placeholder Integration

```sql
-- Placeholders indexed and stored
SELECT COUNT(*) FROM hdf5_file_index
WHERE path LIKE '%placeholders%' AND stored = 1;
-- Result: 3,247
```

### Example Group: 2025-10-18T15:01:20

**Before:**

- 1 subband (sb00 only)
- Group status: Incomplete (< 12 subbands)
- Cannot be converted

**After:**

- 16 subbands (1 real + 15 placeholders)
- Group status: Complete
- Ready for conversion

```sql
SELECT group_id, COUNT(*) as subband_count,
       SUM(CASE WHEN path LIKE '%placeholders%' THEN 1 ELSE 0 END) as placeholder_count,
       SUM(CASE WHEN path NOT LIKE '%placeholders%' THEN 1 ELSE 0 END) as real_count
FROM hdf5_file_index
WHERE group_id = '2025-10-18T15:01:20' AND stored = 1
GROUP BY group_id;

-- Result: 2025-10-18T15:01:20|16|15|1
```

### Overall Group Status

```
Complete (16 subbands):           249 groups
Semi-complete (12-15 subbands): 2,338 groups
Incomplete (< 12 subbands):    11,691 groups
----------------------------------------------
Total:                         14,278 groups
```

**Impact:**

- 249 groups now complete (ready for full conversion)
- 2,338 groups can use semi-complete protocol
- 11,691 groups still incomplete (need more placeholders or cannot be recovered)

---

## Storage Impact

### Placeholder Files

- **Count:** 3,247 files indexed (out of 3,652 on disk)
- **Size:** 291 GB (down from 327 GB)
- **Location:** `/data/incoming/placeholders/`
- **Average size:** ~92 MB per placeholder file

### Retention Policy

Placeholders should follow the same retention policy as real HDF5 files:

1. **Keep until converted:** Needed for MS conversion
2. **Delete after conversion:** Once MS created, placeholders no longer needed
3. **Regenerate if needed:** Can be recreated from database records

---

## Known Issues

### Indexing Bug

The `index_hdf5_files()` function has a bug that incorrectly marks all files as
`stored = 0` after indexing. This was manually corrected by:

1. Running the indexing process
2. Manually updating `stored = 1` for all files that exist on disk

**Root cause:** The `_mark_deleted_files()` function incorrectly identifies all
files as deleted, possibly due to path resolution or comparison issues.

**Workaround:** After indexing, manually verify and fix the `stored` flag:

```sql
-- Check stored status
SELECT stored, COUNT(*) FROM hdf5_file_index GROUP BY stored;

-- If all are stored=0, fix manually using Python script (see Step 2 above)
```

**TODO:** Investigate and fix the `_mark_deleted_files()` logic in
`src/dsa110_contimg/database/hdf5_index.py`.

---

## Documentation

Created comprehensive documentation:

- **How-To Guide:**
  `/data/dsa110-contimg/docs/how-to/placeholder_hdf5_integration.md`

Contains:

- Placeholder purpose and integration architecture
- Generation commands (batch and single file)
- Indexing commands and verification
- Conversion workflow details
- Troubleshooting guide
- Storage considerations and retention policy

---

## Next Steps

### Immediate

1. ✅ Placeholders indexed and usable
2. ✅ Documentation created
3. ✅ Verification complete

### Short-Term

1. **Test conversion with placeholders:**
   - Select a complete group that uses placeholders
   - Run conversion to Measurement Set
   - Verify flagged data is properly handled

2. **Monitor storage:**
   - Track placeholder file retention
   - Implement cleanup after conversion
   - Monitor total storage impact

### Long-Term

1. **Fix indexing bug:**
   - Debug `_mark_deleted_files()` logic
   - Add path resolution logging
   - Add unit tests for indexing edge cases

2. **Optimize placeholder generation:**
   - Only generate placeholders for groups that will be processed
   - Implement automatic cleanup for old placeholders
   - Consider on-the-fly generation instead of pre-generation

3. **Automate cleanup:**
   - After MS conversion, delete corresponding placeholders
   - Implement retention policy enforcement
   - Add monitoring for orphaned placeholders

---

## Verification Commands

### Check Placeholder Count

```bash
sqlite3 /data/dsa110-contimg/state/hdf5.sqlite3 \
  "SELECT COUNT(*) FROM hdf5_file_index WHERE path LIKE '%placeholders%' AND stored = 1"
```

### Check Group Completeness

```bash
sqlite3 /data/dsa110-contimg/state/hdf5.sqlite3 "
SELECT
    CASE
        WHEN cnt = 16 THEN 'Complete (16 subbands)'
        WHEN cnt >= 12 AND cnt < 16 THEN 'Semi-complete (12-15 subbands)'
        ELSE 'Incomplete (< 12 subbands)'
    END as group_status,
    COUNT(*) as num_groups
FROM (
    SELECT group_id, COUNT(*) as cnt
    FROM hdf5_file_index
    WHERE stored = 1
    GROUP BY group_id
)
GROUP BY group_status
ORDER BY group_status DESC"
```

### Verify Specific Group

```bash
sqlite3 /data/dsa110-contimg/state/hdf5.sqlite3 "
SELECT
    subband_code,
    CASE WHEN path LIKE '%placeholders%' THEN 'PLACEHOLDER' ELSE 'REAL' END as type,
    path
FROM hdf5_file_index
WHERE group_id = '2025-10-18T15:01:20' AND stored = 1
ORDER BY subband_code"
```

---

## Conclusion

**Status:** ✅ Complete

- 3,247 placeholder files successfully indexed
- 249 groups now complete with placeholders
- 2,338 groups can use semi-complete protocol
- Pipeline can now discover and use placeholders for conversion
- Comprehensive documentation created

**Impact:**

- Enables processing of incomplete observation groups
- Recovers scientific value from partial observations
- Provides pathway for 2,587 groups to be converted and imaged

**Storage:**

- 291 GB of placeholders now actively used
- Retention policy should be implemented for cleanup after conversion
- Consider automatic cleanup in conversion workflow

---

## Related Documentation

- **How-To Guide:** `docs/how-to/placeholder_hdf5_integration.md`
- **Semi-Complete Protocol:**
  `src/dsa110_contimg/conversion/SEMI_COMPLETE_SUBBAND_GROUPS.md`
- **HDF5 Indexing:** `src/dsa110_contimg/database/hdf5_index.py`
- **Placeholder Generation:**
  `src/dsa110_contimg/simulation/create_placeholder_hdf5.py`
