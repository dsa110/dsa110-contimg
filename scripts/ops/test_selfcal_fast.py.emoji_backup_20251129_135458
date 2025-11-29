#!/usr/bin/env python3
"""
Ultra-fast self-calibration test (<3 minutes)
Tests basic self-cal functionality with minimal imaging parameters.
"""

import logging
from pathlib import Path

from dsa110_contimg.calibration.selfcal import SelfCalConfig, selfcal_ms

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

MS_PATH = Path("/stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms")
OUTPUT_DIR = Path("/stage/dsa110-contimg/test_data/selfcal_output_fast")

# Initial calibration tables (already applied to MS)
INITIAL_CALTABLES = [
    "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_bpcal",
    "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_gpcal",
    "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_2gcal",
]

# ============================================================================
# Main Test
# ============================================================================


def main():
    """Run ultra-fast self-calibration test."""
    logger.info("=" * 80)
    logger.info("ULTRA-FAST SELF-CALIBRATION TEST - 0834+555")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Goal: Test self-cal pipeline in <3 minutes")
    logger.info("")
    logger.info(f"Input MS: {MS_PATH}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Initial caltables: {len(INITIAL_CALTABLES)}")
    logger.info("")
    logger.info("Calibrator: 0834+555")
    logger.info("  RA:  129.278 deg")
    logger.info("  Dec: 55.381 deg")
    logger.info("  Flux: 50.0 mJy")
    logger.info("")

    # Fast configuration - prioritize speed over quality
    config = SelfCalConfig(
        max_iterations=2,  # Just 1 phase self-cal iteration
        min_snr_improvement=1.01,
        phase_solints=["inf"],  # Single solution interval
        phase_minsnr=3.0,
        amp_solint=None,  # Skip amplitude self-cal for speed
        amp_minsnr=5.0,
        niter=2000,  # Minimal cleaning
        threshold="0.001Jy",  # Stop early
        robust=0.0,  # Natural weighting (faster)
        deconvolver="hogbom",  # Fastest deconvolver
        imsize=1024,  # Small image (was 6300!)
        field="0",  # Single field only
        use_nvss_seeding=False,
        calib_ra_deg=129.278,
        calib_dec_deg=55.381,
        calib_flux_jy=0.050,
    )

    logger.info("Configuration:")
    logger.info(f"  Max iterations: {config.max_iterations}")
    logger.info(f"  Phase solution intervals: {config.phase_solints}")
    logger.info(f"  Amplitude self-cal: DISABLED (for speed)")
    logger.info(f"  Image size: {config.imsize} pixels (1024x1024)")
    logger.info(f"  Clean iterations: {config.niter}")
    logger.info(f"  Threshold: {config.threshold}")
    logger.info(f"  Robust weighting: {config.robust}")
    logger.info(f"  Deconvolver: {config.deconvolver} **HOGBOM (FAST)**")
    logger.info(f"  Field selection: '{config.field}' (single field)")
    logger.info("")
    logger.info("-" * 80)

    # Run self-calibration
    success, summary = selfcal_ms(
        ms_path=MS_PATH,
        output_dir=OUTPUT_DIR,
        config=config,
        initial_caltables=INITIAL_CALTABLES,
    )

    # Print summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("FAST TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Success: {success}")
    logger.info(f"Iterations completed: {summary.get('iterations_completed', 0)}")
    logger.info(
        f"Initial SNR: {summary.get('initial_snr', 0):.1f}x (peak={summary.get('initial_peak_jy', 0)*1000:.1f} mJy)"
    )
    logger.info(
        f"Final SNR: {summary.get('final_snr', 0):.1f}x (peak={summary.get('final_peak_jy', 0)*1000:.1f} mJy)"
    )
    logger.info(
        f"SNR improvement: {summary.get('snr_improvement_factor', 1.0):.2f}x ({(summary.get('snr_improvement_factor', 1.0)-1)*100:.1f}%)"
    )
    logger.info(f"Best iteration: {summary.get('best_iteration', -1)}")
    logger.info(
        f"Best SNR: {summary.get('best_snr', 0):.1f}x (image: {summary.get('best_image', 'N/A')})"
    )

    if success:
        logger.info("")
        logger.info(":check: Fast self-calibration test PASSED")
        logger.info(f"  Output: {OUTPUT_DIR}")
        logger.info(
            f"  Best image: {OUTPUT_DIR}/selfcal_iter{summary.get('best_iteration', 0)}-image.fits"
        )
    else:
        logger.error("")
        logger.error(":cross: Fast self-calibration test FAILED")
        logger.error(f"  Reason: {summary.get('error', 'Unknown')}")

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
