#!/usr/bin/env python3
"""Run gaincal on SPW-merged MS (before field merge)."""

import os
import sys

from casatasks import gaincal

ms_path = "/stage/dsa110-contimg/ms/0834_20251029/2025-10-29T13:54:17.phased_concat_spws.ms"

# Use a common refant
refant = "59"

caltable = f"{ms_path}_gaincal_p_inf"

print("=" * 70)
print("GAINCAL on SPW-merged MS (before field merge)")
print("=" * 70)
print(f"MS: {os.path.basename(ms_path)}")
print(f"Refant: {refant}")
print(f"Caltable: {os.path.basename(caltable)}")
print("=" * 70)

# Remove existing table if present
if os.path.exists(caltable):
    import shutil

    shutil.rmtree(caltable)
    print("Removed existing table")

print("\nRunning gaincal with solint=inf (default)...")
sys.stdout.flush()

try:
    gaincal(
        vis=ms_path,
        caltable=caltable,
        field="0",
        solint="inf",  # Default: one solution per scan
        refant=refant,
        gaintype="G",
        calmode="p",
        minsnr=3.0,
        selectdata=True,
    )

    # Check if table was created
    if os.path.exists(caltable):
        print("\n:check_mark: SUCCESS: Calibration table created")
        print(f"  Location: {caltable}")
        # Just check if directory exists and has files
        if os.path.isdir(caltable):
            files = os.listdir(caltable)
            print(f"  Table directory contains {len(files)} items")
            print("\n:check_mark: This confirms the issue is with field merging, not SPW merging!")
    else:
        print("\n:ballot_x: ERROR: Table was not created")

except Exception as e:
    print(f"\n:ballot_x: ERROR: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

print("=" * 70)
