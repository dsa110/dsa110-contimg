# Image Metadata Not Populated

**Date:** 2025-11-12  
**Severity:** HIGH  
**Status:** Open

## Issue

Database query shows all images have `noise_jy`, `center_ra_deg`,
`center_dec_deg` set to NULL.

## Impact

- **Noise filtering will not work** (filters nothing - all noise_jy are null)
- **Declination filtering requires reading FITS files** (slow, inefficient)
- **Performance degraded** for spatial queries
- **User experience** - filters appear broken

## Root Cause

Image creation code is not populating these columns during insertion.

### Current Insertion Code

**Location:** `src/dsa110_contimg/database/products.py:468`

```python
def insert_image(
    conn,
    path: str,
    ms_path: str,
    created_at: float,
    img_type: str,
    pbcor: int,
    *,
    beam_major_arcsec: Optional[float] = None,
    noise_jy: Optional[float] = None,
) -> None:
    """Insert an image artifact record."""
    conn.execute(
        "INSERT INTO images(path, ms_path, created_at, type, beam_major_arcsec, noise_jy, pbcor) "
        "VALUES(?,?,?,?,?,?,?)",
        (
            path,
            ms_path,
            created_at,
            img_type,
            beam_major_arcsec,  # Optional, defaults to None
            noise_jy,           # Optional, defaults to None
            pbcor,
        ),
    )
```

**Problem:** Function accepts `noise_jy` and `beam_major_arcsec` as optional
parameters, but callers are not extracting and passing these values.

### Missing Metadata

1. **`noise_jy`** - Image noise level (Jy)
   - Should be extracted from image statistics
   - Currently: Always NULL

2. **`center_ra_deg`** - Image center right ascension (degrees)
   - Should be extracted from FITS header WCS
   - Currently: Always NULL (not even in INSERT statement)

3. **`center_dec_deg`** - Image center declination (degrees)
   - Should be extracted from FITS header WCS
   - Currently: Always NULL (not even in INSERT statement)

4. **`beam_major_arcsec`** - Beam major axis (arcseconds)
   - Should be extracted from FITS header
   - Currently: Optional, often NULL

5. **`beam_minor_arcsec`** - Beam minor axis (arcseconds)
   - Should be extracted from FITS header
   - Currently: Not in INSERT statement

6. **`beam_pa_deg`** - Beam position angle (degrees)
   - Should be extracted from FITS header
   - Currently: Not in INSERT statement

## Database Schema

**Location:** `src/dsa110_contimg/database/products.py`

```python
CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL,
    ms_path TEXT NOT NULL,
    created_at REAL NOT NULL,
    type TEXT NOT NULL,
    beam_major_arcsec REAL,
    noise_jy REAL,
    pbcor INTEGER DEFAULT 0
)
```

**Note:** Schema does NOT include `center_ra_deg` or `center_dec_deg` columns,
but API response model (`ImageInfo`) expects them.

## Solution

### Step 1: Update Database Schema

Add missing columns to `images` table:

```sql
ALTER TABLE images ADD COLUMN center_ra_deg REAL;
ALTER TABLE images ADD COLUMN center_dec_deg REAL;
ALTER TABLE images ADD COLUMN beam_minor_arcsec REAL;
ALTER TABLE images ADD COLUMN beam_pa_deg REAL;
```

### Step 2: Update Insert Function

**File:** `src/dsa110_contimg/database/products.py`

```python
def insert_image(
    conn,
    path: str,
    ms_path: str,
    created_at: float,
    img_type: str,
    pbcor: int,
    *,
    beam_major_arcsec: Optional[float] = None,
    beam_minor_arcsec: Optional[float] = None,
    beam_pa_deg: Optional[float] = None,
    noise_jy: Optional[float] = None,
    center_ra_deg: Optional[float] = None,
    center_dec_deg: Optional[float] = None,
) -> None:
    """Insert an image artifact record."""
    conn.execute(
        """INSERT INTO images(
            path, ms_path, created_at, type,
            beam_major_arcsec, beam_minor_arcsec, beam_pa_deg,
            noise_jy, center_ra_deg, center_dec_deg, pbcor
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (
            path,
            ms_path,
            created_at,
            img_type,
            beam_major_arcsec,
            beam_minor_arcsec,
            beam_pa_deg,
            noise_jy,
            center_ra_deg,
            center_dec_deg,
            pbcor,
        ),
    )
```

### Step 3: Extract Metadata During Image Creation

**Location:** Where images are created (likely `src/dsa110_contimg/imaging/` or
`src/dsa110_contimg/pipeline/stages_impl.py`)

Create helper function to extract metadata from FITS:

