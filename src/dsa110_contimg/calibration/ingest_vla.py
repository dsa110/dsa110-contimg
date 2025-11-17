#!/opt/miniforge/envs/casa6/bin/python
"""
Ingest a parsed VLA calibrator catalog CSV into SQLite for fast lookups and provenance.

Schema:
  - calibrators(name PRIMARY KEY, ra_deg, dec_deg)
  - fluxes(name, band TEXT, freq_hz REAL, flux_jy REAL, sidx REAL, sidx_f0_hz REAL,
           PRIMARY KEY(name, band),
           FOREIGN KEY(name) REFERENCES calibrators(name) ON DELETE CASCADE)
  - meta(key PRIMARY KEY, value)

Views:
  - vla_20cm: flux at 20cm band if present

Usage:
  python -m dsa110_contimg.calibration.ingest_vla \
    --csv /path/parsed_vla.csv \
    --out state/catalogs/vla_calibrators.sqlite3 \
    --band 20cm
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from .catalogs import read_vla_parsed_catalog_with_flux


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _hash(path: str) -> tuple[str, int, int]:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return (h.hexdigest(), os.path.getsize(path), int(os.path.getmtime(path)))
    except Exception:
        return ("", 0, 0)


def ingest_vla(
    csv_path: str,
    out_db: str = "state/catalogs/vla_calibrators.sqlite3",
    *,
    band: str = "20cm",
) -> Path:
    df = read_vla_parsed_catalog_with_flux(csv_path, band=band)
    # df indexed by name with columns: ra_deg, dec_deg, flux_jy, sidx, sidx_f0_hz
    out = Path(out_db)
    _ensure_dir(out)
    with sqlite3.connect(os.fspath(out)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS calibrators (
                name TEXT PRIMARY KEY,
                ra_deg REAL NOT NULL,
                dec_deg REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fluxes (
                name TEXT NOT NULL,
                band TEXT NOT NULL,
                freq_hz REAL,
                flux_jy REAL,
                sidx REAL,
                sidx_f0_hz REAL,
                PRIMARY KEY(name, band),
                FOREIGN KEY(name) REFERENCES calibrators(name) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)"
        )
        # Overwrite content
        conn.execute("DELETE FROM fluxes")
        conn.execute("DELETE FROM calibrators")
        # Insert calibrators
        cal_rows = [
            (str(idx), float(r.ra_deg), float(r.dec_deg)) for idx, r in df.iterrows()
        ]
        conn.executemany(
            "INSERT OR REPLACE INTO calibrators(name, ra_deg, dec_deg) VALUES(?,?,?)",
            cal_rows,
        )
        # Insert flux entries for one band (and carry spectral index if present)
        fx_rows = []
        for idx, r in df.iterrows():
            fx_rows.append(
                (
                    str(idx),
                    band,
                    1.4e9 if band.lower() in ("20cm", "l", "l-band") else None,
                    float(r.get("flux_jy", float("nan"))),
                    (None if pd.isna(r.get("sidx", None)) else float(r.get("sidx"))),
                    (
                        None
                        if pd.isna(r.get("sidx_f0_hz", None))
                        else float(r.get("sidx_f0_hz"))
                    ),
                )
            )
        conn.executemany(
            "INSERT OR REPLACE INTO fluxes(name, band, freq_hz, flux_jy, sidx, sidx_f0_hz) VALUES(?,?,?,?,?,?)",
            fx_rows,
        )
        # Indices and views
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cal_radec ON calibrators(ra_deg, dec_deg)"
        )
        try:
            conn.execute("DROP VIEW IF EXISTS vla_20cm")
        except Exception:
            pass
        conn.execute(
            """
            CREATE VIEW vla_20cm AS
            SELECT c.name, c.ra_deg, c.dec_deg, f.flux_jy, f.sidx, f.sidx_f0_hz
            FROM calibrators c JOIN fluxes f ON c.name=f.name
            WHERE LOWER(f.band)='20cm'
            """
        )
        # Provenance
        sha, size, mtime = _hash(csv_path)
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('build_time_iso', ?)",
            (datetime.now(timezone.utc).isoformat(),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('source_csv', ?)",
            (os.fspath(csv_path),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('source_sha256', ?)", (sha,)
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('source_size', ?)",
            (str(size),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('source_mtime', ?)",
            (str(mtime),),
        )
        conn.commit()
    return out


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Ingest parsed VLA calibrator CSV into SQLite"
    )
    ap.add_argument("--csv", required=True, help="Path to parsed VLA calibrator CSV")
    ap.add_argument(
        "--out",
        default="state/catalogs/vla_calibrators.sqlite3",
        help="Output SQLite path",
    )
    ap.add_argument(
        "--band",
        default="20cm",
        help="Band name for the flux selection (default: 20cm)",
    )
    args = ap.parse_args(argv)
    try:
        outp = ingest_vla(args.csv, args.out, band=args.band)
        print(f"Wrote VLA calibrator DB: {outp}")
        return 0
    except Exception as e:
        print(f"VLA ingest failed: {e}")
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
