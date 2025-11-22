"""Integration layer for smart calibrator selection in the pipeline.

This module provides drop-in replacements for existing calibrator selection
functions, using the pre-built calibrator registry for 10× speedup.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from dsa110_contimg.catalog.calibrator_registry import (
    get_best_calibrator,
    is_source_blacklisted,
    query_calibrators,
)
from dsa110_contimg.catalog.coverage import recommend_catalogs

logger = logging.getLogger(__name__)


def select_bandpass_calibrator_fast(
    dec_deg: float,
    dec_tolerance: float = 5.0,
    min_flux_jy: float = 1.0,
    use_registry: bool = True,
    fallback_to_catalog: bool = True,
    db_path: str = "/data/dsa110-contimg/state/calibrator_registry.sqlite3",
) -> Optional[Dict]:
    """Fast bandpass calibrator selection using registry.

    This is the main replacement for select_bandpass_from_catalog().
    Expected speedup: 10× (30s → 3s per selection).

    Args:
        dec_deg: Target declination [degrees]
        dec_tolerance: Declination search range [degrees]
        min_flux_jy: Minimum flux [Jy]
        use_registry: If True, use registry (fast). If False, use catalog query (slow)
        fallback_to_catalog: If registry fails, fall back to catalog query
        db_path: Path to calibrator registry database

    Returns:
        Calibrator dictionary with keys:
        - source_name: Calibrator identifier
        - ra_deg: Right ascension [degrees]
        - dec_deg: Declination [degrees]
        - flux_1400mhz_jy: Flux [Jy]
        - quality_score: Quality score (0-100)
        Or None if no suitable calibrator found
    """
    if use_registry:
        try:
            # Registry lookup (fast path)
            calibrator = get_best_calibrator(
                dec_deg=dec_deg,
                dec_tolerance=dec_tolerance,
                min_flux_jy=min_flux_jy,
                db_path=db_path,
            )

            if calibrator:
                logger.info(
                    f"Selected calibrator from registry: {calibrator['source_name']} "
                    f"(quality={calibrator['quality_score']:.1f})"
                )
                return calibrator

            logger.warning(f"No calibrator found in registry for Dec={dec_deg:.1f}°")

            if not fallback_to_catalog:
                return None

        except Exception as e:
            logger.error(f"Registry lookup failed: {e}")
            if not fallback_to_catalog:
                return None

    # Fallback to catalog query (slow path)
    if fallback_to_catalog or not use_registry:
        logger.info(f"Falling back to catalog query for Dec={dec_deg:.1f}°")
        return _select_calibrator_from_catalog_slow(
            dec_deg=dec_deg, dec_tolerance=dec_tolerance, min_flux_jy=min_flux_jy
        )

    return None


def _select_calibrator_from_catalog_slow(
    dec_deg: float, dec_tolerance: float, min_flux_jy: float
) -> Optional[Dict]:
    """Legacy slow calibrator selection via catalog queries.

    Only used as fallback when registry is empty or fails.
    """
    from dsa110_contimg.catalog.query import query_sources

    # Determine which catalog to use based on declination
    catalog_recommendations = recommend_catalogs(
        ra=0.0, dec=dec_deg, purpose="calibration"  # Don't care about RA for calibrators
    )

    if not catalog_recommendations:
        logger.error(f"No catalogs available for Dec={dec_deg:.1f}°")
        return None

    # Try catalogs in priority order
    for catalog_rec in catalog_recommendations:
        catalog_type = catalog_rec["catalog"].lower()

        try:
            sources = query_sources(
                catalog_type=catalog_type,
                ra_center=0.0,
                dec_center=dec_deg,
                radius_deg=dec_tolerance,
                min_flux_mjy=min_flux_jy * 1000,
            )

            if sources is None or len(sources) == 0:
                continue

            # Filter out blacklisted sources
            sources_filtered = []
            for _, source in sources.iterrows():
                is_blacklisted_flag, reason = is_source_blacklisted(
                    ra_deg=source["ra_deg"], dec_deg=source["dec_deg"], radius_deg=0.01
                )
                if not is_blacklisted_flag:
                    sources_filtered.append(source)

            if not sources_filtered:
                logger.warning(f"All sources in {catalog_type} are blacklisted")
                continue

            # Sort by flux and take best
            sources_filtered.sort(key=lambda s: s["flux_mjy"], reverse=True)
            best_source = sources_filtered[0]

            return {
                "source_name": best_source.get("id", f"CAL_{best_source['ra_deg']:.5f}"),
                "ra_deg": best_source["ra_deg"],
                "dec_deg": best_source["dec_deg"],
                "flux_1400mhz_jy": best_source["flux_mjy"] / 1000.0,
                "catalog_source": catalog_type.upper(),
                "quality_score": 50.0,  # Default for catalog sources
            }

        except Exception as e:
            logger.error(f"Error querying {catalog_type} catalog: {e}")
            continue

    return None


def select_multiple_calibrators(
    dec_deg: float,
    n_calibrators: int = 10,
    dec_tolerance: float = 5.0,
    min_flux_jy: float = 0.5,
    min_separation_deg: float = 1.0,
    db_path: str = "/data/dsa110-contimg/state/calibrator_registry.sqlite3",
) -> List[Dict]:
    """Select multiple calibrators for a field.

    Useful for:
    - Multiple gain calibrators
    - Spatial calibration grids
    - Redundancy/backup calibrators

    Args:
        dec_deg: Target declination [degrees]
        n_calibrators: Number of calibrators to select
        dec_tolerance: Declination search range [degrees]
        min_flux_jy: Minimum flux [Jy]
        min_separation_deg: Minimum separation between calibrators [degrees]
        db_path: Path to calibrator registry

    Returns:
        List of calibrator dictionaries
    """
    calibrators = query_calibrators(
        dec_deg=dec_deg,
        dec_tolerance=dec_tolerance,
        min_flux_jy=min_flux_jy,
        max_sources=n_calibrators * 10,  # Get extras for filtering
        db_path=db_path,
    )

    if not calibrators:
        return []

    # Filter for minimum separation
    selected = []
    for cal in calibrators:
        if len(selected) >= n_calibrators:
            break

        # Check separation from already-selected calibrators
        too_close = False
        for sel_cal in selected:
            sep = _angular_separation(
                cal["ra_deg"], cal["dec_deg"], sel_cal["ra_deg"], sel_cal["dec_deg"]
            )
            if sep < min_separation_deg:
                too_close = True
                break

        if not too_close:
            selected.append(cal)

    logger.info(f"Selected {len(selected)} calibrators for Dec={dec_deg:.1f}°")
    return selected


def _angular_separation(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    """Calculate angular separation between two positions [degrees].

    Uses small-angle approximation (good for <10° separations).
    """
    dra = (ra2 - ra1) * np.cos(np.radians((dec1 + dec2) / 2))
    ddec = dec2 - dec1
    return np.sqrt(dra**2 + ddec**2)


def validate_calibrator_selection(
    calibrator: Dict,
    target_dec: float,
    max_dec_offset: float = 10.0,
    min_flux_jy: float = 0.5,
) -> Tuple[bool, Optional[str]]:
    """Validate that a selected calibrator is suitable.

    Args:
        calibrator: Calibrator dictionary
        target_dec: Target field declination [degrees]
        max_dec_offset: Maximum declination offset allowed [degrees]
        min_flux_jy: Minimum required flux [Jy]

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not calibrator:
        return False, "Calibrator is None"

    # Check declination offset
    dec_offset = abs(calibrator["dec_deg"] - target_dec)
    if dec_offset > max_dec_offset:
        return False, f"Declination offset too large: {dec_offset:.1f}° > {max_dec_offset}°"

    # Check flux
    flux = calibrator.get("flux_1400mhz_jy", 0.0)
    if flux < min_flux_jy:
        return False, f"Flux too low: {flux:.2f} Jy < {min_flux_jy} Jy"

    # Check if blacklisted
    is_blacklisted_flag, reason = is_source_blacklisted(
        source_name=calibrator.get("source_name"),
        ra_deg=calibrator.get("ra_deg"),
        dec_deg=calibrator.get("dec_deg"),
    )
    if is_blacklisted_flag:
        return False, f"Source is blacklisted: {reason}"

    # Check quality score if available
    quality = calibrator.get("quality_score", 50.0)
    if quality < 30.0:
        return False, f"Quality score too low: {quality:.1f}"

    return True, None


