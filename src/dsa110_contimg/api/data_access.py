"""Data access helpers for the monitoring API."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import List
import json as _json

from dsa110_contimg.api.config import ApiConfig
from dsa110_contimg.api.models import CalibrationSet, ProductEntry, QueueGroup, QueueStats, CalibratorMatch, CalibratorMatchGroup


QUEUE_COLUMNS = [
    "group_id",
    "state",
    "received_at",
    "last_update",
    "expected_subbands",
]


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def fetch_queue_stats(queue_db: Path) -> QueueStats:
    with closing(_connect(queue_db)) as conn:
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
            return QueueStats(total=0, pending=0, in_progress=0, failed=0, completed=0, collecting=0)
        return QueueStats(
            total=row["total"] or 0,
            pending=row["pending"] or 0,
            in_progress=row["in_progress"] or 0,
            failed=row["failed"] or 0,
            completed=row["completed"] or 0,
            collecting=row["collecting"] or 0,
        )


def fetch_recent_queue_groups(queue_db: Path, config: ApiConfig, limit: int = 20) -> List[QueueGroup]:
    with closing(_connect(queue_db)) as conn:
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
                                weighted_flux=float(m.get("weighted_flux")) if m.get("weighted_flux") is not None else None,
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


def fetch_recent_calibrator_matches(queue_db: Path, limit: int = 50, matched_only: bool = False) -> List[CalibratorMatchGroup]:
    """Fetch recent groups with calibrator match info from ingest_queue."""
    with closing(_connect(queue_db)) as conn:
        base = (
            "SELECT group_id, has_calibrator, calibrators, received_at, last_update "
            "FROM ingest_queue WHERE (calibrators IS NOT NULL OR has_calibrator IS NOT NULL) "
        )
        if matched_only:
            base += "AND has_calibrator = 1 "
        base += "ORDER BY received_at DESC LIMIT ?"
        rows = conn.execute(base, (limit,)).fetchall()
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
                        weighted_flux=float(m.get("weighted_flux")) if m.get("weighted_flux") is not None else None,
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
