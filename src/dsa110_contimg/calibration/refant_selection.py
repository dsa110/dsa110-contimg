"""Reference antenna selection utilities for DSA-110 calibration.

This module provides functions for selecting optimal reference antennas,
with emphasis on using outrigger antennas (103-117) for long-baseline
calibration quality.

Key Concepts:
    - DSA-110 has 117 antennas: core (1-102) and outriggers (103-117)
    - Outrigger antennas provide crucial long baselines for calibration
    - Reference antenna selection should prioritize healthy outriggers
    - CASA automatically falls back through refant chain if first fails

Usage:
    from dsa110_contimg.calibration.refant_selection import (
        get_default_outrigger_refants,
        recommend_refants_from_ms
    )

    # Get default outrigger chain (no data inspection)
    refant_string = get_default_outrigger_refants()

    # Or get optimized chain based on MS antenna health
    refant_string = recommend_refants_from_ms(ms_path, caltable_path)
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# DSA-110 outrigger antenna IDs (from DSA110_Station_Coordinates.csv)
# These antennas are widely separated from the core array and provide
# critical long baselines needed for high-quality calibration
OUTRIGGER_ANTENNAS = list(range(103, 118))  # 103-117 (15 antennas)

# Default priority order for outrigger reference antennas
# Prioritized by geometric position for optimal baseline coverage:
#   - Eastern outriggers (104-108): Best overall baseline coverage
#   - Northern outriggers (109-113): Good azimuthal distribution
#   - Western/peripheral (114-117, 103): Extreme baselines
DEFAULT_OUTRIGGER_PRIORITY = [
    104,
    105,
    106,
    107,
    108,  # Eastern (best coverage)
    109,
    110,
    111,
    112,
    113,  # Northern (good azimuth)
    114,
    115,
    116,
    103,
    117,  # Western/peripheral (extreme)
]


def get_default_outrigger_refants() -> str:
    """Get default outrigger reference antenna chain as CASA-format string.

    This provides the baseline fallback chain without any data inspection.
    CASA will automatically try antennas in order until it finds a healthy one.

    Returns:
        Comma-separated string of antenna IDs for CASA refant parameter.
        Example: '104,105,106,107,108,109,110,111,112,113,114,115,116,103,117'

    Example:
        >>> from casatasks import bandpass
        >>> refant = get_default_outrigger_refants()
        >>> bandpass(vis='obs.ms', refant=refant, ...)
    """
    return ",".join(map(str, DEFAULT_OUTRIGGER_PRIORITY))


def get_outrigger_antenna_ids() -> List[int]:
    """Get list of DSA-110 outrigger antenna IDs.

    Returns:
        List of outrigger antenna IDs (103-117)
    """
    return OUTRIGGER_ANTENNAS.copy()


def analyze_antenna_health_from_caltable(caltable_path: str) -> List[Dict[str, Any]]:
    """Analyze antenna health from calibration table flagging statistics.

    Args:
        caltable_path: Path to CASA calibration table

    Returns:
        List of antenna statistics dictionaries with keys:
            - antenna_id: Antenna number
            - flagged_fraction: Fraction of solutions flagged (0.0-1.0)
            - total_solutions: Total number of solutions
            - flagged_solutions: Number of flagged solutions

    Raises:
        ImportError: If casacore not available
        FileNotFoundError: If calibration table doesn't exist
    """
    try:
        from casacore.tables import table
    except ImportError as e:
        raise ImportError(
            "casacore.tables not available - cannot analyze antenna health"
        ) from e

    caltable = Path(caltable_path)
    if not caltable.exists():
        raise FileNotFoundError(f"Calibration table does not exist: {caltable_path}")

    import numpy as np

    antenna_stats = []

    with table(str(caltable), readonly=True) as tb:
        antenna_ids = tb.getcol("ANTENNA1")
        flags = tb.getcol("FLAG")

        unique_ants = np.unique(antenna_ids)

        for ant_id in unique_ants:
            ant_mask = antenna_ids == ant_id
            ant_flags = flags[ant_mask]

            total_solutions = ant_flags.size
            flagged_solutions = np.sum(ant_flags)
            if total_solutions > 0:
                flagged_fraction = flagged_solutions / total_solutions
            else:
                flagged_fraction = 1.0

            antenna_stats.append(
                {
                    "antenna_id": int(ant_id),
                    "flagged_fraction": float(flagged_fraction),
                    "total_solutions": int(total_solutions),
                    "flagged_solutions": int(flagged_solutions),
                }
            )

    return antenna_stats


def recommend_outrigger_refants(
    antenna_analysis: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Recommend outrigger reference antennas for DSA-110 calibration.

    Provides intelligent refant selection prioritizing healthy outrigger
    antennas. If no antenna statistics are provided, returns default priority.

    Args:
        antenna_analysis: Optional list of antenna statistics from
            analyze_antenna_health_from_caltable() or similar.
            Each dict should have 'antenna_id' and 'flagged_fraction' keys.

    Returns:
        Dictionary with refant recommendations:
            - outrigger_antennas: List of all outrigger antenna IDs
            - default_refant_list: Default priority order (list of ints)
            - default_refant_string: Default chain (CASA format string)
            - recommended_refant: Best single antenna (if stats provided)
            - recommended_refant_string: Optimized chain (if stats provided)
            - healthy_outriggers: List of healthy outriggers (if stats provided)
            - problematic_outriggers: List of bad outriggers (if stats provided)
            - note: Human-readable explanation

    Example:
        >>> # Without antenna statistics (use defaults)
        >>> recs = recommend_outrigger_refants()
        >>> print(recs['default_refant_string'])
        '104,105,106,107,108,109,110,111,112,113,114,115,116,103,117'

        >>> # With antenna health analysis
        >>> from dsa110_contimg.calibration.refant_selection import (
        ...     analyze_antenna_health_from_caltable,
        ...     recommend_outrigger_refants
        ... )
        >>> stats = analyze_antenna_health_from_caltable('cal.bcal')
        >>> recs = recommend_outrigger_refants(stats)
        >>> print(recs['recommended_refant_string'])
        '105,104,106,107,108'  # Optimized based on antenna health
    """
    recommendations = {
        "outrigger_antennas": OUTRIGGER_ANTENNAS.copy(),
        "default_refant_list": DEFAULT_OUTRIGGER_PRIORITY.copy(),
        "default_refant_string": get_default_outrigger_refants(),
    }

    # If no antenna statistics provided, return defaults
    if not antenna_analysis:
        recommendations["recommended_refant"] = DEFAULT_OUTRIGGER_PRIORITY[0]
        recommendations["recommended_refant_string"] = recommendations[
            "default_refant_string"
        ]
        recommendations["note"] = (
            "No antenna statistics available - using default priority order"
        )
        return recommendations

    # Extract outrigger antenna stats
    outrigger_stats = [
        ant for ant in antenna_analysis if ant["antenna_id"] in OUTRIGGER_ANTENNAS
    ]

    if not outrigger_stats:
        logger.warning("No outrigger antennas found in antenna statistics")
        recommendations["recommended_refant"] = DEFAULT_OUTRIGGER_PRIORITY[0]
        recommendations["recommended_refant_string"] = recommendations[
            "default_refant_string"
        ]
        recommendations["note"] = "No outrigger stats found - using default priority"
        return recommendations

    # Sort by flagged fraction (lower is better)
    healthy_outriggers = sorted(outrigger_stats, key=lambda x: x["flagged_fraction"])

    # Filter to reasonably healthy antennas (<50% flagged)
    good_outriggers = [
        ant for ant in healthy_outriggers if ant["flagged_fraction"] < 0.5
    ]

    if good_outriggers:
        # Determine health status
        def get_health_status(frac):
            if frac < 0.1:
                return "excellent"
            elif frac < 0.3:
                return "good"
            else:
                return "fair"

        recommendations["healthy_outriggers"] = [
            {
                "antenna_id": ant["antenna_id"],
                "flagged_fraction": ant["flagged_fraction"],
                "health_status": get_health_status(ant["flagged_fraction"]),
            }
            for ant in good_outriggers
        ]

        # Build optimized refant string from healthy antennas
        top_5 = [str(ant["antenna_id"]) for ant in good_outriggers[:5]]
        top_ant = good_outriggers[0]
        recommendations["recommended_refant"] = top_ant["antenna_id"]
        recommendations["recommended_refant_string"] = ",".join(top_5)

        note = (
            f"Top choice: antenna {top_ant['antenna_id']} "
            f"({top_ant['flagged_fraction']*100:.1f}% flagged)"
        )
        recommendations["note"] = note
    else:
        recommendations["warning"] = (
            "No healthy outrigger antennas found (<50% flagged)"
        )
        recommendations["recommended_refant"] = DEFAULT_OUTRIGGER_PRIORITY[0]
        recommendations["recommended_refant_string"] = recommendations[
            "default_refant_string"
        ]
        recommendations["note"] = "Using default priority - check array status"

    # Identify problematic outriggers (>80% flagged)
    bad_outriggers = [ant for ant in outrigger_stats if ant["flagged_fraction"] > 0.8]

    if bad_outriggers:
        recommendations["problematic_outriggers"] = [
            {
                "antenna_id": ant["antenna_id"],
                "flagged_fraction": ant["flagged_fraction"],
            }
            for ant in bad_outriggers
        ]

    return recommendations


