# Registry Updated with Real Data

**Date:** 2025-11-12  
**Action:** Registered 10 real observational data tiles from `/stage/` into products database

---

## Summary

Successfully registered **10 PB-corrected tiles** from `/stage/dsa110-contimg/images/` into the products database (`/data/dsa110-contimg/state/products.sqlite3`).

---

## Registered Tiles

All tiles are from **2025-10-28** and have:
- ✅ PB-corrected images (`*image-pb.fits`)
- ✅ Existing MS files in `/stage/dsa110-contimg/ms/science/2025-10-28/`
- ✅ Proper timestamps
- ✅ Registered as `type='5min'`, `pbcor=1`, `format='fits'`

### Tile List

1. `2025-10-28T13:30:07.img-image-pb.fits`
2. `2025-10-28T13:35:16.img-image-pb.fits`
3. `2025-10-28T13:40:25.img-image-pb.fits`
4. `2025-10-28T13:45:34.img-image-pb.fits`
5. `2025-10-28T13:50:44.img-image-pb.fits`
6. `2025-10-28T13:55:53.img-image-pb.fits`
7. `2025-10-28T14:01:02.img-image-pb.fits`
8. `2025-10-28T14:06:11.img-image-pb.fits`
9. `2025-10-28T14:11:20.img-image-pb.fits`
10. `2025-10-28T14:16:30.img-image-pb.fits`

---

## Database Status

**Before:**
- Real data tiles in database: 0
- Synthetic tiles flagged: 5

**After:**
- Real data tiles in database: 10
- Synthetic tiles flagged: 5
- Total PB-corrected tiles: 15 (10 real + 5 synthetic)

---

## Query for Real Data

To find real data tiles (excluding synthetic):

```sql
SELECT i.path, i.ms_path, i.pbcor, i.type
FROM images i
LEFT JOIN data_tags dt ON dt.data_id = CAST(i.id AS TEXT)
WHERE i.pbcor = 1
  AND i.ms_path IS NOT NULL
  AND (dt.tag IS NULL OR dt.tag != 'synthetic')
ORDER BY i.created_at DESC;
```

---

## Usage

These tiles can now be used for testing the VAST-like mosaicking implementation:

```bash
# Plan a mosaic with real data
dsa110-contimg mosaic plan \
    --products-db /data/dsa110-contimg/state/products.sqlite3 \
    --name test_real_data_mosaic \
    --method weighted

# Build the mosaic
dsa110-contimg mosaic build \
    --products-db /data/dsa110-contimg/state/products.sqlite3 \
    --name test_real_data_mosaic \
    --output /stage/dsa110-contimg/mosaics/test_real_data.fits
```

---

## Notes

- All tiles are from the same date (2025-10-28)
- Tiles are in chronological order (5-minute intervals)
- MS files exist and are verified
- Images are PB-corrected (ready for mosaicking)
- Synthetic tiles remain flagged and excluded from real data queries

---

**Last Updated:** 2025-11-12

