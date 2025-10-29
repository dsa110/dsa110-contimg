#!/usr/bin/env python3
"""
CLI for forced photometry on FITS images.

Examples:
  # Single coordinate
  python -m dsa110_contimg.photometry.cli peak \
    --fits /path/to/image.pbcor.fits \
    --ra 128.725 --dec 55.573 \
    --box 5 --annulus 12 20

  # Multiple coordinates
  python -m dsa110_contimg.photometry.cli peak-many \
    --fits /path/to/image.pbcor.fits \
    --coords "128.725,55.573; 129.002,55.610"
"""
from __future__ import annotations

import argparse
import json
import os
import time
from typing import List, Tuple
from pathlib import Path

from astropy.io import fits  # type: ignore[reportMissingTypeStubs]
from astropy.wcs import WCS  # type: ignore[reportMissingTypeStubs]
import astropy.coordinates as acoords  # type: ignore[reportMissingTypeStubs]
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

from dsa110_contimg.calibration.catalogs import read_nvss_catalog
from dsa110_contimg.database.products import (
    ensure_products_db,
    photometry_insert,
)
from .forced import measure_forced_peak, measure_many


def _parse_coords_arg(coords_arg: str) -> List[Tuple[float, float]]:
    parts = [c.strip() for c in coords_arg.split(';') if c.strip()]
    coords: List[Tuple[float, float]] = []
    for p in parts:
        ra_s, dec_s = [s.strip() for s in p.split(',')]
        coords.append((float(ra_s), float(dec_s)))
    return coords


def cmd_peak(args: argparse.Namespace) -> int:
    res = measure_forced_peak(
        args.fits,
        args.ra,
        args.dec,
        box_size_pix=args.box,
        annulus_pix=(args.annulus[0], args.annulus[1]),
    )
    print(json.dumps(res.__dict__, indent=2))
    return 0


def cmd_peak_many(args: argparse.Namespace) -> int:
    coords = _parse_coords_arg(args.coords)
    results = measure_many(args.fits, coords, box_size_pix=args.box)
    print(json.dumps([r.__dict__ for r in results], indent=2))
    return 0


def _image_center_and_radius_deg(fits_path: str) -> Tuple[float, float, float]:
    hdr = fits.getheader(fits_path)
    w = WCS(hdr).celestial
    nx = hdr.get('NAXIS1', 0)
    ny = hdr.get('NAXIS2', 0)
    cx = (nx - 1) / 2.0
    cy = (ny - 1) / 2.0
    c = w.pixel_to_world(cx, cy)
    # Corners
    corners = [
        w.pixel_to_world(0.0, 0.0),
        w.pixel_to_world(nx - 1.0, 0.0),
        w.pixel_to_world(0.0, ny - 1.0),
        w.pixel_to_world(nx - 1.0, ny - 1.0),
    ]
    center = acoords.SkyCoord(c.ra.deg, c.dec.deg, unit='deg', frame='icrs')
    rad = 0.0
    for s in corners:
        sep = center.separation(s).deg
        if sep > rad:
            rad = sep
    # Add small margin
    rad = float(rad * 1.02)
    return float(center.ra.deg), float(center.dec.deg), rad


