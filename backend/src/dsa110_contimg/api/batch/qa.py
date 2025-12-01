"""
Quality assessment extraction utilities for batch jobs.

This module provides functions for extracting QA metrics from:
- Calibration tables (K, BP, G)
- Image products
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


def extract_calibration_qa(
    ms_path: str,
    job_id: int,
    caltables: Dict[str, str],
) -> Dict[str, Any]:
    """Extract QA metrics from calibration tables.
    
    Analyzes K (delay), BP (bandpass), and G (gain) calibration tables
    to produce quality metrics and an overall quality assessment.
    
    Args:
        ms_path: Path to the measurement set
        job_id: Job ID for tracking
        caltables: Dictionary mapping table type to path (e.g., {"k": "/path/to/k.cal"})
        
    Returns:
        Dictionary containing:
        - ms_path: The measurement set path
        - job_id: The job ID
        - overall_quality: Quality rating (excellent/good/marginal/poor/unknown)
        - flags_total: Average flagging fraction
        - k_metrics: K table metrics (if available)
        - bp_metrics: BP table metrics (if available)
        - g_metrics: G table metrics (if available)
        - per_spw_stats: Per-SPW statistics (if available)
    """
    # Ensure CASAPATH is set before importing CASA modules
    from dsa110_contimg.utils.casa_init import ensure_casa_path
    ensure_casa_path()

    try:
        from casatools import table
        tb = table()

        qa_metrics = {
            "ms_path": ms_path,
            "job_id": job_id,
            "overall_quality": "unknown",
            "flags_total": None,
        }

        # Analyze K table if present
        qa_metrics.update(_extract_k_table_qa(tb, caltables, ms_path))
        
        # Analyze BP table if present
        qa_metrics.update(_extract_bp_table_qa(tb, caltables, ms_path))
        
        # Analyze G table if present
        qa_metrics.update(_extract_g_table_qa(tb, caltables, ms_path))

        # Overall quality assessment
        qa_metrics.update(_calculate_overall_quality(qa_metrics))

        return qa_metrics
    except (RuntimeError, ValueError, KeyError, OSError) as e:
        # RuntimeError: CASA table errors
        # ValueError/KeyError: data processing errors
        # OSError: file access errors
        logger.error(f"Failed to extract calibration QA for {ms_path}: {e}")
        return {"ms_path": ms_path, "job_id": job_id, "overall_quality": "unknown"}


def _extract_k_table_qa(tb, caltables: Dict[str, str], ms_path: str) -> Dict[str, Any]:
    """Extract QA metrics from K (delay) calibration table."""
    result = {}
    
    if "k" not in caltables or not caltables["k"]:
        return result
        
    if not Path(caltables["k"]).exists():
        return result
        
    try:
        tb.open(caltables["k"])
        flags = tb.getcol("FLAG")
        snr = tb.getcol("SNR") if tb.colnames().count("SNR") > 0 else None
        tb.close()

        flag_fraction = flags.sum() / flags.size if flags.size > 0 else 1.0
        avg_snr = snr.mean() if snr is not None else None

        result["k_metrics"] = {
            "flag_fraction": float(flag_fraction),
            "avg_snr": float(avg_snr) if avg_snr is not None else None,
        }
    except (RuntimeError, ValueError, KeyError) as e:
        logger.warning(f"Failed to extract K QA for {ms_path}: {e}")
        
    return result


def _extract_bp_table_qa(tb, caltables: Dict[str, str], ms_path: str) -> Dict[str, Any]:
    """Extract QA metrics from BP (bandpass) calibration table."""
    result = {}
    
    if "bp" not in caltables or not caltables["bp"]:
        return result
        
    if not Path(caltables["bp"]).exists():
        return result
        
    try:
        tb.open(caltables["bp"])
        flags = tb.getcol("FLAG")
        gains = tb.getcol("CPARAM")
        tb.close()

        flag_fraction = flags.sum() / flags.size if flags.size > 0 else 1.0
        amp = abs(gains)
        amp_mean = amp.mean() if amp.size > 0 else None
        amp_std = amp.std() if amp.size > 0 else None

        result["bp_metrics"] = {
            "flag_fraction": float(flag_fraction),
            "amp_mean": float(amp_mean) if amp_mean is not None else None,
            "amp_std": float(amp_std) if amp_std is not None else None,
        }

        # Extract per-SPW statistics
        result.update(_extract_per_spw_stats(caltables["bp"], ms_path))
        
    except (RuntimeError, ValueError, KeyError) as e:
        logger.warning(f"Failed to extract BP QA for {ms_path}: {e}")
        
    return result


def _extract_per_spw_stats(bp_path: str, ms_path: str) -> Dict[str, Any]:
    """Extract per-SPW flagging statistics from BP table."""
    result = {}
    
    try:
        from dsa110_contimg.qa.calibration_quality import analyze_per_spw_flagging
        
        spw_stats = analyze_per_spw_flagging(bp_path)
        result["per_spw_stats"] = [
            {
                "spw_id": s.spw_id,
                "total_solutions": s.total_solutions,
                "flagged_solutions": s.flagged_solutions,
                "fraction_flagged": s.fraction_flagged,
                "n_channels": s.n_channels,
                "channels_with_high_flagging": s.channels_with_high_flagging,
                "avg_flagged_per_channel": s.avg_flagged_per_channel,
                "max_flagged_in_channel": s.max_flagged_in_channel,
                "is_problematic": bool(s.is_problematic),
            }
            for s in spw_stats
        ]
    except (ImportError, RuntimeError, ValueError, KeyError, AttributeError) as e:
        logger.warning(f"Failed to extract per-SPW statistics for {ms_path}: {e}")
        
    return result


def _extract_g_table_qa(tb, caltables: Dict[str, str], ms_path: str) -> Dict[str, Any]:
    """Extract QA metrics from G (gain) calibration table."""
    result = {}
    
    if "g" not in caltables or not caltables["g"]:
        return result
        
    if not Path(caltables["g"]).exists():
        return result
        
    try:
        tb.open(caltables["g"])
        flags = tb.getcol("FLAG")
        gains = tb.getcol("CPARAM")
        tb.close()

        flag_fraction = flags.sum() / flags.size if flags.size > 0 else 1.0
        amp = abs(gains)
        amp_mean = amp.mean() if amp.size > 0 else None

        result["g_metrics"] = {
            "flag_fraction": float(flag_fraction),
            "amp_mean": float(amp_mean) if amp_mean is not None else None,
        }
    except (RuntimeError, ValueError, KeyError) as e:
        logger.warning(f"Failed to extract G QA for {ms_path}: {e}")
        
    return result


def _calculate_overall_quality(qa_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate overall quality assessment from individual metrics."""
    result = {}
    
    total_flags = []
    for key in ["k_metrics", "bp_metrics", "g_metrics"]:
        if key in qa_metrics and qa_metrics[key]:
            total_flags.append(qa_metrics[key].get("flag_fraction", 1.0))

    if total_flags:
        result["flags_total"] = sum(total_flags) / len(total_flags)
        avg_flag = result["flags_total"]

        if avg_flag < 0.1:
            result["overall_quality"] = "excellent"
        elif avg_flag < 0.3:
            result["overall_quality"] = "good"
        elif avg_flag < 0.5:
            result["overall_quality"] = "marginal"
        else:
            result["overall_quality"] = "poor"
            
    return result


