# Real Data Search Results

**Date:** 2025-11-12  
**Purpose:** Search for real observational data tiles for testing mosaicking

---

## Summary

**No real observational data tiles found** in either database location.

---

## Database Search Results

### Main Database (`/data/dsa110-contimg/state/products.sqlite3`)

- **Total PB-corrected tiles:** 5
- **Tiles with existing MS files:** 0
- **Status:** All 5 tiles are **SYNTHETIC** (explicitly flagged)

**Synthetic tiles flagged:**
1. `2025-01-15T12:00:00.img.image.pbcor.fits` ✓ Tagged as synthetic
2. `2025-01-15T12:05:00.img.image.pbcor.fits` ✓ Tagged as synthetic
3. `2025-01-15T12:10:00.img.image.pbcor.fits` ✓ Tagged as synthetic
4. `2025-01-15T12:15:00.img.image.pbcor.fits` ✓ Tagged as synthetic
5. `2025-01-15T12:20:00.img.image.pbcor.fits` ✓ Tagged as synthetic

**Evidence these are synthetic:**
- MS files don't exist on disk
- Future creation timestamps (2025-11-06)
- Date mismatch between filename and creation time

### Scratch Database (`/scratch/dsa110-contimg/state/products.sqlite3`)

- **Total images:** 48
- **PB-corrected images:** 0
- **Images with MS paths:** 48
- **Images with existing MS files:** 0
- **Status:** No PB-corrected tiles available

---

## Conclusion

**No real observational data tiles are available for testing the VAST-like mosaicking implementation.**

All tiles in the databases are either:
1. Synthetic/test data (explicitly flagged)
2. Not PB-corrected
3. Missing their associated MS files

---

## Recommendations

### For Testing

**Option 1: Generate new real data**
- Process real MS files through the pipeline
- Ensure PB correction is applied
- Register tiles in products database

**Option 2: Use synthetic tiles (with caution)**
- Can test the mosaicking workflow
- Will not reflect real observational conditions
- Useful for code path testing only

**Option 3: Wait for real data**
- Monitor for new tiles from actual observations
- Verify MS files exist before using

### Query to Find Real Data (Future)

```sql
-- Find PB-corrected tiles with existing MS files
SELECT i.path, i.ms_path, i.created_at, i.noise_jy
FROM images i
LEFT JOIN data_tags dt ON dt.data_id = CAST(i.id AS TEXT)
WHERE i.pbcor = 1
  AND i.ms_path IS NOT NULL
  AND (dt.tag IS NULL OR dt.tag != 'synthetic')
ORDER BY i.created_at DESC;
```

Then verify MS files exist:
```python
from pathlib import Path
ms_path = Path(row['ms_path'])
if ms_path.exists():
    # This is real data
    pass
```

---

## Synthetic Tiles Status

All synthetic tiles have been explicitly flagged in the `data_tags` table:
- Tag: `"synthetic"`
- Query: `SELECT * FROM data_tags WHERE tag = 'synthetic'`

**These tiles should NOT be used for production testing or science validation.**

---

**Last Updated:** 2025-11-12

