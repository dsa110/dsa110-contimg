"""
Generate images (.fits and .png) from sky models.

This module provides functions to visualize sky models by creating FITS images
and PNG visualizations.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm


def skymodel_to_image(
    sky: "SkyModel",
    *,
    image_size: Tuple[int, int] = (512, 512),
    pixel_scale_arcsec: float = 10.0,
    center_ra_deg: Optional[float] = None,
    center_dec_deg: Optional[float] = None,
    beam_fwhm_arcsec: Optional[float] = None,
) -> Tuple[np.ndarray, WCS]:
    """Convert sky model to 2D image array with WCS.
    
    Args:
        sky: pyradiosky SkyModel object
        image_size: (width, height) in pixels
        pixel_scale_arcsec: Pixel scale in arcseconds
        center_ra_deg: Center RA in degrees (default: mean of sources)
        center_dec_deg: Center Dec in degrees (default: mean of sources)
        beam_fwhm_arcsec: Optional beam FWHM for convolution (arcseconds)
        
    Returns:
        (image_array, wcs) tuple
    """
    try:
        from pyradiosky import SkyModel
    except ImportError:
        raise ImportError("pyradiosky is required")
    
    from astropy.convolution import Gaussian2DKernel, convolve
    
    width, height = image_size
    
    # Determine center if not provided
    if center_ra_deg is None or center_dec_deg is None:
        ras = [sky.skycoord[i].ra.deg for i in range(sky.Ncomponents)]
        decs = [sky.skycoord[i].dec.deg for i in range(sky.Ncomponents)]
        center_ra_deg = np.mean(ras)
        center_dec_deg = np.mean(decs)
    
    # Create WCS
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [width / 2, height / 2]
    wcs.wcs.crval = [center_ra_deg, center_dec_deg]
    wcs.wcs.cdelt = [
        -pixel_scale_arcsec / 3600.0,  # Negative for RA (east to west)
        pixel_scale_arcsec / 3600.0,    # Positive for Dec (north to south)
    ]
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    
    # Create empty image
    image = np.zeros((height, width))
    
    # Place sources
    for i in range(sky.Ncomponents):
        ra = sky.skycoord[i].ra.deg
        dec = sky.skycoord[i].dec.deg
        flux_jy = sky.stokes[0, 0, i].to('Jy').value
        
        # Convert RA/Dec to pixel coordinates
        world = np.array([[ra, dec]])
        pix = wcs.wcs_world2pix(world, 0)[0]
        x, y = pix[0], pix[1]
        
        # Check if within image bounds
        if 0 <= x < width and 0 <= y < height:
            # Place point source (delta function)
            x_int = int(round(x))
            y_int = int(round(y))
            if 0 <= x_int < width and 0 <= y_int < height:
                image[y_int, x_int] += flux_jy
    
    # Convolve with beam if specified
    if beam_fwhm_arcsec is not None:
        # Convert FWHM to sigma
        beam_sigma_pix = (beam_fwhm_arcsec / pixel_scale_arcsec) / (2 * np.sqrt(2 * np.log(2)))
        kernel = Gaussian2DKernel(beam_sigma_pix)
        image = convolve(image, kernel)
    
    return image, wcs


def write_skymodel_fits(
    sky: "SkyModel",
    output_path: str,
    *,
    image_size: Tuple[int, int] = (512, 512),
    pixel_scale_arcsec: float = 10.0,
    center_ra_deg: Optional[float] = None,
    center_dec_deg: Optional[float] = None,
    beam_fwhm_arcsec: Optional[float] = None,
) -> str:
    """Write sky model as FITS image.
    
    Args:
        sky: pyradiosky SkyModel object
        output_path: Path to output FITS file
        image_size: (width, height) in pixels
        pixel_scale_arcsec: Pixel scale in arcseconds
        center_ra_deg: Center RA in degrees
        center_dec_deg: Center Dec in degrees
        beam_fwhm_arcsec: Optional beam FWHM for convolution
        
    Returns:
        Path to created FITS file
    """
    image, wcs = skymodel_to_image(
        sky,
        image_size=image_size,
        pixel_scale_arcsec=pixel_scale_arcsec,
        center_ra_deg=center_ra_deg,
        center_dec_deg=center_dec_deg,
        beam_fwhm_arcsec=beam_fwhm_arcsec,
    )
    
    # Create FITS HDU
    hdu = fits.PrimaryHDU(data=image)
    hdu.header.update(wcs.to_header())
    hdu.header['BUNIT'] = 'Jy/pixel'
    hdu.header['BTYPE'] = 'Intensity'
    
    # Write FITS file
    hdu.writeto(output_path, overwrite=True)
    
    return output_path


def write_skymodel_png(
    sky: "SkyModel",
    output_path: str,
    *,
    image_size: Tuple[int, int] = (512, 512),
    pixel_scale_arcsec: float = 10.0,
    center_ra_deg: Optional[float] = None,
    center_dec_deg: Optional[float] = None,
    beam_fwhm_arcsec: Optional[float] = None,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    colormap: str = 'viridis',
) -> str:
    """Write sky model as PNG image.
    
    Args:
        sky: pyradiosky SkyModel object
        output_path: Path to output PNG file
        image_size: (width, height) in pixels
        pixel_scale_arcsec: Pixel scale in arcseconds
        center_ra_deg: Center RA in degrees
        center_dec_deg: Center Dec in degrees
        beam_fwhm_arcsec: Optional beam FWHM for convolution
        vmin: Minimum value for scaling (auto if None)
        vmax: Maximum value for scaling (auto if None)
        colormap: Matplotlib colormap name
        
    Returns:
        Path to created PNG file
    """
    image, wcs = skymodel_to_image(
        sky,
        image_size=image_size,
        pixel_scale_arcsec=pixel_scale_arcsec,
        center_ra_deg=center_ra_deg,
        center_dec_deg=center_dec_deg,
        beam_fwhm_arcsec=beam_fwhm_arcsec,
    )
    
    # Create figure
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection=wcs)
    
    # Determine scaling
    if vmin is None:
        vmin = np.max(image) * 1e-3 if np.max(image) > 0 else 1e-6
    if vmax is None:
        vmax = np.max(image) * 1.1 if np.max(image) > 0 else 1.0
    
    # Plot image
    im = ax.imshow(
        image,
        origin='lower',
        cmap=colormap,
        norm=LogNorm(vmin=vmin, vmax=vmax) if vmin > 0 else None,
        interpolation='nearest',
    )
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Flux (Jy/pixel)', rotation=270, labelpad=20)
    
    # Set labels
    ax.set_xlabel('RA')
    ax.set_ylabel('Dec')
    ax.set_title('Sky Model')
    
    # Add grid
    ax.grid(True, color='white', alpha=0.3)
    
    # Save
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return output_path


def write_skymodel_images(
    sky: "SkyModel",
    base_path: str,
    *,
    image_size: Tuple[int, int] = (512, 512),
    pixel_scale_arcsec: float = 10.0,
    center_ra_deg: Optional[float] = None,
    center_dec_deg: Optional[float] = None,
    beam_fwhm_arcsec: Optional[float] = None,
) -> Tuple[str, str]:
    """Write sky model as both FITS and PNG images.
    
    Args:
        sky: pyradiosky SkyModel object
        base_path: Base path (will add .fits and .png extensions)
        image_size: (width, height) in pixels
        pixel_scale_arcsec: Pixel scale in arcseconds
        center_ra_deg: Center RA in degrees
        center_dec_deg: Center Dec in degrees
        beam_fwhm_arcsec: Optional beam FWHM for convolution
        
    Returns:
        (fits_path, png_path) tuple
    """
    fits_path = base_path if base_path.endswith('.fits') else base_path + '.fits'
    png_path = base_path if base_path.endswith('.png') else base_path + '.png'
    
    write_skymodel_fits(
        sky,
        fits_path,
        image_size=image_size,
        pixel_scale_arcsec=pixel_scale_arcsec,
        center_ra_deg=center_ra_deg,
        center_dec_deg=center_dec_deg,
        beam_fwhm_arcsec=beam_fwhm_arcsec,
    )
    
    write_skymodel_png(
        sky,
        png_path,
        image_size=image_size,
        pixel_scale_arcsec=pixel_scale_arcsec,
        center_ra_deg=center_ra_deg,
        center_dec_deg=center_dec_deg,
        beam_fwhm_arcsec=beam_fwhm_arcsec,
    )
    
    return fits_path, png_path

