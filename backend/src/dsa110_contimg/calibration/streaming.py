# pylint: disable=no-member  # astropy.units uses dynamic attributes (deg, etc.)
"""Streaming calibration utilities for autonomous pipeline operation.

This module provides functions for calibrator detection and calibration solving
in the streaming converter context, borrowing from batch mode implementations.
"""

from typing import Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


def has_calibrator(ms_path: str, radius_deg: float = 2.0) -> bool:
    """Detect if MS contains a calibrator source using catalog matching.

    Inspects MS content (field coordinates) and matches against VLA calibrator catalog.
    More robust than path-based detection methods.

    Args:
        ms_path: Path to Measurement Set
        radius_deg: Matching radius in degrees (default: 2.0)

    Returns:
        True if MS contains a known calibrator source, False otherwise
    """
    try:
        import astropy.units as u

        from dsa110_contimg.calibration.catalogs import (
            calibrator_match,
            load_vla_catalog,
        )
        from dsa110_contimg.pointing.utils import load_pointing
        from dsa110_contimg.utils.time_utils import extract_ms_time_range

        # Load calibrator catalog
        cal_catalog = load_vla_catalog()
        if cal_catalog.empty:
            logger.warning("Calibrator catalog is empty")
            return False

        # Get pointing information from MS
        pointing_info = load_pointing(ms_path)
        if pointing_info is None or "dec_deg" not in pointing_info:
            logger.debug(f"Could not read pointing from {ms_path}")
            return False

        pt_dec = pointing_info["dec_deg"] * u.deg

        # Get observation time
        start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_path)
        if mid_mjd is None:
            logger.debug(f"Could not extract time from {ms_path}")
            return False

        # Match against catalog using calibrator_match function
        # This function finds calibrators near the meridian at the observation time
        matches = calibrator_match(
            cal_catalog,
            pt_dec,
            mid_mjd,
            radius_deg=radius_deg,
        )

        # Return True if any matches found
        has_match = len(matches) > 0
        if has_match:
            logger.debug(
                f"Found calibrator match in {ms_path}: {matches[0].get('name', 'unknown')}"
            )
        return has_match

    except Exception as e:
        logger.warning(f"Failed to detect calibrator in {ms_path}: {e}", exc_info=True)
        return False


def solve_calibration_for_ms(
    ms_path: str,
    cal_field: Optional[str] = None,
    refant: Optional[str] = None,
    do_k: bool = False,
    catalog_path: Optional[str] = None,
    calibrator_name: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """Solve calibration for a single MS file.

    Orchestrates K, BP, and G calibration solves using existing batch mode functions.
    Auto-detects calibrator field and reference antenna if not provided.

    Args:
        ms_path: Path to Measurement Set
        cal_field: Calibrator field name/index (auto-detected if None)
        refant: Reference antenna ID (auto-detected if None)
        do_k: If True, perform K-calibration (delay). Default False for DSA-110.
        catalog_path: Optional path to calibrator catalog (auto-resolved if None)
        calibrator_name: Expected calibrator name (e.g., "0834+555"). If provided,
            used for model lookup instead of auto-detection.

    Returns:
        Tuple of (success: bool, error_message: Optional[str])
        On success: (True, None)
        On failure: (False, error_message_string)
    """
    try:
        from dsa110_contimg.calibration.cli import run_calibrator
        from dsa110_contimg.calibration.refant_selection import (
            get_default_outrigger_refants,
        )
        from dsa110_contimg.calibration.selection import select_bandpass_from_catalog

        # Auto-detect calibrator field if not provided
        if cal_field is None:
            logger.info(f"Auto-detecting calibrator field for {ms_path}")
            try:
                field_sel_str, _, _, calinfo, _ = select_bandpass_from_catalog(
                    ms_path,
                    catalog_path=catalog_path,
                    search_radius_deg=1.0,
                    window=3,
                )
                if not field_sel_str:
                    error_msg = (
                        f"Could not auto-detect calibrator field in {ms_path}. "
                        "No calibrator found in catalog within search radius."
                    )
                    logger.error(error_msg)
                    return False, error_msg
                cal_field = field_sel_str
                name, ra_deg, dec_deg, flux_jy = calinfo
                logger.info(
                    f"Auto-detected calibrator field '{cal_field}' "
                    f"for calibrator {name} (RA={ra_deg:.4f}, Dec={dec_deg:.4f})"
                )
            except Exception as e:
                error_msg = f"Failed to auto-detect calibrator field: {e}"
                logger.error(error_msg, exc_info=True)
                return False, error_msg

        # Auto-detect reference antenna if not provided
        if refant is None:
            logger.info(f"Auto-detecting reference antenna for {ms_path}")
            try:
                # Use default outrigger chain (CASA will auto-fallback)
                refant = get_default_outrigger_refants()
                logger.info(f"Using default outrigger refant chain: {refant}")
            except Exception as e:
                error_msg = f"Failed to auto-detect reference antenna: {e}"
                logger.error(error_msg, exc_info=True)
                return False, error_msg

        # Issue #8: Pre-calibration RFI flagging
        try:
            from dsa110_contimg.pipeline.hardening import preflag_rfi
            preflag_rfi(ms_path, backend="aoflagger")
            logger.info(f"Pre-calibration RFI flagging complete for {ms_path}")
        except ImportError:
            logger.debug("preflag_rfi not available (hardening module)")
        except Exception as e:
            logger.warning(f"Pre-calibration RFI flagging failed (non-fatal): {e}")

        # Run calibration solves
        logger.info(
            f"Solving calibration for {ms_path} "
            f"(field={cal_field}, refant={refant}, do_k={do_k})"
        )
        caltables = run_calibrator(
            ms_path,
            cal_field,
            refant,
            do_flagging=True,
            do_k=do_k,
        )

        if not caltables:
            error_msg = "Calibration solve completed but no calibration tables were produced"
            logger.error(error_msg)
            return False, error_msg

        # Issue #5: Automated QA assessment of calibration solutions
        qa_warnings = []
        try:
            from dsa110_contimg.pipeline.hardening import (
                assess_calibration_quality,
                CalibrationQAResult,
            )
            
            for caltable in caltables:
                qa_result: CalibrationQAResult = assess_calibration_quality(
                    caltable_path=caltable,
                    snr_min=3.0,  # Default minimum SNR threshold
                    flagged_max=0.5,  # Max 50% flagged
                )
                
                if not qa_result.passed:
                    qa_warnings.append(
                        f"QA failed for {caltable}: {', '.join(qa_result.issues)}"
                    )
                    logger.warning(
                        "Calibration QA failed for %s: %s",
                        caltable, qa_result.issues
                    )
                elif qa_result.warnings:
                    qa_warnings.extend(qa_result.warnings)
                    logger.info(
                        "Calibration QA warnings for %s: %s",
                        caltable, qa_result.warnings
                    )
                else:
                    logger.debug(
                        "Calibration QA passed for %s (SNR=%.1f, flagged=%.1f%%)",
                        caltable, qa_result.snr_median, qa_result.flagged_fraction * 100
                    )
        except ImportError:
            logger.debug("Hardening module not available, skipping QA")
        except Exception as qa_err:
            logger.warning("QA assessment error: %s", qa_err)

        logger.info(
            "Successfully solved calibration for %s: produced %d calibration table(s)%s",
            ms_path, len(caltables),
            f" (QA warnings: {len(qa_warnings)})" if qa_warnings else ""
        )
        return True, None

    except Exception as e:
        error_msg = f"Calibration solve failed for {ms_path}: {e}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg
