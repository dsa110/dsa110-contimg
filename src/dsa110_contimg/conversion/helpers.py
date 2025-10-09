"""Helper utilities for UVH5 → CASA Measurement Set conversion."""

import logging
from typing import Optional, Tuple

import numpy as np
import astropy.units as u
from astropy.coordinates import EarthLocation, SkyCoord, angular_separation
from astropy.time import Time
from casacore.tables import table

from dsa110_contimg.utils.antpos_local import get_itrf

logger = logging.getLogger("dsa110_contimg.conversion.helpers")


def get_meridian_coords(pt_dec: u.Quantity, time_mjd: float) -> Tuple[u.Quantity, u.Quantity]:
    """Compute the right ascension/declination of the meridian at OVRO."""
    ovro_loc = EarthLocation.from_geodetic(
        lon=-118.2817 * u.deg,
        lat=37.2314 * u.deg,
        height=1222 * u.m,
    )
    obstime = Time(time_mjd, format="mjd")
    hadec_coord = SkyCoord(
        ha=0 * u.hourangle,
        dec=pt_dec,
        frame="hadec",
        obstime=obstime,
        location=ovro_loc,
    )
    icrs_coord = hadec_coord.transform_to("icrs")
    return icrs_coord.ra.to(u.rad), icrs_coord.dec.to(u.rad)


def _get_relative_antenna_positions(uv) -> np.ndarray:
    """Return antenna positions relative to the telescope location."""
    if hasattr(uv, "antenna_positions") and uv.antenna_positions is not None:
        return uv.antenna_positions
    telescope = getattr(uv, "telescope", None)
    if telescope is not None and getattr(telescope, "antenna_positions", None) is not None:
        return telescope.antenna_positions
    raise AttributeError("UVData object has no antenna_positions information")


def _set_relative_antenna_positions(uv, rel_positions: np.ndarray) -> None:
    """Write relative antenna positions back to the UVData structure."""
    if hasattr(uv, "antenna_positions") and uv.antenna_positions is not None:
        uv.antenna_positions[: rel_positions.shape[0]] = rel_positions
    elif hasattr(uv, "antenna_positions"):
        uv.antenna_positions = rel_positions
    else:
        setattr(uv, "antenna_positions", rel_positions)

    telescope = getattr(uv, "telescope", None)
    if telescope is not None:
        if getattr(telescope, "antenna_positions", None) is not None:
            telescope.antenna_positions[: rel_positions.shape[0]] = rel_positions
        elif hasattr(telescope, "antenna_positions"):
            telescope.antenna_positions = rel_positions
        else:
            setattr(telescope, "antenna_positions", rel_positions)


def set_antenna_positions(uvdata) -> np.ndarray:
    """Populate antenna positions for the Measurement Set."""
    logger.info("Setting DSA-110 antenna positions")
    try:
        df_itrf = get_itrf(latlon_center=None)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to load antenna coordinates: %s", exc)
        raise

    abs_positions = np.array(
        [
            df_itrf["x_m"],
            df_itrf["y_m"],
            df_itrf["z_m"],
        ]
    ).T.astype(np.float64)

    telescope_location = getattr(uvdata, "telescope_location", None)
    if telescope_location is None and getattr(uvdata, "telescope", None) is not None:
        telescope_location = getattr(uvdata.telescope, "location", None)
    if telescope_location is None:
        raise AttributeError("UVData object lacks telescope location information")
    if hasattr(telescope_location, "value"):
        telescope_location = telescope_location.value
    telescope_location = np.asarray(telescope_location)
    if getattr(telescope_location, "dtype", None) is not None and telescope_location.dtype.names:
        telescope_location = np.array(
            [telescope_location["x"], telescope_location["y"], telescope_location["z"]]
        )

    rel_positions_target: Optional[np.ndarray] = None
    try:
        rel_positions_target = _get_relative_antenna_positions(uvdata)
    except AttributeError:
        pass

    if rel_positions_target is not None and rel_positions_target.shape[0] != abs_positions.shape[0]:
        raise ValueError(
            f"Mismatch between antenna counts ({rel_positions_target.shape[0]!r} vs "
            f"{abs_positions.shape[0]!r}) when loading antenna catalogue"
        )

    relative_positions = abs_positions - telescope_location
    _set_relative_antenna_positions(uvdata, relative_positions)

    logger.info("Loaded dynamic antenna positions for %s antennas", abs_positions.shape[0])
    return abs_positions


def _ensure_antenna_diameters(uvdata, diameter_m: float = 4.65) -> None:
    """Ensure antenna diameter metadata is populated."""
    nants: Optional[int] = None
    if hasattr(uvdata, "telescope") and getattr(uvdata.telescope, "antenna_numbers", None) is not None:
        nants = len(uvdata.telescope.antenna_numbers)
    elif getattr(uvdata, "antenna_numbers", None) is not None:
        nants = len(np.unique(uvdata.antenna_numbers))

    if nants is None:
        raise AttributeError("Unable to determine antenna count to assign diameters")

    diam_array = np.full(nants, diameter_m, dtype=np.float64)

    telescope = getattr(uvdata, "telescope", None)
    if telescope is not None and hasattr(telescope, "antenna_diameters"):
        telescope.antenna_diameters = diam_array
    if hasattr(uvdata, "antenna_diameters"):
        uvdata.antenna_diameters = diam_array


def primary_beam_response(
    ant_ra: np.ndarray,
    ant_dec: float,
    src_ra: float,
    src_dec: float,
    freq_ghz: np.ndarray,
    dish_diameter_m: float = 4.7,
) -> np.ndarray:
    """Primary beam response using the DSA-110 analytic approximation."""
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
                    "Skipping WEIGHT_SPECTRUM update due to unexpected shape: %s", wspec.shape
                )
            else:
                wspec[flags] = 0.0
                tb.putcol("WEIGHT_SPECTRUM", wspec.astype(np.float32))
                logger.info("Reconstructed WEIGHT_SPECTRUM column.")

    logger.info("MODEL_DATA column set successfully")


__all__ = [
    "get_meridian_coords",
    "set_antenna_positions",
    "_ensure_antenna_diameters",
    "set_model_column",
    "amplitude_sky_model",
    "primary_beam_response",
]
