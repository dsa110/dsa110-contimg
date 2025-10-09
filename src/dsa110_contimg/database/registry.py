"""
Calibration registry database for continuum imaging pipeline.

This module manages a small SQLite database that tracks generated
calibration tables (K/B/G, etc.), their validity windows, and ordered
apply lists, so workers can consistently pick the right tables for a
given observation time.

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
    notes             TEXT

Convenience:
- register_set_from_prefix: scans on-disk tables with a common prefix and
  registers a standard apply order.
- get_active_applylist: returns ordered list of table paths for a given MJD.
"""

import os
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple


DEFAULT_ORDER = [
    ("K", 10),   # delays
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


def ensure_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
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
            notes TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_caltables_set ON caltables(set_name)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_caltables_valid ON caltables(valid_start_mjd, valid_end_mjd)"
    )
    conn.commit()
    return conn


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
            if upsert:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO caltables(set_name, path, table_type, order_index, cal_field, refant,
                                                    created_at, valid_start_mjd, valid_end_mjd, status, notes)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)
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
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO caltables(set_name, path, table_type, order_index, cal_field, refant,
                                                    created_at, valid_start_mjd, valid_end_mjd, status, notes)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)
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
            "UPDATE caltables SET status = 'retired', notes = COALESCE(notes,'') || ? WHERE set_name = ?",
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
    """
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

    # Select winner set by created_at among sets that cover mjd
    rows = conn.execute(
        """
        SELECT set_name, MAX(created_at) AS t
          FROM caltables
         WHERE status = 'active'
           AND (valid_start_mjd IS NULL OR valid_start_mjd <= ?)
           AND (valid_end_mjd   IS NULL OR valid_end_mjd   >= ?)
      GROUP BY set_name
      ORDER BY t DESC
         LIMIT 1
        """,
        (mjd, mjd),
    ).fetchall()
    if not rows:
        return []
    chosen = rows[0][0]
    out = conn.execute(
        "SELECT path FROM caltables WHERE set_name = ? AND status='active' ORDER BY order_index ASC",
        (chosen,),
    ).fetchall()
    return [r[0] for r in out]
