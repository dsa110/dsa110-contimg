# Visualization Module

The `dsa110_contimg.visualization` module provides standardized figure generation for the DSA-110 continuum imaging pipeline. It consolidates plotting utilities from multiple sources into a unified, consistent API.

## Overview

The module supports:

- **FITS image display** with WCS coordinates, beam ellipses, and colorbars
- **Source cutouts** with crosshairs and position markers
- **Calibration diagnostics** (bandpass, gains, delays, dynamic spectra)
- **Source analysis** (lightcurves, spectra, flux comparisons)
- **Mosaic visualization** (tile grids, footprints, coverage maps)
- **Report generation** (HTML and PDF)

## Quick Start

```python
from dsa110_contimg.visualization import (
    FigureConfig, PlotStyle,
    plot_fits_image, plot_cutout, save_quicklook_png,
    plot_bandpass, plot_gains,
    plot_lightcurve, plot_spectrum,
    generate_html_report, ReportSection,
)

# Generate a quick PNG from a FITS file
save_quicklook_png("observation.fits", "preview.png")

# Create a publication-quality figure
config = FigureConfig(style=PlotStyle.PUBLICATION)
plot_fits_image("image.fits", output="figure.pdf", config=config)
```

## Configuration

### FigureConfig

All plotting functions accept a `FigureConfig` object for consistent styling:

```python
from dsa110_contimg.visualization import FigureConfig, PlotStyle

# Default quicklook style
config = FigureConfig()

# Publication quality (300 DPI, PDF output)
config = FigureConfig(style=PlotStyle.PUBLICATION)

# Presentation style (large fonts)
config = FigureConfig(style=PlotStyle.PRESENTATION)

# Custom configuration
config = FigureConfig(
    figsize=(10, 8),
    dpi=200,
    cmap="viridis",
    font_size=14,
    colorbar=True,
    grid=True,
)
```

### Style Presets

| Style          | DPI | Figure Size | Use Case                     |
| -------------- | --- | ----------- | ---------------------------- |
| `QUICKLOOK`    | 140 | 6×5 inches  | Web dashboard, quick preview |
| `PUBLICATION`  | 300 | 8×6 inches  | Journal figures, PDFs        |
| `PRESENTATION` | 150 | 12×9 inches | Slides, talks                |
| `INTERACTIVE`  | 100 | 10×8 inches | Jupyter notebooks            |

## FITS Image Plotting

### plot_fits_image

Display a FITS image with WCS coordinates:

```python
from dsa110_contimg.visualization import plot_fits_image

# Basic usage
fig = plot_fits_image("image.fits", output="image.png")

# With options
fig = plot_fits_image(
    "image.fits",
    output="image.png",
    title="Custom Title",
    vmin=-0.001,
    vmax=0.01,
    stretch="asinh",  # 'linear', 'log', 'sqrt', 'asinh'
    show_beam=True,
    show_colorbar=True,
    config=FigureConfig(style=PlotStyle.PUBLICATION),
)
```

### plot_cutout

Create cutouts centered on a source:

```python
from dsa110_contimg.visualization import plot_cutout
from astropy.coordinates import SkyCoord

# Using RA/Dec
fig = plot_cutout(
    "image.fits",
    ra=180.0,
    dec=45.0,
    radius_arcmin=5.0,
    output="cutout.png",
    show_crosshair=True,
    show_circle=True,
    circle_radius_arcsec=30.0,
)

# Using SkyCoord
coord = SkyCoord("12h00m00s", "+45d00m00s")
fig = plot_cutout("image.fits", coord=coord, radius_arcmin=3.0)
```

### save_quicklook_png

Fast PNG generation with automatic downsampling:

```python
from dsa110_contimg.visualization import save_quicklook_png

# Auto-names output as image.fits.png
output_path = save_quicklook_png("image.fits")

# Custom output and max size
output_path = save_quicklook_png(
    "large_image.fits",
    output="preview.png",
    max_size=1024,  # Downsample if larger
)
```

## Calibration Plots

### plot_bandpass

Plot bandpass calibration solutions:

```python
from dsa110_contimg.visualization import plot_bandpass

# Generate amplitude and phase plots
plots = plot_bandpass(
    "calibration.bcal",
    output="/path/to/output/",
    plot_amplitude=True,
    plot_phase=True,
)
```

### plot_gains

Plot gain solutions vs time:

```python
from dsa110_contimg.visualization import plot_gains

plots = plot_gains(
    "calibration.gcal",
    output="/path/to/output/",
    plot_amplitude=True,
    plot_phase=True,
)
```

### plot_delays

Plot delay calibration (fringe search):

```python
from dsa110_contimg.visualization import plot_delays
import numpy as np

fig = plot_delays(
    delay_data,      # Complex visibility FFT, shape (nvis, nbl, ndelay, npol)
    delay_axis,      # Delay values in nanoseconds
    baseline_names,  # List of baseline labels
    output="delays.png",
)
```

### plot_dynamic_spectrum

Plot dynamic spectrum (waterfall):

