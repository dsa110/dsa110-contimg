#!/usr/bin/env python3
"""
Apply-only imaging for VLA calibrator groups in a time range.

This script mirrors the grouping logic from curate_transit.py to select
5-minute HDF5 subband groups in a [start,end] window, then for each group:
  - convert to an MS (if missing) via uvh5_to_ms + concat
  - ensure imaging columns exist and initialize scratch (clearcal addmodel)
  - apply provided calibration tables (already generated elsewhere)
  - image with optional phasecenter at calibrator RA/Dec and pbcor output

It does not generate calibration solutions; it only applies them.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np
from astropy.coordinates import Angle  # type: ignore[import]

from dsa110_contimg.calibration.catalogs import (  # type: ignore[import]
    read_vla_parsed_catalog_csv,
)
import sqlite3
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (  # type: ignore[import]
    find_subband_groups,
)
from dsa110_contimg.conversion.ms_utils import (  # type: ignore[import]
    configure_ms_for_imaging,
)
# type: ignore[import]
from dsa110_contimg.conversion.uvh5_to_ms import convert_single_file
# type: ignore[import]
from dsa110_contimg.calibration.applycal import apply_to_target
from dsa110_contimg.imaging.cli import image_ms  # type: ignore[import]
from dsa110_contimg.calibration.flagging import (  # type: ignore[import]
    reset_flags as qa_reset_flags,
    flag_zeros as qa_flag_zeros,
    flag_rfi as qa_flag_rfi,
)


def _load_ra_dec_from_db(name: str, vla_db: Optional[str]) -> Optional[Tuple[float, float]]:
    if not vla_db or not os.path.isfile(vla_db):
        return None
    try:
        with sqlite3.connect(vla_db) as conn:
            row = conn.execute(
                "SELECT ra_deg, dec_deg FROM calibrators WHERE name=?", (name,)
            ).fetchone()
            if row:
                return float(row[0]), float(row[1])
    except Exception:
        return None
    return None


def _load_ra_dec(name: str, catalogs: List[str], vla_db: Optional[str] = None) -> Tuple[float, float]:
    dbv = _load_ra_dec_from_db(name, vla_db)
    if dbv is not None:
        return dbv
    for p in catalogs:
        try:
            df = read_vla_parsed_catalog_csv(p)
            if name in df.index:
                row = df.loc[name]
                try:
                    ra = float(row['ra_deg'].iloc[0])
                    dec = float(row['dec_deg'].iloc[0])
                except Exception:
                    ra = float(row['ra_deg'])
                    dec = float(row['dec_deg'])
                if np.isfinite(ra) and np.isfinite(dec):
                    return ra, dec
        except Exception:
            continue
    raise RuntimeError(
        f'Calibrator {name} not found in catalogs: {catalogs}')


def _group_id_from_path(path: str) -> str:
    base = os.path.basename(path)
    return base.split('_sb', 1)[0]


def _write_ms_group_via_uvh5_to_ms(
    file_list: List[str],
    ms_out: Path,
) -> None:
    from casatasks import concat as casa_concat
    part_base = ms_out.parent / (ms_out.stem + '.parts')
    part_base.mkdir(parents=True, exist_ok=True)
    parts: List[str] = []
    for idx, sb in enumerate(sorted(file_list)):
        part_out = part_base / f"{ms_out.stem}.sb{idx:02d}.ms"
        if part_out.exists():
            import shutil as _sh
            _sh.rmtree(part_out, ignore_errors=True)
        convert_single_file(
            sb,
            os.fspath(part_out),
            add_imaging_columns=True,
            create_time_binned_fields=False,
            field_time_bin_minutes=5.0,
            write_recommendations=False,
            enable_phasing=True,
            phase_reference_time=None,
        )
        parts.append(os.fspath(part_out))
    if ms_out.exists():
        import shutil as _sh
        _sh.rmtree(ms_out, ignore_errors=True)
    casa_concat(
        vis=sorted(parts),
        concatvis=os.fspath(ms_out),
        copypointing=False,
    )
    # Configure the final concatenated MS
    configure_ms_for_imaging(os.fspath(ms_out))
    try:
        import shutil as _sh
        _sh.rmtree(part_base, ignore_errors=True)
    except Exception:
        pass


def main() -> int:
    ap = argparse.ArgumentParser(
        description='Apply-only imaging for groups in time range')
    ap.add_argument(
        '--name',
        required=False,
        default=None,
        help='Optional calibrator name used only to derive phasecenter')
    ap.add_argument('--input-dir', default='/data/incoming')
    ap.add_argument('--output-dir', default='state/ms/range')
    ap.add_argument(
        '--catalog',
        action='append',
        default=[
            '/data/dsa110-contimg/data-samples/catalogs/vla_calibrators_parsed.csv',
            'references/dsa110-contimg-main-legacy/data/catalogs/vla_calibrators_parsed.csv',
        ])
    ap.add_argument('--start-iso', required=True)
    ap.add_argument('--end-iso', required=True)
    ap.add_argument('--bpcal', required=True,
                    help='Path to bandpass cal table')
    ap.add_argument('--gpcal', required=True,
                    help='Path to phase-only gain table')
    ap.add_argument('--imsize', type=int, default=2048)
    ap.add_argument(
        '--phasecenter-cal',
        action='store_true',
        default=True,
        help='If set and --name provided, center images on calibrator')
    ap.add_argument(
        '--phasecenter',
        default=None,
        help='Explicit phasecenter, e.g., "J2000 01h23m45.6s +12d34m56s"')
    ap.add_argument('--vla-db', default='state/catalogs/vla_calibrators.sqlite3')
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    groups = find_subband_groups(
        args.input_dir, args.start_iso, args.end_iso)
    if not groups:
        print('No groups found in the requested time range')
        return 0

    phasecenter: Optional[str] = None
    if args.phasecenter:
        phasecenter = args.phasecenter
    elif args.phasecenter_cal and args.name:
        try:
            ra_deg, dec_deg = _load_ra_dec(args.name, args.catalog, vla_db=args.vla_db)
            ra_hms = (
                Angle(ra_deg, unit='deg')
                .to_string(
                    unit='hourangle', sep='hms', precision=2, pad=True)
                .replace(' ', '')
            )
            dec_dms = (
                Angle(dec_deg, unit='deg')
                .to_string(
                    unit='deg', sep='dms', precision=2,
                    alwayssign=True, pad=True)
                .replace(' ', '')
            )
            phasecenter = f"J2000 {ra_hms} {dec_dms}"
        except Exception:
            phasecenter = None

    for g in groups:
        gid = _group_id_from_path(g[0])
        ms_out = out_dir / f'{gid}.ms'
        if not ms_out.is_dir():
            print(f'Converting {gid} -> {ms_out}')
            _write_ms_group_via_uvh5_to_ms(g, ms_out)
        else:
            print(f'Configuring existing MS for imaging: {ms_out}')
            configure_ms_for_imaging(os.fspath(ms_out))

        # Mirror central flow: reset flags and perform basic RFI flagging
        try:
            qa_reset_flags(os.fspath(ms_out))
            qa_flag_zeros(os.fspath(ms_out), datacolumn='data')
            qa_flag_rfi(os.fspath(ms_out), datacolumn='data')
        except Exception as e:
            print('flagging warning (group):', e)

        # Apply existing calibrations
        try:
            apply_to_target(
                os.fspath(ms_out),
                field='',
                gaintables=[args.bpcal, args.gpcal],
                calwt=True,
            )
            # Verify that applycal did something
            from casacore.tables import table
            with table(os.fspath(ms_out), readonly=True) as t:
                corrected = t.getcol('CORRECTED_DATA')
            if np.all(corrected == 0):
                raise RuntimeError(
                    "CORRECTED_DATA is all zeros after applycal"
                )
        except Exception as e:
            print(f'FATAL: applycal failed for {ms_out}: {e}')
            continue

        # Image
        img_base = out_dir / f'{gid}.img'
        print(f'Imaging {ms_out} -> {img_base} ...')
        image_ms(
            os.fspath(ms_out),
            imagename=os.fspath(img_base),
            imsize=args.imsize,
            pbcor=True,
            phasecenter=phasecenter,
        )

    print('Done.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
