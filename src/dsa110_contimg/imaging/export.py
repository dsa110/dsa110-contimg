"""
Export CASA images to FITS and PNG formats.
"""

from __future__ import annotations

import os
from glob import glob
from typing import Iterable, List


def _find_casa_images(source: str, prefix: str) -> List[str]:
    """Find CASA image directories matching prefix."""
    patt = os.path.join(source, prefix + ".*")
    paths = sorted(glob(patt))
    return [p for p in paths if os.path.isdir(p)]


def export_fits(images: Iterable[str]) -> List[str]:
    """Export CASA images to FITS format."""
    try:
        from casatasks import exportfits as _exportfits  # type: ignore
    except Exception as e:
        print("casatasks.exportfits not available:", e, file=__import__("sys").stderr)
        return []

    exported: List[str] = []
    for p in images:
        fits_out = p + ".fits"
        try:
            _exportfits(imagename=p, fitsimage=fits_out, overwrite=True)
            print("Exported FITS:", fits_out)
            exported.append(fits_out)
        except Exception as e:
            print("exportfits failed for", p, ":", e, file=__import__("sys").stderr)
    return exported


def save_png_from_fits(paths: Iterable[str]) -> List[str]:
    """Convert FITS files to PNG quicklook images."""
    saved: List[str] = []
    try:
        import matplotlib
        import numpy as np
        from astropy.io import fits

        from dsa110_contimg.utils.runtime_safeguards import validate_image_shape

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print("PNG conversion dependencies missing:", e, file=__import__("sys").stderr)
        return saved

    for f in paths:
        try:
            with fits.open(f, memmap=False) as hdul:
                data = None
                for hdu in hdul:
                    if (
                        getattr(hdu, "data", None) is not None
                        and getattr(hdu.data, "ndim", 0) >= 2
                    ):
                        # Validate image shape before processing
                        try:
                            validate_image_shape(hdu.data, min_size=1)
                        except ValueError as e:
                            import logging

                            logging.warning(f"Skipping invalid image in {f}: {e}")
                            continue
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
            print("PNG conversion failed for", f, ":", e, file=__import__("sys").stderr)
    return saved
