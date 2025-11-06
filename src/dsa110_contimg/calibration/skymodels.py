"""
Skymodel helpers: create CASA component lists (.cl) and apply via ft().

Usage:
  from dsa110_contimg.calibration.skymodels import make_point_cl, ft_from_cl
  cl = make_point_cl('0834+555', ra_deg, dec_deg, flux_jy=2.3, freq_ghz=1.4,
                     out_path='/scratch/0834+555_pt.cl')
  ft_from_cl('/path/to/obs.ms', cl, field='0', usescratch=True)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Iterable, Tuple


def make_point_cl(
    name: str,
    ra_deg: float,
    dec_deg: float,
    *,
    flux_jy: float,
    freq_ghz: float | str = 1.4,
    out_path: str,
) -> str:
    """Create a CASA component list (.cl) for a single point source.

    Returns the path to the created component list.
    """
    # Lazy import CASA tools to avoid module import during docs/tests
    from casatools import componentlist as casa_cl  # type: ignore

    out = Path(out_path)
    # Remove pre-existing path
    try:
        import shutil as _sh
        _sh.rmtree(out, ignore_errors=True)
    except Exception:
        pass

    # Normalize frequency
    if isinstance(freq_ghz, (int, float)):
        freq_str = f"{float(freq_ghz)}GHz"
    else:
        freq_str = str(freq_ghz)

    cl = casa_cl()
    try:
        cl.addcomponent(
            dir=f"J2000 {ra_deg}deg {dec_deg}deg",
            flux=float(flux_jy),
            fluxunit="Jy",
            freq=freq_str,
            shape="point",
        )
        cl.rename(os.fspath(out))
    finally:
        try:
            cl.close()
            cl.done()
        except Exception:
            pass
    return os.fspath(out)


def ft_from_cl(
    ms_target: str,
    cl_path: str,
    *,
    field: str = "0",
    usescratch: bool = True,
) -> None:
    """Apply a component-list skymodel to MODEL_DATA via CASA ft().
    
    **CRITICAL**: This function is essential for multi-component models (e.g., NVSS
    catalogs with multiple sources). For single point sources, prefer
    :func:`write_point_model_with_ft` with ``use_manual=True``.
    
    **Known Issues:**
    
    1. **Phase Center Bugs**: Uses ft() which does not use PHASE_DIR correctly after
       rephasing. If the MS has been rephased, MODEL_DATA may have incorrect phase
       structure, causing phase scatter in calibration. See docs/reports/FT_PHASE_CENTER_FIX.md.
    
    2. **WSClean Compatibility**: This function should be called BEFORE running WSClean
       or other imaging tools that modify MODEL_DATA. CASA's ft() has a known bug where
       it crashes with "double free or corruption" when MODEL_DATA already contains
       data written by WSClean or other external tools.
    
    **Workflow:**
    1. Seed MODEL_DATA with CASA ft() (this function) - BEFORE WSClean
    2. Run WSClean for imaging (reads seeded MODEL_DATA)
    
    **For Single Point Sources:**
    Use :func:`write_point_model_with_ft` with ``use_manual=True`` instead, which
    bypasses ft() phase center bugs.
    """
    from casatasks import ft as casa_ft  # type: ignore
    from casacore.tables import table  # type: ignore
    import numpy as np
    
    # Ensure MODEL_DATA column exists before calling ft()
    # This is required for ft() to work properly
    try:
        from casacore.tables import addImagingColumns  # type: ignore
        addImagingColumns(ms_target)
    except Exception:
        pass  # Non-fatal if columns already exist

    # Clear existing MODEL_DATA to avoid CASA ft() crashes
    # CASA's ft() has a bug where it crashes with "double free or corruption"
    # when MODEL_DATA already contains data (e.g., from WSClean)
    try:
        t = table(ms_target, readonly=False)
        if "MODEL_DATA" in t.colnames() and t.nrows() > 0:
            # Get DATA shape to match MODEL_DATA shape
            if "DATA" in t.colnames():
                data_sample = t.getcell("DATA", 0)
                data_shape = getattr(data_sample, "shape", None)
                data_dtype = getattr(data_sample, "dtype", None)
                if data_shape and data_dtype:
                    # Clear MODEL_DATA with zeros matching DATA shape (use putcol for speed)
                    zeros = np.zeros((t.nrows(),) + data_shape, dtype=data_dtype)
                    t.putcol("MODEL_DATA", zeros)
        t.close()
    except Exception as e:
        # If clearing fails, the MS may be corrupted by WSClean
        # We'll still try ft() but it will likely crash
        import warnings
        warnings.warn(
            f"Failed to clear MODEL_DATA before ft(): {e}. "
            "This MS may have been corrupted by WSClean. "
            "Consider using a fresh MS or ensure ft() runs before WSClean.",
            RuntimeWarning
        )

    casa_ft(
        vis=os.fspath(ms_target),
        complist=os.fspath(cl_path),
        field=field,
        usescratch=usescratch,
    )


def make_multi_point_cl(
    points: Iterable[Tuple[float, float, float]],
    *,
    freq_ghz: float | str = 1.4,
    out_path: str,
) -> str:
    """Create a CASA component list with multiple point sources.

    points: iterable of (ra_deg, dec_deg, flux_jy)
    freq_ghz: reference frequency for the components
    out_path: destination path for the .cl table (directory)
    """
    from casatools import componentlist as casa_cl  # type: ignore

    out = Path(out_path)
    try:
        import shutil as _sh
        _sh.rmtree(out, ignore_errors=True)
    except Exception:
        pass

    # Convert to list to check if empty
    points_list = list(points)
    if not points_list:
        raise ValueError(f"Cannot create componentlist: no points provided")

    freq_str = f"{float(freq_ghz)}GHz" if isinstance(freq_ghz, (int, float)) else str(freq_ghz)
    cl = casa_cl()
    try:
        for ra_deg, dec_deg, flux_jy in points_list:
            cl.addcomponent(
                dir=f"J2000 {float(ra_deg)}deg {float(dec_deg)}deg",
                flux=float(flux_jy),
                fluxunit="Jy",
                freq=freq_str,
                shape="point",
            )
        cl.rename(os.fspath(out))
        # Verify the rename succeeded
        if not out.exists():
            raise RuntimeError(f"Componentlist rename failed: {out} does not exist")
    finally:
        try:
            cl.close()
            cl.done()
        except Exception:
            pass
    return os.fspath(out)


def make_nvss_component_cl(
    center_ra_deg: float,
    center_dec_deg: float,
    radius_deg: float,
    *,
    min_mjy: float = 10.0,
    freq_ghz: float | str = 1.4,
    out_path: str,
) -> str:
    """Build a multi-component list from NVSS sources in a sky region.

    Selects NVSS sources with flux >= min_mjy within radius_deg of (RA,Dec)
    and writes them as point components at freq_ghz.
    """
    from dsa110_contimg.calibration.catalogs import read_nvss_catalog  # type: ignore
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    import numpy as _np

    df = read_nvss_catalog()
    sc_all = SkyCoord(df["ra"].to_numpy() * u.deg, df["dec"].to_numpy() * u.deg, frame="icrs")
    ctr = SkyCoord(center_ra_deg * u.deg, center_dec_deg * u.deg, frame="icrs")
    sep = sc_all.separation(ctr).deg
    flux_mjy = _np.asarray(df["flux_20_cm"].to_numpy(), float)
    keep = (sep <= float(radius_deg)) & (flux_mjy >= float(min_mjy))
    pts = [
        (float(ra), float(dec), float(fx) / 1000.0)
        for ra, dec, fx in zip(
            df.loc[keep, "ra"].to_numpy(),
            df.loc[keep, "dec"].to_numpy(),
            flux_mjy[keep],
        )
    ]
    return make_multi_point_cl(pts, freq_ghz=freq_ghz, out_path=out_path)
