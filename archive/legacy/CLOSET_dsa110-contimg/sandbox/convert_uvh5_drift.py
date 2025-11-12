import argparse
import glob
import os
import warnings

import numpy as np
from astropy.coordinates import EarthLocation, HADec
from astropy.time import Time
from astropy import units as u
from pyuvdata import UVData


def compute_ra_for_time(phase_dec_rad: float, telescope_loc: EarthLocation, jd_times: np.ndarray) -> np.ndarray:
    """Compute RA(t) for a drift scan at HA=0, fixed Dec.

    Parameters
    ----------
    phase_dec_rad : float
        Drift declination in radians (from header extra_keywords['phase_center_dec']).
    telescope_loc : EarthLocation
        Observatory location.
    jd_times : np.ndarray
        1D array of Julian Dates for each row in the UVData time_array.

    Returns
    -------
    ra_rad : np.ndarray
        RA in radians for each time in jd_times.
    """
    t = Time(jd_times, format='jd', scale='utc')
    lst = t.sidereal_time('apparent', longitude=telescope_loc.lon)
    return np.mod(lst.to(u.rad).value, 2.0 * np.pi)


def convert_uvh5_to_ms_drift(input_files, output_ms, verbose=True):
    if verbose:
        print("\n==============================")
        print("UVH5 → MS (drift-preserving)")
        print("==============================")
        print(f"Files: {len(input_files)}")
        print(f"Output: {output_ms}")

    uv = UVData()
    # Read first file
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        uv.read(input_files[0], file_type='uvh5', run_check=False, check_extra=False)
    if uv.uvw_array.dtype != np.float64:
        uv.uvw_array = uv.uvw_array.astype(np.float64)

    # Concatenate additional files along freq
    for f in input_files[1:]:
        uv2 = UVData()
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            uv2.read(f, file_type='uvh5', run_check=False, check_extra=False)
        if uv2.uvw_array.dtype != np.float64:
            uv2.uvw_array = uv2.uvw_array.astype(np.float64)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            uv.fast_concat(
                uv2,
                axis='freq',
                inplace=True,
                run_check=False,
                check_extra=False,
                run_check_acceptability=False,
                strict_uvw_antpos_check=False,
                ignore_name=True,
            )

    uv.reorder_freqs(channel_order='freq', run_check=False)

    # Get site from header extras if available; otherwise use DSA-110 approximate
    lat = uv.extra_keywords.get('latitude', None)
    lon = uv.extra_keywords.get('longitude', None)
    alt = uv.extra_keywords.get('altitude', None)
    if lat is not None and lon is not None and alt is not None:
        site = EarthLocation.from_geodetic(lon=float(lon) * u.deg, lat=float(lat) * u.deg, height=float(alt) * u.m)
    else:
        site = EarthLocation.from_geodetic(lon=-118.294 * u.deg, lat=37.231 * u.deg, height=1188 * u.m)

    # Drift declination
    drift_dec_rad = uv.extra_keywords.get('phase_center_dec', None)
    if drift_dec_rad is None:
        raise RuntimeError("phase_center_dec not found in extra_keywords; cannot preserve drift dec")
    drift_dec_rad = float(drift_dec_rad)

    # Phase each unique time selection to HA=0 at drift declination
    utime, uind, uinvert = np.unique(uv.time_array, return_index=True, return_inverse=True)
    # Compute RA for each unique time
    ra_rad_ut = compute_ra_for_time(drift_dec_rad, site, utime)

    # Ensure multiple phase centers are created by phasing per-time selection
    # Use cat_name keyed by index to create distinct entries
    for i, ra_ut in enumerate(ra_rad_ut):
        sel = (uinvert == i)
        if not np.any(sel):
            continue
        uv.phase(ra=ra_ut, dec=drift_dec_rad, epoch='J2000', phase_frame='icrs', cat_name=f'drift_{i}', use_ant_pos=True, select_mask=sel)

    # Write MS as already projected (no extra phasing in writer)
    outdir = os.path.dirname(output_ms)
    if outdir and not os.path.exists(outdir):
        os.makedirs(outdir, exist_ok=True)
    if os.path.exists(output_ms):
        # Remove existing directory to avoid writer errors
        import shutil
        shutil.rmtree(output_ms)

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        uv.write_ms(
            output_ms,
            force_phase=False,
            run_check=False,
            check_extra=False,
            run_check_acceptability=False,
            clobber=True,
        )

    if verbose:
        nbytes = 0
        try:
            for root, _, files in os.walk(output_ms):
                for fn in files:
                    fp = os.path.join(root, fn)
                    try:
                        nbytes += os.path.getsize(fp)
                    except OSError:
                        pass
        except Exception:
            pass
        print(f"✓ Wrote MS ({nbytes/1e6:.1f} MB): {output_ms}")
    return output_ms


def main():
    ap = argparse.ArgumentParser(description='Convert UVH5 to MS preserving drift declination (HA=0 phasing per time)')
    ap.add_argument('input_files', nargs='+', help='Input UVH5 files (glob acceptable if shell-expanded)')
    ap.add_argument('-o', '--output', required=True, help='Output MS path (directory)')
    ap.add_argument('-q', '--quiet', action='store_true', help='Suppress progress messages')
    args = ap.parse_args()

    files = sorted(args.input_files)
    if len(files) == 0:
        raise SystemExit('No input files matched')

    convert_uvh5_to_ms_drift(files, args.output, verbose=not args.quiet)


if __name__ == '__main__':
    main()


