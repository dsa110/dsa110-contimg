# Placeholder HDF5 Files: Integration Guide

**Date:** 2025-11-19  
**Type:** How-To Guide  
**Status:** ✅ Complete

---

## Overview

Placeholder HDF5 files are synthetic zero-filled files that replace missing
subbands in incomplete observation groups. This allows the pipeline to process
observations even when some subbands failed to be recorded.

---

## How Placeholders Work

### The Problem

DSA-110 observations require **16 subbands** (sb00-sb15) to form a complete
group. However, hardware failures or data transmission issues can result in
missing subbands. Without placeholders, entire observation groups would be
rejected.

### The Solution

Placeholder files:

- Are stored in `/data/incoming/placeholders/`
- Match the structure of real subband files
- Contain only zeros in visibility data
- Have all data flagged as bad
- Are marked with `IS_PLACEHOLDER: True` metadata

### Integration Architecture

```
/data/incoming/
├── 2025-10-18T15:01:20_sb00.hdf5  ← Real file (139 MB)
├── placeholders/
│   ├── 2025-10-18T15:01:20_sb01.hdf5  ← Placeholder (92 MB)
│   ├── 2025-10-18T15:01:20_sb02.hdf5  ← Placeholder (92 MB)
│   ├── ...
│   └── 2025-10-18T15:01:20_sb15.hdf5  ← Placeholder (92 MB)
```

The conversion process combines both real files and placeholders to form
complete 16-subband groups.

---

## Critical: Indexing Required

**Placeholders MUST be indexed in the database to be used.**

The HDF5 indexing process:

1. Recursively scans `/data/incoming/` (including `placeholders/` subdirectory)
2. Parses filename metadata (timestamp, subband code)
3. Inserts records into `state/hdf5.sqlite3`
4. Enables database queries to discover complete groups

**Without indexing:**

- Placeholders exist on disk but are invisible to the pipeline
- Database queries only return real files
- Groups appear incomplete (e.g., 1/16 subbands instead of 16/16)
- Conversion fails due to missing subbands

**After indexing:**

- Placeholders are visible to the pipeline
- Database queries return both real and placeholder files
- Groups are complete (16/16 subbands)
- Conversion succeeds with flagged placeholder data

---

## Generating Placeholders

### Automatic Generation

Generate placeholders for ALL incomplete groups:

```bash
# Scan database and create all needed placeholders
python -m dsa110_contimg.simulation.create_placeholder_hdf5 batch \
  --hdf5-db /data/dsa110-contimg/state/hdf5.sqlite3 \
  --output-dir /data/incoming/placeholders \
  --tolerance 60.0 \
  --dry-run  # Remove this flag to actually create files
```

**Output:**

```
Incomplete groups found: 228
Placeholders needed: 3,652
Placeholders created: 3,652
Storage used: 327,168 MB
```

### Manual Generation (Single File)

Create a placeholder for a specific subband:

```bash
python -m dsa110_contimg.simulation.create_placeholder_hdf5 single \
  --reference /data/incoming/2025-10-18T15:01:20_sb00.hdf5 \
  --output /data/incoming/placeholders/2025-10-18T15:01:20_sb01.hdf5 \
  --subband-code sb01 \
  --subband-num 1
```

---

## Indexing Placeholders

### Full Index Scan

Index all HDF5 files (including placeholders):

```bash
# Full scan of /data/incoming/ directory
python -m dsa110_contimg.database.cli index-hdf5 \
  --input-dir /data/incoming/ \
  --db /data/dsa110-contimg/state/hdf5.sqlite3
```

This will:

- Scan `/data/incoming/` recursively (finds `placeholders/` subdirectory)
- Parse all `*_sb*.hdf5` files
- Insert new records into database
- Update existing records if files changed

**Expected result:**

```
Scanned: 84,016 files (80,364 existing + 3,652 new placeholders)
Indexed: 3,652 new files
Updated: 0 existing files
Duration: ~2-3 minutes
```

### Incremental Index

Index only new files (faster):

```bash
# Only index files not already in database
python -m dsa110_contimg.database.cli index-hdf5 \
  --input-dir /data/incoming/ \
  --db /data/dsa110-contimg/state/hdf5.sqlite3 \
  --incremental
```

---

## Verifying Integration

### Check Database Records

Verify placeholders are indexed:

```bash
sqlite3 /data/dsa110-contimg/state/hdf5.sqlite3 \
  "SELECT COUNT(*) FROM hdf5_file_index WHERE path LIKE '%placeholders%'"
```

**Expected:** 3,652 (or the number of placeholder files you created)

### Check Complete Groups

Verify incomplete groups now appear complete:

```bash
sqlite3 /data/dsa110-contimg/state/hdf5.sqlite3 "
SELECT group_id, COUNT(*) as subband_count
FROM hdf5_file_index
GROUP BY group_id
HAVING subband_count = 16
LIMIT 20"
```

**Before indexing placeholders:**

```
2025-10-18T15:01:20|1   ← Only 1 subband (sb00)
```

**After indexing placeholders:**

```
2025-10-18T15:01:20|16  ← Complete group (1 real + 15 placeholders)
```

### Verify Placeholder Metadata

Check that placeholders are properly marked:

