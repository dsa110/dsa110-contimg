"""
Cross-match transits with pointing history and UVH5 groups.
"""

from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import h5py
from astropy.time import Time
import astropy.units as u

from dsa110_contimg.calibration.schedule import DSA110_LOCATION, previous_transits
from dsa110_contimg.calibration.catalogs import read_vla_parsed_catalog_csv
from dsa110_contimg.database.products import ensure_products_db

SB_RE = re.compile(r"^(.+)_sb(\d{2})\.hdf5$")


def _read_dec_start_end(sb_path: str) -> Tuple[float | None, float | None, float | None]:
    """Read declination and time range from UVH5 file."""
    dec_rad = None
    jd0 = None
    jd1 = None
    with h5py.File(sb_path, "r") as f:
        if "time_array" in f:
            arr = np.asarray(f["time_array"])  # pyuvdata JD times
            if arr.size > 0:
                jd0 = float(arr[0])
                jd1 = float(arr[-1])
        # Try extra_keywords locations
        def _read_extra(name: str):
            try:
                if "extra_keywords" in f and name in f["extra_keywords"]:
                    return float(np.asarray(f["extra_keywords"][name]))
            except Exception:
                pass
            try:
                if (
                    "Header" in f
                    and "extra_keywords" in f["Header"]
                    and name in f["Header"]["extra_keywords"]
                ):
                    return float(np.asarray(f["Header"]["extra_keywords"][name]))
            except Exception:
                pass
            try:
                if name in f.attrs:
                    return float(f.attrs[name])
            except Exception:
                pass
            return None
        v = _read_extra("phase_center_dec")
        if v is not None and np.isfinite(v):
            dec_rad = float(v)
    dec_deg = float(np.degrees(dec_rad)) if (dec_rad is not None and np.isfinite(dec_rad)) else None
    return dec_deg, jd0, jd1


def _scan_complete_groups(in_root: str) -> Dict[str, List[str]]:
    """Scan for complete 16-subband groups."""
    acc: Dict[str, Dict[str, str]] = {}
    for dirpath, _, files in os.walk(in_root):
        for fn in files:
            m = SB_RE.match(fn)
            if not m:
                continue
            gid, sb = m.group(1), f"sb{m.group(2)}"
            d = acc.setdefault(gid, {})
            d[sb] = os.path.join(dirpath, fn)
    out: Dict[str, List[str]] = {}
    for gid, mp in acc.items():
        expected = [f"sb{i:02d}" for i in range(16)]
        if all(k in mp for k in expected):
            out[gid] = [mp[k] for k in expected]
    return out


def _ensure_transit_table(conn: sqlite3.Connection) -> None:
    """Ensure cal_transits table exists."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cal_transits (
            src_name TEXT NOT NULL,
            transit_mjd REAL NOT NULL,
            PRIMARY KEY (src_name, transit_mjd)
        )
        """
    )


def _write_transits(conn: sqlite3.Connection, name: str, ra_deg: float, *, days_back: int = 21) -> None:
    """Write previous N daily transits (including today) into cal_transits."""
    _ensure_transit_table(conn)
    now = Time.now()
    # Generate window from now backwards
    # Use previous_transits to get the last N transits
    transits = previous_transits(ra_deg, start_time=now, n=days_back)
    with conn:
        for t in transits:
            conn.execute(
                "INSERT OR IGNORE INTO cal_transits(src_name, transit_mjd) VALUES(?, ?)",
                (name, float(t.mjd)),
            )


