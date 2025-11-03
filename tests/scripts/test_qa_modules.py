#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test quality assurance modules with existing data.

Tests MS quality, calibration quality, and image quality validation
on real pipeline outputs.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from dsa110_contimg.qa.pipeline_quality import (
    check_ms_after_conversion,
    check_calibration_quality,
    check_image_quality,
)


def test_ms_quality():
    """Test MS quality validation."""
    print("\n" + "="*70)
    print("TEST 1: MS Quality Validation")
    print("="*70)
    
    # Find an existing MS file
    ms_dir = Path("/scratch/dsa110-contimg/ms/central_cal_rebuild")
    ms_files = list(ms_dir.glob("2025-10-13T13:28:03.ms"))
    
    if not ms_files:
        print("❌ No MS files found for testing")
        return False
    
    ms_path = str(ms_files[0])
    print(f"\nTesting MS: {ms_path}")
    
    # Quick check first
    print("\n--- Quick Check ---")
    passed, metrics = check_ms_after_conversion(
        ms_path,
        quick_check_only=True,
        alert_on_issues=True,
    )
    
    if passed:
        print("✓ MS passed quick check")
        print(f"  Message: {metrics.get('message', 'OK')}")
    else:
        print("✗ MS failed quick check")
        print(f"  Message: {metrics.get('message', 'Unknown')}")
    
    # Full validation
    print("\n--- Full Validation ---")
    passed, metrics = check_ms_after_conversion(
        ms_path,
        quick_check_only=False,
        alert_on_issues=True,
    )
    
    if passed:
        print("✓ MS passed full validation")
    else:
        print("✗ MS failed full validation")
    
    # Print key metrics
    if 'data_quality' in metrics:
        dq = metrics['data_quality']
        print(f"\n  Data Columns:")
        print(f"    DATA present: {dq.get('data_column_present', False)}")
        print(f"    MODEL_DATA present: {dq.get('model_data_present', False)}")
        print(f"    CORRECTED_DATA present: {dq.get('corrected_data_present', False)}")
        print(f"  Data Quality:")
        print(f"    Fraction flagged: {dq.get('fraction_flagged', 0)*100:.1f}%")
        print(f"    Fraction zeros: {dq.get('fraction_zeros', 0)*100:.1f}%")
        print(f"    Median amplitude: {dq.get('median_amplitude', 0):.3e}")
    
    if 'quality' in metrics:
        q = metrics['quality']
        if q.get('has_critical_issues'):
            print(f"\n  ⚠️  Critical Issues: {q.get('issues', [])}")
        if q.get('has_warnings'):
            print(f"  ⚠️  Warnings: {q.get('warnings', [])}")
        if not q.get('has_critical_issues') and not q.get('has_warnings'):
            print("\n  ✓ No issues or warnings")
    
    return passed


def test_calibration_quality():
    """Test calibration quality validation."""
    print("\n" + "="*70)
    print("TEST 2: Calibration Quality Validation")
    print("="*70)
    
    # Find calibration tables
    cal_dir = Path("/scratch/dsa110-contimg/ms/central_cal_rebuild")
    caltables = list(cal_dir.glob("2025-10-13T13:28:03.shift_all_*cal"))
    
    if not caltables:
        print("❌ No calibration tables found for testing")
        return False
    
    caltables = [str(p) for p in caltables]
    print(f"\nTesting {len(caltables)} calibration table(s):")
    for ct in caltables:
        print(f"  - {Path(ct).name}")
    
    # Test calibration quality
    passed, results = check_calibration_quality(
        caltables,
        ms_path=None,  # Skip CORRECTED_DATA check for now
        alert_on_issues=True,
    )
    
    if passed:
        print("\n✓ All calibration tables passed validation")
    else:
        print("\n✗ Some calibration tables failed validation")
    
    # Print results for each table
    for caltable, metrics in results['caltables'].items():
        cal_name = Path(caltable).name
        print(f"\n  {cal_name}:")
        print(f"    Type: {metrics.get('cal_type', 'UNKNOWN')}")
        print(f"    Antennas: {metrics.get('n_antennas', 0)}")
        print(f"    Solutions: {metrics.get('n_solutions', 0)}")
        
        sol_q = metrics.get('solution_quality', {})
        print(f"    Fraction flagged: {sol_q.get('fraction_flagged', 0)*100:.1f}%")
        print(f"    Median amplitude: {sol_q.get('median_amplitude', 0):.3f}")
        print(f"    Phase scatter: {sol_q.get('phase_scatter_deg', 0):.1f}°")
        
        qual = metrics.get('quality', {})
        if qual.get('has_issues'):
            print(f"    ⚠️  Issues: {qual.get('issues', [])}")
        if qual.get('has_warnings'):
            print(f"    ⚠️  Warnings: {qual.get('warnings', [])}")
    
    return passed


