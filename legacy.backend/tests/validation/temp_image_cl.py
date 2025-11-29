#!/usr/bin/env python3
"""Image component list for 0834+555."""

import sys

sys.path.insert(0, "src")
import os
import shutil

from astropy.coordinates import Angle
from casacore.tables import table
from casatasks import tclean

from dsa110_contimg.calibration.catalogs import get_calibrator_radec, load_vla_catalog
from dsa110_contimg.calibration.skymodels import ft_from_cl

# Paths
ms_path = "/stage/dsa110-contimg/ms/0834_20251029/2025-10-29T13:54:17.phased.ms"
cl_path = "/stage/dsa110-contimg/ms/0834_20251029/0834+555.cl"
output_dir = "/stage/dsa110-contimg/ms/0834_20251029"
imagename = os.path.join(output_dir, "0834+555_component_only")

print("=" * 70)
print("IMAGING COMPONENT LIST: 0834+555")
print("=" * 70)

# Step 1: Apply component list to MODEL_DATA
print("\nStep 1: Applying component list to MODEL_DATA...")
try:
    ft_from_cl(ms_path, cl_path, field="", usescratch=True)
    print("  :check_mark: Component list applied")
except Exception as e:
    print(f"  :ballot_x: Error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# Step 2: Create a temporary MS with MODEL_DATA copied to DATA
print("\nStep 2: Creating temporary MS with MODEL_DATA...")
temp_ms = os.path.join(output_dir, "temp_model_ms.ms")

# Copy the MS
if os.path.exists(temp_ms):
    shutil.rmtree(temp_ms)
print(f"  Copying MS to: {temp_ms}")
shutil.copytree(ms_path, temp_ms)

# Copy MODEL_DATA to DATA in the temp MS
print("  Copying MODEL_DATA to DATA...")
with table(temp_ms, readonly=False) as tb:
    if "MODEL_DATA" in tb.colnames() and "DATA" in tb.colnames():
        model_data = tb.getcol("MODEL_DATA")
        tb.putcol("DATA", model_data)
        print("  :check_mark: Copied MODEL_DATA to DATA")
    else:
        print("  :ballot_x: Required columns not found")
        sys.exit(1)

# Step 3: Image the temporary MS
print("\nStep 3: Imaging MODEL_DATA...")

# Get phasecenter
catalog = load_vla_catalog()
ra_deg, dec_deg = get_calibrator_radec(catalog, "0834+555")
ra_hms = (
    Angle(ra_deg, unit="deg")
    .to_string(unit="hourangle", sep="hms", precision=2, pad=True)
    .replace(" ", "")
)
dec_dms = (
    Angle(dec_deg, unit="deg")
    .to_string(unit="deg", sep="dms", precision=2, alwayssign=True, pad=True)
    .replace(" ", "")
)
phasecenter = f"J2000 {ra_hms} {dec_dms}"

os.makedirs(output_dir, exist_ok=True)

try:
    print(f"  Running tclean (phasecenter: {phasecenter})...")
    tclean(
        vis=temp_ms,
        imagename=imagename,
        field="",
        spw="",
        imsize=512,
        cell="1.0arcsec",
        weighting="natural",
        specmode="mfs",
        deconvolver="hogbom",
        niter=0,
        threshold="0.0Jy",
        datacolumn="DATA",
        pbcor=True,
        phasecenter=phasecenter,
        gridder="standard",
        pblimit=0.2,
        savemodel="none",
    )
    print("  :check_mark: Image created")
except Exception as e:
    print(f"  :ballot_x: Error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# Step 4: Clean up temp MS
print("\nStep 4: Cleaning up...")
if os.path.exists(temp_ms):
    shutil.rmtree(temp_ms)
    print("  :check_mark: Removed temporary MS")

# Verify image
image_path = imagename + ".image"
if os.path.exists(image_path):
    from casatools import image as imtool

    ia = imtool()
    ia.open(image_path)
    shape = ia.shape()
    stats = ia.statistics()
    max_val = stats["max"][0]
    print(f"\n:check_mark: Image created: {image_path}")
    print(f"  Shape: {shape}")
    print(f"  Peak flux: {max_val:.3f} Jy/beam")
    ia.close()
else:
    print(f"\n:ballot_x: Image not found: {image_path}")

print("\n" + "=" * 70)
print("COMPLETE")
print("=" * 70)
