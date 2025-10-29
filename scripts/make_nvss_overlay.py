#!/usr/bin/env python3
"""
Create an NVSS overlay PNG for a FITS image (CASA export).

Usage examples:
  # Minimal
  python scripts/make_nvss_overlay.py \
    --image /scratch/dsa110-contimg/out/wproj_validate_1761236590.image.tt0.fits \
    --out   /scratch/dsa110-contimg/out/wproj_validate_1761236590.image.tt0.nvss_overlay.png

  # With PB mask (keep sources where PB>=0.2) and a 20 mJy cutoff
  python scripts/make_nvss_overlay.py \
    --image /path/image.tt0.fits --pb /path/pb.tt0.fits --pblimit 0.2 \
    --min-mjy 20 --out /path/image.tt0.nvss_overlay.png

Notes:
  - First run downloads and caches the NVSS catalog (~large) into .cache/catalogs
  - Overlay draws circles scaled by log10(flux) and labels the brightest sources
"""

from __future__ import annotations

import argparse
import math
import os
from typing import Tuple

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _image_fov_deg(header) -> Tuple[float, float, SkyCoord]:
    w = WCS(header)
    nx = int(header.get('NAXIS1', 0))
    ny = int(header.get('NAXIS2', 0))
    if nx <= 0 or ny <= 0:
        raise ValueError('Invalid image dimensions')
    # pixel corners -> sky
    corners = np.array([[0, 0], [nx-1, 0], [0, ny-1], [nx-1, ny-1]], dtype=float)
    sky = w.pixel_to_world(corners[:,0], corners[:,1])
    ra = sky.ra.wrap_at(180*u.deg).deg
    dec = sky.dec.deg
    ra_span = float(np.max(ra) - np.min(ra))
    dec_span = float(np.max(dec) - np.min(dec))
    # center
    cx, cy = (nx-1)/2.0, (ny-1)/2.0
    ctr = w.pixel_to_world(cx, cy)
    return ra_span, dec_span, ctr


def _load_pb_mask(pb_path: str, pblimit: float) -> np.ndarray | None:
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='Overlay NVSS sources on a FITS image')
    ap.add_argument('--image', required=True, help='Input FITS image (CASA export)')
    ap.add_argument('--pb', help='Primary beam FITS to mask detections (optional)')
    ap.add_argument('--pblimit', type=float, default=0.2, help='PB cutoff when --pb is provided')
    ap.add_argument('--min-mjy', type=float, default=10.0, help='Minimum NVSS flux (mJy) to plot')
    ap.add_argument('--out', required=True, help='Output PNG path')
    args = ap.parse_args(argv)

    # Load image
    data = fits.getdata(args.image)
    hdr = fits.getheader(args.image)
    while data.ndim > 2:
        data = data[0]
    m = np.isfinite(data)
    vals = data[m]
    # Robust stretch
    lo, hi = np.percentile(vals, [1.0, 99.5]) if vals.size else (0.0, 1.0)
    img = np.clip(data, lo, hi)
    img = np.arcsinh((img - lo) / max(1e-12, (hi - lo)))
    img[~m] = np.nan

    # Derive FoV and center
    ra_span, dec_span, ctr = _image_fov_deg(hdr)
    # Padding
    pad_ra = max(0.1, 0.15 * ra_span)
    pad_dec = max(0.1, 0.15 * dec_span)

    # Load NVSS catalog (cached)
    from dsa110_contimg.calibration.catalogs import read_nvss_catalog  # type: ignore
    df = read_nvss_catalog()
    # Filter by sky box
    ra0 = (ctr.ra.deg - pad_ra)
    ra1 = (ctr.ra.deg + pad_ra)
    dec0 = (ctr.dec.deg - pad_dec)
    dec1 = (ctr.dec.deg + pad_dec)
    # Handle RA wrap simply by accepting a slightly larger window when near wrap
    df2 = df[(df['ra'] >= min(ra0, ra1)) & (df['ra'] <= max(ra0, ra1)) &
             (df['dec'] >= min(dec0, dec1)) & (df['dec'] <= max(dec0, dec1))].copy()
    # Flux cut
    if 'flux_20_cm' in df2.columns:
        df2 = df2[pd.to_numeric(df2['flux_20_cm'], errors='coerce') >= (args.min_mjy)].copy()

    # Project to pixels
    w = WCS(hdr)
    sc = SkyCoord(df2['ra'].values * u.deg, df2['dec'].values * u.deg, frame='icrs')
    x, y = w.world_to_pixel(sc)
    # PB mask (optional)
    keep = np.isfinite(x) & np.isfinite(y)
    if args.pb:
        pbmask = _load_pb_mask(args.pb, args.pblimit)
        if pbmask is not None:
            xi = np.clip(np.round(x).astype(int), 0, pbmask.shape[1]-1)
            yi = np.clip(np.round(y).astype(int), 0, pbmask.shape[0]-1)
            keep &= pbmask[yi, xi]

    x = x[keep]; y = y[keep]
    flux_mjy = pd.to_numeric(df2['flux_20_cm'].values[keep], errors='coerce')

    # Plot
    plt.figure(figsize=(7,6), dpi=140)
    plt.imshow(img, origin='lower', cmap='gray', interpolation='nearest')
    # Marker size by log10 flux
    s = 20.0 * (1.0 + np.log10(np.clip(flux_mjy, 1.0, None)))
    plt.scatter(x, y, s=s, edgecolor='yellow', facecolor='none', linewidth=0.9, alpha=0.9)
    # Label top N sources
    try:
        import pandas as pd  # type: ignore
        idx = np.argsort(-flux_mjy)[:10]
        for xi, yi, fm in zip(x[idx], y[idx], flux_mjy[idx]):
            plt.text(xi+5, yi+5, f"{fm:.0f} mJy", color='yellow', fontsize=7, alpha=0.9)
    except Exception:
        pass
    plt.title(os.path.basename(args.image) + f"  (NVSS ≥{args.min_mjy:.0f} mJy)")
    plt.tight_layout()
    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    plt.savefig(args.out, bbox_inches='tight')
    plt.close()
    print('Wrote overlay:', args.out)
    return 0


if __name__ == '__main__':
    import pandas as pd  # noqa: F401 (ensures import present for type ignore above)
    raise SystemExit(main())

