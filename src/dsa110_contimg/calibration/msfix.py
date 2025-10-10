from __future__ import annotations

"""
Utilities to repair common MS metadata issues that can crash CASA tasks.

Currently fixes FIELD::NUM_POLY when DIR columns have a single coefficient.
"""

from casacore.tables import table


def fix_field_num_poly(ms_path: str) -> bool:
    """Set FIELD::NUM_POLY to 0 when DIR columns have only one coefficient.

    CASA expects DIR columns to have shape (NUM_POLY+1, 2). Some writers or
    concat operations produce NUM_POLY=1 with DIR shape (1,2), which can cause
    segfaults in casacore when interpolating the phase center. This function
    normalizes NUM_POLY to 0 in that case.

    Returns True if any changes were made, False otherwise.
    """
    changed = False
    fld = f"{ms_path}::FIELD"
    try:
        with table(fld, readonly=False) as t:
            # Read a sample DIR array to infer coefficient dimension
            pd = t.getcol("PHASE_DIR")
            # DIR array shape per row is (ncoef, 2)
            if pd.ndim == 3 and pd.shape[1] == 1:
                ncoef = 1
            elif pd.ndim == 2:
                ncoef = pd.shape[0]
            else:
                # Fallback: assume constant
                ncoef = 1
            num_poly = t.getcol("NUM_POLY")
            # Expected NUM_POLY = ncoef-1; if ncoef==1 and NUM_POLY!=0, fix it
            if ncoef == 1:
                import numpy as np
                bad = num_poly != 0
                if bad.any():
                    num_poly[bad] = 0
                    t.putcol("NUM_POLY", num_poly)
                    changed = True
    except Exception:
        # Best effort; leave unchanged on failure
        return False
    return changed


def fix_spw_resolution(ms_path: str) -> bool:
    """Ensure SPECTRAL_WINDOW::RESOLUTION and EFFECTIVE_BW arrays are present.

    Some writers leave these as empty array columns per row. CASA calibration
    tasks expect per-channel arrays. This fills missing arrays with the absolute
    CHAN_WIDTH values.

    Returns True if any changes were made, False otherwise.
    """
    from casacore.tables import table
    import numpy as np

    changed = False
    spw = f"{ms_path}::SPECTRAL_WINDOW"
    try:
        with table(spw, readonly=False) as t:
            nrow = t.nrows()
            # Read CHAN_WIDTH as reference
            cw = t.getcol("CHAN_WIDTH")  # shape (nrow, nchan)
            nchan = cw.shape[1] if cw.ndim == 2 else int(np.asarray(cw).size)

            for col in ("RESOLUTION", "EFFECTIVE_BW"):
                if col not in t.colnames():
                    continue
                # Try reading; if it errors or has wrong shape, rewrite
                need_fill = False
                arr = None
                try:
                    arr = t.getcol(col)
                    if arr.ndim != 2 or arr.shape[1] != nchan:
                        need_fill = True
                except Exception:
                    need_fill = True
                if need_fill:
                    fill = np.abs(cw)
                    t.putcol(col, fill)
                    changed = True
    except Exception:
        return False
    return changed


def fix_main_sigma_weight(ms_path: str) -> bool:
    """Ensure SIGMA/WEIGHT arrays exist for each row in the MAIN table.

    Fills missing arrays with ones of length NUM_CORR from POLARIZATION.
    Returns True if any rows were fixed.
    """
    from casacore.tables import table
    import numpy as np

    # Determine number of correlations
    try:
        with table(f"{ms_path}::POLARIZATION", readonly=True) as pt:
            nc = int(np.asarray(pt.getcol("NUM_CORR")).ravel()[0])
    except Exception:
        nc = 2

    fixed = False
    ones = np.ones((nc,), dtype=np.float32)
    try:
        with table(ms_path, readonly=False) as t:
            nrow = t.nrows()
            # Fix SIGMA
            for r in range(nrow):
                try:
                    arr = t.getcell("SIGMA", r)
                    if getattr(arr, "size", 0) != nc:
                        t.putcell("SIGMA", r, ones)
                        fixed = True
                except Exception:
                    t.putcell("SIGMA", r, ones)
                    fixed = True
            # Fix WEIGHT
            for r in range(nrow):
                try:
                    arr = t.getcell("WEIGHT", r)
                    if getattr(arr, "size", 0) != nc:
                        t.putcell("WEIGHT", r, ones)
                        fixed = True
                except Exception:
                    t.putcell("WEIGHT", r, ones)
                    fixed = True
    except Exception:
        return False
    return fixed


