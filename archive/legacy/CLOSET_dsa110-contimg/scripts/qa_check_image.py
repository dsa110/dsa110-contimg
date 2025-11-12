#!/usr/bin/env python3
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any

import numpy as np
from astropy.io import fits
from astropy.stats import sigma_clipped_stats

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ImageQAThresholds:
    max_rms_jy_per_beam: float = 2.0e-4
    min_dynamic_range: float = 10.0
    max_median_over_rms: float = 0.2
    max_beam_axial_ratio: float = 2.5
    max_flagged_fraction_global: float = 0.25
    max_flagged_fraction_per_antenna: float = 0.4
    max_astrometry_offset_beam_frac: float = 0.1
    max_flux_error_frac: float = 0.15


def load_fits(path: str) -> np.ndarray:
    """Load FITS data, handling squeezed dims."""
    with fits.open(path) as h:
        return h[0].data.squeeze()

def beam_info(path: str) -> dict:
    """Get beam info from a CASA image or FITS file."""
    try:
        from casatasks import imhead
        h = imhead(imagename=path, mode='list')
        beam = h.get('restoringbeam')
        if isinstance(beam, dict):
            bmaj = beam.get('major', {}).get('value')
            bmin = beam.get('minor', {}).get('value')
            pa = beam.get('positionangle', {}).get('value')
        else:
            bmaj = bmin = pa = None
        return {'bmaj_arcsec': bmaj, 'bmin_arcsec': bmin, 'pa_deg': pa}
    except Exception:
        # Fallback to FITS header if not a CASA image
        with fits.open(path) as h:
            hdr = h[0].header
            return {
                'bmaj_arcsec': hdr.get('BMAJ', 0) * 3600,
                'bmin_arcsec': hdr.get('BMIN', 0) * 3600,
                'bpa_deg': hdr.get('BPA', 0),
            }


def qa_image(prefix: str, thr: ImageQAThresholds) -> Dict[str, Any]:
    img = load_fits(prefix)
    mean, median, std = sigma_clipped_stats(img, sigma=3.0, maxiters=5)
    peak = float(np.nanmax(img))
    rms = float(std)
    med = float(median)
    dr = float(peak / rms) if rms > 0 else float('inf')

    beam = beam_info(prefix)
    axial = None
    if beam.get('bmaj_arcsec') and beam.get('bmin_arcsec'):
        try:
            axial = float(beam['bmaj_arcsec']) / float(beam['bmin_arcsec'])
        except Exception:
            axial = None

    metrics = {
        'peak_jy_per_beam': peak,
        'rms_jy_per_beam': rms,
        'median_jy_per_beam': med,
        'dynamic_range': dr,
        'beam': beam,
        'beam_axial_ratio': axial,
    }

    status = 'PASS'
    reasons = []
    if rms > thr.max_rms_jy_per_beam:
        status = 'FAIL'; reasons.append('rms_exceeds_limit')
    if dr < thr.min_dynamic_range:
        status = 'FAIL'; reasons.append('dynamic_range_too_low')
    if abs(med) > thr.max_median_over_rms * max(rms, 1e-12):
        status = 'FAIL'; reasons.append('median_bias_large')
    if axial and axial > thr.max_beam_axial_ratio:
        status = 'FAIL'; reasons.append('beam_axial_ratio_high')

    return {'status': status, 'reasons': reasons, 'metrics': metrics, 'thresholds': asdict(thr)}


