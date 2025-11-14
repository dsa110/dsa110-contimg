# Synthetic Tiles Flagged in Database

**Date:** 2025-11-12  
**Action:** Explicitly flagged synthetic/test tiles in products database

---

## Summary

The following tiles in `/data/dsa110-contimg/state/products.sqlite3` have been flagged as **synthetic/test data** using the `data_tags` table:

1. `2025-01-15T12:00:00.img.image.pbcor.fits`
2. `2025-01-15T12:05:00.img.image.pbcor.fits`
3. `2025-01-15T12:10:00.img.image.pbcor.fits`
4. `2025-01-15T12:15:00.img.image.pbcor.fits`
5. `2025-01-15T12:20:00.img.image.pbcor.fits`

---

## Evidence These Are Synthetic

1. **Missing MS files**: All referenced MS files don't exist on disk
2. **Future creation timestamps**: Created on 2025-11-06 (future date)
3. **Date mismatch**: Filenames say 2025-01-15, but created timestamp is 2025-11-06
4. **No real observational data**: No images found with existing MS files in main database

---

## Database Tagging

These tiles are now tagged in the `data_tags` table with:
- `tag = "synthetic"`
- Linked via `data_id` to the image `id`

**Query to find synthetic tiles:**
```sql
SELECT i.path, i.type, i.created_at
FROM images i
JOIN data_tags dt ON dt.data_id = CAST(i.id AS TEXT)
WHERE dt.tag = 'synthetic' AND i.pbcor = 1
```

---

## Real Data Status

**Main database (`/data/dsa110-contimg/state/products.sqlite3`):**
- Found **0** images with existing MS files (real data)

**Scratch database (`/scratch/dsa110-contimg/state/products.sqlite3`):**
- Found **48** images with MS paths
- Need to verify which have existing MS files and are PB-corrected

---

## Recommendation

**For testing mosaicking:**
- ❌ Do NOT use the flagged synthetic tiles
- ✅ Use only tiles with:
  - Existing MS files on disk
  - Valid timestamps (not future dates)
  - Proper date alignment between filename and creation time

**Next steps:**
1. Query scratch database for real PB-corrected tiles
2. Verify MS files exist for those tiles
3. Use those for testing the VAST-like mosaicking implementation

---

**Last Updated:** 2025-11-12

