#!/usr/bin/env python3
"""
Build and calibrate a single 5-minute group centered on the most recent transit
of a given VLA calibrator using in-repo pipeline machinery:

- Find most recent transit (look-back N days) with available subbands
- Convert that 5-minute group to an MS via direct-subband writer
- Solve K/BA/BP/GA/GP on that MS
- Applycal and image a quick continuum map (pbcor)
- Record artifacts into products DB

Designed as a fast sanity check before generating all window groups & mosaic.
"""

from __future__ import annotations

import argparse
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timezone

import numpy as np
import astropy.units as u
from astropy.time import Time

from dsa110_contimg.calibration.schedule import previous_transits
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import find_subband_groups
# Shared helpers (consolidated from duplicate code)
from helpers_catalog import load_ra_dec, load_flux_jy
from helpers_group import group_id_from_path
from helpers_ms_conversion import write_ms_group_via_uvh5_to_ms
from dsa110_contimg.calibration.calibration import solve_delay, solve_bandpass, solve_gains
from dsa110_contimg.calibration.refant_selection import get_default_outrigger_refants
from dsa110_contimg.calibration.skymodels import make_point_cl, ft_from_cl  # type: ignore[import]
from dsa110_contimg.calibration.applycal import apply_to_target
from dsa110_contimg.imaging.cli import image_ms
from dsa110_contimg.database.products import ensure_products_db, images_insert
from dsa110_contimg.calibration import flagging as qa_flag
from astropy.coordinates import Angle


# Removed duplicate functions - now using shared helpers:
# - load_ra_dec() from helpers_catalog
# - load_flux_jy() from helpers_catalog  
# - group_id_from_path() from helpers_group
# - write_ms_group_via_uvh5_to_ms() from helpers_ms_conversion


def _load_curated_manifest(curated_path: Path) -> Dict[str, Any]:
    import json
    man = curated_path / 'manifest.json'
    if not man.exists():
        raise RuntimeError(f'Curated manifest not found: {man}')
    with open(man, 'r', encoding='utf-8') as f:
        return json.load(f)


def _choose_central_from_curated(man: Dict[str, Any]) -> Tuple[str, List[str]]:
    """Return (group_ts, files[]) for the curated group closest to transit_iso."""
    from astropy.time import Time
    t_transit = Time(man['transit_iso'])
    groups = man.get('groups', [])
    if not groups:
        raise RuntimeError('No groups in curated manifest')

    def _t(ts: str) -> Any:
        try:
            return Time(ts)
        except Exception:
            return None
    best = None
    best_dt = None
    for g in groups:
        ts = g.get('group_ts')
        tt = _t(ts)
        if tt is None:
            continue
        dt = abs(tt - t_transit)
        if best is None or dt < best_dt:
            best = g
            best_dt = dt
    if best is None:
        raise RuntimeError(
            'Could not select a central group from curated manifest')
    return best['group_ts'], list(best.get('files', []))


