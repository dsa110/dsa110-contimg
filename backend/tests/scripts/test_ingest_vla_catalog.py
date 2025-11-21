#!/usr/bin/env python3
"""
Smoke test for VLA calibrator SQLite ingestion.

Creates a tiny parsed VLA CSV, ingests to SQLite, and verifies content
and the 20cm view. Run with casa6 Python.

Usage:
  /opt/miniforge/envs/casa6/bin/python scripts/test_ingest_vla_catalog.py
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def ensure_repo_on_path() -> None:
    repo = Path(__file__).resolve().parents[2]
    src = repo / "src"
    if os.fspath(src) not in os.sys.path:
        os.sys.path.insert(0, os.fspath(src))


def write_mock_vla_csv(p: Path) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        """J2000_NAME,RA_J2000,DEC_J2000,BAND,FLUX_JY
0834+555,08:34:54.90,+55:34:21.0,20cm,2.5
0702+445,07:02:15.00,+44:30:00.0,20cm,1.1
""",
        encoding="utf-8",
    )
    return p


def main() -> int:
    ensure_repo_on_path()
    from dsa110_contimg.calibration.ingest_vla import ingest_vla  # type: ignore

    csv = write_mock_vla_csv(Path("/tmp/vla_parsed.csv"))
    out_db = Path("state/catalogs/vla_calibrators.sqlite3")

    dbp = ingest_vla(os.fspath(csv), os.fspath(out_db), band="20cm")
    print(f"Wrote DB: {dbp}")
    with sqlite3.connect(os.fspath(dbp)) as conn:
        n_cal = conn.execute("SELECT COUNT(*) FROM calibrators").fetchone()[0]
        n_flux = conn.execute("SELECT COUNT(*) FROM fluxes").fetchone()[0]
        print(f"Counts: calibrators={n_cal} fluxes={n_flux}")
        row = conn.execute(
            "SELECT name, ra_deg, dec_deg FROM calibrators WHERE name='0834+555'"
        ).fetchone()
        print("0834 coords:", row)
        vrow = conn.execute("SELECT name, flux_jy FROM vla_20cm WHERE name='0834+555'").fetchone()
        print("0834 20cm flux:", vrow)
        # meta
        meta = conn.execute(
            "SELECT key,value FROM meta WHERE key in ('build_time_iso','source_sha256')"
        ).fetchall()
        print("META:", meta)
    # Basic asserts
    assert n_cal == 2 and n_flux == 2, "unexpected row counts"
    assert vrow is not None and abs(float(vrow[1]) - 2.5) < 1e-6, "flux mismatch"
    print("VLA ingest smoke test OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
