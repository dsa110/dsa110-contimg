#!/opt/miniforge/envs/casa6/bin/python
"""Process 10 0834+555 transits through full pipeline."""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, '/data/dsa110-contimg/backend/src')

PYTHON = "/opt/miniforge/envs/casa6/bin/python"
MS_DIR = Path("/stage/dsa110-contimg/ms/0834_lightcurve")
IMG_DIR = Path("/stage/dsa110-contimg/images/0834_lightcurve")
SCRATCH = Path("/stage/dsa110-contimg/scratch")

# 0834+555 coordinates
RA_DEG = 128.7287
DEC_DEG = 55.5725

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def run_cmd(cmd, check=False):
    """Run command and return result."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd='/data/dsa110-contimg'
    )
    return result


def convert_groups(groups):
    """Convert all groups using orchestrator CLI."""
    log("=" * 70)
    log("STEP 1: CONVERTING UVH5 -> MS")
    log("=" * 70)
    
    for i, g in enumerate(groups, 1):
        ts = g['timestamp']
        # Parse timestamp and create time window
        dt = datetime.fromisoformat(ts)
        start = (dt - timedelta(seconds=30)).isoformat()
        end = (dt + timedelta(minutes=5, seconds=30)).isoformat()
        
        ms_path = MS_DIR / f"{ts.replace(':', '-')}.ms"
        if ms_path.exists():
            log(f"  [{i}/10] MS exists: {ts}")
            continue
            
        log(f"  [{i}/10] Converting {ts}...")
        
        cmd = [
            PYTHON, "-m", "dsa110_contimg.conversion.strategies.hdf5_orchestrator",
            "/data/incoming",
            str(MS_DIR),
            start, end,
            "--scratch-dir", str(SCRATCH),
            "--no-stage-to-tmpfs",
            "--writer", "parallel-subband",
            "--skip-existing",
        ]
        
        result = run_cmd(cmd)
        if result.returncode != 0:
            log(f"    :warning: Conversion failed: {result.stderr[-200:]}")
        else:
            log(f"    :check: Converted: {ts}")


def calibrate_all():
    """Calibrate all MS files."""
    log("=" * 70)
    log("STEP 2: CALIBRATING MS FILES")
    log("=" * 70)
    
    ms_files = sorted(MS_DIR.glob("*.ms"))
    for i, ms_path in enumerate(ms_files, 1):
        # Check if already calibrated (has CORRECTED_DATA)
        log(f"  [{i}/{len(ms_files)}] Calibrating {ms_path.name}...")
        
        cmd = [
            PYTHON, "-m", "dsa110_contimg.calibration.cli", "calibrate",
            "--ms", str(ms_path),
            "--field", "0",
            "--auto-fields",
            "--fast",
            "--timebin", "30s",
            "--chanbin", "4",
            "--prebp-phase",
            "--no-plot-bandpass",
            "--no-plot-gain",
        ]
        
        result = run_cmd(cmd)
        if result.returncode != 0:
            log(f"    :warning: Calibration failed: {result.stderr[-200:]}")
        else:
            log(f"    :check: Calibrated: {ms_path.name}")


def image_all():
    """Image all calibrated MS files."""
    log("=" * 70)
    log("STEP 3: IMAGING MS FILES")
    log("=" * 70)
    
    ms_files = sorted(MS_DIR.glob("*.ms"))
    for i, ms_path in enumerate(ms_files, 1):
        img_base = IMG_DIR / ms_path.stem
        fits_candidates = list(IMG_DIR.glob(f"{ms_path.stem}*pbcor*.fits"))
        
        if fits_candidates:
            log(f"  [{i}/{len(ms_files)}] Image exists: {ms_path.stem}")
            continue
            
        log(f"  [{i}/{len(ms_files)}] Imaging {ms_path.name}...")
        
        cmd = [
            PYTHON, "-m", "dsa110_contimg.imaging.cli", "image",
            "--ms", str(ms_path),
            "--imagename", str(img_base),
            "--imsize", "512",
            "--niter", "500",
            "--threshold", "0.5mJy",
            "--quality-tier", "development",
        ]
        
        result = run_cmd(cmd)
        if result.returncode != 0:
            log(f"    :warning: Imaging failed: {result.stderr[-200:]}")
        else:
            log(f"    :check: Imaged: {ms_path.stem}")


def photometry_all():
    """Perform photometry on all images."""
    log("=" * 70)
    log("STEP 4: PHOTOMETRY")
    log("=" * 70)
    
    from astropy.time import Time
    from dsa110_contimg.photometry.forced import measure_forced_peak
    
    fits_files = sorted(IMG_DIR.glob("*pbcor*.fits"))
    if not fits_files:
        fits_files = sorted(IMG_DIR.glob("*image*.fits"))
    
    measurements = []
    for i, fits_path in enumerate(fits_files, 1):
        log(f"  [{i}/{len(fits_files)}] Measuring {fits_path.name}...")
        
        try:
            result = measure_forced_peak(
                str(fits_path),
                RA_DEG,
                DEC_DEG,
                box_size_pix=7,
                annulus_pix=(15, 25)
            )
            
            # Extract timestamp from filename
            stem = fits_path.stem
            # Handle both 2025-10-25T14-11-19 and 2025-10-25T14:11:19 formats
            ts_part = stem.split('.')[0].replace('-', ':')[0:19]
            ts_part = ts_part[:10] + 'T' + ts_part[11:19].replace(':', ':')
            
            # Try to parse MJD
            try:
                mjd = Time(ts_part.replace('-', ':')).mjd
            except Exception:
                mjd = 0.0
            
            measurements.append({
                'fits': str(fits_path),
                'timestamp': ts_part,
                'mjd': mjd,
                'flux_jy': result.peak_jyb,
                'flux_err_jy': result.peak_err_jyb,
                'rms_jy': result.local_rms_jy,
            })
            
            log(f"    Peak: {result.peak_jyb*1000:.2f} ± {result.peak_err_jyb*1000:.2f} mJy")
            
        except Exception as e:
            log(f"    :warning: Photometry failed: {e}")
    
    return measurements


def plot_lightcurve(measurements):
    """Create lightcurve plot."""
    log("=" * 70)
    log("STEP 5: LIGHTCURVE")
    log("=" * 70)
    
    import numpy as np
    import matplotlib.pyplot as plt
    
    # Filter valid measurements
    valid = [(m['timestamp'], m['mjd'], m['flux_jy'], m['flux_err_jy'])
             for m in measurements
             if m['flux_jy'] is not None and np.isfinite(m['flux_jy']) and m['mjd'] > 0]
    
    if len(valid) < 2:
        log("  Not enough valid measurements")
        return
    
    timestamps, mjds, fluxes, errors = zip(*valid)
    mjds = np.array(mjds)
    fluxes = np.array(fluxes)
    errors = np.array(errors)
    errors = np.where(np.isfinite(errors), errors, 0.01)
    
    # Sort by time
    idx = np.argsort(mjds)
    mjds = mjds[idx]
    fluxes = fluxes[idx]
    errors = errors[idx]
    timestamps = [timestamps[i] for i in idx]
    
    # Stats
    mean_flux = np.nanmean(fluxes)
    std_flux = np.nanstd(fluxes)
    
    # Plot
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.errorbar(mjds, fluxes * 1000, yerr=errors * 1000,
                fmt='o', markersize=8, capsize=3, capthick=1,
                color='#2563eb', ecolor='#64748b', label='0834+555')
    
    ax.axhline(mean_flux * 1000, color='#dc2626', linestyle='--',
               label=f'Mean: {mean_flux*1000:.1f} mJy')
    ax.fill_between([mjds.min()-1, mjds.max()+1],
                    (mean_flux - std_flux) * 1000, (mean_flux + std_flux) * 1000,
                    alpha=0.2, color='#dc2626', label=f'Std: {std_flux*1000:.1f} mJy')
    
    ax.set_xlim(mjds.min() - 0.5, mjds.max() + 0.5)
    ax.set_xlabel('MJD', fontsize=12)
    ax.set_ylabel('Flux Density (mJy)', fontsize=12)
    ax.set_title('0834+555 Lightcurve from DSA-110 5-minute Observations', fontsize=14)
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    plot_path = IMG_DIR / '0834_lightcurve.png'
    plt.tight_layout()
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    log(f"  :check: Saved: {plot_path}")
    log(f"  Mean flux: {mean_flux*1000:.2f} mJy")
    log(f"  Std dev:   {std_flux*1000:.2f} mJy")
    log(f"  N points:  {len(fluxes)}")
    
    # Save measurements
    meas_path = IMG_DIR / '0834_measurements.json'
    with open(meas_path, 'w', encoding='utf-8') as f:
        json.dump(measurements, f, indent=2)
    log(f"  :check: Saved measurements: {meas_path}")


def main():
    log("=" * 70)
    log("0834+555 LIGHTCURVE PIPELINE")
    log("=" * 70)
    
    # Ensure directories exist
    MS_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    
    # Load groups
    with open('/tmp/selected_transit_groups.json', encoding='utf-8') as f:
        groups = json.load(f)
    log(f"Processing {len(groups)} transit groups")
    
    # Run pipeline steps
    convert_groups(groups)
    calibrate_all()
    image_all()
    measurements = photometry_all()
    plot_lightcurve(measurements)
    
    log("")
    log("=" * 70)
    log("PIPELINE COMPLETE")
    log("=" * 70)
    log(f"MS files:   {MS_DIR}")
    log(f"Images:     {IMG_DIR}")
    log(f"Lightcurve: {IMG_DIR / '0834_lightcurve.png'}")


if __name__ == '__main__':
    main()