def get_calibrator_performance_metrics(
    calibrator_name: str, db_path: str = "/data/dsa110-contimg/state/calibrator_registry.sqlite3"
) -> Optional[Dict]:
    """Get historical performance metrics for a calibrator.

    Reads from flux_monitoring table to assess calibrator stability.

    Args:
        calibrator_name: Calibrator source name
        db_path: Path to calibrator registry (checks products.sqlite3 for flux monitoring)

    Returns:
        Dictionary with metrics:
        - mean_flux: Average flux [Jy]
        - flux_std: Flux standard deviation [Jy]
        - variability_index: RMS/mean (lower is better)
        - n_measurements: Number of observations
    """
    import sqlite3

    # Check flux monitoring database
    products_db = Path(db_path).parent / "products.sqlite3"
    if not products_db.exists():
        return None

    conn = sqlite3.connect(str(products_db))
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT flux_jy, flux_uncertainty_jy
            FROM calibration_monitoring
            WHERE source_name = ?
            ORDER BY timestamp DESC
            LIMIT 100
        """,
            (calibrator_name,),
        )

        rows = cur.fetchall()
        if not rows:
            return None

        fluxes = np.array([row[0] for row in rows])

        return {
            "mean_flux": float(np.mean(fluxes)),
            "flux_std": float(np.std(fluxes)),
            "variability_index": float(np.std(fluxes) / np.mean(fluxes)),
            "n_measurements": len(rows),
        }

    except Exception as e:
        logger.error(f"Error getting calibrator metrics: {e}")
        return None
    finally:
        conn.close()


def recommend_calibrator_for_observation(
    target_dec: float,
    observation_type: str = "general",
    prefer_monitored: bool = True,
    db_path: str = "/data/dsa110-contimg/state/calibrator_registry.sqlite3",
) -> Optional[Dict]:
    """High-level calibrator recommendation for an observation.

    This is the main user-facing function for calibrator selection.

    Args:
        target_dec: Target field declination [degrees]
        observation_type: Type of observation:
            - 'general': Standard imaging
            - 'precise': High-precision astrometry/photometry
            - 'fast': Quick calibration (relaxed requirements)
        prefer_monitored: Prefer calibrators with flux monitoring history
        db_path: Path to calibrator registry

    Returns:
        Recommended calibrator dictionary
    """
    # Set requirements based on observation type
    if observation_type == "precise":
        min_flux_jy = 2.0
        dec_tolerance = 3.0
        min_quality = 70.0
    elif observation_type == "fast":
        min_flux_jy = 0.5
        dec_tolerance = 10.0
        min_quality = 40.0
    else:  # general
        min_flux_jy = 1.0
        dec_tolerance = 5.0
        min_quality = 50.0

    # Query candidates
    candidates = query_calibrators(
        dec_deg=target_dec,
        dec_tolerance=dec_tolerance,
        min_flux_jy=min_flux_jy,
        max_sources=50,
        min_quality_score=min_quality,
        db_path=db_path,
    )

    if not candidates:
        logger.warning(
            f"No calibrators found for {observation_type} observation at Dec={target_dec:.1f}°"
        )
        return None

    # If prefer monitored, prioritize those with flux history
    if prefer_monitored:
        monitored_candidates = []
        for cal in candidates:
            metrics = get_calibrator_performance_metrics(cal["source_name"])
            if metrics and metrics["n_measurements"] >= 3:
                # Add variability penalty to quality score
                variability_penalty = min(20.0, metrics["variability_index"] * 100)
                cal["adjusted_quality"] = cal["quality_score"] - variability_penalty
                monitored_candidates.append(cal)

        if monitored_candidates:
            # Sort by adjusted quality
            monitored_candidates.sort(key=lambda c: c.get("adjusted_quality", 0), reverse=True)
            best = monitored_candidates[0]
            logger.info(
                f"Selected monitored calibrator: {best['source_name']} "
                f"(quality={best['quality_score']:.1f}, variability monitored)"
            )
            return best

    # Otherwise return highest quality
    best = candidates[0]
    logger.info(f"Selected calibrator: {best['source_name']} (quality={best['quality_score']:.1f})")
    return best
