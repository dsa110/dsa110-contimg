"""
Integrated quality assurance for DSA-110 pipeline.

Performs comprehensive checks at each pipeline stage and triggers alerts
for quality issues.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dsa110_contimg.utils import alerting
from dsa110_contimg.qa.ms_quality import validate_ms_quality, quick_ms_check
from dsa110_contimg.qa.calibration_quality import (
    validate_caltable_quality,
    check_corrected_data_quality,
)
from dsa110_contimg.qa.image_quality import validate_image_quality, quick_image_check

logger = logging.getLogger(__name__)


class QualityThresholds:
    """Quality thresholds for pipeline products."""
    
    def __init__(self):
        # MS quality thresholds
        self.ms_max_flagged_fraction = float(os.getenv("CONTIMG_QA_MS_MAX_FLAGGED", "0.5"))
        self.ms_max_zeros_fraction = float(os.getenv("CONTIMG_QA_MS_MAX_ZEROS", "0.3"))
        self.ms_min_median_amplitude = float(os.getenv("CONTIMG_QA_MS_MIN_AMP", "1e-6"))
        
        # Calibration quality thresholds
        self.cal_max_flagged_fraction = float(os.getenv("CONTIMG_QA_CAL_MAX_FLAGGED", "0.3"))
        self.cal_min_median_amplitude = float(os.getenv("CONTIMG_QA_CAL_MIN_AMP", "0.1"))
        self.cal_max_median_amplitude = float(os.getenv("CONTIMG_QA_CAL_MAX_AMP", "10.0"))
        self.cal_max_phase_scatter_deg = float(os.getenv("CONTIMG_QA_CAL_MAX_PHASE_SCATTER", "90.0"))
        
        # Image quality thresholds
        self.img_min_dynamic_range = float(os.getenv("CONTIMG_QA_IMG_MIN_DYNAMIC_RANGE", "5.0"))
        self.img_min_peak_snr = float(os.getenv("CONTIMG_QA_IMG_MIN_PEAK_SNR", "5.0"))
        self.img_min_5sigma_pixels = int(os.getenv("CONTIMG_QA_IMG_MIN_5SIGMA_PIXELS", "10"))


def check_ms_after_conversion(
    ms_path: str,
    alert_on_issues: bool = True,
    quick_check_only: bool = False,
) -> Tuple[bool, Optional[Dict]]:
    """
    Check MS quality after conversion.
    
    Args:
        ms_path: Path to MS
        alert_on_issues: Whether to send alerts for quality issues
        quick_check_only: Only perform quick checks
    
    Returns:
        (passed, metrics_dict) tuple
    """
    logger.info(f"Checking MS quality after conversion: {ms_path}")
    
    if quick_check_only:
        passed, message = quick_ms_check(ms_path)
        if not passed:
            logger.error(f"MS failed quick check: {message}")
            if alert_on_issues:
                alerting.error(
                    "ms_conversion",
                    f"MS failed quality check after conversion",
                    context={"ms_path": ms_path, "check": "quick", "reason": message},
                )
        return passed, {"message": message}
    
    try:
        metrics = validate_ms_quality(ms_path, check_data_column="DATA")
        
        # Send alerts for critical issues
        if metrics.has_critical_issues:
            logger.error(f"MS has critical issues: {', '.join(metrics.issues)}")
            if alert_on_issues:
                alerting.critical(
                    "ms_conversion",
                    f"MS has critical quality issues after conversion",
                    context={
                        "ms_path": ms_path,
                        "issues": metrics.issues,
                        "n_antennas": metrics.n_antennas,
                        "n_channels": metrics.n_channels,
                        "fraction_flagged": f"{metrics.fraction_flagged:.1%}",
                    },
                )
            return False, metrics.to_dict()
        
        # Send alerts for warnings
        if metrics.has_warnings:
            logger.warning(f"MS has warnings: {', '.join(metrics.warnings)}")
            if alert_on_issues:
                alerting.warning(
                    "ms_conversion",
                    f"MS has quality warnings after conversion",
                    context={
                        "ms_path": ms_path,
                        "warnings": metrics.warnings,
                        "fraction_flagged": f"{metrics.fraction_flagged:.1%}",
                        "median_amplitude": f"{metrics.median_amplitude:.3e}",
                    },
                )
        
        # Success
        logger.info(f"MS passed quality checks: {os.path.basename(ms_path)}")
        return True, metrics.to_dict()
    
    except Exception as e:
        logger.error(f"Exception during MS quality check: {e}")
        if alert_on_issues:
            alerting.error(
                "ms_conversion",
                f"Exception during MS quality check",
                context={"ms_path": ms_path, "exception": str(e)},
            )
        return False, {"exception": str(e)}


def check_calibration_quality(
    caltables: List[str],
    ms_path: Optional[str] = None,
    alert_on_issues: bool = True,
) -> Tuple[bool, Dict]:
    """
    Check quality of calibration tables and optionally CORRECTED_DATA.
    
    Args:
        caltables: List of calibration table paths
        ms_path: Optional MS path to check CORRECTED_DATA
        alert_on_issues: Whether to send alerts
    
    Returns:
        (passed, results_dict) tuple
    """
    logger.info(f"Checking calibration quality: {len(caltables)} tables")
    
    all_passed = True
    results = {"caltables": {}, "corrected_data": None}
    
    # Check each calibration table
    for caltable in caltables:
        if not os.path.exists(caltable):
            logger.warning(f"Calibration table not found: {caltable}")
            continue
        
        try:
            metrics = validate_caltable_quality(caltable)
            results["caltables"][caltable] = metrics.to_dict()
            
            if metrics.has_issues:
                all_passed = False
                logger.error(f"Calibration table has issues: {caltable}")
                if alert_on_issues:
                    alerting.error(
                        "calibration",
                        f"Calibration table has quality issues",
                        context={
                            "caltable": os.path.basename(caltable),
                            "cal_type": metrics.cal_type,
                            "issues": metrics.issues,
                            "fraction_flagged": f"{metrics.fraction_flagged:.1%}",
                        },
                    )
            
            if metrics.has_warnings and alert_on_issues:
                alerting.warning(
                    "calibration",
                    f"Calibration table has quality warnings",
                    context={
                        "caltable": os.path.basename(caltable),
                        "cal_type": metrics.cal_type,
                        "warnings": metrics.warnings,
                    },
                )
        
        except Exception as e:
            all_passed = False
            logger.error(f"Exception checking calibration table {caltable}: {e}")
            if alert_on_issues:
                alerting.error(
                    "calibration",
                    f"Exception during calibration quality check",
                    context={"caltable": os.path.basename(caltable), "exception": str(e)},
                )
    
    # Check CORRECTED_DATA if MS path provided and calibration has been applied
    # CORRECTED_DATA only exists after calibration is applied, so check if it exists first
    if ms_path and os.path.exists(ms_path):
        try:
            from casacore.tables import table
            with table(ms_path, readonly=True, ack=False) as tb:
                has_corrected_data = "CORRECTED_DATA" in tb.colnames()
            
            if has_corrected_data:
                # Calibration has been applied, check CORRECTED_DATA quality
                passed, metrics_dict, issues = check_corrected_data_quality(ms_path)
                results["corrected_data"] = metrics_dict
                
                if not passed:
                    all_passed = False
                    logger.error(f"CORRECTED_DATA quality check failed: {', '.join(issues)}")
                    if alert_on_issues:
                        alerting.error(
                            "calibration",
                            f"CORRECTED_DATA has quality issues",
                            context={"ms_path": os.path.basename(ms_path), "issues": issues},
                        )
            else:
                # CORRECTED_DATA doesn't exist yet - this is expected if calibration hasn't been applied
                logger.info(f"CORRECTED_DATA column not present - calibration not yet applied (expected)")
                results["corrected_data"] = {"status": "not_applied", "message": "Calibration tables created but not yet applied to MS"}
        
        except Exception as e:
            all_passed = False
            logger.error(f"Exception checking CORRECTED_DATA: {e}")
            if alert_on_issues:
                alerting.error(
                    "calibration",
                    f"Exception checking CORRECTED_DATA",
                    context={"ms_path": os.path.basename(ms_path), "exception": str(e)},
                )
    
    return all_passed, results


def check_image_quality(
    image_path: str,
    alert_on_issues: bool = True,
    quick_check_only: bool = False,
) -> Tuple[bool, Optional[Dict]]:
    """
    Check image quality after imaging.
    
    Args:
        image_path: Path to image
        alert_on_issues: Whether to send alerts
        quick_check_only: Only perform quick checks
    
    Returns:
        (passed, metrics_dict) tuple
    """
    logger.info(f"Checking image quality: {image_path}")
    
    if quick_check_only:
        passed, message = quick_image_check(image_path)
        if not passed:
            logger.error(f"Image failed quick check: {message}")
            if alert_on_issues:
                alerting.error(
                    "imaging",
                    f"Image failed quality check",
                    context={"image_path": image_path, "check": "quick", "reason": message},
                )
        return passed, {"message": message}
    
    try:
        metrics = validate_image_quality(image_path)
        
        # Send alerts for critical issues
        if metrics.has_issues:
            logger.error(f"Image has issues: {', '.join(metrics.issues)}")
            if alert_on_issues:
                alerting.error(
                    "imaging",
                    f"Image has critical quality issues",
                    context={
                        "image_path": image_path,
                        "image_type": metrics.image_type,
                        "issues": metrics.issues,
                    },
                )
            return False, metrics.to_dict()
        
        # Send alerts for warnings
        if metrics.has_warnings:
            logger.warning(f"Image has warnings: {', '.join(metrics.warnings)}")
            if alert_on_issues:
                alerting.warning(
                    "imaging",
                    f"Image has quality warnings",
                    context={
                        "image_path": image_path,
                        "image_type": metrics.image_type,
                        "warnings": metrics.warnings,
                        "peak_snr": f"{metrics.peak_snr:.1f}",
                        "dynamic_range": f"{metrics.dynamic_range:.1f}",
                    },
                )
        
        # Success - send info alert for good images
        if not metrics.has_issues and not metrics.has_warnings and alert_on_issues:
            if metrics.image_type in ["image", "pbcor"] and metrics.peak_snr > 10:
                alerting.info(
                    "imaging",
                    f"High-quality image produced",
                    context={
                        "image_path": os.path.basename(image_path),
                        "peak_snr": f"{metrics.peak_snr:.1f}",
                        "dynamic_range": f"{metrics.dynamic_range:.1f}",
                        "n_5sigma_pixels": metrics.n_pixels_above_5sigma,
                    },
                )
        
        logger.info(f"Image passed quality checks: {os.path.basename(image_path)}")
        return True, metrics.to_dict()
    
    except Exception as e:
        logger.error(f"Exception during image quality check: {e}")
        if alert_on_issues:
            alerting.error(
                "imaging",
                f"Exception during image quality check",
                context={"image_path": image_path, "exception": str(e)},
            )
        return False, {"exception": str(e)}

