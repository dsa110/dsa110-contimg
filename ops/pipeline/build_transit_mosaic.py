#!/usr/bin/env python3
"""
Build a 1-hour mosaic around the VLA calibrator 0834+555:
- Identify central transit time from a curated subdir (if available), else use a provided time
- Create 12 groups at 5-minute cadence spanning +/- 30 minutes
- Convert each group (16 subbands) to a group MS using the direct-subband writer
- Image each MS with tclean (pbcor)
- Insert artifacts into products DB and build a mean mosaic via the mosaic CLI

This script intentionally avoids scanning /data/incoming recursively: it checks
for exact expected filenames per group.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List
import subprocess

from dsa110_contimg.database.products import ensure_products_db, images_insert


def _times_list(center_iso: str) -> List[str]:
    base = datetime.fromisoformat(center_iso)
    out: List[str] = []
    for minutes in range(-30, 30, 5):
        t = base + timedelta(minutes=minutes)
        out.append(t.strftime('%Y-%m-%dT%H:%M:%S'))
    return out


def _file_list_for_time(base_dir: Path, ts: str) -> List[Path]:
    return [base_dir / f"{ts}_sb{idx:02d}.hdf5" for idx in range(16)]


def _check_group_exists(base_dir: Path, ts: str) -> bool:
    files = _file_list_for_time(base_dir, ts)
    return all(p.exists() for p in files)


def _write_ms_from_files(file_list: List[Path], ms_out: Path) -> None:
    from dsa110_contimg.conversion.strategies.direct_subband import write_ms_from_subbands
    ms_out.parent.mkdir(parents=True, exist_ok=True)
    write_ms_from_subbands([os.fspath(p) for p in file_list], os.fspath(ms_out), scratch_dir=None)


def _image_ms(ms_path: Path, imagename: Path, imsize: int = 2048, cell_arcsec: float | None = None) -> None:
    from dsa110_contimg.imaging.cli import image_ms
    imagename.parent.mkdir(parents=True, exist_ok=True)
    image_ms(
        os.fspath(ms_path),
        imagename=os.fspath(imagename),
        imsize=imsize,
        cell_arcsec=cell_arcsec,
        niter=1000,
        threshold='0.0Jy',
        pbcor=True,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description='Build 1-hour mosaic around 0834+555')
    ap.add_argument('--incoming-dir', default='/data/incoming', help='Base directory with subband UVH5 files')
    ap.add_argument('--transit-subdir', default='0834_555_transit', help='Optional curated subdir under incoming with central group')
    ap.add_argument('--center', help='Center time ISO (YYYY-MM-DDTHH:MM:SS); if omitted, try to infer from transit-subdir')
    ap.add_argument('--output-dir', default='state/mosaics/0834_555', help='Output directory for MS and images')
    ap.add_argument('--products-db', default='state/products.sqlite3')
    ap.add_argument('--mosaic-name', default=None, help='Mosaic name (default: transit_0834_555_YYYYMMDD)')
    ap.add_argument('--mosaic-output', default=None, help='Output mosaic base path (.img)')
    ap.add_argument('--imsize', type=int, default=2048)
    args = ap.parse_args()

    incoming = Path(args.incoming_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Determine center time
    center = args.center
    if center is None:
        subdir = incoming / args.transit_subdir
        if subdir.is_dir():
            # Look for any sb00 filename and derive center timestamp
            cand = sorted(p for p in subdir.glob('*_sb00.hdf5'))
            if not cand:
                raise SystemExit(f'No sb00 files found in {subdir}')
            # pick the first
            stem = cand[0].name.split('_sb00.hdf5')[0]
            center = stem
        else:
            raise SystemExit('Center time not provided and transit subdir not found; please pass --center')

    times = _times_list(center)
    # Prefer curated subdir for file presence checks; fall back to base dir
    base_dirs = [incoming / args.transit_subdir, incoming]
    groups: List[tuple[str, List[Path]]] = []
    for ts in times:
        file_list: List[Path] = []
        for b in base_dirs:
            files = _file_list_for_time(b, ts)
            if all(p.exists() for p in files):
                file_list = files
                break
        if file_list:
            groups.append((ts, file_list))

    if len(groups) < 6:
        print(f'Warning: only found {len(groups)} groups around center {center}')

    # Convert and image
    pdb_path = Path(args.products_db)
    with ensure_products_db(pdb_path) as conn:
        for ts, files in groups:
            ms_out = out_dir / f'{ts}.ms'
            img_base = out_dir / f'{ts}.img'
            if not ms_out.exists():
                print(f'Writing MS for {ts}...')
                _write_ms_from_files(files, ms_out)
            else:
                print(f'MS exists for {ts}, skipping write')
            # image
            if not (img_base.with_suffix('.image').exists() or (img_base.as_posix()+'.image')):
                print(f'Imaging {ms_out} -> {img_base}...')
                _image_ms(ms_out, img_base, imsize=args.imsize)
            # record products
            now = datetime.now(timezone.utc).timestamp()
            for suf, pbc in [('.image', 0), ('.pb', 0), ('.pbcor', 1), ('.residual', 0), ('.model', 0)]:
                p = Path(img_base.as_posix() + suf)
                if p.is_dir():
                    images_insert(conn, os.fspath(p), os.fspath(ms_out), now, '5min', pbc)
        conn.commit()

    # Plan and build mosaic
    day = datetime.fromisoformat(center).strftime('%Y_%m_%d')
    name = args.mosaic_name or f'transit_0834_555_{day}'
    out_mosaic = Path(args.mosaic_output) if args.mosaic_output else (out_dir / f'{name}.img')

    # Create plan using recent images (last 2 hours)
    since = (datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()
    until = (datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()
    print(f'Planning mosaic {name} from recent images...')
    subprocess.run([
        'python', '-m', 'dsa110_contimg.mosaic.cli', 'plan',
        '--products-db', os.fspath(pdb_path), '--name', name, '--since', str(since), '--until', str(until)
    ], check=False)
    print(f'Building mosaic {out_mosaic} ...')
    subprocess.run([
        'python', '-m', 'dsa110_contimg.mosaic.cli', 'build',
        '--products-db', os.fspath(pdb_path), '--name', name, '--output', os.fspath(out_mosaic)
    ], check=False)

    print('Done.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

