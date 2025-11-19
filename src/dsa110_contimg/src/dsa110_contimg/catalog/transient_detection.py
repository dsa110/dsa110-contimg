"""Transient detection module for DSA-110 continuum imaging pipeline.

This module provides functions to detect transient and variable radio sources
by comparing current observations with baseline catalogs (NVSS, FIRST).

Implements Proposal #2: Transient Detection & Classification
"""

import logging
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def create_transient_detection_tables(
    db_path: str = "/data/dsa110-contimg/state/products.sqlite3",
) -> bool:
    """Create database tables for transient detection.

    Tables created:
    - transient_candidates: Detected transient/variable sources
    - transient_alerts: High-priority alerts for follow-up
    - transient_lightcurves: Flux measurements over time

    Args:
        db_path: Path to products database

    Returns:
        True if successful
    """
    conn = sqlite3.connect(db_path, timeout=30.0)
    cur = conn.cursor()

    try:
        # Main transient candidates table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transient_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT NOT NULL,
                ra_deg REAL NOT NULL,
                dec_deg REAL NOT NULL,
                detection_type TEXT NOT NULL,
                flux_obs_mjy REAL NOT NULL,
                flux_baseline_mjy REAL,
                flux_ratio REAL,
                significance_sigma REAL NOT NULL,
                baseline_catalog TEXT,
                detected_at REAL NOT NULL,
                mosaic_id INTEGER,
                classification TEXT,
                variability_index REAL,
                last_updated REAL NOT NULL,
                notes TEXT,
                FOREIGN KEY (mosaic_id) REFERENCES products(id)
            )
        """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_transients_type 
            ON transient_candidates(detection_type, significance_sigma DESC)
        """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_transients_coords 
            ON transient_candidates(ra_deg, dec_deg)
        """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_transients_detected 
            ON transient_candidates(detected_at DESC)
        """
        )

        # High-priority alerts table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transient_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                alert_level TEXT NOT NULL,
                alert_message TEXT NOT NULL,
                created_at REAL NOT NULL,
                acknowledged BOOLEAN DEFAULT 0,
                acknowledged_at REAL,
                acknowledged_by TEXT,
                follow_up_status TEXT,
                notes TEXT,
                FOREIGN KEY (candidate_id) REFERENCES transient_candidates(id)
            )
        """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_alerts_level 
            ON transient_alerts(alert_level, created_at DESC)
        """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_alerts_status 
            ON transient_alerts(acknowledged, created_at DESC)
        """
        )

        # Lightcurve measurements table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transient_lightcurves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                mjd REAL NOT NULL,
                flux_mjy REAL NOT NULL,
                flux_err_mjy REAL,
                frequency_ghz REAL NOT NULL,
                mosaic_id INTEGER,
                measured_at REAL NOT NULL,
                FOREIGN KEY (candidate_id) REFERENCES transient_candidates(id),
                FOREIGN KEY (mosaic_id) REFERENCES products(id)
            )
        """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_lightcurves_candidate 
            ON transient_lightcurves(candidate_id, mjd)
        """
        )

        conn.commit()
        logger.info("Created transient detection tables")
        return True

    except Exception as e:
        logger.error(f"Error creating transient detection tables: {e}")
        return False
    finally:
        conn.close()


def detect_transients(
    observed_sources: pd.DataFrame,
    baseline_sources: pd.DataFrame,
    detection_threshold_sigma: float = 5.0,
    variability_threshold: float = 3.0,
    match_radius_arcsec: float = 10.0,
    baseline_catalog: str = "NVSS",
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Detect transient and variable sources.

    Compares observed sources with baseline catalog to find:
    1. New sources (not in baseline, significant detection)
    2. Variable sources (flux significantly changed)
    3. Fading sources (baseline source not detected)

    Args:
        observed_sources: DataFrame with columns: ra_deg, dec_deg, flux_mjy, flux_err_mjy
        baseline_sources: DataFrame with columns: ra_deg, dec_deg, flux_mjy
        detection_threshold_sigma: Significance threshold for new sources [sigma]
        variability_threshold: Threshold for flux variability [sigma]
        match_radius_arcsec: Matching radius [arcsec]
        baseline_catalog: Name of baseline catalog

    Returns:
        Tuple of (new_sources, variable_sources, fading_sources) as lists of dicts
    """
    new_sources = []
    variable_sources = []
    fading_sources = []

    if len(observed_sources) == 0:
        logger.warning("No observed sources provided")
        return new_sources, variable_sources, fading_sources

    if len(baseline_sources) == 0:
        logger.warning("No baseline sources provided")
        # All observed sources are "new" if no baseline
        for _, obs in observed_sources.iterrows():
            if obs.get("flux_err_mjy", 0) > 0:
                significance = obs["flux_mjy"] / obs["flux_err_mjy"]
                if significance >= detection_threshold_sigma:
                    new_sources.append(
                        {
                            "ra_deg": obs["ra_deg"],
                            "dec_deg": obs["dec_deg"],
                            "flux_obs_mjy": obs["flux_mjy"],
                            "flux_baseline_mjy": None,
                            "significance_sigma": significance,
                            "detection_type": "new",
                        }
                    )
        return new_sources, variable_sources, fading_sources

    # Cross-match observed with baseline
    match_radius_deg = match_radius_arcsec / 3600.0

    for _, obs in observed_sources.iterrows():
        ra_obs = obs["ra_deg"]
        dec_obs = obs["dec_deg"]
        flux_obs = obs["flux_mjy"]
        flux_err_obs = obs.get("flux_err_mjy", flux_obs * 0.1)  # 10% default if not provided

        # Find closest baseline source
        ra_diff = (baseline_sources["ra_deg"] - ra_obs) * np.cos(np.radians(dec_obs))
        dec_diff = baseline_sources["dec_deg"] - dec_obs
        separation = np.sqrt(ra_diff**2 + dec_diff**2)

        closest_idx = np.argmin(separation)
        closest_sep = separation.iloc[closest_idx]

        if closest_sep <= match_radius_deg:
            # Matched to baseline source
            baseline_source = baseline_sources.iloc[closest_idx]
            flux_baseline = baseline_source["flux_mjy"]

            # Check for variability
            flux_ratio = flux_obs / flux_baseline if flux_baseline > 0 else np.inf
            flux_diff = flux_obs - flux_baseline

            # Significance of variability
            # Assume baseline has ~5% uncertainty
            flux_err_baseline = flux_baseline * 0.05
            flux_err_total = np.sqrt(flux_err_obs**2 + flux_err_baseline**2)

            if flux_err_total > 0:
                variability_sigma = abs(flux_diff) / flux_err_total

                if variability_sigma >= variability_threshold:
                    # Significant variability detected
                    if flux_ratio > 1.5:
                        detection_type = "brightening"
                    elif flux_ratio < 0.67:
                        detection_type = "fading"
                    else:
                        detection_type = "variable"

                    variable_sources.append(
                        {
                            "ra_deg": ra_obs,
                            "dec_deg": dec_obs,
                            "flux_obs_mjy": flux_obs,
                            "flux_baseline_mjy": flux_baseline,
                            "flux_ratio": flux_ratio,
                            "significance_sigma": variability_sigma,
                            "detection_type": detection_type,
                            "separation_arcsec": closest_sep * 3600.0,
                        }
                    )
        else:
            # No match in baseline - potential new source
            if flux_err_obs > 0:
                significance = flux_obs / flux_err_obs

                if significance >= detection_threshold_sigma:
                    new_sources.append(
                        {
                            "ra_deg": ra_obs,
                            "dec_deg": dec_obs,
                            "flux_obs_mjy": flux_obs,
                            "flux_baseline_mjy": None,
                            "significance_sigma": significance,
                            "detection_type": "new",
                        }
                    )

    # Check for fading sources (baseline sources not detected)
    for _, baseline in baseline_sources.iterrows():
        ra_base = baseline["ra_deg"]
        dec_base = baseline["dec_deg"]
        flux_base = baseline["flux_mjy"]

        # Find if observed
        ra_diff = (observed_sources["ra_deg"] - ra_base) * np.cos(np.radians(dec_base))
        dec_diff = observed_sources["dec_deg"] - dec_base
        separation = np.sqrt(ra_diff**2 + dec_diff**2)

        if len(separation) > 0:
            closest_sep = np.min(separation)

            if closest_sep > match_radius_deg:
                # Baseline source not detected - potential fading source
                # Only flag if baseline flux was significant
                if flux_base >= 10.0:  # 10 mJy threshold for fading detection
                    fading_sources.append(
                        {
                            "ra_deg": ra_base,
                            "dec_deg": dec_base,
                            "flux_obs_mjy": 0.0,
                            "flux_baseline_mjy": flux_base,
                            "flux_ratio": 0.0,
                            "significance_sigma": flux_base / (flux_base * 0.05),  # Rough estimate
                            "detection_type": "fading",
                        }
                    )

    logger.info(
        f"Transient detection: {len(new_sources)} new, "
        f"{len(variable_sources)} variable, {len(fading_sources)} fading"
    )

    return new_sources, variable_sources, fading_sources


