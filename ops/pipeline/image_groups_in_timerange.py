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
from dsa110_contimg.conversion.strategies.uvh5_to_ms_converter import (  # type: ignore[import]
    find_subband_groups,
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


def _load_ra_dec(name: str, catalogs: List[str]) -> Tuple[float, float]:
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


def _ensure_flag_and_weight_spectrum(ms_path: str) -> None:
    """Ensure FLAG and WEIGHT_SPECTRUM cells are defined for all rows.

    - FLAG: boolean array shaped like DATA; fill with False when undefined
    - WEIGHT_SPECTRUM: float array of shape like DATA; if present but any
      row undefined, fill by repeating WEIGHT across channels.
    """
    try:
        from casacore.tables import table as _tb
    except Exception:
        return
    try:
        with _tb(ms_path, readonly=False) as tb:
            nrow = tb.nrows()
            colnames = set(tb.colnames())
            has_ws = 'WEIGHT_SPECTRUM' in colnames
            ws_bad = False
            for i in range(nrow):
                # DATA shape drives target shapes
                try:
                    data = tb.getcell('DATA', i)
                except Exception:
                    continue
                target_shape = getattr(data, 'shape', None)
                if not target_shape or len(target_shape) != 2:
                    continue
                nchan, npol = int(target_shape[0]), int(target_shape[1])
                # FLAG: create or fix shape
                try:
                    f = tb.getcell('FLAG', i)
                    f_shape = getattr(f, 'shape', None)
                    if f is None or f_shape != (nchan, npol):
                        raise RuntimeError('FLAG shape mismatch')
                except Exception:
                    tb.putcell('FLAG', i, np.zeros((nchan, npol), dtype=bool))
                # WEIGHT_SPECTRUM: create or fix shape
                if has_ws:
                    try:
                        ws_val = tb.getcell('WEIGHT_SPECTRUM', i)
                        ws_shape = getattr(ws_val, 'shape', None)
                        if ws_val is None or ws_shape != (nchan, npol):
                            raise RuntimeError('WS shape mismatch')
                    except Exception:
                        try:
                            w = tb.getcell('WEIGHT', i)
                            w = np.asarray(w).reshape(-1)  # npol
                            if w.size != npol:
                                w = np.ones((npol,), dtype=float)
                        except Exception:
                            w = np.ones((npol,), dtype=float)
                        ws = np.repeat(w[np.newaxis, :], nchan, axis=0)
                        tb.putcell('WEIGHT_SPECTRUM', i, ws)
                        ws_bad = True
            # If WEIGHT_SPECTRUM remains problematic in practice, drop it so
            # CASA uses WEIGHT
            if has_ws and ws_bad:
                try:
                    tb.removecols(['WEIGHT_SPECTRUM'])
                except Exception:
                    pass
    except Exception:
        return


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
            add_imaging_columns=False,
            create_time_binned_fields=False,
            field_time_bin_minutes=5.0,
            write_recommendations=False,
            enable_phasing=True,
            phase_reference_time=None,
        )
        try:
            from casacore.tables import addImagingColumns as _addImCols
            _addImCols(os.fspath(part_out))
        except Exception:
            pass
        # Ensure per-part imaging columns are populated (arrays not null)
        try:
            from dsa110_contimg.conversion.uvh5_to_ms import (
                # type: ignore[import]
                _ensure_imaging_columns_populated as _fill_cols,
            )
            _fill_cols(os.fspath(part_out))
        except Exception:
            pass
        parts.append(os.fspath(part_out))
    if ms_out.exists():
        import shutil as _sh
        _sh.rmtree(ms_out, ignore_errors=True)
    casa_concat(
        vis=sorted(parts),
        concatvis=os.fspath(ms_out),
        copypointing=False,
    )
    try:
        from casacore.tables import addImagingColumns as _addImCols
        _addImCols(os.fspath(ms_out))
    except Exception:
        pass
    # Populate imaging columns on the concatenated MS as well
    try:
        from dsa110_contimg.conversion.uvh5_to_ms import (
            # type: ignore[import]
            _ensure_imaging_columns_populated as _fill_cols,
        )
        _fill_cols(os.fspath(ms_out))
    except Exception:
        pass
    # Ensure FLAG and WEIGHT_SPECTRUM cell arrays are present
    _ensure_flag_and_weight_spectrum(os.fspath(ms_out))
    # Initialize weights to ensure WEIGHT_SPECTRUM consistency for tclean
    try:
        from casatasks import initweights as _initweights
        _initweights(vis=os.fspath(ms_out), wtmode='weight', dowtsp=True)
    except Exception:
        pass
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
            ra_deg, dec_deg = _load_ra_dec(args.name, args.catalog)
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
        # Ensure imaging columns and initialize CORRECTED_DATA
        try:
            from casacore.tables import table as _tb, addImagingColumns as _addImCols
            with _tb(os.fspath(ms_out)) as t:
                cols = set(t.colnames())
            if 'MODEL_DATA' not in cols or 'CORRECTED_DATA' not in cols:
                print('Adding imaging columns (MODEL_DATA, CORRECTED_DATA) ...')
                _addImCols(os.fspath(ms_out))
        except Exception as e:
            print('addImagingColumns warning (group):', e)
        # Ensure FLAG/WEIGHT_SPECTRUM arrays exist and are well-shaped BEFORE
        # CASA flagging
        try:
            _ensure_flag_and_weight_spectrum(os.fspath(ms_out))
        except Exception as e:
            print('flag/weight spectrum ensure warning (group):', e)
        # Initialize weights (including WEIGHT_SPECTRUM) prior to tclean
        try:
            from casatasks import initweights as _initweights
            _initweights(vis=os.fspath(ms_out), wtmode='weight', dowtsp=True)
        except Exception as e:
            print('initweights warning (group):', e)
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
        except Exception as e:
            print(f'applycal warning for {ms_out}:', e)

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
