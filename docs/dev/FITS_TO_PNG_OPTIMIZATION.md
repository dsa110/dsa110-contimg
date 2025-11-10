# FITS-to-PNG Conversion Optimization

## Overview

The FITS-to-PNG conversion in `dsa110_contimg.imaging.export.save_png_from_fits()` has been optimized to handle large mosaic images efficiently.

## Problem

Large mosaic images (e.g., 6335×16082 pixels = ~102M pixels) caused severe performance bottlenecks:

1. **Memory loading**: Loading entire 388+ MB files into memory
2. **Percentile computation**: Computing percentiles on 100M+ pixels is slow (O(n log n))
3. **Array operations**: Applying transformations to massive arrays
4. **Matplotlib rendering**: Rendering extremely large images

**Previous performance**: 60+ seconds or timeout for large mosaics

## Solution

### 1. Memory Mapping

Changed from `memmap=False` to `memmap=True`:
- Uses memory mapping to avoid loading entire file into memory
- Reduces memory footprint significantly

### 2. Automatic Downsampling

For arrays > 10M pixels, automatically downsamples before processing:
- Calculates downsampling factor to reduce to ~1-5M pixels
- Uses efficient block averaging
- Example: 102M pixel mosaic → downsample by factor 7 → ~2M pixels

### 3. Performance Impact

**After optimization**: ~21 seconds for 102M pixel mosaic
**Speedup**: ~3x faster (from 60+ seconds)

## Implementation Details

```python
# Automatic downsampling for large arrays
n_pixels = arr.size
if n_pixels > 10_000_000:
    # Calculate downsampling factor to get ~1-5M pixels
    factor = max(2, int(np.sqrt(n_pixels / 2_000_000)))
    # Use simple block averaging for downsampling
    h, w = arr.shape
    h_new, w_new = h // factor, w // factor
    if h_new > 0 and w_new > 0:
        arr_downsampled = arr[:h_new * factor, :w_new * factor].reshape(
            h_new, factor, w_new, factor
        ).mean(axis=(1, 3))
        arr = arr_downsampled
```

## Usage

The optimization is automatic and transparent:

```python
from dsa110_contimg.imaging.export import save_png_from_fits

# Automatically optimized for large files
png_files = save_png_from_fits(['large_mosaic.fits'])
```

## Behavior

- **Small images** (< 10M pixels): Processed at full resolution
- **Large images** (> 10M pixels): Automatically downsampled for visualization
- Downsampling factor is printed: `"Downsampled by factor 7 for faster processing"`

## Notes

- Downsampling is only for visualization (PNG generation)
- Original FITS files are not modified
- Quality is maintained for visualization purposes (block averaging preserves structure)

## Related Files

- `src/dsa110_contimg/imaging/export.py` - Implementation
- `docs/reference/LINEARMOSAIC_PARAMETERS.md` - Mosaic building documentation