def extract_image_qa(
    ms_path: str,
    job_id: int,
    image_path: str,
) -> Dict[str, Any]:
    """Extract QA metrics from an image.
    
    Analyzes a CASA image to extract quality metrics including
    noise levels, peak flux, dynamic range, and beam parameters.
    
    Args:
        ms_path: Path to the source measurement set
        job_id: Job ID for tracking
        image_path: Path to the CASA image
        
    Returns:
        Dictionary containing:
        - ms_path: The measurement set path
        - job_id: The job ID
        - image_path: The image path
        - overall_quality: Quality rating (excellent/good/marginal/poor/unknown)
        - rms_noise: RMS noise level
        - peak_flux: Peak flux density
        - dynamic_range: Peak/RMS ratio
        - beam_major: Major axis of synthesized beam
        - beam_minor: Minor axis of synthesized beam
        - beam_pa: Position angle of synthesized beam
    """
    try:
        from casatools import image
        ia = image()

        qa_metrics = {
            "ms_path": ms_path,
            "job_id": job_id,
            "image_path": image_path,
            "overall_quality": "unknown",
        }

        if not Path(image_path).exists():
            return qa_metrics

        ia.open(image_path)

        # Get image statistics
        stats = ia.statistics()
        qa_metrics["rms_noise"] = float(stats.get("rms", [0])[0])
        qa_metrics["peak_flux"] = float(stats.get("max", [0])[0])

        if qa_metrics["rms_noise"] > 0:
            qa_metrics["dynamic_range"] = qa_metrics["peak_flux"] / qa_metrics["rms_noise"]

        # Get beam info
        qa_metrics.update(_extract_beam_info(ia))

        ia.close()

        # Quality assessment based on dynamic range
        qa_metrics.update(_assess_image_quality(qa_metrics))

        return qa_metrics
    except (RuntimeError, ValueError, KeyError, OSError) as e:
        # RuntimeError: CASA image analysis errors
        # ValueError/KeyError: data processing errors
        # OSError: file access errors
        logger.error(f"Failed to extract image QA for {ms_path}: {e}")
        return {
            "ms_path": ms_path,
            "job_id": job_id,
            "image_path": image_path,
            "overall_quality": "unknown",
        }


def _extract_beam_info(ia) -> Dict[str, Any]:
    """Extract beam parameters from image analysis tool."""
    result = {}
    
    beam = ia.restoringbeam()
    if beam:
        major = beam.get("major", {})
        minor = beam.get("minor", {})
        pa = beam.get("positionangle", {})

        if "value" in major:
            result["beam_major"] = float(major["value"])
        if "value" in minor:
            result["beam_minor"] = float(minor["value"])
        if "value" in pa:
            result["beam_pa"] = float(pa["value"])
            
    return result


def _assess_image_quality(qa_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Assess image quality based on dynamic range."""
    result = {}
    
    if qa_metrics.get("dynamic_range"):
        dr = qa_metrics["dynamic_range"]
        if dr > 1000:
            result["overall_quality"] = "excellent"
        elif dr > 100:
            result["overall_quality"] = "good"
        elif dr > 10:
            result["overall_quality"] = "marginal"
        else:
            result["overall_quality"] = "poor"
            
    return result