def recommend_refants_from_ms(
    ms_path: str,
    caltable_path: Optional[str] = None,
    use_defaults_on_error: bool = True,
) -> str:
    """Get recommended refant string for calibration based on MS/caltable.

    This is the high-level convenience function for CLI/orchestrator usage.
    It attempts to analyze antenna health and provide optimized refant chain,
    falling back to defaults if analysis fails.

    Args:
        ms_path: Path to Measurement Set (currently unused, reserved for
            future MS-based health checks)
        caltable_path: Optional path to calibration table for health analysis.
            If not provided, returns default outrigger chain.
        use_defaults_on_error: If True, return default chain on analysis errors.
            If False, raise exceptions.

    Returns:
        CASA-format refant string (comma-separated antenna IDs)

    Raises:
        Exception: If analysis fails and use_defaults_on_error=False

    Example:
        >>> # Use defaults (no caltable inspection)
        >>> refant = recommend_refants_from_ms('obs.ms')
        >>> print(refant)
        '104,105,106,107,108,109,110,111,112,113,114,115,116,103,117'

        >>> # Optimize based on previous calibration
        >>> refant = recommend_refants_from_ms('obs.ms', 'prev.bcal')
        >>> print(refant)
        '105,104,106,107,108'  # Best 5 based on health
    """
    # If no caltable provided, return defaults
    if not caltable_path:
        logger.info("No calibration table provided - using default outrigger chain")
        return get_default_outrigger_refants()

    try:
        # Analyze antenna health from caltable
        antenna_stats = analyze_antenna_health_from_caltable(caltable_path)

        # Get recommendations
        recs = recommend_outrigger_refants(antenna_stats)

        # Use recommended chain if available, otherwise default
        refant_string = recs.get(
            "recommended_refant_string", recs["default_refant_string"]
        )

        logger.info(
            f"Recommended refant chain: {refant_string} "
            f"({recs.get('note', 'optimized from antenna health')})"
        )

        return refant_string

    except Exception as e:
        if use_defaults_on_error:
            logger.warning(
                f"Failed to analyze antenna health: {e}. "
                f"Using default outrigger chain."
            )
            return get_default_outrigger_refants()
        else:
            raise


def format_refant_for_casa(antenna_ids: List[int]) -> str:
    """Format list of antenna IDs as CASA refant parameter string.

    Args:
        antenna_ids: List of antenna IDs (integers)

    Returns:
        Comma-separated string for CASA refant parameter

    Example:
        >>> format_refant_for_casa([104, 105, 106])
        '104,105,106'
    """
    return ",".join(map(str, antenna_ids))


# Convenience function for backward compatibility with debug script
def get_outrigger_refant_recommendations(
    antenna_analysis: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Alias for recommend_outrigger_refants() for backward compatibility.

    This function exists to maintain compatibility with existing code
    (e.g., debug_0834_calibration.py) that may import this name.
    """
    return recommend_outrigger_refants(antenna_analysis)