```bash
python3 -c "
from pyuvdata import UVData
uv = UVData()
uv.read('/data/incoming/placeholders/2025-10-18T15:01:20_sb01.hdf5',
        file_type='uvh5', run_check=False)
print('IS_PLACEHOLDER:', uv.extra_keywords.get('IS_PLACEHOLDER'))
print('All data flagged:', uv.flag_array.all())
print('All data zeros:', (uv.data_array == 0).all())
"
```

**Expected output:**

```
IS_PLACEHOLDER: True
All data flagged: True
All data zeros: True
```

---

## Conversion Workflow

Once placeholders are indexed, the conversion process automatically integrates
them:

1. **Query Database:**
   - `query_subband_groups()` finds all groups with 12-16 subbands
   - Returns list of 16 file paths (real + placeholders)

2. **Identify Placeholders:**
   - Files in `/data/incoming/placeholders/` are recognized as synthetic
   - Metadata `IS_PLACEHOLDER: True` confirms synthetic status

3. **Convert to MS:**
   - All 16 files (real + placeholders) are converted to Measurement Set
   - Placeholder data is fully flagged
   - Real data is processed normally

4. **Calibration/Imaging:**
   - Flagged data (placeholders) is excluded from calibration
   - Only real data contributes to images
   - Missing subbands appear as data gaps (no bad data in images)

---

## Storage Considerations

### Disk Usage

- **Each placeholder:** ~92 MB (zero-filled, compressed)
- **3,652 placeholders:** 327 GB total
- **Location:** `/data/incoming/placeholders/`

### Retention Policy

Placeholders should follow the same retention policy as real HDF5 files:

- **Keep until converted:** Needed for MS conversion
- **Delete after conversion:** Once MS is created, placeholders no longer needed
- **Regenerate if needed:** Can be recreated from database records

**Cleanup after conversion:**

```bash
# Find placeholders for converted groups
sqlite3 /data/dsa110-contimg/state/hdf5.sqlite3 "
SELECT DISTINCT h.path
FROM hdf5_file_index h
JOIN ms_index m ON h.group_id = m.group_id
WHERE h.path LIKE '%placeholders%'
" | xargs rm -f
```

---

## Troubleshooting

### Placeholders Not Found During Conversion

**Symptom:** Conversion fails with "incomplete group" errors despite
placeholders existing on disk

**Cause:** Placeholders not indexed in database

**Solution:**

```bash
# Index placeholders
python -m dsa110_contimg.database.cli index-hdf5 \
  --input-dir /data/incoming/ \
  --db /data/dsa110-contimg/state/hdf5.sqlite3
```

### Too Many Placeholders Generated

**Symptom:** Hundreds of GB of placeholders created

**Cause:** Many incomplete observation groups

**Impact Analysis:**

```bash
# Count incomplete groups
sqlite3 /data/dsa110-contimg/state/hdf5.sqlite3 "
SELECT COUNT(DISTINCT group_id)
FROM (
  SELECT group_id, COUNT(*) as cnt
  FROM hdf5_file_index
  GROUP BY group_id
  HAVING cnt < 16
)"
```

**Action:** Investigate hardware/transmission issues causing missing subbands

### Database Out of Sync

**Symptom:** Database shows different file count than disk

**Solution:** Re-index from scratch:

```bash
# Clear existing index
sqlite3 /data/dsa110-contimg/state/hdf5.sqlite3 \
  "DELETE FROM hdf5_file_index WHERE path LIKE '%placeholders%'"

# Re-index
python -m dsa110_contimg.database.cli index-hdf5 \
  --input-dir /data/incoming/ \
  --db /data/dsa110-contimg/state/hdf5.sqlite3
```

---

## Summary

**Key Points:**

1. Placeholders are **essential** for processing incomplete observation groups
2. Placeholders **must be indexed** to be discovered by conversion
3. Indexing is **recursive** - automatically finds `placeholders/` subdirectory
4. Placeholders are **fully flagged** - no bad data affects images
5. Storage is **significant** - 327 GB for current placeholder set

**Workflow:**

```
Generate → Index → Convert → Image → Cleanup
```

**Commands:**

```bash
# 1. Generate placeholders
python -m dsa110_contimg.simulation.create_placeholder_hdf5 batch \
  --hdf5-db /data/dsa110-contimg/state/hdf5.sqlite3 \
  --output-dir /data/incoming/placeholders

# 2. Index placeholders
python -m dsa110_contimg.database.cli index-hdf5 \
  --input-dir /data/incoming/ \
  --db /data/dsa110-contimg/state/hdf5.sqlite3

# 3. Verify integration
sqlite3 /data/dsa110-contimg/state/hdf5.sqlite3 \
  "SELECT COUNT(*) FROM hdf5_file_index WHERE path LIKE '%placeholders%'"
```

---

## Related Documentation

- **Placeholder Generation:**
  `src/dsa110_contimg/simulation/create_placeholder_hdf5.py`
- **HDF5 Indexing:** `src/dsa110_contimg/database/hdf5_index.py`
- **Semi-Complete Groups:**
  `src/dsa110_contimg/conversion/SEMI_COMPLETE_SUBBAND_GROUPS.md`
- **Conversion Workflow:** `src/dsa110_contimg/conversion/uvh5_to_ms.py`
