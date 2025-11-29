#!/usr/bin/env python3
"""Quick test: self-cal WITHOUT catalog masking to isolate the hang issue."""

import sys
from pathlib import Path

sys.path.insert(0, "/data/dsa110-contimg/src/dsa110_contimg/src")

from dsa110_contimg.calibration.selfcal import SelfCalConfig, selfcal_ms

# MS and caltables
MS_PATH = Path("/stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms")
INITIAL_CALTABLES = [
    "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_bpcal",
    "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_gpcal",
    "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_2gcal",
]

OUTPUT_DIR = Path("/stage/dsa110-contimg/test_data/selfcal_no_mask_test")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("SELF-CAL TEST WITHOUT MASKING (to isolate hang)")
print("=" * 80)
print(f"MS: {MS_PATH}")
print(f"Output: {OUTPUT_DIR}")
print("=" * 80)
print()

# Minimal config: NO NVSS seeding, just 1 phase iteration
config = SelfCalConfig(
    max_iterations=1,
    phase_solints=["inf"],
    do_amplitude=False,
    niter=10000,
    threshold="0.0005Jy",
    robust=-0.5,
    field="0",
    use_nvss_seeding=False,  # NO MASKING
    calib_ra_deg=129.278,
    calib_dec_deg=55.381,
    calib_flux_jy=0.050,
)

print("Starting self-cal (1 iteration, no masking)...")
success, summary = selfcal_ms(
    ms_path=MS_PATH,
    output_dir=OUTPUT_DIR,
    config=config,
    initial_caltables=INITIAL_CALTABLES,
)

print()
print("=" * 80)
if success:
    print("✅ SUCCESS - No hang!")
    print(f"SNR: {summary.get('final_snr', 0.0):.2f}")
else:
    print("❌ FAILED")
print("=" * 80)
