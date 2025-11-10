# Automatic PNG Visualization Generation in Streaming Mosaic Pipeline

## Overview

The streaming mosaic pipeline now automatically generates low-resolution PNG visualizations for every mosaic created. This provides quick visual inspection without manual conversion steps.

## Implementation

### Location
`src/dsa110_contimg/mosaic/streaming_mosaic.py` → `create_mosaic()` method

### Workflow

1. **Mosaic Creation**: Mosaic is built using `_build_weighted_mosaic()`
2. **Format Detection**: Checks if FITS file exists (preferred) or CASA image
3. **FITS Export** (if needed): If only CASA image exists, exports to FITS first
4. **PNG Generation**: Uses optimized `save_png_from_fits()` to create PNG
5. **Error Handling**: PNG generation failures are logged but don't fail mosaic creation

### Code Flow

```python
# After mosaic creation
if Path(fits_path).exists():
    png_source_path = fits_path
else:
    # Export CASA image to FITS first
    exported_fits = export_fits([mosaic_path])
    png_source_path = exported_fits[0]

# Generate PNG
png_files = save_png_from_fits([png_source_path])
```

## Performance

- **PNG Generation Time**: ~21 seconds for large mosaics (102M pixels)
- **Optimization**: Automatic downsampling for arrays > 10M pixels
- **Memory**: Uses memory mapping (`memmap=True`) to avoid loading entire file

## Output Files

For a mosaic named `mosaic_123.image`:
- **CASA Image**: `mosaic_123.image/`
- **FITS** (if exported): `mosaic_123.image.fits`
- **PNG** (auto-generated): `mosaic_123.image.fits.png`

## Features

- **Automatic**: No manual steps required
- **Non-blocking**: Failures don't prevent mosaic creation
- **Optimized**: Uses fast downsampling for large images
- **Low-resolution**: Suitable for quick visual inspection

## Logging

The pipeline logs PNG generation status:
```
INFO: Generating PNG visualization...
INFO: PNG visualization created: /path/to/mosaic.fits.png
```

Or if generation fails:
```
WARNING: PNG visualization generation failed (non-critical): <error>
```

## Related Documentation

- `docs/dev/FITS_TO_PNG_OPTIMIZATION.md` - PNG optimization details
- `docs/dev/MOSAIC_PB_FIX_AND_OPTIMIZATION_SUMMARY.md` - Overall summary

## Date

Added: 2025-11-10

