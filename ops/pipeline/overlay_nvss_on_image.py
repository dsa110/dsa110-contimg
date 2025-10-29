#!/usr/bin/env python3
"""
Simplified NVSS overlay utility (replaces legacy astroquery-based version).

Backwards-compatible CLI:
  --fits <image.fits> [--flux-min-mjy <mJy>] [--radius-deg <deg>]

Internally uses dsa110_contimg.calibration.catalogs.read_nvss_catalog() to
select NVSS sources within the image FoV and overlays them via WCS.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from astropy.visualization import ZScaleInterval, ImageNormalize, AsinhStretch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def _fits_image_and_wcs(fits_path: str):
    hdu = fits.open(fits_path)[0]
    wcs = WCS(hdu.header).celestial
    data = np.asarray(hdu.data, dtype=float)
    while data.ndim > 2:
        data = data.squeeze()
        if data.ndim > 2:
            data = data[0]
    data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)
    return data, wcs, hdu.header


def _image_center(header, wcs: WCS) -> SkyCoord:
    crval1 = header.get('CRVAL1')
    crval2 = header.get('CRVAL2')
    if crval1 is not None and crval2 is not None:
        return SkyCoord(crval1 * u.deg, crval2 * u.deg, frame='icrs')
    nx = header.get('NAXIS1', 0)
    ny = header.get('NAXIS2', 0)
    ra, dec = wcs.wcs_pix2world(nx / 2, ny / 2, 0)
    return SkyCoord(ra * u.deg, dec * u.deg, frame='icrs')


def _query_nvss_local(center: SkyCoord, radius_deg: float, flux_min_mjy: float):
    from dsa110_contimg.calibration.catalogs import read_nvss_catalog  # type: ignore
    df = read_nvss_catalog()
    sc = SkyCoord(df['ra'].values * u.deg, df['dec'].values * u.deg, frame='icrs')
    sep = sc.separation(center).deg
    m = (sep <= radius_deg) & (np.asarray(df['flux_20_cm'].values, float) >= flux_min_mjy)
    ra = df.loc[m, 'ra'].astype(float).values
    dec = df.loc[m, 'dec'].astype(float).values
    flux = df.loc[m, 'flux_20_cm'].astype(float).values
    return ra, dec, flux


def main() -> int:
    ap = argparse.ArgumentParser(description='Overlay NVSS sources on a FITS image (no astroquery)')
    ap.add_argument('--fits', required=True, help='Input FITS image (CASA export)')
    ap.add_argument('--flux-min-mjy', type=float, default=200.0, help='NVSS flux threshold (mJy)')
    ap.add_argument('--radius-deg', type=float, default=None, help='Override search radius in degrees')
    args = ap.parse_args()

    data, wcs, hdr = _fits_image_and_wcs(args.fits)
    center = _image_center(hdr, wcs)
    scales = proj_plane_pixel_scales(wcs)
    nx = hdr.get('NAXIS1', data.shape[-1])
    ny = hdr.get('NAXIS2', data.shape[-2])
    fov_ra = float(scales[0] * nx)
    fov_dec = float(scales[1] * ny)
    half_diag = 0.5 * float(np.hypot(fov_ra, fov_dec))
    radius = args.radius_deg or half_diag

    ra, dec, flux = _query_nvss_local(center, radius, float(args.flux_min_mjy))

    try:
        vmin, vmax = ZScaleInterval().get_limits(data)
    except Exception:
        vmin, vmax = np.percentile(data, [1, 99])

    fig = plt.figure(figsize=(8, 8), dpi=150)
    ax = plt.subplot(projection=wcs)
    im = ax.imshow(
        data,
        origin='lower',
        cmap='grayscale',
        norm=ImageNormalize(vmin=vmin, vmax=vmax, stretch=AsinhStretch()),
    )
    cb = plt.colorbar(im, ax=ax, shrink=0.8)
    bunit = (hdr.get('BUNIT') or '').strip()
    cb.set_label(f'Intensity [{bunit}]' if bunit else 'Intensity')
    ax.set_xlabel('RA (J2000)')
    ax.set_ylabel('Dec (J2000)')

    if ra.size:
        x, y = wcs.world_to_pixel_values(ra, dec)
        size = 10 + 2.5 * np.sqrt(np.clip(flux, 0, None) / 100.0)
        ax.scatter(x, y, s=size, facecolors='none', edgecolors='cyan', linewidths=1.2, alpha=0.9,
                   label='NVSS', transform=ax.get_transform('pixel'))
    else:
        print('No NVSS sources returned for overlay (check radius/flux threshold)')

    plt.tight_layout()
    out = Path(args.fits).with_suffix('').as_posix() + '.nvss_overlay.png'
    plt.savefig(out)
    print('Wrote overlay:', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
