# NVSS Masking Guide

**Purpose:** Guide for using NVSS-based masking in the imaging pipeline  
**Last Updated:** 2025-11-12

---

## Overview

NVSS masking is a performance optimization that restricts deconvolution cleaning
to regions around known NVSS sources. This provides **2-4x faster imaging**
while maintaining or improving image quality.

**Key Benefits:**

- **Faster imaging**: 2-4x speedup (especially for development tier)
- **Better convergence**: Focused cleaning reduces iterations needed
- **Reduced artifacts**: Less cleaning in empty regions
- **Enabled by default**: No configuration needed for optimal performance

---

## How It Works

1. **Mask Generation**: Before imaging, the pipeline queries the NVSS catalog
   for sources within the field of view above a flux threshold (typically 10 mJy
   for standard tier, 5 mJy for high precision).

2. **FITS Mask Creation**: A FITS mask file is generated with circular regions
   (default 60 arcsec radius) around each NVSS source. Zero values indicate
   regions that won't be cleaned, non-zero values indicate regions that will be
   cleaned.

3. **WSClean Integration**: The mask is passed to WSClean via the `-fits-mask`
   parameter, which restricts cleaning to the masked regions.

4. **Hybrid Approach**: Masking works alongside WSClean's auto-masking feature,
   allowing discovery of additional sources during cleaning.

---

## Usage

### CLI Usage

**Default (masking enabled):**

```bash
python -m dsa110_contimg.imaging.cli image \
    --ms /path/to/data.ms \
    --imagename /path/to/output.img
```

**Custom mask radius:**

```bash
python -m dsa110_contimg.imaging.cli image \
    --ms /path/to/data.ms \
    --imagename /path/to/output.img \
    --mask-radius-arcsec 120.0
```

**Disable masking (not recommended):**

```bash
python -m dsa110_contimg.imaging.cli image \
    --ms /path/to/data.ms \
    --imagename /path/to/output.img \
    --no-nvss-mask
```

### Configuration File

```python
from dsa110_contimg.pipeline.config import PipelineConfig

config = PipelineConfig.from_dict({
    "paths": {
        "input_dir": "/data/incoming",
        "output_dir": "/data/ms",
    },
    "imaging": {
        "use_nvss_mask": True,
        "mask_radius_arcsec": 60.0,
    },
})
```

### Environment Variables

```bash
export PIPELINE_USE_NVSS_MASK=true
export PIPELINE_MASK_RADIUS_ARCSEC=60.0
```

### Dashboard UI

1. Navigate to the **Control** page
2. Select the **Image** tab
3. Toggle **"Use NVSS Masking"** on/off
4. Adjust **"Mask Radius (arcsec)"** if needed (default: 60.0)
5. Submit the imaging job

---

## Parameters

### `use_nvss_mask` (boolean)

- **Default**: `True`
- **Description**: Enable/disable NVSS-based masking
- **Recommendation**: Keep enabled for optimal performance

### `mask_radius_arcsec` (float)

- **Default**: `60.0`
- **Range**: `10.0` - `300.0`
- **Description**: Radius around each NVSS source in arcseconds
- **Recommendation**:
  - Default (60.0) is appropriate for most cases (~2-3× beam size)
  - Increase to 120.0 for extended sources or larger beam sizes
  - Decrease to 30.0 for point sources or smaller beam sizes

---

## When to Use Masking

### Always Recommended

Masking is enabled by default and recommended for all use cases:

- **Development tier**: Faster tests (2-4x speedup)
- **Standard tier**: Better quality + efficiency
- **High precision tier**: Faster convergence

### When Masking May Be Disabled

Masking should only be disabled in these rare cases:

- **Testing unmasked code path**: For debugging or validation
- **Very sparse fields**: When NVSS catalog has poor coverage
- **Custom mask**: When providing your own mask file (future feature)

---

## Mask Generation Details

### Source Selection

