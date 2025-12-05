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

from dsa110_contimg.database import ensure_pipeline_db, images_insert
import sqlite3
from astropy.wcs import WCS  # type: ignore[import]
from astropy.io import fits  # type: ignore[import]
import numpy as np  # type: ignore[import]
from dsa110_contimg.photometry.forced import measure_forced_peak  # type: ignore[import]


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
    # Imaging for each group:
    # - Seed MODEL_DATA with NVSS (>10 mJy) sources inside the FoV so cleaning
    #   starts with a known sky model; tclean leaves MODEL_DATA untouched.
    image_ms(
        os.fspath(ms_path),
        imagename=os.fspath(imagename),
        imsize=imsize,
        cell_arcsec=cell_arcsec,
        niter=1000,
        threshold='0.0Jy',
        pbcor=True,
        nvss_min_mjy=10.0,
    )


def _fits_bounds(fits_path: Path) -> tuple[float, float, float, float]:
    with fits.open(fits_path) as hdul:
        wcs = WCS(hdul[0].header)
        ny, nx = hdul[0].data.squeeze().shape[-2:]
        ra = []
        dec = []
        for x, y in [(0, 0), (nx - 1, 0), (0, ny - 1), (nx - 1, ny - 1)]:
            rr, dd = wcs.pixel_to_world_values(x, y)
            ra.append(float(rr))
            dec.append(float(dd))
        return (min(ra), max(ra), min(dec), max(dec))


def _select_final_refs(master_db: Path, ra_min: float, ra_max: float, dec_min: float, dec_max: float) -> list[tuple[float, float, float]]:
    out: list[tuple[float, float, float]] = []
    with sqlite3.connect(os.fspath(master_db)) as conn:
        q = (
            "SELECT ra_deg, dec_deg, s_nvss FROM final_references "
            "WHERE ra_deg BETWEEN ? AND ? AND dec_deg BETWEEN ? AND ?"
        )
        for ra, dec, s in conn.execute(q, (ra_min, ra_max, dec_min, dec_max)).fetchall():
            if s is not None:
                out.append((float(ra), float(dec), float(s)))
    return out


def _fit_scalar_scale(measured: list[float], baseline: list[float]) -> tuple[float, float]:
    if not measured:
        return 1.0, float('nan')
    s0 = np.asarray(baseline, dtype=float)
    sm = np.asarray(measured, dtype=float)
    w = np.square(s0)
    num = np.sum(w * s0 * sm)
    den = np.sum(w * np.square(s0))
    g = float(num / den) if den != 0 else 1.0
    resid = sm / (g * s0 + 1e-12) - 1.0
    rr = 1.4826 * float(np.nanmedian(np.abs(resid)))
    return g, rr


def main() -> int:
    ap = argparse.ArgumentParser(description='Build 1-hour mosaic around 0834+555')
    ap.add_argument('--incoming-dir', default='/data/incoming', help='Base directory with subband UVH5 files')
    ap.add_argument('--transit-subdir', default='0834_555_transit', help='Optional curated subdir under incoming with central group')
    ap.add_argument('--center', help='Center time ISO (YYYY-MM-DDTHH:MM:SS); if omitted, try to infer from transit-subdir')
    ap.add_argument('--output-dir', default='state/mosaics/0834_555', help='Output directory for MS and images')
    ap.add_argument('--products-db', default='state/db/products.sqlite3')
    ap.add_argument('--name', default='0834+555')
    ap.add_argument('--vla-db', default='state/catalogs/vla_calibrators.sqlite3')
    ap.add_argument('--master-db', default='state/catalogs/master_sources.sqlite3')
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
    conn = ensure_pipeline_db()
    try:
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
    finally:
        conn.close()

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

    # Forced photometry at calibrator and references
    fits_path = Path(str(out_mosaic) + '.fits')
    if fits_path.is_file():
        ra_cal = dec_cal = None
        try:
            with sqlite3.connect(os.fspath(args.vla_db)) as conn:
                row = conn.execute(
                    "SELECT ra_deg, dec_deg, flux_jy FROM vla_20cm WHERE name=?",
                    (args.name,),
                ).fetchone()
                if row:
                    ra_cal, dec_cal, flux_cal = float(row[0]), float(row[1]), float(row[2])
        except Exception as e:
            print('VLA DB lookup warning:', e)
        if ra_cal is not None and dec_cal is not None:
            cal_meas = measure_forced_peak(os.fspath(fits_path), ra_cal, dec_cal, box_size_pix=5)
            print(f'Calibrator {args.name} peak={cal_meas.peak_jyb:.3f} ± {cal_meas.peak_err_jyb:.3f} Jy/beam')
            try:
                ra_min, ra_max, dec_min, dec_max = _fits_bounds(fits_path)
                refs = _select_final_refs(Path(args.master_db), ra_min, ra_max, dec_min, dec_max)
                if refs:
                    ref_meas = []
                    s0 = []
                    for ra, dec, s in refs:
                        m = measure_forced_peak(os.fspath(fits_path), ra, dec, box_size_pix=5)
                        ref_meas.append(m.peak_jyb)
                        s0.append(s)
                    g, rr = _fit_scalar_scale(ref_meas, s0)
                    print(f'Relative scale g={g:.3f} (robust rms={rr:.3f}) using {len(refs)} refs')
                    s_corr = cal_meas.peak_jyb / g if np.isfinite(g) and g != 0 else cal_meas.peak_jyb
                    print(f'Calibrator corrected peak={s_corr:.3f} Jy/beam')
            except Exception as e:
                print('Relative calibration warning:', e)

    print('Done.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
