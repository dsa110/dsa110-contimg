"""
Calibration application service for the continuum imaging pipeline.

This service provides a unified interface for applying calibration tables to
Measurement Sets. It handles:
- Calibration table lookup from registry
- Application with proper error handling
- Verification of CORRECTED_DATA population
- Database status updates

This service consolidates duplicate calibration application logic found across
multiple scripts (build_calibrator_transit_offsets.py, image_groups_in_timerange.py,
run_next_field_after_central.py, imaging/worker.py, etc.).
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from casacore.tables import table

from dsa110_contimg.calibration.applycal import apply_to_target
from dsa110_contimg.database.products import ensure_products_db, ms_index_upsert
from dsa110_contimg.database.registry import ensure_db as ensure_cal_db, get_active_applylist

logger = logging.getLogger(__name__)


@dataclass
class CalibrationApplicationResult:
    """Result of calibration application operation."""
    success: bool
    caltables_applied: List[str]
    verified: bool
    error: Optional[str] = None
    metrics: Optional[dict] = None


def _ms_time_range(ms_path: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Extract time range from MS. Returns (start_mjd, end_mjd, mid_mjd)."""
    try:
        from casatools import msmetadata
        msmd = msmetadata()
        msmd.open(ms_path)
        try:
            tr = msmd.timerangeforobs()
            if tr and isinstance(tr, (list, tuple)) and len(tr) >= 2:
                start_mjd = float(tr[0])
                end_mjd = float(tr[1])
                msmd.close()
                return start_mjd, end_mjd, 0.5 * (start_mjd + end_mjd)
        except Exception:
            pass
        
        # Fallback: derive from timesforscans()
        try:
            tmap = msmd.timesforscans()
            msmd.close()
            if isinstance(tmap, dict) and tmap:
                all_ts = [t for arr in tmap.values() for t in arr]
                if all_ts:
                    t0 = min(all_ts) / 86400.0
                    t1 = max(all_ts) / 86400.0
                    return float(t0), float(t1), 0.5 * (t0 + t1)
        except Exception:
            pass
        msmd.close()
    except Exception:
        pass
    
    # Final fallback: use current time
    try:
        from casacore.tables import table as _tb
        with _tb(f"{ms_path}::OBSERVATION", readonly=True) as _obs:
            t0 = _obs.getcol("TIME_RANGE")[0][0] / 86400.0
            t1 = _obs.getcol("TIME_RANGE")[0][1] / 86400.0
            return float(t0), float(t1), 0.5 * (t0 + t1)
    except Exception:
        pass
    
    return None, None, None


def get_active_caltables(
    ms_path: str,
    registry_db: Path,
    *,
    set_name: Optional[str] = None,
    mid_mjd: Optional[float] = None
) -> List[str]:
    """
    Get active calibration tables for a Measurement Set.
    
    Args:
        ms_path: Path to Measurement Set
        registry_db: Path to calibration registry database
        set_name: Optional specific calibration set name to use
        mid_mjd: Optional MJD midpoint (if None, extracted from MS)
    
    Returns:
        List of calibration table paths (ordered by apply order)
    
    Raises:
        ValueError: If mid_mjd cannot be determined and set_name not provided
    """
    if mid_mjd is None:
        _, _, mid_mjd = _ms_time_range(ms_path)
        if mid_mjd is None:
            if set_name is None:
                raise ValueError(
                    f"Cannot determine mid_mjd for {ms_path} and set_name not provided. "
                    "Either provide mid_mjd explicitly or ensure MS has valid time range."
                )
            # Fallback: use current time if set_name provided
            from astropy.time import Time
            mid_mjd = Time.now().mjd
    
    applylist = get_active_applylist(registry_db, float(mid_mjd), set_name=set_name)
    return applylist


def verify_calibration_applied(
    ms_path: str,
    *,
    sample_fraction: float = 0.1,
    min_nonzero_samples: int = 10
) -> Tuple[bool, dict]:
    """
    Verify that CORRECTED_DATA is populated after calibration application.
    
    Args:
        ms_path: Path to Measurement Set
        sample_fraction: Fraction of rows to sample (default: 0.1)
        min_nonzero_samples: Minimum number of non-zero samples required
    
    Returns:
        (verified, metrics) tuple where metrics contains diagnostic information
    """
    metrics = {}
    
    try:
        with table(ms_path, readonly=True, ack=False) as tb:
            if "CORRECTED_DATA" not in tb.colnames():
                metrics["error"] = "CORRECTED_DATA column not present"
                return False, metrics
            
            n_rows = tb.nrows()
            if n_rows == 0:
                metrics["error"] = "MS has zero rows"
                return False, metrics
            
            # Sample data
            sample_size = max(100, min(1024, int(n_rows * sample_fraction)))
            indices = np.linspace(0, n_rows - 1, sample_size, dtype=int)
            
            corrected_data = tb.getcol("CORRECTED_DATA", startrow=indices[0], nrow=len(indices))
            flags = tb.getcol("FLAG", startrow=indices[0], nrow=len(indices))
            
            # Check for all zeros
            unflagged = corrected_data[~flags]
            if len(unflagged) == 0:
                metrics["error"] = "All CORRECTED_DATA is flagged"
                return False, metrics
            
            corrected_amps = np.abs(unflagged)
            nonzero_count = np.count_nonzero(corrected_amps > 1e-10)
            
            metrics["sampled_rows"] = sample_size
            metrics["unflagged_samples"] = len(unflagged)
            metrics["nonzero_samples"] = int(nonzero_count)
            metrics["median_amplitude"] = float(np.median(corrected_amps))
            metrics["min_amplitude"] = float(np.min(corrected_amps))
            metrics["max_amplitude"] = float(np.max(corrected_amps))
            
            if nonzero_count < min_nonzero_samples:
                metrics["error"] = f"Only {nonzero_count} non-zero samples found (minimum: {min_nonzero_samples})"
                return False, metrics
            
            return True, metrics
    
    except Exception as e:
        metrics["error"] = str(e)
        logger.error(f"Error verifying calibration: {e}", exc_info=True)
        return False, metrics


