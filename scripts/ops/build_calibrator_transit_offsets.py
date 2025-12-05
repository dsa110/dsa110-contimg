#!/usr/bin/env python3
"""
Build images for offset groups around a calibrator's most recent transit,
reusing the robust central-group pipeline:

- Identify a ~1 hour window (±half_minutes) around the most recent transit
- Convert every 5-minute group in the window to MS via uvh5_to_ms -> concat
- Solve calibration on the central (closest-to-transit) group
- Apply calibration to all groups in the window (optionally exclude the central)
- Image each group (pbcor), optionally recentring on the calibrator (phasecenter)
- Record artifacts into the products DB and optionally generate NVSS overlays

This intentionally mirrors the methods in build_central_calibrator_group.py.
"""

from __future__ import annotations

import argparse
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime, timezone

import numpy as np
import astropy.units as u  # type: ignore[import]
from astropy.time import Time  # type: ignore[import]
from astropy.coordinates import Angle  # type: ignore[import]

# type: ignore[import]
from dsa110_contimg.calibration.schedule import previous_transits
# Shared helpers (consolidated from duplicate code)
from helpers_catalog import load_ra_dec, load_flux_jy
from helpers_group import group_id_from_path
from helpers_ms_conversion import write_ms_group_via_uvh5_to_ms
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
from dsa110_contimg.database.products import (  # type: ignore[import]
    ensure_products_db,
    images_insert,
)
# type: ignore[import]
from dsa110_contimg.calibration.refant_selection import (
    get_default_outrigger_refants,
)


