#!/usr/bin/env python3
"""Copy phased MS and concatenate SPWs."""

import sys

sys.path.insert(0, "src")
import os
import shutil

from casacore.tables import table

from dsa110_contimg.conversion.merge_spws import merge_spws

# Paths
ms_path = "/stage/dsa110-contimg/ms/0834_20251029/2025-10-29T13:54:17.phased.ms"
ms_dir = os.path.dirname(ms_path)
ms_base = os.path.basename(ms_path).rstrip(".ms")
ms_copy = os.path.join(ms_dir, f"{ms_base}_concat.ms")
ms_concat = os.path.join(ms_dir, f"{ms_base}_concat_spws.ms")

print("=" * 70)
print("COPYING AND CONCATENATING SPWs")
print("=" * 70)

# Step 1: Copy the phased MS
print("\nStep 1: Copying phased MS...")
print(f"  Source: {ms_path}")
print(f"  Destination: {ms_copy}")

if os.path.exists(ms_copy):
    print("  Removing existing copy...")
    shutil.rmtree(ms_copy)

print("  Copying...")
shutil.copytree(ms_path, ms_copy)
print(f"  ✓ Copy created: {ms_copy}")

# Verify copy
with table(ms_copy + "/SPECTRAL_WINDOW", readonly=True) as spw:
    nspw_orig = spw.nrows()
    print(f"  Copy verified: {nspw_orig} SPWs")

# Step 2: Concatenate SPWs using merge_spws
print("\nStep 2: Concatenating SPWs using merge_spws...")
print(f"  Input: {ms_copy}")
print(f"  Output: {ms_concat}")

try:
    print("  Running merge_spws...")
    merge_spws(
        ms_in=ms_copy,
        ms_out=ms_concat,
        datacolumn="all",
        regridms=True,  # Regrid to contiguous frequency grid
        interpolation="linear",
        keepflags=True,
        remove_sigma_spectrum=True,
    )
    print(f"  ✓ Concatenated MS created: {ms_concat}")
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# Step 3: Verify the result
print("\nStep 3: Verifying concatenated MS...")

with table(ms_concat + "/SPECTRAL_WINDOW", readonly=True) as spw:
    nspw = spw.nrows()
    print(f"  Number of SPWs in concatenated MS: {nspw}")

    if nspw == 1:
        print("  ✓ Successfully concatenated to 1 SPW")

        # Get frequency info
        ref_freq = spw.getcol("REF_FREQUENCY")[0]
        nchans = spw.getcol("NUM_CHAN")[0]
        total_bw = spw.getcol("TOTAL_BANDWIDTH")[0]

        print(f"  Reference frequency: {ref_freq / 1e9:.6f} GHz")
        print(f"  Total channels: {nchans}")
        print(f"  Total bandwidth: {total_bw / 1e6:.3f} MHz")
    else:
        print(f"  ⚠ Expected 1 SPW, found {nspw}")

with table(ms_concat, readonly=True) as tb:
    nrows = tb.nrows()
    print(f"  Total rows: {nrows:,}")

print("\n" + "=" * 70)
print("COMPLETE")
print("=" * 70)
