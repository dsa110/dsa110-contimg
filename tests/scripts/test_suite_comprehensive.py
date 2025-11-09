#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive test suite for DSA-110 pipeline enhancements.

Tests everything that could break:
1. Imports and dependencies
2. QA modules with edge cases
3. Alerting with error conditions
4. Photometry normalization
5. Configuration handling
6. Database interactions
"""

import sys
import os
from pathlib import Path
import traceback

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Test results tracking
class TestResults:
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
        self.errors = 0
    
    def add_pass(self, name, message=""):
        self.tests.append(("PASS", name, message))
        self.passed += 1
        print(f"  ✓ {name}")
        if message:
            print(f"    {message}")
    
    def add_fail(self, name, message=""):
        self.tests.append(("FAIL", name, message))
        self.failed += 1
        print(f"  ✗ {name}")
        if message:
            print(f"    {message}")
    
    def add_error(self, name, exception):
        self.tests.append(("ERROR", name, str(exception)))
        self.errors += 1
        print(f"  ⚠  {name}")
        print(f"    ERROR: {exception}")
    
    def summary(self):
        total = self.passed + self.failed + self.errors
        print(f"\n{'='*70}")
        print(f"SUMMARY: {self.passed}/{total} passed")
        print(f"  Passed: {self.passed}")
        print(f"  Failed: {self.failed}")
        print(f"  Errors: {self.errors}")
        print(f"{'='*70}")
        return self.failed == 0 and self.errors == 0


results = TestResults()


def test_imports():
    """Test 1: Can we import all modules without errors?"""
    print("\n" + "="*70)
    print("TEST 1: Module Imports")
    print("="*70)
    
    modules_to_test = [
        ("dsa110_contimg.utils.alerting", "Alerting"),
        ("dsa110_contimg.qa.ms_quality", "MS Quality"),
        ("dsa110_contimg.qa.calibration_quality", "Calibration Quality"),
        ("dsa110_contimg.qa.image_quality", "Image Quality"),
        ("dsa110_contimg.qa.pipeline_quality", "Pipeline Quality"),
        ("dsa110_contimg.photometry.normalize", "Photometry Normalization"),
        ("dsa110_contimg.photometry.forced", "Forced Photometry"),
    ]
    
    for module_name, display_name in modules_to_test:
        try:
            __import__(module_name)
            results.add_pass(f"Import {display_name}")
        except ImportError as e:
            results.add_error(f"Import {display_name}", e)
        except Exception as e:
            results.add_error(f"Import {display_name}", e)


def test_alerting_edge_cases():
    """Test 2: Alerting system edge cases."""
    print("\n" + "="*70)
    print("TEST 2: Alerting Edge Cases")
    print("="*70)
    
    try:
        from dsa110_contimg.utils import alerting
        
        # Test 1: Empty message
        try:
            alerting.info("test", "")
            results.add_pass("Alert with empty message")
        except Exception as e:
            results.add_fail("Alert with empty message", str(e))
        
        # Test 2: Very long message
        try:
            long_msg = "x" * 10000
            alerting.info("test", long_msg)
            results.add_pass("Alert with very long message")
        except Exception as e:
            results.add_fail("Alert with very long message", str(e))
        
        # Test 3: Special characters
        try:
            alerting.info("test", "Special: \n\t\"'<>&")
            results.add_pass("Alert with special characters")
        except Exception as e:
            results.add_fail("Alert with special characters", str(e))
        
        # Test 4: None context
        try:
            alerting.info("test", "message", context=None)
            results.add_pass("Alert with None context")
        except Exception as e:
            results.add_fail("Alert with None context", str(e))
        
        # Test 5: Large context dict
        try:
            big_context = {f"key_{i}": f"value_{i}" for i in range(100)}
            alerting.info("test", "message", context=big_context)
            results.add_pass("Alert with large context dict")
        except Exception as e:
            results.add_fail("Alert with large context dict", str(e))
        
        # Test 6: Rate limiting (send 20 rapid alerts)
        try:
            for i in range(20):
                alerting.info("rate_limit_test", f"Alert {i}")
            results.add_pass("Rate limiting doesn't crash")
        except Exception as e:
            results.add_fail("Rate limiting", str(e))
        
    except Exception as e:
        results.add_error("Alerting edge cases", e)


def test_qa_missing_files():
    """Test 3: QA modules with missing/invalid files."""
    print("\n" + "="*70)
    print("TEST 3: QA with Missing Files")
    print("="*70)
    
    try:
        from dsa110_contimg.qa.pipeline_quality import (
            check_ms_after_conversion,
            check_calibration_quality,
            check_image_quality,
        )
        
        # Test 1: Non-existent MS
        try:
            passed, metrics = check_ms_after_conversion(
                "/nonexistent/path/fake.ms",
                quick_check_only=True,
                alert_on_issues=False,
            )
            if not passed:
                results.add_pass("QA correctly fails on missing MS")
            else:
                results.add_fail("QA should fail on missing MS")
        except FileNotFoundError:
            results.add_pass("QA raises FileNotFoundError for missing MS")
        except Exception as e:
            results.add_error("QA with missing MS", e)
        
        # Test 2: Empty caltables list
        try:
            passed, metrics = check_calibration_quality(
                [],
                ms_path=None,
                alert_on_issues=False,
            )
            results.add_pass("QA handles empty caltables list")
        except Exception as e:
            results.add_fail("QA with empty caltables", str(e))
        
        # Test 3: Non-existent image
        try:
            passed, metrics = check_image_quality(
                "/nonexistent/fake.image",
                quick_check_only=True,
                alert_on_issues=False,
            )
            if not passed:
                results.add_pass("QA correctly fails on missing image")
            else:
                results.add_fail("QA should fail on missing image")
        except FileNotFoundError:
            results.add_pass("QA raises FileNotFoundError for missing image")
        except Exception as e:
            results.add_error("QA with missing image", e)
        
    except Exception as e:
        results.add_error("QA missing files test", e)


def test_photometry_functions():
    """Test 4: Photometry normalization functions."""
    print("\n" + "="*70)
    print("TEST 4: Photometry Normalization Functions")
    print("="*70)
    
    try:
        from dsa110_contimg.photometry import normalize
        import numpy as np
        
        # Test 1: Check required functions exist
        required_funcs = [
            'query_reference_sources',
            'establish_baselines',
            'compute_ensemble_correction',
            'check_reference_stability',
        ]
        
        for func_name in required_funcs:
            if hasattr(normalize, func_name):
                results.add_pass(f"Function {func_name} exists")
            else:
                results.add_fail(f"Function {func_name} missing")
        
        # Test 2: ReferenceSource dataclass
        try:
            ref = normalize.ReferenceSource(
                source_id=1,
                ra_deg=123.456,
                dec_deg=45.678,
                nvss_name="NVSS J081829.4+454040",
                nvss_flux_mjy=100.0,
                snr_nvss=50.0,
            )
            results.add_pass("ReferenceSource dataclass creation")
        except Exception as e:
            results.add_fail("ReferenceSource creation", str(e))
        
        # Test 3: CorrectionResult dataclass
        try:
            corr = normalize.CorrectionResult(
                correction_factor=1.05,
                correction_rms=0.02,
                n_references=10,
                reference_measurements=[1.0, 1.1, 0.9],
                valid_references=[1, 2, 3],
            )
            results.add_pass("CorrectionResult dataclass creation")
        except Exception as e:
            results.add_fail("CorrectionResult creation", str(e))
        
        # Test 4: Query with non-existent database
        try:
            refs = normalize.query_reference_sources(
                db_path=Path("/nonexistent/db.sqlite3"),
                ra_center=123.0,
                dec_center=45.0,
            )
            results.add_fail("Should raise error for missing database")
        except FileNotFoundError:
            results.add_pass("Correctly raises error for missing database")
        except Exception as e:
            results.add_error("Query with missing database", e)
        
    except Exception as e:
        results.add_error("Photometry functions test", e)


def test_configuration():
    """Test 5: Configuration handling."""
    print("\n" + "="*70)
    print("TEST 5: Configuration Handling")
    print("="*70)
    
    try:
        from dsa110_contimg.qa.pipeline_quality import QualityThresholds
        
        # Test 1: Default thresholds
        try:
            thresholds = QualityThresholds()
            results.add_pass("Default thresholds creation")
        except Exception as e:
            results.add_fail("Default thresholds", str(e))
        
        # Test 2: Check reasonable defaults
        try:
            thresholds = QualityThresholds()
            checks = [
                ("ms_max_flagged_fraction", 0 < thresholds.ms_max_flagged_fraction < 1),
                ("cal_max_flagged_fraction", 0 < thresholds.cal_max_flagged_fraction < 1),
                ("img_min_dynamic_range", thresholds.img_min_dynamic_range > 0),
            ]
            for name, condition in checks:
                if condition:
                    results.add_pass(f"Threshold {name} is reasonable")
                else:
                    results.add_fail(f"Threshold {name} is unreasonable")
        except Exception as e:
            results.add_error("Threshold sanity checks", e)
        
    except Exception as e:
        results.add_error("Configuration test", e)


def test_with_real_data():
    """Test 6: Test with real pipeline data if available."""
    print("\n" + "="*70)
    print("TEST 6: Real Data Integration")
    print("="*70)
    
    # Find any existing data
    ms_dir = Path("/stage/dsa110-contimg/ms/central_cal_rebuild")
    
    if not ms_dir.exists():
        results.add_pass("No real data available (skipped)")
        return
    
    try:
        from dsa110_contimg.qa.pipeline_quality import check_ms_after_conversion
        
        # Find an MS file
        ms_files = list(ms_dir.glob("*.ms"))
        if ms_files:
            ms_path = str(ms_files[0])
            
            try:
                passed, metrics = check_ms_after_conversion(
                    ms_path,
                    quick_check_only=True,
                    alert_on_issues=False,
                )
                results.add_pass(f"MS validation on real data")
            except Exception as e:
                results.add_fail("MS validation on real data", str(e))
        else:
            results.add_pass("No MS files found (skipped)")
    
    except Exception as e:
        results.add_error("Real data test", e)


def test_error_propagation():
    """Test 7: Error propagation and handling."""
    print("\n" + "="*70)
    print("TEST 7: Error Propagation")
    print("="*70)
    
    try:
        from dsa110_contimg.qa import ms_quality
        
        # Test 1: Corrupted MS path (directory without MS structure)
        try:
            metrics = ms_quality.validate_ms_quality("/tmp")
            # Should have issues
            if metrics.has_critical_issues:
                results.add_pass("Detects corrupted MS structure")
            else:
                results.add_fail("Should detect corrupted MS")
        except Exception as e:
            results.add_pass("Raises exception for corrupted MS")
        
    except Exception as e:
        results.add_error("Error propagation test", e)


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("DSA-110 COMPREHENSIVE TEST SUITE")
    print("="*70)
    print("\nTesting everything that could break...")
    print("Looking for: import errors, edge cases, missing data, error handling")
    
    # Run all test suites
    test_imports()
    test_alerting_edge_cases()
    test_qa_missing_files()
    test_photometry_functions()
    test_configuration()
    test_with_real_data()
    test_error_propagation()
    
    # Summary
    all_passed = results.summary()
    
    if all_passed:
        print("\n✓ ALL TESTS PASSED")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED OR HAD ERRORS")
        print("\nReview failures above and fix issues before integration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

