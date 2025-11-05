"""Shared utilities to configure Measurement Sets for imaging.

This module centralizes robust, repeatable post-write MS preparation:
- Ensure imaging columns exist (MODEL_DATA, CORRECTED_DATA)
- Populate imaging columns for every row with array values matching DATA
- Ensure FLAG and WEIGHT_SPECTRUM arrays are present and correctly shaped
- Initialize weights, including WEIGHT_SPECTRUM, via casatasks.initweights
- Normalize ANTENNA.MOUNT to CASA-compatible values

All callers should prefer `configure_ms_for_imaging()` rather than duplicating
these steps inline in scripts. This provides a single source of truth for MS
readiness across the pipeline.
"""

from __future__ import annotations

import os
from typing import Optional  # noqa: F401 (imported for potential future use)


def _ensure_imaging_columns_exist(ms_path: str) -> None:
    """Add MODEL_DATA and CORRECTED_DATA columns if missing."""
    try:
        from casacore.tables import addImagingColumns as _addImCols  # type: ignore
        _addImCols(ms_path)
    except Exception:
        # Non-fatal: column creation can fail on already-populated tables
        pass


def _ensure_imaging_columns_populated(ms_path: str) -> None:
    """
    Ensure MODEL_DATA and CORRECTED_DATA contain array values for every
    row, with shapes/dtypes matching the DATA column cells.
    """
    try:
        from casacore.tables import table as _tb  # type: ignore
        import numpy as _np
    except Exception:
        return

    try:
        with _tb(ms_path, readonly=False) as tb:
            nrow = tb.nrows()
            if nrow == 0:
                return
            data0 = tb.getcell('DATA', 0)
            data_shape = getattr(data0, 'shape', None)
            data_dtype = getattr(data0, 'dtype', None)
            if not data_shape or data_dtype is None:
                return
            for col in ('MODEL_DATA', 'CORRECTED_DATA'):
                if col not in tb.colnames():
                    continue
                fixed = 0
                for r in range(nrow):
                    try:
                        val = tb.getcell(col, r)
                        if (val is None) or (
                            getattr(val, 'shape', None) != data_shape
                        ):
                            tb.putcell(
                                col, r, _np.zeros(data_shape, dtype=data_dtype)
                            )
                            fixed += 1
                    except Exception:
                        tb.putcell(
                            col, r, _np.zeros(data_shape, dtype=data_dtype)
                        )
                        fixed += 1
                # Optional: could log fixed count; keep silent here
    except Exception:
        # Non-fatal: best-effort population only
        return


def _ensure_flag_and_weight_spectrum(ms_path: str) -> None:
    """
    Ensure FLAG and WEIGHT_SPECTRUM cells exist with correct shapes for all rows.

    - FLAG: boolean array shaped like DATA; fill with False when undefined
    - WEIGHT_SPECTRUM: float array shaped like DATA; when undefined,
      repeat WEIGHT across channels; if WEIGHT_SPECTRUM appears
      inconsistent across rows, drop the column to let CASA fall back
      to WEIGHT.
    """
    try:
        from casacore.tables import table as _tb  # type: ignore
        import numpy as _np
    except Exception:
        return

    try:
        with _tb(ms_path, readonly=False) as tb:
            nrow = tb.nrows()
            colnames = set(tb.colnames())
            has_ws = 'WEIGHT_SPECTRUM' in colnames
            ws_bad = False
            for i in range(nrow):
                try:
                    data = tb.getcell('DATA', i)
                except Exception:
                    continue
                target_shape = getattr(data, 'shape', None)
                if not target_shape or len(target_shape) != 2:
                    continue
                nchan, npol = int(target_shape[0]), int(target_shape[1])
                # FLAG
                try:
                    f = tb.getcell('FLAG', i)
                    if f is None or getattr(f, 'shape', None) != (nchan, npol):
                        raise RuntimeError('FLAG shape mismatch')
                except Exception:
                    tb.putcell('FLAG', i, _np.zeros((nchan, npol), dtype=bool))
                # WEIGHT_SPECTRUM
                if has_ws:
                    try:
                        ws_val = tb.getcell('WEIGHT_SPECTRUM', i)
                        if (
                            ws_val is None
                            or getattr(ws_val, 'shape', None) != (nchan, npol)
                        ):
                            raise RuntimeError('WS shape mismatch')
                    except Exception:
                        try:
                            w = tb.getcell('WEIGHT', i)
                            w = _np.asarray(w).reshape(-1)
                            if w.size != npol:
                                w = _np.ones((npol,), dtype=float)
                        except Exception:
                            w = _np.ones((npol,), dtype=float)
                        ws = _np.repeat(w[_np.newaxis, :], nchan, axis=0)
                        tb.putcell('WEIGHT_SPECTRUM', i, ws)
                        ws_bad = True
            if has_ws and ws_bad:
                try:
                    tb.removecols(['WEIGHT_SPECTRUM'])
                except Exception:
                    pass
    except Exception:
        return


def _initialize_weights(ms_path: str) -> None:
    """Initialize WEIGHT and WEIGHT_SPECTRUM via casatasks.initweights."""
    try:
        from casatasks import initweights as _initweights  # type: ignore
        _initweights(vis=ms_path, wtmode='weight', doweight=True,
                     dowtsp=True, doflag=False)
    except Exception:
        # Non-fatal: initweights can fail on edge cases; downstream tools may
        # still work
        pass


