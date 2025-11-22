"""Smart calibrator pre-selection and registry.

This module provides functions to build and query a calibrator registry
database with pre-computed primary beam weights and blacklists for
variable sources, enabling 10× speedup in calibrator selection.

Implements Proposal #3: Smart Calibrator Pre-Selection
"""

import logging
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def create_calibrator_registry(
    db_path: str = "/data/dsa110-contimg/state/calibrator_registry.sqlite3",
):
    """Create calibrator registry database schema.

    Tables created:
    - calibrator_sources: Pre-selected calibrators with metadata
    - calibrator_blacklist: Variable/unsuitable sources to exclude
    - pb_weights_cache: Pre-computed primary beam weights per declination

    Args:
        db_path: Path to calibrator registry database

    Returns:
        True if successful
    """
    conn = sqlite3.connect(db_path, timeout=30.0)
    cur = conn.cursor()

    try:
        # Main calibrator sources table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS calibrator_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT NOT NULL,
                ra_deg REAL NOT NULL,
                dec_deg REAL NOT NULL,
                flux_1400mhz_jy REAL NOT NULL,
                spectral_index REAL,
                catalog_source TEXT NOT NULL,
                dec_strip INTEGER NOT NULL,
                pb_weight REAL,
                compactness_score REAL,
                variability_flag INTEGER DEFAULT 0,
                quality_score REAL,
                last_updated REAL NOT NULL,
                notes TEXT,
                UNIQUE(source_name, dec_strip)
            )
        """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_calibrators_dec_strip 
            ON calibrator_sources(dec_strip, quality_score DESC)
        """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_calibrators_coords 
            ON calibrator_sources(ra_deg, dec_deg)
        """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_calibrators_flux 
            ON calibrator_sources(flux_1400mhz_jy DESC)
        """
        )

        # Blacklist table for variable/unsuitable sources
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS calibrator_blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT NOT NULL UNIQUE,
                ra_deg REAL NOT NULL,
                dec_deg REAL NOT NULL,
                reason TEXT NOT NULL,
                source_type TEXT,
                added_at REAL NOT NULL,
                notes TEXT
            )
        """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_blacklist_name 
            ON calibrator_blacklist(source_name)
        """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_blacklist_coords 
            ON calibrator_blacklist(ra_deg, dec_deg)
        """
        )

        # Pre-computed primary beam weights cache
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pb_weights_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dec_strip INTEGER NOT NULL,
                pointing_dec REAL NOT NULL,
                source_dec REAL NOT NULL,
                pb_weight REAL NOT NULL,
                frequency_ghz REAL NOT NULL,
                calculated_at REAL NOT NULL,
                UNIQUE(dec_strip, source_dec, frequency_ghz)
            )
        """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_pb_cache_dec 
            ON pb_weights_cache(dec_strip, source_dec)
        """
        )

        # Registry metadata table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS registry_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
        """
        )

        conn.commit()
        logger.info(f"Created calibrator registry at {db_path}")
        return True

    except Exception as e:
        logger.error(f"Error creating calibrator registry: {e}")
        return False
    finally:
        conn.close()


def blacklist_source(
    source_name: str,
    ra_deg: float,
    dec_deg: float,
    reason: str,
    source_type: Optional[str] = None,
    notes: Optional[str] = None,
    db_path: str = "/data/dsa110-contimg/state/calibrator_registry.sqlite3",
) -> bool:
    """Add a source to the calibrator blacklist.

    Args:
        source_name: Source identifier
        ra_deg: Right ascension [degrees]
        dec_deg: Declination [degrees]
        reason: Reason for blacklisting (e.g., 'pulsar', 'variable', 'extended')
        source_type: Type of source (e.g., 'pulsar', 'AGN', 'transient')
        notes: Additional notes
        db_path: Path to registry database

    Returns:
        True if successful
    """
    conn = sqlite3.connect(db_path, timeout=30.0)
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT OR REPLACE INTO calibrator_blacklist
            (source_name, ra_deg, dec_deg, reason, source_type, added_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (source_name, ra_deg, dec_deg, reason, source_type, time.time(), notes),
        )

        conn.commit()
        logger.info(f"Blacklisted source: {source_name} ({reason})")
        return True

    except Exception as e:
        logger.error(f"Error blacklisting source {source_name}: {e}")
        return False
    finally:
        conn.close()