def fix_observation_table(ms_path: str) -> bool:
    """Ensure OBSERVATION subtable has at least one row and IDs are valid.

    Populates minimal columns (TIME_RANGE, TELESCOPE_NAME, OBSERVER, PROJECT, RELEASE_DATE)
    and sets MAIN::OBSERVATION_ID to 0 for all rows.
    """
    from casacore.tables import table
    import numpy as np
    changed = False
    try:
        # Create/ensure a single OBSERVATION row
        with table(f"{ms_path}::OBSERVATION", ack=False, readonly=False) as tobs:
            n = tobs.nrows()
            if n == 0:
                tobs.addrows(1)
            # Attempt to infer TIME_RANGE from MAIN::TIME
            try:
                with table(ms_path) as mt:
                    times = mt.getcol('TIME') if 'TIME' in mt.colnames() else None
            except Exception:
                times = None
            if times is not None and times.size:
                tr = np.array([float(times.min()), float(times.max())], dtype=np.float64)
                try:
                    tobs.putcell('TIME_RANGE', 0, tr)
                except Exception:
                    pass
            # Minimal metadata
            for col, val in (
                ('TELESCOPE_NAME', 'CARMA'),
                ('OBSERVER', 'unknown'),
                ('PROJECT', ''),
                ('RELEASE_DATE', 0.0),
            ):
                try:
                    tobs.putcell(col, 0, val)
                except Exception:
                    pass
            changed = True
        # Set MAIN::OBSERVATION_ID to 0
        with table(ms_path, ack=False, readonly=False) as mt:
            if 'OBSERVATION_ID' in mt.colnames():
                try:
                    mt.putcol('OBSERVATION_ID', np.zeros(mt.nrows(), dtype=np.int32))
                    changed = True
                except Exception:
                    pass
    except Exception:
        return False
    return changed


def fix_main_interval(ms_path: str) -> bool:
    """Ensure MAIN::INTERVAL has positive values.

    Some writers may leave INTERVAL as zeros, which can destabilize solvers.
    This sets non-positive intervals to the median time-spacing derived from
    MAIN::TIME (in seconds), or 1.0 if it cannot be inferred.
    """
    from casacore.tables import table
    import numpy as np
    try:
        with table(ms_path, readonly=False, ack=False) as t:
            if 'INTERVAL' not in t.colnames() or 'TIME' not in t.colnames():
                return False
            interval = t.getcol('INTERVAL')
            # Determine a safe positive interval
            times = t.getcol('TIME')
            try:
                ut = np.unique(times)
                diffs = np.diff(np.sort(ut))
                diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
                fallback = float(np.median(diffs)) if diffs.size else 1.0
            except Exception:
                fallback = 1.0
            bad = ~np.isfinite(interval) | (interval <= 0)
            if np.any(bad):
                interval[bad] = fallback
                t.putcol('INTERVAL', interval)
                return True
    except Exception:
        return False
    return False


def ensure_weight_spectrum(ms_path: str) -> bool:
    """Ensure MAIN::WEIGHT_SPECTRUM exists and matches DATA shape.

    If absent or wrong-shaped, create/fill it by broadcasting WEIGHT across
    channels: WEIGHT_SPECTRUM[row] = tile(WEIGHT[row], (nchan, 1)).
    """
    import numpy as np
    from casacore.tables import table, makearrcoldesc, maketabdesc
    try:
        with table(ms_path, readonly=False, ack=False) as t:
            cols = set(t.colnames())
            # Determine per-row (nchan, ncorr) from DATA
            try:
                d0 = t.getcell('DATA', 0)
                nchan, ncorr = int(d0.shape[0]), int(d0.shape[1])
            except Exception:
                # Fallback to SPW/POL shapes
                with table(f"{ms_path}::SPECTRAL_WINDOW") as spw:
                    nchan = int(np.asarray(spw.getcol('NUM_CHAN')).ravel()[0])
                with table(f"{ms_path}::POLARIZATION") as pol:
                    ncorr = int(np.asarray(pol.getcol('NUM_CORR')).ravel()[0])

            # Create column if missing
            if 'WEIGHT_SPECTRUM' not in cols:
                desc = maketabdesc(makearrcoldesc('WEIGHT_SPECTRUM', 0.0, ndim=2))
                t.addcols(desc)

            # Fill in chunks to avoid large memory spikes
            nrow = t.nrows()
            chunk = 4096
            w = None
            for start in range(0, nrow, chunk):
                end = min(start + chunk, nrow)
                # Read WEIGHT for this block
                wb = t.getcol('WEIGHT', startrow=start, nrow=end - start)
                # wb shape: (nrow_block, ncorr)
                for i in range(end - start):
                    wr = wb[i]
                    if wr is None or np.size(wr) != ncorr:
                        wr = np.ones((ncorr,), dtype=np.float32)
                    mat = np.broadcast_to(wr[None, :], (nchan, ncorr)).astype(np.float32, copy=False)
                    t.putcell('WEIGHT_SPECTRUM', start + i, mat)
            return True
    except Exception:
        return False


def fix_scan_number(ms_path: str) -> bool:
    """Ensure SCAN_NUMBER is positive (>=1). Sets to 1 if non-positive or NaN.
    """
    import numpy as np
    try:
        with table(ms_path, readonly=False, ack=False) as t:
            if 'SCAN_NUMBER' not in t.colnames():
                return False
            sc = t.getcol('SCAN_NUMBER')
            bad = ~np.isfinite(sc) | (sc <= 0)
            if np.any(bad):
                sc[bad] = 1
                t.putcol('SCAN_NUMBER', sc)
                return True
    except Exception:
        return False
    return False
