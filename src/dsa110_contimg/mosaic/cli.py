"""
CLI for planning and building simple mosaics from 5-minute image tiles.

Phase 1: record mosaic plan (list of tiles) into products DB.
Phase 2: if CASA is available and tiles are consistent, build a mean mosaic.
"""

import argparse
import os
import sqlite3
import time
from pathlib import Path
from typing import List, Optional, Tuple

from dsa110_contimg.database.products import ensure_products_db
try:
    from dsa110_contimg.utils.tempdirs import prepare_temp_environment
except Exception:  # pragma: no cover
    prepare_temp_environment = None  # type: ignore


def _ensure_mosaics_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mosaics (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            created_at REAL NOT NULL,
            status TEXT NOT NULL,
            method TEXT,
            tiles TEXT NOT NULL,
            output_path TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mosaics_name ON mosaics(name)"
    )


def _fetch_tiles(products_db: Path, *, since: Optional[float], until: Optional[float], pbcor_only: bool = True) -> List[str]:
    tiles: List[str] = []
    with ensure_products_db(products_db) as conn:
        q = "SELECT path, created_at, pbcor FROM images"
        where = []
        params: List[object] = []
        if pbcor_only:
            where.append("pbcor = 1")
        if since is not None:
            where.append("created_at >= ?")
            params.append(float(since))
        if until is not None:
            where.append("created_at <= ?")
            params.append(float(until))
        if where:
            q += " WHERE " + " AND ".join(where)
        q += " ORDER BY created_at ASC"
        for r in conn.execute(q, params).fetchall():
            p = r["path"] if isinstance(r, sqlite3.Row) else r[0]
            if p and os.path.isdir(p):
                tiles.append(p)
    return tiles


def cmd_plan(args: argparse.Namespace) -> int:
    pdb = Path(args.products_db)
    name = args.name
    since = args.since
    until = args.until
    tiles = _fetch_tiles(pdb, since=since, until=until, pbcor_only=not args.include_unpbcor)
    if not tiles:
        print("No tiles found for the specified window")
        return 1
    with ensure_products_db(pdb) as conn:
        _ensure_mosaics_table(conn)
        conn.execute(
            "INSERT INTO mosaics(name, created_at, status, method, tiles) VALUES(?,?,?,?,?)",
            (name, time.time(), "planned", args.method, "\n".join(tiles)),
        )
        conn.commit()
    print(f"Planned mosaic '{name}' with {len(tiles)} tiles")
    return 0


def _check_consistent_tiles(tiles: List[str]) -> Tuple[bool, Optional[str]]:
    try:
        from casatasks import imhead
    except Exception as e:
        return False, f"CASA not available: {e}"
    ref = None
    for t in tiles:
        try:
            h = imhead(imagename=t, mode='list')
        except Exception as e:
            return False, f"imhead failed for {t}: {e}"
        key = (h.get('shape'), h.get('cdelt1'), h.get('cdelt2'))
        if ref is None:
            ref = key
        elif key != ref:
            return False, "Tiles have inconsistent grids/cell sizes"
    return True, None


def cmd_build(args: argparse.Namespace) -> int:
    pdb = Path(args.products_db)
    name = args.name
    out = Path(args.output).with_suffix("")
    with ensure_products_db(pdb) as conn:
        _ensure_mosaics_table(conn)
        row = conn.execute("SELECT id, tiles, method FROM mosaics WHERE name = ?", (name,)).fetchone()
        if row is None:
            print("Mosaic plan not found; create with 'plan' first")
            return 1
        tiles = str(row[1]).splitlines()
        method = str(row[2] or 'mean')

    ok, reason = _check_consistent_tiles(tiles)
    if not ok:
        print(f"Cannot build mosaic: {reason}")
        return 2

    try:
        # Keep immath temp products under scratch and avoid polluting CWD
        try:
            if prepare_temp_environment is not None:
                prepare_temp_environment(os.getenv('CONTIMG_SCRATCH_DIR') or '/scratch/dsa110-contimg', cwd_to=out.parent)
        except Exception:
            pass
        from casatasks import immath
        expr = f"({'+'.join([f'IM{i}' for i in range(len(tiles))])})/{len(tiles)}"
        immath(imagename=tiles, expr=expr, outfile=str(out))
        # Export FITS for the mosaic image for downstream photometry
        try:
            from casatasks import exportfits
            exportfits(imagename=str(out), fitsimage=str(out) + ".fits", overwrite=True)
        except Exception as exc:
            print(f"exportfits warning: {exc}")
        with ensure_products_db(pdb) as conn:
            conn.execute("UPDATE mosaics SET status='built', output_path=? WHERE name=?", (str(out), name))
            conn.commit()
        print(f"Built mosaic to {out}")
        return 0
    except Exception as e:
        print(f"Mosaic build failed: {e}")
        return 3


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Mosaic planner/builder")
    sub = p.add_subparsers(dest='cmd')
    sp = sub.add_parser('plan', help='Plan a mosaic from products DB tiles')
    sp.add_argument('--products-db', default='state/products.sqlite3')
    sp.add_argument('--name', required=True)
    sp.add_argument('--since', type=float, help='Only include tiles created_at >= since (epoch seconds)')
    sp.add_argument('--until', type=float, help='Only include tiles created_at <= until (epoch seconds)')
    sp.add_argument('--method', default='mean')
    sp.add_argument('--include-unpbcor', action='store_true', help='Include non-pbcor tiles')
    sp.set_defaults(func=cmd_plan)

    sp = sub.add_parser('build', help='Build a mosaic from a planned set')
    sp.add_argument('--products-db', default='state/products.sqlite3')
    sp.add_argument('--name', required=True)
    sp.add_argument('--output', required=True, help='Output image base path (CASA image)')
    sp.set_defaults(func=cmd_build)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    if not hasattr(args, 'func'):
        p.print_help()
        return 2
    return args.func(args)


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