def is_source_blacklisted(
    source_name: Optional[str] = None,
    ra_deg: Optional[float] = None,
    dec_deg: Optional[float] = None,
    radius_deg: float = 0.01,
    db_path: str = "/data/dsa110-contimg/state/calibrator_registry.sqlite3",
) -> Tuple[bool, Optional[str]]:
    """Check if a source is blacklisted.

    Can search by name or coordinates (within radius).

    Args:
        source_name: Source name to check
        ra_deg: Right ascension [degrees]
        dec_deg: Declination [degrees]
        radius_deg: Search radius for coordinate match [degrees]
        db_path: Path to registry database

    Returns:
        Tuple of (is_blacklisted, reason)
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        if source_name:
            cur.execute(
                """
                SELECT reason FROM calibrator_blacklist 
                WHERE source_name = ?
            """,
                (source_name,),
            )
            result = cur.fetchone()
            if result:
                return True, result[0]

        if ra_deg is not None and dec_deg is not None:
            # Approximate cone search
            cur.execute(
                """
                SELECT source_name, reason FROM calibrator_blacklist
                WHERE ABS(ra_deg - ?) < ? AND ABS(dec_deg - ?) < ?
            """,
                (ra_deg, radius_deg, dec_deg, radius_deg),
            )
            result = cur.fetchone()
            if result:
                return True, f"{result[0]}: {result[1]}"

        return False, None

    except Exception as e:
        logger.error(f"Error checking blacklist: {e}")
        return False, None
    finally:
        conn.close()


def add_calibrator_to_registry(
    source_name: str,
    ra_deg: float,
    dec_deg: float,
    flux_1400mhz_jy: float,
    dec_strip: int,
    catalog_source: str = "NVSS",
    spectral_index: Optional[float] = None,
    pb_weight: Optional[float] = None,
    compactness_score: Optional[float] = None,
    quality_score: Optional[float] = None,
    notes: Optional[str] = None,
    db_path: str = "/data/dsa110-contimg/state/calibrator_registry.sqlite3",
) -> Optional[int]:
    """Add a calibrator source to the registry.

    Args:
        source_name: Source identifier
        ra_deg: Right ascension [degrees]
        dec_deg: Declination [degrees]
        flux_1400mhz_jy: Flux at 1.4 GHz [Jy]
        dec_strip: Declination strip (e.g., 30 for +30°)
        catalog_source: Source catalog (e.g., 'NVSS', 'FIRST')
        spectral_index: Spectral index (if known)
        pb_weight: Pre-computed primary beam weight
        compactness_score: Compactness metric (0-1, higher = more compact)
        quality_score: Overall quality score (0-100)
        notes: Additional notes
        db_path: Path to registry database

    Returns:
        Record ID if successful, None otherwise
    """
    # Check if blacklisted
    is_blacklisted_flag, _ = is_source_blacklisted(source_name=source_name, db_path=db_path)
    if is_blacklisted_flag:
        logger.debug(f"Skipping blacklisted source: {source_name}")
        return None

    # Calculate quality score if not provided
    if quality_score is None:
        quality_score = _calculate_quality_score(flux_1400mhz_jy, spectral_index, compactness_score)

    conn = sqlite3.connect(db_path, timeout=30.0)
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT OR REPLACE INTO calibrator_sources
            (source_name, ra_deg, dec_deg, flux_1400mhz_jy, spectral_index,
             catalog_source, dec_strip, pb_weight, compactness_score,
             quality_score, last_updated, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                source_name,
                ra_deg,
                dec_deg,
                flux_1400mhz_jy,
                spectral_index,
                catalog_source,
                dec_strip,
                pb_weight,
                compactness_score,
                quality_score,
                time.time(),
                notes,
            ),
        )

        record_id = cur.lastrowid
        conn.commit()

        logger.debug(f"Added calibrator: {source_name} (quality={quality_score:.1f})")
        return record_id

    except Exception as e:
        logger.error(f"Error adding calibrator {source_name}: {e}")
        return None
    finally:
        conn.close()


def _calculate_quality_score(
    flux_jy: float, spectral_index: Optional[float], compactness: Optional[float]
) -> float:
    """Calculate calibrator quality score (0-100).

    Higher scores indicate better calibrators.

    Scoring criteria:
    - Flux: Brighter is better (up to ~10 Jy)
    - Spectral index: Flat spectrum preferred (α ~ 0)
    - Compactness: Unresolved/point sources preferred
    """
    score = 0.0

    # Flux component (0-40 points)
    # Optimal range: 1-10 Jy
    if flux_jy >= 10.0:
        flux_score = 40.0
    elif flux_jy >= 1.0:
        flux_score = 30.0 + 10.0 * (flux_jy - 1.0) / 9.0
    elif flux_jy >= 0.5:
        flux_score = 20.0 + 10.0 * (flux_jy - 0.5) / 0.5
    else:
        flux_score = 20.0 * (flux_jy / 0.5)

    score += flux_score

    # Spectral index component (0-30 points)
    # Flat spectrum (α ~ 0) is best
    if spectral_index is not None:
        alpha_dev = abs(spectral_index)
        if alpha_dev < 0.2:
            alpha_score = 30.0
        elif alpha_dev < 0.5:
            alpha_score = 30.0 - 10.0 * (alpha_dev - 0.2) / 0.3
        else:
            alpha_score = 20.0 * np.exp(-(alpha_dev - 0.5) / 0.5)
        score += alpha_score
    else:
        score += 15.0  # Neutral if unknown

    # Compactness component (0-30 points)
    if compactness is not None:
        # compactness: 1.0 = point source, 0.0 = extended
        score += 30.0 * compactness
    else:
        score += 15.0  # Neutral if unknown

    return float(np.clip(score, 0.0, 100.0))


def query_calibrators(
    dec_deg: float,
    dec_tolerance: float = 5.0,
    min_flux_jy: float = 0.5,
    max_sources: int = 100,
    min_quality_score: float = 50.0,
    db_path: str = "/data/dsa110-contimg/state/calibrator_registry.sqlite3",
) -> List[Dict]:
    """Query calibrators from registry for a given declination.

    This is the main fast lookup function - replaces catalog queries.

    Args:
        dec_deg: Target declination [degrees]
        dec_tolerance: Declination search range [degrees]
        min_flux_jy: Minimum flux [Jy]
        max_sources: Maximum number of sources to return
        min_quality_score: Minimum quality score (0-100)
        db_path: Path to registry database

    Returns:
        List of calibrator dictionaries sorted by quality score
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    dec_min = dec_deg - dec_tolerance
    dec_max = dec_deg + dec_tolerance

    try:
        cur.execute(
            """
            SELECT source_name, ra_deg, dec_deg, flux_1400mhz_jy,
                   spectral_index, catalog_source, pb_weight,
                   compactness_score, quality_score, notes
            FROM calibrator_sources
            WHERE dec_deg >= ? AND dec_deg <= ?
              AND flux_1400mhz_jy >= ?
              AND quality_score >= ?
            ORDER BY quality_score DESC
            LIMIT ?
        """,
            (dec_min, dec_max, min_flux_jy, min_quality_score, max_sources),
        )

        rows = cur.fetchall()

        calibrators = []
        for row in rows:
            source_name = row[0]

            # Filter out blacklisted sources
            is_blacklisted_flag, _ = is_source_blacklisted(source_name=source_name, db_path=db_path)
            if is_blacklisted_flag:
                logger.debug(f"Skipping blacklisted calibrator: {source_name}")
                continue

            calibrators.append(
                {
                    "source_name": source_name,
                    "ra_deg": row[1],
                    "dec_deg": row[2],
                    "flux_1400mhz_jy": row[3],
                    "spectral_index": row[4],
                    "catalog_source": row[5],
                    "pb_weight": row[6],
                    "compactness_score": row[7],
                    "quality_score": row[8],
                    "notes": row[9],
                }
            )

        logger.debug(f"Found {len(calibrators)} calibrators for Dec={dec_deg:.1f}°")
        return calibrators

    except Exception as e:
        logger.error(f"Error querying calibrators: {e}")
        return []
    finally:
        conn.close()


