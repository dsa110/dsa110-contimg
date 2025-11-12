#!/usr/bin/env python3
"""
Test script to run DSA-110 declination tracking analysis.

This is a simple wrapper around the main tracking script that can be easily run
to test the DSA-110 declination tracking functionality.
"""

import subprocess
import sys
import os
from pathlib import Path


def main():
    """Run the DSA-110 declination tracking test."""
    script_dir = Path(__file__).parent
    main_script = script_dir / "track_dsa110_declination.py"
    output_dir = script_dir.parent / "output"
    
    # Ensure output directory exists
    output_dir.mkdir(exist_ok=True)
    
    print("Running DSA-110 Declination Tracking Test")
    print("=" * 50)
    
    # Run the main tracking script
    cmd = [
        sys.executable,
        str(main_script),
        "--output-dir", str(output_dir)
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✓ Test completed successfully!")
        print("\nOutput:")
        print(result.stdout)
        
        if result.stderr:
            print("\nWarnings/Errors:")
            print(result.stderr)
            
        # Check if output files were created
        plot_file = output_dir / "dsa110_ra_dec_tracking.png"
        data_file = output_dir / "dsa110_ra_dec_data.csv"
        
        if plot_file.exists() and data_file.exists():
            print(f"\n✓ Output files created:")
            print(f"  - Plot: {plot_file}")
            print(f"  - Data: {data_file}")
        else:
            print("\n✗ Output files not found!")
            return 1
            
    except subprocess.CalledProcessError as e:
        print(f"✗ Test failed with exit code {e.returncode}")
        print("\nError output:")
        print(e.stderr)
        return e.returncode
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
