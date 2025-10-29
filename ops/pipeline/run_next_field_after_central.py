#!/usr/bin/env python3
import os
import sys
import json
import glob
from pathlib import Path
from typing import List, Optional
import numpy as np  # type: ignore[import]

from astropy.time import Time  # type: ignore[import]

from dsa110_contimg.conversion.uvh5_to_ms import (  # type: ignore[import]
    convert_single_file,
    _ensure_imaging_columns_populated,
)
# type: ignore[import]
from dsa110_contimg.calibration.applycal import apply_to_target
from dsa110_contimg.imaging.cli import image_ms  # type: ignore[import]
from dsa110_contimg.calibration.flagging import (  # type: ignore[import]
    reset_flags as qa_reset_flags,
    flag_zeros as qa_flag_zeros,
    flag_rfi as qa_flag_rfi,
)


def _get_spw_count_from_table(table_path: str) -> Optional[int]:
    """Return SPECTRAL_WINDOW row count if available, else None."""
    try:
        from casacore.tables import table as _tb  # type: ignore[import]
        with _tb(f"{table_path}::SPECTRAL_WINDOW", readonly=True) as _t:
            return int(_t.nrows())
    except Exception:
        return None


def _get_field_count(ms_path: str) -> Optional[int]:
    """Return FIELD table row count if available, else None."""
    try:
        from casacore.tables import table as _tb  # type: ignore[import]
        with _tb(f"{ms_path}::FIELD", readonly=True) as _t:
            return int(_t.nrows())
    except Exception:
        return None


def _ensure_flag_and_weight_spectrum(ms_path: str) -> None:
    """Ensure FLAG and WEIGHT_SPECTRUM cells exist with correct shapes.

    - FLAG: boolean array matching DATA shape; fill with False
    - WEIGHT_SPECTRUM: float array per channel/pol; if missing or wrong shape,
      repeat WEIGHT across channels. If inconsistent after fixes, drop column
      so CASA falls back to WEIGHT.
    """
    try:
        from casacore.tables import table as _tb  # type: ignore[import]
    except Exception:
        return
    try:
        with _tb(ms_path, readonly=False) as tb:
            nrow = tb.nrows()
            colnames = set(tb.colnames())
            has_ws = 'WEIGHT_SPECTRUM' in colnames
            ws_bad = False
            for i in range(nrow):
                try:
                    data = tb.getcell('DATA', i)
                except Exception:
                    continue
                target_shape = getattr(data, 'shape', None)
                if not target_shape or len(target_shape) != 2:
                    continue
                nchan, npol = int(target_shape[0]), int(target_shape[1])
                # FLAG
                try:
                    f = tb.getcell('FLAG', i)
                    f_shape = getattr(f, 'shape', None)
                    if f is None or f_shape != (nchan, npol):
                        raise RuntimeError('FLAG shape mismatch')
                except Exception:
                    tb.putcell('FLAG', i, np.zeros((nchan, npol), dtype=bool))
                # WEIGHT_SPECTRUM
                if has_ws:
                    try:
                        ws_val = tb.getcell('WEIGHT_SPECTRUM', i)
                        ws_shape = getattr(ws_val, 'shape', None)
                        if ws_val is None or ws_shape != (nchan, npol):
                            raise RuntimeError('WS shape mismatch')
                    except Exception:
                        try:
                            w = tb.getcell('WEIGHT', i)
                            w = np.asarray(w).reshape(-1)
                            if w.size != npol:
                                w = np.ones((npol,), dtype=float)
                        except Exception:
                            w = np.ones((npol,), dtype=float)
                        ws = np.repeat(w[np.newaxis, :], nchan, axis=0)
                        tb.putcell('WEIGHT_SPECTRUM', i, ws)
                        ws_bad = True
            if has_ws and ws_bad:
                try:
                    tb.removecols(['WEIGHT_SPECTRUM'])
                except Exception:
                    pass
    except Exception:
        return


