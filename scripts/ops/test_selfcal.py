#!/usr/bin/env python3
"""Test script for self-calibration on the calibrated 0834+555 data."""

import logging
import sys
from pathlib import Path

# Add backend/src to path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from dsa110_contimg.calibration.selfcal import SelfCalConfig, selfcal_ms

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("test_selfcal")

# Configuration
MS_PATH = "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms"
OUTPUT_DIR = "/stage/dsa110-contimg/test_data/selfcal_output_clean"
INITIAL_CALTABLES = [
    "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_bpcal",
    "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_gpcal",
    "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_2gcal",
]

# Calibrator information (0834+555)
CALIB_RA_DEG = 128.728752927042  # 08:34:54.9007 J2000
CALIB_DEC_DEG = 55.38156866948  # +55:22:53.6472 J2000
CALIB_FLUX_JY = 0.050  # Approximate flux at 1.4 GHz


def main():
    """Run self-calibration test."""
    logger.info("=" * 80)
    logger.info("SELF-CALIBRATION TEST: 0834+555")
    logger.info("=" * 80)
    logger.info(f"MS: {MS_PATH}")
    logger.info(f"Output: {OUTPUT_DIR}")
    logger.info(f"Initial calibration tables: {len(INITIAL_CALTABLES)}")

    # Check MS exists
    if not Path(MS_PATH).exists():
        logger.error(f"MS not found: {MS_PATH}")
        logger.error("Please run calibration first")
        return 1

    # Check calibration tables exist
    for caltable in INITIAL_CALTABLES:
        if not Path(caltable).exists():
            logger.error(f"Calibration table not found: {caltable}")
            return 1

    # Configure self-calibration
    # Start with conservative parameters for testing
    config = SelfCalConfig(
        max_iterations=5,
        min_snr_improvement=1.05,  # Stop if < 5% improvement
        stop_on_divergence=True,
        # Phase-only iterations (progressive solution intervals)
        phase_solints=["60s", "inf"],  # Start with 60s, then inf
        phase_minsnr=3.0,
        phase_combine="",
        # Amplitude+phase (final iteration)
        do_amplitude=True,
        amp_solint="inf",
        amp_minsnr=5.0,
        amp_combine="scan",
        # Imaging parameters (match previous successful imaging)
        imsize=1024,
        cell_arcsec=None,  # Auto-calculate
        niter=100000,  # Increased for deeper clean to remove PSF artifacts
        threshold="0.00005Jy",  # 0.05 mJy - clean to ~5x RMS to remove sidelobes
        robust=-0.5,  # More uniform weighting for cleaner PSF
        backend="wsclean",
        # Quality control
        min_initial_snr=10.0,  # We expect ~321 from previous run
        max_flagged_fraction=0.5,
        # Data selection
        refant=None,
        uvrange="",
        spw="",
        field="0",  # Only process main calibrator field (24x faster than all fields)
        # Model seeding (Docker hang fixed - NVSS seeding works now)
        use_nvss_seeding=False,  # Disabled for this test, but works if enabled
        nvss_min_mjy=10.0,
        calib_ra_deg=CALIB_RA_DEG,
        calib_dec_deg=CALIB_DEC_DEG,
        calib_flux_jy=CALIB_FLUX_JY,
    )

    logger.info("Configuration:")
    logger.info(f"  Phase solints: {config.phase_solints}")
    logger.info(f"  Amplitude+phase: {config.do_amplitude}")
    logger.info(f"  Min SNR improvement: {config.min_snr_improvement}")
    logger.info(f"  Imaging backend: {config.backend}")
    logger.info(f"  Image size: {config.imsize} x {config.imsize}")
    logger.info(f"  Clean iterations: {config.niter}")
    logger.info(f"  Threshold: {config.threshold}")

    # Run self-calibration
    logger.info("\nStarting self-calibration...")
    success, summary = selfcal_ms(
        ms_path=MS_PATH,
        output_dir=OUTPUT_DIR,
        config=config,
        initial_caltables=INITIAL_CALTABLES,
    )

    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("SELF-CALIBRATION RESULTS")
    logger.info("=" * 80)
    logger.info(f"Status: {summary['status']}")
    logger.info(f"Iterations completed: {summary['iterations_completed']}")

    if summary["status"] == "success":
        logger.info(f"Initial SNR: {summary['initial_snr']:.1f}")
        logger.info(f"Best SNR: {summary['best_snr']:.1f}")
        logger.info(f"SNR improvement: {summary['snr_improvement']:.2f}x")
        logger.info(f"Best iteration: {summary['best_iteration']}")

        logger.info("\nIteration details:")
        for it in summary["iterations"]:
            logger.info(
                f"  Iter {it['iteration']} ({it['calmode']}, {it['solint']}): "
                f"SNR={it['snr']:.1f}, Peak={it['peak_flux_mjy']:.1f} mJy, "
                f"RMS={it['rms_noise_mjy']:.3f} mJy"
            )

        logger.info(f"\nMessage: {summary['message']}")
        logger.info(f"\nOutput files in: {OUTPUT_DIR}")
        logger.info("  - selfcal_iterN_p.gcal: Phase-only calibration tables")
        logger.info("  - selfcal_iterN_ap.gcal: Amplitude+phase calibration table")
        logger.info("  - selfcal_iterN-image.fits: Cleaned images")
        logger.info("  - selfcal_iterN-residual.fits: Residual images")
        logger.info("  - selfcal_summary.json: JSON summary")
    else:
        logger.error(f"Self-calibration failed: {summary.get('message', 'Unknown error')}")

    logger.info("=" * 80)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
