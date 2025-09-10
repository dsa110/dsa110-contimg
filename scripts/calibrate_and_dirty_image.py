#!/usr/bin/env python3
import os
import sys
from pathlib import Path

import numpy as np

def qa_tables():
    try:
        import casacore.tables as pt
    except Exception as e:
        print('casacore.tables not available:', e)
        return False
    ok = True
    root = Path('data/cal_tables')
    for name in ['test_calibration_bandpass.bcal', 'test_calibration_final_gain.gcal']:
        p = root / name
        print(f'Checking cal table: {p}')
        if not p.exists():
            print('  MISSING')
            ok = False
            continue
        try:
            with pt.table(str(p)) as t:
                print(f'  OPEN OK: rows={t.nrows()}, cols={len(t.colnames())}')
        except Exception as e:
            print('  OPEN FAILED:', e)
            ok = False
    return ok


def newest_ms() -> str:
    ms_dir = Path('data/ms')
    mss = sorted(ms_dir.glob('*.ms'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not mss:
        raise RuntimeError('No MS found under data/ms')
    return str(mss[0])


def ms_summary(ms_path: str):
    try:
        import casacore.tables as pt
    except Exception as e:
        print('casacore.tables not available:', e)
        return
    with pt.table(ms_path) as main:
        nrows = main.nrows()
        print(f'MS rows: {nrows}')
    with pt.table(ms_path + '/ANTENNA') as ant:
        print(f'Antennas: {ant.nrows()}')
    with pt.table(ms_path + '/SPECTRAL_WINDOW') as spw:
        print(f'SPWs: {spw.nrows()}')


def apply_and_dirty(ms_path: str, imagename: str, phasecenter: str | None = None):
    from casatasks import applycal, tclean
    # Ensure output dir exists
    outdir = Path(imagename).parent
    outdir.mkdir(parents=True, exist_ok=True)
    # Apply calibrations
    bcal = 'data/cal_tables/test_calibration_bandpass.bcal'
    gcal = 'data/cal_tables/test_calibration_final_gain.gcal'
    print('Applying calibrations:', bcal, gcal)
    applycal(
        vis=ms_path,
        gaintable=[bcal, gcal],
        interp=['linear', 'linear'],
        calwt=[False, False],
        parang=False,
    )
    # Dirty image (niter=0)
    print('Running tclean dirty image...')
    tclean(
        vis=ms_path,
        imagename=imagename,
        datacolumn='corrected',
        imsize=[1024, 1024],
        cell=['10arcsec'],
        stokes='I',
        weighting='natural',
        gridder='standard',
        phasecenter=phasecenter if phasecenter else '',
        niter=0,
        interactive=False,
    )
    print('Dirty image products at:', imagename)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description='Apply cal tables and make dirty image (optionally set phase center)')
    ap.add_argument('--ra-deg', type=float, help='Phase center RA (deg, ICRS)')
    ap.add_argument('--dec-deg', type=float, help='Phase center Dec (deg, ICRS)')
    ap.add_argument('--imagename', type=str, default='images/quick_dirty', help='Output imagename base')
    args = ap.parse_args()
    if not qa_tables():
        print('Calibration tables QA failed')
        return 2
    ms = newest_ms()
    print('Using MS:', ms)
    ms_summary(ms)
    phasecenter = None
    if args.ra_deg is not None and args.dec_deg is not None:
        # CASA phasecenter string: 'J2000 RA Dec'
        phasecenter = f'J2000 {args.ra_deg}deg {args.dec_deg}deg'
        print('Using phasecenter:', phasecenter)
    apply_and_dirty(ms, imagename=args.imagename, phasecenter=phasecenter)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


