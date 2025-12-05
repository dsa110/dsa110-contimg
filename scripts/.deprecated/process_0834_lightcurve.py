#!/opt/miniforge/envs/casa6/bin/python
"""
Process 10 0834+555 transits to create a lightcurve.

Steps:
1. Convert UVH5 to MS
2. Calibrate MS
3. Image MS
4. Perform photometry
5. Construct lightcurve
"""

import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Ensure we use the correct Python path
sys.path.insert(0, '/data/dsa110-contimg/backend/src')

import numpy as np
from astropy.time import Time
from astropy.io import fits

# Import pipeline modules
from dsa110_contimg.conversion.direct_subband import write_ms_from_subbands
from dsa110_contimg.conversion.ms_utils import configure_ms_for_imaging


def log(msg):
    """Print timestamped log message."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def convert_group_to_ms(group_info, output_dir):
    """Convert a group of UVH5 files to MS."""
    timestamp = group_info['timestamp']
    files = group_info['files']
    
    # Sort files by subband (descending for frequency order)
    def get_sb(f):
        return int(Path(f).name.split('_sb')[1].split('.')[0])
    files_sorted = sorted(files, key=get_sb, reverse=True)
    
    ms_path = output_dir / f"0834_{timestamp.replace(':', '-')}.ms"
    
    if ms_path.exists():
        log(f"  MS already exists: {ms_path.name}")
        return ms_path
    
    log(f"  Converting {len(files_sorted)} subbands to {ms_path.name}...")
    
    # Use direct subband writer
    write_ms_from_subbands(
        files_sorted,
        str(ms_path),
        scratch_dir='/dev/shm/dsa110-contimg'
    )
    
    # Configure for imaging
    configure_ms_for_imaging(str(ms_path))
    
    log(f"  :check: Created: {ms_path.name}")
    return ms_path


def calibrate_ms(ms_path):
    """Calibrate a Measurement Set."""
    import subprocess
    
    log(f"  Calibrating {ms_path.name}...")
    
    cmd = [
        '/opt/miniforge/envs/casa6/bin/python',
        '-m', 'dsa110_contimg.calibration.cli', 'calibrate',
        '--ms', str(ms_path),
        '--field', '0',
        '--auto-fields',
        '--fast',  # Development tier for speed
        '--timebin', '30s',
        '--chanbin', '4',
        '--prebp-phase',
        '--no-plot-bandpass',
        '--no-plot-gain',
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd='/data/dsa110-contimg'
    )
    
    if result.returncode != 0:
        log(f"  :warning: Calibration warning: {result.stderr[-500:] if result.stderr else 'unknown'}")
        return False
    
    log(f"  :check: Calibrated: {ms_path.name}")
    return True


def image_ms(ms_path, output_dir, ra_deg, dec_deg):
    """Create image from calibrated MS."""
    import subprocess
    
    image_name = output_dir / ms_path.stem
    fits_path = Path(f"{image_name}.pbcor.fits")
    
    if fits_path.exists():
        log(f"  Image already exists: {fits_path.name}")
        return fits_path
    
    log(f"  Imaging {ms_path.name}...")
    
    # Create phase center string
    ra_hms = f"{int(ra_deg / 15)}h{int((ra_deg / 15 % 1) * 60)}m{((ra_deg / 15 % 1) * 60 % 1) * 60:.2f}s"
    dec_dms = f"{'+' if dec_deg >= 0 else '-'}{int(abs(dec_deg))}d{int((abs(dec_deg) % 1) * 60)}m{((abs(dec_deg) % 1) * 60 % 1) * 60:.1f}s"
    phasecenter = f"J2000 {ra_hms} {dec_dms}"
    
    cmd = [
        '/opt/miniforge/envs/casa6/bin/python',
        '-m', 'dsa110_contimg.imaging.cli', 'image',
        '--ms', str(ms_path),
        '--imagename', str(image_name),
        '--imsize', '512',
        '--niter', '500',
        '--threshold', '0.5mJy',
        '--quality-tier', 'development',
        '--phasecenter', phasecenter,
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd='/data/dsa110-contimg'
    )
    
    if result.returncode != 0:
        log(f"  :warning: Imaging warning: {result.stderr[-500:] if result.stderr else 'unknown'}")
        # Try without phase center
        cmd_simple = [
            '/opt/miniforge/envs/casa6/bin/python',
            '-m', 'dsa110_contimg.imaging.cli', 'image',
            '--ms', str(ms_path),
            '--imagename', str(image_name),
            '--imsize', '512',
            '--niter', '500',
            '--threshold', '0.5mJy',
            '--quality-tier', 'development',
        ]
        result = subprocess.run(
            cmd_simple,
            capture_output=True,
            text=True,
            cwd='/data/dsa110-contimg'
        )
    
    # Find the FITS file
    possible_fits = [
        Path(f"{image_name}.pbcor.fits"),
        Path(f"{image_name}.image.pbcor.fits"),
        Path(f"{image_name}-image.pbcor.fits"),
    ]
    
    for p in possible_fits:
        if p.exists():
            log(f"  :check: Created: {p.name}")
            return p
    
    # Look for any FITS file
    for p in output_dir.glob(f"{ms_path.stem}*.fits"):
        if 'pbcor' in p.name.lower() or 'image' in p.name.lower():
            log(f"  :check: Created: {p.name}")
            return p
    
    log(f"  :warning: No FITS file found for {ms_path.name}")
    return None


def measure_photometry(fits_path, ra_deg, dec_deg):
    """Measure forced photometry at calibrator position."""
    from dsa110_contimg.photometry.forced import measure_forced_peak
    
    if fits_path is None or not fits_path.exists():
        return None
    
    result = measure_forced_peak(
        str(fits_path),
        ra_deg,
        dec_deg,
        box_size_pix=7,
        annulus_pix=(15, 25)
    )
    
    return {
        'peak_jyb': result.peak_jyb,
        'peak_err_jyb': result.peak_err_jyb,
        'local_rms_jy': result.local_rms_jy,
    }


def plot_lightcurve(measurements, output_path):
    """Create lightcurve plot."""
    import matplotlib.pyplot as plt
    
    # Filter valid measurements
    valid = [(m['timestamp'], m['mjd'], m['flux_jy'], m['flux_err_jy']) 
             for m in measurements 
             if m['flux_jy'] is not None and np.isfinite(m['flux_jy'])]
    
    if len(valid) < 2:
        log("  Not enough valid measurements for lightcurve")
        return None
    
    timestamps, mjds, fluxes, errors = zip(*valid)
    
    # Convert to numpy arrays
    mjds = np.array(mjds)
    fluxes = np.array(fluxes)
    errors = np.array(errors)
    errors = np.where(np.isfinite(errors), errors, np.nanmean(errors))
    
    # Sort by time
    idx = np.argsort(mjds)
    mjds = mjds[idx]
    fluxes = fluxes[idx]
    errors = errors[idx]
    timestamps = [timestamps[i] for i in idx]
    
    # Calculate statistics
    mean_flux = np.nanmean(fluxes)
    std_flux = np.nanstd(fluxes)
    
    # Create plot
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.errorbar(mjds, fluxes * 1000, yerr=errors * 1000, 
                fmt='o', markersize=8, capsize=3, capthick=1,
                color='#2563eb', ecolor='#64748b', label='0834+555')
    
    ax.axhline(mean_flux * 1000, color='#dc2626', linestyle='--', 
               label=f'Mean: {mean_flux*1000:.1f} mJy')
    ax.fill_between(mjds, (mean_flux - std_flux) * 1000, (mean_flux + std_flux) * 1000,
                    alpha=0.2, color='#dc2626', label=f'Std: {std_flux*1000:.1f} mJy')
    
    ax.set_xlabel('MJD', fontsize=12)
    ax.set_ylabel('Flux Density (mJy)', fontsize=12)
    ax.set_title('0834+555 Lightcurve from DSA-110 5-minute Observations', fontsize=14)
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    # Add timestamp annotations
    for i, (mjd, flux, ts) in enumerate(zip(mjds, fluxes, timestamps)):
        if i % 2 == 0:  # Every other point to avoid crowding
            ax.annotate(ts[:10], (mjd, flux * 1000), 
                       textcoords='offset points', xytext=(0, 10),
                       fontsize=7, ha='center', rotation=45)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    log(f"  :check: Saved lightcurve plot: {output_path}")
    return {
        'mean_flux_jy': mean_flux,
        'std_flux_jy': std_flux,
        'n_points': len(fluxes),
        'mjd_range': (float(mjds.min()), float(mjds.max())),
    }


def main():
    log("=" * 70)
    log("0834+555 LIGHTCURVE PIPELINE")
    log("=" * 70)
    
    # Load selected groups
    groups_file = Path('/tmp/selected_transit_groups.json')
    with open(groups_file) as f:
        groups = json.load(f)
    
    log(f"Loaded {len(groups)} transit groups")
    
    # 0834+555 coordinates
    ra_deg = 128.7287
    dec_deg = 55.5725
    
    # Output directories
    ms_dir = Path('/stage/dsa110-contimg/ms/0834_lightcurve')
    img_dir = Path('/stage/dsa110-contimg/images/0834_lightcurve')
    ms_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each group
    measurements = []
    
    for i, group in enumerate(groups, 1):
        log(f"\n{'='*70}")
        log(f"Processing group {i}/{len(groups)}: {group['timestamp']}")
        log(f"  Δt from transit: {group['delta_from_transit_min']:.1f} min")
        log(f"{'='*70}")
        
        try:
            # Step 1: Convert to MS
            log("\n[Step 1/4] Converting UVH5 :arrow_right: MS")
            ms_path = convert_group_to_ms(group, ms_dir)
            
            # Step 2: Calibrate
            log("\n[Step 2/4] Calibrating MS")
            cal_ok = calibrate_ms(ms_path)
            
            # Step 3: Image
            log("\n[Step 3/4] Imaging")
            fits_path = image_ms(ms_path, img_dir, ra_deg, dec_deg)
            
            # Step 4: Photometry
            log("\n[Step 4/4] Photometry")
            if fits_path:
                phot = measure_photometry(fits_path, ra_deg, dec_deg)
                if phot:
                    log(f"  Peak flux: {phot['peak_jyb']*1000:.2f} ± {phot['peak_err_jyb']*1000:.2f} mJy")
                    
                    measurements.append({
                        'timestamp': group['timestamp'],
                        'mjd': Time(group['timestamp']).mjd,
                        'delta_min': group['delta_from_transit_min'],
                        'flux_jy': phot['peak_jyb'],
                        'flux_err_jy': phot['peak_err_jyb'],
                        'rms_jy': phot['local_rms_jy'],
                        'ms_path': str(ms_path),
                        'fits_path': str(fits_path),
                    })
                else:
                    log("  :warning: Photometry failed")
            else:
                log("  :warning: No image available for photometry")
                
        except Exception as e:
            log(f"  :cross: Error processing group: {e}")
            import traceback
            traceback.print_exc()
    
    # Create lightcurve
    log(f"\n{'='*70}")
    log("CREATING LIGHTCURVE")
    log(f"{'='*70}")
    
    if measurements:
        # Save measurements
        meas_file = img_dir / '0834_measurements.json'
        with open(meas_file, 'w') as f:
            json.dump(measurements, f, indent=2)
        log(f"Saved {len(measurements)} measurements to {meas_file}")
        
        # Plot lightcurve
        plot_path = img_dir / '0834_lightcurve.png'
        stats = plot_lightcurve(measurements, plot_path)
        
        if stats:
            log(f"\n{'='*70}")
            log("LIGHTCURVE SUMMARY")
            log(f"{'='*70}")
            log(f"  Mean flux: {stats['mean_flux_jy']*1000:.2f} mJy")
            log(f"  Std dev:   {stats['std_flux_jy']*1000:.2f} mJy")
            log(f"  N points:  {stats['n_points']}")
            log(f"  MJD range: {stats['mjd_range'][0]:.3f} - {stats['mjd_range'][1]:.3f}")
    else:
        log("No valid measurements collected!")
    
    log(f"\n{'='*70}")
    log("PIPELINE COMPLETE")
    log(f"{'='*70}")
    log(f"Output directory: {img_dir}")
    

if __name__ == '__main__':
    main()

