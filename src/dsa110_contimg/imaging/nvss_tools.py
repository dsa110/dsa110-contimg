"""
NVSS catalog tools for imaging: masks and overlays.
"""

from __future__ import annotations

import os
from typing import Tuple, Optional

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
import astropy.units as u


def image_center_and_radius_deg(hdr) -> Tuple[SkyCoord, float]:
    """Get image center and radius in degrees."""
    w = WCS(hdr).celestial
    nx = int(hdr.get('NAXIS1', 0))
    ny = int(hdr.get('NAXIS2', 0))
    if nx <= 0 or ny <= 0:
        raise ValueError('Invalid image dimensions')
    cx, cy = (nx - 1) / 2.0, (ny - 1) / 2.0
    ctr = w.pixel_to_world(cx, cy)
    scales = proj_plane_pixel_scales(w)  # deg/pixel
    fov_ra = float(scales[0] * nx)
    fov_dec = float(scales[1] * ny)
    half_diag = 0.5 * float(np.hypot(fov_ra, fov_dec))
    return ctr, half_diag


def create_nvss_mask(image_path: str, min_mjy: float, radius_arcsec: float,
                     out_path: str) -> None:
    """Create CRTF mask with circular regions centered on NVSS sources."""
    hdr = fits.getheader(image_path)
    center, radius_deg = image_center_and_radius_deg(hdr)

    # Load NVSS catalog and select sources in FoV above threshold
    from dsa110_contimg.calibration.catalogs import read_nvss_catalog
    df = read_nvss_catalog()
    sc = SkyCoord(df['ra'].values * u.deg,
                  df['dec'].values * u.deg, frame='icrs')
    sep = sc.separation(center).deg
    m = (sep <= radius_deg) & (np.asarray(
        df['flux_20_cm'].values, float) >= float(min_mjy))
    sub = df.loc[m, ['ra', 'dec']].astype(float).to_numpy()

    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'w') as f:
        f.write('#CRTFv0\n')
        for ra_deg, dec_deg in sub:
            src = SkyCoord(ra_deg * u.deg, dec_deg * u.deg, frame='icrs')
            ra_str = src.ra.to_string(
                unit=u.hourangle, sep=':', precision=2, pad=True)
            dec_str = src.dec.to_string(
                unit=u.deg, sep=':', precision=2, pad=True, alwayssign=True)
            f.write(
                f"circle[[{ra_str}, {dec_str}], {float(radius_arcsec):.3f}arcsec]\n")


def _image_fov_deg(header) -> Tuple[float, float, SkyCoord]:
    """Get image field of view in degrees and center."""
    w = WCS(header)
    nx = int(header.get('NAXIS1', 0))
    ny = int(header.get('NAXIS2', 0))
    if nx <= 0 or ny <= 0:
        raise ValueError('Invalid image dimensions')
    # pixel corners -> sky
    corners = np.array(
        [[0, 0], [nx-1, 0], [0, ny-1], [nx-1, ny-1]], dtype=float)
    sky = w.pixel_to_world(corners[:, 0], corners[:, 1])
    ra = sky.ra.wrap_at(180*u.deg).deg
    dec = sky.dec.deg
    ra_span = float(np.max(ra) - np.min(ra))
    dec_span = float(np.max(dec) - np.min(dec))
    # center
    cx, cy = (nx-1)/2.0, (ny-1)/2.0
    ctr = w.pixel_to_world(cx, cy)
    return ra_span, dec_span, ctr


def _load_pb_mask(pb_path: str, pblimit: float) -> Optional[np.ndarray]:
    """Load primary beam mask."""
    if not pb_path:
        return None
    try:
        pb = fits.getdata(pb_path)
        while pb.ndim > 2:
            pb = pb[0]
        m = np.isfinite(pb) & (pb >= float(pblimit))
        return m
    except Exception:
        return None