def cal_health(ms_path: str, thr: ImageQAThresholds) -> Dict[str, Any]:
    try:
        import casacore.tables as pt
        import numpy as np
    except Exception as e:
        return {'status': 'WARN', 'reasons': ['no_casacore'], 'metrics': {}}
    # FLAG column is boolean array per row, per channel/pol. Compute fraction flagged.
    with pt.table(ms_path) as t:
        # Retrieve FLAG_SUM and FLAG_ROW if available, else compute from FLAG
        reasons = []
        if 'FLAG_ROW' in t.colnames():
            fr = t.getcol('FLAG_ROW')
            frac_row = float(np.mean(fr))
        else:
            frac_row = None
        if 'FLAG' in t.colnames():
            # Approximate global flagged fraction across all elements
            # Beware memory; do in chunks
            nrows = t.nrows()
            chunk = max(1, min(10000, nrows))
            total = 0
            flagged = 0
            for i in range(0, nrows, chunk):
                n = min(chunk, nrows - i)
                arr = t.getcol('FLAG', startrow=i, nrow=n)
                total += arr.size
                flagged += int(np.count_nonzero(arr))
            frac_flag = float(flagged / max(1, total))
        else:
            frac_flag = None

    metrics = {'global_flagged_fraction': frac_flag, 'row_flagged_fraction': frac_row}
    status = 'PASS'
    if frac_flag is not None and frac_flag > thr.max_flagged_fraction_global:
        status = 'FAIL'
        reasons.append('global_flagged_fraction_high')
    if frac_row is not None and frac_row > thr.max_flagged_fraction_global:
        status = 'FAIL'
        reasons.append('row_flagged_fraction_high')
    return {'status': status, 'reasons': reasons, 'metrics': metrics}


def astrometry_flux(prefix: str, ref: Dict[str, Any], thr: ImageQAThresholds) -> Dict[str, Any]:
    # Optional check; if ref missing, return WARN
    if not ref:
        return {'status': 'WARN', 'reasons': ['no_reference'], 'metrics': {}}
    try:
        import numpy as np
        from astropy.io import fits
        from astropy.wcs import WCS
        from astropy.coordinates import SkyCoord
        import astropy.units as u
    except Exception:
        return {'status': 'WARN', 'reasons': ['astropy_missing'], 'metrics': {}}

    fits_path = f"{prefix}.fits"
    with fits.open(fits_path) as hdul:
        hdu = hdul[0]
        img = np.squeeze(hdu.data)
        w = WCS(hdu.header)
        # Find peak pixel coordinates (simplistic)
        iy, ix = np.unravel_index(np.nanargmax(img), img.shape)
        sky = w.pixel_to_world(ix, iy)
        # Reference
        ref_coord = SkyCoord(ref['ra_deg'] * u.deg, ref['dec_deg'] * u.deg, frame='icrs')
        sep = sky.separation(ref_coord).arcsec
        # Beam FWHM in arcsec
        b = beam_info(prefix)
        bmaj = b.get('bmaj_arcsec')
        frac = sep / bmaj if (bmaj and bmaj > 0) else None
        # Flux check: compare peak in Jy/beam to reference
        peak = float(np.nanmax(img))
        flux_err = (abs(peak - ref.get('peak_jy', peak)) / max(ref.get('peak_jy', peak), 1e-12))
    metrics = {'astrometry_sep_arcsec': sep, 'astrometry_sep_beam_frac': frac, 'peak_jy_per_beam': peak, 'flux_error_frac': flux_err}
    status = 'PASS'
    reasons = []
    if frac is None or frac > thr.max_astrometry_offset_beam_frac:
        status = 'FAIL'; reasons.append('astrometry_offset_large')
    if flux_err > thr.max_flux_error_frac:
        status = 'FAIL'; reasons.append('flux_error_large')
    return {'status': status, 'reasons': reasons, 'metrics': metrics}


