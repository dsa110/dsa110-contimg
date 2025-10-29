#!/usr/bin/env python3
"""
Build a CRTF user mask with circular regions centered on NVSS sources.

Example:
  python scripts/make_nvss_mask_crtf.py \
    --image /path/to/image.fits \
    --min-mjy 1.0 \
    --radius-arcsec 6.0 \
    --out /path/to/image.nvss_1mJy_6as_mask.crtf

Notes:
  - Uses local NVSS cache via dsa110_contimg.calibration.catalogs.read_nvss_catalog
  - Regions are written in world coordinates (CRTF) using sexagesimal RA/Dec
"""

from __future__ import annotations

import argparse
import os
from typing import Tuple

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
import astropy.units as u


def image_center_and_radius_deg(hdr) -> Tuple[SkyCoord, float]:
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='Create CRTF mask around NVSS sources')
    ap.add_argument('--image', required=True, help='CASA-exported FITS image path')
    ap.add_argument('--min-mjy', type=float, default=1.0, help='Minimum NVSS flux (mJy)')
    ap.add_argument('--radius-arcsec', type=float, default=6.0, help='Mask circle radius (arcsec)')
    ap.add_argument('--out', help='Output CRTF path (defaults to <image>.nvss_mask.crtf)')
    args = ap.parse_args(argv)

    hdr = fits.getheader(args.image)
    center, radius_deg = image_center_and_radius_deg(hdr)

    # Load NVSS catalog and select sources in FoV above threshold
    from dsa110_contimg.calibration.catalogs import read_nvss_catalog  # type: ignore
    df = read_nvss_catalog()
    sc = SkyCoord(df['ra'].values * u.deg, df['dec'].values * u.deg, frame='icrs')
    sep = sc.separation(center).deg
    m = (sep <= radius_deg) & (np.asarray(df['flux_20_cm'].values, float) >= float(args.min_mjy))
    sub = df.loc[m, ['ra', 'dec']].astype(float).to_numpy()

    out_path = args.out or os.path.splitext(args.image)[0] + f".nvss_{args.min_mjy:g}mJy_{args.radius_arcsec:g}as_mask.crtf"
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'w') as f:
        f.write('#CRTFv0\n')
        for ra_deg, dec_deg in sub:
            src = SkyCoord(ra_deg * u.deg, dec_deg * u.deg, frame='icrs')
            ra_str = src.ra.to_string(unit=u.hourangle, sep=':', precision=2, pad=True)
            dec_str = src.dec.to_string(unit=u.deg, sep=':', precision=2, pad=True, alwayssign=True)
            f.write(f"circle[[{ra_str}, {dec_str}], {float(args.radius_arcsec):.3f}arcsec]\n")
    print(f"Wrote mask with {len(sub)} regions: {out_path}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

