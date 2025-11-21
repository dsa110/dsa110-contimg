# Piecewise Mosaic Testing Strategy

## Overview

The mosaic build process is complex with multiple interdependent stages. To
enable efficient debugging, we've created a piecewise testing script that
isolates each stage.

## Test Script

**Location:** `scripts/test_mosaic_piecewise.py`

**Usage:**

```bash
cd /data/dsa110-contimg
env PYTHONPATH=/data/dsa110-contimg/src MOSAIC_CACHE_DIR=/tmp/mosaic_cache \
  /opt/miniforge/envs/casa6/bin/python scripts/test_mosaic_piecewise.py \
  --tiles <tile1> <tile2> ... \
  --test <test_number|all>
```

## Test Stages

### Test 0: WCS Metadata Extraction

**Purpose:** Verify that WCS metadata can be extracted from FITS files via the
cache.

**What it tests:**

- Cache-based WCS metadata extraction
- Handling of `coordinates()` vs `coordsys()` objects
- Scalar value extraction from arrays

**Example:**

```bash
--test 0 --tiles /path/to/tile.fits
```

### Test 1: Coordinate Extraction

**Purpose:** Verify direct coordinate system access from a single tile.

**What it tests:**

- `coordsys()` vs `coordinates()` fallback
- `referencevalue()` vs `get_referencevalue()` fallback
- `increment()` vs `get_increment()` fallback
- Image closing (or lack thereof for FITS files)

**Example:**

```bash
--test 1 --tiles /path/to/tile.fits
```

### Test 2: Bounding Box Calculation

**Purpose:** Verify that bounding boxes can be calculated from all tiles.

**What it tests:**

- `_calculate_mosaic_bounds()` function
- astropy WCS extraction (with `.celestial` for 4D images)
- CASA fallback coordinate extraction
- RA/Dec range calculation

**Example:**

```bash
--test 2 --tiles /path/to/tile1.fits /path/to/tile2.fits ...
```

### Test 3: Common Coordinate System Creation

**Purpose:** Validate bounds and calculate expected output shape.

**What it tests:**

- Bounds validation
- Expected output shape calculation
- Pixel scale handling

**Note:** Full coordinate system creation requires complex CASA API usage and is
tested in the full build.

**Example:**

```bash
--test 3 --tiles /path/to/tile1.fits ... --pixel-scale 2.0
```

### Test 4: Single Tile Regridding

**Purpose:** Test regridding a single tile to a template image.

**What it tests:**

- `imregrid` functionality
- Template image creation
- Output shape matching

**Example:**

```bash
--test 4 --tiles /path/to/tile.fits --template /path/to/template.image
```

## Benefits

1. **Isolated Debugging:** Each test focuses on one specific functionality
2. **Fast Iteration:** Failed tests can be rerun quickly without rebuilding
   everything
3. **Clear Error Messages:** Failures are immediately localized to specific
   stages
4. **Progressive Validation:** Tests build on each other, catching issues early

## Workflow

1. **Start with Test 0:** Verify basic WCS extraction works
2. **Test 1:** Verify coordinate system access
3. **Test 2:** Verify bounding box calculation
4. **Test 3:** Validate bounds (coordinate system creation tested in full build)
5. **Test 4:** Test regridding (if template available)
6. **Full Build:** Once all piecewise tests pass, run full mosaic build

## Integration with Full Build

The piecewise tests validate the same functions used in the full mosaic build:

- `_calculate_mosaic_bounds()` - Test 2
- `_create_common_coordinate_system()` - Test 3 (bounds validation)
- `imregrid()` - Test 4

Once piecewise tests pass, the full build should work, with any remaining issues
likely in:

- PB image handling
- Weight calculation
- Mosaic combination logic
- Output image creation

## Example Full Test Run

```bash
# Test all stages
cd /data/dsa110-contimg
env PYTHONPATH=/data/dsa110-contimg/src MOSAIC_CACHE_DIR=/tmp/mosaic_cache \
  /opt/miniforge/envs/casa6/bin/python scripts/test_mosaic_piecewise.py \
  --tiles \
    /stage/dsa110-contimg/images/2025-10-28T13:30:07.img-image-pb.fits \
    /stage/dsa110-contimg/images/2025-10-28T13:35:16.img-image-pb.fits \
    /stage/dsa110-contimg/images/2025-10-28T13:40:25.img-image-pb.fits \
    /stage/dsa110-contimg/images/2025-10-28T13:45:34.img-image-pb.fits \
    /stage/dsa110-contimg/images/2025-10-28T13:50:44.img-image-pb.fits \
  --test all \
  --pixel-scale 2.0
```

## Troubleshooting

### Test 0/1 Failures

- Check that FITS files are readable
- Verify casa6 environment is active
- Check cache directory permissions

### Test 2 Failures

- Verify all tiles have valid WCS headers
- Check for 4D vs 2D WCS issues (should be handled by `.celestial`)
- Verify astropy is available

### Test 3 Failures

- Usually indicates invalid bounds from Test 2
- Check pixel scale is reasonable (typically 1-5 arcsec)

### Test 4 Failures

- Requires a template image
- Check `imregrid` is available
- Verify template and source have compatible coordinate systems
