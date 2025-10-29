"""Mock data for enhanced dashboard features."""
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random


def generate_mock_ese_candidates(count: int = 5) -> List[Dict[str, Any]]:
    """Generate mock ESE candidate data."""
    candidates = []
    base_time = datetime.utcnow()
    
    statuses = ['active', 'active', 'resolved', 'false_positive']
    
    for i in range(count):
        ra = random.uniform(0, 360)
        dec = random.uniform(-90, 90)
        baseline_flux = random.uniform(0.05, 0.5)  # Jy
        sigma_dev = random.uniform(5.0, 15.0) if i < 2 else random.uniform(2.0, 4.0)
        
        candidates.append({
            'id': i + 1,
            'source_id': f'NVSS J{int(ra):06d}{dec:+07.3f}'.replace('.', ''),
            'ra_deg': ra,
            'dec_deg': dec,
            'first_detection_at': (base_time - timedelta(hours=random.randint(1, 24))).isoformat(),
            'last_detection_at': base_time.isoformat(),
            'max_sigma_dev': sigma_dev,
            'current_flux_jy': baseline_flux * (1 + sigma_dev * 0.1),
            'baseline_flux_jy': baseline_flux,
            'status': statuses[i % len(statuses)],
            'notes': f'Detected at {sigma_dev:.1f}σ deviation' if i < 2 else None,
        })
    
    return candidates


def generate_mock_mosaics(start_time: str, end_time: str) -> List[Dict[str, Any]]:
    """Generate mock mosaic data for time range."""
    mosaics = []
    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
    
    # Generate 2-3 mosaics
    duration = (end_dt - start_dt).total_seconds() / 3600  # hours
    num_mosaics = max(1, int(duration))
    
    for i in range(min(num_mosaics, 3)):
        mosaic_start = start_dt + timedelta(hours=i)
        mosaic_end = mosaic_start + timedelta(hours=1)
        
        mosaics.append({
            'id': i + 1,
            'name': f'mosaic_{mosaic_start.strftime("%Y%m%d_%H%M%S")}',
            'path': f'/data/mosaics/mosaic_{i+1}.fits',
            'start_mjd': (mosaic_start - datetime(1858, 11, 17)).total_seconds() / 86400,
            'end_mjd': (mosaic_end - datetime(1858, 11, 17)).total_seconds() / 86400,
            'start_time': mosaic_start.isoformat(),
            'end_time': mosaic_end.isoformat(),
            'created_at': datetime.utcnow().isoformat(),
            'status': 'completed',
            'image_count': random.randint(8, 15),
            'noise_jy': random.uniform(0.0008, 0.0012),
            'source_count': random.randint(120, 180),
        })
    
    return mosaics


def generate_mock_source_timeseries(source_id: str) -> Dict[str, Any]:
    """Generate mock source timeseries data."""
    ra = random.uniform(0, 360)
    dec = random.uniform(-90, 90)
    base_flux = random.uniform(0.05, 0.5)
    
    # Generate 20 flux measurements
    flux_points = []
    base_time = datetime.utcnow() - timedelta(days=7)
    
    for i in range(20):
        obs_time = base_time + timedelta(hours=i * 8)
        flux = base_flux + random.gauss(0, base_flux * 0.1)
        
        flux_points.append({
            'mjd': (obs_time - datetime(1858, 11, 17)).total_seconds() / 86400,
            'time': obs_time.isoformat(),
            'flux_jy': max(0, flux),
            'flux_err_jy': flux * 0.05,
            'image_id': f'img_{i:03d}',
        })
    
    fluxes = [p['flux_jy'] for p in flux_points]
    mean_flux = sum(fluxes) / len(fluxes)
    std_flux = (sum((f - mean_flux)**2 for f in fluxes) / len(fluxes))**0.5
    chi_sq_nu = random.uniform(0.8, 6.0)
    
    return {
        'source_id': source_id,
        'ra_deg': ra,
        'dec_deg': dec,
        'catalog': 'NVSS',
        'flux_points': flux_points,
        'mean_flux_jy': mean_flux,
        'std_flux_jy': std_flux,
        'chi_sq_nu': chi_sq_nu,
        'is_variable': chi_sq_nu > 3.0,
    }


def generate_mock_alert_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Generate mock alert history."""
    alerts = []
    base_time = datetime.utcnow()
    
    alert_types = ['ESE_CANDIDATE', 'CALIBRATOR_ISSUE', 'SYSTEM_WARNING']
    severities = ['info', 'warning', 'critical']
    
    for i in range(limit):
        alert_type = random.choice(alert_types)
        severity = random.choice(severities)
        triggered = base_time - timedelta(hours=random.randint(1, 48))
        
        alerts.append({
            'id': i + 1,
            'source_id': f'NVSS J{random.randint(100000, 999999)}',
            'alert_type': alert_type,
            'severity': severity,
            'message': f'{alert_type.replace("_", " ").title()}: Sample alert message',
            'triggered_at': triggered.isoformat(),
            'resolved_at': (triggered + timedelta(hours=2)).isoformat() if i % 3 == 0 else None,
        })
    
    return alerts

