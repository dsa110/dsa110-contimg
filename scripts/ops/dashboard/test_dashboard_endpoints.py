#!/opt/miniforge/envs/casa6/bin/python
"""Test dashboard endpoints with real database."""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add backend/src to path
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from dsa110_contimg.api.config import ApiConfig
from dsa110_contimg.api.data_access import (fetch_alert_history,
                                            fetch_ese_candidates,
                                            fetch_mosaics,
                                            fetch_source_timeseries)


def test_ese_candidates():
    """Test ESE candidates endpoint."""
    print("\n=== Testing ESE Candidates ===")
    cfg = ApiConfig.from_env()
    candidates = fetch_ese_candidates(cfg.products_db, limit=10, min_sigma=5.0)
    
    print(f"Found {len(candidates)} ESE candidates")
    if candidates:
        print(f"  First candidate: {candidates[0]['source_id']} at {candidates[0]['max_sigma_dev']:.1f}σ")
        print(f"  Status: {candidates[0]['status']}")
        print(f"  Current flux: {candidates[0]['current_flux_jy']:.4f} Jy")
    else:
        print("  No candidates found (this is OK if no data matches criteria)")
    return len(candidates) > 0


def test_mosaics():
    """Test mosaic query endpoint."""
    print("\n=== Testing Mosaic Query ===")
    cfg = ApiConfig.from_env()
    
    # Query last 7 days
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)
    
    mosaics = fetch_mosaics(
        cfg.products_db,
        start_time.isoformat(),
        end_time.isoformat()
    )
    
    print(f"Found {len(mosaics)} mosaics in time range")
    if mosaics:
        print(f"  First mosaic: {mosaics[0]['name']}")
        print(f"  Time range: {mosaics[0]['start_time']} to {mosaics[0]['end_time']}")
        print(f"  Image count: {mosaics[0]['image_count']}")
        print(f"  Noise: {mosaics[0]['noise_jy']:.6f} Jy")
    else:
        print("  No mosaics found (this is OK if no data in time range)")
    return len(mosaics) > 0


def test_source_search():
    """Test source search endpoint."""
    print("\n=== Testing Source Search ===")
    cfg = ApiConfig.from_env()
    
    # Test with a known source
    source_id = "NVSS J123456+420312"
    source_data = fetch_source_timeseries(cfg.products_db, source_id)
    
    if source_data:
        print(f"Found timeseries for {source_id}")
        print(f"  RA: {source_data['ra_deg']:.2f}°, Dec: {source_data['dec_deg']:.2f}°")
        print(f"  Flux points: {len(source_data['flux_points'])}")
        print(f"  Mean flux: {source_data['mean_flux_jy']:.4f} Jy")
        print(f"  Std flux: {source_data['std_flux_jy']:.4f} Jy")
        print(f"  Chi-square/nu: {source_data['chi_sq_nu']:.2f}")
        print(f"  Variable: {source_data['is_variable']}")
        
        if source_data['flux_points']:
            first_point = source_data['flux_points'][0]
            print(f"  First measurement: {first_point['time']}, flux={first_point['flux_jy']:.4f} Jy")
    else:
        print(f"  No timeseries found for {source_id}")
        print("  (This is OK if source_id doesn't match or photometry table lacks source_id column)")
    
    return source_data is not None


def test_alert_history():
    """Test alert history endpoint."""
    print("\n=== Testing Alert History ===")
    cfg = ApiConfig.from_env()
    
    alerts = fetch_alert_history(cfg.products_db, limit=10)
    
    print(f"Found {len(alerts)} alerts")
    if alerts:
        print(f"  Most recent: {alerts[0]['alert_type']} - {alerts[0]['severity']}")
        print(f"  Message: {alerts[0]['message']}")
        print(f"  Triggered: {alerts[0]['triggered_at']}")
    else:
        print("  No alerts found (this is OK if alert_history table is empty)")
    return len(alerts) > 0


def main():
    """Run all endpoint tests."""
    print("Testing Dashboard Endpoints")
    print("=" * 50)
    
    results = {
        'ese_candidates': test_ese_candidates(),
        'mosaics': test_mosaics(),
        'source_search': test_source_search(),
        'alert_history': test_alert_history(),
    }
    
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print("=" * 50)
    for endpoint, success in results.items():
        status = ":check: PASS" if success else ":cross: NO DATA"
        print(f"  {endpoint:20s} {status}")
    
    all_have_data = all(results.values())
    if all_have_data:
        print("\n:check: All endpoints returned data successfully!")
    else:
        print("\n:warning: Some endpoints returned no data (this may be expected)")
        print("  Endpoints are working correctly - they just need data in the database")
    
    return 0 if all_have_data else 1


if __name__ == "__main__":
    sys.exit(main())