def test_image_quality():
    """Test image quality validation."""
    print("\n" + "="*70)
    print("TEST 3: Image Quality Validation")
    print("="*70)
    
    # Find image files
    img_dir = Path("/scratch/dsa110-contimg/ms/central_cal_rebuild")
    images = list(img_dir.glob("2025-10-13T13:28:03.wproj.image.pbcor"))
    
    if not images:
        print("❌ No images found for testing")
        return False
    
    image_path = str(images[0])
    print(f"\nTesting image: {image_path}")
    
    # Quick check first
    print("\n--- Quick Check ---")
    passed, metrics = check_image_quality(
        image_path,
        quick_check_only=True,
        alert_on_issues=True,
    )
    
    if passed:
        print("✓ Image passed quick check")
        print(f"  Message: {metrics.get('message', 'OK')}")
    else:
        print("✗ Image failed quick check")
        print(f"  Message: {metrics.get('message', 'Unknown')}")
    
    # Full validation
    print("\n--- Full Validation ---")
    passed, metrics = check_image_quality(
        image_path,
        quick_check_only=False,
        alert_on_issues=True,
    )
    
    if passed:
        print("✓ Image passed full validation")
    else:
        print("✗ Image failed full validation")
    
    # Print key metrics
    print(f"\n  Image Properties:")
    print(f"    Type: {metrics.get('image_type', 'unknown')}")
    dims = metrics.get('dimensions', {})
    print(f"    Dimensions: {dims.get('nx', 0)} × {dims.get('ny', 0)} pixels")
    print(f"    Channels: {dims.get('n_channels', 0)}")
    
    pixel_stats = metrics.get('pixel_statistics', {})
    print(f"  Pixel Statistics:")
    print(f"    Median: {pixel_stats.get('median', 0):.3e}")
    print(f"    RMS: {pixel_stats.get('rms', 0):.3e}")
    print(f"    Dynamic range: {pixel_stats.get('dynamic_range', 0):.1f}")
    
    sources = metrics.get('sources', {})
    print(f"  Source Detection:")
    print(f"    Peak value: {sources.get('peak_value', 0):.3e}")
    print(f"    Peak SNR: {sources.get('peak_snr', 0):.1f}")
    print(f"    Pixels >5σ: {sources.get('n_pixels_above_5sigma', 0)}")
    
    qual = metrics.get('quality', {})
    if qual.get('has_issues'):
        print(f"\n  ⚠️  Issues: {qual.get('issues', [])}")
    if qual.get('has_warnings'):
        print(f"  ⚠️  Warnings: {qual.get('warnings', [])}")
    if not qual.get('has_issues') and not qual.get('has_warnings'):
        print("\n  ✓ No issues or warnings")
    
    return passed


def main():
    """Run all QA tests."""
    print("\n" + "="*70)
    print("DSA-110 Quality Assurance Module Testing")
    print("="*70)
    print("\nTesting QA modules with existing pipeline outputs...")
    print("Note: Alerts will be logged to console (Slack webhook not configured)")
    
    results = {
        'ms_quality': False,
        'calibration_quality': False,
        'image_quality': False,
    }
    
    try:
        results['ms_quality'] = test_ms_quality()
    except Exception as e:
        print(f"\n❌ MS quality test failed with exception: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        results['calibration_quality'] = test_calibration_quality()
    except Exception as e:
        print(f"\n❌ Calibration quality test failed with exception: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        results['image_quality'] = test_image_quality()
    except Exception as e:
        print(f"\n❌ Image quality test failed with exception: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name:30s} {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✓ All QA module tests PASSED")
        return 0
    else:
        print("\n✗ Some QA module tests FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())