def check_astrometry_and_flux(fits_path, expected_ra_deg, expected_dec_deg, search_radius_deg=1.0, catalog='VLASS1.2'):
    """
    Performs astrometry and flux checks against a reference catalog.

    Args:
        fits_path (str): Path to the FITS image.
        expected_ra_deg (float): Pointing center RA in degrees.
        expected_dec_deg (float): Pointing center Dec in degrees.
        search_radius_deg (float): Radius to search for catalog sources.
        catalog (str): VizieR catalog name to use for reference.

    Returns:
        dict: A dictionary containing the status and results of the check.
    """
    from astropy.coordinates import SkyCoord, Angle
    from astropy import units as u
    from astropy.wcs import WCS
    from astropy.io import fits
    from astropy.stats import sigma_clipped_stats
    from astroquery.vizier import Vizier
    from photutils.detection import DAOStarFinder
    from pyradiosky import SkyModel
    import numpy as np
    import logging

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    report = {'status': 'FAIL'}  # Default to fail

    # 1. Get image properties
    with fits.open(fits_path) as hdul:
        wcs = WCS(hdul[0].header)
        data = hdul[0].data.squeeze()
        obs_freq_hz = hdul[0].header.get('CRVAL3', 1.4e9)  # Default to 1.4 GHz
        bmaj_deg = hdul[0].header.get('BMAJ', 0.01)

    # 2. Find sources in the image using photutils
    mean, median, std = sigma_clipped_stats(data, sigma=3.0)
    daofind = DAOStarFinder(fwhm=bmaj_deg / np.abs(wcs.celestial.pixel_scale_matrix[0, 0]), threshold=3.0*std)
    sources = daofind(data - median)

    if sources is None or len(sources) == 0:
        report['reason'] = "No sources detected in the image."
        return report

    # Convert pixel coords to sky coords
    detected_coords = wcs.celestial.pixel_to_world(sources['xcentroid'], sources['ycentroid'])
    sources['ra'] = detected_coords.ra.deg
    sources['dec'] = detected_coords.dec.deg

    logger.info(f"Detected {len(sources)} sources in the image.")

    # 3. Query reference catalog using astroquery/pyradiosky
    logger.info(f"Querying {catalog} around ({expected_ra_deg:.2f}, {expected_dec_deg:.2f}) with radius {search_radius_deg} deg")
    pointing_center = SkyCoord(ra=expected_ra_deg*u.deg, dec=expected_dec_deg*u.deg, frame='icrs')
    
    try:
        vizier = Vizier(catalog=catalog, columns=['*'])
        vizier.ROW_LIMIT = -1
        result = vizier.query_region(pointing_center, radius=Angle(search_radius_deg, "deg"))
        if not result:
            report['reason'] = f"No reference sources found in {catalog} within search radius."
            return report
        ref_cat = result[0]
    except Exception as e:
        report['reason'] = f"Failed to query VizieR catalog {catalog}: {e}"
        return report
    
    ref_coords = SkyCoord(ra=ref_cat['RA_ICRS']*u.deg, dec=ref_cat['DE_ICRS']*u.deg, frame='icrs')
    logger.info(f"Found {len(ref_cat)} sources in reference catalog.")

    # 4. Cross-match detected sources with reference catalog
    idx, d2d, d3d = detected_coords.match_to_catalog_sky(ref_coords)
    # Match within half the beam major axis
    matching_radius_deg = bmaj_deg / 2.0
    match_mask = d2d < Angle(matching_radius_deg, 'deg')
    
    detected_matches = sources[match_mask]
    ref_matches = ref_cat[idx[match_mask]]
    
    num_matches = len(detected_matches)
    if num_matches < 1:
        report['reason'] = f"No cross-matches found between detected sources and catalog (matching radius: {matching_radius_deg:.4f} deg)."
        return report
    
    logger.info(f"Found {num_matches} cross-matches.")

    # 5. Perform Astrometry Check
    ra_offsets_arcsec = (detected_matches['ra'] - ref_matches['RA_ICRS']) * 3600 * np.cos(np.deg2rad(ref_matches['DE_ICRS']))
    dec_offsets_arcsec = (detected_matches['dec'] - ref_matches['DE_ICRS']) * 3600
    
    median_ra_offset = np.median(ra_offsets_arcsec)
    median_dec_offset = np.median(dec_offsets_arcsec)
    rms_ra_offset = np.sqrt(np.mean(ra_offsets_arcsec**2))
    rms_dec_offset = np.sqrt(np.mean(dec_offsets_arcsec**2))
    
    report['astrometry'] = {
        'num_matches': num_matches,
        'median_ra_offset_arcsec': round(median_ra_offset, 3),
        'median_dec_offset_arcsec': round(median_dec_offset, 3),
        'rms_ra_offset_arcsec': round(rms_ra_offset, 3),
        'rms_dec_offset_arcsec': round(rms_dec_offset, 3),
    }

    # Define astrometry pass criteria (e.g., offset < 10% of beam)
    pos_offset_threshold_arcsec = (bmaj_deg * 3600) * 0.1
    astrometry_pass = (abs(median_ra_offset) < pos_offset_threshold_arcsec) and \
                      (abs(median_dec_offset) < pos_offset_threshold_arcsec)

    # 6. Perform Flux Check
    # VLASS flux is in mJy, detected source flux is in Jy/beam
    ref_flux_jy = ref_matches['Fpeak'] / 1000.0
    detected_flux_jy = detected_matches['peak']
    
    flux_ratio = detected_flux_jy / ref_flux_jy
    median_flux_ratio = np.median(flux_ratio)
    std_flux_ratio = np.std(flux_ratio)
    
    report['flux'] = {
        'median_flux_ratio': round(median_flux_ratio, 3),
        'std_flux_ratio': round(std_flux_ratio, 3),
    }

    # Define flux pass criteria (e.g., ratio between 0.8 and 1.2)
    flux_pass = (median_flux_ratio > 0.8) and (median_flux_ratio < 1.2)

    # 7. Final Status
    if astrometry_pass and flux_pass:
        report['status'] = 'PASS'
        report['reason'] = 'Astrometry and flux are consistent with reference catalog.'
    else:
        report['status'] = 'FAIL'
        reasons = []
        if not astrometry_pass:
            reasons.append(f"Median positional offset > {pos_offset_threshold_arcsec:.2f} arcsec")
        if not flux_pass:
            reasons.append("Median flux ratio is outside the acceptable range (0.8-1.2)")
        report['reason'] = "; ".join(reasons)

    return report


