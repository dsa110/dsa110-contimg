"""Model helper functions for conversion."""

import logging
from typing import Optional

import astropy.units as u

# Ensure CASAPATH is set before importing CASA modules
from dsa110_contimg.utils.casa_init import ensure_casa_path

ensure_casa_path()

import casacore.tables as casatables  # type: ignore
import numpy as np

table = casatables.table  # noqa: N816

logger = logging.getLogger("dsa110_contimg.conversion.helpers")


def primary_beam_response(
    ant_ra: np.ndarray,
    ant_dec: float,
    src_ra: float,
    src_dec: float,
    freq_ghz: np.ndarray,
    dish_diameter_m: float = 4.7,
) -> np.ndarray:
    """Primary beam response using the DSA-110 analytic approximation."""
    try:
        from astropy.coordinates import angular_separation  # type: ignore
    except Exception:
        # Fallback implementation
        def angular_separation(ra1, dec1, ra2, dec2):
            ra1 = np.asarray(ra1, dtype=float)
            dec1 = np.asarray(dec1, dtype=float)
            ra2 = np.asarray(ra2, dtype=float)
            dec2 = np.asarray(dec2, dtype=float)
            cossep = np.sin(dec1) * np.sin(dec2) + np.cos(dec1) * np.cos(dec2) * np.cos(ra1 - ra2)
            cossep = np.clip(cossep, -1.0, 1.0)
            return np.arccos(cossep)

    dis = np.array(angular_separation(ant_ra, ant_dec, src_ra, src_dec))
    if dis.ndim > 0 and dis.shape[0] > 1:
        dis = dis[:, np.newaxis]

    lam = 0.299792458 / freq_ghz
    arg = 1.2 * dis * dish_diameter_m / lam
    with np.errstate(divide="ignore", invalid="ignore"):
        pb = (np.cos(np.pi * arg) / (1 - 4 * arg**2)) ** 4
    return pb


def amplitude_sky_model(
    source_ra: u.Quantity,
    source_dec: u.Quantity,
    flux_jy: float,
    lst: np.ndarray,
    pt_dec: u.Quantity,
    freq_ghz: np.ndarray,
    dish_diameter_m: float = 4.7,
) -> np.ndarray:
    """Construct a primary-beam weighted amplitude model."""
    ant_ra = lst
    ant_dec = pt_dec.to_value(u.rad)
    src_ra = source_ra.to_value(u.rad)
    src_dec = source_dec.to_value(u.rad)

    pb = primary_beam_response(
        ant_ra,
        ant_dec,
        src_ra,
        src_dec,
        freq_ghz,
        dish_diameter_m=dish_diameter_m,
    )
    return (flux_jy * pb).astype(np.float32)


def set_model_column(
    msname: str,
    uvdata,
    pt_dec: u.Quantity,
    ra: u.Quantity,
    dec: u.Quantity,
    flux_jy: Optional[float] = None,
) -> None:
    """Populate MODEL_DATA (and related columns) for the produced MS."""
    logger.info("Setting MODEL_DATA column")
    if flux_jy is not None:
        fobs = uvdata.freq_array.squeeze() / 1e9
        lst = uvdata.lst_array
        model = amplitude_sky_model(ra, dec, flux_jy, lst, pt_dec, fobs)
        model = np.tile(model[:, :, np.newaxis], (1, 1, uvdata.Npols)).astype(np.complex64)
    else:
        model = np.ones((uvdata.Nblts, uvdata.Nfreqs, uvdata.Npols), dtype=np.complex64)

    ms_path = f"{msname}.ms"
    with table(ms_path, readonly=False) as tb:
        data_shape = tb.getcol("DATA").shape
        model_transposed = np.transpose(model, (2, 1, 0))

        if model_transposed.shape != data_shape:
            logger.warning(
                "Model shape %s does not match DATA shape %s; skipping MODEL_DATA write",
                model_transposed.shape,
                data_shape,
            )
        else:
            tb.putcol("MODEL_DATA", model_transposed)

        if "CORRECTED_DATA" in tb.colnames():
            try:
                corr = tb.getcol("CORRECTED_DATA")
                if not np.any(corr):
                    tb.putcol("CORRECTED_DATA", tb.getcol("DATA"))
            except Exception:  # pragma: no cover - best effort
                pass

        if "WEIGHT_SPECTRUM" in tb.colnames():
            flags = tb.getcol("FLAG")
            weights = tb.getcol("WEIGHT")
            ncorr = weights.shape[0]
            nchan = flags.shape[0]

            wspec = np.repeat(weights[np.newaxis, :, :], nchan, axis=0)
            if wspec.shape != (nchan, ncorr, weights.shape[1]):
                logger.debug(
                    "Skipping WEIGHT_SPECTRUM update due to unexpected shape: %s",
                    wspec.shape,
                )
            else:
                wspec[flags] = 0.0
                tb.putcol("WEIGHT_SPECTRUM", wspec.astype(np.float32))
                logger.info("Reconstructed WEIGHT_SPECTRUM column.")

    logger.info("MODEL_DATA column set successfully")
