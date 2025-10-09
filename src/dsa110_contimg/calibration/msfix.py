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
