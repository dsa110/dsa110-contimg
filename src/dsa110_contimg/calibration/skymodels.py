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
from typing import Optional


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
        cl.open()
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
    """Apply a component-list skymodel to MODEL_DATA via CASA ft()."""
    from casatasks import ft as casa_ft  # type: ignore

    casa_ft(
        vis=os.fspath(ms_target),
        complist=os.fspath(cl_path),
        field=field,
        usescratch=usescratch,
    )

