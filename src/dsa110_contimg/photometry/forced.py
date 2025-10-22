"""
Forced photometry utilities on FITS images (PB-corrected mosaics or tiles).

Minimal functionality: measure peak within a small pixel box around a world
coordinate, plus estimate local RMS in an annulus for error bars.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, List

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS


@dataclass
class ForcedPhotometryResult:
    ra_deg: float
    dec_deg: float
    peak_jyb: float
    peak_err_jyb: float
    pix_x: float
    pix_y: float
    box_size_pix: int


def _world_to_pixel(wcs: WCS, ra_deg: float, dec_deg: float) -> Tuple[float, float]:
    xy = wcs.world_to_pixel_values(ra_deg, dec_deg)
    # astropy WCS: returns (x, y) with 0-based pixel coordinates
    return float(xy[0]), float(xy[1])


def measure_forced_peak(
    fits_path: str, ra_deg: float, dec_deg: float, *, box_size_pix: int = 5, annulus_pix: Tuple[int, int] = (12, 20)
) -> ForcedPhotometryResult:
    """Measure peak within a pixel box centered on world coordinate.

    - peak in Jy/beam for PB-corrected images
    - error estimated from sigma-clipped RMS in annulus [r_in, r_out] pixels
    """
    p = Path(fits_path)
    with fits.open(p) as hdul:
        # assume primary HDU contains the image
        data = np.asarray(hdul[0].data).squeeze()
        wcs = WCS(hdul[0].header)
    x0, y0 = _world_to_pixel(wcs, ra_deg, dec_deg)
    # Define integer box centered at nearest pixel
    cx, cy = int(round(x0)), int(round(y0))
    half = max(1, box_size_pix // 2)
    x1, x2 = cx - half, cx + half
    y1, y2 = cy - half, cy + half
    h, w = data.shape[-2], data.shape[-1]
    x1c, x2c = max(0, x1), min(w - 1, x2)
    y1c, y2c = max(0, y1), min(h - 1, y2)
    cut = data[y1c : y2c + 1, x1c : x2c + 1]
    peak = float(np.nanmax(cut)) if cut.size else float("nan")

    # Local RMS in annulus
    rin, rout = annulus_pix
    yy, xx = np.ogrid[0:h, 0:w]
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    ann = (r >= rin) & (r <= rout)
    vals = data[ann]
    # sigma-clip (3-sigma, simple)
    m = np.nanmedian(vals)
    s = 1.4826 * np.nanmedian(np.abs(vals - m))
    mask = (vals > m - 3 * s) & (vals < m + 3 * s)
    rms = float(np.nanstd(vals[mask])) if np.any(mask) else float("nan")

    return ForcedPhotometryResult(
        ra_deg=ra_deg,
        dec_deg=dec_deg,
        peak_jyb=peak,
        peak_err_jyb=rms,
        pix_x=x0,
        pix_y=y0,
        box_size_pix=box_size_pix,
    )


def measure_many(
    fits_path: str, coords: List[Tuple[float, float]], *, box_size_pix: int = 5
) -> List[ForcedPhotometryResult]:
    out: List[ForcedPhotometryResult] = []
    for ra, dec in coords:
        out.append(measure_forced_peak(fits_path, ra, dec, box_size_pix=box_size_pix))
    return out

