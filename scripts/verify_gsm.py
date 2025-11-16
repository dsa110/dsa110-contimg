#!/usr/bin/env python3
"""Simple verification script for GSM generation.

This script verifies that the exact code from the user's example works:
    import pygdsm
    sky_map = pygdsm.GlobalSkyModel16().generate(1400)
    hp.mollview(np.log10(sky_map), title="GSM at 1.4 GHz (log10 scale)",
                unit="log$_{10}$(K)", cmap="inferno")

Run with: python scripts/verify_gsm.py
"""

import sys

try:
    import healpy as hp
    import matplotlib
    import numpy as np
    import pygdsm

    matplotlib.use("Agg")  # Use non-interactive backend
    import matplotlib.pyplot as plt
except ImportError as e:
    print(f"ERROR: Missing required package: {e}")
    print("\nInstall required packages with:")
    print("  pip install pygdsm healpy numpy matplotlib")
    sys.exit(1)

print("=" * 60)
print("GSM Sky Map Generation Verification")
print("=" * 60)

print("\n1. Testing: import pygdsm")
print("   ✓ pygdsm imported successfully")

print("\n2. Testing: pygdsm.GlobalSkyModel16().generate(1400)")
gsm = pygdsm.GlobalSkyModel16()
sky_map = gsm.generate(1400)
print(f"   ✓ Sky map generated successfully")
print(f"     Shape: {sky_map.shape}")
print(f"     Size: {sky_map.size}")
print(f"     Min: {np.min(sky_map):.6e} K")
print(f"     Max: {np.max(sky_map):.6e} K")
print(f"     Mean: {np.mean(sky_map):.6e} K")

print("\n3. Testing: np.log10(sky_map)")
log_sky_map = np.log10(sky_map + 1e-10)
print(f"   ✓ Log10 transformation successful")
print(f"     Log min: {np.min(log_sky_map):.6f}")
print(f"     Log max: {np.max(log_sky_map):.6f}")

print("\n4. Testing: healpy properties")
nside = hp.get_nside(sky_map)
npix = hp.nside2npix(nside)
print(f"   ✓ HEALPix properties:")
print(f"     NSIDE: {nside}")
print(f"     NPIX: {npix}")

print("\n5. Testing: hp.mollview() (without display)")
# Test that mollview can be called (we'll suppress the actual plot)
try:
    # Create a figure but don't show it
    fig = plt.figure(figsize=(10, 5))
    hp.mollview(
        np.log10(sky_map),
        title="GSM at 1.4 GHz (log10 scale)",
        unit="log$_{10}$(K)",
        cmap="inferno",
        fig=fig.number,
        return_projected_map=False,
    )
    plt.close(fig)  # Close without showing
    print("   ✓ hp.mollview() works correctly")
    print("     (Plot generated but not displayed in headless mode)")
except Exception as e:
    print(f"   ✗ hp.mollview() failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ ALL VERIFICATIONS PASSED!")
print("=" * 60)
print("\nThe GSM generation code works correctly:")
print("  - pygdsm.GlobalSkyModel16().generate(1400) ✓")
print("  - np.log10(sky_map) ✓")
print("  - hp.mollview() ✓")
print("\nThe backend implementation should work correctly when")
print("pygdsm and healpy are installed in the backend environment.")