def cmd_nvss(args: argparse.Namespace) -> int:
    ra0, dec0, auto_rad = _image_center_and_radius_deg(args.fits)
    radius_deg = (
        float(args.radius_deg)
        if args.radius_deg is not None
        else auto_rad
    )
    df = read_nvss_catalog()
    sc = acoords.SkyCoord(
        df['ra'].to_numpy(),
        df['dec'].to_numpy(),
        unit='deg',
        frame='icrs',
    )
    center = acoords.SkyCoord(ra0, dec0, unit='deg', frame='icrs')
    sep_deg = sc.separation(center).deg
    flux_mjy = df['flux_20_cm'].to_numpy()
    keep = (
        (sep_deg <= radius_deg)
        & (flux_mjy >= float(args.min_mjy))
    )
    ra_sel = df['ra'].to_numpy()[keep]
    dec_sel = df['dec'].to_numpy()[keep]
    flux_sel = flux_mjy[keep]

    results = []
    now = time.time()
    pdb_path = os.getenv('PIPELINE_PRODUCTS_DB', args.products_db)
    conn = ensure_products_db(Path(pdb_path))
    try:
        inserted = 0
        skipped = 0
        for ra, dec, nvss in zip(ra_sel, dec_sel, flux_sel):
            m = measure_forced_peak(
                args.fits,
                float(ra),
                float(dec),
                box_size_pix=args.box,
                annulus_pix=(args.annulus[0], args.annulus[1]),
            )
            if not np.isfinite(m.peak_jyb):
                skipped += 1
                continue
            perr = None if (m.peak_err_jyb is None or not np.isfinite(m.peak_err_jyb)) else float(m.peak_err_jyb)
            photometry_insert(
                conn,
                image_path=args.fits,
                ra_deg=m.ra_deg,
                dec_deg=m.dec_deg,
                nvss_flux_mjy=float(nvss),
                peak_jyb=m.peak_jyb,
                peak_err_jyb=perr,
                measured_at=now,
            )
            results.append(m.__dict__)
            inserted += 1
        conn.commit()
    finally:
        conn.close()
    print(
        json.dumps(
            {
                'image': args.fits,
                'center_ra_deg': ra0,
                'center_dec_deg': dec0,
                'radius_deg': radius_deg,
                'min_mjy': float(args.min_mjy),
                'count': len(results),
                'inserted': inserted,
                'skipped': skipped,
                'results': results,
            },
            indent=2,
        )
    )
    return 0


