"""
Calibration diagnostic plotting utilities.

Provides functions for:
- Bandpass solutions (amplitude, phase vs frequency)
- Gain solutions (amplitude, phase vs time)
- Delay solutions
- Dynamic spectra / waterfalls

Adapted from:
- dsa110-calib/dsacalib/plotting.py (Dana Simard)
- dsa110_contimg/calibration/plotting.py (existing CASA plotbandpass wrapper)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

import numpy as np

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from numpy.typing import NDArray

from dsa110_contimg.visualization.config import FigureConfig, PlotStyle

logger = logging.getLogger(__name__)


def _setup_matplotlib() -> None:
    """Configure matplotlib for headless operation."""
    import matplotlib
    matplotlib.use("Agg")


def plot_bandpass(
    caltable: Union[str, Path],
    output: Optional[Union[str, Path]] = None,
    config: Optional[FigureConfig] = None,
    plot_amplitude: bool = True,
    plot_phase: bool = True,
    antenna: Optional[str] = None,
    spw: Optional[int] = None,
) -> list[Path]:
    """Plot bandpass calibration solutions.
    
    Generates per-SPW plots showing amplitude and phase vs frequency.
    
    Args:
        caltable: Path to CASA bandpass calibration table
        output: Output directory or file prefix
        config: Figure configuration
        plot_amplitude: Generate amplitude plot
        plot_phase: Generate phase plot
        antenna: Specific antenna to plot (default: all)
        spw: Specific spectral window (default: all)
        
    Returns:
        List of generated plot file paths
    """
    _setup_matplotlib()
    
    if config is None:
        config = FigureConfig(style=PlotStyle.QUICKLOOK)
    
    caltable = Path(caltable)
    if output is None:
        output = caltable.parent / f"{caltable.name}_plots"
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    
    generated = []
    
    try:
        # Try CASA plotbandpass first (higher quality)
        # Import with CASA log environment protection
        try:
            from dsa110_contimg.utils.tempdirs import casa_log_environment
            with casa_log_environment():
                from casatasks import plotbandpass
        except ImportError:
            from casatasks import plotbandpass
        
        if plot_amplitude:
            amp_plot = str(output / f"{caltable.name}_amp")
            # Wrap plotbandpass call
            try:
                from dsa110_contimg.utils.tempdirs import casa_log_environment
                with casa_log_environment():
                    plotbandpass(
                caltable=str(caltable),
                xaxis="freq",
                yaxis="amp",
                figfile=amp_plot,
                interactive=False,
                showflagged=False,
                overlay="antenna" if antenna is None else "",
                antenna=antenna or "",
                spw=str(spw) if spw is not None else "",
            )
            # Find generated files
            for f in output.glob(f"{caltable.name}_amp*.png"):
                generated.append(f)
        
        if plot_phase:
            phase_plot = str(output / f"{caltable.name}_phase")
            plotbandpass(
                caltable=str(caltable),
                xaxis="freq",
                yaxis="phase",
                figfile=phase_plot,
                interactive=False,
                showflagged=False,
                overlay="antenna" if antenna is None else "",
                antenna=antenna or "",
                spw=str(spw) if spw is not None else "",
                plotrange=[0, 0, -180, 180],
            )
            for f in output.glob(f"{caltable.name}_phase*.png"):
                generated.append(f)
                
    except ImportError:
        logger.warning("CASA not available, using fallback plotting")
        generated = _plot_bandpass_fallback(
            caltable, output, config, plot_amplitude, plot_phase
        )
    except Exception as e:
        logger.error(f"plotbandpass failed: {e}, using fallback")
        generated = _plot_bandpass_fallback(
            caltable, output, config, plot_amplitude, plot_phase
        )
    
    logger.info(f"Generated {len(generated)} bandpass plots in {output}")
    return generated


def _plot_bandpass_fallback(
    caltable: Path,
    output: Path,
    config: FigureConfig,
    plot_amplitude: bool,
    plot_phase: bool,
) -> list[Path]:
    """Fallback bandpass plotting using casacore directly."""
    import matplotlib.pyplot as plt
    
    generated = []
    
    try:
        from casacore.tables import table
        
        with table(str(caltable), readonly=True) as tb:
            cparam = tb.getcol("CPARAM")  # Complex gains
            freq = tb.getcol("CHAN_FREQ") if "CHAN_FREQ" in tb.colnames() else None
            antenna1 = tb.getcol("ANTENNA1")
        
        nant = len(np.unique(antenna1))
        nchan = cparam.shape[1]
        _npol = cparam.shape[2]  # Stored for potential future use
        
        # Frequency axis
        if freq is None:
            freq = np.arange(nchan)
            freq_label = "Channel"
        else:
            freq = freq[0] / 1e9  # Convert to GHz
            freq_label = "Frequency (GHz)"
        
        # Plot amplitude
        if plot_amplitude:
            fig, axes = plt.subplots(
                2, 1, figsize=(config.figsize[0], config.figsize[1] * 2),
                sharex=True
            )
            
            for pol_idx, pol_label in enumerate(["Pol A", "Pol B"]):
                ax = axes[pol_idx]
                for ant in range(min(nant, 10)):  # Limit to first 10 antennas
                    amp = np.abs(cparam[ant, :, pol_idx])
                    ax.plot(freq, amp, alpha=0.7, label=f"Ant {ant}")
                ax.set_ylabel("Amplitude")
                ax.set_title(pol_label)
                ax.legend(ncol=5, fontsize=8)
            
            axes[-1].set_xlabel(freq_label)
            fig.suptitle(f"Bandpass: {caltable.name}")
            fig.tight_layout()
            
            amp_path = output / f"{caltable.name}_amp_fallback.png"
            fig.savefig(amp_path, dpi=config.dpi, bbox_inches="tight")
            plt.close(fig)
            generated.append(amp_path)
        
        # Plot phase
        if plot_phase:
            fig, axes = plt.subplots(
                2, 1, figsize=(config.figsize[0], config.figsize[1] * 2),
                sharex=True
            )
            
            for pol_idx, pol_label in enumerate(["Pol A", "Pol B"]):
                ax = axes[pol_idx]
                for ant in range(min(nant, 10)):
                    phase = np.angle(cparam[ant, :, pol_idx], deg=True)
                    ax.plot(freq, phase, alpha=0.7, label=f"Ant {ant}")
                ax.set_ylabel("Phase (deg)")
                ax.set_ylim(-180, 180)
                ax.set_title(pol_label)
                ax.legend(ncol=5, fontsize=8)
            
            axes[-1].set_xlabel(freq_label)
            fig.suptitle(f"Bandpass Phase: {caltable.name}")
            fig.tight_layout()
            
            phase_path = output / f"{caltable.name}_phase_fallback.png"
            fig.savefig(phase_path, dpi=config.dpi, bbox_inches="tight")
            plt.close(fig)
            generated.append(phase_path)
            
    except Exception as e:
        logger.error(f"Fallback bandpass plotting failed: {e}")
    
    return generated


def plot_gains(
    caltable: Union[str, Path],
    output: Optional[Union[str, Path]] = None,
    config: Optional[FigureConfig] = None,
    plot_amplitude: bool = True,
    plot_phase: bool = True,
) -> list[Path]:
    """Plot gain calibration solutions vs time.
    
    Args:
        caltable: Path to CASA gain calibration table
        output: Output directory or file prefix
        config: Figure configuration
        plot_amplitude: Generate amplitude plot
        plot_phase: Generate phase plot
        
    Returns:
        List of generated plot file paths
    """
    _setup_matplotlib()
    import matplotlib.pyplot as plt
    
    if config is None:
        config = FigureConfig(style=PlotStyle.QUICKLOOK)
    
    caltable = Path(caltable)
    if output is None:
        output = caltable.parent / f"{caltable.name}_plots"
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    
    generated = []
    
    try:
        from casacore.tables import table
        
        with table(str(caltable), readonly=True) as tb:
            cparam = tb.getcol("CPARAM")
            time = tb.getcol("TIME")
            antenna1 = tb.getcol("ANTENNA1")
        
        # Convert time to minutes from start
        time_min = (time - time.min()) / 60.0
        
        nant = len(np.unique(antenna1))
        _npol = cparam.shape[-1]  # Stored for potential future use
        
        # Plot amplitude
        if plot_amplitude:
            fig, axes = plt.subplots(
                2, 1, figsize=(config.figsize[0], config.figsize[1] * 2),
                sharex=True
            )
            
            for pol_idx, pol_label in enumerate(["Pol A", "Pol B"]):
                ax = axes[pol_idx]
                for ant in range(min(nant, 10)):
                    mask = antenna1 == ant
                    amp = np.abs(cparam[mask, 0, pol_idx])
                    t = time_min[mask]
                    ax.plot(t, amp, ".", alpha=0.7, label=f"Ant {ant}")
                ax.set_ylabel("Amplitude")
                ax.set_title(pol_label)
                ax.legend(ncol=5, fontsize=8)
            
            axes[-1].set_xlabel("Time (minutes)")
            fig.suptitle(f"Gains: {caltable.name}")
            fig.tight_layout()
            
            amp_path = output / f"{caltable.name}_gain_amp.png"
            fig.savefig(amp_path, dpi=config.dpi, bbox_inches="tight")
            plt.close(fig)
            generated.append(amp_path)
        
        # Plot phase
        if plot_phase:
            fig, axes = plt.subplots(
                2, 1, figsize=(config.figsize[0], config.figsize[1] * 2),
                sharex=True
            )
            
            for pol_idx, pol_label in enumerate(["Pol A", "Pol B"]):
                ax = axes[pol_idx]
                for ant in range(min(nant, 10)):
                    mask = antenna1 == ant
                    phase = np.angle(cparam[mask, 0, pol_idx], deg=True)
                    t = time_min[mask]
                    ax.plot(t, phase, ".", alpha=0.7, label=f"Ant {ant}")
                ax.set_ylabel("Phase (deg)")
                ax.set_ylim(-180, 180)
                ax.set_title(pol_label)
                ax.legend(ncol=5, fontsize=8)
            
            axes[-1].set_xlabel("Time (minutes)")
            fig.suptitle(f"Gain Phase: {caltable.name}")
            fig.tight_layout()
            
            phase_path = output / f"{caltable.name}_gain_phase.png"
            fig.savefig(phase_path, dpi=config.dpi, bbox_inches="tight")
            plt.close(fig)
            generated.append(phase_path)
            
    except Exception as e:
        logger.error(f"Gain plotting failed: {e}")
    
    logger.info(f"Generated {len(generated)} gain plots")
    return generated


def plot_delays(
    delay_data: "NDArray",
    delay_axis: "NDArray",
    baseline_names: list[str],
    output: Optional[Union[str, Path]] = None,
    config: Optional[FigureConfig] = None,
    labels: Optional[list[str]] = None,
) -> "Figure":
    """Plot visibility amplitude vs delay (fringe search).
    
    Adapted from dsacalib/plotting.py plot_delays().
    
    Args:
        delay_data: Complex visibilities FFT'd along freq axis, shape (nvis, nbl, ndelay, npol)
        delay_axis: Delay values in nanoseconds
        baseline_names: List of baseline labels
        output: Output file path
        config: Figure configuration
        labels: Labels for each visibility type
        
    Returns:
        matplotlib Figure object
    """
    _setup_matplotlib()
    import matplotlib.pyplot as plt
    
    if config is None:
        config = FigureConfig(style=PlotStyle.QUICKLOOK)
    
    nvis = delay_data.shape[0]
    nbl = delay_data.shape[1]
    npol = delay_data.shape[-1]
    
    if labels is None:
        labels = [f"Vis {i}" for i in range(nvis)]
    
    # Compute peak delays
    delays = delay_axis[np.argmax(np.abs(delay_data), axis=2)]
    
    # Layout
    nx = min(nbl, 5)
    ny = (nbl + nx - 1) // nx
    
    alpha = 0.5 if nvis > 2 else 1.0
    
    for pol_idx in range(npol):
        pol_label = "B" if pol_idx else "A"
        
        fig, axes = plt.subplots(
            ny, nx, figsize=(config.figsize[0] * nx / 2, config.figsize[1] * ny / 2),
            sharex=True
        )
        axes = np.atleast_2d(axes).flatten()
        
        for bl_idx in range(nbl):
            ax = axes[bl_idx]
            ax.axvline(0, color="gray", linestyle="--", alpha=0.5)
            
            for vis_idx in range(nvis):
                ax.plot(
                    delay_axis,
                    np.log10(np.abs(delay_data[vis_idx, bl_idx, :, pol_idx]) + 1e-10),
                    label=labels[vis_idx],
                    alpha=alpha,
                )
                ax.axvline(delays[vis_idx, bl_idx, pol_idx], color="red", alpha=0.5)
            
            ax.text(
                0.05, 0.95, f"{baseline_names[bl_idx]}: {pol_label}",
                transform=ax.transAxes, fontsize=10, verticalalignment="top"
            )
        
        axes[0].legend(fontsize=8)
        
        for ax in axes[-(nx):]:
            ax.set_xlabel("Delay (ns)")
        
        fig.suptitle(f"Delay Search - Pol {pol_label}")
        fig.tight_layout()
        
        if output:
            out_path = Path(output).with_suffix(f".pol{pol_label}.png")
            fig.savefig(out_path, dpi=config.dpi, bbox_inches="tight")
            plt.close(fig)
            logger.info(f"Saved delay plot: {out_path}")
    
    return fig


def plot_dynamic_spectrum(
    vis: "NDArray",
    freq_ghz: "NDArray",
    mjd: "NDArray",
    baseline_names: list[str],
    output: Optional[Union[str, Path]] = None,
    config: Optional[FigureConfig] = None,
    normalize: bool = False,
    vmin: float = -100,
    vmax: float = 100,
) -> "Figure":
    """Plot dynamic spectrum (waterfall) of visibilities.
    
    Adapted from dsacalib/plotting.py plot_dyn_spec().
    
    Args:
        vis: Visibilities, shape (nbl, ntime, nfreq, npol)
        freq_ghz: Frequency array in GHz
        mjd: Time array in MJD
        baseline_names: List of baseline labels
        output: Output file path
        config: Figure configuration
        normalize: Normalize visibilities by amplitude
        vmin: Minimum display value
        vmax: Maximum display value
        
    Returns:
        matplotlib Figure object
    """
    _setup_matplotlib()
    import matplotlib.pyplot as plt
    import astropy.units as u
    
    if config is None:
        config = FigureConfig(style=PlotStyle.QUICKLOOK)
    
    nbl, nt, nf, npol = vis.shape
    
    # Layout
    nx = min(nbl, 5)
    ny = (nbl * 2 + nx - 1) // nx
    
    # Rebin if needed
    if nt > 125:
        vis_plot = np.nanmean(
            vis[:, :nt // 125 * 125, ...].reshape(nbl, 125, -1, nf, npol), 2
        )
        t_plot = mjd[:nt // 125 * 125].reshape(125, -1).mean(-1)
    else:
        vis_plot = vis.copy()
        t_plot = mjd
    
    if nf > 125:
        vis_plot = np.nanmean(
            vis_plot[:, :, :nf // 125 * 125, :].reshape(nbl, vis_plot.shape[1], 125, -1, npol), 3
        )
        f_plot = freq_ghz[:nf // 125 * 125].reshape(125, -1).mean(-1)
    else:
        f_plot = freq_ghz
    
    # Normalize
    dplot = vis_plot.real
    norm_factor = dplot.reshape(nbl, -1, npol).mean(axis=1)[:, np.newaxis, np.newaxis, :]
    dplot = dplot / np.where(norm_factor != 0, norm_factor, 1)
    
    if normalize:
        dplot = dplot / np.abs(dplot)
        vmin, vmax = -1, 1
    
    dplot = dplot - 1
    
    # Time axis in minutes
    t_min = ((t_plot - t_plot[0]) * u.d).to_value(u.min)
    
    fig, axes = plt.subplots(ny, nx, figsize=(8 * nx, 8 * ny))
    axes = np.atleast_2d(axes).flatten()
    
    for bl_idx in range(nbl):
        for pol_idx in range(npol):
            ax_idx = pol_idx * nbl + bl_idx
            ax = axes[ax_idx]
            
            ax.imshow(
                dplot[bl_idx, :, :, pol_idx].T,
                origin="lower",
                interpolation="none",
                aspect="auto",
                vmin=vmin,
                vmax=vmax,
                extent=[t_min[0], t_min[-1], f_plot[0], f_plot[-1]],
                cmap="RdBu_r",
            )
            ax.text(
                0.05, 0.95,
                f"{baseline_names[bl_idx]}, pol {'B' if pol_idx else 'A'}",
                transform=ax.transAxes, fontsize=14, color="white",
                verticalalignment="top"
            )
    
    # Axis labels
    for ax in axes[-(nx):]:
        ax.set_xlabel("Time (min)")
    for ax in axes[::nx]:
        ax.set_ylabel("Freq (GHz)")
    
    fig.tight_layout()
    
    if output:
        fig.savefig(output, dpi=config.dpi, bbox_inches="tight")
        logger.info(f"Saved dynamic spectrum: {output}")
        plt.close(fig)
    
    return fig