Sources are selected based on:

- **Flux threshold**:
  - Development tier: ≥10 mJy
  - Standard tier: ≥10 mJy
  - High precision tier: ≥5 mJy
- **Field of view**: Sources within the image FoV
- **Primary beam limit**: When `pbcor=True`, sources are limited to primary beam
  extent

### Mask Format

- **Format**: FITS (compatible with WSClean)
- **Convention**: Zero = not cleaned, non-zero = cleaned
- **File location**: `{imagename}.nvss_mask.fits`
- **WCS**: Matches image WCS for proper alignment

### Error Handling

If mask generation fails (e.g., NVSS catalog unavailable), the pipeline:

1. Logs a warning
2. Continues imaging without mask
3. Does not fail the imaging job

This ensures robustness even when external dependencies are unavailable.

---

## Performance Impact

### Expected Speedup

| Quality Tier   | Without Masking | With Masking | Speedup |
| -------------- | --------------- | ------------ | ------- |
| Development    | ~5 minutes      | ~1-2 minutes | 2-4×    |
| Standard       | ~30 minutes     | ~10-15 min   | 2-3×    |
| High Precision | ~2 hours        | ~45-60 min   | 2-3×    |

_Times are approximate and depend on data characteristics_

### Computational Overhead

- **Mask generation**: <1 second (negligible)
- **WSClean processing**: ~1-2% overhead from mask application
- **Net benefit**: Significant speedup outweighs overhead

---

## Troubleshooting

### Mask Not Generated

**Symptoms**: Warning message "Failed to generate NVSS mask"

**Possible Causes**:

- NVSS catalog not available
- Network connectivity issues
- Catalog file corruption

**Solution**: Imaging continues without mask (non-fatal). Check NVSS catalog
availability if masking is critical.

### Mask Too Small/Large

**Symptoms**: Sources not fully cleaned or excessive cleaning

**Solution**: Adjust `mask_radius_arcsec`:

- Increase radius for extended sources
- Decrease radius for point sources
- Consider beam size when setting radius

### Masking Not Applied

**Symptoms**: No speedup observed

**Possible Causes**:

- Masking disabled (`use_nvss_mask=False`)
- Mask generation failed silently
- Using CASA tclean backend (masking only supported for WSClean)

**Solution**:

- Verify `use_nvss_mask=True` in configuration
- Check logs for mask generation messages
- Ensure WSClean backend is used (`backend="wsclean"`)

---

## Advanced Topics

### Mask Radius Selection

The optimal mask radius depends on:

- **Beam size**: Typically 2-3× the beam FWHM
- **Source type**: Extended sources need larger radius
- **Image quality**: Larger radius for higher quality tiers

**Rule of thumb**: `mask_radius_arcsec ≈ 2-3 × beam_FWHM_arcsec`

### Combining with Auto-Masking

WSClean's auto-masking feature works alongside NVSS masking:

- **NVSS mask**: Provides initial regions to clean
- **Auto-masking**: Discovers additional sources during cleaning
- **Result**: Hybrid approach combines prior knowledge with discovery

### Future Enhancements

Potential future improvements:

- Elliptical masks for extended sources
- Flux-weighted mask sizes
- Multi-scale mask support
- Custom mask file upload

---

## References

- **Analysis**:
  [Masked Imaging Analysis](../../archive/analysis/MASKED_IMAGING_ANALYSIS.md)
- **Efficiency**:
  [Masking Efficiency Analysis](../../archive/analysis/MASKING_EFFICIENCY_ANALYSIS.md)
- **Implementation**:
  [Masking Implementation Complete](../../archive/analysis/MASKING_IMPLEMENTATION_COMPLETE.md)
- **Configuration**: See pipeline configuration in
  [Pipeline Overview](../../architecture/pipeline/pipeline_overview.md)
- **CLI Reference**: [CLI Reference](../../reference/cli.md)
