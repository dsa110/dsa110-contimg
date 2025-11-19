"""
Unified Catalog Query Interface

Provides a single interface to query multiple source catalogs
(VLA, NVSS, FIRST, RACS) and find suitable calibrators.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord

logger = logging.getLogger(__name__)


def query_unified_catalog(
    ra_deg: float,
    dec_deg: float,
    radius_deg: float,
    catalogs: Optional[List[str]] = None,
    min_flux_jy: Optional[float] = None,
    max_sources: Optional[int] = None,
) -> List[Dict]:
    """Query multiple catalogs and return unified results.

    Args:
        ra_deg: Right ascension in degrees
        dec_deg: Declination in degrees
        radius_deg: Search radius in degrees
        catalogs: List of catalogs to query (default: ['nvss', 'vla'])
                  Options: 'nvss', 'vla', 'first', 'racs'
        min_flux_jy: Minimum flux in Jansky
        max_sources: Maximum number of sources to return

    Returns:
        List of source dictionaries with unified schema
    """
    if catalogs is None:
        catalogs = ["nvss", "vla"]

    all_sources = []

    # Query NVSS
    if "nvss" in catalogs:
        try:
            from dsa110_contimg.catalog.query import query_sources

            nvss_results = query_sources(
                catalog_type=catalog,
                ra_deg,
                dec_deg,
                radius_deg,
                min_flux_mjy=min_flux_jy * 1000 if min_flux_jy else None,
            )
            if nvss_results is not None and len(nvss_results) > 0:
                for _, row in nvss_results.iterrows():
                    all_sources.append(
                        {
                            "source_name": f"NVSS_{row['ra_deg']:.6f}_{row['dec_deg']:.6f}",
                            "ra_deg": row["ra_deg"],
                            "dec_deg": row["dec_deg"],
                            "flux_jy": row["flux_mjy"] / 1000.0,
                            "catalog": "NVSS",
                            "catalog_id": None,
                        }
                    )
        except Exception as e:
            logger.warning(f"Failed to query NVSS catalog: {e}")

    # Query VLA calibrators
    if "vla" in catalogs:
        try:
            from dsa110_contimg.database.calibrators import get_bandpass_calibrators

            vla_calibrators = get_bandpass_calibrators(status="active")
            center_coord = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")

            for cal in vla_calibrators:
                cal_coord = SkyCoord(
                    ra=cal["ra_deg"] * u.deg, dec=cal["dec_deg"] * u.deg, frame="icrs"
                )
                separation = center_coord.separation(cal_coord).deg

                if separation <= radius_deg:
                    if min_flux_jy is None or cal.get("flux_jy", 0) >= min_flux_jy:
                        all_sources.append(
                            {
                                "source_name": cal["calibrator_name"],
                                "ra_deg": cal["ra_deg"],
                                "dec_deg": cal["dec_deg"],
                                "flux_jy": cal.get("flux_jy"),
                                "catalog": "VLA",
                                "catalog_id": cal["calibrator_name"],
                            }
                        )
        except Exception as e:
            logger.warning(f"Failed to query VLA catalog: {e}")

    # Query FIRST (if available)
    if "first" in catalogs:
        try:
            # TODO: Implement FIRST catalog query when available
            logger.debug("FIRST catalog query not yet implemented")
        except Exception as e:
            logger.warning(f"Failed to query FIRST catalog: {e}")

    # Query RACS (if available)
    if "racs" in catalogs:
        try:
            # TODO: Implement RACS catalog query when available
            logger.debug("RACS catalog query not yet implemented")
        except Exception as e:
            logger.warning(f"Failed to query RACS catalog: {e}")

    # Sort by flux (brightest first)
    all_sources.sort(key=lambda x: x.get("flux_jy", 0) or 0, reverse=True)

    # Limit results
    if max_sources:
        all_sources = all_sources[:max_sources]

    return all_sources


def find_calibrators_for_field(
    ra_deg: float,
    dec_deg: float,
    radius_deg: float = 0.1,
    min_flux_jy: float = 1.0,
    prefer_bandpass: bool = True,
) -> Tuple[Optional[Dict], List[Dict]]:
    """Find suitable calibrators for a field.

    Args:
        ra_deg: Field center RA in degrees
        dec_deg: Field center Dec in degrees
        radius_deg: Search radius in degrees (default: 0.1)
        min_flux_jy: Minimum flux in Jansky (default: 1.0)
        prefer_bandpass: If True, prefer known bandpass calibrators

    Returns:
        Tuple of (bandpass_calibrator, gain_calibrators)
        - bandpass_calibrator: Best BP calibrator or None
        - gain_calibrators: List of suitable gain calibrators
    """
    # Find bandpass calibrator
    bandpass_cal = None
    if prefer_bandpass:
        try:
            from dsa110_contimg.database.calibrators import get_bandpass_calibrators

            bp_calibrators = get_bandpass_calibrators(dec_deg=dec_deg, status="active")
            if bp_calibrators:
                # Use first active calibrator for this declination
                bp_calibrators.sort(key=lambda x: x.get("registered_at", 0), reverse=True)
                bp = bp_calibrators[0]
                bandpass_cal = {
                    "name": bp["calibrator_name"],
                    "ra_deg": bp["ra_deg"],
                    "dec_deg": bp["dec_deg"],
                    "flux_jy": bp.get("flux_jy"),
                    "catalog": "VLA",
                }
        except Exception as e:
            logger.warning(f"Failed to find bandpass calibrator: {e}")

    # Find gain calibrators (bright sources in field)
    gain_calibrators = query_unified_catalog(
        ra_deg=ra_deg,
        dec_deg=dec_deg,
        radius_deg=radius_deg,
        catalogs=["nvss", "vla"],
        min_flux_jy=min_flux_jy,
        max_sources=10,
    )

    # Filter out bandpass calibrator if it's in the list
    if bandpass_cal:
        gain_calibrators = [g for g in gain_calibrators if g["source_name"] != bandpass_cal["name"]]

    return bandpass_cal, gain_calibrators


def get_source_info(source_name: str, catalog: Optional[str] = None) -> Optional[Dict]:
    """Get detailed information about a source.

    Args:
        source_name: Name of the source
        catalog: Catalog to search (None = search all)

    Returns:
        Source dictionary with detailed info, or None if not found
    """
    # Try VLA calibrators first
    if catalog is None or catalog.lower() == "vla":
        try:
            from dsa110_contimg.database.calibrators import get_bandpass_calibrators

            calibrators = get_bandpass_calibrators()
            for cal in calibrators:
                if cal["calibrator_name"] == source_name:
                    return {
                        "source_name": cal["calibrator_name"],
                        "ra_deg": cal["ra_deg"],
                        "dec_deg": cal["dec_deg"],
                        "flux_jy": cal.get("flux_jy"),
                        "catalog": "VLA",
                        "dec_range_min": cal.get("dec_range_min"),
                        "dec_range_max": cal.get("dec_range_max"),
                        "status": cal.get("status"),
                        "notes": cal.get("notes"),
                    }
        except Exception as e:
            logger.warning(f"Failed to query VLA catalog: {e}")

    # TODO: Add queries for other catalogs when available
    return None


def cone_search(
    ra_deg: float,
    dec_deg: float,
    radius_deg: float,
    catalogs: Optional[List[str]] = None,
) -> List[Dict]:
    """Perform a cone search across multiple catalogs.

    Args:
        ra_deg: Center RA in degrees
        dec_deg: Center Dec in degrees
        radius_deg: Search radius in degrees
        catalogs: List of catalogs to search (default: all available)

    Returns:
        List of sources within the cone
    """
    return query_unified_catalog(
        ra_deg=ra_deg,
        dec_deg=dec_deg,
        radius_deg=radius_deg,
        catalogs=catalogs,
    )
