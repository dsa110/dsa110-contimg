"""
Visualization module for DSA-110 continuum imaging pipeline.

Provides standardized figure generation for:
- FITS images (cutouts, mosaics, quicklook PNGs)
- Calibration diagnostics (bandpass, gains, delays)
- Source analysis (lightcurves, spectra, validation reports)

Adapted from:
- dsa110-calib/dsacalib/plotting.py (Dana Simard)
- VAST/vastfast/plot.py (Yuanming Wang)
- ASKAP-continuum-validation/report.py (Jordan Collier)
- radiopadre/fitsfile.py

Usage:
    from dsa110_contimg.visualization import (
        plot_fits_image,
        plot_cutout,
        save_quicklook_png,
        FigureConfig,
    )
    
    # Quick PNG from FITS
    save_quicklook_png("image.fits", "image.png")
    
    # Publication-quality cutout
    plot_cutout("image.fits", ra=180.0, dec=45.0, radius_arcmin=5.0,
                output="cutout.pdf", config=FigureConfig(style="publication"))
"""

from dsa110_contimg.visualization.config import FigureConfig, PlotStyle
from dsa110_contimg.visualization.fits_plots import (
    plot_fits_image,
    plot_cutout,
    save_quicklook_png,
    plot_mosaic_overview,
)
from dsa110_contimg.visualization.calibration_plots import (
    plot_bandpass,
    plot_gains,
    plot_delays,
    plot_dynamic_spectrum,
)
from dsa110_contimg.visualization.source_plots import (
    plot_lightcurve,
    plot_spectrum,
    plot_source_comparison,
)

__all__ = [
    # Config
    "FigureConfig",
    "PlotStyle",
    # FITS
    "plot_fits_image",
    "plot_cutout",
    "save_quicklook_png",
    "plot_mosaic_overview",
    # Calibration
    "plot_bandpass",
    "plot_gains",
    "plot_delays",
    "plot_dynamic_spectrum",
    # Sources
    "plot_lightcurve",
    "plot_spectrum",
    "plot_source_comparison",
]
