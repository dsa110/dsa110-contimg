# JS9 CASA Analysis Plugin

**Date:** 2025-11-12  
**Status:** complete  
**Related:** [Dashboard Documentation](../reference/dashboard_backend_api.md), [Sky View Page](../analysis/DASHBOARD_OVERVIEW_DETAILED.md)

---

## Overview

The JS9 CASA Analysis Plugin integrates server-side CASA analysis tasks directly into the JS9 FITS image viewer in the dashboard. This allows scientists to run CASA analysis tasks (imstat, imfit, imview, specflux, imval) on FITS images without leaving the browser.

---

## Features

### Supported CASA Tasks

1. **Image Statistics (imstat)** - Calculate image statistics (mean, std, min, max, sum) for entire image or selected region
2. **Source Fitting (imfit)** - Fit Gaussian models to sources in selected region
3. **Contour Generation (imview)** - Generate contour paths for visualization
4. **Spectral Flux (specflux)** - Extract spectral flux statistics
5. **Pixel Extraction (imval)** - Extract pixel values from image or region

### Key Capabilities

- **Region Support**: Use JS9 regions (circles, boxes) to limit analysis to specific areas
- **Result Caching**: Automatic caching of results to avoid re-running identical analyses
- **Export Functionality**: Export results as JSON or CSV files
- **Interactive UI**: Material-UI dialog with formatted result display
- **Table View**: Statistics displayed in formatted tables for easy reading

---

## Usage

### Accessing the Plugin

1. Navigate to the **Sky View** page (`/sky`) in the dashboard
2. Select an image from the Image Browser sidebar
3. The CASA Analysis Plugin appears below the image viewer

### Running Analysis

#### Method 1: Using the Plugin UI

1. **Select a CASA Task** from the dropdown:
   - Image Statistics
   - Source Fitting
   - Contour Generation
   - Spectral Flux
   - Pixel Extraction

2. **Optional: Create a Region** in JS9:
   - Click the region tools in JS9 (circle, box, etc.)
   - Draw a region on the image
   - The plugin will detect the region automatically

3. **Toggle Region Usage**:
   - Use the "Use Region" switch to enable/disable region-based analysis
   - When enabled, analysis runs only on pixels within the selected region

4. **Click "Run Analysis"** button

5. **View Results**:
   - Results appear in a dialog
   - Statistics are displayed in formatted tables
   - Execution time and cache status are shown

#### Method 2: Using JS9 Menu (if available)

1. Right-click on the JS9 image viewer
2. Navigate to **Analysis → CASA: [Task Name]**
3. Results appear in the plugin dialog

### Exporting Results

1. After analysis completes, click **Export JSON** or **Export CSV** in the results dialog
2. Files are downloaded with names like: `casa_analysis_imstat_1234567890.json`

---

## Region Selection

### Creating Regions

Regions can be created using JS9's built-in region tools:

- **Circle**: Click and drag to create circular region
- **Box**: Click and drag to create rectangular region
- **Other shapes**: Additional region types supported by JS9

### Region Information

The plugin displays:
- Region type (circle, box, etc.)
- Center coordinates (x, y)
- Size parameters (radius for circles, width/height for boxes)

### Refreshing Region

Click the refresh icon (↻) next to the region chip to update the region from JS9.

---

## Result Display

### Statistics Table View

For `imstat` results, statistics are displayed in a formatted table:

| Statistic | Value |
|-----------|-------|
| mean      | 0.0012 |
| std       | 0.0008 |
| min       | -0.0021 |
| max       | 0.0156 |
| sum       | 1234.56 |

### JSON View

For other task types, results are displayed as formatted JSON:

```json
{
  "fit": {
    "amplitude": 0.015,
    "center": [123.45, 67.89],
    "major_axis": 2.3,
    "minor_axis": 1.8
  }
}
```

### Cache Indicator

When results are retrieved from cache, a green "Cached" chip appears next to the results title. Cached results have execution time < 0.01s.

---

## API Reference

### Backend Endpoint

**POST** `/api/visualization/js9/analysis`

**Request Body:**
```json
{
  "task": "imstat",
  "image_path": "/path/to/image.fits",
  "region": {
    "shape": "circle",
    "x": 100,
    "y": 200,
    "r": 50
  },
  "parameters": {
    "n_levels": 10,
    "smoothing_sigma": 1.0
  }
}
```