# Removed duplicate functions - now using shared helpers:
# - load_ra_dec() from helpers_catalog
# - load_flux_jy() from helpers_catalog
# - group_id_from_path() from helpers_group
# - write_ms_group_via_uvh5_to_ms() from helpers_ms_conversion


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            'Build offset images around latest transit using central pipeline '
            'methods'
        )
    )
    ap.add_argument('--input-dir', default='/data/incoming')
    ap.add_argument('--output-dir', default='state/ms/transit_offsets')
    ap.add_argument('--products-db', default='state/db/products.sqlite3')
    ap.add_argument('--name', default='0834+555')
    ap.add_argument('--catalog', action='append', default=[
        '/data/dsa110-contimg/data-samples/catalogs/vla_calibrators_parsed.csv'
    ])
    ap.add_argument('--max-days-back', type=int, default=5)
    ap.add_argument('--half-minutes', type=int, default=30)
    ap.add_argument('--imsize', type=int, default=2048)
    ap.add_argument('--exclude-central', action='store_true')
    ap.add_argument('--overlay', action='store_true', default=True)
    ap.add_argument(
        '--phasecenter-cal',
        action='store_true',
        default=True,
        help='Image with phasecenter at calibrator RA/Dec',
    )
    ap.add_argument(
        '--direction',
        choices=['before', 'after', 'both'],
        default='both',
        help='Restrict groups relative to central transit time',
    )
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pdb = Path(args.products_db)

    # Find the most recent transit window with data
    ra_deg, dec_deg = load_ra_dec(args.name, args.catalog)
    transits = previous_transits(
        ra_deg, start_time=Time.now(), n=args.max_days_back
    )
    chosen_window: Tuple[str, str, Time] | None = None
    chosen_groups: List[List[str]] = []
    for t in transits:
        t0 = (
            t - args.half_minutes * u.min
        ).to_datetime().strftime('%Y-%m-%d %H:%M:%S')
        t1 = (
            t + args.half_minutes * u.min
        ).to_datetime().strftime('%Y-%m-%d %H:%M:%S')
        groups = find_subband_groups(args.input_dir, t0, t1)
        if groups:
            chosen_window = (t0, t1, t)
            chosen_groups = groups
            break
    if not chosen_window:
        raise SystemExit('No subband groups found for recent transits')

    start_iso, end_iso, center_t = chosen_window
    print(
        f'Using window {start_iso} .. {end_iso} around transit {center_t.isot}'
    )

    # Identify central group (closest to transit) to solve on
    def _mid_of_group(file_list: List[str]) -> Time:
        gid = group_id_from_path(file_list[0])
        return Time(gid)
    mid_times = [(_mid_of_group(g), g) for g in chosen_groups]
    central_group = min(mid_times, key=lambda x: abs(x[0] - center_t))[1]
    central_gid = group_id_from_path(central_group[0])
    central_ms = out_dir / f'{central_gid}.ms'

    # Optionally restrict groups to those strictly before or after the central
    # time
    if args.direction != 'both':
        filtered: List[List[str]] = []
        for mt, g in mid_times:
            if args.direction == 'before' and mt < center_t:
                filtered.append(g)
            elif args.direction == 'after' and mt > center_t:
                filtered.append(g)
        chosen_groups = filtered

    # Convert central group first (needed for calibration tables)
    print(f'Converting central group {central_gid} -> {central_ms}')
    write_ms_group_via_uvh5_to_ms(central_group, central_ms, add_imaging_columns=True, configure_final_ms=True)

    # Phase-shift the central MS to the calibrator center
    try:
        from casatasks import phaseshift as casa_phaseshift
        ra_hms = (
            Angle(ra_deg, unit='deg')
            .to_string(unit='hourangle', sep='hms', precision=2, pad=True)
            .replace(' ', '')
        )
        dec_dms = (
            Angle(
                dec_deg,
                unit='deg') .to_string(
                unit='deg',
                sep='dms',
                precision=2,
                alwayssign=True,
                pad=True) .replace(
                ' ',
                ''))
        pc = f"J2000 {ra_hms} {dec_dms}"
        ms_shift = central_ms.with_suffix('.shift.ms')
        if ms_shift.exists():
            import shutil as _sh
            _sh.rmtree(ms_shift, ignore_errors=True)
        casa_phaseshift(
            vis=os.fspath(central_ms),
            outputvis=os.fspath(ms_shift),
            phasecenter=pc)
        central_ms = ms_shift
        print('phaseshift applied:', pc)
    except Exception as e_ps:
        try:
            from casatasks import fixvis as casa_fixvis
            ms_shift = central_ms.with_suffix('.shift.ms')
            if ms_shift.exists():
                import shutil as _sh
                _sh.rmtree(ms_shift, ignore_errors=True)
            casa_fixvis(
                vis=os.fspath(central_ms),
                outputvis=os.fspath(ms_shift),
                phasecenter=f'J2000 {ra_deg}deg {dec_deg}deg',
            )
            central_ms = ms_shift
            print('fixvis applied (fallback)')
        except Exception as e_fix:
            print('phase center shift warning:', e_ps, e_fix)

    # Ensure imaging columns exist before setjy/ft/applycal
    try:
        from casacore.tables import table as _tb, addImagingColumns as _addImCols
        with _tb(os.fspath(central_ms)) as t:
            cols = set(t.colnames())
        if 'MODEL_DATA' not in cols or 'CORRECTED_DATA' not in cols:
            print('Adding imaging columns (MODEL_DATA, CORRECTED_DATA) ...')
            _addImCols(os.fspath(central_ms))
    except Exception as e:
        print('addImagingColumns warning:', e)

    # Provide a simple point-source model for the calibrator
    try:
        flux = load_flux_jy(args.name, args.catalog, band='20cm')
        if flux is not None and flux > 0:
            # Run clearcal to ensure MODEL_DATA is writeable
            from casatasks import clearcal
            clearcal(vis=os.fspath(central_ms), addmodel=True)
            try:
                from casatasks import setjy as casa_setjy
                casa_setjy(
                    vis=os.fspath(central_ms),
                    field='0',
                    standard='manual',
                    fluxdensity=[float(flux), 0, 0, 0],
                )
                print(f'setjy(manual): flux={flux:.2f} Jy on field 0')
            except Exception as e_setjy:
                print('setjy manual failed, falling back to ft():', e_setjy)
                from casatools import componentlist as _cl
                from casatasks import ft as casa_ft
                clpath = os.fspath(central_ms.with_suffix('')) + '_pt.cl'
                try:
                    import shutil as _sh
                    _sh.rmtree(clpath, ignore_errors=True)
                except Exception:
                    pass
                cl = _cl()
                cl.open()
                cl.addcomponent(
                    dir=f'J2000 {ra_deg}deg {dec_deg}deg',
                    flux=float(flux),
                    fluxunit='Jy',
                    freq='1.4GHz',
                    shape='point',
                )
                cl.rename(clpath)
                cl.close()
                cl.done()
                casa_ft(
                    vis=os.fspath(central_ms),
                    complist=clpath,
                    field='0',
                    usescratch=True,
                )
    except Exception as e:
        print('skymodel warning:', e)

    # Calibration solves on central MS: pre-phase, bandpass, then gains
    from casatasks import bandpass as casa_bandpass, gaincal as casa_gaincal
    
    # Use outrigger antenna chain for reference antenna selection
    # This ensures CASA falls back through healthy outriggers if first fails
    refant = get_default_outrigger_refants()
    
    prefix = os.fspath(central_ms.with_suffix('')) + '_all'
    prebp_path = Path(prefix + '_prebp_phase')
    if not prebp_path.is_dir():
        print('Solving pre-bandpass phase-only (no uvrange cut)...')
        print(f'Using outrigger refant chain: {refant}')
        casa_gaincal(
            vis=os.fspath(central_ms),
            caltable=os.fspath(prebp_path),
            field='0',
            solint='inf',
            refant=refant,
            gaintype='G',
            calmode='p',
            combine='scan',
            minsnr=3.0,
            selectdata=True,
        )
    bpcal_path = Path(prefix + '_bpcal')
    if not bpcal_path.is_dir():
        print('Solving bandpass (no uvrange cut, with pre-phase)...')
        casa_bandpass(
            vis=os.fspath(central_ms),
            caltable=os.fspath(bpcal_path),
            field='0',
            solint='inf',
            refant=refant,
            combine='scan',
            solnorm=True,
            bandtype='B',
            selectdata=True,
            minsnr=3.0,
            gaintable=[os.fspath(prebp_path)],
        )
    gpcal_path = Path(prefix + '_gpcal')
    if not gpcal_path.is_dir():
        print('Solving phase-only gains (uvrange >1klambda)...')
        casa_gaincal(
            vis=os.fspath(central_ms),
            caltable=os.fspath(gpcal_path),
            field='0',
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

    # Convert remaining groups and image
    # Optionally exclude the central group from outputs
    targets: List[List[str]] = []
    for g in chosen_groups:
        if args.exclude_central and g is central_group:
            continue
        targets.append(g)

    # Always ensure central group is included for calibration application
    # if user requested inclusion
    if not args.exclude_central:
        # Guarantee central is first for progress clarity
        targets = [central_group] + \
            [g for g in targets if g is not central_group]

    # Imaging loop
    with ensure_products_db(pdb) as conn:
        for g in targets:
            gid = group_id_from_path(g[0])
            ms_out = out_dir / f'{gid}.ms'
            if not ms_out.is_dir():
                print(f'Converting {gid} -> {ms_out}')
                write_ms_group_via_uvh5_to_ms(g, ms_out, add_imaging_columns=True, configure_final_ms=True)
            else:
                # Always re-configure if the MS exists to ensure it's ready
                print(f'Configuring existing MS for imaging: {ms_out}')
                configure_ms_for_imaging(os.fspath(ms_out))

            print(f'Applying calibration to {ms_out} ...')
            try:
                apply_to_target(
                    os.fspath(ms_out),
                    field='',
                    gaintables=apply_list,
                    calwt=True)
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
                continue  # Skip to next group

            img_base = out_dir / f'{gid}.img'
            print(f'Imaging {ms_out} -> {img_base} ...')
            # Compute calibrator phasecenter if requested
            phasecenter: Optional[str] = None
            if args.phasecenter_cal:
                try:
                    ra_hms = (
                        Angle(ra_deg, unit='deg')
                        .to_string(
                            unit='hourangle', sep='hms', precision=2, pad=True
                        )
                        .replace(' ', '')
                    )
                    dec_dms = (
                        Angle(
                            dec_deg,
                            unit='deg') .to_string(
                            unit='deg',
                            sep='dms',
                            precision=2,
                            alwayssign=True,
                            pad=True) .replace(
                            ' ',
                            ''))
                    phasecenter = f"J2000 {ra_hms} {dec_dms}"
                except Exception:
                    phasecenter = None
            # Imaging:
            # - Prefer a calibrator point-source model (if within FoV) using
            #   the RA/Dec/Flux from the catalogs/DB; otherwise seed a
            #   multi-source NVSS model (>10 mJy) within the FoV.
            # - tclean preserves the seeded MODEL_DATA (savemodel='none').
            image_ms(
                os.fspath(ms_out),
                imagename=os.fspath(img_base),
                imsize=args.imsize,
                pbcor=True,
                phasecenter=phasecenter,
                nvss_min_mjy=10.0,
                calib_ra_deg=float(ra_deg),
                calib_dec_deg=float(dec_deg),
                calib_flux_jy=float(fx) if (fx:=load_flux_jy(args.name, args.catalog, band='20cm', vla_db=args.vla_db)) is not None else None,
            )
            # Optional NVSS overlay generation
            if args.overlay:
                try:
                    fits_img = Path(img_base.as_posix() + '.image.fits')
                    if fits_img.is_file():
                        overlay_script = Path(__file__).with_name(
                            'overlay_nvss_on_image.py'
                        )
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
