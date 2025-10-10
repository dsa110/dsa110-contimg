#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DSA-110 UVH5 → CASA MS converter.

This module adapts the proven grouping and MS-writing behavior while keeping our current runtime stack (pyuvdata,
casatools/casatasks) and data model assumptions stable.

Key choices vs. our legacy converter:
- Group subbands by filename timestamp with a ±30 s tolerance
- Expect the canonical 16 SPWs (sb00..sb15); skip incomplete groups
- Merge subbands along frequency and ensure ascending channel order
- Prefer direct MS writing via pyuvdata.write_ms (single-SPW) by default
- Preserve our phasing/UVW logic via phase_visibilities (stable in our env)
- Optionally set a unity/beam model via set_model_column when flux is provided

The legacy converter remains available as
`archive/legacy/core_conversion/uvh5_to_ms_converter`.
"""

from dsa110_contimg.utils.fringestopping import calc_uvw_blt
from dsa110_contimg.conversion.helpers import (
    set_antenna_positions,
    _ensure_antenna_diameters,
    get_meridian_coords,
    set_model_column,
)
import os
import time
import glob
import logging
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import astropy.units as u
from astropy.time import Time
from astropy.coordinates import SkyCoord
from pyuvdata import UVData
from casacore.tables import addImagingColumns
from dsa110_contimg.calibration.model import write_point_model_with_ft
from dsa110_contimg.calibration.catalogs import (
    read_vla_parsed_catalog_with_flux,
    nearest_calibrator_within_radius,
)
from pyuvdata import utils as uvutils
# Prefer the phasing.calc_uvw entry point when available (pyuvdata>=3.2)
try:  # pragma: no cover
    from pyuvdata.utils.phasing import calc_uvw as _PU_CALC_UVW
except Exception:  # pragma: no cover
    _PU_CALC_UVW = None

def _calc_uvw_fast(
    *,
    app_ra,
    app_dec,
    frame_pa,
    lst_array,
    antenna_positions,
    antenna_numbers,
    ant_1_array,
    ant_2_array,
    telescope_lat,
    telescope_lon,
):
    """Vectorized UVW computation using pyuvdata if available.

    Falls back to uvutils.calc_uvw if phasing.calc_uvw is not exposed.
    """
    if _PU_CALC_UVW is not None:
        return _PU_CALC_UVW(
            app_ra=app_ra,
            app_dec=app_dec,
            frame_pa=frame_pa,
            lst_array=lst_array,
            use_ant_pos=True,
            antenna_positions=antenna_positions,
            antenna_numbers=antenna_numbers,
            ant_1_array=ant_1_array,
            ant_2_array=ant_2_array,
            telescope_lat=telescope_lat,
            telescope_lon=telescope_lon,
        )
    # Fallback to uvutils.calc_uvw (older import path)
    return uvutils.calc_uvw(
        app_ra=app_ra,
        app_dec=app_dec,
        frame_pa=frame_pa,
        lst_array=lst_array,
        use_ant_pos=True,
        antenna_positions=antenna_positions,
        antenna_numbers=antenna_numbers,
        ant_1_array=ant_1_array,
        ant_2_array=ant_2_array,
        telescope_lat=telescope_lat,
        telescope_lon=telescope_lon,
    )
import shutil
import csv

from dsa110_contimg.conversion.strategies.direct_subband import (
    write_ms_from_subbands as _direct_write_ms,
    _write_ms_subband_part as _direct_write_subband,
)
from dsa110_contimg.qa.quicklooks import (
    run_ragavi_vis,
    run_shadems_quicklooks,
)


def write_ms_from_subbands(file_list, ms_path, scratch_dir=None):
    """Write MS from subband files using direct subband approach."""
    return _direct_write_ms(file_list, ms_path, scratch_dir=scratch_dir)


def write_ms_subband(subband_file, part_out):
    """Write a single subband MS."""
    return _direct_write_subband(subband_file, part_out)


logger = logging.getLogger("uvh5_to_ms_converter_v2")

# Optional dask-ms support
try:  # pragma: no cover - optional import
    import dask
    import dask.array as da
    from daskms import Dataset as DMSDataset
    from daskms.dask_ms import xds_to_table
    HAVE_DASKMS = True
except Exception:  # pragma: no cover
    HAVE_DASKMS = False


# ---------------------------
# dask-ms writer (optional)
# ---------------------------

def _write_ms_with_daskms(
        uv: "UVData",
        ms_full_path: str,
        *,
        row_chunks: Optional[int] = None,
        cube_row_chunks: Optional[int] = None,
        field_per_integration: bool = False) -> None:
    """Write an MS using dask-ms from a prepared UVData object.

    Assumes a single SPW and linear pols (XX/YY). This function writes
    the subtables first, then the main table, and computes the dask graph.
    """
    if not HAVE_DASKMS:
        raise RuntimeError("dask-ms not importable in this environment")

    import os, shutil
    # Do NOT pre-create the MS root directory; dask-ms will create proper tables.
    # If a stale directory exists (not a proper table), remove it first.
    try:
        if os.path.isdir(ms_full_path):
            shutil.rmtree(ms_full_path, ignore_errors=True)
    except Exception:
        pass

    # Allow tuning via env var DASKMS_ROW_CHUNKS
    try:
        _row_chunks = int(os.getenv('DASKMS_ROW_CHUNKS', '8192'))
    except Exception:
        _row_chunks = 8192
    # Basic shape logging
    try:
        nrow = int(getattr(uv, 'Nblts', 0))
        nchan = int(getattr(uv, 'Nfreqs', 0))
        npol = int(getattr(uv, 'Npols', 0))
        logging.getLogger("uvh5_to_ms_converter_v2").info(
            "dask-ms: preparing datasets (rows=%d, chans=%d, pols=%d)", nrow, nchan, npol)
    except Exception:
        pass
    main_ds = _build_main_table_dataset(uv, row_chunks=_row_chunks, field_per_integration=field_per_integration)
    spw_ds = _build_spw_dataset(uv)
    pol_ds = _build_pol_dataset(uv)
    ant_ds = _build_antenna_dataset(uv)
    feed_ds = _build_feed_dataset(uv)

    # Field center: meridian at pointing declination at mid MJD
    from astropy.time import Time
    mid_mjd = float(np.mean(Time(uv.time_array, format='jd').mjd))
    pt_dec = uv.extra_keywords.get("phase_center_dec",
                                   0.0) * u.rad if hasattr(uv,
                                                           'extra_keywords') else 0.0 * u.rad
    ra_icrs, dec_icrs = get_meridian_coords(pt_dec, mid_mjd)
    if field_per_integration:
        # Build one FIELD row per unique integration time
        from astropy.time import Time as _Time
        utime, _, invert = np.unique(uv.time_array, return_index=True, return_inverse=True)
        mjd_vec = _Time(utime, format='jd').mjd.astype(float)
        try:
            logging.getLogger("uvh5_to_ms_converter_v2").info(
                "dask-ms: field-per-integration enabled (unique_times=%d)", len(utime))
        except Exception:
            pass
        ra_list = []
        dec_list = []
        for mjd in mjd_vec:
            ra_i, dec_i = get_meridian_coords(pt_dec, mjd)
            ra_list.append(ra_i)
            dec_list.append(dec_i)
        # TIME column in FIELD is in seconds (MJD seconds)
        time_list_sec = list((mjd_vec * 86400.0).astype(float))
        field_ds = _build_field_dataset_multi(ra_list, dec_list, time_list_sec=time_list_sec)
        # Update FIELD_ID mapping on main table
        # Rebuild main_ds with explicit FIELD_ID set to per-row mapping
        main_ds = _build_main_table_dataset(uv, row_chunks=_row_chunks, field_per_integration=True, field_id_map=invert.astype(np.int32))
    else:
        # Use midpoint time in seconds for single FIELD TIME
        field_mid_sec = float(mid_mjd * 86400.0)
        field_ds = _build_field_dataset(ra_icrs, dec_icrs, time_sec=field_mid_sec)

    ddid_ds = _build_ddid_dataset()

    # OBSERVATION dataset (1 row)
    from astropy.time import Time as _Time
    t_sec = _Time(uv.time_array, format='jd').mjd.astype(float) * 86400.0
    t_min = float(np.min(t_sec)) if t_sec.size else 0.0
    t_max = float(np.max(t_sec)) if t_sec.size else 0.0
    telname = getattr(uv, 'telescope_name', None) or getattr(getattr(uv, 'telescope', None), 'name', None) or 'DSA-110'
    obs_vars = {
        'TIME_RANGE': (('row', 'tr'), da.from_array(np.array([[t_min, t_max]], dtype=np.float64), chunks=(1, 2))),
        'TELESCOPE_NAME': (('row',), da.from_array(np.array([str(telname)], dtype=object), chunks=(1,))),
        'OBSERVER': (('row',), da.from_array(np.array(['unknown'], dtype=object), chunks=(1,))),
        'PROJECT': (('row',), da.from_array(np.array([''], dtype=object), chunks=(1,))),
        'RELEASE_DATE': (('row',), da.from_array(np.array([0.0], dtype=np.float64), chunks=(1,))),
    }
    obs_coords = {
        'row': (('row',), da.arange(1, chunks=(1,))),
        'tr': (('tr',), da.arange(2, chunks=(2,))),
    }
    from daskms import Dataset as DMSDataset
    obs_ds = DMSDataset(obs_vars, coords=obs_coords, attrs={})

    writes = []
    # Create main table first
    writes += xds_to_table(
        main_ds,
        ms_full_path,
        columns=[
            'ANTENNA1',
            'ANTENNA2',
            'UVW',
            'TIME',
            'TIME_CENTROID',
            'INTERVAL',
            'SCAN_NUMBER',
            'ARRAY_ID',
            'OBSERVATION_ID',
            'FIELD_ID',
            'DATA_DESC_ID',
            'DATA',
            'FLAG',
            'SIGMA',
            'WEIGHT',
            'WEIGHT_SPECTRUM',
        ],
    )
    logging.getLogger("uvh5_to_ms_converter_v2").info("dask-ms: MAIN table write graph built")
    # Then create and link subtables
    writes += xds_to_table(spw_ds,
                           f"{ms_full_path}::SPECTRAL_WINDOW",
                           columns="ALL")
    writes += xds_to_table(pol_ds,
                           f"{ms_full_path}::POLARIZATION",
                           columns="ALL")
    writes += xds_to_table(ant_ds, f"{ms_full_path}::ANTENNA", columns="ALL")
    writes += xds_to_table(feed_ds, f"{ms_full_path}::FEED", columns="ALL")
    writes += xds_to_table(field_ds, f"{ms_full_path}::FIELD", columns="ALL")
    writes += xds_to_table(ddid_ds,
                           f"{ms_full_path}::DATA_DESCRIPTION",
                           columns="ALL")
    writes += xds_to_table(obs_ds, f"{ms_full_path}::OBSERVATION", columns="ALL")

    logging.getLogger("uvh5_to_ms_converter_v2").info(
        "dask-ms: submitting %d write tasks", len(writes))
    dask.compute(writes)
    logging.getLogger("uvh5_to_ms_converter_v2").info("dask-ms: write completed for %s", ms_full_path)

    # Attach MEASINFO keywords for direction and epoch columns
    try:
        from casacore.tables import table as ctable
        with ctable(f"{ms_full_path}::FIELD", readonly=False) as tf:
            for col in ("PHASE_DIR", "DELAY_DIR", "REFERENCE_DIR"):
                if col in tf.colnames():
                    kw = tf.getcolkeywords(col)
                    kw = kw or {}
                    kw["MEASINFO"] = {"Ref": "J2000", "Type": "Direction"}
                    tf.putcolkeywords(col, kw)
        with ctable(ms_full_path, readonly=False) as mt:
            for col in ("TIME", "TIME_CENTROID"):
                if col in mt.colnames():
                    kw = mt.getcolkeywords(col)
                    kw = kw or {}
                    kw["MEASINFO"] = {"Ref": "UTC", "Type": "Epoch"}
                    mt.putcolkeywords(col, kw)
        with ctable(f"{ms_full_path}::FEED", readonly=False) as ft:
            if 'RECEPTOR_ANGLE' in ft.colnames():
                kw = ft.getcolkeywords('RECEPTOR_ANGLE')
                kw = kw or {}
                kw["MEASINFO"] = {"Ref": "RAD", "Type": "Angle"}
                ft.putcolkeywords('RECEPTOR_ANGLE', kw)
    except Exception as e:
        logging.getLogger("uvh5_to_ms_converter_v2").warning("MEASINFO keyword attach skipped: %s", e)

    # Ensure main table OBSERVATION_ID column points to row 0
    try:
        from casacore.tables import table as ctable
        with ctable(ms_full_path, ack=False, readonly=False) as mt:
            if 'OBSERVATION_ID' in mt.colnames():
                mt.putcol('OBSERVATION_ID', np.zeros(mt.nrows(), dtype=np.int32))
    except Exception as e:
        logging.getLogger("uvh5_to_ms_converter_v2").warning("Set OBSERVATION_ID failed: %s", e)

    # Optional strict validation
    try:
        from dsa110_contimg.conversion.uvh5_to_ms_converter_v2 import _validate_ms_strict as _v
        _v(ms_full_path, expect_fields=(len(utime) if field_per_integration else None), expect_linear=True)
    except Exception as e:
        # Surface as runtime error to caller
        raise RuntimeError(f"MS strict validation failed: {e}")


def _validate_ms_strict(ms_path: str, *, expect_fields: Optional[int] = None, expect_linear: bool = True) -> None:
    """Validate key MS invariants required by our calibration pipeline.

    Raises RuntimeError with a concise message on the first failed check.
    """
    from casacore.tables import table as ctable
    import numpy as np

    # MAIN checks
    with ctable(ms_path) as tb:
        cols = set(tb.colnames())
        for c in ("DATA", "FLAG", "TIME", "TIME_CENTROID", "INTERVAL", "FIELD_ID", "DATA_DESC_ID", "SIGMA", "WEIGHT"):
            if c not in cols:
                raise RuntimeError(f"MS missing required column {c}")
        # WEIGHT_SPECTRUM strongly recommended
        if "WEIGHT_SPECTRUM" not in cols:
            raise RuntimeError("MS missing WEIGHT_SPECTRUM")
        nrow = tb.nrows()
        if nrow <= 0:
            raise RuntimeError("MS has zero rows")
        d0 = tb.getcell("DATA", 0)
        if d0.ndim != 2 or d0.shape[0] <= 0 or d0.shape[1] <= 0:
            raise RuntimeError(f"DATA cell shape invalid: {d0.shape}")
        iv = tb.getcol("INTERVAL")
        if not np.all(np.isfinite(iv)) or not np.all(iv > 0):
            raise RuntimeError("INTERVAL must be positive and finite for all rows")

    # SPW checks
    with ctable(f"{ms_path}::SPECTRAL_WINDOW") as spw:
        for c in ("NUM_CHAN", "CHAN_FREQ", "CHAN_WIDTH", "EFFECTIVE_BW", "RESOLUTION"):
            if c not in spw.colnames():
                raise RuntimeError(f"SPW missing {c}")
        if int(np.asarray(spw.getcol("NUM_CHAN")).ravel()[0]) <= 0:
            raise RuntimeError("SPW::NUM_CHAN must be >0")

    # POL checks
    with ctable(f"{ms_path}::POLARIZATION") as pol:
        ct = np.asarray(pol.getcol("CORR_TYPE"))
        if ct.size == 0:
            raise RuntimeError("POLARIZATION::CORR_TYPE empty")
        if expect_linear:
            # 5=XX,6=YY
            if not np.all(np.isin(ct, [5, 6])):
                raise RuntimeError("POLARIZATION must be linear [5,6] (XX,YY)")

    # FIELD checks
    with ctable(f"{ms_path}::FIELD") as fld:
        nf = fld.nrows()
        if expect_fields is not None and nf != int(expect_fields):
            raise RuntimeError(f"FIELD rows {nf} != expected {expect_fields}")
        if "NUM_POLY" in fld.colnames():
            npoly = np.asarray(fld.getcol("NUM_POLY"))
            if np.any(npoly != 0):
                raise RuntimeError("FIELD::NUM_POLY must be 0 for constant directions")
        # PHASE_DIR presence and MEASINFO are strongly expected
        if "PHASE_DIR" not in fld.colnames():
            raise RuntimeError("FIELD missing PHASE_DIR")
        for col in ("DELAY_DIR", "REFERENCE_DIR"):
            if col not in fld.colnames():
                raise RuntimeError(f"FIELD missing {col}")

    # OBSERVATION present
    with ctable(f"{ms_path}::OBSERVATION") as obs:
        if obs.nrows() == 0:
            raise RuntimeError("OBSERVATION has zero rows")


def _build_main_table_dataset(uv: "UVData", *, row_chunks: int = 8192, field_per_integration: bool = False, field_id_map: Optional[np.ndarray] = None) -> "DMSDataset":
    import numpy as np
    from astropy.time import Time

    nrow = int(uv.Nblts)
    nchan = int(uv.Nfreqs)
    npol = int(uv.Npols)

    chunks_row = (min(row_chunks, nrow),)
    chunks_cube = (min(row_chunks, nrow), nchan, npol)

    a1 = da.from_array(
        np.asarray(
            uv.ant_1_array,
            dtype=np.int32),
        chunks=chunks_row)
    a2 = da.from_array(
        np.asarray(
            uv.ant_2_array,
            dtype=np.int32),
        chunks=chunks_row)
    uvw = da.from_array(
        np.asarray(
            uv.uvw_array, dtype=np.float64), chunks=(
            chunks_row[0], 3))

    t_mjd = Time(uv.time_array, format='jd').mjd.astype(np.float64)
    time_sec = da.from_array(t_mjd * 86400.0, chunks=chunks_row)
    time_centroid = time_sec

    try:
        tint = np.asarray(getattr(uv, 'integration_time', None))
        if tint is None or np.size(tint) == 0:
            raise ValueError
        if np.ndim(tint) == 0:
            intval = np.full(nrow, float(tint), dtype=np.float64)
        else:
            intval = np.asarray(tint, dtype=np.float64)
        # Sanity: if non-positive or non-finite, derive from TIME spacing
        if not np.all(np.isfinite(intval)) or np.all(intval <= 0):
            raise ValueError
    except Exception:
        utime = np.unique(uv.time_array)
        dt_s = float(np.median(np.diff(utime))) * 86400.0 if utime.size >= 2 else 1.0
        intval = np.full(nrow, dt_s, dtype=np.float64)
    interval = da.from_array(intval, chunks=chunks_row)

    # Use 1-based scan number by default for CASA friendliness
    scan = da.from_array(np.ones(nrow, dtype=np.int32), chunks=chunks_row)
    arr_id = da.from_array(np.zeros(nrow, dtype=np.int32), chunks=chunks_row)
    obs_id = da.from_array(np.zeros(nrow, dtype=np.int32), chunks=chunks_row)
    if field_per_integration and field_id_map is not None:
        field_id = da.from_array(np.asarray(field_id_map, dtype=np.int32), chunks=chunks_row)
    else:
        field_id = da.from_array(np.zeros(nrow, dtype=np.int32), chunks=chunks_row)
    ddid = da.from_array(np.zeros(nrow, dtype=np.int32), chunks=chunks_row)

    # Ensure DATA/FLAG are shaped (row, chan, corr); squeeze single-SPW axis if present
    _data_np = np.asarray(uv.data_array)
    if _data_np.ndim == 4 and _data_np.shape[1] == 1:
        _data_np = _data_np[:, 0, :, :]
    elif _data_np.ndim == 4:
        # Unexpected multiple SPWs at this stage
        raise RuntimeError(f"DATA has multiple SPWs (shape={_data_np.shape}); expected single-SPW")
    if _data_np.shape[1] != nchan or _data_np.shape[2] != npol:
        # Re-derive channel/pol counts from array in case uv.Nfreqs/Npols are stale
        nchan = int(_data_np.shape[1])
        npol = int(_data_np.shape[2])
    data = da.from_array(_data_np, chunks=(chunks_row[0], nchan, npol))

    _flag_np = np.asarray(uv.flag_array).astype(np.bool_)
    if _flag_np.ndim == 4 and _flag_np.shape[1] == 1:
        _flag_np = _flag_np[:, 0, :, :]
    elif _flag_np.ndim == 4:
        raise RuntimeError(f"FLAG has multiple SPWs (shape={_flag_np.shape}); expected single-SPW")
    flag = da.from_array(_flag_np, chunks=(chunks_row[0], nchan, npol))

    # Per-row SIGMA/WEIGHT (npol) initialized to ones
    sigma = da.from_array(np.ones((nrow, npol), dtype=np.float32), chunks=(chunks_row[0], npol))
    weight = sigma

    # Per-channel WEIGHT_SPECTRUM by broadcasting WEIGHT across channels
    try:
        weight_spectrum = da.broadcast_to(weight[:, None, :], (nrow, nchan, npol))
    except Exception:
        weight_spectrum = None

    vars_main = {
        'ANTENNA1': (('row',), a1),
        'ANTENNA2': (('row',), a2),
        'UVW': (('row', 'uvw'), uvw),
        'TIME': (('row',), time_sec),
        'TIME_CENTROID': (('row',), time_centroid),
        'INTERVAL': (('row',), interval),
        'SCAN_NUMBER': (('row',), scan),
        'ARRAY_ID': (('row',), arr_id),
        'OBSERVATION_ID': (('row',), obs_id),
        'FIELD_ID': (('row',), field_id),
        'DATA_DESC_ID': (('row',), ddid),
        'DATA': (('row', 'chan', 'corr'), data),
        'FLAG': (('row', 'chan', 'corr'), flag),
        'SIGMA': (('row', 'corr'), sigma),
        'WEIGHT': (('row', 'corr'), weight),
    }
    if weight_spectrum is not None:
        vars_main['WEIGHT_SPECTRUM'] = (('row', 'chan', 'corr'), weight_spectrum)
    coords = {
        'row': (('row',), da.arange(nrow, chunks=chunks_row)),
        'chan': (('chan',), da.arange(nchan, chunks=(nchan,))),
        'corr': (('corr',), da.arange(npol, chunks=(npol,))),
        'uvw': (('uvw',), da.arange(3, chunks=(3,))),
    }
    return DMSDataset(vars_main, coords=coords, attrs={})


def _build_spw_dataset(uv: "UVData") -> "DMSDataset":
    import numpy as np
    freq = np.asarray(uv.freq_array).reshape(-1)
    nchan = int(freq.size)
    try:
        chwid = float(np.abs(getattr(uv, 'channel_width', None)))
        if not np.isfinite(chwid) or chwid == 0.0:
            raise ValueError
        chan_width = np.full(nchan, chwid, dtype=np.float64)
    except Exception:
        df = np.diff(freq)
        w = float(np.median(np.abs(df))) if df.size else 1.0
        chan_width = np.full(nchan, w, dtype=np.float64)

    eff_bw = np.abs(chan_width)
    resolution = np.abs(chan_width)
    vars_spw = {
        'NUM_CHAN': (('row',), da.from_array(np.array([nchan], dtype=np.int32), chunks=(1,))),
        'CHAN_FREQ': (('row', 'chan'), da.from_array(freq[np.newaxis, :], chunks=(1, nchan))),
        'CHAN_WIDTH': (('row', 'chan'), da.from_array(chan_width[np.newaxis, :], chunks=(1, nchan))),
        'EFFECTIVE_BW': (('row', 'chan'), da.from_array(eff_bw[np.newaxis, :], chunks=(1, nchan))),
        'RESOLUTION': (('row', 'chan'), da.from_array(resolution[np.newaxis, :], chunks=(1, nchan))),
        'MEAS_FREQ_REF': (('row',), da.from_array(np.array([5], dtype=np.int32), chunks=(1,))),
        'NAME': (('row',), da.from_array(np.array(['SPW1'], dtype=object), chunks=(1,))),
    }
    coords = {
        'row': (('row',), da.arange(1, chunks=(1,))),
        'chan': (('chan',), da.arange(nchan, chunks=(nchan,))),
    }
    return DMSDataset(vars_spw, coords=coords, attrs={})


def _build_pol_dataset(uv: "UVData") -> "DMSDataset":
    import numpy as np
    # UVData.polarization_array is in AIPS convention: -5=XX, -6=YY, -7=XY, -8=YX
    # MS POLARIZATION::CORR_TYPE must use casacore Stokes enum (positive): 5,6,7,8
    raw = np.asarray(getattr(uv, 'polarization_array', np.array([-5, -6], dtype=np.int32)))
    aips_to_ms = {-5: 5, -6: 6, -7: 7, -8: 8}
    corr_types = np.array([aips_to_ms.get(int(c), int(c)) for c in raw], dtype=np.int32)
    nc = int(corr_types.size)
    # CORR_PRODUCT maps receptors (0/1) for each correlation; stays the same
    prod_map = {5: (0, 0), 6: (1, 1), 7: (0, 1), 8: (1, 0), -5: (0, 0), -6: (1, 1), -7: (0, 1), -8: (1, 0)}
    corr_prod = np.array([prod_map.get(int(c), (0, 0)) for c in raw], dtype=np.int32)

    vars_pol = {
        'NUM_CORR': (('row',), da.from_array(np.array([nc], dtype=np.int32), chunks=(1,))),
        'CORR_TYPE': (('row', 'corr'), da.from_array(corr_types[np.newaxis, :], chunks=(1, nc))),
        'CORR_PRODUCT': (('row', 'corr', 'receptors'), da.from_array(corr_prod[np.newaxis, :, :], chunks=(1, nc, 2))),
    }
    coords = {
        'row': (('row',), da.arange(1, chunks=(1,))),
        'corr': (('corr',), da.arange(nc, chunks=(nc,))),
        'receptors': (('receptors',), da.arange(2, chunks=(2,))),
    }
    return DMSDataset(vars_pol, coords=coords, attrs={})


def _build_antenna_dataset(uv: "UVData") -> "DMSDataset":
    import numpy as np
    # Positions are required; ensure present
    pos = np.asarray(getattr(uv, 'antenna_positions', None), dtype=np.float64)
    if pos is None or pos.size == 0:
        raise RuntimeError(
            "UVData missing antenna_positions; cannot build ANTENNA table")
    if pos.ndim != 2 or pos.shape[1] != 3:
        raise RuntimeError(
            f"antenna_positions has invalid shape {pos.shape}; expected (N,3)")
    nants = int(pos.shape[0])

    # Names: prefer UVData.antenna_names; otherwise synthesize pad1..padN
    try:
        names_list = list(getattr(uv, 'antenna_names', []))
    except Exception:
        names_list = []
    if not names_list or len(names_list) != nants:
        names_list = [f'pad{i+1}' for i in range(nants)]
    names = np.array(names_list, dtype=object)

    diam = np.full(nants, 4.65, dtype=np.float32)
    mount = np.array(['ALT-AZ'] * nants, dtype=object)
    station = np.array(['DSA-110'] * nants, dtype=object)

    vars_ant = {
        'NAME': (('row',), da.from_array(names, chunks=(nants,))),
        'STATION': (('row',), da.from_array(station, chunks=(nants,))),
        'POSITION': (('row', 'xyz'), da.from_array(pos, chunks=(nants, 3))),
        'DISH_DIAMETER': (('row',), da.from_array(diam, chunks=(nants,))),
        'MOUNT': (('row',), da.from_array(mount, chunks=(nants,))),
    }
    coords = {
        'row': (('row',), da.arange(nants, chunks=(nants,))),
        'xyz': (('xyz',), da.arange(3, chunks=(3,))),
    }
    return DMSDataset(vars_ant, coords=coords, attrs={})


def _build_feed_dataset(uv: "UVData") -> "DMSDataset":
    """Construct a FEED subtable with linear receptors X/Y for each antenna.

    - POLARIZATION_TYPE: ['X','Y'] per antenna
    - RECEPTOR_ANGLE: [0, 90 deg] in radians by convention for X/Y receptors
    - POL_RESPONSE: 2x2 identity matrix (complex)
    - SPECTRAL_WINDOW_ID: -1 (applies to all SPWs)
    - ANTENNA_ID: 0..Nant-1, FEED_ID=0, BEAM_ID=-1, TIME=0, INTERVAL=1e9
    """
    import numpy as np
    nants = int(getattr(uv, 'Nants_telescope', 0) or np.asarray(getattr(uv, 'antenna_positions')).shape[0])
    # Object arrays need dtype=object for dask-ms
    pol_type = np.empty((nants, 2), dtype=object)
    pol_type[:, 0] = 'X'
    pol_type[:, 1] = 'Y'
    # receptor angles in radians: X=0, Y=pi/2
    rec_ang = np.zeros((nants, 2), dtype=np.float64)
    rec_ang[:, 1] = np.pi / 2.0
    # 2x2 identity PolResponse per antenna (complex64)
    pol_resp = np.zeros((nants, 2, 2), dtype=np.complex64)
    pol_resp[:, 0, 0] = 1.0 + 0.0j
    pol_resp[:, 1, 1] = 1.0 + 0.0j
    ant_id = np.arange(nants, dtype=np.int32)
    sw = np.full(nants, -1, dtype=np.int32)
    feed_id = np.zeros(nants, dtype=np.int32)
    beam_id = np.full(nants, -1, dtype=np.int32)
    num_rec = np.full(nants, 2, dtype=np.int32)
    time = np.zeros(nants, dtype=np.float64)
    interval = np.full(nants, 1e9, dtype=np.float64)

    vars_feed = {
        'ANTENNA_ID': (('row',), da.from_array(ant_id, chunks=(nants,))),
        'SPECTRAL_WINDOW_ID': (('row',), da.from_array(sw, chunks=(nants,))),
        'FEED_ID': (('row',), da.from_array(feed_id, chunks=(nants,))),
        'BEAM_ID': (('row',), da.from_array(beam_id, chunks=(nants,))),
        'NUM_RECEPTORS': (('row',), da.from_array(num_rec, chunks=(nants,))),
        'POLARIZATION_TYPE': (('row', 'receptor'), da.from_array(pol_type, chunks=(nants, 2))),
        'RECEPTOR_ANGLE': (('row', 'receptor'), da.from_array(rec_ang, chunks=(nants, 2))),
        'POL_RESPONSE': (('row', 'rec_x', 'rec_y'), da.from_array(pol_resp, chunks=(nants, 2, 2))),
        'TIME': (('row',), da.from_array(time, chunks=(nants,))),
        'INTERVAL': (('row',), da.from_array(interval, chunks=(nants,))),
    }
    coords = {
        'row': (('row',), da.arange(nants, chunks=(nants,))),
        'receptor': (('receptor',), da.arange(2, chunks=(2,))),
        'rec_x': (('rec_x',), da.arange(2, chunks=(2,))),
        'rec_y': (('rec_y',), da.arange(2, chunks=(2,))),
    }
    return DMSDataset(vars_feed, coords=coords, attrs={})


def _build_field_dataset(
        phase_ra: "u.Quantity",
        phase_dec: "u.Quantity",
        *,
        time_sec: float = 0.0) -> "DMSDataset":
    import numpy as np
    ra = float(phase_ra.to_value())
    dec = float(phase_dec.to_value())
    # Per-row shape (NUM_POLY+1, 2). For constant (NUM_POLY=0) -> (1,2)
    phase_dir = np.array([[ra, dec]], dtype=np.float64)
    vars_field = {
        'NAME': (('row',), da.from_array(np.array(['field0'], dtype=object), chunks=(1,))),
        'NUM_POLY': (('row',), da.from_array(np.array([0], dtype=np.int32), chunks=(1,))),
        'PHASE_DIR': (('num_poly', 'loc'), da.from_array(phase_dir, chunks=(1, 2))),
        'DELAY_DIR': (('num_poly', 'loc'), da.from_array(phase_dir, chunks=(1, 2))),
        'REFERENCE_DIR': (('num_poly', 'loc'), da.from_array(phase_dir, chunks=(1, 2))),
        'TIME': (('row',), da.from_array(np.array([float(time_sec)], dtype=np.float64), chunks=(1,))),
    }
    coords = {
        'num_poly': (('num_poly',), da.arange(1, chunks=(1,))),
        'loc': (('loc',), da.arange(2, chunks=(2,))),
    }
    return DMSDataset(vars_field, coords=coords, attrs={})


def _build_field_dataset_multi(phase_ra_list: List["u.Quantity"], phase_dec_list: List["u.Quantity"], time_list_sec: Optional[List[float]] = None) -> "DMSDataset":
    import numpy as np
    n = int(len(phase_ra_list))
    if n == 0:
        # Fallback to single dummy field
        return _build_field_dataset(0.0 * u.rad, 0.0 * u.rad)
    # Build PHASE/DELAY/REFERENCE_DIR with shape (row, num_poly=1, loc=2)
    phase_dir = np.zeros((n, 1, 2), dtype=np.float64)
    for i, (ra, dec) in enumerate(zip(phase_ra_list, phase_dec_list)):
        phase_dir[i, 0, 0] = float(ra.to_value())
        phase_dir[i, 0, 1] = float(dec.to_value())
    names = np.array([f'field{i}' for i in range(n)], dtype=object)
    if time_list_sec is None or len(time_list_sec) != n:
        time_arr = np.zeros(n, dtype=np.float64)
    else:
        time_arr = np.array([float(t) for t in time_list_sec], dtype=np.float64)
    vars_field = {
        'NAME': (('row',), da.from_array(names, chunks=(n,))),
        # Constant direction per field → NUM_POLY = 0 (shape is (1,2) = NUM_POLY+1)
        'NUM_POLY': (('row',), da.from_array(np.zeros(n, dtype=np.int32), chunks=(n,))),
        'PHASE_DIR': (('row', 'num_poly', 'loc'), da.from_array(phase_dir, chunks=(n, 1, 2))),
        'DELAY_DIR': (('row', 'num_poly', 'loc'), da.from_array(phase_dir, chunks=(n, 1, 2))),
        'REFERENCE_DIR': (('row', 'num_poly', 'loc'), da.from_array(phase_dir, chunks=(n, 1, 2))),
        'TIME': (('row',), da.from_array(time_arr, chunks=(n,))),
    }
    coords = {
        'row': (('row',), da.arange(n, chunks=(n,))),
        'num_poly': (('num_poly',), da.arange(1, chunks=(1,))),
        'loc': (('loc',), da.arange(2, chunks=(2,))),
    }
    return DMSDataset(vars_field, coords=coords, attrs={})


def _build_ddid_dataset() -> "DMSDataset":
    import numpy as np
    vars_dd = {
        'SPECTRAL_WINDOW_ID': (
            ('row',), da.from_array(
                np.array(
                    [0], dtype=np.int32), chunks=(
                    1,))), 'POLARIZATION_ID': (
                        ('row',), da.from_array(
                            np.array(
                                [0], dtype=np.int32), chunks=(
                                    1,))), }
    coords = {'row': (('row',), da.arange(1, chunks=(1,)))}
    return DMSDataset(vars_dd, coords=coords, attrs={})




def _search_vla_calibrator(csv_path: str,
                           pointing: "SkyCoord",
                           radius_deg: float) -> Tuple[Optional[str],
                                                       Optional["SkyCoord"],
                                                       Optional[float]]:
    """Find nearest L-band (20cm) VLA calibrator within radius.

    Expects a CSV with headers including RA_J2000, DEC_J2000, BAND, FLUX_JY,
    J2000_NAME (as in vla_calibrators_parsed.csv).
    Returns (name, SkyCoord, flux_Jy) or (None, None, None) if no match.
    """
    try:
        from astropy.coordinates import SkyCoord
        import astropy.units as u
    except Exception as e:
        logger.warning("Astropy not available for calibrator search: %s", e)
        return None, None, None
    candidates = []
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('BAND') != '20cm':
                    continue
                name = row.get('J2000_NAME') or row.get(
                    'B1950_NAME') or row.get('ALT_NAME')
                ra = row.get('RA_J2000', '')
                dec = row.get('DEC_J2000', '')
                flux_s = row.get('FLUX_JY', '')
                if not name or not ra or not dec or not flux_s:
                    continue
                try:
                    flux = float(flux_s)
                except Exception:
                    continue
                ra_c = ra.lower().replace(
                    'h',
                    ':').replace(
                    'm',
                    ':').replace(
                    's',
                    '')
                dec_c = dec.lower().replace(
                    'd',
                    ':').replace(
                    "'",
                    ':').replace(
                    '"',
                    '')
                try:
                    sc = SkyCoord(
                        ra_c + ' ' + dec_c,
                        unit=(
                            u.hourangle,
                            u.deg),
                        frame='icrs')
                except Exception:
                    continue
                sep = pointing.separation(sc).deg
                if sep <= radius_deg:
                    candidates.append((sep, -flux, name, sc, flux))
    except Exception as e:
        logger.warning("Calibrator catalog read failed: %s", e)
        return None, None, None
    if not candidates:
        return None, None, None
    candidates.sort(key=lambda t: (t[0], t[1]))
    _, _, name, sc, flux = candidates[0]
    return name, sc, flux


def _write_calibrator_model_quick(
        ms_path: str,
        cal_sc: "SkyCoord",
        flux_jy: float) -> None:
    """Write a simple Gaussian primary-beam model for a calibrator into MODEL_DATA.

    - Reads FIELD::PHASE_DIR as pointing center and SPECTRAL_WINDOW::CHAN_FREQ
    - Computes Gaussian PB amplitude at fixed separation over frequency
    - Writes MODEL_DATA in row chunks and initializes CORRECTED_DATA = DATA
    """
    from casacore.tables import table as ctable
    import numpy as np
    import astropy.units as u
    from astropy.coordinates import SkyCoord

    # Read center RA/DEC from FIELD
    with ctable(f"{ms_path}::FIELD") as tf:
        phase_dir = tf.getcol('PHASE_DIR')  # shape (num_poly=1, loc=2, dir=1)
        ra = float(phase_dir[0, 0, 0])
        dec = float(phase_dir[0, 1, 0])
    pt_center = SkyCoord(ra=ra * u.rad, dec=dec * u.rad, frame='icrs')

    # Frequencies (Hz)
    with ctable(f"{ms_path}::SPECTRAL_WINDOW") as ts:
        freqs = ts.getcol('CHAN_FREQ')[0]
    freqs_ghz = freqs / 1e9

    # Fixed separation (radians) at mid-time
    sep = pt_center.separation(cal_sc).to_value(u.rad)
    # Gaussian PB: FWHM = 1.2 * lambda / D (D≈4.7m)
    wl = 0.299792458 / freqs_ghz
    sigma = (1.2 * wl / 4.7) / 2.355
    amp = np.exp(-0.5 * (sep / sigma) ** 2).astype(np.float32)  # (nchan,)

    # Write MODEL_DATA in chunks and initialize CORRECTED_DATA safely
    with ctable(ms_path, readonly=False) as tb:
        data_shape = tb.getcol('DATA').shape  # (npol, nchan, nrow)
        npol, nchan, nrow = data_shape
        if nchan != amp.size:
            raise RuntimeError("Frequency axis size mismatch for MODEL_DATA write")
        blk = 4096
        model_line = (flux_jy * amp.astype(np.complex64))  # (nchan,)
        for start in range(0, nrow, blk):
            end = min(start + blk, nrow)
            model = model_line[None, :, None]
            model = np.broadcast_to(model, (npol, nchan, end - start)).copy()
            tb.putcolslice('MODEL_DATA', model, blc=[0, 0, start], trc=[npol - 1, nchan - 1, end - 1])
        # Initialize CORRECTED_DATA as a copy of DATA (best-effort)
        try:
            tb.putcol('CORRECTED_DATA', tb.getcol('DATA'))
        except Exception:
            pass


def _write_calibrator_model_with_ft(
        ms_path: str,
        cal_sc: "SkyCoord",
        flux_jy: float,
        *,
        reffreq_hz: float = 1.4e9,
        spectrum: Optional[dict] = None) -> None:
    """Write a physically-correct complex point-source model using CASA ft.

    - Builds a component list with a single point component at cal_sc with flux_jy.
    - Uses casatasks.ft to Fourier transform the component list into MODEL_DATA.
    - Initializes CORRECTED_DATA as a copy of DATA.
    """
    try:
        from casatools import componentlist as cltool
        from casatasks import ft
        import casacore.tables as tb
    except Exception as e:
        raise RuntimeError(f"CASA tools not available for ft model write: {e}")

    comp_path = os.path.join(os.path.dirname(ms_path), 'cal_component.cl')
    # Create component list
    cl = cltool()
    # Build direction string in J2000
    ra_hms = cal_sc.ra.to_string(unit=u.hour, sep=':', precision=9)
    dec_dms = cal_sc.dec.to_string(
        unit=u.deg, sep=':', precision=9, alwayssign=True)
    dir_str = f"J2000 {ra_hms} {dec_dms}"
    cl.addcomponent(dir=dir_str,
                    flux=float(flux_jy), fluxunit='Jy',
                    freq=f"{reffreq_hz}Hz",
                    shape='point')
    # Optional: spectral index
    if spectrum and 'index' in spectrum and 'reffreq' in spectrum:
        try:
            cl.setspectrum(
                which=0, type='spectral index', index=[
                    float(
                        spectrum['index'])], reffreq=str(
                    spectrum['reffreq']))
        except Exception:
            pass
    cl.rename(comp_path)
    cl.close()

    # Ensure imaging columns exist before writing MODEL_DATA
    try:
        addImagingColumns(ms_path)
    except Exception:
        pass

    # Fourier transform component into MODEL_DATA
    ft(vis=ms_path, complist=comp_path, usescratch=True)

    # Initialize CORRECTED_DATA if present
    try:
        with tb.table(ms_path, readonly=False) as t:
            if 'CORRECTED_DATA' in t.colnames():
                t.putcol('CORRECTED_DATA', t.getcol('DATA'))
    except Exception:
        pass


def _parse_timestamp_from_filename(filename: str) -> Optional[Time]:
    base = os.path.splitext(filename)[0]
    if "_sb" not in base:
        return None
    ts = base.split("_sb", 1)[0]
    # Expect ISO-like YYYY-MM-DDTHH:MM:SS
    try:
        return Time(ts)
    except Exception:
        return None


def _extract_subband_code(filename: str) -> Optional[str]:
    """Return subband code in canonical form 'sbXX' from a filename."""
    base = os.path.splitext(filename)[0]
    if "_sb" not in base:
        return None
    tail = base.rsplit("_sb", 1)[1]
    # Normalize to 'sbXX'
    if tail.startswith('sb'):
        return tail
    return f"sb{tail}"


def find_subband_groups(
    input_dir: str,
    start_time: str,
    end_time: str,
    *,
    spw: Optional[Sequence[str]] = None,
    same_timestamp_tolerance_s: float = 30.0,
) -> List[List[str]]:
    """Identify complete subband groups within a time window using ±30 s tolerance.

    Returns a list of groups; each group is a list of 16 filepaths ordered by sbXX.
    Incomplete groups are skipped.
    """
    if spw is None:
        spw = [f"sb{idx:02d}" for idx in range(16)]

    tmin = Time(start_time)
    tmax = Time(end_time)

    # Gather candidate files
    candidates: List[Tuple[str, Time]] = []
    for path in glob.glob(os.path.join(input_dir, "*_sb??.hdf5")):
        fname = os.path.basename(path)
        ts = _parse_timestamp_from_filename(fname)
        if ts is None:
            continue
        if not (tmin <= ts <= tmax):
            continue
        code = _extract_subband_code(fname) or ""
        if code not in spw:
            continue
        candidates.append((path, ts))

    if not candidates:
        logger.info(
            "No subband files found in %s between %s and %s",
            input_dir,
            start_time,
            end_time)
        return []

    # Group by timestamp closeness (±tolerance)
    candidates.sort(key=lambda it: it[1].unix)
    times_sec = np.array([ts.unix for _, ts in candidates], dtype=float)
    files = np.array([p for p, _ in candidates])

    groups: List[List[str]] = []
    used = np.zeros(len(times_sec), dtype=bool)
    atol = same_timestamp_tolerance_s

    for i in range(len(times_sec)):
        if used[i]:
            continue
        # Close in time to times[i]
        close = np.abs(times_sec - times_sec[i]) <= atol
        idxs = np.where(close & (~used))[0]
        if idxs.size == 0:
            continue
        # Select matching SPWs and order by sbXX suffix
        selected = [files[j] for j in idxs]
        pairs = [(p, _extract_subband_code(os.path.basename(p)) or "")
                 for p in selected]
        # Keep only desired spw set
        pairs = [(p, s) for (p, s) in pairs if s in spw]
        if len(pairs) != len(spw):
            continue
        pairs.sort(key=lambda ps: ps[1])
        groups.append([p for p, _ in pairs])
        used[idxs] = True

    return groups


def _load_and_merge_subbands(file_list: Sequence[str]) -> UVData:
    """Read a list of UVH5 subband files and merge along frequency (ascending)."""
    uv = UVData()
    first = True
    acc: List[UVData] = []
    for i, path in enumerate(file_list):
        t_read0 = time.perf_counter()
        logger.info(
            "Reading subband %d/%d: %s",
            i + 1,
            len(file_list),
            os.path.basename(path))
        tmp = UVData()
        tmp.read(
            path,
            file_type="uvh5",
            run_check=False,
            run_check_acceptability=False,
            strict_uvw_antpos_check=False,
            check_extra=False,
        )
        logger.info(
            "Read subband %d in %.2fs (Nblts=%s, Nfreqs=%s, Npols=%s)",
            i +
            1,
            time.perf_counter() -
            t_read0,
            tmp.Nblts,
            tmp.Nfreqs,
            tmp.Npols)
        tmp.uvw_array = tmp.uvw_array.astype(np.float64)
        if first:
            uv = tmp
            first = False
        else:
            acc.append(tmp)

    if acc:
        try:
            t_cat0 = time.perf_counter()
            uv.fast_concat(
                acc, axis="freq", inplace=True,
                run_check=False, check_extra=False,
                run_check_acceptability=False, strict_uvw_antpos_check=False,
                ignore_name=True,
            )
            logger.info(
                "Concatenated %d subbands in %.2fs",
                len(acc) + 1,
                time.perf_counter() - t_cat0)
        except Exception as e:
            logger.warning(
                "fast_concat across subbands failed (%s). Proceeding with first subband only for this quick run.",
                e,
            )

    # Ensure ascending frequency order
    try:
        uv.reorder_freqs(channel_order="freq", run_check=False)
    except Exception:
        pass

    # CASA works more smoothly with a known telescope name
    try:
        uv.telescope_name = "CARMA"
    except Exception:
        pass

    # Rename antenna names for clarity if needed
    try:
        names = list(getattr(uv, "antenna_names", []))
        if names and not all(str(n).startswith("pad") for n in names):
            uv.antenna_names = [f"pad{str(n)}" if not str(
                n).startswith("pad") else str(n) for n in names]
    except Exception:
        pass

    return uv


def _downsample_frequency(uv: "UVData", factor: int) -> None:
    """Downsample frequency axis in-place by an integer factor.

    Updates DATA/FLAG/NSAMPLE, freq_array, channel_width, and Nfreqs.
    """
    if factor <= 1:
        return
    nchan = int(uv.Nfreqs)
    if nchan % factor != 0:
        raise ValueError(f"Nfreqs ({nchan}) not divisible by ds-freq={factor}")
    # Determine array rank: pyuvdata usually uses (Nblts, Nspws, Nfreqs, Npols),
    # but some sources may squeeze Nspws when it's 1 to (Nblts, Nfreqs, Npols).

    def _freq_reduce(arr, reduce_fn):
        if arr.ndim == 4:
            nb, ns, nf, npol = arr.shape
            new_nf = nf // factor
            return reduce_fn(arr.reshape(nb, ns, new_nf, factor, npol), axis=3)
        elif arr.ndim == 3:
            nb, nf, npol = arr.shape
            new_nf = nf // factor
            return reduce_fn(arr.reshape(nb, new_nf, factor, npol), axis=2)
        else:
            raise ValueError(
                f"Unsupported array rank for freq DS: {arr.shape}")

    data = _freq_reduce(uv.data_array, np.mean)
    flag = _freq_reduce(uv.flag_array, np.any)
    try:
        nsamp = _freq_reduce(uv.nsample_array, np.sum)
    except Exception:
        nsamp = None

    uv.data_array = data.astype(uv.data_array.dtype, copy=False)
    uv.flag_array = flag.astype(bool, copy=False)
    if nsamp is not None:
        uv.nsample_array = nsamp.astype(
            getattr(
                uv,
                'nsample_array',
                nsamp).dtype,
            copy=False)

    # Frequencies and widths
    freq = np.asarray(uv.freq_array).reshape(-1)
    new_nf = nchan // factor
    freq_ds = freq.reshape(new_nf, factor).mean(axis=1)
    uv.freq_array = freq_ds.reshape(1, -1)
    try:
        cw = np.asarray(uv.channel_width).reshape(-1)
        # Use sum of widths to preserve total BW sign
        cw_ds = cw.reshape(new_nf, factor).sum(axis=1)
        uv.channel_width = cw_ds.reshape(1, -1)
    except Exception:
        pass
    uv.Nfreqs = int(uv.freq_array.size)


def _downsample_time(uv: "UVData", factor: int) -> None:
    """Downsample time axis in-place by an integer factor.

    Groups adjacent time samples; averages DATA/UVW/TIME/LST, ORs FLAG, sums NSAMPLE and integration_time.
    Robust to arbitrary row ordering by grouping rows by unique times and sorting baselines consistently.
    """
    if factor <= 1:
        return
    # Unique times and counts
    utime = np.unique(uv.time_array)
    nt = utime.size
    if nt % factor != 0:
        raise ValueError(f"Ntimes ({nt}) not divisible by ds-time={factor}")
    # Build per-time index lists
    idx_per_time = [np.where(uv.time_array == t)[0] for t in utime]
    # Establish baseline order from first time
    i0 = idx_per_time[0]
    base_pairs = list(
        zip(uv.ant_1_array[i0].tolist(), uv.ant_2_array[i0].tolist()))
    # Build (time, baseline) index matrix with consistent ordering
    nbls = len(base_pairs)
    idx_mat = np.empty((nt, nbls), dtype=int)
    for ti, inds in enumerate(idx_per_time):
        pairs = list(
            zip(uv.ant_1_array[inds].tolist(), uv.ant_2_array[inds].tolist()))
        order = {p: i for i, p in enumerate(pairs)}
        try:
            idx_mat[ti, :] = [inds[order[p]] for p in base_pairs]
        except Exception:
            raise RuntimeError(
                "Baseline set/order inconsistent across times; cannot downsample time robustly")

    # Prepare outputs
    nb_out = nbls * (nt // factor)
    data_out = np.empty(
        (nb_out,
         uv.Nspws,
         uv.Nfreqs,
         uv.Npols),
        dtype=uv.data_array.dtype)
    flag_out = np.empty_like(data_out, dtype=bool)
    uvw_out = np.empty((nb_out, 3), dtype=float)
    time_out = np.empty((nb_out,), dtype=float)
    lst_out = np.empty((nb_out,), dtype=float)
    try:
        nsamp_out = np.empty_like(data_out, dtype=uv.nsample_array.dtype)
        have_ns = True
    except Exception:
        nsamp_out = None
        have_ns = False
    try:
        itime = np.asarray(uv.integration_time, dtype=float)
        have_it = True
    except Exception:
        itime = None
        have_it = False

    # Also prepare ant arrays (repeat base_pairs per output time)
    a1_out = np.repeat(
        np.array([p[0] for p in base_pairs], dtype=uv.ant_1_array.dtype), nt // factor)
    a2_out = np.repeat(
        np.array([p[1] for p in base_pairs], dtype=uv.ant_2_array.dtype), nt // factor)

    # Process groups
    out_row = 0
    for g in range(nt // factor):
        rows = idx_mat[g * factor: (g + 1) * factor, :].reshape(-1)
        # DATA/FLAG/NSAMPLE
        block = uv.data_array[rows, ...].reshape(
            factor, nbls, uv.Nspws, uv.Nfreqs, uv.Npols)
        data_avg = block.mean(axis=0)
        flag_block = uv.flag_array[rows, ...].reshape(
            factor, nbls, uv.Nspws, uv.Nfreqs, uv.Npols)
        flag_or = flag_block.any(axis=0)
        if have_ns:
            ns_block = uv.nsample_array[rows, ...].reshape(
                factor, nbls, uv.Nspws, uv.Nfreqs, uv.Npols)
            ns_sum = ns_block.sum(axis=0)
        # UVW/TIME/LST
        uvw_block = uv.uvw_array[rows, :].reshape(factor, nbls, 3)
        uvw_avg = uvw_block.mean(axis=0)
        t_block = uv.time_array[rows].reshape(factor, nbls)
        t_avg = t_block.mean(axis=0)
        l_block = uv.lst_array[rows].reshape(factor, nbls)
        l_avg = l_block.mean(axis=0)
        if have_it:
            it_block = itime[rows].reshape(factor, nbls)
            it_sum = it_block.sum(axis=0)

        # Write into outputs
        sl = slice(out_row, out_row + nbls)
        data_out[sl, ...] = data_avg
        flag_out[sl, ...] = flag_or
        if have_ns:
            nsamp_out[sl, ...] = ns_sum
        uvw_out[sl, :] = uvw_avg
        time_out[sl] = t_avg
        lst_out[sl] = l_avg
        out_row += nbls

    # Assign
    uv.data_array = data_out
    uv.flag_array = flag_out
    if have_ns:
        uv.nsample_array = nsamp_out
    uv.uvw_array = uvw_out
    uv.time_array = time_out
    uv.lst_array = lst_out
    if have_it:
        uv.integration_time = np.repeat((itime[:nbls * factor].sum() / (
            nbls * factor)), nb_out) if np.ndim(itime) == 0 else it_sum.repeat(nb_out // nbls)
    # Ant arrays
    uv.ant_1_array = np.tile(
        np.array([p[0] for p in base_pairs], dtype=uv.ant_1_array.dtype), nt // factor)
    uv.ant_2_array = np.tile(
        np.array([p[1] for p in base_pairs], dtype=uv.ant_2_array.dtype), nt // factor)


def _ensure_phasecenter_arrays(uv: UVData) -> None:
    """Ensure per-row phase center arrays exist on the UVData object."""
    n = uv.Nblts
    # Allocate if missing (pyuvdata normally provides these after phasing)
    if getattr(uv, 'phase_center_app_ra', None) is None:
        try:
            uv.phase_center_app_ra = np.zeros(n, dtype=float)
            uv.phase_center_app_dec = np.zeros(n, dtype=float)
            uv.phase_center_frame_pa = np.zeros(n, dtype=float)
        except Exception:
            pass
    if getattr(uv, 'phase_center_id_array', None) is None:
        try:
            uv.phase_center_id_array = np.zeros(n, dtype=int)
        except Exception:
            pass


def set_per_time_phase_centers(
        uv: UVData,
        pt_dec: u.Quantity,
        *,
        field_name: Optional[str] = None) -> None:
    """Assign per-time phase centers and recompute UVW for each time block.

    Mirrors the behavior in the dsa110-hi pipeline's set_phases, adapted to our
    environment and pyuvdata 3.2.4 API.
    """
    _ensure_phasecenter_arrays(uv)

    # Unique times and inverse mapping to per-row selections
    utime, uind, uinvert = np.unique(
        uv.time_array, return_index=True, return_inverse=True)

    # Build field name template
    if field_name is None:
        fmt = 'drift_ra{}'
    else:
        fmt = field_name + '_drift_ra{}'

    # Telescope metadata used by uvutils (prefer UVData.telescope in pyuvdata>=3.2.4)
    tel_latlonalt = getattr(uv, 'telescope_location_lat_lon_alt', None)
    if tel_latlonalt is None and hasattr(uv, 'telescope'):
        tel_latlonalt = getattr(uv.telescope, 'location_lat_lon_alt', None)
    tel_frame = getattr(uv, '_telescope_location', None)
    tel_frame = getattr(tel_frame, 'frame', None)

    # Antenna metadata (positions & numbers)
    ant_pos = getattr(uv, 'antenna_positions', None)
    if ant_pos is None and hasattr(uv, 'telescope'):
        ant_pos = getattr(uv.telescope, 'antenna_positions', None)
    ant_nums = getattr(uv, 'antenna_numbers', None)
    if ant_nums is None and hasattr(uv, 'telescope'):
        ant_nums = getattr(uv.telescope, 'antenna_numbers', None)
    ant_pos = np.asarray(ant_pos) if ant_pos is not None else None
    ant_nums = np.asarray(ant_nums) if ant_nums is not None else None

    # Vectorized fast path: compute apparent coords per unique time, map to rows, compute UVW once
    mjd_unique = Time(utime, format='jd').mjd.astype(float)
    ra_icrs_list = []
    dec_icrs_list = []
    for mjd in mjd_unique:
        ra_icrs, dec_icrs = get_meridian_coords(pt_dec, mjd)
        ra_icrs_list.append(ra_icrs)
        dec_icrs_list.append(dec_icrs)

    app_ra_unique = np.zeros(len(utime), dtype=float)
    app_dec_unique = np.zeros(len(utime), dtype=float)
    frame_pa_unique = np.zeros(len(utime), dtype=float)

    for i in range(len(utime)):
        sel = (uinvert == i)
        if not np.any(sel):
            continue
        try:
            ra0 = ra_icrs_list[i].to_value(u.rad)
            dec0 = dec_icrs_list[i].to_value(u.rad)
            new_app_ra, new_app_dec = uvutils.calc_app_coords(
                ra0,
                dec0,
                coord_frame='icrs',
                coord_epoch=2000.0,
                coord_times=None,
                coord_type='sidereal',
                time_array=uv.time_array[sel],
                lst_array=uv.lst_array[sel],
                pm_ra=None,
                pm_dec=None,
                vrad=None,
                dist=None,
                telescope_loc=tel_latlonalt,
                telescope_frame=tel_frame,
            )
            new_frame_pa = uvutils.calc_frame_pos_angle(
                uv.time_array[sel], new_app_ra, new_app_dec,
                tel_latlonalt,
                'icrs',
                ref_epoch=2000.0,
                telescope_frame=tel_frame,
            )
            app_ra_unique[i] = float(new_app_ra[0])
            app_dec_unique[i] = float(new_app_dec[0])
            frame_pa_unique[i] = float(new_frame_pa[0])
        except Exception:
            app_ra_unique[i] = float(ra_icrs_list[i].to_value(u.rad))
            app_dec_unique[i] = float(dec_icrs_list[i].to_value(u.rad))
            frame_pa_unique[i] = 0.0

    app_ra_all = app_ra_unique[uinvert]
    app_dec_all = app_dec_unique[uinvert]
    frame_pa_all = frame_pa_unique[uinvert]
    try:
        uvw_all = _calc_uvw_fast(
            app_ra=app_ra_all,
            app_dec=app_dec_all,
            frame_pa=frame_pa_all,
            lst_array=uv.lst_array,
            antenna_positions=ant_pos,
            antenna_numbers=ant_nums,
            ant_1_array=uv.ant_1_array,
            ant_2_array=uv.ant_2_array,
            telescope_lat=tel_latlonalt[0],
            telescope_lon=tel_latlonalt[1],
        )
        uv.uvw_array[:, :] = uvw_all
    except Exception as e:
        logger.warning("Vectorized UVW failed (%s); falling back to block-wise compute", e)
        for i in range(len(utime)):
            sel = (uinvert == i)
            if not np.any(sel):
                continue
            try:
                uvw = _calc_uvw_fast(
                    app_ra=app_ra_all[sel],
                    app_dec=app_dec_all[sel],
                    frame_pa=frame_pa_all[sel],
                    lst_array=uv.lst_array[sel],
                    antenna_positions=ant_pos,
                    antenna_numbers=ant_nums,
                    ant_1_array=uv.ant_1_array[sel],
                    ant_2_array=uv.ant_2_array[sel],
                    telescope_lat=tel_latlonalt[0],
                    telescope_lon=tel_latlonalt[1],
                )
                uv.uvw_array[sel, :] = uvw
            except Exception:
                row_idx = np.where(sel)[0]
                blen = ant_pos[uv.ant_2_array[sel], :] - ant_pos[uv.ant_1_array[sel], :]
                times_mjd = Time(uv.time_array[sel], format='jd').mjd.astype(float)
                uvw_rows = calc_uvw_blt(
                    blen,
                    times_mjd,
                    'J2000',
                    u.Quantity(app_ra_all[sel], u.rad),
                    u.Quantity(app_dec_all[sel], u.rad),
                    obs='OVRO_MMA',
                )
                uv.uvw_array[row_idx, :] = uvw_rows

    # Per-row phase center metadata
    try:
        uv.phase_center_app_ra[:] = app_ra_all
        uv.phase_center_app_dec[:] = app_dec_all
        uv.phase_center_frame_pa[:] = frame_pa_all
    except Exception:
        pass

    # Create phase center catalog entries and set IDs
    pc_ids = np.zeros(len(utime), dtype=int)
    for i in range(len(utime)):
        try:
            ra_str = ra_icrs_list[i].to_string(unit=u.hour, sep=':', precision=3, pad=True)
        except Exception:
            ra_str = 'RA'
        try:
            pc_ids[i] = uv._add_phase_center(
                cat_name=f"{fmt.format(ra_str)}_t{i:03d}",
                cat_type='sidereal',
                cat_lon=ra_icrs_list[i].to_value(u.rad),
                cat_lat=dec_icrs_list[i].to_value(u.rad),
                cat_frame='icrs',
                force_update=False,
            )
        except Exception:
            pc_ids[i] = i
    try:
        uv.phase_center_id_array[:] = pc_ids[uinvert]
    except Exception:
        pass

    # Ensure all phase-center metadata use an equatorial frame and epoch
    try:
        uv.phase_center_frame = 'icrs'
        uv.phase_center_epoch = 2000.0
    except Exception:
        pass
    try:
        if hasattr(uv, 'phase_center_catalog') and uv.phase_center_catalog:
            for pc_id, entry in uv.phase_center_catalog.items():
                entry['cat_frame'] = 'icrs'
                entry['cat_epoch'] = 2000.0
                entry.setdefault('cat_name', f'phase{pc_id}')
    except Exception:
        pass

    # Drop any unused phase centers (e.g., initial 'unprojected' entries) to
    # avoid pyuvdata MS writer errors in SOURCE table writeout.
    try:
        if hasattr(uv, '_clear_unused_phase_centers'):
            uv._clear_unused_phase_centers()
    except Exception:
        pass


def convert_subband_groups_to_ms(
    input_dir: str,
    output_dir: str,
    start_time: str,
    end_time: str,
    *,
    antenna_list: Optional[List[str]] = None,
    duration: Optional[float] = None,
    refmjd: Optional[float] = None,
    flux: Optional[float] = None,
    fringestop: bool = True,
    phase_ra: Optional[u.Quantity] = None,
    phase_dec: Optional[u.Quantity] = None,
    # Optional calibrator MS (MODEL_DATA) generation via catalog search
    cal_catalog: Optional[str] = None,
    cal_search_radius_deg: float = 0.0,
    cal_output_dir: Optional[str] = None,
    checkpoint_dir: Optional[str] = None,
    scratch_dir: Optional[str] = None,
    # Default to monolithic pyuvdata.write_ms so each integration can map
    # to its own FIELD via per-time phase centers.
    direct_ms: bool = False,
    stage_to_tmpfs: bool = True,
    tmpfs_path: str = "/dev/shm",
    parallel_subband: bool = False,
    max_workers: int = 4,
    dask_write: bool = False,
    field_per_integration: bool = False,
    dask_failfast: bool = False,
    # dask-ms chunk tuning
    daskms_row_chunks: Optional[int] = None,
    daskms_cube_row_chunks: Optional[int] = None,
    # QA quicklooks (shadeMS)
    qa_shadems: bool = False,
    qa_shadems_resid: bool = False,
    qa_shadems_max: int = 4,
    qa_shadems_timeout: int = 600,
    qa_state_dir: Optional[str] = None,
    # QA ragavi (HTML export)
    qa_ragavi_vis: bool = False,
    qa_ragavi_timeout: int = 600,
) -> None:
    """Convert all complete subband groups in `input_dir` to MS in `output_dir`.

    Behavior mirrors dsa110-hi's pipeline_msmaker:
    - 30 s grouping tolerance
    - merge subbands along frequency
    - direct MS write (single SPW)
    - phasing/UVW update via our stable helpers
    """
    os.makedirs(output_dir, exist_ok=True)
    # Allow quick tests with fewer subbands by inferring expected set from available files
    # Default to canonical 16 if not obvious
    expected = [f"sb{idx:02d}" for idx in range(16)]
    try:
        # Probe directory for present sb codes
        present = set()
        for p in glob.glob(os.path.join(input_dir, "*_sb??.hdf5")):
            code = _extract_subband_code(os.path.basename(p))
            if code:
                present.add(code)
        if 0 < len(present) < 16:
            expected = sorted(present)
    except Exception:
        pass
    groups = find_subband_groups(input_dir, start_time, end_time, spw=expected)
    if not groups:
        logger.info("No complete subband groups to convert")
        return

    for file_list in groups:
        first_file = os.path.basename(file_list[0])
        base = os.path.splitext(first_file)[0].split("_sb")[0]
        msname = os.path.join(output_dir, base)
        logger.info("Converting group %s → %s.ms", base, msname)

        # If an MS already exists for this group and we're primarily generating a cal MS,
        # skip the heavy rebuild and reuse existing MS + field center
        reuse_existing_ms = False  # Force fresh conversion for testing
        skip_build = bool(reuse_existing_ms and os.path.exists(msname + '.ms'))
        if skip_build:
            logger.info("Base MS exists; skipping rewrite: %s.ms", msname)
            try:
                from casacore.tables import table as ctable
                with ctable(msname + '.ms::FIELD') as tf:
                    phase_dir = tf.getcol('PHASE_DIR')
                    phase_ra_use = float(phase_dir[0, 0, 0]) * u.rad
                    phase_dec_use = float(phase_dir[0, 1, 0]) * u.rad
            except Exception:
                # Fallback: compute from time if needed
                phase_ra_use = None
                phase_dec_use = None
            pt_dec = None
        else:
            # Load & merge subbands
            t0 = time.perf_counter()
            uv = _load_and_merge_subbands(file_list)
            logger.info(
                "Timing: load+merge took %.2fs",
                time.perf_counter() - t0)

            # Determine phase center (meridian at pointing dec) if not provided
            pt_dec = uv.extra_keywords.get("phase_center_dec", 0.0) * u.rad
            if phase_ra is None or phase_dec is None:
                phase_time = Time(float(np.mean(uv.time_array)), format="jd")
                phase_ra_use, phase_dec_use = get_meridian_coords(
                    pt_dec, phase_time.mjd)
            else:
                phase_ra_use, phase_dec_use = phase_ra, phase_dec

            # Antenna geometry metadata + per-time UVW
            t1 = time.perf_counter()
            set_antenna_positions(uv)
            _ensure_antenna_diameters(uv)
            try:
                set_per_time_phase_centers(uv, pt_dec)
            except Exception as e:
                logger.warning(
                    "Per-time phase center assignment failed: %s; continuing", e)
            logger.info(
                "Timing: phase/uvw update took %.2fs",
                time.perf_counter() - t1)

        # Optional downsampling before writing (env knobs for quick testing)
        if not skip_build:
            try:
                t2f = time.perf_counter()
                dsf = int(os.getenv('DS_FREQ', '1'))
                _downsample_frequency(uv, dsf)
                if dsf > 1:
                    logger.info(
                        "Timing: freq downsample (x%d) took %.2fs",
                        dsf,
                        time.perf_counter() - t2f)
            except Exception as e:
                logger.warning("Freq downsample skipped: %s", e)
            try:
                t2t = time.perf_counter()
                dst = int(os.getenv('DS_TIME', '1'))
                _downsample_time(uv, dst)
                if dst > 1:
                    logger.info(
                        "Timing: time downsample (x%d) took %.2fs",
                        dst,
                        time.perf_counter() - t2t)
            except Exception as e:
                logger.warning("Time downsample skipped: %s", e)

        # Paths
        ms_final_path = f"{msname}.ms"
        if not skip_build:
            # Estimate size for staging decision
            nrows = uv.Nblts
            nchan = uv.Nfreqs
            npols = uv.Npols
            bytes_data = nrows * nchan * npols * 8  # complex64
            est_total = int(bytes_data * 3.0)
            stage_here = False
            stage_dir = None
            try:
                if stage_to_tmpfs and tmpfs_path:
                    usage = shutil.disk_usage(tmpfs_path)
                    if est_total < int(0.8 * usage.free):
                        stage_here = True
                        stage_dir = os.path.join(tmpfs_path, "ms_stage")
                        os.makedirs(stage_dir, exist_ok=True)
                        logger.info(
                            "Staging MS to tmpfs (%s). est=%.2f GB free=%.2f GB",
                            tmpfs_path,
                            est_total / 1e9,
                            usage.free / 1e9,
                        )
                    else:
                        logger.info(
                            "Not staging to tmpfs: est=%.2f GB exceeds free=%.2f GB (80%% threshold)",
                            est_total / 1e9,
                            usage.free / 1e9,
                        )
                # If tmpfs not selected, stage to scratch_dir when provided
                if not stage_here and scratch_dir:
                    try:
                        os.makedirs(scratch_dir, exist_ok=True)
                    except Exception:
                        pass
                    stage_here = True
                    stage_dir = scratch_dir
                    logger.info(
                        "Staging MS to scratch (%s). est=%.2f GB",
                        scratch_dir,
                        est_total / 1e9,
                    )
            except Exception:
                stage_here = False

            ms_stage_path = os.path.join(stage_dir, os.path.basename(
                ms_final_path)) if stage_here else ms_final_path
            if os.path.exists(ms_stage_path):
                shutil.rmtree(ms_stage_path, ignore_errors=True)

        if not skip_build:
            # Defensive: coerce frames/epoch before export
            try:
                uv.phase_center_frame = 'icrs'
                uv.phase_center_epoch = 2000.0
                if hasattr(
                        uv,
                        'phase_center_catalog') and uv.phase_center_catalog:
                    for pc_id, entry in uv.phase_center_catalog.items():
                        entry['cat_frame'] = 'icrs'
                        entry['cat_epoch'] = 2000.0
                        entry.setdefault('cat_name', f'phase{pc_id}')
            except Exception:
                pass

        # Writer selection
        writer_type = None
        # If field-per-integration requested, prefer dask-ms writer
        if field_per_integration and not dask_write:
            dask_write = True

        if not skip_build and dask_write and HAVE_DASKMS:
            logger.info("dask-ms write -> %s", ms_stage_path)
            try:
                t3 = time.perf_counter()
                _write_ms_with_daskms(
                    uv,
                    ms_stage_path,
                    row_chunks=daskms_row_chunks,
                    cube_row_chunks=daskms_cube_row_chunks,
                    field_per_integration=bool(field_per_integration))
                logger.info(
                    "Timing: dask-ms write took %.2fs",
                    time.perf_counter() - t3)
                writer_type = 'dask-ms'
            except Exception as e:
                if dask_failfast:
                    logger.error("dask-ms write failed (failfast): %s", e)
                    raise
                else:
                    logger.error(
                        "dask-ms write failed: %s. Falling back to direct path.", e)
                    # Fall through to other writers
                    dask_write = False
        elif not skip_build and dask_write and not HAVE_DASKMS:
            msg = "dask-ms not available in this environment"
            if dask_failfast:
                logger.error("%s (failfast)", msg)
                raise RuntimeError(msg)
            else:
                logger.warning("%s; falling back to direct path", msg)
                dask_write = False
                field_per_integration = False

        # If a writer already succeeded, skip further writers
        wrote_already = writer_type is not None

        if not skip_build and not wrote_already and not dask_write and parallel_subband:
            logger.info(
                "Parallel per-subband write enabled (workers=%d)",
                max_workers)
            # Write per-subband MS parts in parallel and concat
            # Stage into tmpfs if enabled
            part_base = os.path.join(
                stage_dir or (
                    scratch_dir or output_dir),
                os.path.basename(msname))
            os.makedirs(part_base, exist_ok=True)
            # Submit parallel jobs
            # Use processes, not threads: casatools/casacore are not
            # thread-safe for concurrent Simulator usage
            from concurrent.futures import ProcessPoolExecutor, as_completed
            futures = []
            with ProcessPoolExecutor(max_workers=max_workers) as ex:
                for idx, sb in enumerate(sorted(file_list)):
                    part_out = os.path.join(
                        part_base, f"{os.path.basename(msname)}.sb{idx:02d}.ms")
                    futures.append(ex.submit(write_ms_subband, sb, part_out))
                done = 0
                parts = []
                for fu in as_completed(futures):
                    try:
                        parts.append(fu.result())
                        done += 1
                        if done % 4 == 0 or done == len(futures):
                            logger.info(
                                "Per-subband writes completed: %d/%d", done, len(futures))
                    except Exception as e:
                        raise RuntimeError(f"Subband write failed: {e}")
            # Concat parts into staged MS
            try:
                from casatasks import concat as casa_concat
                logger.info(
                    "Concatenating %d parts into %s",
                    len(parts),
                    ms_stage_path)
                casa_concat(
                    vis=sorted(parts),
                    concatvis=ms_stage_path,
                    copypointing=False)
            except Exception as e:
                raise RuntimeError(f"Concat failed: {e}")
            writer_type = 'direct-subband+concat'
        elif not skip_build and not wrote_already and not dask_write and direct_ms:
            logger.info(
                "Direct per-subband writer (sequential) -> %s",
                ms_stage_path)
            # Use sequential direct writer which creates per-subband then
            # concat
            t4 = time.perf_counter()
            write_ms_from_subbands(
                sorted(file_list),
                ms_stage_path,
                scratch_dir=stage_dir or scratch_dir)
            logger.info(
                "Timing: direct per-subband writer took %.2fs",
                time.perf_counter() - t4)
            writer_type = 'direct-subband'
        elif not skip_build and not wrote_already:
            logger.info("Direct pyuvdata.write_ms -> %s", ms_stage_path)
            # Direct pyuvdata write with resilience: fallback to dask-ms or direct-subband
            try:
                t5 = time.perf_counter()
                uv.write_ms(
                    ms_stage_path,
                    clobber=True,
                    run_check=False,
                    check_extra=False,
                    run_check_acceptability=False,
                    strict_uvw_antpos_check=False,
                    check_autos=False,
                    fix_autos=False,
                )
                logger.info(
                    "Timing: pyuvdata write took %.2fs",
                    time.perf_counter() - t5)
                writer_type = 'pyuvdata'
            except Exception as e_py:
                logger.error("pyuvdata.write_ms failed: %s", e_py)
                # Attempt dask-ms writer if available
                if HAVE_DASKMS:
                    try:
                        logger.info("Falling back to dask-ms writer -> %s", ms_stage_path)
                        t3b = time.perf_counter()
                        _write_ms_with_daskms(
                            uv,
                            ms_stage_path,
                            row_chunks=daskms_row_chunks,
                            cube_row_chunks=daskms_cube_row_chunks,
                            field_per_integration=bool(field_per_integration))
                        logger.info(
                            "Timing: dask-ms fallback write took %.2fs",
                            time.perf_counter() - t3b)
                        writer_type = 'dask-ms'
                    except Exception as e_dm:
                        logger.error("dask-ms fallback failed: %s", e_dm)
                # If still not written, fallback to direct subband writer
                if writer_type is None:
                    try:
                        logger.info(
                            "Falling back to direct per-subband writer (sequential) -> %s",
                            ms_stage_path)
                        t4b = time.perf_counter()
                        write_ms_from_subbands(
                            sorted(file_list),
                            ms_stage_path,
                            scratch_dir=stage_dir or scratch_dir)
                        logger.info(
                            "Timing: direct per-subband fallback took %.2fs",
                            time.perf_counter() - t4b)
                        writer_type = 'direct-subband'
                    except Exception as e_ds:
                        raise RuntimeError(
                            f"All writer paths failed (pyuvdata/dask-ms/direct-subband). Last error: {e_ds}")

        # Move staged MS into final destination if needed
        if not skip_build and stage_here and ms_stage_path != ms_final_path:
            try:
                if os.path.exists(ms_final_path):
                    shutil.rmtree(ms_final_path, ignore_errors=True)
                logger.info("Moving staged MS %s -> %s", ms_stage_path, ms_final_path)
                shutil.move(ms_stage_path, ms_final_path)
            except Exception:
                # Fallback to copytree
                logger.info("Copying staged MS %s -> %s (fallback)", ms_stage_path, ms_final_path)
                shutil.copytree(ms_stage_path, ms_final_path)
                shutil.rmtree(ms_stage_path, ignore_errors=True)

        # Ensure imaging columns exist after writing
        if not skip_build:
            try:
                addImagingColumns(ms_final_path)
            except Exception:
                pass

        # Optional: populate MODEL_DATA (unity/beam) when a flux is specified
        if not skip_build and flux is not None and pt_dec is not None:
            try:
                set_model_column(
                    msname,
                    uv,
                    pt_dec,
                    phase_ra_use,
                    phase_dec_use,
                    flux_Jy=flux)
            except Exception as e:
                logger.warning("MODEL_DATA write failed: %s", e)

        logger.info("✓ Wrote %s", ms_final_path)
        try:
            print(
                f"WRITER_TYPE: {writer_type or ('reused' if skip_build else 'unknown')}")
        except Exception:
            pass

        # Optional: produce a separate calibrator-model MS by searching a VLA
        # catalog
        try:
            if cal_catalog and cal_search_radius_deg and cal_search_radius_deg > 0:
                cal_dir = cal_output_dir or output_dir
                os.makedirs(cal_dir, exist_ok=True)

                # Approximate pointing center at mid-time for search
                if phase_ra_use is None or phase_dec_use is None:
                    # Fallback if phase center not available
                    phase_time = Time(
                        float(
                            np.mean(
                                uv.time_array)),
                        format="jd")
                    phase_ra_use, phase_dec_use = get_meridian_coords(
                        pt_dec or 0.0 * u.rad, phase_time.mjd)
                pt_ra_deg = float(phase_ra_use.to_value(u.rad) * 180.0 / np.pi)
                pt_dec_deg = float(
                    phase_dec_use.to_value(
                        u.rad) * 180.0 / np.pi)

                # Read VLA catalog and find nearest calibrator
                cdf = read_vla_parsed_catalog_with_flux(
                    cal_catalog, band='20cm')
                match = nearest_calibrator_within_radius(
                    pt_ra_deg, pt_dec_deg, cdf, cal_search_radius_deg)
                if not match:
                    logger.info(
                        "No calibrator found within %.2f deg of pointing",
                        cal_search_radius_deg)
                else:
                    cal_name, cra_deg, cdec_deg, cflux = match
                    cal_msname = os.path.join(cal_dir, f"{cal_name}_{base}")
                    cal_mspath = cal_msname + ".ms"
                    # Copy base MS and write MODEL_DATA via CASA ft for correct
                    # complex model
                    try:
                        if os.path.exists(cal_mspath):
                            shutil.rmtree(cal_mspath, ignore_errors=True)
                        logger.info(
                            "Creating calibrator MS %s via copy", cal_mspath)
                        shutil.copytree(ms_final_path, cal_mspath)
                        addImagingColumns(cal_mspath)
                        # Flux fallback if missing
                        flux_use = float(cflux) if np.isfinite(cflux) else 8.0
                        write_point_model_with_ft(
                            cal_mspath, cra_deg, cdec_deg, flux_use)
                        logger.info(
                            "✓ Wrote calibrator MS %s (MODEL_DATA for %s, %.2f Jy)",
                            cal_mspath,
                            cal_name,
                            flux_use)
                    except Exception as e:
                        logger.warning(
                            "Calibrator MODEL_DATA write failed: %s", e)
        except Exception as e:
            logger.warning("Calibrator MS generation skipped: %s", e)

        # Optional quicklook QA plots via shadeMS
        if qa_shadems:
            try:
                run_shadems_quicklooks(
                    ms_final_path,
                    state_dir=qa_state_dir,
                    resid=qa_shadems_resid,
                    max_plots=qa_shadems_max,
                    timeout=qa_shadems_timeout,
                )
            except Exception as e:
                logger.warning("shadeMS quicklooks failed or skipped: %s", e)

        # Optional ragavi-vis export (HTML)
        if qa_ragavi_vis:
            try:
                run_ragavi_vis(
                    ms_final_path,
                    state_dir=qa_state_dir,
                    timeout=qa_ragavi_timeout,
                )
            except Exception as e:
                logger.warning("ragavi-vis export failed or skipped: %s", e)


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(
        description="Convert DSA-110 subband UVH5 to MS (HI-compatible defaults)")
    p.add_argument("input_dir")
    p.add_argument("output_dir")
    p.add_argument("start_time", help="YYYY-MM-DD HH:MM:SS")
    p.add_argument("end_time", help="YYYY-MM-DD HH:MM:SS")
    p.add_argument("--flux", type=float)
    p.add_argument("--no-fringestop", action="store_true")
    # Compatibility with streaming converter CLI surface
    p.add_argument("--log-level", default="INFO")
    p.add_argument("--checkpoint-dir")
    p.add_argument("--scratch-dir")
    p.add_argument("--direct-ms", action="store_true")
    # Calibrator search (VLA catalogs)
    p.add_argument(
        "--cal-catalog",
        default=None,
        help="Path to VLA calibrator CSV (e.g., vla_calibrators_parsed.csv)")
    p.add_argument(
        "--cal-search-radius-deg",
        type=float,
        default=0.0,
        help="Search radius in degrees for calibrator lookup")
    p.add_argument(
        "--cal-output-dir",
        default=None,
        help="Directory for calibrator-model MS (defaults to output_dir)")
    # New CLI flags
    p.add_argument(
        "--no-stage-tmpfs",
        dest="stage_tmpfs",
        action="store_false",
        default=True,
        help="Disable staging MS to tmpfs (/dev/shm) before moving to output")
    p.add_argument(
        "--tmpfs-path",
        default="/dev/shm",
        help="tmpfs path to stage MS when enabled")
    p.add_argument(
        "--parallel-subband",
        action="store_true",
        default=False,
        help="Write per-subband MS files in parallel then concat for faster full writes")
    p.add_argument("--max-workers", type=int, default=4,
                   help="Parallel subband writer workers")
    p.add_argument("--dask-write", action="store_true", default=False,
                   help="Write MS via dask-ms (experimental)")
    p.add_argument(
        "--dask-write-failfast",
        action="store_true",
        default=False,
        help="Abort immediately if dask-ms write fails (no fallback)")
    p.add_argument(
        "--field-per-integration",
        action="store_true",
        default=False,
        help="Create one FIELD row per integration time (requires dask-ms writer)")
    # dask-ms chunk tuning
    p.add_argument("--daskms-row-chunks", type=int, default=None,
                   help="Row chunk size for dask-ms Dataset (default: 8192)")
    p.add_argument(
        "--daskms-cube-row-chunks",
        type=int,
        default=None,
        help="Row chunk size for DATA/FLAG cubes (default: same as row-chunks)")
    # QA quicklooks (shadeMS)
    p.add_argument("--qa-shadems", action="store_true", default=False,
                   help="Enable shadeMS quicklook plots after writing each MS")
    p.add_argument(
        "--qa-shadems-resid",
        action="store_true",
        default=False,
        help="Include residual plot (CORRECTED_DATA-MODEL_DATA) if MODEL_DATA exists")
    p.add_argument(
        "--qa-shadems-max",
        type=int,
        default=4,
        help="Maximum number of quicklook plots to produce (default: 4)")
    p.add_argument("--qa-shadems-timeout", type=int, default=600,
                   help="Per-plot timeout in seconds (default: 600)")
    p.add_argument(
        "--qa-state-dir",
        default=None,
        help="Base state directory for QA artifacts (default: $PIPELINE_STATE_DIR or 'state')")
    # QA ragavi (HTML inspector)
    p.add_argument("--qa-ragavi-vis", action="store_true", default=False,
                   help="Enable ragavi-vis HTML export after writing each MS")
    p.add_argument(
        "--qa-ragavi-timeout",
        type=int,
        default=600,
        help="Timeout in seconds for ragavi-vis export (default: 600)")
    p.add_argument("--strict-ms", action="store_true", default=True, help="Validate MS structure after write (recommended)")
    args = p.parse_args()

    try:
        logging.basicConfig(
            level=getattr(logging, args.log_level.upper(), logging.INFO),
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    except Exception:
        pass

    # Apply safe default environment overrides for stability when not provided
    os.environ.setdefault('HDF5_USE_FILE_LOCKING', 'FALSE')
    os.environ.setdefault('OMP_NUM_THREADS', '4')
    os.environ.setdefault('MKL_NUM_THREADS', '4')

    convert_subband_groups_to_ms(
        args.input_dir,
        args.output_dir,
        args.start_time,
        args.end_time,
        flux=args.flux,
        fringestop=not args.no_fringestop,
        cal_catalog=args.cal_catalog,
        cal_search_radius_deg=float(args.cal_search_radius_deg or 0.0),
        cal_output_dir=args.cal_output_dir,
        checkpoint_dir=args.checkpoint_dir,
        scratch_dir=args.scratch_dir,
        direct_ms=bool(args.direct_ms),
        stage_to_tmpfs=args.stage_tmpfs,
        tmpfs_path=args.tmpfs_path,
        parallel_subband=args.parallel_subband,
        max_workers=args.max_workers,
        dask_write=bool(args.dask_write),
        dask_failfast=bool(args.dask_write_failfast),
        field_per_integration=bool(args.field_per_integration),
        daskms_row_chunks=args.daskms_row_chunks,
        daskms_cube_row_chunks=args.daskms_cube_row_chunks,
        qa_shadems=bool(args.qa_shadems),
        qa_shadems_resid=bool(args.qa_shadems_resid),
        qa_shadems_max=int(args.qa_shadems_max),
        qa_shadems_timeout=int(args.qa_shadems_timeout),
        qa_state_dir=args.qa_state_dir,
        qa_ragavi_vis=bool(args.qa_ragavi_vis),
        qa_ragavi_timeout=int(args.qa_ragavi_timeout),
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
