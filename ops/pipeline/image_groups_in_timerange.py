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

from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (  # type: ignore[import]
    find_subband_groups,
)
from dsa110_contimg.conversion.ms_utils import (  # type: ignore[import]
    configure_ms_for_imaging,
)
# Shared helpers (consolidated from duplicate code)
from helpers_catalog import load_ra_dec
from helpers_group import group_id_from_path
from helpers_ms_conversion import write_ms_group_via_uvh5_to_ms
# type: ignore[import]
from dsa110_contimg.calibration.applycal import apply_to_target
from dsa110_contimg.imaging.cli import image_ms  # type: ignore[import]
from dsa110_contimg.calibration.flagging import (  # type: ignore[import]
    reset_flags as qa_reset_flags,
    flag_zeros as qa_flag_zeros,
    flag_rfi as qa_flag_rfi,
)


# Removed duplicate functions - now using shared helpers:
# - load_ra_dec() from helpers_catalog
# - group_id_from_path() from helpers_group
# - write_ms_group_via_uvh5_to_ms() from helpers_ms_conversion


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
            ra_deg, dec_deg = load_ra_dec(args.name, args.catalog, vla_db=args.vla_db)
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
        gid = group_id_from_path(g[0])
        ms_out = out_dir / f'{gid}.ms'
        if not ms_out.is_dir():
            print(f'Converting {gid} -> {ms_out}')
            write_ms_group_via_uvh5_to_ms(g, ms_out, add_imaging_columns=True, configure_final_ms=True)
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
        # Imaging:
        # - Seed NVSS point sources (>10 mJy) within the FoV into MODEL_DATA
        #   via ft() so deconvolution starts with known sources.
        # - tclean is configured to preserve the seeded model.
        image_ms(
            os.fspath(ms_out),
            imagename=os.fspath(img_base),
            imsize=args.imsize,
            pbcor=True,
            phasecenter=phasecenter,
            nvss_min_mjy=10.0,
        )

    print('Done.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