def main() -> int:
    ap = argparse.ArgumentParser(
        description='Build & calibrate central transit group for a calibrator')
    ap.add_argument('--input-dir', default='/data/incoming')
    ap.add_argument('--output-dir', default='state/ms/central_cal')
    ap.add_argument('--products-db', default='state/products.sqlite3')
    ap.add_argument('--vla-db', default='state/catalogs/vla_calibrators.sqlite3', help='Optional VLA calibrator SQLite DB')
    ap.add_argument('--name', default='0834+555')
    ap.add_argument('--catalog', action='append', default=[
        '/data/dsa110-contimg/data-samples/catalogs/vla_calibrators_parsed.csv'
    ])
    ap.add_argument('--max-days-back', type=int, default=5)
    ap.add_argument('--imsize', type=int, default=2048)
    ap.add_argument(
        '--curated-path',
        type=str,
        default=None,
        help='Use curated manifest at this path to select central group')
    ap.add_argument(
        '--convert-only',
        action='store_true',
        help='Only convert the central 5-min group to MS and exit')
    ap.add_argument(
        '--reuse-ms',
        action='store_true',
        help='Reuse an existing MS if it exists and is valid (skip reconvert)')
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pdb = Path(args.products_db)

    ra_deg, dec_deg = load_ra_dec(args.name, args.catalog, vla_db=args.vla_db)
    chosen_files: List[str]
    if args.curated_path:
        man = _load_curated_manifest(Path(args.curated_path))
        gid, chosen_files = _choose_central_from_curated(man)
    else:
        transits = previous_transits(
            ra_deg, start_time=Time.now(), n=args.max_days_back)
        chosen: List[List[str]] = []
        center_t: Time | None = None
        for t in transits:
            # 5-minute groups: use a 1-hour window around transit to ensure we
            # capture center
            start_iso = (
                t - 30 * u.min).to_datetime().strftime('%Y-%m-%d %H:%M:%S')
            end_iso = (
                t + 30 * u.min).to_datetime().strftime('%Y-%m-%d %H:%M:%S')
            groups = find_subband_groups(args.input_dir, start_iso, end_iso)
            if groups:
                # choose group whose timestamp is closest to transit
                def _mid(g: List[str]) -> Time:
                    gid_local = group_id_from_path(g[0])
                    return Time(gid_local)
                chosen = min(groups, key=lambda g: abs(_mid(g) - t))
                center_t = t
                break
        if not chosen:
            raise SystemExit('No central group found near recent transits')
        gid = group_id_from_path(chosen[0])
        chosen_files = chosen
    ms_out = out_dir / f'{gid}.ms'
    print(f'Converting central group {gid} -> {ms_out}')
    # Default: regenerate the MS even if it exists (to ensure current method)
    # Pass --reuse-ms to keep an existing, valid MS
    if args.reuse_ms and ms_out.exists():
        try:
            from casacore.tables import table as _tb
            with _tb(os.fspath(ms_out)) as t:
                nrow = t.nrows()
            if nrow > 0:
                print(
                    f'MS exists with {nrow} rows; reusing (skip reconvert due to --reuse-ms)')
            else:
                raise RuntimeError('Existing MS has zero rows')
        except Exception:
            if ms_out.exists():
                import shutil as _sh
                print('Existing MS invalid; removing before rebuild ...')
                _sh.rmtree(ms_out, ignore_errors=True)
            write_ms_group_via_uvh5_to_ms(chosen_files, ms_out, add_imaging_columns=False, configure_final_ms=False)
    else:
        if ms_out.exists():
            import shutil as _sh
            print('Removing existing MS to regenerate with current method ...')
            _sh.rmtree(ms_out, ignore_errors=True)
        _write_ms_group_via_uvh5_to_ms(chosen_files, ms_out)
    if args.convert_only:
        print(f'Converted central group to MS: {ms_out}')
        return 0
    # Phase-shift the MS to the catalog calibrator center before calibration
    try:
        from casatasks import phaseshift as casa_phaseshift
        from astropy.coordinates import Angle as _Angle
        ra_hms = _Angle(ra_deg, unit='deg').to_string(
            unit='hourangle', sep='hms', precision=2, pad=True
        ).replace(' ', '')
        dec_dms = _Angle(dec_deg, unit='deg').to_string(
            unit='deg', sep='dms', precision=2, alwayssign=True, pad=True
        ).replace(' ', '')
        pc = f"J2000 {ra_hms} {dec_dms}"
        ms_shift = ms_out.with_suffix('.shift.ms')
        if ms_shift.exists():
            import shutil as _sh
            _sh.rmtree(ms_shift, ignore_errors=True)
        casa_phaseshift(
            vis=os.fspath(ms_out),
            outputvis=os.fspath(ms_shift),
            phasecenter=pc)
        ms_out = ms_shift
        print('phaseshift applied:', pc)
    except Exception as e_ps:
        try:
            from casatasks import fixvis as casa_fixvis
            ms_shift = ms_out.with_suffix('.shift.ms')
            if ms_shift.exists():
                import shutil as _sh
                _sh.rmtree(ms_shift, ignore_errors=True)
            casa_fixvis(vis=os.fspath(ms_out), outputvis=os.fspath(ms_shift),
                        phasecenter=f'J2000 {ra_deg}deg {dec_deg}deg')
            ms_out = ms_shift
            print('fixvis applied (fallback)')
        except Exception as e_fix:
            print('phase center shift warning:', e_ps, e_fix)
    # Ensure imaging columns exist for MODEL_DATA/CORRECTED_DATA before
    # ft/applycal
    try:
        from casacore.tables import table as _tb, addImagingColumns as _addImCols
        with _tb(os.fspath(ms_out)) as t:
            cols = set(t.colnames())
        if 'MODEL_DATA' not in cols or 'CORRECTED_DATA' not in cols:
            print('Adding imaging columns (MODEL_DATA, CORRECTED_DATA) ...')
            _addImCols(os.fspath(ms_out))
    except Exception as e:
        print('addImagingColumns warning:', e)

    # Solve chain (Flagging -> BP first with skymodel via ft, then gains)
    # Determine field selection and use outrigger refant chain
    try:
        from casacore.tables import table
        with table(os.fspath(ms_out) + '::FIELD') as tf:
            nfields = tf.nrows()
        cal_field = '0' if nfields <= 1 else f'0~{nfields-1}'
    except Exception:
        cal_field = '0'
    
    # Use outrigger antenna chain for reference antenna selection
    # This ensures CASA falls back through healthy outriggers if first fails
    refant = get_default_outrigger_refants()
    print(f'Using outrigger refant chain: {refant}')
    
    prefix = os.fspath(ms_out.with_suffix('')) + '_all'
    # Flagging: reset → zero-amplitude → RFI (tfcrop + rflag)
    try:
        print('Flagging: reset flags ...')
        qa_flag.reset_flags(os.fspath(ms_out))
        print('Flagging: zeros ...')
        qa_flag.flag_zeros(os.fspath(ms_out), datacolumn='data')
        print('Flagging: RFI (tfcrop + rflag) ...')
        qa_flag.flag_rfi(os.fspath(ms_out), datacolumn='data')
    except Exception as e:
        print('flagging warning:', e)
    # Provide a simple point-source model (ft()) for the calibrator to
    # stabilize BP
    try:
        flux = load_flux_jy(args.name, args.catalog, band='20cm', vla_db=args.vla_db)
        if flux is not None and flux > 0:
            # Prefer setjy(manual) for robustness; fallback to ft with
            # component list if needed
            try:
                from casatasks import setjy as casa_setjy
                casa_setjy(
                    vis=os.fspath(ms_out),
                    field=cal_field,
                    standard='manual',
                    fluxdensity=[
                        float(flux),
                        0,
                        0,
                        0])
                print(
                    f'setjy(manual): flux={flux:.2f} Jy on field {cal_field}')
            except Exception as e_setjy:
                print('setjy manual failed, falling back to ft():', e_setjy)
                clpath = os.fspath(ms_out.with_suffix('')) + '_pt.cl'
                clpath = make_point_cl(
                    args.name,
                    float(ra_deg),
                    float(dec_deg),
                    flux_jy=float(flux),
                    freq_ghz=1.4,
                    out_path=clpath,
                )
                print(
                    f'ft() point model at RA={ra_deg:.6f} deg, Dec={dec_deg:.6f} deg, flux={flux:.2f} Jy')
                ft_from_cl(os.fspath(ms_out), clpath, field=cal_field, usescratch=True)
            # Verify MODEL_DATA nonzero
            try:
                from casacore.tables import table as _tb
                with _tb(os.fspath(ms_out)) as tb:
                    md = tb.getcell('MODEL_DATA', 0)
                if np.allclose(np.abs(md), 0):
                    print(
                        'model note: MODEL_DATA first row appears zero; continuing, but BP may be weak')
            except Exception:
                pass
    except Exception as e:
        print('skymodel warning:', e)

    # Pre-bandpass phase-only solve, then bandpass
    from casatasks import bandpass as casa_bandpass, gaincal as casa_gaincal
    prebp_path = Path(prefix + '_prebp_phase')
    if prebp_path.is_dir():
        print('Pre-bandpass phase table exists; skipping solve')
    else:
        print('Solving pre-bandpass phase-only (no uvrange cut)...')
        casa_gaincal(
            vis=os.fspath(ms_out),
            caltable=os.fspath(prebp_path),
            field=cal_field,
            solint='inf',
            refant=refant,
            gaintype='G',
            calmode='p',
            combine='scan',
            minsnr=3.0,
            selectdata=True,
        )
    bpcal_path = Path(prefix + '_bpcal')
    if bpcal_path.is_dir():
        print('Bandpass table exists; skipping solve')
    else:
        print('Solving bandpass (no uvrange cut, with pre-phase)...')
        casa_bandpass(
            vis=os.fspath(ms_out),
            caltable=os.fspath(bpcal_path),
            field=cal_field,
            solint='inf',
            refant=refant,
            combine='scan',
            solnorm=True,
            bandtype='B',
            selectdata=True,
            minsnr=3.0,
            gaintable=[os.fspath(prebp_path)],
        )

    # Phase-only gains, with uvrange >1klambda, referencing bandpass
    gpcal_path = Path(prefix + '_gpcal')
    if gpcal_path.is_dir():
        print('Phase gain table exists; skipping solve')
    else:
        print('Solving phase-only gains (uvrange >1klambda)...')
        casa_gaincal(
            vis=os.fspath(ms_out),
            caltable=os.fspath(gpcal_path),
            field=cal_field,
            solint='inf',
            refant=refant,
            gaintype='G',
            calmode='p',
            gaintable=[os.fspath(bpcal_path)],
            uvrange='>1klambda',
            combine='scan',
            minsnr=5.0,
            selectdata=True,
        )
    apply_list = [os.fspath(bpcal_path), os.fspath(gpcal_path)]

    # Apply + image
    print('Applying calibration...')
    try:
        apply_to_target(
            os.fspath(ms_out),
            field='',
            gaintables=apply_list,
            calwt=True)
    except Exception as e:
        print('applycal warning:', e)
    img_base = out_dir / f'{gid}.img'
    print(f'Imaging {ms_out} -> {img_base}')
    # Skip imaging if pbcor already exists
    if (Path(img_base.as_posix() + '.pbcor')).is_dir():
        print('Image already exists (pbcor); skipping imaging')
    else:
        # Center imaging on the calibrator position to avoid WCS offset when
        # the MS phase center is at the meridian rather than the calibrator.
        try:
            ra_hms = Angle(ra_deg, unit='deg').to_string(
                unit='hourangle', sep='hms', precision=2, pad=True
            ).replace(' ', '')
            dec_dms = Angle(dec_deg, unit='deg').to_string(
                unit='deg', sep='dms', precision=2, alwayssign=True, pad=True
            ).replace(' ', '')
            phasecenter = f"J2000 {ra_hms} {dec_dms}"
        except Exception:
            phasecenter = None
        # Imaging:
        # - Seeds MODEL_DATA with a single-component calibrator model if the
        #   calibrator is inside the FoV; otherwise falls back to a
        #   multi-component NVSS model (>10 mJy) within the FoV.
        # - tclean is called with savemodel='none' so the seeded model is
        #   preserved and used during deconvolution.
        image_ms(
            os.fspath(ms_out),
            imagename=os.fspath(img_base),
            imsize=args.imsize,
            pbcor=True,
            phasecenter=phasecenter,
            nvss_min_mjy=10.0,
            calib_ra_deg=float(ra_deg),
            calib_dec_deg=float(dec_deg),
            calib_flux_jy=float(flux) if flux is not None else None,
        )

    # Auto-generate NVSS overlay PNG for the primary image FITS
    try:
        fits_img = Path(img_base.as_posix() + '.image.fits')
        if fits_img.is_file():
            overlay_script = Path(__file__).with_name(
                'overlay_nvss_on_image.py')
            cmd = [
                sys.executable,
                os.fspath(overlay_script),
                '--fits', os.fspath(fits_img),
                '--flux-min-mjy', '100',
                '--label-top', '5',
                '--cal-ra', str(float(ra_deg)),
                '--cal-dec', str(float(dec_deg)),
            ]
            subprocess.run(cmd, check=False)
    except Exception as e:
        print('overlay warning:', e)

    # Record products
    with ensure_products_db(pdb) as conn:
        now = datetime.now(timezone.utc).timestamp()
        for suf, pbc in [('.image', 0), ('.pb', 0),
                         ('.pbcor', 1), ('.residual', 0), ('.model', 0)]:
            p = Path(img_base.as_posix() + suf)
            if p.is_dir():
                images_insert(
                    conn,
                    os.fspath(p),
                    os.fspath(ms_out),
                    now,
                    '5min',
                    pbc)
        conn.commit()
    print('Done.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
