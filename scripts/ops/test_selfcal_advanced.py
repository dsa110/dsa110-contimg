#!/usr/bin/env python3
"""
Advanced self-calibration test on 0834+555 with aggressive parameters.

This script tests:
1. Multi-scale clean (better PSF artifact suppression)
2. Even deeper cleaning (lower threshold)
3. More iterations with shorter solution intervals
4. More uniform weighting (robust=-0.75)
"""

import logging
from pathlib import Path

from dsa110_contimg.calibration.selfcal import SelfCalConfig, selfcal_ms

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Input MS and calibration tables
MS_PATH = Path("/stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms")
OUTPUT_DIR = Path("/stage/dsa110-contimg/test_data/selfcal_output_advanced")
INITIAL_CALTABLES = [
    "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_bpcal",
    "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_gpcal",
    "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_2gcal",
]

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("ADVANCED SELF-CALIBRATION TEST - 0834+555")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Goal: Suppress PSF artifacts with multi-scale clean")
    logger.info("")

    # Calibrator source info (for model seeding)
    cal_ra_deg = 129.278  # 08h37m06.8s
    cal_dec_deg = 55.381  # +55d22m51s
    cal_flux_jy = 0.05  # 50 mJy at 1.4 GHz

    logger.info(f"Input MS: {MS_PATH}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Initial caltables: {len(INITIAL_CALTABLES)}")
    logger.info("")
    logger.info(f"Calibrator: 0834+555")
    logger.info(f"  RA:  {cal_ra_deg:.3f} deg")
    logger.info(f"  Dec: {cal_dec_deg:.3f} deg")
    logger.info(f"  Flux: {cal_flux_jy*1000:.1f} mJy")
    logger.info("")

    # ADVANCED Configuration for PSF artifact suppression
    config = SelfCalConfig(
        max_iterations=8,  # More iterations to fully converge
        min_snr_improvement=1.02,  # Continue even with small improvements (2%)
        stop_on_divergence=True,
        # Phase-only self-cal solution intervals (progressively shorter)
        phase_solints=["inf", "120s", "60s", "30s"],  # Shorter intervals for better tracking
        do_amplitude=True,  # Try amplitude self-cal at end
        amp_solint="inf",
        amp_minsnr=5.0,  # Minimum SNR for amplitude solutions
        amp_combine="",
        # Phase-only parameters
        phase_minsnr=3.0,
        phase_combine="",  # Don't combine across scans
        # Advanced parameters
        refant=None,  # Auto-select
        uvrange="",
        field="0",  # Only calibrator field (much faster)
        spw="",
        # **ADVANCED Imaging parameters**
        imsize=6300,
        cell_arcsec=1.0,
        niter=200000,  # 2x deeper clean
        threshold="0.00003Jy",  # 0.03 mJy - clean to ~3x RMS
        robust=-0.75,  # Even more uniform weighting for cleaner PSF
        backend="wsclean",
        deconvolver="multiscale",  # **KEY: Multi-scale clean**
        # Quality control
        min_initial_snr=10.0,
        # Model seeding (disabled for speed, but works now - Docker hang fixed)
        use_nvss_seeding=False,
        # Calibrator model for seeding
        calib_ra_deg=cal_ra_deg,
        calib_dec_deg=cal_dec_deg,
        calib_flux_jy=cal_flux_jy,
    )

    logger.info("Configuration:")
    logger.info(f"  Max iterations: {config.max_iterations}")
    logger.info(f"  Phase solution intervals: {config.phase_solints}")
    logger.info(f"  Min SNR improvement: {(config.min_snr_improvement-1)*100:.1f}%")
    logger.info(f"  Amplitude self-cal: {config.amp_solint} (min SNR: {config.amp_minsnr})")
    logger.info(f"  Image size: {config.imsize} pixels")
    logger.info(f"  Clean iterations: {config.niter}")
    logger.info(f"  Threshold: {config.threshold}")
    logger.info(f"  Robust weighting: {config.robust}")
    logger.info(f"  Deconvolver: {config.deconvolver} **MULTI-SCALE**")
    logger.info(f"  Field selection: '{config.field}' (single field)")

    # Run self-calibration
    logger.info("\nStarting advanced self-calibration...")
    logger.info("-" * 80)

    success, summary = selfcal_ms(
        ms_path=str(MS_PATH),
        output_dir=str(OUTPUT_DIR),
        config=config,
        initial_caltables=[str(ct) for ct in INITIAL_CALTABLES],
    )

    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("SELF-CALIBRATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Status: {summary['status']}")
    logger.info(f"Iterations completed: {summary['iterations_completed']}")
    logger.info(f"Total time: {summary['total_time_sec']:.1f} sec")
    logger.info("")
    logger.info("SNR Evolution:")
    for iter_result in summary["iterations"]:
        logger.info(
            f"  Iter {iter_result['iteration']}: "
            f"SNR {iter_result['snr']:.1f} "
            f"(improvement: {iter_result.get('snr_improvement', 1.0):.3f}x)"
        )
    logger.info("")
    logger.info(f"Initial SNR: {summary['initial_snr']:.1f}")
    logger.info(f"Final SNR: {summary['final_snr']:.1f}")
    logger.info(f"Total SNR improvement: {summary['snr_improvement']:.2f}x")
    logger.info("")
    logger.info("Output files:")
    logger.info(f"  Best image: {OUTPUT_DIR}/selfcal_iter{summary['best_iteration']}-image.fits")
    logger.info(f"  Summary JSON: {OUTPUT_DIR}/selfcal_summary.json")