def store_transient_candidates(
    candidates: List[Dict],
    baseline_catalog: str = "NVSS",
    mosaic_id: Optional[int] = None,
    db_path: str = "/data/dsa110-contimg/state/products.sqlite3",
) -> List[int]:
    """Store transient candidates in database.

    Args:
        candidates: List of candidate dictionaries from detect_transients()
        baseline_catalog: Name of baseline catalog
        mosaic_id: Associated mosaic product ID
        db_path: Path to products database

    Returns:
        List of candidate IDs
    """
    conn = sqlite3.connect(db_path, timeout=30.0)
    cur = conn.cursor()

    candidate_ids = []
    current_time = time.time()

    try:
        for candidate in candidates:
            # Generate source name
            ra = candidate["ra_deg"]
            dec = candidate["dec_deg"]
            source_name = f"DSA_TRANSIENT_J{ra:08.4f}{dec:+09.4f}".replace(".", "")

            # Calculate variability index if applicable
            variability_index = None
            if candidate.get("flux_baseline_mjy") and candidate.get("flux_obs_mjy"):
                flux_ratio = candidate["flux_obs_mjy"] / candidate["flux_baseline_mjy"]
                variability_index = abs(np.log10(flux_ratio))

            cur.execute(
                """
                INSERT INTO transient_candidates (
                    source_name, ra_deg, dec_deg, detection_type,
                    flux_obs_mjy, flux_baseline_mjy, flux_ratio,
                    significance_sigma, baseline_catalog, detected_at,
                    mosaic_id, variability_index, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    source_name,
                    candidate["ra_deg"],
                    candidate["dec_deg"],
                    candidate["detection_type"],
                    candidate["flux_obs_mjy"],
                    candidate.get("flux_baseline_mjy"),
                    candidate.get("flux_ratio"),
                    candidate["significance_sigma"],
                    baseline_catalog,
                    current_time,
                    mosaic_id,
                    variability_index,
                    current_time,
                ),
            )

            candidate_ids.append(cur.lastrowid)

        conn.commit()
        logger.info(f"Stored {len(candidate_ids)} transient candidates")
        return candidate_ids

    except Exception as e:
        logger.error(f"Error storing transient candidates: {e}")
        return []
    finally:
        conn.close()


def generate_transient_alerts(
    candidate_ids: List[int],
    alert_threshold_sigma: float = 7.0,
    db_path: str = "/data/dsa110-contimg/state/products.sqlite3",
) -> List[int]:
    """Generate alerts for high-priority transient candidates.

    Alert levels:
    - CRITICAL: >10σ detection, new source
    - HIGH: >7σ detection, significant variability
    - MEDIUM: 5-7σ detection

    Args:
        candidate_ids: List of candidate IDs to check
        alert_threshold_sigma: Minimum significance for alerts [sigma]
        db_path: Path to products database

    Returns:
        List of alert IDs created
    """
    conn = sqlite3.connect(db_path, timeout=30.0)
    cur = conn.cursor()

    alert_ids = []
    current_time = time.time()

    try:
        for candidate_id in candidate_ids:
            # Get candidate details
            cur.execute(
                """
                SELECT source_name, detection_type, flux_obs_mjy, flux_baseline_mjy,
                       flux_ratio, significance_sigma
                FROM transient_candidates
                WHERE id = ?
            """,
                (candidate_id,),
            )

            row = cur.fetchone()
            if not row:
                continue

            source_name, detection_type, flux_obs, flux_baseline, flux_ratio, significance = row

            # Determine alert level
            alert_level = None
            alert_message = None

            if significance >= 10.0 and detection_type == "new":
                alert_level = "CRITICAL"
                alert_message = (
                    f"New source {source_name}: {flux_obs:.1f} mJy "
                    f"({significance:.1f}σ detection)"
                )
            elif significance >= alert_threshold_sigma:
                if detection_type in ["brightening", "fading"]:
                    alert_level = "HIGH"
                    action = "brightened" if detection_type == "brightening" else "faded"
                    alert_message = (
                        f"Variable source {source_name}: {action} from "
                        f"{flux_baseline:.1f} to {flux_obs:.1f} mJy "
                        f"({flux_ratio:.2f}×, {significance:.1f}σ)"
                    )
                elif detection_type == "new":
                    alert_level = "HIGH"
                    alert_message = (
                        f"New source {source_name}: {flux_obs:.1f} mJy "
                        f"({significance:.1f}σ detection)"
                    )
                else:
                    alert_level = "MEDIUM"
                    alert_message = (
                        f"Variable source {source_name}: {flux_obs:.1f} mJy "
                        f"({significance:.1f}σ variability)"
                    )

            if alert_level:
                cur.execute(
                    """
                    INSERT INTO transient_alerts (
                        candidate_id, alert_level, alert_message, created_at
                    ) VALUES (?, ?, ?, ?)
                """,
                    (candidate_id, alert_level, alert_message, current_time),
                )

                alert_ids.append(cur.lastrowid)
                logger.info(f"{alert_level} alert: {alert_message}")

        conn.commit()
        logger.info(f"Generated {len(alert_ids)} transient alerts")
        return alert_ids

    except Exception as e:
        logger.error(f"Error generating transient alerts: {e}")
        return []
    finally:
        conn.close()


def get_transient_candidates(
    min_significance: float = 5.0,
    detection_types: Optional[List[str]] = None,
    limit: int = 100,
    db_path: str = "/data/dsa110-contimg/state/products.sqlite3",
) -> pd.DataFrame:
    """Query transient candidates from database.

    Args:
        min_significance: Minimum significance threshold [sigma]
        detection_types: Filter by types (e.g., ['new', 'brightening'])
        limit: Maximum number of candidates to return
        db_path: Path to products database

    Returns:
        DataFrame with candidate information
    """
    conn = sqlite3.connect(db_path)

    query = """
        SELECT * FROM transient_candidates
        WHERE significance_sigma >= ?
    """
    params = [min_significance]

    if detection_types:
        placeholders = ",".join("?" * len(detection_types))
        query += f" AND detection_type IN ({placeholders})"
        params.extend(detection_types)

    query += " ORDER BY significance_sigma DESC LIMIT ?"
    params.append(limit)

    try:
        df = pd.read_sql_query(query, conn, params=params)
        return df
    finally:
        conn.close()


def get_transient_alerts(
    alert_level: Optional[str] = None,
    acknowledged: bool = False,
    limit: int = 50,
    db_path: str = "/data/dsa110-contimg/state/products.sqlite3",
) -> pd.DataFrame:
    """Query transient alerts from database.

    Args:
        alert_level: Filter by level ('CRITICAL', 'HIGH', 'MEDIUM')
        acknowledged: If True, show only acknowledged; if False, show unacknowledged
        limit: Maximum number of alerts to return
        db_path: Path to products database

    Returns:
        DataFrame with alert information
    """
    conn = sqlite3.connect(db_path)

    query = "SELECT * FROM transient_alerts WHERE acknowledged = ?"
    params = [1 if acknowledged else 0]

    if alert_level:
        query += " AND alert_level = ?"
        params.append(alert_level)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    try:
        df = pd.read_sql_query(query, conn, params=params)
        return df
    finally:
        conn.close()
