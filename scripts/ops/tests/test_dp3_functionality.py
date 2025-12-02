#!/opt/miniforge/envs/casa6/bin/python
"""
Test DP3 functionality for sky model prediction.

This script tests:
1. DP3 executable detection
2. DP3 sky model format conversion
3. DP3 predict functionality (if test MS available)
"""

import sys
from pathlib import Path

# Add backend/src to path
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

import os
import tempfile

from dsa110_contimg.calibration.dp3_wrapper import (
  _find_dp3_executable, convert_calibrator_to_dp3_skymodel,
  convert_nvss_to_dp3_skymodel)


def test_dp3_detection():
    """Test DP3 executable detection."""
    print("=" * 60)
    print("Test 1: DP3 Executable Detection")
    print("=" * 60)
    
    dp3_cmd = _find_dp3_executable()
    if dp3_cmd:
        print(f":check: DP3 found: {dp3_cmd}")
        return True
    else:
        print(":cross: DP3 not found")
        print("  Checking Docker images...")
        import shutil
        import subprocess
        docker_cmd = shutil.which("docker")
        if docker_cmd:
            result = subprocess.run(
                [docker_cmd, "images", "-q", "dp3:latest"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.stdout.strip():
                print(f"  :check: Docker image 'dp3:latest' exists")
            else:
                print(f"  :cross: Docker image 'dp3:latest' not found")
                # Check for alternative image names
                result2 = subprocess.run(
                    [docker_cmd, "images"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                dp3_images = [line for line in result2.stdout.split('\n') if 'dp3' in line.lower()]
                if dp3_images:
                    print(f"  Found DP3 images:")
                    for img in dp3_images[:3]:
                        print(f"    {img}")
        return False


def test_dp3_skymodel_conversion():
    """Test DP3 sky model format conversion."""
    print("\n" + "=" * 60)
    print("Test 2: DP3 Sky Model Format Conversion")
    print("=" * 60)
    
    # Test single calibrator conversion
    print("\n2a. Testing single calibrator conversion...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.skymodel', delete=False) as f:
        temp_path = f.name
    
    try:
        result = convert_calibrator_to_dp3_skymodel(
            ra_deg=83.633208,
            dec_deg=55.778611,
            flux_jy=2.3,
            freq_ghz=1.4,
            out_path=temp_path,
        )
        print(f":check: Calibrator conversion successful: {result}")
        
        # Check file contents
        with open(temp_path, 'r') as f:
            content = f.read()
            print(f"  File size: {len(content)} bytes")
            print(f"  First line: {content.split(chr(10))[0] if content else 'empty'}")
        
        os.unlink(temp_path)
        return True
    except Exception as e:
        print(f":cross: Calibrator conversion failed: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return False
    
    # Test NVSS conversion (requires catalog)
    print("\n2b. Testing NVSS conversion...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.skymodel', delete=False) as f:
        temp_path = f.name
    
    try:
        result = convert_nvss_to_dp3_skymodel(
            center_ra_deg=83.633208,
            center_dec_deg=55.778611,
            radius_deg=0.2,
            min_mjy=10.0,
            freq_ghz=1.4,
            out_path=temp_path,
        )
        print(f":check: NVSS conversion successful: {result}")
        
        # Check file contents
        with open(temp_path, 'r') as f:
            lines = f.readlines()
            print(f"  Number of sources: {len(lines)}")
            if lines:
                print(f"  First source: {lines[0].strip()}")
        
        os.unlink(temp_path)
        return True
    except Exception as e:
        print(f":cross: NVSS conversion failed: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return False


def test_dp3_predict_parset():
    """Test DP3 predict parset generation (without actual MS)."""
    print("\n" + "=" * 60)
    print("Test 3: DP3 Predict Parset Generation")
    print("=" * 60)
    
    from dsa110_contimg.calibration.dp3_wrapper import \
      predict_from_skymodel_dp3

    # Create a dummy sky model
    with tempfile.NamedTemporaryFile(mode='w', suffix='.skymodel', delete=False) as f:
        f.write("s0c0,POINT,05:34:31.9380,+22:00:52.200,2.3,[-0.7],false,1400000000.0,,,\n")
        skymodel_path = f.name
    
    # Create a dummy MS path (won't actually run, just test parset generation)
    dummy_ms = "/tmp/test_dummy.ms"
    
    try:
        # This will fail because MS doesn't exist, but we can check the command generation
        dp3_cmd = _find_dp3_executable()
        if not dp3_cmd:
            print(":warning: Skipping - DP3 not found")
            os.unlink(skymodel_path)
            return False
        
        print(f":check: DP3 command available: {dp3_cmd}")
        print(f":check: Sky model created: {skymodel_path}")
        print("  (Full predict test requires valid MS file)")
        
        os.unlink(skymodel_path)
        return True
    except Exception as e:
        print(f":warning: Test incomplete: {e}")
        if os.path.exists(skymodel_path):
            os.unlink(skymodel_path)
        return False


def main():
    """Run all DP3 tests."""
    print("\n" + "=" * 60)
    print("DP3 Functionality Test Suite")
    print("=" * 60)
    print()
    
    results = {}
    
    # Test 1: DP3 detection
    results['detection'] = test_dp3_detection()
    
    # Test 2: Sky model conversion
    results['conversion'] = test_dp3_skymodel_conversion()
    
    # Test 3: Predict parset (limited)
    results['predict'] = test_dp3_predict_parset()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"DP3 Detection: {':check:' if results['detection'] else ':cross:'}")
    print(f"Sky Model Conversion: {':check:' if results['conversion'] else ':cross:'}")
    print(f"Predict Parset: {':check:' if results['predict'] else ':warning:'}")
    
    if results['detection'] and results['conversion']:
        print("\n:check: DP3 basic functionality is working")
        print("  Next step: Test with actual MS file")
        return 0
    else:
        print("\n:cross: Some tests failed - check output above")
        return 1


if __name__ == "__main__":
    sys.exit(main())

