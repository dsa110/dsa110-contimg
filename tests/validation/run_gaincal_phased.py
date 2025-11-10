#!/usr/bin/env python3
"""Run gaincal on 2025-10-29T13:54:17.phased.ms

This phase-only gaincal output can be used as input to bandpass() via gaintable.
The .gcal extension follows CASA naming conventions for gain calibration tables.
"""
import os

from casatasks import gaincal

ms_path = "/stage/dsa110-contimg/ms/0834_20251029/2025-10-29T13:54:17.phased.ms"
refant = "59"  # Middle antenna
# Use .gcal extension for gain calibration table (standard CASA convention)
# This table can be passed to bandpass() via gaintable parameter
caltable = f"{ms_path}.gaincal_p30s.gcal"

print("=" * 70)
print("Running gaincal on phased MS")
print("=" * 70)
print(f"MS: {os.path.basename(ms_path)}")
print(f"Field: 0")
print(f"Refant: {refant}")
print(f"Mode: phase-only (p)")
print(f"Solint: 30s")
print(f"Output: {os.path.basename(caltable)}")
print("=" * 70)

# Remove existing table if present
if os.path.exists(caltable):
    import shutil

    shutil.rmtree(caltable)
    print("Removed existing calibration table")

print("\nRunning gaincal...")

gaincal(
    vis=ms_path,
    caltable=caltable,
    field="0",
    solint="30s",
    refant=refant,
    gaintype="G",
    calmode="p",  # Phase-only
    minsnr=3.0,
    selectdata=True,
)

if os.path.exists(caltable):
    print(f"\n✓ SUCCESS: Calibration table created")
    print(f"  Location: {caltable}")
else:
    print(f"\n✗ ERROR: Calibration table was not created")

print("=" * 70)