def write_ms_group_via_uvh5_to_ms(file_list: List[str], ms_out: Path) -> None:
    from casatasks import concat as casa_concat  # type: ignore[import]
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
            # type: ignore[import]
            from casacore.tables import addImagingColumns as _addImCols
            _addImCols(os.fspath(part_out))
        except Exception:
            pass
        try:
            _ensure_imaging_columns_populated(os.fspath(part_out))
        except Exception:
            pass
        parts.append(os.fspath(part_out))
    if ms_out.exists():
        import shutil as _sh
        _sh.rmtree(ms_out, ignore_errors=True)
    casa_concat(
        vis=sorted(parts),
        concatvis=os.fspath(ms_out),
        copypointing=False)
    try:
        # type: ignore[import]
        from casacore.tables import addImagingColumns as _addImCols
        _addImCols(os.fspath(ms_out))
    except Exception:
        pass
    try:
        _ensure_imaging_columns_populated(os.fspath(ms_out))
    except Exception:
        pass
    try:
        import shutil as _sh
        _sh.rmtree(part_base, ignore_errors=True)
    except Exception:
        pass


def main() -> int:
    curated_manifests = sorted(
        glob.glob('/scratch/dsa110-contimg/curated/0702_445/*/manifest.json'))
    if not curated_manifests:
        print('No curated manifests found for 0702_445')
        return 1
    # Prefer the one with 2025_10_13 in path
    man_path = None
    for m in curated_manifests:
        if '2025_10_13' in m:
            man_path = m
            break
    if man_path is None:
        man_path = curated_manifests[-1]
    with open(man_path, 'r', encoding='utf-8') as f:
        man = json.load(f)
    t_transit = Time(man['transit_iso'])
    groups = man.get('groups', [])
    if not groups:
        print('No groups in curated manifest')
        return 1

    # Choose the first group strictly after transit (tt > t_transit)
    def _tt(g):
        try:
            return Time(g['group_ts'])
        except Exception:
            return None
    groups_sorted = sorted(
        groups,
        key=lambda g: _tt(g) or Time(0, format='mjd'),
    )
    after = [
        g for g in groups_sorted
        if (_tt(g) is not None and _tt(g) > t_transit)
    ]
    if not after:
        print('No group strictly after transit')
        return 1
    # first after transit
    target_group = sorted(after, key=lambda g: _tt(g))[0]
    gid = target_group['group_ts']
    files = target_group.get('files', [])
    if not files:
        print('Next group has no files')
        return 1

    out_dir = Path('/scratch/dsa110-contimg/ms/central_cal_rebuild')
    out_dir.mkdir(parents=True, exist_ok=True)
    ms_out = out_dir / f'{gid}.ms'
    if not ms_out.exists():
        print(f'Converting next group {gid} -> {ms_out}')
        write_ms_group_via_uvh5_to_ms(files, ms_out)
    else:
        print(f'Using existing MS (skip conversion): {ms_out}')
    # Ensure downstream-safe columns
    try:
        _ensure_flag_and_weight_spectrum(os.fspath(ms_out))
    except Exception:
        pass
    # Initialize weights with per-channel spectra for CASA
    try:
        # type: ignore[import]
        from casatasks import initweights as casa_initweights
        casa_initweights(vis=os.fspath(ms_out), wtmode='weight', dowtsp=True)
    except Exception:
        pass
    # Basic QA flagging to mirror central pipeline
    try:
        qa_reset_flags(os.fspath(ms_out))
        qa_flag_zeros(os.fspath(ms_out), datacolumn='data')
        qa_flag_rfi(os.fspath(ms_out), datacolumn='data')
    except Exception:
        pass

    # Locate calibration tables from central_cal_rebuild
    bp_opts = sorted(
        glob.glob('/scratch/dsa110-contimg/ms/central_cal_rebuild/*bpcal'))
    gp_opts = sorted(
        glob.glob('/scratch/dsa110-contimg/ms/central_cal_rebuild/*gpcal'))
    if not bp_opts or not gp_opts:
        print(
            'Calibration tables not found under '
            '/scratch/dsa110-contimg/ms/central_cal_rebuild'
        )
        return 1
    # Prefer shift_all_* if present; otherwise most recent by mtime

    def _pick(opts):
        preferred = [p for p in opts if 'shift_all_' in os.path.basename(p)]
        cand = preferred if preferred else opts
        cand = sorted(cand, key=lambda p: os.path.getmtime(p))
        return cand[-1]
    bp = _pick(bp_opts)
    gp = _pick(gp_opts)

    print('Applying calibration:', bp, gp)
    sys.stdout.flush()
    try:
        # Optional SPW sanity: warn if SPW counts differ
        ms_spw = _get_spw_count_from_table(os.fspath(ms_out))
        gt_spw_counts = []
        for gt in (bp, gp):
            c = _get_spw_count_from_table(gt)
            if c is not None:
                gt_spw_counts.append(c)
        # Build robust spw application strategy
        field_sel = '0' if (
            _get_field_count(
                os.fspath(ms_out)) or 1) >= 1 else ''
        if ms_spw is not None and gt_spw_counts:
            if all(c == ms_spw for c in gt_spw_counts):
                # direct apply for both tables
                apply_to_target(
                    os.fspath(ms_out),
                    field=field_sel,
                    gaintables=[bp, gp],
                    calwt=True,
                )
            elif all(c == 1 for c in gt_spw_counts) and ms_spw >= 1:
                # apply each table with single-spw mapping [0]*ms_spw
                spwmap_single = [0] * int(ms_spw)
                apply_to_target(
                    os.fspath(ms_out),
                    field=field_sel,
                    gaintables=[bp],
                    calwt=True,
                    spwmap=spwmap_single,
                )
                apply_to_target(
                    os.fspath(ms_out),
                    field=field_sel,
                    gaintables=[gp],
                    calwt=True,
                    spwmap=spwmap_single,
                )
            else:
                print(
                    'Incompatible SPW configuration between MS and cal tables; '
                    'aborting. Provide explicit spwmap.')
                return 1
        else:
            # counts unavailable: fall back to direct apply
            apply_to_target(
                os.fspath(ms_out),
                field=field_sel,
                gaintables=[bp, gp],
                calwt=True,
            )
    except Exception as e:
        print('applycal failed:', e)
        return 1
    # Quick verification: ensure CORRECTED_DATA has non-zero samples
    try:
        from casacore.tables import table as _tb
        with _tb(os.fspath(ms_out), readonly=True) as _t:
            if 'CORRECTED_DATA' in set(_t.colnames()):
                import numpy as _np
                n = min(1024, _t.nrows())
                nz = 0
                if n > 0:
                    cd = _t.getcol('CORRECTED_DATA', 0, n)
                    nz = int(_np.count_nonzero(_np.abs(cd) > 0))
                print(
                    'Post-applycal check: CORRECTED_DATA non-zero samples '
                    f'in first {n} rows = {nz}'
                )
                sys.stdout.flush()
                if nz == 0:
                    print(
                        'Calibration appears not applied (all zeros in '
                        'sample); aborting before imaging'
                    )
                    return 1
    except Exception as _e:
        print('Post-applycal check failed:', _e)
        sys.stdout.flush()
        return 1

    img_base = out_dir / f'{gid}.img'
    # Remove any prior image products to ensure a single fresh, calibrated
    # image
    try:
        import shutil as _sh
        from glob import glob as _glob
        # Remove known tclean artifact directories
        for suf in [
            '.image', '.pb', '.pbcor', '.residual', '.model',
                '.mask', '.psf', '.sumwt', '.image.pbcor']:
            p = img_base.as_posix() + suf
            if os.path.isdir(p):
                _sh.rmtree(p, ignore_errors=True)
        # Remove any pattern-matched artifacts (both dirs and files)
        patterns = [
            f"{img_base}.image*",
            f"{img_base}.pb*",
            f"{img_base}.residual*",
            f"{img_base}.model*",
            f"{img_base}.mask*",
            f"{img_base}.psf*",
            f"{img_base}.sumwt*",
        ]
        for pat in patterns:
            for p in _glob(pat):
                try:
                    if os.path.isdir(p):
                        _sh.rmtree(p, ignore_errors=True)
                    elif os.path.isfile(p):
                        os.remove(p)
                except Exception:
                    pass
        # Remove FITS and overlay byproducts
        for suf in [
            '.image.fits',
            '.pb.fits',
            '.pbcor.fits',
            '.residual.fits',
            '.model.fits',
                '.image.nvss_overlay.png']:
            p = img_base.as_posix() + suf
            if os.path.isfile(p):
                os.remove(p)
    except Exception:
        pass
    print(f'Imaging {ms_out} -> {img_base}')
    # Imaging:
    # - Seed NVSS sources (>10 mJy) into MODEL_DATA when calibrator is not
    #   explicitly provided; tclean preserves the seeded model.
    image_ms(
        os.fspath(ms_out),
        imagename=os.fspath(img_base),
        imsize=2048,
        pbcor=True,
        phasecenter=None,
        gridder='wproject',
        wprojplanes=128,
        specmode='mfs',
        deconvolver='mtmfs',
        nterms=2,
        uvrange='>1klambda',
        robust=0.5,
        pblimit=0.25,
        threshold='0.005Jy',
        nvss_min_mjy=10.0)
    print('Done:', img_base)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
