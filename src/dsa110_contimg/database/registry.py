"""
Calibration registry database for continuum imaging pipeline.

This module manages a small SQLite database that tracks generated
calibration tables (K/B/G, etc.), their validity windows, and ordered
apply lists, so workers can consistently pick the right tables for a
given observation time.

**Registry Database Path Determination:**

The registry database path is determined consistently across CLI and pipeline
code using the following precedence order:

1. **CAL_REGISTRY_DB environment variable** (highest priority)
   - If set, uses this exact path
   - Example: `export CAL_REGISTRY_DB=/custom/path/cal_registry.sqlite3`

2. **PIPELINE_STATE_DIR environment variable**
   - If set, uses `{PIPELINE_STATE_DIR}/cal_registry.sqlite3`
   - Example: `export PIPELINE_STATE_DIR=/data/pipeline/state`

3. **Default path** (lowest priority)
   - Pipeline: `{config.paths.state_dir}/cal_registry.sqlite3` (defaults to `state/cal_registry.sqlite3`)
   - CLI: `/data/dsa110-contimg/state/cal_registry.sqlite3`

This ensures that CLI and pipeline use the same registry database when
environment variables are set consistently.

Schema (tables):
- caltables: one row per calibration table file
    id                INTEGER PRIMARY KEY
    set_name          TEXT            -- logical set/group name
    path              TEXT UNIQUE     -- filesystem path to cal table
    table_type        TEXT            -- e.g., K, BA, BP, GA, GP, 2G, FLUX
    order_index       INTEGER         -- apply order within the set
    cal_field         TEXT            -- source/field used to solve
    refant            TEXT            -- reference antenna
    created_at        REAL            -- time.time() when registered
    valid_start_mjd   REAL            -- start of validity window (MJD)
    valid_end_mjd     REAL            -- end of validity window (MJD)
    status            TEXT            -- active|retired|failed
    notes             TEXT            -- free-form notes
    source_ms_path    TEXT            -- input MS that generated this caltable
    solver_command    TEXT            -- full CASA command executed
    solver_version    TEXT            -- CASA version used
    solver_params     TEXT            -- JSON: all calibration parameters
    quality_metrics   TEXT            -- JSON: SNR, flagged_fraction, etc.

Convenience:
- register_set_from_prefix: scans on-disk tables with a common prefix and
  registers a standard apply order.
- get_active_applylist: returns ordered list of table paths for a given MJD.
"""

import json
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

DEFAULT_ORDER = [
    ("K", 10),  # delays
    ("BA", 20),  # bandpass amplitude
    ("BP", 30),  # bandpass phase
    ("GA", 40),  # gain amplitude
    ("GP", 50),  # gain phase
    ("2G", 60),  # short-timescale ap gains (optional)
    ("FLUX", 70),  # fluxscale table (optional)
]


@dataclass
class CalTableRow:
    set_name: str
    path: str
    table_type: str
    order_index: int
    cal_field: Optional[str]
    refant: Optional[str]
    valid_start_mjd: Optional[float]
    valid_end_mjd: Optional[float]
    status: str = "active"
    notes: Optional[str] = None
    source_ms_path: Optional[str] = None
    solver_command: Optional[str] = None
    solver_version: Optional[str] = None
    solver_params: Optional[Dict[str, Any]] = None
    quality_metrics: Optional[Dict[str, Any]] = None