def _ingest_pointing_from_groups(conn: sqlite3.Connection, groups: Dict[str, List[str]]) -> None:
    """Populate pointing_history from UVH5 groups (midpoint RA=LST at DSA-110, DEC from header)."""
    # ensure_products_db already created pointing_history table
    with conn:
        for gid, files in groups.items():
            dec_deg, jd0, jd1 = _read_dec_start_end(files[0])
            if dec_deg is None or jd0 is None or jd1 is None:
                continue
            mid = 0.5 * (jd0 + jd1)
            t = Time(mid, format="jd")
            ra_deg = t.sidereal_time("apparent", DSA110_LOCATION.lon).deg
            # upsert by timestamp
            conn.execute(
                "INSERT OR REPLACE INTO pointing_history(timestamp, ra_deg, dec_deg) VALUES(?,?,?)",
                (float(t.mjd), float(ra_deg), float(dec_deg)),
            )


def find_transit_groups(name: str,
                        input_dir: str,
                        products_db: str,
                        catalogs: List[str],
                        *,
                        dec_tolerance_deg: float = 1.5,
                        time_pad_minutes: float = 10.0,
                        days_back: int = 21) -> List[dict]:
    """Cross-match daily transits with pointing history and UVH5 groups.
    
    Args:
        name: Calibrator name
        input_dir: Directory containing UVH5 files
        products_db: Path to products database
        catalogs: List of VLA catalog paths
        dec_tolerance_deg: Declination tolerance (degrees)
        time_pad_minutes: Time padding around transit (minutes)
        days_back: Days to search back
        
    Returns:
        List of matching transit groups with metadata
    """
    # Calibrator coordinates
    ra_deg = dec_deg = None
    for p in catalogs:
        if not os.path.exists(p):
            continue
        try:
            df = read_vla_parsed_catalog_csv(p)
            if name in df.index:
                row = df.loc[name]
                try:
                    ra_deg = float(row["ra_deg"].iloc[0])
                    dec_deg = float(row["dec_deg"].iloc[0])
                except Exception:
                    ra_deg = float(row["ra_deg"])
                    dec_deg = float(row["dec_deg"])
                break
        except Exception:
            continue
    if ra_deg is None or dec_deg is None:
        raise RuntimeError(f"Calibrator {name} not found in catalogs: {catalogs}")

    # Ensure DB and ingest
    conn = ensure_products_db(Path(products_db))
    _write_transits(conn, name, ra_deg, days_back=days_back)

    groups = _scan_complete_groups(input_dir)
    _ingest_pointing_from_groups(conn, groups)

    # Build per-group time windows
    windows = {}
    meta = {}
    for gid, files in groups.items():
        d, jd0, jd1 = _read_dec_start_end(files[0])
        if d is None or jd0 is None or jd1 is None:
            continue
        windows[gid] = (jd0, jd1)
        meta[gid] = {"dec_deg": d, "files": files}

    pad_days = (time_pad_minutes * u.min).to(u.day).value

    # Cross-match
    rows = conn.execute(
        "SELECT transit_mjd FROM cal_transits WHERE src_name = ? ORDER BY transit_mjd DESC",
        (name,),
    ).fetchall()
    results: List[dict] = []
    for (tmjd,) in rows:
        # pick candidate groups whose dec close and whose window +/- pad contains tmjd
        for gid, (jd0, jd1) in windows.items():
            if abs(meta[gid]["dec_deg"] - dec_deg) > dec_tolerance_deg:
                continue
            if (jd0 - pad_days) <= tmjd <= (jd1 + pad_days):
                dt_min = abs((Time(0.5 * (jd0 + jd1), format="jd") - Time(tmjd, format="mjd")).to(u.min).value)
                results.append(
                    {
                        "group_id": gid,
                        "transit_iso": Time(tmjd, format="mjd").isot,
                        "group_start_iso": Time(jd0, format="jd").isot,
                        "group_end_iso": Time(jd1, format="jd").isot,
                        "dec_deg": meta[gid]["dec_deg"],
                        "delta_minutes_mid": dt_min,
                        "files": meta[gid]["files"],
                    }
                )
    # Sort by transit time desc then closeness
    results.sort(key=lambda r: (r["transit_iso"], -r["delta_minutes_mid"]), reverse=True)
    return results

