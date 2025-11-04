from typing import Optional
import os

import astropy.units as u
from astropy.coordinates import SkyCoord
from casacore.tables import addImagingColumns
import casacore.tables as tb


def _ensure_imaging_columns(ms_path: str) -> None:
    try:
        addImagingColumns(ms_path)
    except Exception:
        pass


def _initialize_corrected_from_data(ms_path: str) -> None:
    try:
        with tb.table(ms_path, readonly=False) as t:
            if "DATA" in t.colnames() and "CORRECTED_DATA" in t.colnames():
                t.putcol("CORRECTED_DATA", t.getcol("DATA"))
    except Exception:
        pass


def write_point_model_with_ft(
    ms_path: str,
    ra_deg: float,
    dec_deg: float,
    flux_jy: float,
    *,
    reffreq_hz: float = 1.4e9,
    spectral_index: Optional[float] = None,
    field: Optional[str] = None,
) -> None:
    """Write a physically-correct complex point-source model into MODEL_DATA using CASA ft.
    
    Args:
        ms_path: Path to Measurement Set
        ra_deg: Right ascension in degrees
        dec_deg: Declination in degrees
        flux_jy: Flux in Jy
        reffreq_hz: Reference frequency in Hz (default: 1.4 GHz)
        spectral_index: Optional spectral index for frequency-dependent flux
        field: Optional field selection (default: all fields). If specified, MODEL_DATA
              will only be written to the selected field(s).
    """
    from casatools import componentlist as cltool
    from casatasks import ft

    _ensure_imaging_columns(ms_path)

    comp_path = os.path.join(os.path.dirname(ms_path), "cal_component.cl")
    # Remove existing component list if it exists (cl.rename() will fail if it exists)
    if os.path.exists(comp_path):
        import shutil
        shutil.rmtree(comp_path, ignore_errors=True)
    cl = cltool()
    sc = SkyCoord(ra_deg * u.deg, dec_deg * u.deg, frame="icrs")
    dir_dict = {
        "refer": "J2000",
        "type": "direction",
        "long": f"{sc.ra.deg}deg",
        "lat": f"{sc.dec.deg}deg",
    }
    cl.addcomponent(
        dir=dir_dict,
        flux=float(flux_jy),
        fluxunit="Jy",
        freq=f"{reffreq_hz}Hz",
        shape="point")
    if spectral_index is not None:
        try:
            cl.setspectrum(
                which=0,
                type="spectral index",
                index=[
                    float(spectral_index)],
                reffreq=f"{reffreq_hz}Hz")
        except Exception:
            pass
    cl.rename(comp_path)
    cl.close()

    # CRITICAL: Explicitly clear MODEL_DATA with zeros before calling ft()
    # This matches the approach in ft_from_cl() and ensures MODEL_DATA is properly cleared
    # clearcal() may not fully clear MODEL_DATA, especially after rephasing
    try:
        import numpy as np
        from casacore.tables import table
        t = table(ms_path, readonly=False)
        if "MODEL_DATA" in t.colnames() and t.nrows() > 0:
            # Get DATA shape to match MODEL_DATA shape
            if "DATA" in t.colnames():
                data_sample = t.getcell("DATA", 0)
                data_shape = getattr(data_sample, "shape", None)
                data_dtype = getattr(data_sample, "dtype", None)
                if data_shape and data_dtype:
                    # Clear MODEL_DATA with zeros matching DATA shape
                    zeros = np.zeros((t.nrows(),) + data_shape, dtype=data_dtype)
                    t.putcol("MODEL_DATA", zeros)
        t.close()
    except Exception as e:
        # Non-fatal: log warning but continue
        import warnings
        warnings.warn(
            f"Failed to explicitly clear MODEL_DATA before ft(): {e}. "
            "Continuing with ft() call, but MODEL_DATA may not be properly cleared.",
            RuntimeWarning
        )

    # Pass field parameter to ensure MODEL_DATA is written to the correct field
    ft_kwargs = {"vis": ms_path, "complist": comp_path, "usescratch": True}
    if field is not None:
        ft_kwargs["field"] = field
    ft(**ft_kwargs)
    _initialize_corrected_from_data(ms_path)


def write_point_model_quick(
    ms_path: str,
    ra_deg: float,
    dec_deg: float,
    flux_jy: float,
) -> None:
    """Write a simple amplitude-only model line per frequency (testing only)."""
    import numpy as np

    _ensure_imaging_columns(ms_path)

    with tb.table(f"{ms_path}::SPECTRAL_WINDOW") as ts:
        freqs = ts.getcol("CHAN_FREQ")[0]
    amp = np.ones_like(freqs, dtype=np.float32)

    with tb.table(ms_path, readonly=False) as t:
        npol, nchan, nrow = t.getcol("DATA").shape
        blk = 4096
        line = (float(flux_jy) * amp.astype(np.complex64))
        for start in range(0, nrow, blk):
            end = min(start + blk, nrow)
            model = line[None, :, None]
            model = np.broadcast_to(model, (npol, nchan, end - start)).copy()
            t.putcolslice(
                "MODEL_DATA", model, blc=[
                    0, 0, start], trc=[
                    npol - 1, nchan - 1, end - 1])
    _initialize_corrected_from_data(ms_path)


def write_component_model_with_ft(ms_path: str, component_path: str) -> None:
    """Apply an existing CASA component list (.cl) into MODEL_DATA using ft."""
    from casatasks import ft

    if not os.path.exists(component_path):
        raise FileNotFoundError(f"Component list not found: {component_path}")

    _ensure_imaging_columns(ms_path)
    ft(vis=ms_path, complist=component_path, usescratch=True)
    _initialize_corrected_from_data(ms_path)


def write_image_model_with_ft(ms_path: str, image_path: str) -> None:
    """Apply a CASA image model into MODEL_DATA using ft."""
    from casatasks import ft

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Model image not found: {image_path}")

    _ensure_imaging_columns(ms_path)
    ft(vis=ms_path, model=image_path, usescratch=True)
    _initialize_corrected_from_data(ms_path)


def write_setjy_model(
    ms_path: str,
    field: str,
    *,
    standard: str = "Perley-Butler 2017",
    spw: str = "",
    usescratch: bool = True,
) -> None:
    """Populate MODEL_DATA via casatasks.setjy for standard calibrators."""
    from casatasks import setjy

    _ensure_imaging_columns(ms_path)
    setjy(
        vis=ms_path,
        field=str(field),
        spw=spw,
        standard=standard,
        usescratch=usescratch)
    _initialize_corrected_from_data(ms_path)