def create_nvss_fits_mask(
    imagename: str,
    imsize: int,
    cell_arcsec: float,
    ra0_deg: float,
    dec0_deg: float,
    nvss_min_mjy: float,
    radius_arcsec: float = 60.0,
    out_path: Optional[str] = None,
) -> str:
    """Create FITS mask from NVSS sources for WSClean.

    Creates a FITS mask file with circular regions around NVSS sources.
    Zero values = not cleaned, non-zero values = cleaned.

    Args:
        imagename: Base image name (used to determine output path)
        imsize: Image size in pixels
        cell_arcsec: Pixel scale in arcseconds
        ra0_deg: Phase center RA in degrees
        dec0_deg: Phase center Dec in degrees
        nvss_min_mjy: Minimum NVSS flux in mJy
        radius_arcsec: Mask radius around each source in arcseconds
        out_path: Optional output path (defaults to {imagename}.nvss_mask.fits)

    Returns:
        Path to created FITS mask file
    """
    # Create WCS for mask
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [imsize / 2.0, imsize / 2.0]
    wcs.wcs.crval = [ra0_deg, dec0_deg]
    # Negative RA for standard convention
    wcs.wcs.cdelt = [-cell_arcsec / 3600.0, cell_arcsec / 3600.0]
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]

    # Initialize mask (all zeros = not cleaned)
    mask = np.zeros((imsize, imsize), dtype=np.float32)

    # Query NVSS sources
    from dsa110_contimg.calibration.catalogs import read_nvss_catalog
    df = read_nvss_catalog()
    sc = SkyCoord(df['ra'].values * u.deg,
                  df['dec'].values * u.deg, frame='icrs')
    center = SkyCoord(ra0_deg * u.deg, dec0_deg * u.deg, frame='icrs')

    # Calculate FoV radius
    fov_radius_deg = (cell_arcsec * imsize) / 3600.0 / 2.0
    sep = sc.separation(center).deg
    flux_mjy = np.asarray(df['flux_20_cm'].values, float)

    # Select sources within FoV and above threshold
    keep = (sep <= fov_radius_deg) & (flux_mjy >= float(nvss_min_mjy))
    sources = df.loc[keep]

    if len(sources) == 0:
        # No sources found, create empty mask
        if out_path is None:
            out_path = f"{imagename}.nvss_mask.fits"
        from dsa110_contimg.utils.fits_utils import create_fits_hdu
        header = wcs.to_header()
        hdu = create_fits_hdu(data=mask, header=header, fix_cdelt=True)
        hdu.writeto(out_path, overwrite=True)
        return out_path

    # Create circular masks for each source
    radius_pixels = radius_arcsec / cell_arcsec

    for _, row in sources.iterrows():
        coord = SkyCoord(row['ra'] * u.deg, row['dec'] * u.deg, frame='icrs')
        x, y = wcs.world_to_pixel(coord)

        # Skip if outside image bounds
        if x < 0 or x >= imsize or y < 0 or y >= imsize:
            continue

        # Create circular mask
        y_grid, x_grid = np.ogrid[:imsize, :imsize]
        dist_sq = (x_grid - x)**2 + (y_grid - y)**2
        mask[dist_sq <= radius_pixels**2] = 1.0

    # Write FITS mask
    if out_path is None:
        out_path = f"{imagename}.nvss_mask.fits"

    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    from dsa110_contimg.utils.fits_utils import create_fits_hdu
    header = wcs.to_header()
    hdu = create_fits_hdu(data=mask, header=header, fix_cdelt=True)
    hdu.writeto(out_path, overwrite=True)

    return out_path


def create_nvss_overlay(image_path: str, out_path: str, pb_path: Optional[str] = None,
                        pblimit: float = 0.2, min_mjy: float = 10.0) -> None:
    """Create NVSS overlay PNG for a FITS image."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Load image
    data = fits.getdata(image_path)
    hdr = fits.getheader(image_path)
    while data.ndim > 2:
        data = data[0]

    # Get FoV
    ra_span, dec_span, center = _image_fov_deg(hdr)
    radius_deg = 0.5 * max(ra_span, dec_span) * 1.1  # 10% padding

    # Load NVSS catalog
    from dsa110_contimg.calibration.catalogs import read_nvss_catalog
    df = read_nvss_catalog()
    sc = SkyCoord(df['ra'].values * u.deg,
                  df['dec'].values * u.deg, frame='icrs')
    sep = sc.separation(center).deg
    flux = np.asarray(df['flux_20_cm'].values, float)
    m = (sep <= radius_deg) & (flux >= float(min_mjy))
    sub = df.loc[m].copy()

    # Load PB mask if provided
    pb_mask = _load_pb_mask(pb_path, pblimit) if pb_path else None

    # Plot
    w = WCS(hdr)
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={'projection': w})

    # Image
    m_data = np.isfinite(data)
    if np.any(m_data):
        vals = data[m_data]
        vmin, vmax = np.percentile(vals, [1, 99])
        im = ax.imshow(data, origin='lower', cmap='gray', vmin=vmin, vmax=vmax)
        if pb_mask is not None and pb_mask.shape == data.shape:
            ax.contour(pb_mask, levels=[0.5],
                       colors='cyan', linewidths=1, alpha=0.5)

    # Overlay NVSS sources
    if len(sub) > 0:
        nvss_coords = SkyCoord(
            sub['ra'].values * u.deg, sub['dec'].values * u.deg, frame='icrs')
        nvss_pix = w.world_to_pixel(nvss_coords)

        # Scale circle sizes by log10(flux)
        log_flux = np.log10(np.maximum(sub['flux_20_cm'].values, 1.0))
        sizes = 50 * (log_flux - np.min(log_flux)) / \
            (np.max(log_flux) - np.min(log_flux) + 1e-6) + 20

        ax.scatter(nvss_pix[0], nvss_pix[1], s=sizes, facecolors='none',
                   edgecolors='red', linewidths=1.5, alpha=0.7, label='NVSS')

        # Label brightest sources
        n_label = min(10, len(sub))
        brightest = sub.nlargest(n_label, 'flux_20_cm')
        for _, row in brightest.iterrows():
            coord = SkyCoord(row['ra'] * u.deg, row['dec']
                             * u.deg, frame='icrs')
            pix = w.world_to_pixel(coord)
            ax.text(pix[0], pix[1], f"{row['flux_20_cm']:.1f}",
                    color='yellow', fontsize=8, ha='center', va='bottom')

    ax.set_xlabel('RA')
    ax.set_ylabel('Dec')
    ax.set_title(os.path.basename(image_path))
    ax.legend()

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
