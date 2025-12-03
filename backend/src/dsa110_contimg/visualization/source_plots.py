"""
Source analysis plotting utilities.

Provides functions for:
- Lightcurves (flux vs time)
- Spectra (flux vs frequency)
- Source comparison plots (ASKAP vs reference catalogs)

Adapted from:
- VAST/vastfast/plot.py (lightcurves)
- ASKAP-continuum-validation/report.py (validation plots)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

import numpy as np

if TYPE_CHECKING:
    from astropy.time import Time
    from matplotlib.figure import Figure
    from numpy.typing import NDArray

from dsa110_contimg.visualization.config import FigureConfig, PlotStyle

logger = logging.getLogger(__name__)


def _setup_matplotlib() -> None:
    """Configure matplotlib for headless operation."""
    import matplotlib
    matplotlib.use("Agg")


def plot_lightcurve(
    flux: "NDArray",
    times: Union["NDArray", "Time", list],
    errors: Optional["NDArray"] = None,
    output: Optional[Union[str, Path]] = None,
    config: Optional[FigureConfig] = None,
    title: str = "",
    flux_unit: str = "mJy",
    source_name: Optional[str] = None,
) -> "Figure":
    """Plot a source lightcurve with error bars.
    
    Adapted from VAST/vastfast/plot.py plot_lightcurve().
    
    Args:
        flux: Flux density values
        times: Timestamps (MJD, datetime, or astropy Time)
        errors: Flux density errors (optional)
        output: Output file path
        config: Figure configuration
        title: Plot title
        flux_unit: Unit label for flux axis
        source_name: Source name for labeling
        
    Returns:
        matplotlib Figure object
    """
    _setup_matplotlib()
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from astropy.time import Time
    
    if config is None:
        config = FigureConfig(style=PlotStyle.QUICKLOOK)
    
    # Convert times to datetime for plotting
    if not isinstance(times, Time):
        times = Time(times)
    times.format = "datetime64"
    
    # Convert flux to display units
    flux = np.asarray(flux)
    if flux_unit == "mJy" and np.nanmax(flux) < 0.1:
        flux = flux * 1e3
    elif flux_unit == "Jy" and np.nanmax(flux) > 100:
        flux = flux / 1e3
        flux_unit = "mJy"
    
    if errors is not None:
        errors = np.asarray(errors)
        if flux_unit == "mJy":
            errors = errors * 1e3
    
    fig, ax = plt.subplots(figsize=config.figsize, dpi=config.dpi)
    
    if errors is not None:
        ax.errorbar(
            times.value, flux, yerr=errors,
            fmt="o", color="black", markersize=config.marker_size,
            alpha=config.alpha, capsize=3,
        )
    else:
        ax.plot(
            times.value, flux,
            "o-", color="black", markersize=config.marker_size,
            alpha=config.alpha,
        )
    
    ax.set_xlabel("Time (UTC)", fontsize=config.effective_label_size)
    ax.set_ylabel(f"Peak Flux Density ({flux_unit}/beam)", fontsize=config.effective_label_size)
    
    # Format time axis
    date_formatter = mdates.DateFormatter("%Y-%b-%d\n%H:%M")
    ax.xaxis.set_major_formatter(date_formatter)
    
    # Auto-adjust tick spacing
    if len(times) > 1:
        span_hours = (times[-1] - times[0]).to_value("hour")
        if span_hours > 24:
            ax.xaxis.set_major_locator(mdates.DayLocator())
        elif span_hours > 4:
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, int(span_hours / 6))))
    
    fig.autofmt_xdate(rotation=15)
    
    # Title
    if title:
        ax.set_title(title, fontsize=config.effective_title_size)
    elif source_name:
        ax.set_title(f"Lightcurve: {source_name}", fontsize=config.effective_title_size)
    
    if config.grid:
        ax.grid(True, alpha=0.3)
    
    fig.tight_layout()
    
    if output:
        fig.savefig(output, dpi=config.dpi, bbox_inches="tight")
        logger.info(f"Saved lightcurve: {output}")
        plt.close(fig)
    
    return fig


def plot_spectrum(
    flux: "NDArray",
    freq_ghz: "NDArray",
    errors: Optional["NDArray"] = None,
    output: Optional[Union[str, Path]] = None,
    config: Optional[FigureConfig] = None,
    title: str = "",
    source_name: Optional[str] = None,
    fit_powerlaw: bool = False,
) -> "Figure":
    """Plot a source spectrum (flux vs frequency).
    
    Args:
        flux: Flux density values in Jy
        freq_ghz: Frequencies in GHz
        errors: Flux density errors (optional)
        output: Output file path
        config: Figure configuration
        title: Plot title
        source_name: Source name for labeling
        fit_powerlaw: Fit and overlay a power-law model
        
    Returns:
        matplotlib Figure object
    """
    _setup_matplotlib()
    import matplotlib.pyplot as plt
    
    if config is None:
        config = FigureConfig(style=PlotStyle.QUICKLOOK)
    
    flux = np.asarray(flux)
    freq_ghz = np.asarray(freq_ghz)
    
    # Convert to mJy if values are small
    flux_unit = "Jy"
    if np.nanmax(flux) < 0.1:
        flux = flux * 1e3
        flux_unit = "mJy"
        if errors is not None:
            errors = np.asarray(errors) * 1e3
    
    fig, ax = plt.subplots(figsize=config.figsize, dpi=config.dpi)
    
    if errors is not None:
        ax.errorbar(
            freq_ghz, flux, yerr=errors,
            fmt="o", color="black", markersize=config.marker_size,
            alpha=config.alpha, capsize=3,
        )
    else:
        ax.plot(
            freq_ghz, flux,
            "o", color="black", markersize=config.marker_size,
            alpha=config.alpha,
        )
    
    # Power-law fit
    if fit_powerlaw and len(flux) > 2:
        try:
            mask = np.isfinite(flux) & np.isfinite(freq_ghz) & (flux > 0)
            if np.sum(mask) > 2:
                from scipy.optimize import curve_fit
                
                def powerlaw(f, S0, alpha):
                    return S0 * (f / freq_ghz[mask].mean()) ** alpha
                
                popt, _ = curve_fit(powerlaw, freq_ghz[mask], flux[mask])
                
                freq_fit = np.linspace(freq_ghz.min(), freq_ghz.max(), 100)
                flux_fit = powerlaw(freq_fit, *popt)
                
                ax.plot(
                    freq_fit, flux_fit, "--", color="red",
                    label=f"α = {popt[1]:.2f}"
                )
                ax.legend(fontsize=config.effective_tick_size)
        except Exception as e:
            logger.warning(f"Power-law fit failed: {e}")
    
    ax.set_xlabel("Frequency (GHz)", fontsize=config.effective_label_size)
    ax.set_ylabel(f"Flux Density ({flux_unit})", fontsize=config.effective_label_size)
    
    # Log-log scale often useful for spectra
    ax.set_xscale("log")
    ax.set_yscale("log")
    
    if title:
        ax.set_title(title, fontsize=config.effective_title_size)
    elif source_name:
        ax.set_title(f"Spectrum: {source_name}", fontsize=config.effective_title_size)
    
    if config.grid:
        ax.grid(True, alpha=0.3, which="both")
    
    fig.tight_layout()
    
    if output:
        fig.savefig(output, dpi=config.dpi, bbox_inches="tight")
        logger.info(f"Saved spectrum: {output}")
        plt.close(fig)
    
    return fig


def plot_source_comparison(
    measured_flux: "NDArray",
    reference_flux: "NDArray",
    errors_measured: Optional["NDArray"] = None,
    errors_reference: Optional["NDArray"] = None,
    output: Optional[Union[str, Path]] = None,
    config: Optional[FigureConfig] = None,
    title: str = "Flux Comparison",
    measured_label: str = "DSA-110",
    reference_label: str = "Reference",
    show_ratio: bool = True,
) -> "Figure":
    """Plot measured vs reference flux comparison.
    
    Adapted from ASKAP-continuum-validation/report.py.
    
    Args:
        measured_flux: Measured flux densities
        reference_flux: Reference catalog flux densities
        errors_measured: Measured flux errors
        errors_reference: Reference flux errors
        output: Output file path
        config: Figure configuration
        title: Plot title
        measured_label: Label for measured data
        reference_label: Label for reference data
        show_ratio: Show flux ratio histogram
        
    Returns:
        matplotlib Figure object
    """
    _setup_matplotlib()
    import matplotlib.pyplot as plt
    from scipy import stats
    
    if config is None:
        config = FigureConfig(style=PlotStyle.QUICKLOOK)
    
    measured_flux = np.asarray(measured_flux)
    reference_flux = np.asarray(reference_flux)
    
    # Filter valid data
    mask = np.isfinite(measured_flux) & np.isfinite(reference_flux)
    mask &= (measured_flux > 0) & (reference_flux > 0)
    
    meas = measured_flux[mask]
    ref = reference_flux[mask]
    
    if show_ratio:
        fig, (ax1, ax2) = plt.subplots(
            1, 2, figsize=(config.figsize[0] * 2, config.figsize[1])
        )
    else:
        fig, ax1 = plt.subplots(figsize=config.figsize)
    
    # Scatter plot
    ax1.scatter(
        ref, meas,
        alpha=config.alpha, s=config.marker_size * 5,
        edgecolors="none"
    )
    
    # 1:1 line
    lims = [
        min(ref.min(), meas.min()) * 0.8,
        max(ref.max(), meas.max()) * 1.2
    ]
    ax1.plot(lims, lims, "k--", alpha=0.5, label="1:1")
    
    # Linear fit
    if len(meas) > 5:
        slope, intercept, r_value, _, _ = stats.linregress(np.log10(ref), np.log10(meas))
        fit_x = np.array(lims)
        fit_y = 10 ** (slope * np.log10(fit_x) + intercept)
        ax1.plot(
            fit_x, fit_y, "r-", alpha=0.7,
            label=f"Fit: slope={slope:.2f}, r²={r_value**2:.2f}"
        )
    
    ax1.set_xlim(lims)
    ax1.set_ylim(lims)
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel(f"{reference_label} Flux (Jy)", fontsize=config.effective_label_size)
    ax1.set_ylabel(f"{measured_label} Flux (Jy)", fontsize=config.effective_label_size)
    ax1.legend(fontsize=config.effective_tick_size)
    ax1.set_title(title, fontsize=config.effective_title_size)
    
    # Ratio histogram
    if show_ratio:
        ratio = meas / ref
        
        median_ratio = np.median(ratio)
        mad = np.median(np.abs(ratio - median_ratio))
        
        ax2.hist(
            ratio, bins=50, alpha=0.7,
            edgecolor="black", linewidth=0.5
        )
        ax2.axvline(1.0, color="black", linestyle="--", label="1.0")
        ax2.axvline(
            median_ratio, color="red", linestyle="-",
            label=f"Median: {median_ratio:.3f}"
        )
        ax2.axvline(
            median_ratio - mad, color="red", linestyle=":",
            alpha=0.7
        )
        ax2.axvline(
            median_ratio + mad, color="red", linestyle=":",
            alpha=0.7, label=f"MAD: {mad:.3f}"
        )
        
        ax2.set_xlabel(f"Flux Ratio ({measured_label}/{reference_label})", 
                       fontsize=config.effective_label_size)
        ax2.set_ylabel("Count", fontsize=config.effective_label_size)
        ax2.legend(fontsize=config.effective_tick_size)
        ax2.set_title("Flux Ratio Distribution", fontsize=config.effective_title_size)
    
    fig.tight_layout()
    
    if output:
        fig.savefig(output, dpi=config.dpi, bbox_inches="tight")
        logger.info(f"Saved comparison plot: {output}")
        plt.close(fig)
    
    return fig
