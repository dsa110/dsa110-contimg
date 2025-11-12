"""
Skymodel helpers: create CASA component lists (.cl) and apply via ft().

This module now uses pyradiosky as the default for sky model construction,
providing better sky model management, support for multiple catalog formats,
and advanced spectral modeling capabilities.

Usage:
  # Single point source (uses pyradiosky internally)
  from dsa110_contimg.calibration.skymodels import make_point_cl, ft_from_cl
  cl = make_point_cl('0834+555', ra_deg, dec_deg, flux_jy=2.3, freq_ghz=1.4,
                     out_path='/stage/dsa110-contimg/0834+555_pt.cl')
  ft_from_cl('/path/to/obs.ms', cl, field='0', usescratch=True)

  # NVSS sources (uses pyradiosky internally)
  from dsa110_contimg.calibration.skymodels import make_nvss_component_cl, ft_from_cl
  cl = make_nvss_component_cl(ra_deg, dec_deg, radius_deg=0.2, min_mjy=10.0,
                               freq_ghz=1.4, out_path='nvss.cl')
  ft_from_cl('/path/to/obs.ms', cl)

  # Direct pyradiosky usage:
  from pyradiosky import SkyModel
  from dsa110_contimg.calibration.skymodels import convert_skymodel_to_componentlist, ft_from_cl
  sky = SkyModel.from_votable_catalog('nvss.vot')
  cl = convert_skymodel_to_componentlist(sky, out_path='model.cl')
  ft_from_cl('/path/to/obs.ms', cl)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional, Tuple


def make_point_skymodel(
    name: str,
    ra_deg: float,
    dec_deg: float,
    *,
    flux_jy: float,
    freq_ghz: float | str = 1.4,
) -> "SkyModel":
    """Create a pyradiosky SkyModel for a single point source.

    Args:
        name: Source name
        ra_deg: RA in degrees
        dec_deg: Dec in degrees
        flux_jy: Flux in Jy
        freq_ghz: Reference frequency in GHz (default: 1.4)

    Returns:
        pyradiosky SkyModel object
    """
    try:
        from pyradiosky import SkyModel
    except ImportError:
        raise ImportError(
            "pyradiosky is required for make_point_skymodel(). "
            "Install with: pip install pyradiosky"
        )

    import astropy.units as u
    import numpy as np
    from astropy.coordinates import SkyCoord

    # Get reference frequency
    if isinstance(freq_ghz, (int, float)):
        ref_freq = freq_ghz * u.GHz
    else:
        ref_freq = 1.4 * u.GHz  # Default

    # Create SkyCoord
    skycoord = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")

    # Create stokes array: (4, Nfreqs, Ncomponents)
    stokes = np.zeros((4, 1, 1)) * u.Jy
    stokes[0, 0, 0] = flux_jy * u.Jy  # I stokes

    # Create SkyModel
    sky = SkyModel(
        name=[name],
        skycoord=skycoord,
        stokes=stokes,
        spectral_type="flat",
        component_type="point",
        freq_array=np.array([ref_freq.to("Hz").value]) * u.Hz,
    )

    return sky


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

    This function now uses pyradiosky internally for better sky model management.

    Returns the path to the created component list.
    """
    # Use pyradiosky to create SkyModel, then convert to componentlist
    sky = make_point_skymodel(
        name,
        ra_deg,
        dec_deg,
        flux_jy=flux_jy,
        freq_ghz=freq_ghz,
    )

    # Convert to componentlist
    return convert_skymodel_to_componentlist(sky, out_path=out_path, freq_ghz=freq_ghz)


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

    **Known Issues**:

    1. **Phase Center Bugs**: Uses ft() which does not use PHASE_DIR correctly after
       rephasing. If the MS has been rephased, MODEL_DATA may have incorrect phase
       structure, causing phase scatter in calibration. See docs/reports/FT_PHASE_CENTER_FIX.md.

    2. **WSClean Compatibility**: This function should be called BEFORE running WSClean
       or other imaging tools that modify MODEL_DATA. CASA's ft() has a known bug where
       it crashes with "double free or corruption" when MODEL_DATA already contains
       data written by WSClean or other external tools.

    **Workflow**:
    1. Seed MODEL_DATA with CASA ft() (this function) - BEFORE WSClean
    2. Run WSClean for imaging (reads seeded MODEL_DATA)

    **For Single Point Sources**:
    Use :func:`write_point_model_with_ft` with ``use_manual=True`` instead, which
    bypasses ft() phase center bugs.
    """
    # Ensure CASA env
    from dsa110_contimg.utils.casa_init import ensure_casa_path

    ensure_casa_path()

    import numpy as np
    from casatasks import ft as casa_ft  # type: ignore
    import casacore.tables as casatables  # type: ignore

    table = casatables.table  # noqa: N816

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
            RuntimeWarning,
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

    freq_str = (
        f"{float(freq_ghz)}GHz" if isinstance(freq_ghz, (int, float)) else str(freq_ghz)
    )
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


def convert_skymodel_to_componentlist(
    sky: "SkyModel",
    *,
    out_path: str,
    freq_ghz: float | str = 1.4,
) -> str:
    """Convert pyradiosky SkyModel to CASA componentlist.

    Args:
        sky: pyradiosky SkyModel object
        out_path: Path to output componentlist (.cl directory)
        freq_ghz: Reference frequency if not specified in SkyModel

    Returns:
        Path to created componentlist
    """
    try:
        from pyradiosky import SkyModel
    except ImportError:
        raise ImportError(
            "pyradiosky is required for convert_skymodel_to_componentlist(). "
            "Install with: pip install pyradiosky"
        )

    from casatools import componentlist as casa_cl  # type: ignore

    out = Path(out_path)
    try:
        import shutil as _sh

        _sh.rmtree(out, ignore_errors=True)
    except Exception:
        pass

    # Get reference frequency
    if sky.freq_array is not None and len(sky.freq_array) > 0:
        ref_freq_ghz = sky.freq_array[0].to("GHz").value
        freq_str = f"{ref_freq_ghz}GHz"
    else:
        freq_str = (
            f"{float(freq_ghz)}GHz"
            if isinstance(freq_ghz, (int, float))
            else str(freq_ghz)
        )

    from astropy.coordinates import Angle

    # Handle empty sky model
    if sky.Ncomponents == 0:
        # Create empty componentlist
        cl = casa_cl()
        try:
            cl.rename(os.fspath(out))
        finally:
            try:
                cl.close()
                cl.done()
            except Exception:
                pass
        return os.fspath(out)

    cl = casa_cl()
    try:
        for i in range(sky.Ncomponents):
            ra = sky.skycoord[i].ra
            dec = sky.skycoord[i].dec
            flux_jy = sky.stokes[0, 0, i].to("Jy").value  # I stokes, first frequency

            # Format RA/Dec as CASA expects (HH:MM:SS.sss, DD:MM:SS.sss)
            ra_str = Angle(ra).to_string(unit="hour", precision=3, pad=True)
            dec_str = Angle(dec).to_string(
                unit="deg", precision=3, alwayssign=True, pad=True
            )

            # Get spectral index if available
            if sky.spectral_type == "spectral_index" and hasattr(sky, "spectral_index"):
                spec_idx = (
                    float(sky.spectral_index[i])
                    if sky.spectral_index is not None
                    else -0.7
                )
                ref_freq_hz = (
                    sky.reference_frequency[i].to("Hz").value
                    if hasattr(sky, "reference_frequency")
                    and sky.reference_frequency is not None
                    else None
                )
                if ref_freq_hz is None:
                    ref_freq_hz = float(freq_str.replace("GHz", "")) * 1e9

                cl.addcomponent(
                    dir=f"J2000 {ra_str} {dec_str}",
                    flux=float(flux_jy),
                    fluxunit="Jy",
                    freq=freq_str,
                    shape="point",
                    spectrumtype="spectral index",
                    index=spec_idx,
                    referencerefreq=f"{ref_freq_hz}Hz",
                )
            else:
                cl.addcomponent(
                    dir=f"J2000 {ra_str} {dec_str}",
                    flux=float(flux_jy),
                    fluxunit="Jy",
                    freq=freq_str,
                    shape="point",
                )
        cl.rename(os.fspath(out))
        if not out.exists():
            raise RuntimeError(f"Componentlist rename failed: {out} does not exist")
    finally:
        try:
            cl.close()
            cl.done()
        except Exception:
            pass

    return os.fspath(out)


def make_nvss_skymodel(
    center_ra_deg: float,
    center_dec_deg: float,
    radius_deg: float,
    *,
    min_mjy: float = 10.0,
    freq_ghz: float | str = 1.4,
) -> "SkyModel":
    """Create a pyradiosky SkyModel from NVSS sources in a sky region.

    Selects NVSS sources with flux >= min_mjy within radius_deg of (RA,Dec)
    and returns a pyradiosky SkyModel object.

    Args:
        center_ra_deg: Center RA in degrees
        center_dec_deg: Center Dec in degrees
        radius_deg: Search radius in degrees
        min_mjy: Minimum flux in mJy (default: 10.0)
        freq_ghz: Reference frequency in GHz (default: 1.4)

    Returns:
        pyradiosky SkyModel object
    """
    try:
        from pyradiosky import SkyModel
    except ImportError:
        raise ImportError(
            "pyradiosky is required for make_nvss_skymodel(). "
            "Install with: pip install pyradiosky"
        )

    import astropy.units as u
    import numpy as np
    from astropy.coordinates import SkyCoord

    from dsa110_contimg.calibration.catalogs import read_nvss_catalog  # type: ignore

    df = read_nvss_catalog()
    sc_all = SkyCoord(
        df["ra"].to_numpy() * u.deg, df["dec"].to_numpy() * u.deg, frame="icrs"
    )
    ctr = SkyCoord(center_ra_deg * u.deg, center_dec_deg * u.deg, frame="icrs")
    sep = sc_all.separation(ctr).deg
    flux_mjy = np.asarray(df["flux_20_cm"].to_numpy(), float)
    keep = (sep <= float(radius_deg)) & (flux_mjy >= float(min_mjy))

    if keep.sum() == 0:
        # Return empty SkyModel
        return SkyModel(
            name=[],
            skycoord=SkyCoord([], [], unit=u.deg, frame="icrs"),
            stokes=np.zeros((4, 1, 0)) * u.Jy,
            spectral_type="flat",
            component_type="point",
        )

    # Extract sources
    ras = df.loc[keep, "ra"].to_numpy()
    decs = df.loc[keep, "dec"].to_numpy()
    fluxes = flux_mjy[keep] / 1000.0  # Convert to Jy

    # Create SkyCoord
    ra = ras * u.deg
    dec = decs * u.deg
    skycoord = SkyCoord(ra=ra, dec=dec, frame="icrs")

    # Create stokes array: (4, Nfreqs, Ncomponents)
    # For flat spectrum, we use a single frequency
    n_components = len(ras)
    stokes = np.zeros((4, 1, n_components)) * u.Jy
    stokes[0, 0, :] = fluxes * u.Jy  # I stokes

    # Get reference frequency
    if isinstance(freq_ghz, (int, float)):
        ref_freq = freq_ghz * u.GHz
    else:
        ref_freq = 1.4 * u.GHz  # Default

    # Create SkyModel
    sky = SkyModel(
        name=[f"nvss_{i}" for i in range(n_components)],
        skycoord=skycoord,
        stokes=stokes,
        spectral_type="flat",
        component_type="point",
        freq_array=np.array([ref_freq.to("Hz").value]) * u.Hz,
    )

    return sky


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

    This function now uses pyradiosky internally for better sky model management.

    Args:
        center_ra_deg: Center RA in degrees
        center_dec_deg: Center Dec in degrees
        radius_deg: Search radius in degrees
        min_mjy: Minimum flux in mJy (default: 10.0)
        freq_ghz: Reference frequency in GHz (default: 1.4)
        out_path: Path to output componentlist (.cl directory)

    Returns:
        Path to created componentlist
    """
    # Use pyradiosky to create SkyModel, then convert to componentlist
    sky = make_nvss_skymodel(
        center_ra_deg,
        center_dec_deg,
        radius_deg,
        min_mjy=min_mjy,
        freq_ghz=freq_ghz,
    )

    # Convert to componentlist
    return convert_skymodel_to_componentlist(sky, out_path=out_path, freq_ghz=freq_ghz)