```python
from astropy.io import fits
from astropy.wcs import WCS
from pathlib import Path

def extract_image_metadata(fits_path: str) -> dict:
    """Extract metadata from FITS file header.

    Returns:
        dict with keys: noise_jy, center_ra_deg, center_dec_deg,
                       beam_major_arcsec, beam_minor_arcsec, beam_pa_deg
    """
    metadata = {
        'noise_jy': None,
        'center_ra_deg': None,
        'center_dec_deg': None,
        'beam_major_arcsec': None,
        'beam_minor_arcsec': None,
        'beam_pa_deg': None,
    }

    if not Path(fits_path).exists():
        return metadata

    try:
        with fits.open(fits_path) as hdul:
            hdr = hdul[0].header

            # Extract WCS coordinates
            try:
                wcs = WCS(hdr)
                if wcs.has_celestial:
                    center_pix = [hdr.get('NAXIS1', 0) / 2, hdr.get('NAXIS2', 0) / 2]
                    if hdr.get('NAXIS', 0) >= 2:
                        ra, dec = wcs.all_pix2world(center_pix[0], center_pix[1], 0)
                        metadata['center_ra_deg'] = float(ra)
                        metadata['center_dec_deg'] = float(dec)
            except Exception:
                pass

            # Extract beam parameters
            if 'BMAJ' in hdr:
                metadata['beam_major_arcsec'] = float(hdr['BMAJ'] * 3600)  # Convert deg to arcsec
            if 'BMIN' in hdr:
                metadata['beam_minor_arcsec'] = float(hdr['BMIN'] * 3600)
            if 'BPA' in hdr:
                metadata['beam_pa_deg'] = float(hdr['BPA'])

            # Extract noise (if available in header)
            # Note: May need to compute from image data if not in header
            if 'NOISE' in hdr:
                metadata['noise_jy'] = float(hdr['NOISE'])
            elif 'RMS' in hdr:
                metadata['noise_jy'] = float(hdr['RMS'])
    except Exception:
        pass

    return metadata
```

### Step 4: Update Image Creation Code

Find where `insert_image` is called and extract metadata before insertion:

```python
# Example (location TBD)
from dsa110_contimg.database.products import insert_image, extract_image_metadata

# After image is created
fits_path = get_fits_path(image_path)  # Get FITS file path
metadata = extract_image_metadata(fits_path)

insert_image(
    conn,
    path=image_path,
    ms_path=ms_path,
    created_at=timestamp,
    img_type=img_type,
    pbcor=pbcor,
    beam_major_arcsec=metadata['beam_major_arcsec'],
    beam_minor_arcsec=metadata['beam_minor_arcsec'],
    beam_pa_deg=metadata['beam_pa_deg'],
    noise_jy=metadata['noise_jy'],
    center_ra_deg=metadata['center_ra_deg'],
    center_dec_deg=metadata['center_dec_deg'],
)
```

### Step 5: Backfill Existing Images

Create migration script to populate existing images:

```python
# scripts/backfill_image_metadata.py
from pathlib import Path
from dsa110_contimg.database.products import ensure_products_db, extract_image_metadata
from dsa110_contimg.api.image_utils import get_fits_path

def backfill_metadata():
    db_path = Path("/data/dsa110-contimg/state/products.sqlite3")
    with ensure_products_db(db_path) as conn:
        # Get all images without metadata
        rows = conn.execute("""
            SELECT id, path FROM images
            WHERE center_ra_deg IS NULL OR noise_jy IS NULL
        """).fetchall()

        for row in rows:
            fits_path = get_fits_path(row['path'])
            metadata = extract_image_metadata(fits_path)

            conn.execute("""
                UPDATE images SET
                    center_ra_deg = ?,
                    center_dec_deg = ?,
                    noise_jy = ?,
                    beam_major_arcsec = ?,
                    beam_minor_arcsec = ?,
                    beam_pa_deg = ?
                WHERE id = ?
            """, (
                metadata['center_ra_deg'],
                metadata['center_dec_deg'],
                metadata['noise_jy'],
                metadata['beam_major_arcsec'],
                metadata['beam_minor_arcsec'],
                metadata['beam_pa_deg'],
                row['id'],
            ))

        conn.commit()
        print(f"Updated {len(rows)} images")
```

## Testing

After implementing:

1. **Verify new images have metadata:**

   ```bash
   curl "http://localhost:8000/api/images?limit=1" | jq '.items[0] | {noise_jy, center_ra_deg, center_dec_deg}'
   ```

2. **Test noise filtering:**

   ```bash
   curl "http://localhost:8000/api/images?noise_max=0.001&limit=5"
   # Should return filtered results
   ```

3. **Test declination filtering:**
   ```bash
   curl "http://localhost:8000/api/images?dec_min=40&dec_max=50&limit=5"
   # Should be fast (SQL-level) instead of slow (FITS reading)
   ```

## Priority

**HIGH** - Affects core filter functionality

## Related Files

- `src/dsa110_contimg/database/products.py` - Database schema and insertion
- `src/dsa110_contimg/api/routers/images.py` - API endpoint (currently does
  post-filtering)
- `src/dsa110_contimg/imaging/` - Image creation code (location TBD)
- `src/dsa110_contimg/pipeline/stages_impl.py` - Pipeline stages (may create
  images)

## Workaround

Current implementation uses post-filtering (reading FITS files) for declination
filtering, which is slow but functional. Noise filtering will not work until
metadata is populated.

---

**Created:** 2025-11-12  
**Assigned to:** [TBD]  
**Estimated Effort:** 4-6 hours (schema update + extraction + backfill)
