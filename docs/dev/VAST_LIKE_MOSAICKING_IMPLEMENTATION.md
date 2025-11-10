# VAST-Like Mosaicking Implementation

**Date:** 2025-01-XX  
**Status:** Implemented  
**Purpose:** Migrate DSA-110 mosaicking to VAST Pipeline's simpler, more robust approach

---

## Summary

DSA-110's mosaicking implementation has been refactored to follow VAST Pipeline's philosophy of using automated tools rather than manual pixel-by-pixel operations. This addresses issues with the previous complex implementation that was causing problems generating science-quality mosaics.

---

## Key Changes

### 1. New VAST-Like Function: `_build_weighted_mosaic_vast_like()`

**Location:** `src/dsa110_contimg/mosaic/cli.py:850`

**Key Simplifications:**
- Uses first tile as template for automatic coordinate alignment
- Lets CASA handle regridding automatically via `imregrid` template parameter
- Simpler workflow - less manual coordinate system manipulation
- More robust error handling

**Weighting Scheme:** Sault weighting (PB²/σ²)
- `weight[k] = pb_response[k]² / noise_variance[k]`
- `mosaic = sum(weight[k] * tile[k]) / sum(weight[k])`

**Workflow:**
1. Convert FITS to CASA format if needed
2. Use first tile as template for coordinate system
3. Regrid all tiles and PB images to template coordinate system
4. Create weighted images: `tile * PB² / σ²`
5. Combine: `sum(weighted_tiles) / sum(weights)`

**Fallback:** If PB images not available, uses noise-weighted combination (1/σ²)

### 2. Legacy Function Redirect: `_build_weighted_mosaic()`

**Location:** `src/dsa110_contimg/mosaic/cli.py:1117`

The old complex implementation (1200+ lines) has been replaced with a simple redirect to the VAST-like function:

```python
def _build_weighted_mosaic(...):
    """LEGACY - use _build_weighted_mosaic_vast_like"""
    LOG.info("Using VAST-like mosaicking approach (simplified)")
    return _build_weighted_mosaic_vast_like(tiles, metrics_dict, output_path)
```

### 3. Integration with CLI

**Location:** `src/dsa110_contimg/mosaic/cli.py:1133` (`cmd_build()`)

The `cmd_build()` function calls `_build_weighted_mosaic()` for methods `'weighted'` or `'pbweighted'`, which now automatically uses the VAST-like implementation.

---

## Comparison: Old vs. New Approach

### Old Approach (Complex)
- Manual bounding box calculation
- Manual common coordinate system creation
- Complex template image generation
- Manual pixel-by-pixel operations
- ~1200 lines of code
- Many edge cases and failure modes

### New Approach (VAST-Like)
- Uses first tile as template (automatic alignment)
- CASA handles regridding automatically
- Simpler workflow with fewer steps
- ~260 lines of code
- More robust error handling
- Follows VAST Pipeline's proven approach

---

## Technical Details

### Dependencies
- CASA tasks: `immath`, `imregrid`, `importfits`, `exportfits`
- CASA core: `casacore.images.image`
- Standard library: `tempfile`, `shutil`, `os`, `pathlib`

### Key Functions Used
- `imregrid()`: Regrids images to template coordinate system
- `immath()`: Performs image arithmetic (PB², weighting, combination)
- `importfits()`: Converts FITS to CASA image format

### Error Handling
- Validates all tiles exist before processing
- Checks for CASA availability
- Handles missing PB images gracefully (falls back to noise weighting)
- Cleans up temporary files automatically

---

## Testing Recommendations

1. **Unit Tests:**
   - Test with mock CASA tools
   - Test PB-weighted combination
   - Test noise-weighted fallback
   - Test single tile case
   - Test FITS vs CASA image formats

2. **Integration Tests:**
   - Test with real tiles from products DB
   - Verify mosaic quality metrics
   - Compare with old implementation (if possible)

3. **Validation:**
   - Check mosaic coordinate system
   - Verify flux scaling
   - Check for artifacts
   - Validate against known sources

---

## Usage

The new implementation is automatically used when building mosaics:

```bash
# Plan a mosaic
dsa110-contimg mosaic plan --name test_mosaic --method weighted

# Build the mosaic (uses VAST-like approach automatically)
dsa110-contimg mosaic build --name test_mosaic --output mosaics/test.fits
```

---

## References

- **VAST Pipeline:** https://vast-survey.org/vast-pipeline/
- **VAST Mosaicking Analysis:** `docs/analysis/VAST_MOSAIC_AND_ANALYSIS_WORKFLOW.md`
- **Sault Weighting Scheme:** Sault et al. (1996) - Primary beam weighting for optimal SNR

---

## Migration Notes

- **Backward Compatibility:** The `_build_weighted_mosaic()` function signature is unchanged, so existing code continues to work
- **No Configuration Changes:** No changes needed to CLI arguments or database schema
- **Performance:** Expected to be faster due to simpler workflow and fewer operations
- **Reliability:** Expected to be more reliable due to using CASA's proven regridding and combination tools

---

**Last Updated:** 2025-01-XX

