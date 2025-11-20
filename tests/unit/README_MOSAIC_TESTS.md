# Mosaic Unit Tests

This directory contains comprehensive unit tests for the mosaic functionality.

## Test Files

### `test_mosaic_bounds_calculation.py`

Tests for `_calculate_mosaic_bounds()` function:

- ✅ 4D CASA image bounds calculation
- ✅ 2D CASA image bounds calculation
- ✅ Multiple tiles union bounds
- ✅ Correct pixel coordinate order for 4D images (`[0, 0, y, x]` fix)
- ✅ Handling missing corner coordinates gracefully

**Status:** All 5 tests passing ✅

### `test_mosaic_coordinate_system.py`

Tests for `_create_common_coordinate_system()` function:

- Template creation from FITS files
- Template creation from CASA images
- Coordinate system centering verification
- Pixel scale calculation

**Status:** Tests created, may need CASA mocking adjustments

### `test_mosaic_weight_image_init.py`

Tests for weight image initialization fix:

- Output path cleanup before `defineoutputimage()`
- Both image and weight paths removed
- Correct paths passed to `defineoutputimage()`

**Status:** Tests created, may need mocking adjustments

### `test_mosaic_overlap_filtering.py`

Tests for overlap filtering functions:

- `filter_tiles_by_overlap()` basic functionality
- `check_tile_overlaps_template()` overlap detection
- `get_tile_coordinate_bounds()` coordinate extraction

**Status:** Tests created, may need mocking adjustments

## Running Tests

```bash
# Run all mosaic tests
pytest tests/unit/test_mosaic_*.py -v

# Run specific test file
pytest tests/unit/test_mosaic_bounds_calculation.py -v

# Run with coverage
pytest tests/unit/test_mosaic_*.py --cov=dsa110_contimg.mosaic
```

## Key Fixes Tested

1. **Bounds Calculation Fix**: Tests verify that pixel coordinate order is
   correct for 4D images (`[0, 0, y, x]` instead of `[y, x, 0, 0]`)

2. **Weight Image Initialization Fix**: Tests verify that output paths are
   cleaned up before calling `linearmosaic.defineoutputimage()`

3. **Coordinate System Centering**: Tests verify that templates are centered on
   calculated mosaic bounds

## Mocking Strategy

All tests use mocks to avoid requiring real CASA images:

- `MockCASAImage`: Simulates CASA image objects
- `MockCoordinateSystem`: Simulates CASA coordinate systems
- `patch('casacore.images.image')`: Mocks CASA image imports

This allows fast, isolated unit tests without CASA dependencies.