def ensure_db(path: Path) -> sqlite3.Connection:
    """Ensure database exists with current schema, migrating if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))

    # Create table with current schema
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS caltables (
            id INTEGER PRIMARY KEY,
            set_name TEXT NOT NULL,
            path TEXT NOT NULL UNIQUE,
            table_type TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            cal_field TEXT,
            refant TEXT,
            created_at REAL NOT NULL,
            valid_start_mjd REAL,
            valid_end_mjd REAL,
            status TEXT NOT NULL,
            notes TEXT,
            source_ms_path TEXT,
            solver_command TEXT,
            solver_version TEXT,
            solver_params TEXT,
            quality_metrics TEXT
        )
        """
    )

    # Migrate existing databases by adding new columns if they don't exist
    _migrate_schema(conn)

    # Create indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_caltables_set ON caltables(set_name)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_caltables_valid "
        "ON caltables(valid_start_mjd, valid_end_mjd)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_caltables_source " "ON caltables(source_ms_path)")
    conn.commit()
    return conn


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Migrate existing database schema to add provenance columns."""
    cursor = conn.cursor()

    # Get existing columns
    cursor.execute("PRAGMA table_info(caltables)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    # Add missing provenance columns
    new_columns = [
        ("source_ms_path", "TEXT"),
        ("solver_command", "TEXT"),
        ("solver_version", "TEXT"),
        ("solver_params", "TEXT"),
        ("quality_metrics", "TEXT"),
    ]

    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            try:
                conn.execute(f"ALTER TABLE caltables ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError as e:
                # Column might already exist from concurrent migration
                if "duplicate column" not in str(e).lower():
                    raise

    # Create index on source_ms_path if column exists
    if "source_ms_path" in existing_columns or any(
        name == "source_ms_path" for name, _ in new_columns
    ):
        try:
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_caltables_source " "ON caltables(source_ms_path)"
            )
        except sqlite3.OperationalError:
            # Index might already exist
            pass

    conn.commit()


def _detect_type_from_filename(path: Path) -> Optional[str]:
    name = path.name.lower()
    # Common CASA table suffixes used in this repo
    if name.endswith("_kcal"):
        return "K"
    if name.endswith("_2kcal"):
        return "K"  # treat fast K as K; generally not applied separately
    if name.endswith("_bacal"):
        return "BA"
    if name.endswith("_bpcal"):
        return "BP"
    if name.endswith("_gacal"):
        return "GA"
    if name.endswith("_gpcal"):
        return "GP"
    if name.endswith("_2gcal"):
        return "2G"
    if name.endswith("_flux.cal") or name.endswith("_fluxcal"):
        return "FLUX"
    return None


def register_set(
    db_path: Path,
    set_name: str,
    rows: Sequence[CalTableRow],
    *,
    upsert: bool = True,
) -> None:
    conn = ensure_db(db_path)
    now = time.time()
    with conn:
        for r in rows:
            # Serialize JSON fields
            solver_params_json = json.dumps(r.solver_params) if r.solver_params else None
            quality_metrics_json = json.dumps(r.quality_metrics) if r.quality_metrics else None

            if upsert:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO caltables(
                        set_name, path, table_type, order_index, cal_field, refant,
                        created_at, valid_start_mjd, valid_end_mjd, status, notes,
                        source_ms_path, solver_command, solver_version, solver_params,
                        quality_metrics
                    )
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        r.set_name,
                        os.fspath(r.path),
                        r.table_type,
                        int(r.order_index),
                        r.cal_field,
                        r.refant,
                        now,
                        r.valid_start_mjd,
                        r.valid_end_mjd,
                        r.status,
                        r.notes,
                        r.source_ms_path,
                        r.solver_command,
                        r.solver_version,
                        solver_params_json,
                        quality_metrics_json,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO caltables(
                        set_name, path, table_type, order_index, cal_field, refant,
                        created_at, valid_start_mjd, valid_end_mjd, status, notes,
                        source_ms_path, solver_command, solver_version, solver_params,
                        quality_metrics
                    )
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        r.set_name,
                        os.fspath(r.path),
                        r.table_type,
                        int(r.order_index),
                        r.cal_field,
                        r.refant,
                        now,
                        r.valid_start_mjd,
                        r.valid_end_mjd,
                        r.status,
                        r.notes,
                        r.source_ms_path,
                        r.solver_command,
                        r.solver_version,
                        solver_params_json,
                        quality_metrics_json,
                    ),
                )


def register_set_from_prefix(
    db_path: Path,
    set_name: str,
    prefix: Path,
    *,
    cal_field: Optional[str],
    refant: Optional[str],
    valid_start_mjd: Optional[float],
    valid_end_mjd: Optional[float],
    status: str = "active",
) -> List[CalTableRow]:
    """Register tables found with a common prefix.

    Example prefix: "/data/ms/calpass_J1234+5678" where files named
    calpass_J1234+5678_kcal, _bacal, _bpcal, _gacal, _gpcal, etc.
    """
    parent = prefix.parent
    base = prefix.name
    found: List[Tuple[str, Path]] = []
    for p in parent.glob(base + "*"):
        if not p.is_dir():
            continue
        t = _detect_type_from_filename(p)
        if t is None:
            continue
        found.append((t, p))

    # Determine apply order using DEFAULT_ORDER, then any extras appended
    order_map = {t: oi for t, oi in DEFAULT_ORDER}
    rows: List[CalTableRow] = []
    extras: List[Tuple[str, Path]] = []
    for t, p in found:
        if t in order_map:
            oi = order_map[t]
        else:
            extras.append((t, p))
            continue
        rows.append(
            CalTableRow(
                set_name=set_name,
                path=str(p),
                table_type=t,
                order_index=oi,
                cal_field=cal_field,
                refant=refant,
                valid_start_mjd=valid_start_mjd,
                valid_end_mjd=valid_end_mjd,
                status=status,
                notes=None,
            )
        )

    # Append extras at the end in alpha order
    start_idx = max([oi for _, oi in DEFAULT_ORDER] + [60]) + 10
    for i, (t, p) in enumerate(sorted(extras)):
        rows.append(
            CalTableRow(
                set_name=set_name,
                path=str(p),
                table_type=t,
                order_index=start_idx + 10 * i,
                cal_field=cal_field,
                refant=refant,
                valid_start_mjd=valid_start_mjd,
                valid_end_mjd=valid_end_mjd,
                status=status,
                notes=None,
            )
        )

    if rows:
        register_set(db_path, set_name, rows, upsert=True)
    return rows


def retire_set(db_path: Path, set_name: str, *, reason: Optional[str] = None) -> None:
    conn = ensure_db(db_path)
    with conn:
        conn.execute(
            "UPDATE caltables SET status = 'retired', "
            "notes = COALESCE(notes,'') || ? WHERE set_name = ?",
            (f" Retired: {reason or ''}", set_name),
        )


def list_sets(db_path: Path) -> List[Tuple[str, int, int, int]]:
    conn = ensure_db(db_path)
    cur = conn.execute(
        """
        SELECT set_name,
               COUNT(*) AS nrows,
               SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS n_active,
               MIN(order_index) AS min_order
          FROM caltables
      GROUP BY set_name
      ORDER BY MAX(created_at) DESC
        """
    )
    return [(r[0], r[1], r[2], r[3]) for r in cur.fetchall()]


def get_active_applylist(db_path: Path, mjd: float, set_name: Optional[str] = None) -> List[str]:
    """Return ordered list of active tables applicable to mjd.

    When set_name is provided, restrict to that group; otherwise choose among
    active sets whose validity window includes mjd. If multiple sets match,
    pick the most recently created set (by created_at max) as winner.

    **Compatibility Validation:**

    When multiple sets overlap, this function validates compatibility by checking:
    - Same reference antenna (refant)
    - Same calibration field (cal_field)

    If incompatible sets overlap, a warning is logged and the newest set is still
    selected, but users should be aware of potential calibration inconsistencies.
    """
    import logging

    logger = logging.getLogger(__name__)

    conn = ensure_db(db_path)
    if set_name:
        rows = conn.execute(
            """
            SELECT path FROM caltables
             WHERE set_name = ? AND status = 'active'
             ORDER BY order_index ASC
            """,
            (set_name,),
        ).fetchall()
        return [r[0] for r in rows]

    # Select all sets that cover mjd (for compatibility checking)
    all_matching_sets = conn.execute(
        """
        SELECT DISTINCT set_name, MAX(created_at) AS t
          FROM caltables
         WHERE status = 'active'
           AND (valid_start_mjd IS NULL OR valid_start_mjd <= ?)
           AND (valid_end_mjd   IS NULL OR valid_end_mjd   >= ?)
      GROUP BY set_name
      ORDER BY t DESC
        """,
        (mjd, mjd),
    ).fetchall()

    if not all_matching_sets:
        return []

    # If multiple sets match, check compatibility
    if len(all_matching_sets) > 1:
        # Get metadata for all matching sets
        set_metadata = {}
        for set_name_row, _ in all_matching_sets:
            rows = conn.execute(
                """
                SELECT DISTINCT cal_field, refant
                  FROM caltables
                 WHERE set_name = ? AND status = 'active'
                 LIMIT 1
                """,
                (set_name_row,),
            ).fetchone()
            if rows:
                set_metadata[set_name_row] = {
                    "cal_field": rows[0],
                    "refant": rows[1],
                }

        # Check compatibility between sets
        set_names = [s[0] for s in all_matching_sets]
        newest_set = set_names[0]
        newest_metadata = set_metadata.get(newest_set, {})

        for other_set in set_names[1:]:
            other_metadata = set_metadata.get(other_set, {})

            # Check refant compatibility
            if (
                newest_metadata.get("refant")
                and other_metadata.get("refant")
                and newest_metadata["refant"] != other_metadata["refant"]
            ):
                logger.warning(
                    f"Overlapping calibration sets have different reference antennas: "
                    f"'{newest_set}' uses refant={newest_metadata['refant']}, "
                    f"'{other_set}' uses refant={other_metadata['refant']}. "
                    f"Selecting newest set '{newest_set}' but calibration may be inconsistent."
                )

            # Check cal_field compatibility
            if (
                newest_metadata.get("cal_field")
                and other_metadata.get("cal_field")
                and newest_metadata["cal_field"] != other_metadata["cal_field"]
            ):
                logger.warning(
                    f"Overlapping calibration sets have different calibration fields: "
                    f"'{newest_set}' uses field={newest_metadata['cal_field']}, "
                    f"'{other_set}' uses field={other_metadata['cal_field']}. "
                    f"Selecting newest set '{newest_set}' but calibration may be inconsistent."
                )

    # Select winner set by created_at (most recent)
    chosen = all_matching_sets[0][0]
    out = conn.execute(
        "SELECT path FROM caltables WHERE set_name = ? AND status='active' ORDER BY order_index ASC",
        (chosen,),
    ).fetchall()
    return [r[0] for r in out]


def register_and_verify_caltables(
    registry_db: Path,
    set_name: str,
    table_prefix: Path,
    *,
    cal_field: Optional[str],
    refant: Optional[str],
    valid_start_mjd: Optional[float],
    valid_end_mjd: Optional[float],
    mid_mjd: Optional[float] = None,
    status: str = "active",
    verify_discoverable: bool = True,
) -> List[str]:
    """Register calibration tables and verify they are discoverable.

    This is a robust wrapper around register_set_from_prefix that:
    1. Registers tables (idempotent via upsert)
    2. Verifies tables are discoverable after registration
    3. Returns list of registered table paths

    Args:
        registry_db: Path to calibration registry database
        set_name: Logical calibration set name
        table_prefix: Filesystem prefix for calibration tables
        cal_field: Field used for calibration solve
        refant: Reference antenna used
        valid_start_mjd: Start of validity window (MJD)
        valid_end_mjd: End of validity window (MJD)
        mid_mjd: Optional MJD midpoint for verification (if None, uses valid window midpoint)
        status: Status for registered tables (default: "active")
        verify_discoverable: Whether to verify tables are discoverable after registration

    Returns:
        List of registered calibration table paths (ordered by apply order)

    Raises:
        RuntimeError: If registration fails or tables are not discoverable
        ValueError: If no tables found with prefix
    """
    import logging

    logger = logging.getLogger(__name__)

    # Ensure registry DB exists
    ensure_db(registry_db)

    # Register tables (idempotent via upsert=True)
    try:
        registered_rows = register_set_from_prefix(
            registry_db,
            set_name,
            table_prefix,
            cal_field=cal_field,
            refant=refant,
            valid_start_mjd=valid_start_mjd,
            valid_end_mjd=valid_end_mjd,
            status=status,
        )
    except Exception as e:
        error_msg = f"Failed to register calibration tables with prefix {table_prefix}: {e}"
        logger.error(error_msg, exc_info=True)
        raise RuntimeError(error_msg) from e

    if not registered_rows:
        error_msg = (
            f"No calibration tables found with prefix {table_prefix}. "
            f"Cannot register empty set."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    registered_paths = [row.path for row in registered_rows]
    logger.info(
        "Registered %d calibration tables in set '%s'",
        len(registered_paths),
        set_name,
    )

    # Verify tables are discoverable if requested
    if verify_discoverable:
        try:
            # Use mid_mjd if provided, otherwise use midpoint of validity window
            if mid_mjd is None:
                if valid_start_mjd is not None and valid_end_mjd is not None:
                    mid_mjd = (valid_start_mjd + valid_end_mjd) / 2.0
                else:
                    # Fallback: use current time
                    from astropy.time import Time

                    mid_mjd = Time.now().mjd
                    logger.warning(
                        "Using current time (%.6f) for verification "
                        "since validity window not fully specified",
                        mid_mjd,
                    )

            # Verify tables are discoverable via registry lookup
            discovered = get_active_applylist(registry_db, mid_mjd, set_name=set_name)

            if not discovered:
                error_msg = (
                    f"Registered tables are not discoverable: "
                    f"get_active_applylist returned empty list for set '{set_name}' "
                    f"at MJD {mid_mjd:.6f}"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Verify all registered tables are in discovered list
            discovered_set = set(discovered)
            registered_set = set(registered_paths)
            missing = registered_set - discovered_set
            if missing:
                error_msg = (
                    f"Some registered tables are not discoverable: {missing}. "
                    f"Registered: {registered_set}, Discovered: {discovered_set}"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Verify discovered tables exist on filesystem
            missing_files = [p for p in discovered if not Path(p).exists()]
            if missing_files:
                error_msg = (
                    f"Discovered calibration tables do not exist on filesystem: " f"{missing_files}"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            logger.info(
                "✓ Verified %d calibration tables are discoverable " "and exist on filesystem",
                len(discovered),
            )

        except Exception as e:
            # Registration succeeded but verification failed
            # Rollback: retire the set so it's not used
            try:
                retire_set(registry_db, set_name, reason=f"Verification failed: {e}")
                logger.warning(
                    "Retired calibration set '%s' due to verification failure",
                    set_name,
                )
            except Exception as rollback_error:
                logger.error(
                    f"Failed to rollback registration after verification failure: "
                    f"{rollback_error}",
                    exc_info=True,
                )

            error_msg = (
                f"Calibration tables registered but not discoverable: {e}. "
                f"Set '{set_name}' has been retired."
            )
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

    return registered_paths
