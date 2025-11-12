# Real Tiles Found in Registry for Testing

**Date:** 2025-11-12  
**Purpose:** Document real tiles available for testing the new VAST-like mosaicking implementation

---

## Summary

Found **5 PB-corrected tiles** in the products database (`/data/dsa110-contimg/state/products.sqlite3`), all of which exist on disk and can be used for testing.

---

## Tiles Found

### Location
All tiles are stored in: `/data/dsa110-contimg/state/images/`

### Tile List

1. **2025-01-15T12:00:00.img.image.pbcor.fits**
   - Path: `/data/dsa110-contimg/state/images/2025-01-15T12:00:00.img.image.pbcor.fits`
   - Size: 2.01 MB
   - Noise: 1.000e-03 Jy
   - Beam: 12.50" × 0.00"
   - Status: ✓ Exists on disk

2. **2025-01-15T12:05:00.img.image.pbcor.fits**
   - Path: `/data/dsa110-contimg/state/images/2025-01-15T12:05:00.img.image.pbcor.fits`
   - Size: 2.01 MB
   - Noise: 1.200e-03 Jy
   - Beam: 12.80" × 0.00"
   - Status: ✓ Exists on disk

3. **2025-01-15T12:10:00.img.image.pbcor.fits**
   - Path: `/data/dsa110-contimg/state/images/2025-01-15T12:10:00.img.image.pbcor.fits`
   - Size: 2.01 MB
   - Noise: 9.000e-04 Jy
   - Beam: 12.30" × 0.00"
   - Status: ✓ Exists on disk

4. **2025-01-15T12:15:00.img.image.pbcor.fits**
   - Path: `/data/dsa110-contimg/state/images/2025-01-15T12:15:00.img.image.pbcor.fits`
   - Size: 2.01 MB
   - Noise: 1.100e-03 Jy
   - Beam: 12.60" × 0.00"
   - Status: ✓ Exists on disk

5. **2025-01-15T12:20:00.img.image.pbcor.fits**
   - Path: `/data/dsa110-contimg/state/images/2025-01-15T12:20:00.img.image.pbcor.fits`
   - Size: 2.01 MB
   - Noise: 1.000e-03 Jy
   - Beam: 12.40" × 0.00"
   - Status: ✓ Exists on disk

---

## Primary Beam Images

**Note:** Primary beam images have a different naming pattern than expected.

- **PB file pattern:** `YYYY-MM-DDTHH:MM:SS.img.pb.fits` (no `.image` in name)
- **PB-corrected pattern:** `YYYY-MM-DDTHH:MM:SS.img.image.pbcor.fits`

**Found PB file:**
- `/data/dsa110-contimg/state/images/2025-01-15T12:00:00.img.pb.fits` ✓ Exists

**Missing PB files:** The other 4 tiles don't have corresponding PB files in the expected location. The mosaicking implementation will fall back to noise-weighted combination if PB images are not available.

---

## Testing Recommendations

### 1. Test with Available Tiles

```bash
# Plan a mosaic with the 5 tiles
dsa110-contimg mosaic plan \
    --products-db /data/dsa110-contimg/state/products.sqlite3 \
    --name test_vast_like_mosaic \
    --method weighted

# Build the mosaic
dsa110-contimg mosaic build \
    --products-db /data/dsa110-contimg/state/products.sqlite3 \
    --name test_vast_like_mosaic \
    --output /data/dsa110-contimg/state/mosaics/test_vast_like.fits
```

### 2. Expected Behavior

Since only 1 PB file exists, the implementation should:
- Use PB-weighted combination for tile 1 (if PB path can be found)
- Fall back to noise-weighted combination for tiles 2-5
- Still produce a valid mosaic

### 3. Validation

After building, verify:
- Mosaic file exists and is readable
- Coordinate system is correct
- Flux scaling is reasonable
- No artifacts from mixing weighting schemes

---

## Database Query

To find more tiles in the future:

```python
import sqlite3
from pathlib import Path

db_path = Path("/data/dsa110-contimg/state/products.sqlite3")
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row

cursor = conn.execute("""
    SELECT path, created_at, pbcor, noise_jy
    FROM images
    WHERE pbcor = 1
    ORDER BY created_at DESC
    LIMIT 10
""")

rows = cursor.fetchall()
for row in rows:
    path = Path(row['path'])
    if path.exists():
        print(f"{path} (noise: {row['noise_jy']:.6e} Jy)")
```

---

## Notes

- All tiles are from the same date (2025-01-15) and time range (12:00-12:20)
- Tiles are in chronological order (good for mosaicking)
- Noise values are similar (~1 mJy), which is good for testing
- Beam sizes are consistent (~12-13 arcsec)
- Only 1 PB file exists, so full PB-weighted testing will require more PB files

---

**Last Updated:** 2025-11-12

