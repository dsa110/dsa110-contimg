"""Pre-calculation and caching of transit times for registered calibrators.

This module provides functionality to pre-calculate transit times and assess
data availability when:
1. A new calibrator is registered
2. Telescope pointing changes significantly

This avoids recalculating transit times on every pipeline run.
"""

import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional

from astropy import units as u
from astropy.time import Time

from dsa110_contimg.calibration.schedule import previous_transits
from dsa110_contimg.conversion.calibrator_ms_service import CalibratorMSService
from dsa110_contimg.conversion.helpers_db import query_subband_groups

logger = logging.getLogger(__name__)


def ensure_calibrator_transits_table(conn: sqlite3.Connection) -> None:
    """Ensure calibrator_transits table exists.

    Table stores pre-calculated transit times with data availability assessment.
    This is permanent storage in the products database, not a cache.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS calibrator_transits (
            calibrator_name TEXT NOT NULL,
            transit_mjd REAL NOT NULL,
            transit_iso TEXT NOT NULL,
            has_data INTEGER NOT NULL DEFAULT 0,
            group_id TEXT,
            group_mid_iso TEXT,
            delta_minutes REAL,
            pb_response REAL,
            dec_match INTEGER NOT NULL DEFAULT 0,
            calculated_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            PRIMARY KEY (calibrator_name, transit_mjd)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_calibrator_transits_calibrator 
        ON calibrator_transits(calibrator_name, updated_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_calibrator_transits_has_data 
        ON calibrator_transits(calibrator_name, has_data, transit_mjd DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_calibrator_transits_mjd 
        ON calibrator_transits(transit_mjd DESC)
        """
    )


def precalculate_transits_for_calibrator(
    products_db: sqlite3.Connection,
    calibrator_name: str,
    ra_deg: float,
    dec_deg: float,
    max_days_back: int = 60,
    window_minutes: int = 60,
    dec_tolerance_deg: float = 2.5,
    min_pb_response: float = 0.3,
    freq_ghz: float = 1.4,
) -> int:
    """Pre-calculate transit times and assess data availability for a calibrator.

    Args:
        products_db: Products database connection
        calibrator_name: Name of calibrator (e.g., "0834+555")
        ra_deg: Calibrator RA in degrees
        dec_deg: Calibrator Dec in degrees
        max_days_back: Maximum days to search back (default: 60)
        window_minutes: Search window around transit (default: 60)
        dec_tolerance_deg: Declination tolerance in degrees (default: 2.5)
        min_pb_response: Minimum primary beam response (default: 0.3)
        freq_ghz: Frequency in GHz (default: 1.4)

    Returns:
        Number of transits with available data
    """
    ensure_calibrator_transits_table(products_db)
    
    # Get theoretical transit times
    transits = previous_transits(ra_deg, start_time=Time.now(), n=max_days_back)
    
    logger.info(
        f"Pre-calculating transit times for {calibrator_name} "
        f"(RA={ra_deg:.6f}, Dec={dec_deg:.6f})"
    )
    
    # Initialize calibrator service for validation
    service = CalibratorMSService(
        products_db=products_db,
        output_dir=Path("/tmp"),  # Not used for pre-calculation
    )
    
    transits_with_data = 0
    calculated_at = time.time()
    
    for transit in transits:
        transit_mjd = transit.mjd
        transit_iso = transit.isot
        
        # Check if already stored in database (and recent)
        cursor = products_db.cursor()
        existing = cursor.execute(
            """
            SELECT has_data, group_id, group_mid_iso, delta_minutes, pb_response, dec_match
            FROM calibrator_transits
            WHERE calibrator_name = ? AND transit_mjd = ?
            AND updated_at > ? - 86400
            """,
            (calibrator_name, transit_mjd, calculated_at - 86400),  # Refresh if older than 24 hours
        ).fetchone()
        
        if existing:
            # Use existing result from database
            has_data, group_id, group_mid_iso, delta_minutes, pb_response, dec_match = existing
            if has_data:
                transits_with_data += 1
            continue
        
        # Calculate transit window
        half_window = window_minutes // 2
        t0 = (transit - half_window * u.min).to_datetime().strftime("%Y-%m-%d %H:%M:%S")
        t1 = (transit + half_window * u.min).to_datetime().strftime("%Y-%m-%d %H:%M:%S")
        
        # Query for groups in window
        groups = query_subband_groups(products_db, t0, t1, tolerance_s=1.0)
        
        has_data = 0
        group_id = None
        group_mid_iso = None
        delta_minutes = None
        pb_response = None
        dec_match = 0
        
        if groups:
            # Find best candidate group
            from astropy import units as u
            best_result = service._find_best_candidate_group(groups, transit)
            
            if best_result:
                dt_min, gbest, mid = best_result
                
                # Check if complete subband group
                is_complete, _ = service._is_complete_subband_group(gbest)
                
                if is_complete:
                    # Extract declination from file
                    pt_dec_deg = None
                    try:
                        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import \
                          _peek_uvh5_phase_and_midtime
                        _, pt_dec_rad, _ = _peek_uvh5_phase_and_midtime(gbest[0])
                        pt_dec_deg = float(pt_dec_rad.to_value(u.deg)) if pt_dec_rad is not None else None
                    except Exception:
                        pass
                    
                    # Check declination match
                    if pt_dec_deg is not None:
                        dec_diff = abs(pt_dec_deg - dec_deg)
                        dec_match = 1 if dec_diff <= dec_tolerance_deg else 0
                    
                    # Check primary beam response
                    pb_validation = service._validate_primary_beam(
                        gbest[0], ra_deg, dec_deg, min_pb_response, freq_ghz
                    )
                    
                    if pb_validation and dec_match:
                        has_data = 1
                        group_id = os.path.basename(gbest[0]).split("_")[0]  # Extract group ID
                        group_mid_iso = mid.isot
                        delta_minutes = dt_min
                        pb_response = pb_validation["pb_response"]
                        transits_with_data += 1
        
        # Store in database
        products_db.execute(
            """
            INSERT OR REPLACE INTO calibrator_transits
            (calibrator_name, transit_mjd, transit_iso, has_data, group_id,
             group_mid_iso, delta_minutes, pb_response, dec_match, calculated_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                calibrator_name,
                transit_mjd,
                transit_iso,
                has_data,
                group_id,
                group_mid_iso,
                delta_minutes,
                pb_response,
                dec_match,
                calculated_at,
                calculated_at,  # updated_at same as calculated_at for new entries
            ),
        )
    
    products_db.commit()
    
    logger.info(
        f"Pre-calculated {len(transits)} transits for {calibrator_name}, "
        f"{transits_with_data} have available data"
    )
    
    return transits_with_data


# Alias for backward compatibility
get_cached_transits = get_calibrator_transits


# Alias for backward compatibility
invalidate_transit_cache = delete_calibrator_transits



