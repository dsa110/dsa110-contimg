#!/usr/bin/env python3
import argparse
import os
import shutil

from astropy.coordinates import SkyCoord
import astropy.units as u

from casatasks import tclean, clearcal, gaincal, applycal

from core.calibration.calibrator_finder import CalibratorFinder
from core.calibration.skymodel_builder import SkyModelBuilder


def image(vis: str, imagename: str, cell='3arcsec', imsize=2048, niter=2000, threshold='5e-5Jy', phasecenter: str = ''):
    for ext in ['.image','.model','.pb','.psf','.residual','.sumwt', '.mask']:
        p=imagename+ext
        if os.path.isdir(p): shutil.rmtree(p)
        elif os.path.exists(p): os.remove(p)
    clearcal(vis=vis, addmodel=False)
    tclean(vis=vis,
           imagename=imagename,
           specmode='mfs',
           deconvolver='hogbom',
           imsize=[imsize, imsize],
           cell=[cell],
           weighting='briggs',
           robust=0.5,
           gridder='standard',
           phasecenter=phasecenter,
           niter=niter,
           threshold=threshold,
           usemask='auto-multithresh',
           noisethreshold=4.5,
           sidelobethreshold=2.0,
           lownoisethreshold=1.5,
           minbeamfrac=0.3)


def main():
    p = argparse.ArgumentParser(description='Single-iteration selfcal loop with QA gating and explicit phasecenter.')
    p.add_argument('--ms', type=str, required=True)
    p.add_argument('--phasecenter', type=str, default='', help="CASA phasecenter string, e.g. 'J2000 12h00m00 30d00m00'")
    p.add_argument('--bcal', type=str, required=True)
    p.add_argument('--gcal_out', type=str, default='data/cal_tables/selfcal_gain.gcal')
    p.add_argument('--niter', type=int, default=3000)
    p.add_argument('--threshold', type=str, default='3e-5Jy')
    args = p.parse_args()

    # Initial image
    image(args.ms, 'images/selfcal_iter0', niter=0, threshold='1Jy', phasecenter=args.phasecenter)

    # Phase-only gaincal on short solint
    gaincal(vis=args.ms,
            caltable=args.gcal_out,
            gaintype='G',
            calmode='p',
            solint='60s',
            refant='',
            combine='scan',
            minsnr=2.0,
            append=False)

    applycal(vis=args.ms, gaintable=[args.bcal, args.gcal_out], calwt=False, flagbackup=False, applymode='calonly')

    # Re-image deeper
    image(args.ms, 'images/selfcal_iter1', niter=args.niter, threshold=args.threshold, phasecenter=args.phasecenter)
    print('SELFCAL DONE')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
