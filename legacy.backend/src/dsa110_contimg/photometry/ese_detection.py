"""ESE (Extreme Scattering Event) detection from variability statistics.

This module provides functions to detect ESE candidates by analyzing
variability statistics computed from photometry measurements.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path
from typing import List, Optional

import numpy as np

from dsa110_contimg.photometry.scoring import (
    calculate_composite_score,
    get_confidence_level,
)
from dsa110_contimg.photometry.variability import calculate_sigma_deviation

logger = logging.getLogger(__name__)


def detect_ese_candidates(
    products_db: Path,
    min_sigma: float = 5.0,
    source_id: Optional[str] = None,
    recompute: bool = False,
    use_composite_scoring: bool = False,
    scoring_weights: Optional[dict] = None,
) -> List[dict]:
    """Detect ESE candidates from variability statistics.

    Queries the variability_stats table for sources with sigma_deviation >= min_sigma
    and flags them as ESE candidates in the ese_candidates table.

    Args:
        products_db: Path to products database
        min_sigma: Minimum sigma deviation threshold (default: 5.0)
        source_id: Optional specific source ID to check (if None, checks all sources)
        recompute: If True, recompute variability stats before detection
        use_composite_scoring: If True, compute composite score from multiple metrics
        scoring_weights: Optional custom weights for composite scoring

    Returns:
        List of detected ESE candidate dictionaries with source_id, significance, etc.
        If use_composite_scoring is True, includes 'composite_score' and 'confidence_level'.
    """
    if not products_db.exists():
        logger.warning(f"Products database not found: {products_db}")
        return []

    conn = sqlite3.connect(products_db, timeout=30.0)
    conn.row_factory = sqlite3.Row

    try:
        # Ensure tables exist
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }

        if "variability_stats" not in tables:
            logger.warning("variability_stats table not found in database")
            return []

        if "ese_candidates" not in tables:
            logger.warning("ese_candidates table not found - creating it")
            from dsa110_contimg.database.schema_evolution import evolve_schema

            evolve_schema(products_db, verbose=False)

        # If recompute requested, update variability stats first
        if recompute:
            logger.info("Recomputing variability statistics...")
            _recompute_variability_stats(conn)

        # Query for sources with high variability
        # Include eta_metric if available for composite scoring
        if source_id:
            query = """
                SELECT 
                    source_id,
                    ra_deg,
                    dec_deg,
                    nvss_flux_mjy,
                    mean_flux_mjy,
                    std_flux_mjy,
                    chi2_nu,
                    sigma_deviation,
                    eta_metric,
                    n_obs,
                    last_mjd
                FROM variability_stats
                WHERE source_id = ? AND sigma_deviation >= ?
            """
            params = (source_id, min_sigma)
        else:
            query = """
                SELECT 
                    source_id,
                    ra_deg,
                    dec_deg,
                    nvss_flux_mjy,
                    mean_flux_mjy,
                    std_flux_mjy,
                    chi2_nu,
                    sigma_deviation,
                    eta_metric,
                    n_obs,
                    last_mjd
                FROM variability_stats
                WHERE sigma_deviation >= ?
                ORDER BY sigma_deviation DESC
            """
            params = (min_sigma,)

        rows = conn.execute(query, params).fetchall()

        if not rows:
            logger.info(f"No sources found with sigma_deviation >= {min_sigma}")
            return []

        detected = []
        flagged_at = time.time()

        for row in rows:
            source_id_val = row["source_id"]
            significance = float(row["sigma_deviation"])

            # Compute composite score if enabled
            composite_score = None
            confidence_level = None
            if use_composite_scoring:
                metrics = {
                    "sigma_deviation": significance,
                }

                # Add chi2_nu if available
                if row["chi2_nu"] is not None:
                    metrics["chi2_nu"] = float(row["chi2_nu"])

                # Add eta_metric if available
                if row.get("eta_metric") is not None:
                    metrics["eta_metric"] = float(row["eta_metric"])

                if metrics:
                    composite_score = calculate_composite_score(
                        metrics,
                        weights=scoring_weights,
                        normalize=True,
                    )
                    confidence_level = get_confidence_level(composite_score)

            # Check if already flagged
            existing = conn.execute(
                """
                SELECT id, status FROM ese_candidates 
                WHERE source_id = ? AND status = 'active'
                """,
                (source_id_val,),
            ).fetchone()

            if existing:
                # Update existing candidate if significance increased
                if significance > min_sigma:
                    conn.execute(
                        """
                        UPDATE ese_candidates
                        SET significance = ?, flagged_at = ?, flag_type = 'auto'
                        WHERE id = ?
                        """,
                        (significance, flagged_at, existing["id"]),
                    )
                    logger.debug(
                        f"Updated ESE candidate {source_id_val} "
                        f"(significance: {significance:.2f})"
                    )
                else:
                    logger.debug(f"Skipping {source_id_val} - already flagged as active candidate")
                    continue
            else:
                # Insert new candidate
                conn.execute(
                    """
                    INSERT INTO ese_candidates 
                    (source_id, flagged_at, flagged_by, significance, flag_type, status)
                    VALUES (?, ?, 'auto', ?, 'auto', 'active')
                    """,
                    (source_id_val, flagged_at, significance),
                )
                logger.info(
                    f"Flagged ESE candidate {source_id_val} " f"(significance: {significance:.2f})"
                )

            candidate_dict = {
                "source_id": source_id_val,
                "ra_deg": float(row["ra_deg"]),
                "dec_deg": float(row["dec_deg"]),
                "significance": significance,
                "nvss_flux_mjy": float(row["nvss_flux_mjy"]) if row["nvss_flux_mjy"] else None,
                "mean_flux_mjy": float(row["mean_flux_mjy"]) if row["mean_flux_mjy"] else None,
                "std_flux_mjy": float(row["std_flux_mjy"]) if row["std_flux_mjy"] else None,
                "chi2_nu": float(row["chi2_nu"]) if row["chi2_nu"] else None,
                "n_obs": int(row["n_obs"]),
                "last_mjd": float(row["last_mjd"]) if row["last_mjd"] else None,
            }

            # Add composite scoring fields if enabled
            if use_composite_scoring and composite_score is not None:
                candidate_dict["composite_score"] = composite_score
                candidate_dict["confidence_level"] = confidence_level

            detected.append(candidate_dict)

        conn.commit()
        logger.info(f"Detected {len(detected)} ESE candidates")

        # Hook: Update ESE candidate dashboard after detection
        if detected:
            try:
                from dsa110_contimg.qa.pipeline_hooks import hook_ese_detection_complete

                hook_ese_detection_complete()
            except Exception as e:
                logger.debug(f"ESE dashboard update hook failed: {e}")

        return detected

    except Exception as e:
        logger.error(f"Error detecting ESE candidates: {e}", exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()


def _recompute_variability_stats(conn: sqlite3.Connection) -> None:
    """Recompute variability statistics from photometry measurements.

    This function queries the photometry table and computes variability
    statistics for all sources, updating the variability_stats table.

    Args:
        conn: Database connection
    """
    # Check if photometry table exists
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }

    if "photometry" not in tables:
        logger.warning("photometry table not found - cannot recompute stats")
        return

    # Get all unique sources from photometry
    sources = conn.execute(
        """
        SELECT DISTINCT source_id 
        FROM photometry 
        WHERE source_id IS NOT NULL
        """
    ).fetchall()

    logger.info(f"Recomputing variability stats for {len(sources)} sources...")

    for (source_id,) in sources:
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

        if len(rows) < 2:
            continue

        # Compute statistics
        fluxes = [float(r["peak_jyb"]) for r in rows if r["peak_jyb"] is not None]
        if len(fluxes) < 2:
            continue

        mean_flux = np.mean(fluxes)
        std_flux = np.std(fluxes)
        min_flux = np.min(fluxes)
        max_flux = np.max(fluxes)
        n_obs = len(fluxes)

        # Compute chi2_nu (reduced chi-squared)
        errors = [
            float(r["peak_err_jyb"])
            for r in rows
            if r["peak_err_jyb"] is not None and r["peak_jyb"] is not None
        ]
        if len(errors) == len(fluxes) and all(e > 0 for e in errors):
            chi2 = np.sum(((np.array(fluxes) - mean_flux) ** 2) / (np.array(errors) ** 2))
            chi2_nu = chi2 / (len(fluxes) - 1) if len(fluxes) > 1 else 0.0
        else:
            chi2_nu = None

        # Compute sigma deviation (how many sigma away from mean)
        # This measures the maximum deviation from the mean in units of standard deviation
        try:
            sigma_deviation = calculate_sigma_deviation(
                np.array(fluxes), mean=mean_flux, std=std_flux
            )
        except ValueError:
            # Handle edge case: empty array or all NaN
            sigma_deviation = 0.0

        # Get first row for position and NVSS flux
        first_row = rows[0]
        ra_deg = float(first_row["ra_deg"])
        dec_deg = float(first_row["dec_deg"])
        nvss_flux_mjy = (
            float(first_row["nvss_flux_mjy"]) * 1000.0
            if first_row["nvss_flux_mjy"] is not None
            else None
        )

        # Get last measurement time
        last_row = rows[-1]
        last_measured_at = (
            float(last_row["measured_at"]) if last_row["measured_at"] else time.time()
        )
        last_mjd = float(last_row["mjd"]) if last_row["mjd"] else None

        # Upsert variability stats
        conn.execute(
            """
            INSERT INTO variability_stats 
            (source_id, ra_deg, dec_deg, nvss_flux_mjy, n_obs, mean_flux_mjy, 
             std_flux_mjy, min_flux_mjy, max_flux_mjy, chi2_nu, sigma_deviation,
             last_measured_at, last_mjd, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                n_obs = excluded.n_obs,
                mean_flux_mjy = excluded.mean_flux_mjy,
                std_flux_mjy = excluded.std_flux_mjy,
                min_flux_mjy = excluded.min_flux_mjy,
                max_flux_mjy = excluded.max_flux_mjy,
                chi2_nu = excluded.chi2_nu,
                sigma_deviation = excluded.sigma_deviation,
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
                mean_flux * 1000.0,  # Convert to mJy
                std_flux * 1000.0,
                min_flux * 1000.0,
                max_flux * 1000.0,
                chi2_nu,
                sigma_deviation,
                last_measured_at,
                last_mjd,
                time.time(),
            ),
        )

    conn.commit()
    logger.info("Finished recomputing variability statistics")
