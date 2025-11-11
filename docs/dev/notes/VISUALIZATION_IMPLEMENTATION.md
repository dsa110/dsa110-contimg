# Enhanced Visualization Implementation

## Overview

This document describes the implementation of enhanced visualization for validation results, adding diagnostic plots to HTML reports.

## What Was Implemented

### 1. New Plotting Module (`qa/validation_plots.py`)

**New Functions**:

1. **`plot_astrometry_scatter()`**
   - Generates astrometry scatter plot showing detected vs catalog positions
   - Two-panel plot:
     - Left: RA vs Dec offset scatter plot (color-coded by total offset)
     - Right: Offset distribution histogram
   - Includes statistics (mean, RMS) and reference lines
   - Returns base64-encoded PNG image

2. **`plot_flux_ratio_histogram()`**
   - Generates flux ratio analysis plots
   - Two-panel plot:
     - Left: Flux ratio histogram (detected/catalog)
     - Right: Detected vs catalog flux scatter plot with 1:1 line
   - Includes statistics (mean, RMS, error) and reference lines
   - Returns base64-encoded PNG image

3. **`plot_completeness_curve()`**
   - Generates completeness vs flux density curve
   - Two-panel plot:
     - Left: Completeness curve with threshold lines (95%, 80%)
     - Right: Source counts per flux bin (catalog vs detected)
   - Marks completeness limit
   - Returns base64-encoded PNG image

**Features**:
- Headless matplotlib backend (Agg) for server environments
- Base64 encoding for embedding in HTML
- Professional styling with grids, legends, and statistics
- Error handling with graceful fallback

### 2. Enhanced HTML Report Generation (`qa/html_reports.py`)

**Updates**:
- Integrated plotting functions into HTML report generation
- Plots automatically embedded when validation data is available
- Responsive image display with proper styling
- Plots appear in respective validation sections:
  - Astrometry plot in astrometry section
  - Flux ratio plot in flux scale section
  - Completeness plot in source counts section

## Plot Details

### Astrometry Scatter Plot
- **Left Panel**: RA vs Dec offset scatter
  - Color-coded by total offset magnitude
  - Reference lines at (0,0)
  - Statistics overlay (mean, RMS)
- **Right Panel**: Offset distribution histogram
  - Shows distribution of total offsets
  - Mean and RMS reference lines
  - Grid for easy reading

### Flux Ratio Histogram
- **Left Panel**: Flux ratio histogram
  - Distribution of detected/catalog flux ratios
  - Perfect ratio line at 1.0
  - Mean ratio reference line
  - Statistics overlay
- **Right Panel**: Detected vs catalog flux scatter
  - 1:1 reference line
  - Shows systematic offsets or scatter
  - Equal aspect ratio for accurate comparison

### Completeness Curve
- **Left Panel**: Completeness vs flux density
  - Logarithmic flux axis
  - 95% and 80% threshold lines
  - Completeness limit marker
  - Overall completeness text
- **Right Panel**: Source counts per bin
  - Stacked bars (catalog vs detected)
  - Logarithmic flux axis
  - Shows detection efficiency per flux range

## Usage

### Python API

```python
from dsa110_contimg.qa.validation_plots import (
    plot_astrometry_scatter,
    plot_flux_ratio_histogram,
    plot_completeness_curve
)
from dsa110_contimg.qa.catalog_validation import validate_astrometry

# Run validation
result = validate_astrometry("/path/to/image.fits")

# Generate plot
plot_img = plot_astrometry_scatter(result)
if plot_img:
    # plot_img is a base64-encoded data URI
    # Can be used directly in HTML: <img src="{plot_img}">
    print("Plot generated successfully")
```

### HTML Report Integration

Plots are automatically included when generating HTML reports:

```python
from dsa110_contimg.qa.html_reports import generate_validation_report
from dsa110_contimg.qa.catalog_validation import (
    validate_astrometry,
    validate_flux_scale,
    validate_source_counts
)

# Run validations
astrometry = validate_astrometry("/path/to/image.fits")
flux_scale = validate_flux_scale("/path/to/image.fits")
source_counts = validate_source_counts("/path/to/image.fits")

# Generate HTML report (plots automatically included)
report = generate_validation_report(
    image_path="/path/to/image.fits",
    astrometry_result=astrometry,
    flux_scale_result=flux_scale,
    source_counts_result=source_counts,
    output_path="/path/to/report.html"
)
```

## Test Results

**Test Script**: `test_validation_plots.py`

**Test Results**:
- ✓ All three plot types generated successfully
- ✓ Plots embedded as base64 images in HTML
- ✓ HTML report size: ~250 KB (with 3 plots)
- ✓ All plot indicators present in HTML
- ✓ Plots display correctly in web browsers

**Sample Output**:
```
✓ Astrometry result created
✓ Flux scale result created
✓ Completeness result created
✓ HTML report created
  Report status: WARNING
  Report score: 90.0%
  File size: 250,076 bytes
  ✓ All plot indicators present in HTML
  Found 3 embedded plots
```

## Benefits

1. **Visual Assessment**: Plots provide immediate visual feedback on validation quality
2. **Integrated Reports**: Plots embedded directly in HTML (no external files)
3. **Self-Contained**: Base64 encoding means reports can be shared easily
4. **Professional Presentation**: High-quality plots suitable for data releases
5. **Diagnostic Value**: Helps identify systematic issues (offsets, flux scale errors)

## Technical Details

### Plot Generation
- Uses matplotlib with Agg backend (headless)
- 100 DPI resolution (good quality, reasonable file size)
- PNG format (good compression, universal support)
- Base64 encoding for HTML embedding

### File Size Considerations
- Each plot: ~50-100 KB (base64 encoded)
- Total HTML with 3 plots: ~250 KB
- Acceptable for web viewing and email sharing
- Can be optimized further if needed (lower DPI, SVG format)

### Error Handling
- Plots return `None` if data unavailable
- HTML generation gracefully handles missing plots
- Logs errors without failing report generation

## Comparison with ASKAP

| Feature | ASKAP | DSA-110 | Status |
|---------|-------|---------|--------|
| Astrometry plots | ✅ | ✅ | **Implemented** |
| Flux ratio plots | ✅ | ✅ | **Implemented** |
| Completeness plots | ✅ | ✅ | **Implemented** |
| HTML embedding | ✅ | ✅ | **Implemented** |
| Base64 encoding | ✅ | ✅ | **Implemented** |

## Files Created/Modified

- **Created**: `src/dsa110_contimg/qa/validation_plots.py` - Plotting functions
- **Modified**: `src/dsa110_contimg/qa/html_reports.py` - Plot integration
- **Test**: `test_validation_plots.py` - Test script

## Future Enhancements

1. **Interactive Plots**: Consider Plotly for interactive plots (zoom, pan, hover)
2. **SVG Format**: Use SVG for vector graphics (scalable, smaller file size)
3. **Plot Customization**: Allow custom colors, styles via configuration
4. **Additional Plots**: Add more diagnostic plots (SNR distribution, etc.)
5. **Plot Export**: Allow exporting plots as separate image files

## Notes

- Plots require matplotlib (already in dependencies)
- Base64 encoding increases file size but ensures portability
- Plots are optional - reports work without them if data unavailable
- All plots use consistent styling for professional appearance

