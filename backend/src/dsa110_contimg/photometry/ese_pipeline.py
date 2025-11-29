"""Automated ESE detection pipeline integration.

This module provides functions to automatically compute variability statistics
and detect ESE candidates after photometry measurements are completed.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path
from typing import List, Optional

from dsa110_contimg.database.products import ensure_products_db
from dsa110_contimg.photometry.caching import (
    invalidate_cache,
)
from dsa110_contimg.photometry.ese_detection import detect_ese_candidates
from dsa110_contimg.photometry.variability import (
    calculate_eta_metric,
    calculate_sigma_deviation,
)

logger = logging.getLogger(__name__)


def update_variability_stats_for_source(
    conn: sqlite3.Connection,
    source_id: str,
    use_cache: bool = True,
    cache_ttl: int = 3600,
    products_db: Optional[Path] = None,
) -> bool:
    """Update variability statistics for a single source from photometry measurements.

    Args:
        conn: Database connection
        source_id: Source ID to update
        use_cache: If True, check cache before recomputing (default: True)
        cache_ttl: Cache time-to-live in seconds (default: 3600)

    Returns:
        True if stats were updated, False otherwise
    """
    # Check if photometry table exists
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }

    if "photometry" not in tables:
        logger.debug(f"photometry table not found - skipping variability stats for {source_id}")
        return False

    # Check cache first if enabled
    if use_cache:
        # Get database path from connection (approximate)
        # Note: SQLite connections don't expose the path directly, so we'll skip cache check
        # for now and rely on database-level caching in get_cached_variability_stats
        pass

    # Get photometry history for this source
    rows = conn.execute(
        """
        SELECT 
            ra_deg,
            dec_deg,
            nvss_flux_mjy,
            peak_jyb,
            peak_err_jyb,
            measured_at,
            mjd
        FROM photometry
        WHERE source_id = ?
        ORDER BY measured_at
        """,
        (source_id,),
    ).fetchall()

    if not rows:
        logger.debug(f"No photometry data found for source {source_id}")
        return False

    # Convert to DataFrame-like structure for calculations
    import pandas as pd

    df = pd.DataFrame(
        rows,
        columns=[
            "ra_deg",
            "dec_deg",
            "nvss_flux_mjy",
            "peak_jyb",
            "peak_err_jyb",
            "measured_at",
            "mjd",
        ],
    )

    # Use first row for position and NVSS flux
    ra_deg = df["ra_deg"].iloc[0]
    dec_deg = df["dec_deg"].iloc[0]
    nvss_flux_mjy = (
        df["nvss_flux_mjy"].iloc[0] if not pd.isna(df["nvss_flux_mjy"].iloc[0]) else None
    )

    # Convert peak_jyb to mJy for consistency
    flux_mjy = df["peak_jyb"].values * 1000.0  # Jy to mJy
    flux_err_mjy = df["peak_err_jyb"].values * 1000.0 if "peak_err_jyb" in df.columns else None

    # Normalize flux by NVSS if available
    if nvss_flux_mjy is not None and nvss_flux_mjy > 0:
        normalized_flux = flux_mjy / nvss_flux_mjy
        normalized_err = flux_err_mjy / nvss_flux_mjy if flux_err_mjy is not None else None
    else:
        normalized_flux = flux_mjy
        normalized_err = flux_err_mjy

    # Calculate statistics
    n_obs = len(df)
    mean_flux_mjy = float(flux_mjy.mean())
    std_flux_mjy = float(flux_mjy.std())
    min_flux_mjy = float(flux_mjy.min())
    max_flux_mjy = float(flux_mjy.max())

    # Calculate chi2_nu (chi-squared per degree of freedom)
    if normalized_err is not None and (normalized_err > 0).any():
        chi2 = ((normalized_flux - normalized_flux.mean()) ** 2 / (normalized_err**2)).sum()
        chi2_nu = float(chi2 / (n_obs - 1)) if n_obs > 1 else 0.0
    else:
        chi2_nu = None

    # Calculate eta metric (weighted variance)
    if normalized_err is not None:
        df_normalized = pd.DataFrame(
            {
                "normalized_flux_jy": normalized_flux,
                "normalized_flux_err_jy": normalized_err,
            }
        )
        eta_metric = calculate_eta_metric(df_normalized)
    else:
        eta_metric = None

    # Calculate sigma deviation (how many sigma away from mean)
    try:
        # Handle both pandas Series and numpy arrays
        flux_array = flux_mjy.values if hasattr(flux_mjy, "values") else flux_mjy
        sigma_deviation = calculate_sigma_deviation(
            flux_array, mean=mean_flux_mjy, std=std_flux_mjy
        )
    except ValueError:
        # Handle edge case: empty array or all NaN
        sigma_deviation = 0.0

    # Get last measurement time
    last_measured_at = float(df["measured_at"].max())
    last_mjd = (
        float(df["mjd"].max()) if "mjd" in df.columns and not df["mjd"].isna().all() else None
    )
    updated_at = time.time()

    # Insert or update variability_stats
    conn.execute(
        """
        INSERT INTO variability_stats 
        (source_id, ra_deg, dec_deg, nvss_flux_mjy, n_obs, mean_flux_mjy,
         std_flux_mjy, min_flux_mjy, max_flux_mjy, chi2_nu, sigma_deviation,
         eta_metric, last_measured_at, last_mjd, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_id) DO UPDATE SET
            n_obs = excluded.n_obs,
            mean_flux_mjy = excluded.mean_flux_mjy,
            std_flux_mjy = excluded.std_flux_mjy,
            min_flux_mjy = excluded.min_flux_mjy,
            max_flux_mjy = excluded.max_flux_mjy,
            chi2_nu = excluded.chi2_nu,
            sigma_deviation = excluded.sigma_deviation,
            eta_metric = excluded.eta_metric,
            last_measured_at = excluded.last_measured_at,
            last_mjd = excluded.last_mjd,
            updated_at = excluded.updated_at
        """,
        (
            source_id,
            ra_deg,
            dec_deg,
            nvss_flux_mjy,
            n_obs,
            mean_flux_mjy,
            std_flux_mjy,
            min_flux_mjy,
            max_flux_mjy,
            chi2_nu,
            sigma_deviation,
            eta_metric,
            last_measured_at,
            last_mjd,
            updated_at,
        ),
    )

    logger.debug(
        f"Updated variability stats for source {source_id}: sigma_deviation={sigma_deviation:.2f}"
    )

    # Invalidate cache for this source since we just updated stats
    # Only invalidate if products_db is provided (cache needs it for key generation)
    if products_db:
        invalidate_cache(source_id, products_db)

    return True


def auto_detect_ese_after_photometry(
    products_db: Path,
    source_ids: Optional[List[str]] = None,
    min_sigma: float = 5.0,
    update_variability_stats: bool = True,
) -> List[dict]:
    """Automatically detect ESE candidates after photometry measurements.

    This function:
    1. Updates variability statistics for specified sources (or all sources)
    2. Detects ESE candidates based on updated statistics

    Args:
        products_db: Path to products database
        source_ids: Optional list of source IDs to process (if None, processes all)
        min_sigma: Minimum sigma deviation threshold for ESE detection
        update_variability_stats: If True, update variability stats before detection

    Returns:
        List of detected ESE candidate dictionaries
    """
    if not products_db.exists():
        logger.warning(f"Products database not found: {products_db}")
        return []

    conn = ensure_products_db(products_db)

    try:
        # Ensure tables exist
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }

        if "photometry" not in tables:
            logger.debug("photometry table not found - skipping ESE detection")
            return []

        if "variability_stats" not in tables:
            logger.debug("variability_stats table not found - creating schema")
            from dsa110_contimg.database.schema_evolution import evolve_schema

            evolve_schema(products_db, verbose=False)

        # Update variability stats for sources
        if update_variability_stats:
            if source_ids:
                # Update specific sources
                for source_id in source_ids:
                    try:
                        update_variability_stats_for_source(
                            conn, source_id, products_db=products_db
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update variability stats for {source_id}: {e}")
            else:
                # Update all sources with photometry data
                source_rows = conn.execute(
                    """
                    SELECT DISTINCT source_id 
                    FROM photometry 
                    WHERE source_id IS NOT NULL
                    """
                ).fetchall()

                logger.info(f"Updating variability stats for {len(source_rows)} sources...")
                for (source_id,) in source_rows:
                    try:
                        update_variability_stats_for_source(
                            conn, source_id, products_db=products_db
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update variability stats for {source_id}: {e}")

            conn.commit()

        # Detect ESE candidates
        candidates = detect_ese_candidates(
            products_db=products_db,
            min_sigma=min_sigma,
            source_id=None if not source_ids else source_ids[0] if len(source_ids) == 1 else None,
            recompute=False,  # Already updated above
        )

        logger.info(f"Auto-detected {len(candidates)} ESE candidates")
        return candidates

    except Exception as e:
        logger.error(f"Error in auto ESE detection: {e}", exc_info=True)
        return []
    finally:
        conn.close()


def auto_detect_ese_for_new_measurements(
    products_db: Path,
    source_id: str,
    min_sigma: float = 5.0,
) -> Optional[dict]:
    """Automatically detect ESE candidate for a single source after new measurement.

    This is optimized for single-source updates after a new photometry measurement.

    Args:
        products_db: Path to products database
        source_id: Source ID that was just measured
        min_sigma: Minimum sigma deviation threshold

    Returns:
        ESE candidate dict if detected, None otherwise
    """
    if not products_db.exists():
        return None

    conn = ensure_products_db(products_db)

    try:
        # Update variability stats for this source
        updated = update_variability_stats_for_source(conn, source_id, products_db=products_db)
        if not updated:
            return None

        conn.commit()

        # Check if this source qualifies as ESE candidate
        row = conn.execute(
            """
            SELECT sigma_deviation 
            FROM variability_stats 
            WHERE source_id = ?
            """,
            (source_id,),
        ).fetchone()

        if not row or row[0] < min_sigma:
            return None

        # Detect ESE candidate for this source
        candidates = detect_ese_candidates(
            products_db=products_db,
            min_sigma=min_sigma,
            source_id=source_id,
            recompute=False,
        )

        return candidates[0] if candidates else None

    except Exception as e:
        logger.warning(f"Error in auto ESE detection for {source_id}: {e}")
        return None
    finally:
        conn.close()
