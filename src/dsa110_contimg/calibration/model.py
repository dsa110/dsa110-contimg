from typing import Optional
import os

import astropy.units as u
from astropy.coordinates import SkyCoord
from casacore.tables import addImagingColumns


def write_point_model_with_ft(
    ms_path: str,
    ra_deg: float,
    dec_deg: float,
    flux_jy: float,
    *,
    reffreq_hz: float = 1.4e9,
    spectral_index: Optional[float] = None,
) -> None:
    """Write a physically-correct complex point-source model into MODEL_DATA using CASA ft.

    Parameters
    ----------
    ms_path : str
        Path to Measurement Set directory.
    ra_deg, dec_deg : float
        Calibrator ICRS coordinates (degrees).
    flux_jy : float
        Flux density in Jy (at ``reffreq_hz`` unless spectral index provided).
    reffreq_hz : float
        Reference frequency for the component (default 1.4 GHz).
    spectral_index : float, optional
        If provided, sets a spectral-index spectrum on the component (single term).
    """
    from casatools import componentlist as cltool
    from casatasks import ft
    import casacore.tables as tb

    # Ensure imaging columns exist
    try:
        addImagingColumns(ms_path)
    except Exception:
        pass

    # Build component list
    comp_path = os.path.join(os.path.dirname(ms_path), "cal_component.cl")
    cl = cltool()
    sc = SkyCoord(ra_deg * u.deg, dec_deg * u.deg, frame="icrs")
    ra_hms = sc.ra.to_string(unit=u.hour, sep=":", precision=9)
    dec_dms = sc.dec.to_string(unit=u.deg, sep=":", precision=9, alwayssign=True)
    dir_str = f"J2000 {ra_hms} {dec_dms}"
    cl.addcomponent(dir=dir_str, flux=float(flux_jy), fluxunit="Jy", freq=f"{reffreq_hz}Hz", shape="point")
    if spectral_index is not None:
        try:
            cl.setspectrum(which=0, type="spectral index", index=[float(spectral_index)], reffreq=f"{reffreq_hz}Hz")
        except Exception:
            pass
    cl.rename(comp_path)
    cl.close()

    # Fourier-transform the component into MODEL_DATA
    ft(vis=ms_path, complist=comp_path, usescratch=True)

    # Initialize CORRECTED_DATA from DATA if present
    try:
        with tb.table(ms_path, readonly=False) as t:
            if "CORRECTED_DATA" in t.colnames():
                t.putcol("CORRECTED_DATA", t.getcol("DATA"))
    except Exception:
        pass


def write_point_model_quick(
    ms_path: str,
    ra_deg: float,
    dec_deg: float,
    flux_jy: float,
) -> None:
    """Write a simple amplitude-only model line per frequency (testing only).

    This is not phase-correct and should not be used for real solves; kept for fast tests.
    """
    import numpy as np
    import casacore.tables as tb

    try:
        addImagingColumns(ms_path)
    except Exception:
        pass

    with tb.table(f"{ms_path}::SPECTRAL_WINDOW") as ts:
        freqs = ts.getcol("CHAN_FREQ")[0]
    # Flat spectrum
    amp = np.ones_like(freqs, dtype=np.float32)

    with tb.table(ms_path, readonly=False) as t:
        npol, nchan, nrow = t.getcol("DATA").shape
        blk = 4096
        line = (float(flux_jy) * amp.astype(np.complex64))
        for start in range(0, nrow, blk):
            end = min(start + blk, nrow)
            model = line[None, :, None]
            model = np.broadcast_to(model, (npol, nchan, end - start)).copy()
            t.putcolslice("MODEL_DATA", model, blc=[0, 0, start], trc=[npol - 1, nchan - 1, end - 1])
        try:
            t.putcol("CORRECTED_DATA", t.getcol("DATA"))
        except Exception:
            pass

