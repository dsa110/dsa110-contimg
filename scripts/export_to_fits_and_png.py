#!/usr/bin/env python3
"""
Export CASA image tables to FITS and quicklook PNGs.

Usage:
  python scripts/export_to_fits_and_png.py \
    --source /scratch/dsa110-contimg/out \
    --prefix wproj_validate_1761236590 \
    --make-fits --make-png

Notes:
  - Requires a CASA 6 environment for casatasks.exportfits
  - PNG conversion uses astropy + matplotlib
"""

from __future__ import annotations

import argparse
import os
import sys
from glob import glob
from typing import Iterable, List


def _find_casa_images(source: str, prefix: str) -> List[str]:
    patt = os.path.join(source, prefix + ".*")
    paths = sorted(glob(patt))
    return [p for p in paths if os.path.isdir(p)]


def export_fits(images: Iterable[str]) -> List[str]:
    try:
        from casatasks import exportfits as _exportfits  # type: ignore
    except Exception as e:  # pragma: no cover
        print("casatasks.exportfits not available:", e, file=sys.stderr)
        return []

    exported: List[str] = []
    for p in images:
        fits_out = p + ".fits"
        try:
            _exportfits(imagename=p, fitsimage=fits_out, overwrite=True)
            print("Exported FITS:", fits_out)
            exported.append(fits_out)
        except Exception as e:
            print("exportfits failed for", p, ":", e, file=sys.stderr)
    return exported


def save_png_from_fits(paths: Iterable[str]) -> List[str]:
    saved: List[str] = []
    try:
        from astropy.io import fits  # type: ignore
        import numpy as np  # type: ignore
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # type: ignore
    except Exception as e:  # pragma: no cover
        print("PNG conversion dependencies missing:", e, file=sys.stderr)
        return saved

    for f in paths:
        try:
            with fits.open(f, memmap=False) as hdul:
                data = None
                for hdu in hdul:
                    if getattr(hdu, "data", None) is not None and getattr(hdu.data, "ndim", 0) >= 2:
                        data = hdu.data
                        break
                if data is None:
                    print("Skip (no 2D image in FITS):", f)
                    continue
                arr = np.array(data, dtype=float)
                while arr.ndim > 2:
                    arr = arr[0]
                m = np.isfinite(arr)
                if not np.any(m):
                    print("Skip (all NaN):", f)
                    continue
                vals = arr[m]
                lo, hi = np.percentile(vals, [1.0, 99.5])
                img = np.clip(arr, lo, hi)
                img = np.arcsinh((img - lo) / max(1e-12, (hi - lo)))
                img[~m] = np.nan
                plt.figure(figsize=(6, 5), dpi=140)
                plt.imshow(img, origin="lower", cmap="inferno", interpolation="nearest")
                plt.colorbar(fraction=0.046, pad=0.04)
                plt.title(os.path.basename(f))
                plt.tight_layout()
                out = f + ".png"
                plt.savefig(out, bbox_inches="tight")
                plt.close()
                print("Wrote PNG:", out)
                saved.append(out)
        except Exception as e:
            print("PNG conversion failed for", f, ":", e, file=sys.stderr)
    return saved


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Export CASA images to FITS and PNGs")
    ap.add_argument("--source", required=True, help="Directory containing CASA images")
    ap.add_argument("--prefix", required=True, help="Prefix of image set (e.g., imagename prefix)")
    ap.add_argument("--make-fits", action="store_true", help="Export FITS from CASA images")
    ap.add_argument("--make-png", action="store_true", help="Convert FITS to PNGs")
    args = ap.parse_args(argv)

    casa_images = _find_casa_images(args.source, args.prefix)
    if not casa_images:
        print("No CASA image directories found for prefix", args.prefix, "under", args.source)
        return 1

    fits_paths: List[str] = []
    if args.make_fits:
        fits_paths = export_fits(casa_images)
        if not fits_paths:
            print("No FITS files exported (check casatasks and inputs)")
    if args.make_png:
        # If FITS were not just created, try to discover existing ones
        if not fits_paths:
            patt = os.path.join(args.source, args.prefix + "*.fits")
            fits_paths = sorted(glob(patt))
        if not fits_paths:
            print("No FITS files found to convert for", args.prefix)
        else:
            save_png_from_fits(fits_paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

