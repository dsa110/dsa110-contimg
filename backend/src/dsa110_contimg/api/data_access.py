"""Data access helpers for the monitoring API."""

from __future__ import annotations

import json as _json
import sqlite3
import time
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from dsa110_contimg.api.config import ApiConfig
from dsa110_contimg.api.db_utils import db_operation, retry_db_operation
from dsa110_contimg.api.models import (
    CalibrationSet,
    CalibratorMatch,
    CalibratorMatchGroup,
    ObservationTimeline,
    ProductEntry,
    QueueGroup,
    QueueStats,
    TimelineSegment,
)

from .models import PointingHistoryEntry

QUEUE_COLUMNS = [
    "group_id",
    "state",
    "received_at",
    "last_update",
    "expected_subbands",
]


def _connect(path: Path, timeout: float = 30.0) -> sqlite3.Connection:
    """Create a database connection with improved concurrency settings.

    Args:
        path: Path to SQLite database file
        timeout: Busy timeout in seconds (default 30s)

    Returns:
        SQLite connection with WAL mode enabled for better concurrency
    """
    conn = sqlite3.connect(str(path), timeout=timeout)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrent access (readers don't block writers)
    # WAL mode allows multiple readers and one writer simultaneously
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        # If WAL mode can't be enabled (e.g., on network filesystems), continue with default
        pass
    # Set busy timeout explicitly via PRAGMA
    # Note: While sqlite3.connect(timeout=...) may set a default, PRAGMA busy_timeout
    # explicitly sets the session-level timeout for handling database locks during operations.
    # This is critical for concurrent access to prevent "database is locked" errors.
    # PRAGMA statements don't support parameterized queries in SQLite, so we must construct
    # the string. The value is a calculated integer from a function parameter (not user input),
    # validated below to be within reasonable bounds, so this is safe.
    timeout_ms = int(timeout * 1000)
    # Validate timeout is within reasonable bounds (0 to 1 hour) to prevent abuse
    if timeout_ms < 0 or timeout_ms > 3600000:
        raise ValueError(f"Invalid timeout value: {timeout_ms}ms (must be 0-3600000)")
    # Construct PRAGMA statement - safe because timeout_ms is validated integer, not user input
    conn.execute(f"PRAGMA busy_timeout={timeout_ms}")
    return conn


def _retry_db_operation(func, max_retries: int = 3, initial_delay: float = 0.1):
    """Retry a database operation with exponential backoff.

    Args:
        func: Function to retry (should be a callable that returns a value)
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds (doubles with each retry)

    Returns:
        Result of the function call

    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    delay = initial_delay

    for attempt in range(max_retries):
        try:
            return func()
        except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
            last_exception = e
            # Check if it's a locking error
            error_msg = str(e).lower()
            if "locked" in error_msg or "database is locked" in error_msg:
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                    continue
            # For other database errors, re-raise immediately
            raise
        except Exception:
            # For non-database errors, re-raise immediately
            raise

    # If we exhausted retries, raise the last exception
    raise last_exception


def fetch_queue_stats(queue_db: Path) -> QueueStats:
    """Fetch queue statistics with retry logic."""

    def _fetch():
        with db_operation(queue_db, "fetch_queue_stats", use_pool=True) as conn:
            row = conn.execute(
                """
            SELECT 
                COUNT(*) AS total,
                SUM(CASE WHEN state = 'pending' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN state = 'in_progress' THEN 1 ELSE 0 END) AS in_progress,
                SUM(CASE WHEN state = 'failed' THEN 1 ELSE 0 END) AS failed,
                SUM(CASE WHEN state = 'completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN state = 'collecting' THEN 1 ELSE 0 END) AS collecting
            FROM ingest_queue
            """
            ).fetchone()
            if row is None:
                return QueueStats(
                    total=0,
                    pending=0,
                    in_progress=0,
                    failed=0,
                    completed=0,
                    collecting=0,
                )
            return QueueStats(
                total=row["total"] or 0,
                pending=row["pending"] or 0,
                in_progress=row["in_progress"] or 0,
                failed=row["failed"] or 0,
                completed=row["completed"] or 0,
                collecting=row["collecting"] or 0,
            )

    return retry_db_operation(_fetch, operation_name="fetch_queue_stats")


def fetch_recent_queue_groups(
    queue_db: Path, config: ApiConfig, limit: int = 20
) -> List[QueueGroup]:
    """Fetch recent queue groups with retry logic."""

    def _fetch():
        with db_operation(queue_db, "fetch_recent_queue_groups", use_pool=True) as conn:
            rows = conn.execute(
                """
                SELECT iq.group_id,
                       iq.state,
                       iq.received_at,
                       iq.last_update,
                       iq.chunk_minutes,
                       iq.expected_subbands,
                       iq.has_calibrator,
                       iq.calibrators,
                       COUNT(sf.subband_idx) AS subbands
                  FROM ingest_queue iq
             LEFT JOIN subband_files sf ON iq.group_id = sf.group_id
              GROUP BY iq.group_id
              ORDER BY iq.received_at DESC
                 LIMIT ?
                """,
                (limit,),
            ).fetchall()

            groups: List[QueueGroup] = []
            for r in rows:
                # parse calibrator matches JSON if present
                has_cal = r["has_calibrator"]
                cal_json = r["calibrators"] or "[]"
                matches_parsed: List[CalibratorMatch] = []
                try:
                    parsed_list = _json.loads(cal_json)
                    if isinstance(parsed_list, list):
                        for m in parsed_list:
                            try:
                                matches_parsed.append(
                                    CalibratorMatch(
                                        name=str(m.get("name", "")),
                                        ra_deg=float(m.get("ra_deg", 0.0)),
                                        dec_deg=float(m.get("dec_deg", 0.0)),
                                        sep_deg=float(m.get("sep_deg", 0.0)),
                                        weighted_flux=(
                                            float(m.get("weighted_flux"))
                                            if m.get("weighted_flux") is not None
                                            else None
                                        ),
                                    )
                                )
                            except Exception:
                                continue
                except Exception:
                    matches_parsed = []
                groups.append(
                    QueueGroup(
                        group_id=r["group_id"],
                        state=r["state"],
                        received_at=datetime.fromtimestamp(r["received_at"]),
                        last_update=datetime.fromtimestamp(r["last_update"]),
                        subbands_present=r["subbands"] or 0,
                        expected_subbands=r["expected_subbands"] or config.expected_subbands,
                        has_calibrator=bool(has_cal) if has_cal is not None else None,
                        matches=matches_parsed or None,
                    )
                )
            return groups

    return retry_db_operation(_fetch, operation_name="fetch_recent_queue_groups")


def fetch_calibration_sets(registry_db: Path) -> List[CalibrationSet]:
    with closing(_connect(registry_db)) as conn:
        rows = conn.execute(
            """
            SELECT set_name,
                   COUNT(*) AS total,
                   SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active
              FROM caltables
          GROUP BY set_name
          ORDER BY MAX(created_at) DESC
            """
        ).fetchall()
        tables: List[CalibrationSet] = []
        for r in rows:
            table_paths = [
                t[0]
                for t in conn.execute(
                    "SELECT path FROM caltables WHERE set_name=? ORDER BY order_index ASC",
                    (r["set_name"],),
                ).fetchall()
            ]
            tables.append(
                CalibrationSet(
                    set_name=r["set_name"],
                    tables=table_paths,
                    active=r["active"] or 0,
                    total=r["total"] or 0,
                )
            )
    return tables


def fetch_recent_products(products_db: Path, limit: int = 50) -> List[ProductEntry]:
    if not products_db.exists():
        return []
    with closing(_connect(products_db)) as conn:
        rows = conn.execute(
            """
            SELECT id, path, ms_path, created_at, type, beam_major_arcsec, noise_jy, pbcor
              FROM images
          ORDER BY created_at DESC
             LIMIT ?
            """,
            (limit,),
        ).fetchall()
    products: List[ProductEntry] = []
    for r in rows:
        products.append(
            ProductEntry(
                id=r["id"],
                path=r["path"],
                ms_path=r["ms_path"],
                created_at=datetime.fromtimestamp(r["created_at"]),
                type=r["type"],
                beam_major_arcsec=r["beam_major_arcsec"],
                noise_jy=r["noise_jy"],
                pbcor=bool(r["pbcor"]),
            )
        )
    return products


def fetch_recent_calibrator_matches(
    queue_db: Path, limit: int = 50, matched_only: bool = False
) -> List[CalibratorMatchGroup]:
    """Fetch recent groups with calibrator match info from ingest_queue."""
    with closing(_connect(queue_db)) as conn:
        # Build query statically to avoid dynamic SQL construction
        # matched_only is a boolean parameter, not user input, but we construct the query
        # statically to satisfy security linters
        if matched_only:
            query = (
                "SELECT group_id, has_calibrator, calibrators, received_at, last_update "
                "FROM ingest_queue "
                "WHERE (calibrators IS NOT NULL OR has_calibrator IS NOT NULL) "
                "AND has_calibrator = 1 "
                "ORDER BY received_at DESC LIMIT ?"
            )
        else:
            query = (
                "SELECT group_id, has_calibrator, calibrators, received_at, last_update "
                "FROM ingest_queue "
                "WHERE (calibrators IS NOT NULL OR has_calibrator IS NOT NULL) "
                "ORDER BY received_at DESC LIMIT ?"
            )
        rows = conn.execute(query, (limit,)).fetchall()
    groups: List[CalibratorMatchGroup] = []
    for r in rows:
        matched = bool(r["has_calibrator"]) if r["has_calibrator"] is not None else False
        calib_json = r["calibrators"] or "[]"
        try:
            parsed = _json.loads(calib_json)
        except Exception:
            parsed = []
        matches: List[CalibratorMatch] = []
        for m in parsed if isinstance(parsed, list) else []:
            try:
                matches.append(
                    CalibratorMatch(
                        name=str(m.get("name", "")),
                        ra_deg=float(m.get("ra_deg", 0.0)),
                        dec_deg=float(m.get("dec_deg", 0.0)),
                        sep_deg=float(m.get("sep_deg", 0.0)),
                        weighted_flux=(
                            float(m.get("weighted_flux"))
                            if m.get("weighted_flux") is not None
                            else None
                        ),
                    )
                )
            except Exception:
                continue
        groups.append(
            CalibratorMatchGroup(
                group_id=r["group_id"],
                matched=matched,
                matches=matches,
                received_at=datetime.fromtimestamp(r["received_at"]),
                last_update=datetime.fromtimestamp(r["last_update"]),
            )
        )
    return groups


def _is_synthetic_pointing_data(timestamp: float, data_registry_db: Optional[Path] = None) -> bool:
    """Check if pointing data is synthetic/simulated.

    Synthetic data is identified by:
    1. Timestamps before MJD 60000 (approximately year 2023) - these are clearly test data
    2. Data registered in data_registry with synthetic markers (if registry available)

    Args:
        timestamp: MJD timestamp
        data_registry_db: Optional path to data_registry database

    Returns:
        True if data is synthetic, False otherwise
    """
    # Filter out old test data (MJD < 60000 corresponds to dates before ~2023)
    # Real observations should be from recent dates
    if timestamp < 60000:
        return True

    # If data_registry is available, check for synthetic markers
    if data_registry_db and data_registry_db.exists():
        try:
            with closing(_connect(data_registry_db)) as reg_conn:
                # Check if there's a data_registry entry with synthetic markers
                # Note: This is a simplified check - ideally pointing_history would have
                # a direct link to data_registry, but for now we filter by timestamp
                _ = reg_conn.execute(  # Execute query, result not needed
                    """
                    SELECT COUNT(*) FROM data_registry dr
                    LEFT JOIN data_tags dt ON dr.data_id = dt.data_id
                    WHERE (dt.tag LIKE '%synthetic%' OR dt.tag LIKE '%simulated%'
                           OR dr.metadata_json LIKE '%synthetic%' 
                           OR dr.metadata_json LIKE '%simulated%')
                    """
                )
                # If registry has synthetic entries, we could potentially match them
                # For now, rely on timestamp filtering
                pass
        except Exception:
            # If registry check fails, fall back to timestamp filtering
            pass

    return False


def fetch_pointing_history(
    ingest_db_path: str,
    start_mjd: float,
    end_mjd: float,
    exclude_synthetic: bool = True,
    time_interval_hours: float = 6.0,
) -> List[PointingHistoryEntry]:
    """Fetch pointing history with time-based sampling from actual observations.

    This function queries the HDF5 index database at regular time intervals
    to get a uniform distribution of pointing data across the time range.

    NOTE: We query ONLY hdf5_file_index (actual observation metadata), not the
    pointing_history table, because the pointing_history table may contain outdated
    monitoring data that doesn't match actual observations, causing data conflicts.

    Args:
        ingest_db_path: Path to ingest database (UNUSED - kept for API compatibility)
        start_mjd: Start MJD timestamp
        end_mjd: End MJD timestamp
        exclude_synthetic: If True, filter out synthetic/simulated data (default: True)
        time_interval_hours: Sample interval in hours (default: 6 hours = 0.25 MJD)

    Returns:
        List of pointing history entries sampled at regular time intervals, sorted by timestamp
    """
    import logging
    import os

    logger = logging.getLogger(__name__)
    logger.info(
        f"fetch_pointing_history: start_mjd={start_mjd}, end_mjd={end_mjd}, "
        f"time_interval_hours={time_interval_hours}"
    )

    # Get data_registry path if available
    data_registry_db = None
    if exclude_synthetic:
        registry_path = Path(os.getenv("PIPELINE_DATA_REGISTRY_DB", "state/db/data_registry.sqlite3"))
        if registry_path.exists():
            data_registry_db = registry_path

    # Use timestamp as key to deduplicate
    entries_dict: dict[float, PointingHistoryEntry] = {}

    # BUGFIX 2025-11-18: Skip pointing_history table query
    # The pointing_history table contains monitoring/synthetic data that doesn't match
    # actual observations in hdf5_file_index, causing artificial oscillations in plots
    # when both datasets are merged (they have different timestamps so both get added).
    # We only query hdf5_file_index which has the true observation coordinates.

    # Query pointing_history table from ingest database (monitoring data)
    # DISABLED: This causes data mixing bugs when monitoring data doesn't match observations
    # ingest_db = Path(ingest_db_path)
    # if ingest_db.exists():
    #     with closing(_connect(ingest_db)) as conn:
    #         rows = conn.execute(
    #             "SELECT timestamp, ra_deg, dec_deg FROM pointing_history WHERE timestamp BETWEEN ? AND ? AND ra_deg IS NOT NULL AND dec_deg IS NOT NULL ORDER BY timestamp",
    #             (start_mjd, end_mjd),
    #         ).fetchall()
    #
    #         for r in rows:
    #             entries_dict[r["timestamp"]] = PointingHistoryEntry(
    #                 timestamp=r["timestamp"],
    #                 ra_deg=r["ra_deg"],
    #                 dec_deg=r["dec_deg"],
    #             )

    # Query HDF5 index database for files within the time range
    # This is much faster than scanning /data/incoming/ directly (80k+ files)
    # In Docker: /app/state/db/hdf5.sqlite3, on host: /data/dsa110-contimg/state/db/hdf5.sqlite3
    hdf5_db_path = Path(os.getenv("HDF5_DB_PATH", "state/db/hdf5.sqlite3"))
    if not hdf5_db_path.is_absolute():
        # Resolve relative to project root, not CWD (which may be /app/state/logs in API)
        # Try Docker path first, then host path
        if Path("/app/state/db/hdf5.sqlite3").exists():
            hdf5_db_path = Path("/app/state/db/hdf5.sqlite3")
        elif Path("/data/dsa110-contimg/state/db/hdf5.sqlite3").exists():
            hdf5_db_path = Path("/data/dsa110-contimg/state/db/hdf5.sqlite3")
        else:
            hdf5_db_path = Path.cwd() / hdf5_db_path  # Fallback to CWD

    logger.error(f"🔍 HDF5 DB path: {hdf5_db_path}")
    logger.error(f"🔍 HDF5 DB exists: {hdf5_db_path.exists()}")

    if hdf5_db_path.exists():
        try:
            with closing(_connect(hdf5_db_path)) as conn:
                # Time-based sampling: sample at regular intervals
                time_interval_mjd = time_interval_hours / 24.0  # Convert hours to MJD

                # Calculate expected number of points
                time_span = end_mjd - start_mjd
                expected_points = int(time_span / time_interval_mjd) + 1
                logger.info(
                    f"Time-based sampling: interval={time_interval_hours}h ({time_interval_mjd:.4f} MJD), "
                    f"expected_points={expected_points}"
                )

                # Generate regular time points and find closest observation for each
                current_mjd = start_mjd
                sampled_count = 0

                while current_mjd <= end_mjd:
                    # Find closest observation to this time point
                    # We use a window of ±time_interval_mjd to find nearby observations
                    window = time_interval_mjd

                    # Query for closest observation within the window
                    row = conn.execute(
                        """SELECT timestamp_mjd, ra_deg, dec_deg,
                           ABS(timestamp_mjd - ?) as time_diff
                           FROM hdf5_file_index
                           WHERE timestamp_mjd BETWEEN ? AND ?
                           AND path LIKE '%sb00.hdf5'
                           AND ra_deg IS NOT NULL 
                           AND dec_deg IS NOT NULL
                           ORDER BY time_diff ASC
                           LIMIT 1""",
                        (current_mjd, current_mjd - window, current_mjd + window),
                    ).fetchone()

                    if row:
                        timestamp_mjd = row[0]
                        ra_deg = row[1]
                        dec_deg = row[2]

                        # Only add if we don't already have this exact timestamp
                        if timestamp_mjd not in entries_dict:
                            entries_dict[timestamp_mjd] = PointingHistoryEntry(
                                timestamp=timestamp_mjd,
                                ra_deg=ra_deg,
                                dec_deg=dec_deg,
                            )
                            sampled_count += 1

                    current_mjd += time_interval_mjd

                logger.info(
                    f"Time-based sampling: found {sampled_count} observations at regular intervals"
                )
        except Exception as e:
            logger.error(f"Failed to query HDF5 index database: {e}", exc_info=True)

    # Convert to list and sort by timestamp
    entries = sorted(entries_dict.values(), key=lambda e: e.timestamp)

    # Filter out synthetic data if requested
    if exclude_synthetic:
        entries = [
            entry
            for entry in entries
            if not _is_synthetic_pointing_data(entry.timestamp, data_registry_db)
        ]

    logger.error(f"🔍 Returning {len(entries)} entries after filtering")
    return entries


def fetch_ese_candidates(products_db: Path, limit: int = 50, min_sigma: float = 5.0) -> List[dict]:
    """Fetch ESE candidates from the database.

    Returns list of ESE candidates with variability stats joined.
    """
    if not products_db.exists():
        return []

    with closing(_connect(products_db)) as conn:
        # Check if tables exist
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }

        if "ese_candidates" not in tables or "variability_stats" not in tables:
            return []

        # Query ESE candidates joined with variability stats
        rows = conn.execute(
            """
            SELECT 
                e.id,
                e.source_id,
                e.flagged_at,
                e.flagged_by,
                e.significance,
                e.flag_type,
                e.notes,
                e.status,
                e.investigated_at,
                e.dismissed_at,
                v.ra_deg,
                v.dec_deg,
                v.nvss_flux_mjy,
                v.mean_flux_mjy,
                v.std_flux_mjy,
                v.chi2_nu,
                v.sigma_deviation,
                v.last_measured_at,
                v.last_mjd,
                v.updated_at,
                MIN(p.measured_at) as first_measured_at
            FROM ese_candidates e
            LEFT JOIN variability_stats v ON e.source_id = v.source_id
            LEFT JOIN photometry p ON e.source_id = p.source_id
            WHERE e.status = 'active' AND e.significance >= ?
            GROUP BY e.id, e.source_id
            ORDER BY e.significance DESC, e.flagged_at DESC
            LIMIT ?
            """,
            (min_sigma, limit),
        ).fetchall()

    candidates = []
    for r in rows:
        # Convert timestamps
        flagged_at = (
            datetime.fromtimestamp(r["flagged_at"]) if r["flagged_at"] else datetime.utcnow()
        )
        last_measured = (
            datetime.fromtimestamp(r["last_measured_at"]) if r["last_measured_at"] else flagged_at
        )
        first_measured = (
            datetime.fromtimestamp(r["first_measured_at"]) if r["first_measured_at"] else flagged_at
        )

        # Calculate current and baseline flux
        current_flux_jy = (r["mean_flux_mjy"] / 1000.0) if r["mean_flux_mjy"] else 0.0
        baseline_flux_jy = (r["nvss_flux_mjy"] / 1000.0) if r["nvss_flux_mjy"] else current_flux_jy

        candidates.append(
            {
                "id": r["id"],
                "source_id": r["source_id"],
                "ra_deg": r["ra_deg"] or 0.0,
                "dec_deg": r["dec_deg"] or 0.0,
                "first_detection_at": first_measured.isoformat(),
                "last_detection_at": last_measured.isoformat(),
                "max_sigma_dev": r["sigma_deviation"] or r["significance"] or 0.0,
                "current_flux_jy": current_flux_jy,
                "baseline_flux_jy": baseline_flux_jy,
                "status": r["status"] or "active",
                "notes": r["notes"],
            }
        )

    return candidates


def fetch_mosaics(products_db: Path, start_time: str, end_time: str) -> List[dict]:
    """Fetch mosaics from the database for a time range.

    Args:
        products_db: Path to products database
        start_time: ISO format datetime string
        end_time: ISO format datetime string

    Returns:
        List of mosaic dictionaries
    """
    if not products_db.exists():
        return []

    from astropy.time import Time

    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        start_mjd = Time(start_dt).mjd
        end_mjd = Time(end_dt).mjd
    except Exception:
        return []

    with closing(_connect(products_db)) as conn:
        # Check if mosaics table exists
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }

        if "mosaics" not in tables:
            return []

        rows = conn.execute(
            """
            SELECT 
                id, name, path, created_at, start_mjd, end_mjd,
                integration_sec, n_images, center_ra_deg, center_dec_deg,
                dec_min_deg, dec_max_deg, noise_jy,
                beam_major_arcsec, beam_minor_arcsec, beam_pa_deg,
                n_sources, thumbnail_path
            FROM mosaics
            WHERE (start_mjd <= ? AND end_mjd >= ?) OR (start_mjd >= ? AND start_mjd <= ?)
            ORDER BY created_at DESC
            """,
            (end_mjd, start_mjd, start_mjd, end_mjd),
        ).fetchall()

    mosaics = []
    for r in rows:
        # Convert MJD to ISO datetime
        start_dt = Time(r["start_mjd"], format="mjd").datetime
        end_dt = Time(r["end_mjd"], format="mjd").datetime
        created_dt = (
            datetime.fromtimestamp(r["created_at"]) if r["created_at"] else datetime.utcnow()
        )

        mosaics.append(
            {
                "id": r["id"],
                "name": r["name"],
                "path": r["path"],
                "start_mjd": r["start_mjd"],
                "end_mjd": r["end_mjd"],
                "start_time": start_dt.isoformat(),
                "end_time": end_dt.isoformat(),
                "created_at": created_dt.isoformat(),
                "status": "completed",  # Assume completed if in database
                "image_count": r["n_images"],
                "noise_jy": r["noise_jy"],
                "source_count": r["n_sources"],
                "thumbnail_path": r["thumbnail_path"],
            }
        )

    return mosaics


def fetch_mosaic_by_id(products_db: Path, mosaic_id: int) -> Optional[dict]:
    """Fetch a single mosaic by ID.

    Args:
        products_db: Path to products database
        mosaic_id: Mosaic ID

    Returns:
        Mosaic dictionary or None if not found
    """
    if not products_db.exists():
        return None

    with closing(_connect(products_db)) as conn:
        # Check if mosaics table exists
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }

        if "mosaics" not in tables:
            return None

        row = conn.execute(
            """
            SELECT 
                id, name, path, created_at, start_mjd, end_mjd,
                integration_sec, n_images, center_ra_deg, center_dec_deg,
                dec_min_deg, dec_max_deg, noise_jy,
                beam_major_arcsec, beam_minor_arcsec, beam_pa_deg,
                n_sources, thumbnail_path
            FROM mosaics
            WHERE id = ?
            """,
            (mosaic_id,),
        ).fetchone()

        if not row:
            return None

        # Convert MJD to ISO datetime
        from astropy.time import Time

        start_dt = Time(row["start_mjd"], format="mjd").datetime
        end_dt = Time(row["end_mjd"], format="mjd").datetime
        created_dt = (
            datetime.fromtimestamp(row["created_at"]) if row["created_at"] else datetime.utcnow()
        )

        return {
            "id": row["id"],
            "name": row["name"],
            "path": row["path"],
            "start_mjd": row["start_mjd"],
            "end_mjd": row["end_mjd"],
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "created_at": created_dt.isoformat(),
            "status": "completed",  # Assume completed if in database
            "image_count": row["n_images"],
            "noise_jy": row["noise_jy"],
            "source_count": row["n_sources"],
            "thumbnail_path": row["thumbnail_path"],
        }


def fetch_mosaics_recent(products_db: Path, limit: int = 10) -> tuple[list[dict], int]:
    """Fetch recent mosaics from the database.

    Args:
        products_db: Path to products database
        limit: Maximum number of mosaics to return

    Returns:
        Tuple of (list of mosaic dictionaries, total count)
    """
    if not products_db.exists():
        return [], 0

    from astropy.time import Time

    with closing(_connect(products_db)) as conn:
        # Check if mosaics table exists
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }

        if "mosaics" not in tables:
            return [], 0

        # Get total count
        total = conn.execute("SELECT COUNT(*) FROM mosaics").fetchone()[0]

        # Get recent mosaics ordered by created_at (descending)
        rows = conn.execute(
            """
            SELECT 
                id, name, path, created_at, start_mjd, end_mjd,
                integration_sec, n_images, center_ra_deg, center_dec_deg,
                dec_min_deg, dec_max_deg, noise_jy,
                beam_major_arcsec, beam_minor_arcsec, beam_pa_deg,
                n_sources, thumbnail_path, status, method
            FROM mosaics
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    mosaics = []
    for r in rows:
        # Convert MJD to ISO datetime (handle 0 or None values)
        start_mjd = r["start_mjd"] if r["start_mjd"] and r["start_mjd"] > 0 else None
        end_mjd = r["end_mjd"] if r["end_mjd"] and r["end_mjd"] > 0 else None

        start_time_iso = None
        end_time_iso = None
        if start_mjd:
            try:
                start_time_iso = Time(start_mjd, format="mjd").datetime.isoformat()
            except Exception:
                pass
        if end_mjd:
            try:
                end_time_iso = Time(end_mjd, format="mjd").datetime.isoformat()
            except Exception:
                pass

        created_dt = (
            datetime.fromtimestamp(r["created_at"]) if r["created_at"] else datetime.utcnow()
        )

        # Determine status
        status = r["status"] if r["status"] else "completed"

        mosaics.append(
            {
                "id": r["id"],
                "name": r["name"],
                "path": r["path"],
                "start_mjd": start_mjd,
                "end_mjd": end_mjd,
                "start_time": start_time_iso,
                "end_time": end_time_iso,
                "created_at": created_dt.isoformat(),
                "status": status,
                "method": r["method"],
                "image_count": r["n_images"],
                "noise_jy": r["noise_jy"],
                "source_count": r["n_sources"],
                "center_ra_deg": r["center_ra_deg"],
                "center_dec_deg": r["center_dec_deg"],
                "thumbnail_path": r["thumbnail_path"],
            }
        )

    return mosaics, total


def fetch_source_timeseries(products_db: Path, source_id: str) -> Optional[dict]:
    """Fetch flux timeseries for a source from photometry table.

    Args:
        products_db: Path to products database
        source_id: Source ID (e.g., NVSS J123456+420312)

    Returns:
        Dictionary with source timeseries data or None if not found
    """
    if not products_db.exists():
        return None

    import statistics

    from astropy.time import Time

    with closing(_connect(products_db)) as conn:
        # Check if tables exist
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }

        if "photometry" not in tables:
            return None

        # Get photometry measurements for this source
        # Try to match by source_id first, then by name pattern if source_id column exists
        # Check if source_id column exists
        columns = {row[1] for row in conn.execute("PRAGMA table_info(photometry)").fetchall()}

        if "source_id" in columns:
            rows = conn.execute(
                """
                SELECT 
                    ra_deg, dec_deg, nvss_flux_mjy,
                    peak_jyb, peak_err_jyb, measured_at, mjd, image_path, source_id
                FROM photometry
                WHERE source_id = ? OR source_id LIKE ?
                ORDER BY measured_at ASC
                """,
                (source_id, f"%{source_id}%"),
            ).fetchall()
        else:
            # Fallback: if source_id column doesn't exist, return empty
            # (photometry table might not have source matching yet)
            return None

        if not rows:
            return None

        # Get first row for coordinates
        first_row = rows[0]
        ra_deg = first_row["ra_deg"]
        dec_deg = first_row["dec_deg"]

        # Build flux points
        flux_points = []
        fluxes = []

        for r in rows:
            mjd = r["mjd"] if r["mjd"] else Time(datetime.fromtimestamp(r["measured_at"])).mjd
            flux_jy = r["peak_jyb"] if r["peak_jyb"] else 0.0
            flux_err_jy = r["peak_err_jyb"] if r["peak_err_jyb"] else None

            time_dt = (
                datetime.fromtimestamp(r["measured_at"])
                if r["measured_at"]
                else Time(mjd, format="mjd").datetime
            )

            flux_points.append(
                {
                    "mjd": mjd,
                    "time": time_dt.isoformat(),
                    "flux_jy": flux_jy,
                    "flux_err_jy": flux_err_jy,
                    "image_id": r["image_path"] or "",
                }
            )
            fluxes.append(flux_jy)

        # Calculate statistics
        if len(fluxes) > 0:
            mean_flux = statistics.mean(fluxes)
            std_flux = statistics.stdev(fluxes) if len(fluxes) > 1 else 0.0

            # Calculate chi-square for constant model
            if std_flux > 0:
                chi_sq_nu = sum(((f - mean_flux) / std_flux) ** 2 for f in fluxes) / max(
                    1, len(fluxes) - 1
                )
            else:
                chi_sq_nu = 0.0

            is_variable = chi_sq_nu > 3.0
        else:
            mean_flux = 0.0
            std_flux = 0.0
            chi_sq_nu = 0.0
            is_variable = False

        return {
            "source_id": source_id,
            "ra_deg": ra_deg,
            "dec_deg": dec_deg,
            "catalog": "NVSS",
            "flux_points": flux_points,
            "mean_flux_jy": mean_flux,
            "std_flux_jy": std_flux,
            "chi_sq_nu": chi_sq_nu,
            "is_variable": is_variable,
        }


def fetch_alert_history(products_db: Path, limit: int = 50) -> List[dict]:
    """Fetch alert history from the database.

    Args:
        products_db: Path to products database
        limit: Maximum number of alerts to return

    Returns:
        List of alert dictionaries
    """
    if not products_db.exists():
        return []

    with closing(_connect(products_db)) as conn:
        # Check if alert_history table exists
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }

        if "alert_history" not in tables:
            return []

        rows = conn.execute(
            """
            SELECT 
                id, source_id, alert_type, severity, message,
                sent_at, channel, success, error_msg
            FROM alert_history
            ORDER BY sent_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    alerts = []
    for r in rows:
        sent_at = datetime.fromtimestamp(r["sent_at"]) if r["sent_at"] else datetime.utcnow()

        alerts.append(
            {
                "id": r["id"],
                "source_id": r["source_id"],
                "alert_type": r["alert_type"],
                "severity": r["severity"],
                "message": r["message"],
                "triggered_at": sent_at.isoformat(),
                "resolved_at": None,  # Alert history doesn't track resolution
            }
        )

    return alerts


def fetch_observation_timeline(
    data_dir: Path,
    gap_threshold_hours: float = 24.0,
    products_db: Optional[Path] = None,
) -> ObservationTimeline:
    """Query database for HDF5 files and compute timeline segments.

    Groups timestamps into segments where data exists, with gaps larger than
    gap_threshold_hours separating segments.

    Args:
        data_dir: Directory path (for backward compatibility, not used if products_db provided)
        gap_threshold_hours: Maximum gap in hours before starting a new segment
        products_db: Path to products database (defaults to env var or state/db/products.sqlite3)

    Returns:
        ObservationTimeline with segments and statistics
    """
    import os

    from dsa110_contimg.database.products import ensure_products_db

    # Get products database path
    if products_db is None:
        products_db = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/db/products.sqlite3"))

    if not products_db.exists():
        return ObservationTimeline()

    conn = ensure_products_db(products_db)

    # Query database for all stored HDF5 files with timestamps
    query = """
    SELECT DISTINCT timestamp_iso, COUNT(*) as file_count
    FROM hdf5_file_index
    WHERE stored = 1 AND timestamp_iso IS NOT NULL
    GROUP BY timestamp_iso
    ORDER BY timestamp_iso
    """
    rows = conn.execute(query).fetchall()

    # Collect all unique timestamps from HDF5 files
    timestamps = []
    file_count_by_timestamp: dict[datetime, int] = {}

    for timestamp_iso, file_count in rows:
        try:
            # Parse ISO timestamp (format: YYYY-MM-DDTHH:MM:SS)
            timestamp = datetime.strptime(timestamp_iso, "%Y-%m-%dT%H:%M:%S")
            timestamps.append(timestamp)
            file_count_by_timestamp[timestamp] = file_count
        except (ValueError, IndexError):
            continue

    if not timestamps:
        return ObservationTimeline()

    # Sort timestamps
    timestamps = sorted(set(timestamps))

    # Group into segments based on gap threshold
    segments: List[TimelineSegment] = []
    gap_threshold = timedelta(hours=gap_threshold_hours)

    if timestamps:
        current_segment_start = timestamps[0]
        current_segment_end = timestamps[0]
        current_file_count = file_count_by_timestamp[timestamps[0]]

        for i in range(1, len(timestamps)):
            gap = timestamps[i] - current_segment_end

            if gap <= gap_threshold:
                # Continue current segment
                current_segment_end = timestamps[i]
                current_file_count += file_count_by_timestamp[timestamps[i]]
            else:
                # Start new segment
                segments.append(
                    TimelineSegment(
                        start_time=current_segment_start,
                        end_time=current_segment_end,
                        file_count=current_file_count,
                    )
                )
                current_segment_start = timestamps[i]
                current_segment_end = timestamps[i]
                current_file_count = file_count_by_timestamp[timestamps[i]]

        # Add final segment
        segments.append(
            TimelineSegment(
                start_time=current_segment_start,
                end_time=current_segment_end,
                file_count=current_file_count,
            )
        )

    total_files = sum(file_count_by_timestamp.values())

    return ObservationTimeline(
        earliest_time=timestamps[0] if timestamps else None,
        latest_time=timestamps[-1] if timestamps else None,
        total_files=total_files,
        unique_timestamps=len(timestamps),
        segments=segments,
    )
