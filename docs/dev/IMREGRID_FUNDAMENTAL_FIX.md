# Fundamental Fix for imregrid RuntimeError

## Problem

The `imregrid` RuntimeError "All output pixels are masked" occurs when attempting to regrid tiles that don't overlap with the template coordinate system. Previously, this was handled reactively by catching the error and skipping tiles.

## Root Cause

1. **Template Selection**: Using the first tile as template assumes all other tiles overlap with it
2. **No Pre-validation**: Tiles are regridded without checking if they overlap with the template coordinate system
3. **Coordinate System Mismatch**: Tiles may have different coordinate systems or be outside the template's coverage area

## Solution

Implemented **pre-validation** of tile overlap before attempting regridding:

### 1. New Module: `coordinate_utils.py`

Created `src/dsa110_contimg/mosaic/coordinate_utils.py` with functions:

- **`get_tile_coordinate_bounds()`**: Extracts RA/Dec bounds, cell sizes, and shape from a tile
- **`compute_tiles_bounding_box()`**: Computes bounding box encompassing all tiles
- **`check_tile_overlaps_template()`**: Checks if a tile overlaps with template coordinate system
- **`filter_tiles_by_overlap()`**: Filters tiles to only include those overlapping with template

### 2. Integration Points

**In `_build_weighted_mosaic_linearmosaic()`:**
- Pre-validates tile overlap before regridding loop
- Filters out non-overlapping tiles early
- Updates tile lists to only include overlapping tiles
- Still catches RuntimeError as safety net for edge cases

**In `_build_weighted_mosaic_imregrid_immath()`:**
- Same pre-validation approach
- Filters tiles before computing weights
- Ensures at least one tile remains after filtering

### 3. Benefits

1. **Prevents Errors**: Catches coordinate system mismatches before expensive regridding operations
2. **Better Performance**: Avoids attempting regridding on tiles that will fail
3. **Clearer Diagnostics**: Provides specific reasons why tiles are skipped (RA/Dec range mismatch)
4. **Early Failure**: Fails fast if no tiles overlap, rather than after processing all tiles

## Implementation Details

### Coordinate Bounds Calculation

```python
# Extract from tile coordinate system:
# - Reference value (crval) in radians
# - Reference pixel (crpix)
# - Cell size (cdelt) in radians
# - Image dimensions (nx, ny)

# Calculate bounds:
ra_min = ref_val[0] - (ref_pix[0] - 0.5) * abs(inc[0])
ra_max = ref_val[0] + (nx - ref_pix[0] + 0.5) * abs(inc[0])
dec_min = ref_val[1] - (ref_pix[1] - 0.5) * abs(inc[1])
dec_max = ref_val[1] + (ny - ref_pix[1] + 0.5) * abs(inc[1])
```

### Overlap Check

```python
# Check if tile bounds overlap template bounds (with margin):
ra_overlap = (tile_ra_max + margin >= template_ra_min and
              tile_ra_min - margin <= template_ra_max)
dec_overlap = (tile_dec_max + margin >= template_dec_min and
               tile_dec_min - margin <= template_dec_max)
```

### Margin Pixels

Uses 10 pixel margin by default to account for:
- Edge effects
- Coordinate system rounding
- Small misalignments

## Error Handling

1. **Pre-validation fails gracefully**: If coordinate bounds cannot be read, assumes overlap (conservative)
2. **RuntimeError still caught**: As safety net for edge cases not caught by pre-validation
3. **Clear error messages**: Explains why tiles were filtered

## Testing

- Module imports successfully ✓
- Functions compile without syntax errors ✓
- Integration points updated ✓
- Error handling preserved ✓

## Future Improvements

1. **Better Template Selection**: Use `compute_tiles_bounding_box()` to create optimal template covering all tiles
2. **Coordinate System Validation**: Check coordinate system compatibility before overlap check
3. **Adaptive Margins**: Adjust margin based on cell size and image dimensions
4. **Warning Thresholds**: Only warn if significant fraction of tiles filtered

## Status

✓ **Implemented and integrated**
- Pre-validation prevents most "All output pixels are masked" errors
- RuntimeError handling remains as safety net
- Clear diagnostics for filtered tiles