def generate_qa_report(fits_path, ms_path, no_astrometry=False, expected_ra_deg=None, expected_dec_deg=None):
    """
    Generates a full QA report by calling all individual check functions.
    """
    qa_report = {}
    overall_status = 'PASS'

    # Image Noise/DR check
    qa_report['image_noise_dr'] = check_image_noise_dr(fits_path)
    if qa_report['image_noise_dr']['status'] != 'PASS':
        overall_status = 'FAIL'

    # Beam Sanity check
    qa_report['beam_sanity'] = check_beam_sanity(fits_path)
    if qa_report['beam_sanity']['status'] != 'PASS':
        overall_status = 'FAIL'

    # Calibration Health check
    qa_report['calibration_health'] = check_calibration_health(ms_path)
    if qa_report['calibration_health']['status'] != 'PASS':
        overall_status = 'FAIL'

    # Astrometry & Flux check
    if not no_astrometry:
        try:
            qa_report['astrometry_flux'] = check_astrometry_and_flux(
                fits_path=fits_path,
                expected_ra_deg=expected_ra_deg,
                expected_dec_deg=expected_dec_deg
            )
            if qa_report['astrometry_flux']['status'] != 'PASS':
                overall_status = 'FAIL'
        except Exception as e:
            logger.error(f"Astrometry/Flux check failed catastrophically: {e}")
            qa_report['astrometry_flux'] = {'status': 'FAIL', 'reason': f"Runtime error: {e}"}
            overall_status = 'FAIL'
    else:
        logger.warning("Astrometry/Flux check skipped by user request.")
        qa_report['astrometry_flux'] = {'status': 'WARN', 'reason': 'Check skipped by user.'}

    qa_report['overall_status'] = overall_status
    return qa_report

def print_report(report):
    """Prints the QA report in a readable format."""
    print(json.dumps(report, indent=2))

def check_image_noise_dr(fits_path):
    """Checks the dynamic range (peak/rms) of the image."""
    from astropy.io import fits
    from astropy.stats import sigma_clipped_stats
    import numpy as np

    report = {'status': 'PASS', 'metrics': {}, 'reason': ''}
    reasons = []

    try:
        img = load_fits(fits_path)
        mean, median, std = sigma_clipped_stats(img, sigma=3.0, maxiters=5)
        peak = float(np.nanmax(img))
        rms = float(std)
        med = float(median)
        dr = float(peak / rms) if rms > 0 else float('inf')

        report['metrics'] = {
            'peak_jy_per_beam': peak,
            'rms_jy_per_beam': rms,
            'median_jy_per_beam': med,
            'dynamic_range': dr,
        }

        # Define pass criteria
        thr = ImageQAThresholds()
        if dr < thr.min_dynamic_range:
            status = 'FAIL'; reasons.append('dynamic_range_too_low')
        else:
            status = 'PASS'
        report['status'] = status
        report['reason'] = "; ".join(reasons)

    except Exception as e:
        report['status'] = 'FAIL'
        report['reason'] = f"Error calculating dynamic range: {e}"
        report['metrics'] = {}

    return report