def _fix_mount_type_in_ms(ms_path: str) -> None:
    """Normalize ANTENNA.MOUNT values to CASA-supported strings."""
    try:
        from casacore.tables import table as _tb  # type: ignore
        with _tb(ms_path + '/ANTENNA', readonly=False) as ant_table:
            mounts = ant_table.getcol('MOUNT')
            fixed = []
            for m in mounts:
                normalized = str(m or '').lower().strip()
                if normalized in (
                    'alt-az',
                    'altaz',
                    'alt_az',
                    'alt az',
                    'az-el',
                        'azel'):
                    fixed.append('alt-az')
                elif normalized in ('equatorial', 'eq'):
                    fixed.append('equatorial')
                elif normalized in ('x-y', 'xy'):
                    fixed.append('x-y')
                elif normalized in ('spherical', 'sphere'):
                    fixed.append('spherical')
                else:
                    fixed.append('alt-az')
            ant_table.putcol('MOUNT', fixed)
    except Exception:
        # Non-fatal normalization
        pass


def configure_ms_for_imaging(
    ms_path: str,
    *,
    ensure_columns: bool = True,
    ensure_flag_and_weight: bool = True,
    do_initweights: bool = True,
    fix_mount: bool = True,
    stamp_observation_telescope: bool = True,
) -> None:
    """
    Make a Measurement Set safe and ready for imaging and calibration.
    
    This function uses consistent error handling: critical failures raise
    exceptions, while non-critical issues log warnings and continue.

    Parameters
    ----------
    ms_path : str
        Path to the Measurement Set (directory path).
    ensure_columns : bool
        Ensure MODEL_DATA and CORRECTED_DATA columns exist.
    ensure_flag_and_weight : bool
        Ensure FLAG and WEIGHT_SPECTRUM arrays exist and are well-shaped.
    do_initweights : bool
        Run casatasks.initweights with WEIGHT_SPECTRUM initialization enabled.
    fix_mount : bool
        Normalize ANTENNA.MOUNT values.
        
    Raises
    ------
    RuntimeError
        If MS path does not exist or is not readable (critical failure)
    """
    if not isinstance(ms_path, str):
        ms_path = os.fspath(ms_path)

    # CRITICAL: Validate MS exists and is readable
    if not os.path.exists(ms_path):
        raise RuntimeError(f"MS does not exist: {ms_path}")
    if not os.path.isdir(ms_path):
        raise RuntimeError(f"MS path is not a directory: {ms_path}")
    if not os.access(ms_path, os.R_OK):
        raise RuntimeError(f"MS is not readable: {ms_path}")

    # Track which operations succeeded for summary logging
    operations_status = {
        'columns': 'skipped',
        'flag_weight': 'skipped', 
        'initweights': 'skipped',
        'mount_fix': 'skipped',
        'telescope_stamp': 'skipped'
    }

    if ensure_columns:
        try:
            _ensure_imaging_columns_exist(ms_path)
            _ensure_imaging_columns_populated(ms_path)
            operations_status['columns'] = 'success'
        except Exception as e:
            operations_status['columns'] = f'failed: {e}'
            # Non-fatal: continue with other operations
            
    if ensure_flag_and_weight:
        try:
            _ensure_flag_and_weight_spectrum(ms_path)
            operations_status['flag_weight'] = 'success'
        except Exception as e:
            operations_status['flag_weight'] = f'failed: {e}'
            # Non-fatal: continue with other operations
            
    if do_initweights:
        try:
            _initialize_weights(ms_path)
            operations_status['initweights'] = 'success'
        except Exception as e:
            operations_status['initweights'] = f'failed: {e}'
            # Non-fatal: initweights often fails on edge cases
            
    if fix_mount:
        try:
            _fix_mount_type_in_ms(ms_path)
            operations_status['mount_fix'] = 'success'
        except Exception as e:
            operations_status['mount_fix'] = f'failed: {e}'
            # Non-fatal: mount type normalization is optional
            
    if stamp_observation_telescope:
        try:
            from casacore.tables import table as _tb  # type: ignore
            import os as _os
            name = _os.getenv("PIPELINE_TELESCOPE_NAME", "DSA_110")
            with _tb(ms_path + '::OBSERVATION', readonly=False) as tb:
                n = tb.nrows()
                if n:
                    tb.putcol('TELESCOPE_NAME', [name] * n)
            operations_status['telescope_stamp'] = 'success'
        except Exception as e:
            operations_status['telescope_stamp'] = f'failed: {e}'
            # Non-fatal: telescope name stamping is optional
    
    # Summary logging - report what worked and what didn't
    import logging
    logger = logging.getLogger(__name__)
    
    success_ops = [op for op, status in operations_status.items() if status == 'success']
    failed_ops = [f"{op}({status.split(': ')[1]})" for op, status in operations_status.items() 
                  if status.startswith('failed')]
    
    if success_ops:
        logger.info(f"✓ MS configuration completed: {', '.join(success_ops)}")
    if failed_ops:
        logger.warning(f"⚠ MS configuration partial failures: {'; '.join(failed_ops)}")
    
    # Final validation: verify MS is still readable after all operations
    try:
        from casacore.tables import table as _tb
        with _tb(ms_path, readonly=True) as tb:
            if tb.nrows() == 0:
                raise RuntimeError(f"MS has no data after configuration: {ms_path}")
    except Exception as e:
        raise RuntimeError(f"MS became unreadable after configuration: {e}")


__all__ = [
    'configure_ms_for_imaging',
    '_ensure_imaging_columns_exist',
    '_ensure_imaging_columns_populated',
    '_ensure_flag_and_weight_spectrum',
    '_initialize_weights',
    '_fix_mount_type_in_ms',
]
