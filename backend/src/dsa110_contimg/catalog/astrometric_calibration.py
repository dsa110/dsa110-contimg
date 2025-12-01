"""Astrometric self-calibration for DSA-110 continuum imaging pipeline.

This module provides functions to refine astrometric accuracy by calculating
systematic offsets from high-precision catalogs (FIRST) and applying WCS corrections.

Implements Proposal #5: Astrometric Self-Calibration
Target: <1" accuracy (from current ~2-3")
"""

import logging
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def create_astrometry_tables(db_path: str = "/data/dsa110-contimg/state/db/pipeline.sqlite3") -> bool:
    """Create database tables for astrometric calibration tracking.

    Tables created:
    - astrometric_solutions: WCS correction solutions per mosaic
    - astrometric_residuals: Per-source offsets for quality assessment

    Args:
        db_path: Path to products database

    Returns:
        True if successful
    """
    conn = sqlite3.connect(db_path, timeout=30.0)
    cur = conn.cursor()

    try:
        # Astrometric solutions table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS astrometric_solutions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mosaic_id INTEGER NOT NULL,
                reference_catalog TEXT NOT NULL,
                n_matches INTEGER NOT NULL,
                ra_offset_mas REAL NOT NULL,
                dec_offset_mas REAL NOT NULL,
                ra_offset_err_mas REAL NOT NULL,
                dec_offset_err_mas REAL NOT NULL,
                rotation_deg REAL,
                scale_factor REAL,
                rms_residual_mas REAL NOT NULL,
                applied BOOLEAN DEFAULT 0,
                computed_at REAL NOT NULL,
                applied_at REAL,
                notes TEXT,
                FOREIGN KEY (mosaic_id) REFERENCES products(id)
            )
        """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_astrometry_mosaic 
            ON astrometric_solutions(mosaic_id, computed_at DESC)
        """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_astrometry_applied 
            ON astrometric_solutions(applied, computed_at DESC)
        """
        )

        # Per-source residuals table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS astrometric_residuals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                solution_id INTEGER NOT NULL,
                source_ra_deg REAL NOT NULL,
                source_dec_deg REAL NOT NULL,
                reference_ra_deg REAL NOT NULL,
                reference_dec_deg REAL NOT NULL,
                ra_offset_mas REAL NOT NULL,
                dec_offset_mas REAL NOT NULL,
                separation_mas REAL NOT NULL,
                source_flux_mjy REAL,
                reference_flux_mjy REAL,
                measured_at REAL NOT NULL,
                FOREIGN KEY (solution_id) REFERENCES astrometric_solutions(id)
            )
        """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_residuals_solution 
            ON astrometric_residuals(solution_id)
        """
        )

        conn.commit()
        logger.info("Created astrometric calibration tables")
        return True

    except Exception as e:
        logger.error(f"Error creating astrometric tables: {e}")
        return False
    finally:
        conn.close()


def calculate_astrometric_offsets(
    observed_sources: pd.DataFrame,
    reference_sources: pd.DataFrame,
    match_radius_arcsec: float = 5.0,
    min_matches: int = 10,
    flux_weight: bool = True,
) -> Optional[Dict]:
    """Calculate systematic astrometric offsets from reference catalog.

    Cross-matches observed sources with reference catalog (typically FIRST)
    and calculates median RA/Dec offsets.

    Args:
        observed_sources: DataFrame with columns: ra_deg, dec_deg, flux_mjy
        reference_sources: DataFrame with columns: ra_deg, dec_deg, flux_mjy
        match_radius_arcsec: Matching radius [arcsec]
        min_matches: Minimum number of matches required
        flux_weight: Weight offsets by source flux

    Returns:
        Dictionary with offset solution, or None if insufficient matches
    """
    if len(observed_sources) == 0 or len(reference_sources) == 0:
        logger.warning("Insufficient sources for astrometric calibration")
        return None

    matches = []
    match_radius_deg = match_radius_arcsec / 3600.0

    # Cross-match observed with reference
    for _, obs in observed_sources.iterrows():
        ra_obs = obs["ra_deg"]
        dec_obs = obs["dec_deg"]
        flux_obs = obs.get("flux_mjy", 1.0)

        # Find closest reference source
        ra_diff = (reference_sources["ra_deg"] - ra_obs) * np.cos(np.radians(dec_obs))
        dec_diff = reference_sources["dec_deg"] - dec_obs
        separation = np.sqrt(ra_diff**2 + dec_diff**2)

        closest_idx = np.argmin(separation)
        closest_sep = separation.iloc[closest_idx]

        if closest_sep <= match_radius_deg:
            ref_source = reference_sources.iloc[closest_idx]

            # Calculate offsets in milliarcseconds
            ra_offset_mas = (
                (ra_obs - ref_source["ra_deg"]) * 3600.0 * 1000.0 * np.cos(np.radians(dec_obs))
            )
            dec_offset_mas = (dec_obs - ref_source["dec_deg"]) * 3600.0 * 1000.0

            matches.append(
                {
                    "ra_obs": ra_obs,
                    "dec_obs": dec_obs,
                    "ra_ref": ref_source["ra_deg"],
                    "dec_ref": ref_source["dec_deg"],
                    "ra_offset_mas": ra_offset_mas,
                    "dec_offset_mas": dec_offset_mas,
                    "separation_mas": closest_sep * 3600.0 * 1000.0,
                    "flux_obs": flux_obs,
                    "flux_ref": ref_source.get("flux_mjy", 1.0),
                }
            )

    if len(matches) < min_matches:
        logger.warning(
            f"Insufficient matches for astrometric calibration: " f"{len(matches)} < {min_matches}"
        )
        return None

    logger.info(f"Found {len(matches)} astrometric matches")

    # Calculate weighted median offsets
    ra_offsets = np.array([m["ra_offset_mas"] for m in matches])
    dec_offsets = np.array([m["dec_offset_mas"] for m in matches])

    if flux_weight:
        # Weight by flux (brighter sources more reliable)
        weights = np.array([m["flux_obs"] for m in matches])
        weights = weights / np.sum(weights)

        # Weighted median
        ra_offset = _weighted_median(ra_offsets, weights)
        dec_offset = _weighted_median(dec_offsets, weights)
    else:
        ra_offset = np.median(ra_offsets)
        dec_offset = np.median(dec_offsets)

    # Calculate uncertainties (MAD estimator)
    ra_offset_err = 1.4826 * np.median(np.abs(ra_offsets - ra_offset))
    dec_offset_err = 1.4826 * np.median(np.abs(dec_offsets - dec_offset))

    # Calculate RMS residual after offset correction
    ra_residuals = ra_offsets - ra_offset
    dec_residuals = dec_offsets - dec_offset
    rms_residual = np.sqrt(np.mean(ra_residuals**2 + dec_residuals**2))

    solution = {
        "n_matches": len(matches),
        "ra_offset_mas": float(ra_offset),
        "dec_offset_mas": float(dec_offset),
        "ra_offset_err_mas": float(ra_offset_err),
        "dec_offset_err_mas": float(dec_offset_err),
        "rms_residual_mas": float(rms_residual),
        "matches": matches,
    }

    logger.info(
        f"Astrometric solution: RA offset = {ra_offset:.1f} ± {ra_offset_err:.1f} mas, "
        f"Dec offset = {dec_offset:.1f} ± {dec_offset_err:.1f} mas, "
        f"RMS = {rms_residual:.1f} mas"
    )

    return solution


def _weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    """Calculate weighted median.

    Args:
        values: Array of values
        weights: Array of weights (must sum to 1)

    Returns:
        Weighted median value
    """
    sorted_indices = np.argsort(values)
    sorted_values = values[sorted_indices]
    sorted_weights = weights[sorted_indices]

    cumulative_weights = np.cumsum(sorted_weights)
    median_idx = np.searchsorted(cumulative_weights, 0.5)

    return float(sorted_values[median_idx])


def store_astrometric_solution(
    solution: Dict,
    mosaic_id: int,
    reference_catalog: str = "FIRST",
    db_path: str = "/data/dsa110-contimg/state/db/pipeline.sqlite3",
) -> Optional[int]:
    """Store astrometric solution in database.

    Args:
        solution: Solution dictionary from calculate_astrometric_offsets()
        mosaic_id: Associated mosaic product ID
        reference_catalog: Name of reference catalog
        db_path: Path to products database

    Returns:
        Solution ID, or None if failed
    """
    conn = sqlite3.connect(db_path, timeout=30.0)
    cur = conn.cursor()

    current_time = time.time()

    try:
        # Store solution
        cur.execute(
            """
            INSERT INTO astrometric_solutions (
                mosaic_id, reference_catalog, n_matches,
                ra_offset_mas, dec_offset_mas,
                ra_offset_err_mas, dec_offset_err_mas,
                rms_residual_mas, computed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                mosaic_id,
                reference_catalog,
                solution["n_matches"],
                solution["ra_offset_mas"],
                solution["dec_offset_mas"],
                solution["ra_offset_err_mas"],
                solution["dec_offset_err_mas"],
                solution["rms_residual_mas"],
                current_time,
            ),
        )

        solution_id = cur.lastrowid

        # Store individual residuals
        for match in solution.get("matches", []):
            cur.execute(
                """
                INSERT INTO astrometric_residuals (
                    solution_id, source_ra_deg, source_dec_deg,
                    reference_ra_deg, reference_dec_deg,
                    ra_offset_mas, dec_offset_mas, separation_mas,
                    source_flux_mjy, reference_flux_mjy, measured_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    solution_id,
                    match["ra_obs"],
                    match["dec_obs"],
                    match["ra_ref"],
                    match["dec_ref"],
                    match["ra_offset_mas"],
                    match["dec_offset_mas"],
                    match["separation_mas"],
                    match["flux_obs"],
                    match["flux_ref"],
                    current_time,
                ),
            )

        conn.commit()
        logger.info(f"Stored astrometric solution {solution_id}")
        return solution_id

    except Exception as e:
        logger.error(f"Error storing astrometric solution: {e}")
        return None
    finally:
        conn.close()


def apply_wcs_correction(
    ra_offset_mas: float,
    dec_offset_mas: float,
    fits_path: str,
) -> bool:
    """Apply astrometric correction to FITS WCS headers.

    Updates CRVAL1/CRVAL2 in FITS header to correct systematic offsets.

    Args:
        ra_offset_mas: RA offset to apply [mas]
        dec_offset_mas: Dec offset to apply [mas]
        fits_path: Path to FITS file to update

    Returns:
        True if successful
    """
    try:
        from astropy.io import fits

        # Convert offsets to degrees
        ra_offset_deg = ra_offset_mas / (3600.0 * 1000.0)
        dec_offset_deg = dec_offset_mas / (3600.0 * 1000.0)

        # Update FITS header
        with fits.open(fits_path, mode="update") as hdul:
            header = hdul[0].header

            # Get current CRVAL
            crval1 = header.get("CRVAL1", 0.0)
            crval2 = header.get("CRVAL2", 0.0)

            # Apply correction (subtract offset, since offset = observed - reference)
            crval1_new = crval1 - ra_offset_deg / np.cos(np.radians(crval2))
            crval2_new = crval2 - dec_offset_deg

            # Update header
            header["CRVAL1"] = crval1_new
            header["CRVAL2"] = crval2_new

            # Add history
            header.add_history(
                f"Astrometric correction applied: "
                f"RA offset = {ra_offset_mas:.1f} mas, "
                f"Dec offset = {dec_offset_mas:.1f} mas"
            )

            hdul.flush()

        logger.info(f"Applied astrometric correction to {fits_path}")
        return True

    except Exception as e:
        logger.error(f"Error applying WCS correction: {e}")
        return False


def mark_solution_applied(
    solution_id: int,
    db_path: str = "/data/dsa110-contimg/state/db/pipeline.sqlite3",
) -> bool:
    """Mark astrometric solution as applied.

    Args:
        solution_id: Solution ID
        db_path: Path to products database

    Returns:
        True if successful
    """
    conn = sqlite3.connect(db_path, timeout=30.0)
    cur = conn.cursor()

    try:
        cur.execute(
            """
            UPDATE astrometric_solutions
            SET applied = 1, applied_at = ?
            WHERE id = ?
        """,
            (time.time(), solution_id),
        )

        conn.commit()
        logger.info(f"Marked solution {solution_id} as applied")
        return True

    except Exception as e:
        logger.error(f"Error marking solution applied: {e}")
        return False
    finally:
        conn.close()


def get_astrometric_accuracy_stats(
    time_window_days: Optional[float] = 30.0,
    db_path: str = "/data/dsa110-contimg/state/db/pipeline.sqlite3",
) -> Dict:
    """Get astrometric accuracy statistics.

    Args:
        time_window_days: Time window for statistics [days], None for all time
        db_path: Path to products database

    Returns:
        Dictionary with accuracy statistics
    """
    conn = sqlite3.connect(db_path)

    query = "SELECT * FROM astrometric_solutions"
    params = []

    if time_window_days:
        cutoff_time = time.time() - (time_window_days * 86400.0)
        query += " WHERE computed_at >= ?"
        params.append(cutoff_time)

    query += " ORDER BY computed_at DESC"

    try:
        df = pd.read_sql_query(query, conn, params=params)

        if len(df) == 0:
            return {
                "n_solutions": 0,
                "mean_rms_mas": None,
                "median_rms_mas": None,
                "mean_ra_offset_mas": None,
                "mean_dec_offset_mas": None,
            }

        stats = {
            "n_solutions": len(df),
            "mean_rms_mas": float(df["rms_residual_mas"].mean()),
            "median_rms_mas": float(df["rms_residual_mas"].median()),
            "mean_ra_offset_mas": float(df["ra_offset_mas"].mean()),
            "mean_dec_offset_mas": float(df["dec_offset_mas"].mean()),
            "std_ra_offset_mas": float(df["ra_offset_mas"].std()),
            "std_dec_offset_mas": float(df["dec_offset_mas"].std()),
            "mean_n_matches": float(df["n_matches"].mean()),
        }

        return stats

    finally:
        conn.close()


def get_recent_astrometric_solutions(
    limit: int = 10,
    db_path: str = "/data/dsa110-contimg/state/db/pipeline.sqlite3",
) -> pd.DataFrame:
    """Get recent astrometric solutions.

    Args:
        limit: Maximum number of solutions to return
        db_path: Path to products database

    Returns:
        DataFrame with solution information
    """
    conn = sqlite3.connect(db_path)

    query = """
        SELECT * FROM astrometric_solutions
        ORDER BY computed_at DESC
        LIMIT ?
    """

    try:
        df = pd.read_sql_query(query, conn, params=[limit])
        return df
    finally:
        conn.close()
