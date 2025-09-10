#!/usr/bin/env python3
import os
from pathlib import Path

from astropy.coordinates import SkyCoord
import astropy.units as u

from core.calibration.calibrator_finder import CalibratorFinder
from core.calibration.skymodel_builder import SkyModelBuilder


def main():
    # Inputs
    ms_dir = Path('data/ms')
    ms_list = sorted(ms_dir.glob('*.ms'))
    if not ms_list:
        print('No MS files found under data/ms')
        return 1
    ms_path = str(ms_list[0])

    # Approximate pointing center (from earlier): RA 276.81 deg, Dec 37.22 deg
    center = SkyCoord(ra=276.81 * u.deg, dec=37.22 * u.deg, frame='icrs')

    # Find calibrator (cache-first)
    finder = CalibratorFinder()
    cands = finder.find_nearby(center.ra.deg, center.dec.deg, radius_deg=30.0, min_flux_jy=0.0)
    if not cands:
        print('No calibrator candidates found.')
        return 2
    cal = cands[0]
    print(f"Selected calibrator: {cal.name} @ ({cal.ra_deg:.5f}, {cal.dec_deg:.5f}) sep={cal.separation_deg:.2f} deg [{cal.provenance}]")

    # Build SkyModel and CASA component list
    builder = SkyModelBuilder(output_dir='data/sky_models')
    flux_jy = cal.flux_jy_ref if cal.flux_jy_ref is not None else 1.0
    sm = builder.build_point_sources(
        names=[cal.name],
        ras_deg=[cal.ra_deg],
        decs_deg=[cal.dec_deg],
        fluxes_jy=[flux_jy],
        ref_freq_hz=cal.ref_freq_hz or 1.4e9,
    )
    cl_path = builder.write_casa_component_list(sm, out_name=f"cal_{cal.name}")
    print('Component list:', cl_path)

    # Inject model and run gaincal
    try:
        from casatasks import ft, clearcal, gaincal
    except Exception as e:
        print('CASA tasks not available:', e)
        return 3

    # Ensure cal_tables dir
    cal_dir = Path('data/cal_tables'); cal_dir.mkdir(parents=True, exist_ok=True)
    gcal_path = str(cal_dir / 'test_run_gain.gcal')

    clearcal(vis=ms_path, addmodel=True)
    ft(vis=ms_path, complist=cl_path, usescratch=True)
    print('ft applied')

    gaincal(vis=ms_path,
            caltable=gcal_path,
            gaintype='G',
            calmode='p',
            solint='inf',
            refant='',
            combine='scan',
            minsnr=2.0,
            append=False)
    print('gaincal wrote:', gcal_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