def cmd_plot(args: argparse.Namespace) -> int:
    # Load image
    hdr = fits.getheader(args.fits)
    data = np.asarray(fits.getdata(args.fits)).squeeze()
    w = WCS(hdr).celestial

    # Build mask for valid pixels
    m = np.isfinite(data)
    vals = data[m]
    lo, hi = (np.nanpercentile(vals, 2.0), np.nanpercentile(vals, 98.0)) if vals.size else (0.0, 1.0)
    img = np.clip(data, lo, hi)

    # Compute FoV outline directly in pixel space to avoid spherical → WCS distortions
    nx = hdr.get('NAXIS1', 0)
    ny = hdr.get('NAXIS2', 0)
    cx = (nx - 1) / 2.0
    cy = (ny - 1) / 2.0
    # Use largest inscribed circle in the image bounds as an outline; shrink slightly
    r_pix = 0.98 * float(min(cx, cy, (nx - 1) - cx, (ny - 1) - cy))
    th = np.linspace(0, 2 * np.pi, 360)
    xcirc = cx + r_pix * np.cos(th)
    ycirc = cy + r_pix * np.sin(th)

    # Load photometry rows for this image
    pdb_path = os.getenv('PIPELINE_PRODUCTS_DB', args.products_db)
    conn = ensure_products_db(Path(pdb_path))
    rows = conn.execute(
        'SELECT ra_deg, dec_deg, peak_jyb, nvss_flux_mjy FROM photometry WHERE image_path = ?',
        (args.fits,)
    ).fetchall()
    conn.close()
    if not rows:
        print('No photometry rows for image; run nvss first')
        return 1
    ra = np.array([r[0] for r in rows], dtype=float)
    dec = np.array([r[1] for r in rows], dtype=float)
    peak = np.array([r[2] for r in rows], dtype=float)
    nvss_jy = np.array([np.nan if r[3] is None else (float(r[3]) / 1e3) for r in rows], dtype=float)
    coords = acoords.SkyCoord(ra, dec, unit='deg', frame='icrs')
    x, y = w.world_to_pixel(coords)

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(12, 6), subplot_kw={'projection': w})
    # Left: forced photometry peak
    ax = axes[0]
    ax.imshow(img, origin='lower', cmap='gray')
    ax.plot(xcirc, ycirc, color='black', linewidth=1.0, alpha=0.8, transform=ax.get_transform('pixel'))
    norm_p = Normalize(vmin=args.vmin if args.vmin is not None else np.nanmin(peak),
                       vmax=args.vmax if args.vmax is not None else np.nanmax(peak))
    sc0 = ax.scatter(x, y, c=peak, s=24, cmap=args.cmap, norm=norm_p, edgecolor='white', linewidths=0.3)
    cb0 = fig.colorbar(sc0, ax=ax, orientation='vertical', fraction=0.046, pad=0.04)
    cb0.set_label('Peak [Jy/beam]')
    ax.set_title('Forced Photometry Peak')
    ax.set_xlabel('RA'); ax.set_ylabel('Dec')

    # Right: NVSS catalog flux (Jy)
    ax = axes[1]
    ax.imshow(img, origin='lower', cmap='gray')
    ax.plot(xcirc, ycirc, color='black', linewidth=1.0, alpha=0.8, transform=ax.get_transform('pixel'))
    norm_n = Normalize(vmin=np.nanmin(nvss_jy), vmax=np.nanmax(nvss_jy))
    sc1 = ax.scatter(x, y, c=nvss_jy, s=24, cmap=args.cmap, norm=norm_n, edgecolor='white', linewidths=0.3)
    cb1 = fig.colorbar(sc1, ax=ax, orientation='vertical', fraction=0.046, pad=0.04)
    cb1.set_label('NVSS Flux [Jy]')
    ax.set_title('NVSS Catalog Flux')
    ax.set_xlabel('RA'); ax.set_ylabel('Dec')
    out = args.out or (os.path.splitext(args.fits)[0] + '_photometry_compare.png')
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches='tight')
    print(out)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Forced photometry utilities")
    sub = p.add_subparsers(dest='cmd')

    sp = sub.add_parser('peak', help='Measure peak at a single RA,Dec')
    sp.add_argument(
        '--fits', required=True,
        help='Input FITS image (PB-corrected)'
    )
    sp.add_argument('--ra', type=float, required=True, help='Right Ascension (deg)')
    sp.add_argument('--dec', type=float, required=True, help='Declination (deg)')
    sp.add_argument('--box', type=int, default=5, help='Box size in pixels')
    sp.add_argument(
        '--annulus', type=int, nargs=2, default=(12, 20),
        help='Annulus radii in pixels [rin rout]'
    )
    sp.set_defaults(func=cmd_peak)

    sp = sub.add_parser(
        'peak-many', help='Measure peaks for a list of RA,Dec pairs'
    )
    sp.add_argument(
        '--fits', required=True,
        help='Input FITS image (PB-corrected)'
    )
    sp.add_argument(
        '--coords', required=True,
        help='Semicolon-separated RA,Dec pairs: "ra1,dec1; ra2,dec2"'
    )
    sp.add_argument('--box', type=int, default=5, help='Box size in pixels')
    sp.set_defaults(func=cmd_peak_many)

    sp = sub.add_parser(
        'nvss', help='Forced photometry for NVSS sources within the image FoV'
    )
    sp.add_argument(
        '--fits', required=True,
        help='Input FITS image (PB-corrected)'
    )
    sp.add_argument('--products-db', default='state/products.sqlite3')
    sp.add_argument('--min-mjy', type=float, default=10.0)
    sp.add_argument(
        '--radius-deg', type=float, default=None,
        help='Override FoV radius (deg)'
    )
    sp.add_argument('--box', type=int, default=5, help='Box size in pixels')
    sp.add_argument(
        '--annulus', type=int, nargs=2, default=(12, 20),
        help='Annulus radii in pixels [rin rout]'
    )
    sp.set_defaults(func=cmd_nvss)

    sp = sub.add_parser(
        'plot', help='Visualize photometry results overlaid on FITS image'
    )
    sp.add_argument('--fits', required=True, help='Input FITS image (PB-corrected)')
    sp.add_argument('--products-db', default='state/products.sqlite3')
    sp.add_argument('--out', default=None, help='Output PNG path')
    sp.add_argument('--cmap', default='viridis')
    sp.add_argument('--vmin', type=float, default=None)
    sp.add_argument('--vmax', type=float, default=None)
    sp.set_defaults(func=cmd_plot)

    return p


def main(argv: list[str] | None = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    if not hasattr(args, 'func'):
        p.print_help()
        return 2
    return args.func(args)


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())


