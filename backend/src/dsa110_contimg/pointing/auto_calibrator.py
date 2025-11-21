"""Automatic calibrator registration and transit pre-calculation on declination change.

This module implements the algorithm:
1. Monitor /data/incoming/ for new HDF5 files
2. When Dec change is detected:
   - Check if BP calibrator is registered
   - If yes: calculate transit times for time range spanned by data on disk
   - If no: find and register brightest VLA calibrator or NVSS source within tolerance
   - Calculate transit times for registered calibrator
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
from astropy import units as u
from astropy.time import Time

from dsa110_contimg.calibration.catalogs import load_vla_catalog
from dsa110_contimg.catalog.query import query_sources
from dsa110_contimg.conversion.transit_precalc import (
    precalculate_transits_for_calibrator,
)
from dsa110_contimg.database.products import get_products_db_connection
from dsa110_contimg.mosaic.streaming_mosaic import StreamingMosaicManager
from dsa110_contimg.pointing.utils import load_pointing

logger = logging.getLogger(__name__)

# Declination tolerance for calibrator matching
DEC_TOLERANCE_DEG = 2.5


def get_data_time_range(products_db_path: Path) -> Optional[Tuple[Time, Time]]:
    """Get the time range spanned by HDF5 files currently on disk.

    Uses query_subband_groups to find all complete groups with files on disk,
    then determines the time range from the earliest to latest group.

    Args:
        products_db_path: Path to products database

    Returns:
        Tuple of (start_time, end_time) in Time objects, or None if no data
    """
    try:
        from dsa110_contimg.database.hdf5_index import query_subband_groups

        # Query for a very wide time range to get all data
        # Use a time range that covers all possible observations
        now = Time.now()
        start_time_str = (now - 365 * u.day).strftime("%Y-%m-%d %H:%M:%S")
        end_time_str = (now + 1 * u.day).strftime("%Y-%m-%d %H:%M:%S")

        # Determine HDF5 database path
        import os as _os_inner

        hdf5_db_path = Path(_os_inner.getenv("HDF5_DB_PATH", "state/hdf5.sqlite3"))

        # Query for all groups with files on disk
        groups = query_subband_groups(
            hdf5_db_path,
            start_time=start_time_str,
            end_time=end_time_str,
            only_stored=True,  # Only files on disk
        )

        if not groups:
            logger.debug("No groups with files on disk found")
            return None

        # Extract times from file paths
        # File paths typically contain timestamps in the filename
        # Format: YYYYMMDD_HHMMSS or similar
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            _peek_uvh5_phase_and_midtime,
        )

        times = []
        for group in groups:
            if group:  # Non-empty group
                try:
                    # Get midtime from first file in group
                    _, _, midtime = _peek_uvh5_phase_and_midtime(group[0])
                    if midtime is not None:
                        times.append(midtime)
                except Exception:
                    continue

        if not times:
            logger.warning("Could not extract times from file groups")
            return None

        start_time = Time(min(times))
        end_time = Time(max(times))

        logger.debug(
            f"Data time range: {start_time.iso} to {end_time.iso} "
            f"({len(groups)} groups, {len(times)} times)"
        )

        return start_time, end_time

    except Exception as e:
        logger.warning(f"Could not determine data time range: {e}", exc_info=True)
        return None


def check_bp_calibrator_registered(
    products_db: sqlite3.Connection,
    dec_deg: float,
    dec_tolerance_deg: float = DEC_TOLERANCE_DEG,
) -> Optional[Tuple[str, float, float]]:
    """Check if a BP calibrator is registered for the given declination.

    Args:
        products_db: Products database connection
        dec_deg: Declination in degrees
        dec_tolerance_deg: Tolerance in degrees

    Returns:
        Tuple of (calibrator_name, ra_deg, dec_deg) if found, None otherwise
    """
    # Query for active calibrators within declination range
    from dsa110_contimg.database.calibrators import get_bandpass_calibrators

    calibrators = get_bandpass_calibrators(dec_deg=dec_deg, status="active")

    if not calibrators:
        return None

    # Filter by tolerance and return first match
    for cal in calibrators:
        dec_range_min = cal.get("dec_range_min")
        dec_range_max = cal.get("dec_range_max")

        if dec_range_min is not None and dec_range_max is not None:
            if (
                dec_range_min <= dec_deg + dec_tolerance_deg
                and dec_range_max >= dec_deg - dec_tolerance_deg
            ):
                return (
                    cal["calibrator_name"],
                    cal["ra_deg"],
                    cal["dec_deg"],
                )

    return None


def find_brightest_vla_calibrator(
    dec_deg: float, dec_tolerance_deg: float = DEC_TOLERANCE_DEG
) -> Optional[Tuple[str, float, float, float]]:
    """Find the brightest VLA calibrator within declination tolerance.

    Args:
        dec_deg: Target declination in degrees
        dec_tolerance_deg: Tolerance in degrees

    Returns:
        Tuple of (calibrator_name, ra_deg, dec_deg, flux_jy) if found, None otherwise
    """
    try:
        vla_df = load_vla_catalog()

        if vla_df.empty:
            logger.warning("VLA catalog is empty")
            return None

        # Filter by declination tolerance
        dec_min = dec_deg - dec_tolerance_deg
        dec_max = dec_deg + dec_tolerance_deg

        # Ensure we have required columns
        if "dec_deg" not in vla_df.columns:
            logger.error("VLA catalog missing 'dec_deg' column")
            return None

        filtered = vla_df[(vla_df["dec_deg"] >= dec_min) & (vla_df["dec_deg"] <= dec_max)]

        if filtered.empty:
            logger.info(
                f"No VLA calibrators found within ±{dec_tolerance_deg}° of Dec={dec_deg:.2f}°"
            )
            return None

        # Find brightest (highest flux)
        # VLA catalog may have flux columns like 'flux_20cm_jy', 's_20cm', etc.
        flux_col = None
        for col in ["flux_20cm_jy", "s_20cm", "flux_jy", "flux"]:
            if col in filtered.columns:
                flux_col = col
                break

        if flux_col is None:
            # If no flux column, just pick first one
            logger.warning("No flux column found in VLA catalog, using first match")
            row = filtered.iloc[0]
            return (
                str(row.get("name", row.index[0])),
                float(row["ra_deg"]),
                float(row["dec_deg"]),
                0.0,  # Unknown flux
            )

        # Sort by flux descending and pick brightest
        filtered = filtered.sort_values(flux_col, ascending=False, na_last=True)
        row = filtered.iloc[0]

        calibrator_name = str(row.get("name", row.index[0]))
        ra_deg = float(row["ra_deg"])
        dec_deg_cal = float(row["dec_deg"])
        flux_jy = float(row[flux_col]) if pd.notna(row[flux_col]) else 0.0

        logger.info(
            f"Found brightest VLA calibrator: {calibrator_name} "
            f"at RA={ra_deg:.6f}°, Dec={dec_deg_cal:.6f}°, Flux={flux_jy:.2f} Jy"
        )

        return (calibrator_name, ra_deg, dec_deg_cal, flux_jy)

    except Exception as e:
        logger.error(f"Error finding VLA calibrator: {e}", exc_info=True)
        return None


def find_brightest_nvss_source(
    dec_deg: float, dec_tolerance_deg: float = DEC_TOLERANCE_DEG
) -> Optional[Tuple[str, float, float, float]]:
    """Find the brightest NVSS source within declination tolerance.

    Args:
        dec_deg: Target declination in degrees
        dec_tolerance_deg: Tolerance in degrees

    Returns:
        Tuple of (source_name, ra_deg, dec_deg, flux_mjy) if found, None otherwise
    """
    try:
        # Check for missing FIRST and RACS databases when NVSS is used
        # Auto-build if missing (helps during pipeline debugging)
        from dsa110_contimg.catalog.builders import check_missing_catalog_databases

        check_missing_catalog_databases(
            dec_deg,
            logger_instance=logger,
            auto_build=True,  # Auto-build missing databases
        )

        # Query NVSS sources within tolerance
        # Use a small radius initially, then filter by declination
        radius_deg = dec_tolerance_deg * 2  # Search in a larger radius
        nvss_df = query_sources(
            catalog_type=catalog,
            ra_deg=0.0,  # Will filter by dec anyway
            dec_deg=dec_deg,
            radius_deg=radius_deg,
            min_flux_mjy=None,  # No minimum flux
            max_sources=1000,  # Get many candidates
        )

        if nvss_df.empty:
            logger.info(f"No NVSS sources found within ±{dec_tolerance_deg}° of Dec={dec_deg:.2f}°")
            return None

        # Filter by declination tolerance
        dec_min = dec_deg - dec_tolerance_deg
        dec_max = dec_deg + dec_tolerance_deg

        if "dec_deg" not in nvss_df.columns:
            logger.error("NVSS catalog missing 'dec_deg' column")
            return None

        filtered = nvss_df[(nvss_df["dec_deg"] >= dec_min) & (nvss_df["dec_deg"] <= dec_max)]

        if filtered.empty:
            logger.info("No NVSS sources within declination tolerance")
            return None

        # Find brightest (highest flux)
        # NVSS flux is typically in mJy
        flux_col = None
        for col in ["flux_mjy", "s_mjy", "flux", "peak_flux"]:
            if col in filtered.columns:
                flux_col = col
                break

        if flux_col is None:
            logger.warning("No flux column found in NVSS catalog, using first match")
            row = filtered.iloc[0]
            source_name = f"NVSS J{row.get('ra_deg', 0):.2f}+{row.get('dec_deg', 0):.2f}"
            return (
                source_name,
                float(row["ra_deg"]),
                float(row["dec_deg"]),
                0.0,  # Unknown flux
            )

        # Sort by flux descending and pick brightest
        filtered = filtered.sort_values(flux_col, ascending=False, na_last=True)
        row = filtered.iloc[0]

        # Generate source name
        ra_deg = float(row["ra_deg"])
        dec_deg_src = float(row["dec_deg"])
        flux_mjy = float(row[flux_col]) if pd.notna(row[flux_col]) else 0.0

        # Format as NVSS JHHMM+DDMM
        ra_h = int(ra_deg / 15.0)
        ra_m = int((ra_deg / 15.0 - ra_h) * 60)
        dec_d = int(abs(dec_deg_src))
        dec_m = int((abs(dec_deg_src) - dec_d) * 60)
        sign = "+" if dec_deg_src >= 0 else "-"
        source_name = f"NVSS J{ra_h:02d}{ra_m:02d}{sign}{dec_d:02d}{dec_m:02d}"

        logger.info(
            f"Found brightest NVSS source: {source_name} "
            f"at RA={ra_deg:.6f}°, Dec={dec_deg_src:.6f}°, Flux={flux_mjy:.2f} mJy"
        )

        return (source_name, ra_deg, dec_deg_src, flux_mjy)

    except Exception as e:
        logger.error(f"Error finding NVSS source: {e}", exc_info=True)
        return None


def register_and_precalculate_transits(
    products_db: sqlite3.Connection,
    calibrator_name: str,
    ra_deg: float,
    dec_deg: float,
    products_db_path: Path,
    dec_tolerance: float = 5.0,
) -> bool:
    """Register a BP calibrator and pre-calculate transit times.

    Args:
        products_db: Products database connection
        calibrator_name: Name of calibrator
        ra_deg: RA in degrees
        dec_deg: Dec in degrees
        ingest_db_path: Path to ingest database (for time range)
        dec_tolerance: Declination tolerance for registration

    Returns:
        True if successful, False otherwise
    """
    try:
        # Register the calibrator
        manager = StreamingMosaicManager(products_db=products_db)
        manager.register_bandpass_calibrator(
            calibrator_name=calibrator_name,
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            dec_tolerance=dec_tolerance,
            registered_by="auto_calibrator",
            notes="Auto-registered on declination change",
        )

        logger.info(
            f"Registered BP calibrator {calibrator_name} " f"(RA={ra_deg:.6f}°, Dec={dec_deg:.6f}°)"
        )

        # Get time range of data on disk
        time_range = get_data_time_range(products_db_path)

        if time_range:
            start_time, end_time = time_range
            days_back = int((Time.now() - start_time).to(u.day).value) + 1
            int((end_time - Time.now()).to(u.day).value) + 1
            max_days_back = max(days_back, 60)  # At least 60 days

            logger.info(
                f"Data on disk spans {start_time.iso} to {end_time.iso} "
                f"(calculating transits for {max_days_back} days back)"
            )
        else:
            max_days_back = 60
            logger.warning("Could not determine data time range, using default 60 days")

        # Pre-calculate transit times
        transits_with_data = precalculate_transits_for_calibrator(
            products_db=products_db,
            calibrator_name=calibrator_name,
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            max_days_back=max_days_back,
            dec_tolerance_deg=DEC_TOLERANCE_DEG,
        )

        logger.info(
            f"Pre-calculated {transits_with_data} transit(s) with available data "
            f"for {calibrator_name}"
        )

        return True

    except Exception as e:
        logger.error(f"Failed to register and pre-calculate transits: {e}", exc_info=True)
        return False


def handle_declination_change(
    new_dec_deg: float,
    products_db_path: Path,
    dec_change_threshold: float = 0.1,
) -> bool:
    """Handle declination change: check for BP calibrator and register if needed.

    This is the main algorithm entry point.

    Args:
        new_dec_deg: New declination in degrees
        products_db_path: Path to products database
        dec_change_threshold: Minimum declination change to trigger (degrees)

    Returns:
        True if calibrator was found/registered, False otherwise
    """
    try:
        products_db = get_products_db_connection(products_db_path)

        # Check if BP calibrator is already registered
        registered = check_bp_calibrator_registered(products_db, new_dec_deg, DEC_TOLERANCE_DEG)

        if registered:
            calibrator_name, ra_deg, dec_deg = registered
            logger.info(
                f"BP calibrator {calibrator_name} already registered " f"for Dec={new_dec_deg:.2f}°"
            )

            # Calculate transit times for time range spanned by data on disk
            time_range = get_data_time_range(products_db_path)

            if time_range:
                start_time, end_time = time_range
                days_back = int((Time.now() - start_time).to(u.day).value) + 1
                max_days_back = max(days_back, 60)

                logger.info(
                    f"Pre-calculating transit times for existing calibrator "
                    f"{calibrator_name} (data spans {start_time.iso} to {end_time.iso})"
                )

                transits_with_data = precalculate_transits_for_calibrator(
                    products_db=products_db,
                    calibrator_name=calibrator_name,
                    ra_deg=ra_deg,
                    dec_deg=dec_deg,
                    max_days_back=max_days_back,
                    dec_tolerance_deg=DEC_TOLERANCE_DEG,
                )

                logger.info(f"Pre-calculated {transits_with_data} transit(s) with available data")

            products_db.close()
            return True

        # No BP calibrator registered - find and register one
        logger.info(
            f"No BP calibrator registered for Dec={new_dec_deg:.2f}°, "
            f"searching for calibrator..."
        )

        # Try VLA calibrator first
        vla_result = find_brightest_vla_calibrator(new_dec_deg, DEC_TOLERANCE_DEG)

        if vla_result:
            calibrator_name, ra_deg, dec_deg, flux = vla_result
            success = register_and_precalculate_transits(
                products_db=products_db,
                calibrator_name=calibrator_name,
                ra_deg=ra_deg,
                dec_deg=dec_deg,
                products_db_path=products_db_path,
            )
            products_db.close()
            return success

        # No VLA calibrator found - try NVSS source
        logger.info("No VLA calibrator found, searching NVSS catalog...")
        nvss_result = find_brightest_nvss_source(new_dec_deg, DEC_TOLERANCE_DEG)

        if nvss_result:
            source_name, ra_deg, dec_deg, flux_mjy = nvss_result
            # Use source name as calibrator name
            success = register_and_precalculate_transits(
                products_db=products_db,
                calibrator_name=source_name,
                ra_deg=ra_deg,
                dec_deg=dec_deg,
                products_db_path=products_db_path,
            )
            products_db.close()
            return success

        # No calibrator found at all
        logger.warning(
            f"No calibrator found within ±{DEC_TOLERANCE_DEG}° of Dec={new_dec_deg:.2f}°"
        )
        products_db.close()
        return False

    except Exception as e:
        logger.error(f"Error handling declination change: {e}", exc_info=True)
        return False


def on_new_hdf5_file(
    file_path: Path,
    products_db_path: Path,
    dec_change_threshold: float = 0.1,
) -> None:
    """Callback when a new HDF5 file is detected.

    This function should be called from the watchdog service when a new HDF5 file
    is registered in /data/incoming/.

    Args:
        file_path: Path to the new HDF5 file
        products_db_path: Path to products database
        dec_change_threshold: Minimum declination change to trigger (degrees)
    """
    try:
        # Extract pointing from file
        pointing_info = load_pointing(file_path)

        if not pointing_info or "dec_deg" not in pointing_info:
            logger.debug(f"Could not extract pointing from {file_path}")
            return

        new_dec_deg = pointing_info["dec_deg"]

        # Check for declination change
        products_db = get_products_db_connection(products_db_path)
        cursor = products_db.cursor()

        cursor.execute(
            """
            SELECT dec_deg FROM pointing_history
            ORDER BY timestamp DESC LIMIT 1
            """
        )

        result = cursor.fetchone()
        products_db.close()

        previous_dec_deg = None
        dec_change = None

        if result:
            previous_dec_deg = result[0]
            dec_change = abs(new_dec_deg - previous_dec_deg)

            if dec_change < dec_change_threshold:
                logger.debug(
                    f"Declination change {dec_change:.6f}° below threshold "
                    f"{dec_change_threshold:.6f}°, skipping"
                )
                return

        # Declination change detected - handle it
        if previous_dec_deg is not None:
            logger.info(
                f"Declination change detected: {previous_dec_deg:.6f}° → {new_dec_deg:.6f}° "
                f"(Δ = {dec_change:.6f}°)"
            )
        else:
            logger.info(
                f"No previous declination found, processing new pointing: Dec={new_dec_deg:.6f}°"
            )

        handle_declination_change(
            new_dec_deg=new_dec_deg,
            products_db_path=products_db_path,
            dec_change_threshold=dec_change_threshold,
        )

    except Exception as e:
        logger.error(f"Error processing new HDF5 file {file_path}: {e}", exc_info=True)