```python
from dsa110_contimg.visualization import plot_dynamic_spectrum

fig = plot_dynamic_spectrum(
    vis,            # Visibilities, shape (nbl, ntime, nfreq, npol)
    freq_ghz,       # Frequency array in GHz
    mjd,            # Time array in MJD
    baseline_names, # Baseline labels
    output="dynspec.png",
    normalize=False,
    vmin=-100,
    vmax=100,
)
```

## Source Analysis Plots

### plot_lightcurve

Plot flux density vs time:

```python
from dsa110_contimg.visualization import plot_lightcurve
from astropy.time import Time
import numpy as np

flux = np.array([1.0, 1.1, 0.9, 1.2])  # Jy
errors = np.array([0.1, 0.1, 0.1, 0.1])
times = Time([60000.0, 60000.1, 60000.2, 60000.3], format="mjd")

fig = plot_lightcurve(
    flux, times,
    errors=errors,
    output="lightcurve.png",
    source_name="J1234+5678",
    flux_unit="mJy",
)
```

### plot_spectrum

Plot flux density vs frequency:

```python
from dsa110_contimg.visualization import plot_spectrum

fig = plot_spectrum(
    flux,           # Flux in Jy
    freq_ghz,       # Frequencies in GHz
    errors=errors,
    output="spectrum.png",
    source_name="3C286",
    fit_powerlaw=True,  # Fit and display spectral index
)
```

### plot_source_comparison

Compare measured vs reference catalog fluxes:

```python
from dsa110_contimg.visualization import plot_source_comparison

fig = plot_source_comparison(
    measured_flux,
    reference_flux,
    errors_measured=meas_err,
    errors_reference=ref_err,
    output="comparison.png",
    measured_label="DSA-110",
    reference_label="NVSS",
    show_ratio=True,  # Show flux ratio histogram
)
```

## Mosaic Visualization

### plot_tile_grid

Display a grid of mosaic tile thumbnails:

```python
from dsa110_contimg.visualization import plot_tile_grid

tiles = ["/path/to/tile1.fits", "/path/to/tile2.fits", ...]

fig = plot_tile_grid(
    tiles,
    output="tile_grid.png",
    ncols=4,
    show_labels=True,
    stretch="asinh",
)
```

### plot_mosaic_footprints

Show tile footprints on sky:

```python
from dsa110_contimg.visualization import plot_mosaic_footprints

fig = plot_mosaic_footprints(
    tiles,
    output="footprints.png",
    mosaic_wcs=final_mosaic_wcs,  # Optional: for coordinate frame
    title="Mosaic Tile Coverage",
)
```

### plot_coverage_map

Show number of contributing tiles per pixel:

```python
from dsa110_contimg.visualization import plot_coverage_map

fig = plot_coverage_map(
    coverage_data,  # 2D array of coverage counts
    wcs=mosaic_wcs,
    output="coverage.png",
    title="Coverage Map",
)
```

## Report Generation

### HTML Reports

Generate HTML reports with embedded figures:

```python
from dsa110_contimg.visualization import (
    generate_html_report,
    ReportSection,
    ReportMetadata,
)

# Create sections
sections = [
    ReportSection(
        title="Observation Overview",
        content="This observation covers...",
        tables=[{
            "Target": "3C286",
            "Date": "2025-12-03",
            "Duration": "5 minutes",
        }],
        table_captions=["Observation Parameters"],
    ),
    ReportSection(
        title="Calibration",
        content="Bandpass and gain solutions.",
        figures=[bandpass_fig, gains_fig],
        figure_captions=["Bandpass Solutions", "Gain Amplitude"],
    ),
]

# Generate report
metadata = ReportMetadata(
    title="Calibration Report: 3C286",
    observation_id="2025-12-03T12:00:00",
)

report_path = generate_html_report(sections, "report.html", metadata)
```

### PDF Reports

Generate multi-page PDF reports:

```python
from dsa110_contimg.visualization import generate_pdf_report

report_path = generate_pdf_report(sections, "report.pdf", metadata)
```

### Diagnostic Reports

Automatically generate a full diagnostic report:

```python
from dsa110_contimg.visualization import create_diagnostic_report

report = create_diagnostic_report(
    ms_path="/stage/dsa110-contimg/ms/observation.ms",
    output_dir="/stage/dsa110-contimg/reports/",
    include_calibration=True,
    include_imaging=True,
)
```

## Module Structure

```
dsa110_contimg/visualization/
├── __init__.py           # Public API exports
├── config.py             # FigureConfig, PlotStyle
├── fits_plots.py         # FITS image plotting
├── calibration_plots.py  # Calibration diagnostics
├── source_plots.py       # Lightcurves, spectra
├── mosaic_plots.py       # Mosaic visualization
└── report.py             # HTML/PDF generation
```

## Dependencies

The visualization module requires:

- `matplotlib` (figure generation)
- `astropy` (FITS I/O, WCS, coordinates)
- `numpy` (array operations)

Optional dependencies for enhanced functionality:

- `casatasks` (CASA plotbandpass for calibration)
- `casacore` (fallback calibration plotting)
- `scipy` (power-law fitting, statistics)

## See Also

- [API Reference](../API_REFERENCE.md) - Full API documentation
- [User Guide](../USER_GUIDE.md) - Pipeline usage guide
- [Mosaic Module](mosaic.md) - Mosaic processing documentation