**Response:**
```json
{
  "success": true,
  "task": "imstat",
  "result": {
    "DATA": {
      "mean": 0.0012,
      "std": 0.0008,
      "min": -0.0021,
      "max": 0.0156,
      "sum": 1234.56
    }
  },
  "execution_time_sec": 0.234
}
```

### Task-Specific Parameters

#### imstat
- No special parameters required
- Returns: mean, std, min, max, sum, rms, etc.

#### imfit
- `model`: Model type (default: "gaussian")
- Returns: fitted parameters (amplitude, center, axes, position angle)

#### imview (contour generation)
- `n_levels`: Number of contour levels (default: 10)
- `smoothing_sigma`: Gaussian smoothing sigma (default: 1.0)
- Returns: contour paths with x, y coordinates for each level

#### specflux
- No special parameters required
- Returns: flux statistics

#### imval
- `box`: Box region as "x1,y1,x2,y2" (optional)
- `stokes`: Stokes parameter (optional)
- Returns: pixel values array

---

## Caching

Results are automatically cached based on:
- Task name
- Image path
- Region (if provided)
- Parameters

Cache key is computed using SHA256 hash of these values. Cache size is limited to 100 entries (FIFO eviction).

**Cache Benefits:**
- Instant results for repeated analyses
- Reduced server load
- Better user experience

**Cache Limitations:**
- Cache is in-memory (lost on server restart)
- Errors are not cached
- Cache is per-server instance

---

## Troubleshooting

### No Image Loaded

**Error:** "No image loaded in JS9 viewer"

**Solution:** Select an image from the Image Browser sidebar first.

### Region Not Detected

**Problem:** Region chip shows "No region" even after drawing one

**Solutions:**
1. Click the refresh icon (↻) to update region
2. Ensure region is created on the correct JS9 display
3. Try creating a new region

### Analysis Fails

**Error:** Task execution error

**Solutions:**
1. Check that image path is valid and accessible
2. Verify image is a valid FITS file
3. Check server logs for detailed error messages
4. Ensure CASA6 environment is properly configured

### Contour Generation Returns Statistics

**Problem:** Contour task returns statistics instead of contours

**Solution:** Matplotlib is required for contour generation. Install matplotlib in the CASA6 environment:
```bash
conda activate casa6
conda install matplotlib
```

---

## Technical Details

### Architecture

- **Frontend**: React component (`CASAnalysisPlugin.tsx`) integrated into Sky View page
- **Backend**: FastAPI endpoint (`/api/visualization/js9/analysis`) executing CASA tasks
- **Caching**: In-memory dictionary with SHA256-based keys
- **Region Conversion**: JS9 pixel coordinates converted to CASA region format

### Dependencies

**Backend:**
- `casatasks` - CASA task execution
- `astropy` - FITS file handling
- `matplotlib` - Contour generation (optional)
- `scipy` - Image smoothing

**Frontend:**
- Material-UI components
- React hooks for state management
- Axios for API calls

### Security Considerations

- Image paths are validated to ensure they exist and are FITS files
- Region coordinates are validated
- Cache keys use SHA256 (not MD5) for security
- Results are JSON-serialized to prevent code injection

---

## Examples

### Example 1: Image Statistics for Entire Image

1. Select image
2. Choose "Image Statistics" task
3. Disable "Use Region" switch
4. Click "Run Analysis"
5. View mean, std, min, max statistics

### Example 2: Source Fitting in Region

1. Select image
2. Draw circle region around source
3. Choose "Source Fitting" task
4. Enable "Use Region" switch
5. Click "Run Analysis"
6. View fitted Gaussian parameters

### Example 3: Contour Generation

1. Select image
2. Choose "Contour Generation" task
3. Click "Run Analysis"
4. View contour paths (can be used for visualization)
5. Export JSON to use contours in other tools

---

## Related Documentation

- [Dashboard API Reference](../reference/dashboard_backend_api.md)
- [Sky View Page Documentation](../analysis/DASHBOARD_OVERVIEW_DETAILED.md)
- JS9 Integration: `../qa/visualization/js9/README.md` (external file, if exists)
- [CASA Tasks Documentation](https://casa.nrao.edu/docs/casa-reference/)

---

## Future Enhancements

Potential improvements:
- Additional CASA tasks (imval with more options, imhead, etc.)
- Visual contour overlay on JS9 display
- Batch analysis for multiple regions
- Result comparison between regions
- Integration with photometry pipeline
- Custom parameter input forms

