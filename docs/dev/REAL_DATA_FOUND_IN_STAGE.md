# Real Data Found in /stage/

**Date:** 2025-01-XX  
**Location:** `/stage/dsa110-contimg/`  
**Status:** ✅ Found real observational data tiles

---

## Summary

Found **10+ PB-corrected tiles** in `/stage/dsa110-contimg/images/` with corresponding MS files in `/stage/dsa110-contimg/ms/science/`. These are **real observational data** from October 2025.

---

## Real Data Tiles Found

### Location
- **Images:** `/stage/dsa110-contimg/images/`
- **MS files:** `/stage/dsa110-contimg/ms/science/YYYY-MM-DD/`
- **Naming pattern:** `YYYY-MM-DDTHH:MM:SS.img-image-pb.fits` (PB-corrected)

### Tiles from 2025-10-28

1. **2025-10-28T13:30:07.img-image-pb.fits**
   - Path: `/stage/dsa110-contimg/images/2025-10-28T13:30:07.img-image-pb.fits`
   - Size: ~152 MB
   - MS: `/stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T13:30:07.ms` ✓
   - Status: ✅ Real data

2. **2025-10-28T13:35:16.img-image-pb.fits**
   - Path: `/stage/dsa110-contimg/images/2025-10-28T13:35:16.img-image-pb.fits`
   - Size: ~152 MB
   - MS: `/stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T13:35:16.ms` ✓
   - Status: ✅ Real data

3. **2025-10-28T13:40:25.img-image-pb.fits**
   - Path: `/stage/dsa110-contimg/images/2025-10-28T13:40:25.img-image-pb.fits`
   - Size: ~152 MB
   - MS: `/stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T13:40:25.ms` ✓
   - Status: ✅ Real data

4. **2025-10-28T13:45:34.img-image-pb.fits**
   - Path: `/stage/dsa110-contimg/images/2025-10-28T13:45:34.img-image-pb.fits`
   - Size: ~152 MB
   - MS: `/stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T13:45:34.ms` ✓
   - Status: ✅ Real data

5. **2025-10-28T13:50:44.img-image-pb.fits**
   - Path: `/stage/dsa110-contimg/images/2025-10-28T13:50:44.img-image-pb.fits`
   - Size: ~152 MB
   - MS: `/stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T13:50:44.ms` ✓
   - Status: ✅ Real data

6. **2025-10-28T13:55:53.img-image-pb.fits**
   - Path: `/stage/dsa110-contimg/images/2025-10-28T13:55:53.img-image-pb.fits`
   - Size: ~152 MB
   - MS: `/stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T13:55:53.fast.ms` ✓
   - Status: ✅ Real data

7. **2025-10-28T14:01:02.img-image-pb.fits**
   - Path: `/stage/dsa110-contimg/images/2025-10-28T14:01:02.img-image-pb.fits`
   - Size: ~152 MB
   - MS: `/stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T14:01:02.ms` ✓
   - Status: ✅ Real data

8. **2025-10-28T14:06:11.img-image-pb.fits**
   - Path: `/stage/dsa110-contimg/images/2025-10-28T14:06:11.img-image-pb.fits`
   - Size: ~152 MB
   - MS: `/stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T14:06:11.ms` ✓
   - Status: ✅ Real data

9. **2025-10-28T14:11:20.img-image-pb.fits**
   - Path: `/stage/dsa110-contimg/images/2025-10-28T14:11:20.img-image-pb.fits`
   - Size: ~152 MB
   - MS: `/stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T14:11:20.ms` ✓
   - Status: ✅ Real data

10. **2025-10-28T14:16:30.img-image-pb.fits**
    - Path: `/stage/dsa110-contimg/images/2025-10-28T14:16:30.img-image-pb.fits`
    - Size: ~152 MB
    - MS: `/stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T14:16:30.ms` ✓
    - Status: ✅ Real data

---

## Evidence These Are Real Data

1. ✅ **MS files exist**: All tiles have corresponding MS files on disk
2. ✅ **Realistic dates**: October 2025 (past date, not future)
3. ✅ **Consistent timestamps**: Filenames match MS file timestamps
4. ✅ **File sizes**: ~152 MB per tile (realistic for radio astronomy images)
5. ✅ **Chronological order**: Tiles are in 5-minute intervals (13:30, 13:35, etc.)

---

## Primary Beam Files

**Note:** PB files may use different naming conventions. Need to verify:
- Pattern might be: `YYYY-MM-DDTHH:MM:SS.img-pb.fits`
- Or embedded in the image-pb.fits filename itself

---

## Usage for Testing

These tiles can be used to test the VAST-like mosaicking implementation:

```bash
# Example: Plan a mosaic with real data tiles
dsa110-contimg mosaic plan \
    --products-db /data/dsa110-contimg/state/products.sqlite3 \
    --name test_real_data_mosaic \
    --method weighted

# Note: Tiles need to be registered in products database first
# Or use direct paths if CLI supports it
```

---

## Registry Issue

**Problem:** These tiles are NOT registered in the products database (`/data/dsa110-contimg/state/products.sqlite3`).

**Solution:** Need to register these tiles in the database before using them for mosaicking, OR update the mosaicking code to work with direct file paths.

---

## Next Steps

1. ✅ Found real data tiles in `/stage/`
2. ⏳ Register tiles in products database (if needed)
3. ⏳ Verify PB file locations/names
4. ⏳ Test VAST-like mosaicking with real data

---

**Last Updated:** 2025-01-XX

