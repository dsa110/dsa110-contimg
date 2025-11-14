# Mosaic Primary Beam Correction Fix

## Issue

Mosaics were showing semi-circular patterns at tile edges, indicating incorrect primary beam (PB) correction.

## Root Cause

The `-pb.fits` files in the pipeline were **not actually PB-corrected** (they were identical to uncorrected `-image.fits` files). However, the code was setting `imageweighttype=1` in `linearmosaic.makemosaic()`, telling CASA that the images were already PB-corrected. This caused `linearmosaic` to skip PB correction, leading to artifacts.

## Solution

Modified `_build_weighted_mosaic_linearmosaic()` in `src/dsa110_contimg/mosaic/cli.py`:

1. **Changed `imageweighttype=0`**: Tells `linearmosaic` that input images are **NOT** PB-corrected
2. **Changed default `pbcor_only=False`**: Ensures uncorrected images (`-image.fits`) are fetched by default
3. **Created wrapper function**: `_build_weighted_mosaic()` ensures both manual and streaming modes use the fixed logic

## Implementation

```python
# In _build_weighted_mosaic_linearmosaic()
lm.makemosaic(
    images=regridded_tiles,
    weightimages=regridded_pbs,
    imageweighttype=0,  # Images are NOT PB-corrected
    weighttype=1        # Weight images are PB values
)
```

## Integration

- **Manual mode**: `cmd_build()` → `_build_weighted_mosaic()` → `_build_weighted_mosaic_linearmosaic()`
- **Streaming mode**: `streaming_mosaic.py` → `_build_weighted_mosaic()` → `_build_weighted_mosaic_linearmosaic()`

Both modes now use the same fixed logic.

## Verification

- Mosaic rebuilt with fixed code: `/stage/dsa110-contimg/tmp/mosaic_test_fixed/mosaic_fixed.image`
- Visual comparison confirmed semi-circular artifacts are resolved
- Both manual and streaming modes verified to use `imageweighttype=0`

## Related Documentation

- `docs/reference/LINEARMOSAIC_PARAMETERS.md` - Detailed parameter documentation
- `docs/dev/IMREGRID_ERRORS_ANALYSIS.md` - Related error analysis

## Date

Fixed: 2025-11-10

