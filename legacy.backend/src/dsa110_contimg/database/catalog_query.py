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
                ra_center=ra_deg,
                dec_center=dec_deg,
                radius_deg=radius_deg,
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
            # FIRST catalog database query
            # FIRST covers declination > -40° with 1.4 GHz observations
            if dec_deg < -40.0:
                logger.debug(f"FIRST catalog does not cover Dec={dec_deg:.2f}° (min: -40°)")
            else:
                try:
                    from dsa110_contimg.catalog.catalog_crossmatch_astropy import query_sources

                    df = query_sources(
                        catalog_type="first",
                        ra_center=ra_deg,
                        dec_center=dec_deg,
                        radius_deg=radius_deg,
                        min_flux_mjy=(
                            min_flux_mjy * 1000 if min_flux_mjy else None
                        ),  # Convert Jy to mJy
                    )
                    if not df.empty:
                        for _, row in df.iterrows():
                            all_sources.append(
                                {
                                    "ra_deg": float(row.get("ra", row.get("ra_deg", 0))),
                                    "dec_deg": float(row.get("dec", row.get("dec_deg", 0))),
                                    "flux_jy": float(
                                        row.get("flux_jy", row.get("flux_mjy", 0) / 1000)
                                    ),
                                    "catalog": "FIRST",
                                    "catalog_id": row.get(
                                        "source_name", f"FIRST_J{ra_deg:.4f}{dec_deg:+.4f}"
                                    ),
                                }
                            )
                except ImportError:
                    logger.debug("FIRST catalog query requires catalog_crossmatch_astropy module")
        except Exception as e:
            logger.warning(f"Failed to query FIRST catalog: {e}")

    # Query RACS (if available)
    if "racs" in catalogs:
        try:
            # RACS (Rapid ASKAP Continuum Survey) catalog database query
            # RACS covers declination < +41° with 887.5 MHz observations
            if dec_deg > 41.0:
                logger.debug(f"RACS catalog does not cover Dec={dec_deg:.2f}° (max: +41°)")
            else:
                try:
                    from dsa110_contimg.catalog.catalog_crossmatch_astropy import query_sources

                    df = query_sources(
                        catalog_type="racs",
                        ra_center=ra_deg,
                        dec_center=dec_deg,
                        radius_deg=radius_deg,
                        min_flux_mjy=(
                            min_flux_mjy * 1000 if min_flux_mjy else None
                        ),  # Convert Jy to mJy
                    )
                    if not df.empty:
                        for _, row in df.iterrows():
                            all_sources.append(
                                {
                                    "ra_deg": float(row.get("ra", row.get("ra_deg", 0))),
                                    "dec_deg": float(row.get("dec", row.get("dec_deg", 0))),
                                    "flux_jy": float(
                                        row.get("flux_jy", row.get("flux_mjy", 0) / 1000)
                                    ),
                                    "catalog": "RACS",
                                    "catalog_id": row.get(
                                        "source_name", f"RACS_J{ra_deg:.4f}{dec_deg:+.4f}"
                                    ),
                                }
                            )
                except ImportError:
                    logger.debug("RACS catalog query requires catalog_crossmatch_astropy module")
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

    def _parse_coords_from_name(prefix: str) -> Optional[Tuple[float, float]]:
        """Extract RA/Dec in degrees from a catalog-style source name."""
        name_upper = source_name.upper()
        if not name_upper.startswith(prefix.upper()):
            return None

        # Strip prefix and common separators
        remainder = source_name[len(prefix) :].lstrip("_")
        if remainder.startswith("J"):
            remainder = remainder[1:]

        # Try underscore-separated decimal degrees (e.g., NVSS_202.7_30.5)
        if "_" in remainder:
            parts = remainder.split("_")
            if len(parts) >= 2:
                try:
                    ra_val = float(parts[0])
                    dec_val = float(parts[1])
                    return ra_val, dec_val
                except ValueError:
                    pass

        # Try compact sexagesimal (e.g., 123456+123456)
        sep_idx = None
        for sign in ["+", "-"]:
            idx = remainder.find(sign, 1)
            if idx != -1:
                sep_idx = idx
                break

        if sep_idx is None:
            return None

        ra_str = remainder[:sep_idx]
        dec_str = remainder[sep_idx + 1 :]
        sign = -1 if remainder[sep_idx] == "-" else 1

        try:
            ra_hours = int(ra_str[0:2])
            ra_minutes = int(ra_str[2:4])
            ra_seconds = float(ra_str[4:])
            dec_degrees = int(dec_str[0:2])
            dec_minutes = int(dec_str[2:4])
            dec_seconds = float(dec_str[4:])
        except ValueError:
            return None

        ra_deg = 15.0 * (ra_hours + ra_minutes / 60.0 + ra_seconds / 3600.0)
        dec_deg = sign * (dec_degrees + dec_minutes / 60.0 + dec_seconds / 3600.0)
        return ra_deg, dec_deg

    def _query_catalog_by_coords(
        cat_key: str, coords: Optional[Tuple[float, float]]
    ) -> Optional[Dict]:
        """Query a catalog near the provided coordinates and normalize output."""
        if coords is None:
            return None

        try:
            from dsa110_contimg.catalog.query import query_sources

            ra_deg, dec_deg = coords
            df = query_sources(
                catalog_type=cat_key,
                ra_center=ra_deg,
                dec_center=dec_deg,
                radius_deg=0.05,
                max_sources=1,
            )
            if df is None or getattr(df, "empty", False):
                return None

            row = df.iloc[0]
            flux_mjy = row.get("flux_mjy")
            flux_jy = row.get("flux_jy")
            if flux_jy is None and flux_mjy is not None:
                flux_jy = float(flux_mjy) / 1000.0

            return {
                "source_name": source_name,
                "ra_deg": float(row.get("ra_deg", ra_deg)),
                "dec_deg": float(row.get("dec_deg", dec_deg)),
                "flux_jy": flux_jy,
                "catalog": cat_key.upper(),
                "catalog_id": row.get("source_name"),
            }
        except Exception as e:
            logger.warning(f"Failed to query {cat_key.upper()} catalog: {e}")
            return None

    catalogs_to_search = [catalog.lower()] if catalog else ["vla", "nvss", "first", "racs"]

    # Try VLA calibrators first
    if "vla" in catalogs_to_search:
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

    # Try NVSS/FIRST/RACS catalogs using coordinate parsing
    if "nvss" in catalogs_to_search:
        coords = _parse_coords_from_name("NVSS")
        result = _query_catalog_by_coords("nvss", coords)
        if result:
            return result

    if "first" in catalogs_to_search:
        coords = _parse_coords_from_name("FIRST")
        result = _query_catalog_by_coords("first", coords)
        if result:
            return result

    if "racs" in catalogs_to_search:
        coords = _parse_coords_from_name("RACS")
        result = _query_catalog_by_coords("racs", coords)
        if result:
            return result

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
