#!/usr/bin/env python3
"""Create mock data for dashboard testing."""

import sqlite3
import time
import random
from pathlib import Path
from datetime import datetime, timedelta
from astropy.time import Time

def create_mock_data(db_path: Path):
    """Create mock data for dashboard endpoints."""
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    
    # Get current time
    now = time.time()
    now_mjd = Time.now().mjd
    
    print("Creating mock dashboard data...")
    
    # 1. Create variability_stats entries
    print("  Adding variability_stats...")
    sources = [
        ("NVSS J123456+420312", 188.73, 42.05, 45.2, 0.052, 0.008, 6.5, 8.2),
        ("NVSS J234567+123456", 356.36, 12.58, 38.5, 0.038, 0.006, 5.2, 7.1),
        ("NVSS J345678+234567", 64.33, 23.76, 52.1, 0.061, 0.009, 7.8, 9.5),
        ("NVSS J456789+345678", 91.96, 34.65, 41.3, 0.041, 0.007, 4.9, 6.3),
        ("NVSS J567890+456789", 119.58, 45.76, 48.7, 0.049, 0.008, 6.1, 7.8),
    ]
    
    for source_id, ra, dec, nvss_flux, mean_flux, std_flux, chi2_nu, sigma_dev in sources:
        cur.execute("""
            INSERT OR REPLACE INTO variability_stats 
            (source_id, ra_deg, dec_deg, nvss_flux_mjy, n_obs, mean_flux_mjy, 
             std_flux_mjy, min_flux_mjy, max_flux_mjy, chi2_nu, sigma_deviation,
             last_measured_at, last_mjd, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            source_id, ra, dec, nvss_flux, 20, mean_flux, std_flux,
            mean_flux - 2*std_flux, mean_flux + 2*std_flux,
            chi2_nu, sigma_dev, now, now_mjd, now
        ))
    
    # 2. Create ese_candidates entries
    print("  Adding ese_candidates...")
    ese_sources = sources[:3]  # First 3 sources as ESE candidates
    for i, (source_id, ra, dec, nvss_flux, mean_flux, std_flux, chi2_nu, sigma_dev) in enumerate(ese_sources):
        flagged_at = now - (i * 3600)  # Stagger flagging times
        cur.execute("""
            INSERT INTO ese_candidates 
            (source_id, flagged_at, flagged_by, significance, flag_type, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            source_id, flagged_at, 'auto', sigma_dev, 'variability',
            f'Detected at {sigma_dev:.1f}σ deviation', 'active'
        ))
    
    # 3. Create photometry entries for timeseries
    print("  Adding photometry measurements...")
    base_time = now - (7 * 24 * 3600)  # 7 days ago
    for source_id, ra, dec, nvss_flux, mean_flux, std_flux, chi2_nu, sigma_dev in sources:
        for j in range(20):  # 20 measurements per source
            obs_time = base_time + (j * 8 * 3600)  # Every 8 hours
            obs_mjd = Time(datetime.fromtimestamp(obs_time)).mjd
            # Add some variability
            flux_jy = mean_flux / 1000.0 + random.gauss(0, std_flux / 1000.0)
            flux_err_jy = abs(flux_jy * 0.05)
            
            cur.execute("""
                INSERT INTO photometry 
                (image_path, ra_deg, dec_deg, nvss_flux_mjy, peak_jyb, peak_err_jyb, 
                 measured_at, mjd, source_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f'/data/images/img_{source_id}_{j:03d}.fits',
                ra, dec, nvss_flux, flux_jy, flux_err_jy,
                obs_time, obs_mjd, source_id
            ))
    
    # 4. Create mosaics entries
    print("  Adding mosaics...")
    mosaic_start = now_mjd - 3  # 3 days ago
    for i in range(5):
        mosaic_start_mjd = mosaic_start + (i * 0.5)  # Every 12 hours
        mosaic_end_mjd = mosaic_start_mjd + 0.5
        created_at = Time(mosaic_start_mjd, format='mjd').datetime.timestamp()
        
        cur.execute("""
            INSERT INTO mosaics 
            (name, path, created_at, start_mjd, end_mjd, integration_sec, n_images,
             center_ra_deg, center_dec_deg, dec_min_deg, dec_max_deg, noise_jy,
             beam_major_arcsec, beam_minor_arcsec, beam_pa_deg, n_sources, thumbnail_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f'mosaic_{Time(mosaic_start_mjd, format="mjd").datetime.strftime("%Y%m%d_%H%M%S")}',
            f'/data/mosaics/mosaic_{i+1}.fits',
            created_at, mosaic_start_mjd, mosaic_end_mjd,
            1800.0,  # 30 minutes integration
            random.randint(8, 15),  # Number of input images
            180.0, 35.0,  # Center coordinates
            30.0, 40.0,  # Dec range
            random.uniform(0.0008, 0.0012),  # Noise
            12.5, 11.2, 45.0,  # Beam parameters
            random.randint(120, 180),  # Source count
            f'/data/mosaics/thumbnails/mosaic_{i+1}.png'
        ))
    
    # 5. Create alert_history entries
    print("  Adding alert_history...")
    alert_types = ['ese_candidate', 'calibrator_missing', 'system_error']
    severities = ['info', 'warning', 'critical']
    
    for i in range(15):
        alert_type = random.choice(alert_types)
        severity = random.choice(severities)
        source_id = random.choice([s[0] for s in sources])
        sent_at = now - (i * 3600)  # Stagger alert times
        
        messages = {
            'ese_candidate': f'ESE candidate detected: {source_id}',
            'calibrator_missing': f'No calibrator found for observation group',
            'system_error': f'System warning: High CPU usage detected'
        }
        
        cur.execute("""
            INSERT INTO alert_history 
            (source_id, alert_type, severity, message, sent_at, channel, success)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            source_id, alert_type, severity, messages[alert_type],
            sent_at, '#ese-alerts', 1
        ))
    
    conn.commit()
    conn.close()
    print("✓ Mock data created successfully!")


if __name__ == "__main__":
    import sys
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/data/dsa110-contimg/state/products.sqlite3")
    create_mock_data(db_path)

