#!/usr/bin/env python3
"""Quick masked self-cal test - 1 iteration only for validation."""

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

OUTPUT_DIR = Path("/stage/dsa110-contimg/test_data/selfcal_masked_quick")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("QUICK MASKED SELF-CAL VALIDATION TEST")
print("=" * 80)
print("Config: 1 iteration, 10 mJy, low resolution")
print("Expected runtime: 2-3 minutes")
print("=" * 80)
print()

# Ultra-fast config for validation
config = SelfCalConfig(
    max_iterations=1,  # Just 1 iteration
    phase_solints=["inf"],  # One solution interval
    do_amplitude=False,  # Skip amplitude
    niter=5000,  # Fewer iterations
    threshold="0.001Jy",  # Coarser threshold
    robust=-0.5,
    field="0",
    use_nvss_seeding=True,  # TEST THE FIX
    nvss_min_mjy=10.0,  # 10 mJy limit
    # No calibrator model (fix for MODEL_DATA conflict)
    calib_ra_deg=None,
    calib_dec_deg=None,
    calib_flux_jy=None,
)

print("Starting quick validation test...")
success, summary = selfcal_ms(
    ms_path=MS_PATH,
    output_dir=OUTPUT_DIR,
    config=config,
    initial_caltables=INITIAL_CALTABLES,
)

print()
print("=" * 80)
if success:
    print(":check: SUCCESS - Masked self-cal works!")
    final_snr = summary.get("final_snr", 0.0)
    print(f"Final SNR: {final_snr:.2f}")
    print(f"Iterations: {summary.get('iterations_completed', 0)}")
else:
    print(":cross: FAILED")
print("=" * 80)
