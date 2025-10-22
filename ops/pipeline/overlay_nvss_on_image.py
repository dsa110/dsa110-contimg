#!/usr/bin/env python3
"""
Overlay NVSS sources on a FITS image using WCS, optionally marking a known calibrator.

Usage example:
  python ops/pipeline/overlay_nvss_on_image.py \
    --fits /scratch/transit-ms/0834_555_central/2025-10-10T15:09:49.img.image.fits \
    --flux-min-mjy 200 --label-top 5 --cal-ra 128.728767 --cal-dec 55.572520

If astroquery is not available, falls back to downloading/parsing the NVSS catalog
via dsa110_contimg.calibration.catalogs.read_nvss_catalog() and filters locally.
"""

from __future__ import annotations
from matplotlib.patches import Circle
import matplotlib.pyplot as plt

import argparse
import os
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.visualization import ZScaleInterval, ImageNormalize, AsinhStretch

import matplotlib
matplotlib.use('Agg')

try:
    from astroquery.vizier import Vizier
    Vizier.ROW_LIMIT = -1
    Vizier.TIMEOUT = 120
    HAVE_ASTROQUERY = True
except Exception:
    HAVE_ASTROQUERY = False


def _fits_image_and_wcs(fits_path: str) -> Tuple[np.ndarray, WCS, fits.Header]:
    hdu = fits.open(fits_path)[0]
    wcs = WCS(hdu.header).celestial
    data = np.asarray(hdu.data, dtype=float)
    while data.ndim > 2:
        data = data.squeeze()
        if data.ndim > 2:
            data = data[0]
    data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)
    return data, wcs, hdu.header


def _image_center(header: fits.Header, wcs: WCS) -> SkyCoord:
    # Center in world coords
    crval1 = header.get('CRVAL1')
    crval2 = header.get('CRVAL2')
    if crval1 is not None and crval2 is not None:
        return SkyCoord(crval1 * u.deg, crval2 * u.deg, frame='icrs')
    # Fallback: center pixel
    nx = header.get('NAXIS1', 0)
    ny = header.get('NAXIS2', 0)
    ra, dec = wcs.wcs_pix2world(nx / 2, ny / 2, 0)
    return SkyCoord(ra * u.deg, dec * u.deg, frame='icrs')


def query_nvss(center: SkyCoord, radius_deg: float, flux_min_mjy: float):
    # Returns arrays of RA[deg], Dec[deg], Flux[mJy], Name
    if HAVE_ASTROQUERY:
        v = Vizier(
            columns=[
                'NVSS',
                'RAJ2000',
                'DEJ2000',
                'S1.4',
                'MajAxis',
                'MinAxis',
                'PA',
                'Field'],
            column_filters={
                'S1.4': f'>{flux_min_mjy}'})
        res = v.query_region(
            center,
            radius=radius_deg * u.deg,
            catalog='VIII/65/nvss')
        if not res or len(res) == 0:
            return np.array([]), np.array([]), np.array([]), []
        tab = res[0]
        # Handle RA/Dec which may be sexagesimal strings in some mirrors
        ra_col = tab['RAJ2000']
        dec_col = tab['DEJ2000']
        if not np.issubdtype(
                ra_col.dtype,
                np.number) or not np.issubdtype(
                dec_col.dtype,
                np.number):
            sc = SkyCoord(
                ra_col.astype(str),
                dec_col.astype(str),
                unit=(
                    u.hourangle,
                    u.deg),
                frame='icrs')
            ra = sc.ra.deg
            dec = sc.dec.deg
        else:
            ra = np.asarray(ra_col, dtype=float)
            dec = np.asarray(dec_col, dtype=float)
        # Flux is in mJy
        try:
            flux = tab['S1.4'].filled(np.nan).astype(float)
        except Exception:
            flux = np.asarray(tab['S1.4'], dtype=float)
        name = [f'NVSS_{n}' for n in tab['NVSS'].astype(str).tolist()]
        return ra, dec, flux, name
    else:
        # Fallback to local NVSS table reader
        try:
            from dsa110_contimg.calibration.catalogs import read_nvss_catalog
            df = read_nvss_catalog()
            # df has columns ra (deg), dec (deg), flux_20_cm (mJy)
            sc = SkyCoord(
                df['ra'].values * u.deg,
                df['dec'].values * u.deg,
                frame='icrs')
            sep = sc.separation(center).deg
            m = (
                sep <= radius_deg) & (
                np.asarray(
                    df['flux_20_cm'].values,
                    float) >= flux_min_mjy)
            ra = df.loc[m, 'ra'].astype(float).values
            dec = df.loc[m, 'dec'].astype(float).values
            flux = df.loc[m, 'flux_20_cm'].astype(float).values
            name = [f'NVSS_{i}' for i in np.nonzero(m)[0].tolist()]
            return ra, dec, flux, name
        except Exception:
            return np.array([]), np.array([]), np.array([]), []


