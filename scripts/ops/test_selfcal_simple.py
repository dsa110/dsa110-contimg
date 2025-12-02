#!/usr/bin/env python3
"""
Simple self-calibration test - NO NVSS seeding to avoid Docker hang.

This test uses standard self-calibration without catalog-based MODEL_DATA
seeding, which avoids the Docker container cleanup hang issue.
"""

import sys
from pathlib import Path

# Add backend/src to path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from dsa110_contimg.calibration.selfcal import SelfCalConfig, selfcal_ms

MS_PATH = Path("/stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms")
INITIAL_CALTABLES = [
    "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_bpcal",
    "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_gpcal",
    "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_2gcal",
]

OUTPUT_DIR = Path("/stage/dsa110-contimg/test_data/selfcal_simple")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("SIMPLE SELF-CALIBRATION TEST")
print("=" * 80)
print("Strategy: Standard self-cal without NVSS seeding")
print("         (avoids Docker container hang issue)")
print("=" * 80)
print()

# Simple config: No NVSS seeding, just clean self-cal
config = SelfCalConfig(
    max_iterations=3,
    phase_solints=["inf", "120s"],
    do_amplitude=True,
    amp_solint="inf",
    niter=50000,
    threshold="0.0001Jy",
    robust=-0.5,
    field="0",
    # NO NVSS seeding (avoids Docker hang)
    use_nvss_seeding=False,
    # Use calibrator model for initial MODEL_DATA
    calib_ra_deg=129.278,
    calib_dec_deg=55.381,
    calib_flux_jy=0.050,
)

print("Starting simple self-calibration...")
success, summary = selfcal_ms(
    ms_path=MS_PATH,
    output_dir=OUTPUT_DIR,
    config=config,
    initial_caltables=INITIAL_CALTABLES,
)

print()
print("=" * 80)
if success:
    print(":check: SUCCESS!")
    final_snr = summary.get("final_snr", 0.0)
    initial_snr = summary.get("initial_snr", 0.0)
    improvement = summary.get("total_snr_improvement", 0.0)
    iters = summary.get("iterations_completed", 0)
    print(f"Iterations: {iters}")
    print(f"Initial SNR: {initial_snr:.2f}")
    print(f"Final SNR: {final_snr:.2f}")
    print(f"Improvement: {improvement:.2f}x")
else:
    print(":cross: FAILED")
print("=" * 80)