def check_beam_sanity(fits_path):
    """Checks beam properties from the FITS header."""
    from astropy.io import fits
    
    report = {'status': 'PASS', 'metrics': {}, 'reason': ''}
    reasons = []
    
    try:
        beam = beam_info(fits_path)
        axial = None
        if beam.get('bmaj_arcsec') and beam.get('bmin_arcsec'):
            try:
                axial = float(beam['bmaj_arcsec']) / float(beam['bmin_arcsec'])
            except Exception:
                axial = None

        report['metrics'] = {
            'beam': beam,
            'beam_axial_ratio': axial,
        }

        # Define pass criteria
        thr = ImageQAThresholds()
        if axial is not None and axial > thr.max_beam_axial_ratio:
            status = 'FAIL'; reasons.append('beam_axial_ratio_high')
        else:
            status = 'PASS'
        report['status'] = status
        report['reason'] = "; ".join(reasons)

    except Exception as e:
        report['status'] = 'FAIL'
        report['reason'] = f"Error checking beam sanity: {e}"
        report['metrics'] = {}

    return report

def check_calibration_health(ms_path):
    """Checks the fraction of flagged data in an MS."""
    from casatasks import listobs
    import re
    import casacore.tables as pt
    import numpy as np

    report = {'status': 'PASS', 'metrics': {}, 'reason': ''}
    reasons = []

    try:
        # FLAG column is boolean array per row, per channel/pol. Compute fraction flagged.
        with pt.table(ms_path) as t:
            # Retrieve FLAG_SUM and FLAG_ROW if available, else compute from FLAG
            if 'FLAG_ROW' in t.colnames():
                fr = t.getcol('FLAG_ROW')
                frac_row = float(np.mean(fr))
            else:
                frac_row = None
            if 'FLAG' in t.colnames():
                # Approximate global flagged fraction across all elements
                # Beware memory; do in chunks
                nrows = t.nrows()
                chunk = max(1, min(10000, nrows))
                total = 0
                flagged = 0
                for i in range(0, nrows, chunk):
                    n = min(chunk, nrows - i)
                    arr = t.getcol('FLAG', startrow=i, nrow=n)
                    total += arr.size
                    flagged += int(np.count_nonzero(arr))
                frac_flag = float(flagged / max(1, total))
            else:
                frac_flag = None

            report['metrics'] = {'global_flagged_fraction': frac_flag, 'row_flagged_fraction': frac_row}

            # Define pass criteria
            thr = ImageQAThresholds()
            if frac_flag is not None and frac_flag > thr.max_flagged_fraction_global:
                status = 'FAIL'; reasons.append('global_flagged_fraction_high')
            if frac_row is not None and frac_row > thr.max_flagged_fraction_global:
                status = 'FAIL'; reasons.append('row_flagged_fraction_high')
            report['status'] = 'PASS' if not reasons else 'FAIL'
            report['reason'] = "; ".join(reasons)

    except Exception as e:
        report['status'] = 'FAIL'
        report['reason'] = f"Error checking calibration health: {e}"
        report['metrics'] = {}

    return report


def main():
    """Main execution."""
    import argparse
    import logging

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description='Generate a QA report for a FITS image and associated Measurement Set.')
    parser.add_argument('--fits_path', type=str, required=True, help='Path to the FITS image file')
    parser.add_argument('--ms_path', type=str, required=True, help='Path to the Measurement Set')
    parser.add_argument('--no-astrometry', action='store_true', help='Skip the astrometry/flux check.')
    parser.add_argument('--expected_ra', type=float, default=None, help='Expected RA pointing center in degrees for astrometry check.')
    parser.add_argument('--expected_dec', type=float, default=None, help='Expected Dec pointing center in degrees for astrometry check.')

    args = parser.parse_args()

    if not args.no_astrometry and (args.expected_ra is None or args.expected_dec is None):
        parser.error("--expected_ra and --expected_dec are required unless --no-astrometry is set.")

    report = generate_qa_report(
        fits_path=args.fits_path,
        ms_path=args.ms_path,
        no_astrometry=args.no_astrometry,
        expected_ra_deg=args.expected_ra,
        expected_dec_deg=args.expected_dec
    )
    print_report(report)


if __name__ == '__main__':
    main()


