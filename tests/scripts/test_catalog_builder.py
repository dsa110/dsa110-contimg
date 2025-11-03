#!/usr/bin/env python3
"""
Smoke test for dsa110_contimg.catalog.build_master.

Creates tiny mock NVSS/VLASS/FIRST catalogs, builds the master SQLite DB,
and verifies tables/views and optional CSV export. Run with casa6 Python.

Usage:
  /opt/miniforge/envs/casa6/bin/python scripts/test_catalog_builder.py
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path
import csv


def ensure_repo_on_path() -> None:
    # Add repo src to sys.path if not already present
    repo = Path(__file__).resolve().parents[2]
    src = repo / "src"
    if os.fspath(src) not in sys.path:
        sys.path.insert(0, os.fspath(src))


def write_mock_catalogs(basedir: Path) -> tuple[Path, Path, Path]:
    basedir.mkdir(parents=True, exist_ok=True)
    nvss = basedir / "nvss.csv"
    vlass = basedir / "vlass.csv"
    first = basedir / "first.csv"
    nvss.write_text(
        """RAJ2000,DEJ2000,S1.4,SNR
10.0000,20.0000,100.0,60
10.0100,20.0050,300.0,120
""",
        encoding="utf-8",
    )
    vlass.write_text(
        """RA,Dec,Peak_mJy
10.0002,20.0003,80.0
10.0101,20.0051,260.0
""",
        encoding="utf-8",
    )
    first.write_text(
        """RA,Dec,Deconv_Maj,Deconv_Min
10.0002,20.0003,4.0,3.8
10.0101,20.0051,4.0,3.8
""",
        encoding="utf-8",
    )
    return nvss, vlass, first


def export_view_to_csv(db_path: Path, view: str, out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(os.fspath(db_path)) as conn, open(out_csv, "w", newline="", encoding="utf-8") as f:
        cur = conn.execute(f"SELECT * FROM {view}")
        cols = [c[0] for c in cur.description]
        w = csv.writer(f)
        w.writerow(cols)
        for row in cur.fetchall():
            w.writerow(row)


def main() -> int:
    ensure_repo_on_path()
    from dsa110_contimg.catalog.build_master import build_master  # type: ignore

    tmp = Path("/tmp/mastercat_test_run")
    nvss, vlass, first = write_mock_catalogs(tmp)
    out_db = Path("state/catalogs/master_sources.sqlite3")

    # Build the DB (mJy -> Jy), default thresholds yield 2 good and 1 final reference
    dbp = build_master(
        os.fspath(nvss),
        vlass_path=os.fspath(vlass),
        first_path=os.fspath(first),
        out_db=os.fspath(out_db),
        match_radius_arcsec=7.5,
        map_nvss={"ra": "RAJ2000", "dec": "DEJ2000", "flux": "S1.4", "snr": "SNR"},
        map_vlass={"ra": "RA", "dec": "Dec", "flux": "Peak_mJy"},
        map_first={"ra": "RA", "dec": "Dec", "maj": "Deconv_Maj", "min": "Deconv_Min"},
        nvss_flux_unit="mjy",
        vlass_flux_unit="mjy",
        goodref_snr_min=50.0,
        goodref_alpha_min=-1.2,
        goodref_alpha_max=0.2,
        finalref_snr_min=80.0,
        materialize_final=True,
    )
    print(f"Built DB: {dbp}")

    with sqlite3.connect(os.fspath(dbp)) as conn:
        n_sources = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        n_good = conn.execute("SELECT COUNT(*) FROM good_references").fetchone()[0]
        n_final = conn.execute("SELECT COUNT(*) FROM final_references").fetchone()[0]
        print(f"Counts: sources={n_sources} good={n_good} final={n_final}")
        rows = conn.execute(
            "SELECT source_id, ra_deg, dec_deg, s_nvss, s_vlass, alpha, resolved_flag, confusion_flag FROM sources ORDER BY source_id"
        ).fetchall()
        for r in rows:
            print("ROW:", r)
        meta = conn.execute(
            "SELECT key, value FROM meta WHERE key IN (" 
            "'build_time_iso','nvss_sha256','vlass_sha256','first_sha256','goodref_snr_min','finalref_snr_min')"
        ).fetchall()
        print("META:", meta)

    # Export final_references to CSV
    out_csv = Path("state/catalogs/final_refs.csv")
    export_view_to_csv(out_db, "final_references", out_csv)
    print(f"Exported CSV: {out_csv} size={out_csv.stat().st_size} bytes")
    # Show first few lines
    with open(out_csv, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            print(line.rstrip())
            if i >= 4:
                break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