def main() -> int:
    ap = argparse.ArgumentParser(
        description='Overlay NVSS sources on a FITS image')
    ap.add_argument(
        '--fits',
        required=True,
        help='Input FITS image (CASA-exported)')
    ap.add_argument('--flux-min-mjy', type=float, default=200.0)
    ap.add_argument(
        '--radius-deg',
        type=float,
        default=None,
        help='Search radius in degrees (default: half-diagonal of image FOV)')
    ap.add_argument(
        '--cal-ra',
        type=float,
        help='Optional calibrator RA (deg) to mark')
    ap.add_argument(
        '--cal-dec',
        type=float,
        help='Optional calibrator Dec (deg) to mark')
    ap.add_argument(
        '--label-top',
        type=int,
        default=0,
        help='Label the N brightest NVSS sources (0 for none)')
    args = ap.parse_args()

    data, wcs, hdr = _fits_image_and_wcs(args.fits)
    center = _image_center(hdr, wcs)
    # Determine image FOV
    scales = proj_plane_pixel_scales(wcs)  # deg/pixel along axes
    nx = hdr.get('NAXIS1', data.shape[-1])
    ny = hdr.get('NAXIS2', data.shape[-2])
    fov_ra = float(scales[0] * nx)
    fov_dec = float(scales[1] * ny)
    half_diag = 0.5 * float(np.hypot(fov_ra, fov_dec))
    radius = args.radius_deg or half_diag

    ra, dec, flux, name = query_nvss(center, radius, args.flux_min_mjy)

    # Plot image
    try:
        vmin, vmax = ZScaleInterval().get_limits(data)
    except Exception:
        vmin, vmax = np.percentile(data, [1, 99])

    fig = plt.figure(figsize=(8, 8), dpi=150)
    ax = plt.subplot(projection=wcs)
    im = ax.imshow(
        data,
        origin='lower',
        cmap='inferno',
        norm=ImageNormalize(
            vmin=vmin,
            vmax=vmax,
            stretch=AsinhStretch()))
    cb = plt.colorbar(im, ax=ax, shrink=0.8)
    bunit = (hdr.get('BUNIT') or '').strip()
    cb.set_label(f'Intensity [{bunit}]' if bunit else 'Intensity')
    ax.set_xlabel('RA (J2000)')
    ax.set_ylabel('Dec (J2000)')

    # Overlay NVSS sources
    if ra.size:
        x, y = wcs.world_to_pixel_values(ra, dec)
        # marker size scaled by sqrt(flux)
        size = 10 + 2.5 * np.sqrt(np.clip(flux, 0, None) / 100.0)
        ax.scatter(
            x,
            y,
            s=size,
            facecolors='none',
            edgecolors='cyan',
            linewidths=1.2,
            alpha=0.9,
            label='NVSS',
            transform=ax.get_transform('pixel'))
        if args.label_top and args.label_top > 0:
            idx = np.argsort(flux)[::-1][:args.label_top]
            for i in idx:
                ax.text(
                    x[i] + 3,
                    y[i] + 3,
                    f'{flux[i]/1000.0:.2f} Jy',
                    color='cyan',
                    fontsize=8,
                    ha='left',
                    va='bottom',
                    bbox=dict(
                        facecolor='black',
                        alpha=0.35,
                        linewidth=0,
                        pad=1),
                    transform=ax.get_transform('pixel'))
    else:
        print('No NVSS sources returned for overlay (check radius/flux threshold)')

    # Optional calibrator marker
    if args.cal_ra is not None and args.cal_dec is not None:
        px, py = wcs.world_to_pixel_values(args.cal_ra, args.cal_dec)
        # crosshair and circle ~1 arcmin
        deg_per_pix = float(
            np.mean(scales)) if np.all(
            np.isfinite(scales)) else 1.0 / 3600.0
        r_pix = (1.0 / 60.0) / deg_per_pix
        ax.add_patch(
            Circle(
                (px,
                 py),
                radius=r_pix * 1.2,
                edgecolor='black',
                facecolor='none',
                linewidth=3.0,
                alpha=0.9,
                transform=ax.get_transform('pixel')))
        ax.add_patch(
            Circle(
                (px,
                 py),
                radius=r_pix,
                edgecolor='lime',
                facecolor='none',
                linewidth=2.0,
                alpha=1.0,
                transform=ax.get_transform('pixel')))
        ax.plot([px - 2 * r_pix, px + 2 * r_pix], [py, py],
                color='lime', lw=1.5, transform=ax.get_transform('pixel'))
        ax.plot([px, px], [py - 2 * r_pix, py + 2 * r_pix],
                color='lime', lw=1.5, transform=ax.get_transform('pixel'))
        ax.text(
            px + 3 * r_pix,
            py + 3 * r_pix,
            'Calibrator',
            color='lime',
            fontsize=10,
            ha='left',
            va='bottom',
            bbox=dict(
                facecolor='black',
                alpha=0.35,
                linewidth=0,
                pad=2),
            transform=ax.get_transform('pixel'))

    plt.tight_layout()
    out = Path(args.fits).with_suffix('').as_posix() + '.nvss_overlay.png'
    plt.savefig(out)
    print('Wrote overlay:', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
