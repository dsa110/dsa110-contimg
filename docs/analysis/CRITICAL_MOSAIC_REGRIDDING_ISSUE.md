# Critical Mosaic Regridding Issue

## Date: 2025-11-09

## Problem Summary

The mosaic builder is **not regridding tiles to a common coordinate system** before combining them. It assumes all tiles are at the same sky position and on the same pixel grid, which is incorrect.

## Current Behavior

**What the code does:**
1. Reads tiles directly from disk
2. Uses first tile's coordinate system as reference
3. Adds tiles pixel-by-pixel: `mosaic_data += weights * tile_data`
4. Assumes all tiles are aligned

**What actually happens:**
- Tiles are at **different sky positions**:
  - Tile 1: RA=179.999°, Dec=35.001°
  - Tile 2: RA=180.099°, Dec=35.101° (0.1° offset in both RA and Dec)
  - Tile 3: RA=180.199°, Dec=35.201°
  - etc.
- Tiles are **not aligned** - they form diagonal strips, not horizontal strips
- Mosaic shows isolated spots instead of overlapping horizontal strips

## Expected Behavior

**What should happen:**
1. **Calculate bounding box** of all tiles:
   - RA range: min(RA_min) to max(RA_max) across all tiles
   - Dec range: min(Dec_min) to max(Dec_max) across all tiles
   
2. **Create common output coordinate system**:
   - Center: midpoint of bounding box
   - Pixel scale: same as tiles (2 arcsec/pixel)
   - Size: large enough to encompass all tiles
   
3. **Regrid all tiles** to this common coordinate system:
   - Use `imregrid` to resample each tile to the common grid
   - Preserve flux (use appropriate interpolation)
   
4. **Combine regridded tiles**:
   - Now tiles are on the same pixel grid
   - Can combine pixel-by-pixel with proper weighting
   - Result: horizontal strips overlapping in RA

## Code Location

**Current problematic code:**
- `src/dsa110_contimg/mosaic/cli.py:918-930`
- Assumes `tile_data_list[0].shape` applies to all tiles
- No regridding of tiles to common coordinate system

## Impact

- **Mosaics are incorrect**: Tiles not properly aligned
- **Visual appearance**: Isolated spots instead of horizontal strips
- **Astrometry**: Wrong coordinate system in output mosaic
- **Coverage**: Low coverage because tiles aren't overlapping properly

## Required Fix

1. Add function to calculate mosaic bounds from all tiles
2. Create common output coordinate system
3. Regrid all tiles (and PB images) to common coordinate system
4. Then combine regridded tiles

This is a **fundamental architectural issue** that needs to be fixed for mosaics to work correctly.

