# Mosaic Creation Issues Analysis

## Date: 2025-01-XX

## Summary

After fixing the chronological ordering issue, a comprehensive analysis of the mosaic creation code revealed several additional issues that could cause mosaic artifacts, incorrect coordinate systems, and database inconsistencies.

## Issues Identified

### 1. Reference Coordinate System Inconsistency (CRITICAL)

**Location**: `src/dsa110_contimg/mosaic/cli.py:532-549`

**Problem**:
- The reference coordinate system (`ref_coordsys`) is taken from the **first PB image** (`pb_paths[0]`)
- However, when regridding PB images that don't match the reference, the template is selected as:
  - `tiles[0]` if it's a directory (CASA format)
  - `pb_paths[0]` otherwise
- This creates an inconsistency: if `tiles[0]` has a different coordinate system than `pb_paths[0]`, regridded PB images will have the wrong coordinate system

**Impact**:
- Mosaic coordinate system may not match the chronologically first tile
- Regridded PB images may have incorrect WCS information
- Can cause astrometric errors in the final mosaic

**Fix Required**:
- Always use `pb_paths[0]` (the reference PB image) as the template for regridding PB images
- Ensure the reference coordinate system matches the chronologically first tile's coordinate system

### 2. Image Path Construction Issue

**Location**: `src/dsa110_contimg/mosaic/streaming_mosaic.py:1428-1440`

**Problem**:
- Code constructs image paths assuming `imagename` from `ms_index` is a base path:
  ```python
  pbcor_fits = f"{row[0]}-image-pb.fits"  # WSClean format
  pbcor = f"{row[0]}.pbcor"  # CASA format
  image = f"{row[0]}.image"  # CASA format
  ```
- However, `imagename` may already be:
  - A full path (e.g., `/path/to/image.image`)
  - A path with extensions already included
  - A different format than expected

**Impact**:
- Image lookup may fail even when images exist
- Mosaic creation may skip valid images
- Could cause "Only N images found, need 10" warnings

**Fix Required**:
- Check if `imagename` already includes extensions
- Handle both base paths and full paths correctly
- Try multiple path construction strategies

### 3. Database Consistency Issue

**Location**: Multiple (migration vs. registration)

**Problem**:
- Images are registered in the `images` table via `images_insert()`
- Migration script renames `images` → `images_all`
- If images are registered after migration, they may be in `images` but not `images_all`
- Earlier investigation showed no images in `images_all` table within mosaic time range

**Impact**:
- Queries against `images_all` may miss recently registered images
- Mosaic planning may not find available tiles
- Database queries may return inconsistent results

**Fix Required**:
- Ensure all image registration uses the correct table name (`images_all` if migration has run)
- Add migration check before inserting images
- Consider using a view or unified query function

### 4. PB Regridding Template Selection

**Location**: `src/dsa110_contimg/mosaic/cli.py:547-549`

**Problem**:
- When regridding PB images, template selection logic:
  ```python
  template_img = tiles[0] if os.path.isdir(tiles[0]) else None
  template = template_img or str(pb_paths[0])
  ```
- This prefers `tiles[0]` over `pb_paths[0]` if `tiles[0]` is a directory
- But `ref_coordsys` comes from `pb_paths[0]`, creating inconsistency

**Impact**:
- Regridded PB images may not match the reference coordinate system
- Can cause pixel misalignment in mosaic combination

**Fix Required**:
- Always use `pb_paths[0]` as the template for PB regridding
- Ensure consistency with reference coordinate system

### 5. NaN Threshold Strictness

**Location**: `src/dsa110_contimg/mosaic/cli.py:843`

**Problem**:
- Pixels with `total_weight < 1e-10` are set to NaN
- This threshold may be too strict for edge pixels with low but valid PB response
- Could contribute to the 41.2% NaN pixels observed in the problematic mosaic

**Impact**:
- Valid pixels at mosaic edges may be incorrectly set to NaN
- Mosaic coverage may be artificially reduced

**Fix Required**:
- Consider using a more lenient threshold (e.g., `1e-12` or relative threshold)
- Log statistics about NaN pixel distribution
- Consider using a relative threshold based on maximum weight

## Recommended Fix Priority

1. **HIGH**: Reference coordinate system consistency (#1, #4)
2. **MEDIUM**: Image path construction (#2)
3. **MEDIUM**: Database consistency (#3)
4. **LOW**: NaN threshold (#5)

## Testing Recommendations

After fixes:
1. Verify reference coordinate system matches chronologically first tile
2. Test image path lookup with various `imagename` formats
3. Verify database queries return consistent results
4. Check NaN pixel percentage in test mosaics
5. Validate mosaic astrometry against catalog sources