def get_best_calibrator(
    dec_deg: float,
    dec_tolerance: float = 5.0,
    min_flux_jy: float = 1.0,
    db_path: str = "/data/dsa110-contimg/state/calibrator_registry.sqlite3",
) -> Optional[Dict]:
    """Get single best calibrator for a declination.

    Convenience function that returns the highest-quality calibrator.

    Args:
        dec_deg: Target declination [degrees]
        dec_tolerance: Declination search range [degrees]
        min_flux_jy: Minimum flux [Jy]
        db_path: Path to registry database

    Returns:
        Calibrator dictionary or None if none found
    """
    calibrators = query_calibrators(
        dec_deg=dec_deg,
        dec_tolerance=dec_tolerance,
        min_flux_jy=min_flux_jy,
        max_sources=1,
        db_path=db_path,
    )

    if len(calibrators) > 0:
        return calibrators[0]
    return None


def get_registry_statistics(
    db_path: str = "/data/dsa110-contimg/state/calibrator_registry.sqlite3",
) -> Dict:
    """Get statistics on calibrator registry.

    Returns:
        Dictionary with registry statistics
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        stats = {}

        # Total calibrators
        cur.execute("SELECT COUNT(*) FROM calibrator_sources")
        stats["total_calibrators"] = cur.fetchone()[0]

        # By declination strip
        cur.execute(
            """
            SELECT dec_strip, COUNT(*) 
            FROM calibrator_sources 
            GROUP BY dec_strip 
            ORDER BY dec_strip
        """
        )
        stats["by_dec_strip"] = {row[0]: row[1] for row in cur.fetchall()}

        # Quality distribution
        cur.execute(
            """
            SELECT 
                COUNT(CASE WHEN quality_score >= 80 THEN 1 END) as excellent,
                COUNT(CASE WHEN quality_score >= 60 AND quality_score < 80 THEN 1 END) as good,
                COUNT(CASE WHEN quality_score >= 40 AND quality_score < 60 THEN 1 END) as fair,
                COUNT(CASE WHEN quality_score < 40 THEN 1 END) as poor
            FROM calibrator_sources
        """
        )
        row = cur.fetchone()
        stats["quality_distribution"] = {
            "excellent (≥80)": row[0],
            "good (60-80)": row[1],
            "fair (40-60)": row[2],
            "poor (<40)": row[3],
        }

        # Blacklist count
        cur.execute("SELECT COUNT(*) FROM calibrator_blacklist")
        stats["blacklisted_sources"] = cur.fetchone()[0]

        # Flux distribution
        cur.execute(
            """
            SELECT AVG(flux_1400mhz_jy), MIN(flux_1400mhz_jy), MAX(flux_1400mhz_jy)
            FROM calibrator_sources
        """
        )
        row = cur.fetchone()
        stats["flux_stats"] = {
            "mean_jy": row[0],
            "min_jy": row[1],
            "max_jy": row[2],
        }

        return stats

    except Exception as e:
        logger.error(f"Error getting registry statistics: {e}")
        return {}
    finally:
        conn.close()


def build_calibrator_registry_from_catalog(
    catalog_type: str = "nvss",
    dec_strips: Optional[List[int]] = None,
    min_flux_jy: float = 0.5,
    max_sources_per_strip: int = 1000,
    db_path: str = "/data/dsa110-contimg/state/calibrator_registry.sqlite3",
    catalog_db_path: Optional[str] = None,
) -> int:
    """Build calibrator registry by importing from a catalog database.

    This is the main registry building function. Run this once to populate
    the registry from existing catalog databases.

    Args:
        catalog_type: Source catalog ('nvss', 'first', etc.)
        dec_strips: List of declination strips to build (e.g., [20, 30, 40])
                   If None, builds all strips from -40° to +90° in 10° steps
        min_flux_jy: Minimum flux for calibrator candidates [Jy]
        max_sources_per_strip: Maximum calibrators per declination strip
        db_path: Path to calibrator registry database
        catalog_db_path: Path to source catalog database

    Returns:
        Number of calibrators added to registry
    """
    # Import here to avoid circular dependency
    from dsa110_contimg.catalog.query import query_sources

    # Ensure registry exists
    create_calibrator_registry(db_path)

    # Default declination strips (every 10°)
    if dec_strips is None:
        dec_strips = list(range(-40, 91, 10))

    total_added = 0

    for dec_strip in dec_strips:
        logger.info(f"Building calibrator registry for Dec strip {dec_strip:+d}°...")

        try:
            # Query catalog for bright sources
            sources = query_sources(
                catalog_type=catalog_type,
                ra_center=0.0,  # Doesn't matter for all-sky
                dec_center=dec_strip,
                radius_deg=10.0,  # ±10° around strip center
                min_flux_mjy=min_flux_jy * 1000,  # Convert to mJy
            )

            if sources is None or len(sources) == 0:
                logger.warning(f"No sources found for Dec strip {dec_strip:+d}°")
                continue

            # Sort by flux and take top N
            sources = sources.sort_values("flux_mjy", ascending=False).head(max_sources_per_strip)

            # Add to registry
            for _, source in sources.iterrows():
                record_id = add_calibrator_to_registry(
                    source_name=source.get(
                        "id", f"SRC_{source['ra_deg']:.5f}_{source['dec_deg']:+.5f}"
                    ),
                    ra_deg=source["ra_deg"],
                    dec_deg=source["dec_deg"],
                    flux_1400mhz_jy=source["flux_mjy"] / 1000.0,
                    dec_strip=dec_strip,
                    catalog_source=catalog_type.upper(),
                    db_path=db_path,
                )

                if record_id:
                    total_added += 1

            logger.info(f"Added {total_added} calibrators for Dec strip {dec_strip:+d}°")

        except Exception as e:
            logger.error(f"Error building registry for Dec strip {dec_strip:+d}°: {e}")
            continue

    logger.info(f"Calibrator registry build complete: {total_added} sources added")
    return total_added
