"""Legacy testing-only function: write_point_model_quick()

ARCHIVED: 2025-11-05
REASON: Testing-only function, not used in production
STATUS: Deprecated - Use write_point_model_with_ft(use_manual=True) instead

This function was used for testing only. It writes an amplitude-only model
without proper phase calculation. For production use, see:
- write_point_model_with_ft(use_manual=True) - Recommended
- _calculate_manual_model_data() - Core implementation
"""

from typing import Optional
import casacore.tables as tb
import numpy as np


def _ensure_imaging_columns(ms_path: str) -> None:
    """Ensure imaging columns exist in MS."""
    try:
        from casacore.tables import addImagingColumns
        addImagingColumns(ms_path)
    except Exception:
        pass


def _initialize_corrected_from_data(ms_path: str) -> None:
    """Initialize CORRECTED_DATA from DATA."""
    try:
        with tb.table(ms_path, readonly=False) as t:
            if "DATA" in t.colnames() and "CORRECTED_DATA" in t.colnames():
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
    
    .. deprecated:: 2025-11-05
        This function is archived. It was testing-only and not used in production.
        Use :func:`dsa110_contimg.calibration.model.write_point_model_with_ft` with
        ``use_manual=True`` instead.
        
        Issues:
        - No phase calculation (amplitude-only)
        - Not physically correct
        - Testing only, never used in production
    """
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