def apply_calibration(
    ms_path: str,
    registry_db: Path,
    *,
    caltables: Optional[List[str]] = None,
    set_name: Optional[str] = None,
    field: str = "",
    verify: bool = True,
    update_db: bool = False,
    products_db: Optional[Path] = None,
    sample_fraction: float = 0.1
) -> CalibrationApplicationResult:
    """
    Apply calibration tables to a Measurement Set.
    
    This is the main entry point for calibration application. It handles:
    - Calibration table lookup (if not provided)
    - Application with error handling
    - Verification of CORRECTED_DATA population
    - Database status updates
    
    Args:
        ms_path: Path to Measurement Set
        registry_db: Path to calibration registry database
        caltables: Optional explicit list of calibration table paths.
                   If None, looks up active tables from registry.
        set_name: Optional calibration set name (used if caltables not provided)
        field: Field selection for applycal (default: "" = all fields)
        verify: Whether to verify CORRECTED_DATA is populated
        update_db: Whether to update products database status
        products_db: Path to products database (required if update_db=True)
        sample_fraction: Fraction of data to sample for verification
    
    Returns:
        CalibrationApplicationResult with success status and diagnostics
    """
    ms_path_str = os.fspath(ms_path)
    
    # Lookup calibration tables if not provided
    if caltables is None:
        try:
            caltables = get_active_caltables(ms_path_str, registry_db, set_name=set_name)
        except Exception as e:
            error_msg = f"Failed to lookup calibration tables: {e}"
            logger.error(error_msg)
            return CalibrationApplicationResult(
                success=False,
                caltables_applied=[],
                verified=False,
                error=error_msg
            )
    
    if not caltables:
        error_msg = "No calibration tables available"
        logger.warning(f"{ms_path_str}: {error_msg}")
        return CalibrationApplicationResult(
            success=False,
            caltables_applied=[],
            verified=False,
            error=error_msg
        )
    
    # Verify tables exist
    missing = [ct for ct in caltables if not Path(ct).exists()]
    if missing:
        error_msg = f"Calibration tables not found: {missing}"
        logger.error(f"{ms_path_str}: {error_msg}")
        return CalibrationApplicationResult(
            success=False,
            caltables_applied=[],
            verified=False,
            error=error_msg
        )
    
    # Apply calibration
    try:
        logger.info(f"Applying {len(caltables)} calibration tables to {ms_path_str}")
        apply_to_target(ms_path_str, field=field, gaintables=caltables, calwt=True)
        logger.info(f"Successfully applied calibration to {ms_path_str}")
    except Exception as e:
        error_msg = f"applycal failed: {e}"
        logger.error(f"{ms_path_str}: {error_msg}", exc_info=True)
        return CalibrationApplicationResult(
            success=False,
            caltables_applied=caltables,
            verified=False,
            error=error_msg
        )
    
    # Verify if requested
    verified = False
    metrics = None
    if verify:
        verified, metrics = verify_calibration_applied(ms_path_str, sample_fraction=sample_fraction)
        if not verified:
            error_msg = metrics.get("error", "Verification failed")
            logger.warning(f"{ms_path_str}: Calibration verification failed: {error_msg}")
            return CalibrationApplicationResult(
                success=False,
                caltables_applied=caltables,
                verified=False,
                error=f"Verification failed: {error_msg}",
                metrics=metrics
            )
        logger.info(f"{ms_path_str}: Calibration verified successfully")
    
    # Update database if requested
    if update_db and products_db is not None:
        try:
            conn = ensure_products_db(products_db)
            start_mjd, end_mjd, mid_mjd = _ms_time_range(ms_path_str)
            ms_index_upsert(
                conn,
                ms_path_str,
                start_mjd=start_mjd,
                end_mjd=end_mjd,
                mid_mjd=mid_mjd,
                cal_applied=1 if verified else 0,
                stage="calibrated" if verified else "calibration_failed",
                processed_at=time.time(),
                stage_updated_at=time.time()
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to update products database: {e}", exc_info=True)
    
    return CalibrationApplicationResult(
        success=True,
        caltables_applied=caltables,
        verified=verified,
        metrics=metrics
    )

