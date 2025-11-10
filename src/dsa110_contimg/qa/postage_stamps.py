"""
Postage stamp visualization for DSA-110 sources.

Adopted from VAST Tools for creating image cutouts around source positions
and displaying them in a grid layout for visual verification of ESE candidates.

Reference: archive/references/vast-tools/vasttools/source.py
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from astropy.io import fits
from astropy.wcs import WCS
from astropy.nddata.utils import Cutout2D
from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.visualization import (
    ZScaleInterval,
    ImageNormalize,
    PercentileInterval,
    AsinhStretch,
    LinearStretch,
)

from dsa110_contimg.photometry.source import Source

logger = logging.getLogger(__name__)


def create_cutout(
    fits_path: Path,
    ra_deg: float,
    dec_deg: float,
    size_arcmin: float = 2.0
) -> Tuple[np.ndarray, WCS, Dict[str, Any]]:
    """
    Create image cutout around source position.
    
    Args:
        fits_path: Path to FITS image file
        ra_deg: Right ascension in degrees
        dec_deg: Declination in degrees
        size_arcmin: Cutout size in arcminutes (default: 2.0)
    
    Returns:
        Tuple of (cutout_data, cutout_wcs, metadata)
        - cutout_data: 2D numpy array of cutout image
        - cutout_wcs: WCS object for cutout
        - metadata: Dictionary with header info, beam parameters, etc.
    
    Raises:
        FileNotFoundError: If FITS file doesn't exist
        ValueError: If coordinates are invalid or cutout fails
    """
    fits_path = Path(fits_path)
    if not fits_path.exists():
        raise FileNotFoundError(f"FITS file not found: {fits_path}")
    
    coord = SkyCoord(ra_deg, dec_deg, unit=(u.deg, u.deg))
    size = size_arcmin * u.arcmin
    
    try:
        with fits.open(fits_path) as hdul:
            # Get data (handle multi-dimensional arrays)
            data = hdul[0].data
            if data is None:
                raise ValueError(f"No data in FITS file: {fits_path}")
            
            # Squeeze out singleton dimensions
            data = np.asarray(data).squeeze()
            
            # Handle 3D/4D arrays (stokes, freq, ra, dec)
            if data.ndim > 2:
                # Take first channel/stokes
                data = data[0] if data.ndim == 3 else data[0, 0]
            
            if data.ndim != 2:
                raise ValueError(f"Expected 2D data, got {data.ndim}D")
            
            # Get WCS (use celestial WCS for 2D)
            header = hdul[0].header
            wcs = WCS(header).celestial
            
            # Create cutout
            cutout = Cutout2D(data, coord, size, wcs=wcs, mode='partial')
            
            # Extract metadata
            metadata = {
                'header': header,
                'beam_major_arcsec': header.get('BMAJ', None),
                'beam_minor_arcsec': header.get('BMIN', None),
                'beam_pa_deg': header.get('BPA', None),
                'bunit': header.get('BUNIT', 'Jy/beam'),
                'original_shape': data.shape,
                'cutout_shape': cutout.data.shape,
            }
            
            return cutout.data, cutout.wcs_celestial, metadata
            
    except Exception as e:
        raise ValueError(f"Failed to create cutout from {fits_path}: {e}") from e


def normalize_cutout(
    data: np.ndarray,
    method: str = 'zscale',
    percentile: float = 99.9,
    contrast: float = 0.2,
    stretch: str = 'asinh'
) -> ImageNormalize:
    """
    Create normalization for cutout display.
    
    Args:
        data: 2D image data
        method: Normalization method ('zscale' or 'percentile')
        percentile: Percentile for percentile normalization
        contrast: Contrast for zscale normalization
        stretch: Stretch function ('asinh' or 'linear')
    
    Returns:
        ImageNormalize object
    """
    # Filter out NaN/Inf values
    valid_data = data[np.isfinite(data)]
    
    if len(valid_data) == 0:
        # Fallback to simple normalization
        return ImageNormalize(
            data=data,
            interval=PercentileInterval(99.0),
            stretch=LinearStretch()
        )
    
    # Choose interval
    if method == 'zscale':
        interval = ZScaleInterval(contrast=contrast)
    else:
        interval = PercentileInterval(percentile)
    
    # Choose stretch
    if stretch == 'asinh':
        stretch_func = AsinhStretch()
    else:
        stretch_func = LinearStretch()
    
    return ImageNormalize(data=data, interval=interval, stretch=stretch_func)


def plot_cutout(
    data: np.ndarray,
    wcs: WCS,
    ax: Optional[plt.Axes] = None,
    title: Optional[str] = None,
    show_beam: bool = True,
    show_coords: bool = True,
    normalize: Optional[ImageNormalize] = None,
    cmap: str = 'viridis',
    metadata: Optional[Dict[str, Any]] = None,
    **kwargs
) -> plt.Axes:
    """
    Plot a single cutout on an axes.
    
    Args:
        data: 2D image data
        wcs: WCS object for cutout
        ax: Matplotlib axes with WCS projection (creates new if None)
        title: Plot title
        show_beam: Show beam ellipse
        show_coords: Show coordinate labels
        normalize: ImageNormalize object (auto-created if None)
        cmap: Colormap name
        metadata: Dictionary with beam parameters and other metadata
        **kwargs: Additional arguments passed to imshow
    
    Returns:
        Matplotlib axes object
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={'projection': wcs})
    
    # Create normalization if not provided
    if normalize is None:
        normalize = normalize_cutout(data)
    
    # Plot image
    im = ax.imshow(data, origin='lower', cmap=cmap, norm=normalize, **kwargs)
    
    # Add colorbar
    plt.colorbar(im, ax=ax, label='Flux (Jy/beam)')
    
    # Add beam ellipse if metadata available
    if show_beam and metadata:
        bmaj = metadata.get('beam_major_arcsec')
        bmin = metadata.get('beam_minor_arcsec')
        bpa = metadata.get('beam_pa_deg')
        
        if bmaj and bmin:
            # Convert arcsec to degrees
            bmaj_deg = bmaj / 3600.0
            
            # Get center pixel
            center_pix = (data.shape[0] // 2, data.shape[1] // 2)
            
            # Estimate pixel scale (degrees per pixel)
            try:
                pixel_scale_deg = np.abs(wcs.pixel_scale_matrix[0, 0])
            except AttributeError:
                # Fallback: estimate from WCS
                try:
                    cdelt = wcs.wcs.cdelt[0]
                    pixel_scale_deg = abs(cdelt)
                except:
                    pixel_scale_deg = 0.001  # Default fallback
            
            # Create beam circle (simplified - just show size)
            beam_size_pix = bmaj_deg / pixel_scale_deg
            circle = Circle(
                center_pix[::-1],  # (x, y) for matplotlib
                radius=beam_size_pix / 2,
                fill=False,
                edgecolor='white',
                linewidth=1.5,
                linestyle='--',
                alpha=0.8
            )
            ax.add_patch(circle)
    
    # Set labels
    if show_coords and hasattr(ax, 'coords'):
        try:
            ax.coords[0].set_axislabel('RA')
            ax.coords[1].set_axislabel('Dec')
            ax.coords[0].set_major_formatter('hh:mm:ss')
            ax.coords[1].set_major_formatter('dd:mm:ss')
        except Exception:
            # Fallback if WCS projection not available
            ax.set_xlabel('RA')
            ax.set_ylabel('Dec')
    
    if title:
        ax.set_title(title, fontsize=10)
    
    return ax


def show_all_cutouts(
    source: Source,
    size_arcmin: float = 2.0,
    columns: int = 5,
    figsize: Optional[Tuple[int, int]] = None,
    save: bool = False,
    outfile: Optional[str] = None,
    normalize_method: str = 'zscale',
    show_beam: bool = True,
    plot_dpi: int = 150
) -> Optional[plt.Figure]:
    """
    Display all cutouts for a source in a grid layout.
    
    Adopted from VAST Tools Source.show_all_png_cutouts().
    
    Args:
        source: Source object with measurements
        size_arcmin: Cutout size in arcminutes
        columns: Number of columns in grid
        figsize: Figure size tuple (auto-calculated if None)
        save: Save figure instead of returning
        outfile: Output filename (auto-generated if None)
        normalize_method: Normalization method ('zscale' or 'percentile')
        show_beam: Show beam ellipse on each cutout
        plot_dpi: DPI for saved figure
    
    Returns:
        matplotlib.figure.Figure if save=False, None otherwise
    
    Raises:
        ValueError: If source has no measurements or images
    """
    if source.measurements.empty:
        raise ValueError(f"Source {source.source_id} has no measurements")
    
    # Filter measurements with valid image paths
    valid_measurements = source.measurements[
        source.measurements['image_path'].notna()
    ].copy()
    
    if valid_measurements.empty:
        raise ValueError(f"Source {source.source_id} has no valid image paths")
    
    n_images = len(valid_measurements)
    rows = int(np.ceil(n_images / columns))
    
    # Calculate figure size if not provided
    if figsize is None:
        width = columns * 3
        height = rows * 3
        figsize = (width, height)
    
    fig = plt.figure(figsize=figsize, dpi=plot_dpi)
    
    # Create shared normalization from first detection (if available)
    shared_norm = None
    first_data = None
    
    # Plot each cutout
    for idx, (_, row) in enumerate(valid_measurements.iterrows()):
        image_path = Path(row['image_path'])
        
        # Get time label
        if 'mjd' in row and pd.notna(row['mjd']):
            from astropy.time import Time
            time_label = f"MJD {row['mjd']:.1f}"
        elif 'measured_at' in row and pd.notna(row['measured_at']):
            time_label = f"{row['measured_at']}"
        else:
            time_label = f"Epoch {idx + 1}"
        
        try:
            # Create cutout
            cutout_data, cutout_wcs, metadata = create_cutout(
                image_path,
                source.ra_deg,
                source.dec_deg,
                size_arcmin=size_arcmin
            )
            
            # Create normalization (use shared if available)
            if shared_norm is None:
                shared_norm = normalize_cutout(cutout_data, method=normalize_method)
                first_data = cutout_data
            
            # Create subplot with WCS projection
            ax = plt.subplot(rows, columns, idx + 1, projection=cutout_wcs)
            
            # Plot cutout
            ax = plot_cutout(
                cutout_data,
                cutout_wcs,
                ax=ax,
                title=time_label,
                show_beam=show_beam,
                normalize=shared_norm,
                metadata=metadata
            )
            
        except Exception as e:
            logger.warning(f"Failed to create cutout for {image_path}: {e}")
            ax = plt.subplot(rows, columns, idx + 1)
            ax.text(0.5, 0.5, f"Error\n{str(e)[:30]}", 
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title(time_label)
            ax.axis('off')
    
    # Add overall title
    fig.suptitle(f'Postage Stamps: {source.name}', fontsize=14, y=0.995)
    
    plt.tight_layout()
    
    if save:
        if outfile is None:
            safe_name = source.source_id.replace(' ', '_').replace('/', '_')
            outfile = f"{safe_name}_postage_stamps.png"
        fig.savefig(outfile, dpi=plot_dpi, bbox_inches='tight')
        logger.info(f"Saved postage stamps to {outfile}")
        plt.close(fig)
        return None
    
    return fig


# Add method to Source class via monkey-patching or extension
def _source_show_all_cutouts(
    self: Source,
    size_arcmin: float = 2.0,
    columns: int = 5,
    figsize: Optional[Tuple[int, int]] = None,
    save: bool = False,
    outfile: Optional[str] = None,
    normalize_method: str = 'zscale',
    show_beam: bool = True,
    plot_dpi: int = 150
) -> Optional[plt.Figure]:
    """Show all cutouts for this source (added to Source class)."""
    return show_all_cutouts(
        self,
        size_arcmin=size_arcmin,
        columns=columns,
        figsize=figsize,
        save=save,
        outfile=outfile,
        normalize_method=normalize_method,
        show_beam=show_beam,
        plot_dpi=plot_dpi
    )


# Monkey-patch Source class to add this method
Source.show_all_cutouts = _source_show_all_cutouts

