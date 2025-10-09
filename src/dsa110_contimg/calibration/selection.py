from __future__ import annotations

import numpy as np
from typing import Tuple, List

from casacore.tables import table
import astropy.units as u
from astropy.coordinates import Angle

from .catalogs import airy_primary_beam_response, read_vla_calibrator_catalog


def _read_field_dirs(ms_path: str) -> Tuple[np.ndarray, np.ndarray]:
    """Read FIELD::PHASE_DIR and return arrays of RA/Dec in radians per field.

    Handles column shapes (n,1,2), (n,2), or (2,) per row.
    """
    with table(f"{ms_path}::FIELD") as tf:
        pd = tf.getcol("PHASE_DIR")
        n = tf.nrows()
        ra = np.zeros(n, dtype=float)
        dec = np.zeros(n, dtype=float)
        for i in range(n):
            arr = np.asarray(pd[i])
            if arr.ndim == 3 and arr.shape[-1] == 2:  # (1,1,2)
                ra[i] = float(arr[0, 0, 0])
                dec[i] = float(arr[0, 0, 1])
            elif arr.ndim == 2 and arr.shape[-1] == 2:  # (1,2)
                ra[i] = float(arr[0, 0])
                dec[i] = float(arr[0, 1])
            elif arr.ndim == 1 and arr.shape[0] == 2:  # (2,)
                ra[i] = float(arr[0])
                dec[i] = float(arr[1])
            else:
                # Fallback
                ra[i] = float(arr.ravel()[-2])
                dec[i] = float(arr.ravel()[-1])
    return ra, dec


def select_bandpass_fields(
    ms_path: str,
    cal_ra_deg: float,
    cal_dec_deg: float,
    cal_flux_jy: float,
    *,
    window: int = 3,
    freq_GHz: float = 1.4,
) -> Tuple[str, List[int], np.ndarray]:
    """Pick optimal FIELD indices for bandpass solving based on PB-weighted flux.

    Returns a CASA field selection string (numeric indices, e.g., "10~12"),
    the list of selected indices, and the array of weighted flux per field.
    """
    ra_f, dec_f = _read_field_dirs(ms_path)
    n = ra_f.size
    if n == 0:
        return "", [], np.array([])

    src_ra = float(Angle(cal_ra_deg, unit=u.deg).rad)
    src_dec = float(Angle(cal_dec_deg, unit=u.deg).rad)

    # Primary-beam weighted flux per field
    wflux = np.zeros(n, dtype=float)
    for i in range(n):
        resp = airy_primary_beam_response(ra_f[i], dec_f[i], src_ra, src_dec, freq_GHz)
        wflux[i] = resp * float(cal_flux_jy)

    # Pick best center and window
    idx = int(np.nanargmax(wflux))
    half = max(1, int(window)) // 2
    start = max(0, idx - half)
    end = min(n - 1, idx + half)

    sel_str = f"{start}~{end}" if start != end else f"{start}"
    indices = list(range(start, end + 1))
    return sel_str, indices, wflux


def select_bandpass_from_catalog(
    ms_path: str,
    catalog_path: str,
    *,
    search_radius_deg: float = 1.0,
    freq_GHz: float = 1.4,
    window: int = 3,
) -> Tuple[str, List[int], np.ndarray, Tuple[str, float, float, float]]:
    """Select bandpass fields by scanning a VLA calibrator catalog.

    Returns (field_sel_str, indices, weighted_flux_per_field, calibrator_info)
    where calibrator_info = (name, ra_deg, dec_deg, flux_jy).
    """
    df = read_vla_calibrator_catalog(catalog_path)
    if df.empty:
        raise RuntimeError(f"Catalog {catalog_path} contains no entries")

    ra_field, dec_field = _read_field_dirs(ms_path)
    if ra_field.size == 0:
        raise RuntimeError("MS has no FIELD rows")

    field_coords = Angle(ra_field, unit=u.rad), Angle(dec_field, unit=u.rad)
    field_ra = field_coords[0].rad
    field_dec = field_coords[1].rad

    best = None
    best_wflux = None

    for name, row in df.iterrows():
        try:
            ra_deg = float(row.get('ra', row.get('RA', np.nan)))
            dec_deg = float(row.get('dec', row.get('DEC', np.nan)))
            flux_mJy = float(row.get('flux_20_cm', row.get('flux', np.nan)))
        except Exception:
            continue
        if not np.isfinite(ra_deg) or not np.isfinite(dec_deg) or not np.isfinite(flux_mJy):
            continue
        flux_jy = flux_mJy / 1000.0
        src_ra = Angle(ra_deg, unit=u.deg).rad
        src_dec = Angle(dec_deg, unit=u.deg).rad

        # Compute angular separation to each field and filter by search radius
        sep = np.rad2deg(np.arccos(np.clip(
            np.sin(field_dec) * np.sin(src_dec) +
            np.cos(field_dec) * np.cos(src_dec) * np.cos(field_ra - src_ra),
            -1.0, 1.0)))
        if np.nanmin(sep) > float(search_radius_deg):
            continue

        resp = np.array([
            airy_primary_beam_response(ra, dec, src_ra, src_dec, freq_GHz)
            for ra, dec in zip(field_ra, field_dec)
        ])
        wflux = resp * flux_jy
        peak_idx = int(np.nanargmax(wflux))
        peak_val = float(wflux[peak_idx])

        if best is None or peak_val > best[0]:
            best = (peak_val, peak_idx, name, ra_deg, dec_deg, flux_jy)
            best_wflux = wflux

    if best is None:
        raise RuntimeError("No calibrator candidates found within search radius")

    _, peak_idx, name, ra_deg, dec_deg, flux_jy = best
    wflux = best_wflux
    half = max(1, int(window)) // 2
    start = max(0, peak_idx - half)
    end = min(len(wflux) - 1, peak_idx + half)
    sel_str = f"{start}~{end}" if start != end else f"{start}"
    indices = list(range(start, end + 1))
    cal_info = (name, ra_deg, dec_deg, flux_jy)
    return sel_str, indices, wflux, cal_info
