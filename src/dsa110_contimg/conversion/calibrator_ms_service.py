"""
Calibrator MS generation service.

This service provides an elegant, reusable interface for generating Measurement Sets
from calibrator transits. It handles transit finding, group discovery, conversion,
database registration, and progress reporting.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
import astropy.units as u
from astropy.time import Time

from dsa110_contimg.calibration.catalogs import read_vla_parsed_catalog_csv
from dsa110_contimg.calibration.schedule import previous_transits
from dsa110_contimg.conversion.config import CalibratorMSConfig
from dsa110_contimg.conversion.exceptions import (
    CalibratorNotFoundError,
    ConversionError,
    GroupNotFoundError,
    TransitNotFoundError,
    ValidationError,
)
from dsa110_contimg.conversion.ms_utils import configure_ms_for_imaging
from dsa110_contimg.conversion.progress import ProgressReporter
from dsa110_contimg.conversion.strategies.direct_subband import write_ms_from_subbands
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import find_subband_groups
from dsa110_contimg.database.products import ensure_products_db, ms_index_upsert

logger = logging.getLogger(__name__)


@dataclass
class CalibratorMSResult:
    """Result of calibrator MS generation."""

    success: bool
    ms_path: Optional[Path]
    transit_info: Optional[dict]
    group_id: Optional[str]
    already_exists: bool
    error: Optional[str] = None
    metrics: Optional[dict] = None
    progress_summary: Optional[dict] = None


class CalibratorMSGenerator:
    """Service for generating MS files from calibrator transits."""

    def __init__(
        self,
        *,
        input_dir: Path,
        output_dir: Path,
        products_db: Path,
        catalogs: List[Path],
        scratch_dir: Optional[Path] = None,
        verbose: bool = True,
    ):
        """Initialize generator with configuration.

        Args:
            input_dir: Directory containing UVH5 files
            output_dir: Directory for output MS files
            products_db: Path to products database
            catalogs: List of calibrator catalog paths
            scratch_dir: Optional scratch directory for staging
            verbose: Whether to print progress messages
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.products_db = Path(products_db)
        self.catalogs = [Path(c) for c in catalogs]
        self.scratch_dir = Path(scratch_dir) if scratch_dir else None
        self.verbose = verbose

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_config(
        cls, config: CalibratorMSConfig, verbose: bool = True
    ) -> CalibratorMSGenerator:
        """Create generator from configuration."""
        return cls(
            input_dir=config.input_dir,
            output_dir=config.output_dir,
            products_db=config.products_db,
            catalogs=config.catalogs,
            scratch_dir=config.scratch_dir,
            verbose=verbose,
        )

    def _validate_inputs(
        self,
        calibrator_name: str,
        transit_time: Optional[Time],
        window_minutes: int,
        max_days_back: int,
    ) -> None:
        """Validate input parameters.

        Raises:
            ValidationError: If any input is invalid
        """
        if not calibrator_name or not calibrator_name.strip():
            raise ValidationError("Calibrator name cannot be empty")

        if window_minutes <= 0:
            raise ValidationError(
                f"window_minutes must be positive, got {window_minutes}"
            )

        if max_days_back <= 0:
            raise ValidationError(
                f"max_days_back must be positive, got {max_days_back}"
            )

        if transit_time is not None and transit_time > Time.now():
            raise ValidationError(
                f"transit_time cannot be in the future: {transit_time}"
            )

        if not self.input_dir.exists():
            raise ValidationError(f"Input directory does not exist: {self.input_dir}")

        if not self.input_dir.is_dir():
            raise ValidationError(
                f"Input directory is not a directory: {self.input_dir}"
            )

    def _load_radec(self, name: str) -> Tuple[float, float]:
        """Load RA/Dec for calibrator from catalogs.

        Always prefers SQLite database over CSV files. Iterates through catalogs
        in order until the calibrator is found.
        """
        import numpy as np
        from dsa110_contimg.calibration.catalogs import (
            load_vla_catalog_from_sqlite,
            read_vla_parsed_catalog_csv,
        )

        for catalog_path in self.catalogs:
            if not catalog_path.exists():
                continue
            try:
                # Handle SQLite database (preferred)
                if str(catalog_path).endswith(".sqlite3"):
                    df = load_vla_catalog_from_sqlite(str(catalog_path))
                else:
                    # Handle CSV file
                    df = read_vla_parsed_catalog_csv(catalog_path)

                if name in df.index:
                    row = df.loc[name]
                    # Handle both Series and DataFrame cases
                    if isinstance(row, pd.DataFrame):
                        row = row.iloc[0]
                    try:
                        ra = float(row["ra_deg"])
                        dec = float(row["dec_deg"])
                    except (TypeError, KeyError):
                        # Try attribute access for Series
                        ra = float(row.ra_deg)
                        dec = float(row.dec_deg)
                    if np.isfinite(ra) and np.isfinite(dec):
                        return ra, dec
            except Exception as e:
                logger.debug(f"Failed to read catalog {catalog_path}: {e}")
                continue

        raise CalibratorNotFoundError(
            f"Calibrator {name} not found in catalogs: {self.catalogs}"
        )

    def find_transit(
        self,
        calibrator_name: str,
        *,
        transit_time: Optional[Time] = None,
        window_minutes: int = 60,
        max_days_back: int = 14,
        min_pb_response: float = 0.3,
        freq_ghz: float = 1.4,
    ) -> Optional[dict]:
        """Find transit for calibrator.

        **IRON-CLAD SAFEGUARD**: Validates BOTH transit time AND pointing declination.
        Only returns transit info if calibrator is actually in the primary beam.

        Args:
            calibrator_name: Name of calibrator (e.g., "0834+555")
            transit_time: Optional specific transit time to use
            window_minutes: Search window around transit
            max_days_back: Maximum days to search back
            min_pb_response: Minimum primary beam response (0-1) required [default: 0.3]
            freq_ghz: Frequency in GHz for PB calculation [default: 1.4]

        Returns:
            Transit info dict or None if not found (or calibrator not in beam)
        """
        ra_deg, dec_deg = self._load_radec(calibrator_name)

        if transit_time is None:
            transits = previous_transits(ra_deg, start_time=Time.now(), n=max_days_back)
        else:
            transits = [transit_time]

        for t in transits:
            half = window_minutes // 2
            t0 = (t - half * u.min).to_datetime().strftime("%Y-%m-%d %H:%M:%S")
            t1 = (t + half * u.min).to_datetime().strftime("%Y-%m-%d %H:%M:%S")

            # Use 1-second tolerance to match pipeline standard (filename precision is to the second)
            # This matches the streaming converter's timestamp string grouping (same second = same group)
            groups = find_subband_groups(
                os.fspath(self.input_dir),
                t0,
                t1,
                tolerance_s=1.0,  # 1-second tolerance matches filename precision (YYYY-MM-DDTHH:MM:SS)
            )

            if not groups:
                # No groups found - find_subband_groups already logged this
                continue

            # Count total files found (not groups) for clearer logging
            total_files = sum(len(g) for g in groups)
            logger.info(
                f"Found {len(groups)} complete 16-subband group(s) ({total_files} total files) "
                f"for transit {t.isot}"
            )
            # Format search window more clearly to show it's a time range, not date range
            t0_date = t0.split()[0]  # Extract date part
            t0_time = t0.split()[1] if len(t0.split()) > 1 else ""
            t1_time = t1.split()[1] if len(t1.split()) > 1 else ""

            if t0.split()[0] == t1.split()[0]:
                # Same day - show time range more clearly
                logger.info(
                    f"Search window: {t0_date} {t0_time} to {t1_time} "
                    f"(±{window_minutes//2} minutes around transit at {t.to_datetime().strftime('%H:%M:%S')}). "
                    f"Selecting group closest to transit time..."
                )
            else:
                # Different days - show full date/time
                logger.info(
                    f"Search window: {t0} to {t1} (±{window_minutes//2} minutes around transit). "
                    f"Selecting group closest to transit time..."
                )

            # Prefer groups whose mid-time is closest to transit
            candidates = []
            for g in groups:
                # Extract timestamp from first file
                base = os.path.basename(g[0])
                ts_str = base.split("_sb")[0]
                try:
                    mid = Time(ts_str)
                    dt_min = abs((mid - t).to(u.min)).value
                    candidates.append((dt_min, g, mid))
                except Exception:
                    continue

            # Sort by time proximity
            candidates.sort(key=lambda x: x[0])
            if candidates:
                dt_min, gbest, mid = candidates[0]

                # Check for complete 16-subband group
                # Use _extract_subband_code to match the grouping algorithm's logic
                from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
                    _extract_subband_code,
                )

                sb_codes = sorted(
                    _extract_subband_code(os.path.basename(p)) for p in gbest
                )

                # CRITICAL: DSA-110 subbands use DESCENDING frequency order (sb00=highest, sb15=lowest).
                # For proper frequency ordering (ascending, low to high), REVERSE the sort.
                # This ensures files are in correct order even if they have different timestamps
                def sort_by_subband(fpath):
                    sb_code = _extract_subband_code(os.path.basename(fpath))
                    if sb_code:
                        sb_num = int(sb_code.replace("sb", ""))
                        return sb_num
                    return 999  # Put files without subband code at end

                gbest_sorted = sorted(gbest, key=sort_by_subband, reverse=True)
                full = len(gbest) == 16 and all(
                    code and code.startswith("sb") for code in sb_codes
                )

                if full:
                    # IRON-CLAD SAFEGUARD: Verify calibrator is in primary beam
                    # Extract ACTUAL pointing RA and Dec from first file (not assumed)
                    from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
                        _peek_uvh5_phase_and_midtime,
                    )
                    from dsa110_contimg.calibration.catalogs import (
                        airy_primary_beam_response,
                    )
                    import numpy as np

                    pt_ra_rad, pt_dec_rad, _ = _peek_uvh5_phase_and_midtime(gbest[0])
                    pt_ra_deg = float(pt_ra_rad.to_value(u.deg))
                    pt_dec_deg = float(pt_dec_rad.to_value(u.deg))

                    # Calculate primary beam response using ACTUAL pointing coordinates
                    # This fixes the bug where we assumed pointing RA = calibrator RA at transit
                    cal_ra_rad = np.deg2rad(ra_deg)
                    cal_dec_rad = np.deg2rad(dec_deg)
                    pt_ra_rad_val = float(pt_ra_rad.to_value(u.rad))
                    pt_dec_rad_val = float(pt_dec_rad.to_value(u.rad))

                    pb_response = airy_primary_beam_response(
                        pt_ra_rad_val, pt_dec_rad_val, cal_ra_rad, cal_dec_rad, freq_ghz
                    )

                    # Calculate angular separation
                    from astropy.coordinates import SkyCoord

                    pt_coord = SkyCoord(
                        ra=pt_ra_rad_val * u.rad, dec=pt_dec_rad_val * u.rad
                    )
                    cal_coord = SkyCoord(ra=cal_ra_rad * u.rad, dec=cal_dec_rad * u.rad)
                    sep = pt_coord.separation(cal_coord)
                    sep_deg = float(sep.to_value(u.deg))

                    if pb_response < min_pb_response:
                        logger.warning(
                            f"REJECTING transit {t.isot}: Calibrator {calibrator_name} "
                            f"is NOT in primary beam\n"
                            f"  Calibrator: RA={ra_deg:.4f}°, Dec={dec_deg:.4f}°\n"
                            f"  Pointing: RA={pt_ra_deg:.4f}°, Dec={pt_dec_deg:.4f}°\n"
                            f"  Separation: {sep_deg:.4f}° ({sep_deg*60:.1f} arcmin)\n"
                            f"  Primary beam response: {pb_response:.4f} (minimum required: {min_pb_response:.2f})\n"
                            f"  This group will be skipped - calibrator is outside usable beam."
                        )
                        continue

                    # Success! Calibrator is in beam
                    logger.info(
                        f"✓ Found complete 16-subband group for transit {t.isot}: "
                        f"{os.path.basename(gbest[0]).split('_sb')[0]} "
                        f"({dt_min:.1f} min from transit)"
                    )
                    logger.info(
                        f"✓ Pointing validation PASSED: Calibrator in primary beam\n"
                        f"  Pointing: RA={pt_ra_deg:.4f}°, Dec={pt_dec_deg:.4f}°\n"
                        f"  Calibrator: RA={ra_deg:.4f}°, Dec={dec_deg:.4f}°\n"
                        f"  Separation: {sep_deg:.4f}° ({sep_deg*60:.1f} arcmin)\n"
                        f"  Primary beam response: {pb_response:.4f}"
                    )
                    return {
                        "name": calibrator_name,
                        "transit_iso": t.isot,
                        "start_iso": t0,
                        "end_iso": t1,
                        "group_id": os.path.basename(gbest[0]).split("_sb")[0],
                        "mid_iso": mid.isot,
                        "delta_minutes": dt_min,
                        "files": gbest_sorted,
                        "pointing_dec_deg": pt_dec_deg,
                        "calibrator_dec_deg": dec_deg,
                        "separation_deg": sep_deg,
                        "pb_response": pb_response,
                    }
                else:
                    # Groups found but incomplete - log this as a skip reason
                    logger.info(
                        f"Skipping transit {t.isot}: found group with {len(gbest)} subbands "
                        f"(need 16 complete), best candidate: {os.path.basename(gbest[0])}"
                    )

        return None

    def _derive_output_path(
        self,
        calibrator_name: str,
        transit_info: dict,
        *,
        auto_naming: bool = True,
        output_name: Optional[str] = None,
    ) -> Path:
        """Derive output MS path intelligently."""
        if output_name:
            return self.output_dir / output_name

        if auto_naming:
            # Use calibrator name + transit time
            cal_safe = calibrator_name.replace("+", "_").replace("-", "_")
            transit_iso = (
                transit_info["transit_iso"].replace(":", "-").replace("T", "_")
            )
            return self.output_dir / f"{cal_safe}_{transit_iso}.ms"

        # Fallback: use group ID
        return self.output_dir / f"{transit_info['group_id']}.ms"

    def _check_existing_ms(
        self, ms_path: Path, transit_info: dict
    ) -> Tuple[bool, Optional[dict]]:
        """Check if MS already exists (filesystem or database)."""
        # Check filesystem
        if ms_path.exists():
            return True, {"reason": "filesystem", "path": os.fspath(ms_path)}

        # Check database
        conn = ensure_products_db(self.products_db)
        row = conn.execute(
            "SELECT path, status, stage FROM ms_index WHERE path = ?",
            (os.fspath(ms_path),),
        ).fetchone()
        conn.close()

        if row:
            return True, {"reason": "database", "status": row[1], "stage": row[2]}

        return False, None

    def has_ms_for_transit(
        self,
        calibrator_name: str,
        transit_time: Optional[Time] = None,
        *,
        tolerance_minutes: float = 5.0,
        max_days_back: int = 14,
    ) -> bool:
        """Check if MS already exists for this transit.

        If transit_time is not provided, finds the latest transit automatically.

        Args:
            calibrator_name: Name of calibrator
            transit_time: Optional transit time to check (if None, finds latest transit)
            tolerance_minutes: Time tolerance in minutes
            max_days_back: Maximum days to search back (only used if transit_time is None)

        Returns:
            True if MS exists, False otherwise
        """
        if transit_time is None:
            # Find latest transit automatically
            transit_info = self.find_transit(
                calibrator_name,
                transit_time=None,
                window_minutes=int(tolerance_minutes * 2),
                max_days_back=max_days_back,
            )
            if not transit_info:
                return False
            transit_time = Time(transit_info["transit_iso"])

        existing = self.find_existing_ms_for_transit(
            calibrator_name, transit_time, tolerance_minutes=tolerance_minutes
        )
        return existing is not None

    def find_existing_ms_for_transit(
        self,
        calibrator_name: str,
        transit_time: Optional[Time] = None,
        *,
        tolerance_minutes: float = 5.0,
        max_days_back: int = 14,
    ) -> Optional[dict]:
        """Find existing MS for calibrator transit in database.

        If transit_time is not provided, finds the latest transit automatically.

        Queries products DB for MS files matching:
        - Transit time within tolerance
        - Calibrator name (from MS path)

        Args:
            calibrator_name: Name of calibrator (e.g., "0834+555")
            transit_time: Optional transit time to search for (if None, finds latest transit)
            tolerance_minutes: Time tolerance in minutes (default: 5.0)
            max_days_back: Maximum days to search back (only used if transit_time is None)

        Returns:
            Dict with ms_path, status, stage, mid_mjd, or None if not found
        """
        if transit_time is None:
            # Find latest transit automatically
            transit_info = self.find_transit(
                calibrator_name,
                transit_time=None,
                window_minutes=int(tolerance_minutes * 2),
                max_days_back=max_days_back,
            )
            if not transit_info:
                return None
            transit_time = Time(transit_info["transit_iso"])

        conn = ensure_products_db(self.products_db)

        transit_mjd = transit_time.mjd
        tol_mjd = tolerance_minutes / (24 * 60)

        # Query by time range (sorted by proximity to transit)
        rows = conn.execute(
            """
            SELECT path, status, stage, mid_mjd, processed_at
            FROM ms_index
            WHERE mid_mjd BETWEEN ? AND ?
            ORDER BY ABS(mid_mjd - ?) ASC
            LIMIT 20
            """,
            (transit_mjd - tol_mjd, transit_mjd + tol_mjd, transit_mjd),
        ).fetchall()

        conn.close()

        if not rows:
            return None

        # Filter by calibrator name in path
        cal_patterns = [
            calibrator_name.replace("+", "_").replace("-", "_"),
            calibrator_name.replace("+", "_"),
            calibrator_name.replace("-", "_"),
            calibrator_name,
        ]

        for row in rows:
            path, status, stage, mid_mjd, processed_at = row
            path_str = Path(path).stem.lower()

            # Check if any calibrator pattern matches
            for pattern in cal_patterns:
                if pattern.lower() in path_str:
                    return {
                        "ms_path": Path(path),
                        "status": status,
                        "stage": stage,
                        "mid_mjd": mid_mjd,
                        "processed_at": processed_at,
                    }

        return None

    def list_ms_for_calibrator(
        self, calibrator_name: str, *, limit: int = 10
    ) -> List[dict]:
        """List all MS files for a calibrator in the database.

        Args:
            calibrator_name: Name of calibrator (e.g., "0834+555")
            limit: Maximum number of results to return

        Returns:
            List of dicts with ms_path, status, stage, mid_mjd, processed_at
        """
        conn = ensure_products_db(self.products_db)

        # Search for calibrator name in path (try multiple patterns)
        cal_patterns = [
            f"%{calibrator_name.replace('+', '_').replace('-', '_')}%",
            f"%{calibrator_name.replace('+', '_')}%",
            f"%{calibrator_name.replace('-', '_')}%",
            f"%{calibrator_name}%",
        ]

        # Build query with OR conditions
        conditions = " OR ".join(["path LIKE ?"] * len(cal_patterns))
        query = f"""
            SELECT path, status, stage, mid_mjd, processed_at
            FROM ms_index
            WHERE {conditions}
            ORDER BY processed_at DESC
            LIMIT ?
        """

        rows = conn.execute(query, tuple(cal_patterns) + (limit,)).fetchall()
        conn.close()

        return [
            {
                "ms_path": Path(row[0]),
                "status": row[1],
                "stage": row[2],
                "mid_mjd": row[3],
                "processed_at": row[4],
            }
            for row in rows
        ]

    def list_available_transits(
        self, calibrator_name: str, *, max_days_back: int = 30, window_minutes: int = 60
    ) -> List[dict]:
        """List all available transits for a calibrator that have data in input directory.

        This method scans the input directory for actual data files first, then checks
        if transits fall within each group's observation window (typically 5 minutes).

        Args:
            calibrator_name: Name of calibrator (e.g., "0834+555")
            max_days_back: Maximum days to search back
            window_minutes: Not used for matching, but kept for API compatibility

        Returns:
            List of transit info dicts with available data, sorted by most recent first.
            Each dict includes:
            - 'transit_iso': Transit time (ISO format)
            - 'transit_mjd': Transit time (MJD)
            - 'group_id': Group timestamp (YYYY-MM-DDTHH:MM:SS)
            - 'group_mid_iso': Group mid-time (ISO format)
            - 'delta_minutes': Time difference between group mid and transit
            - 'subband_count': Number of subbands (should be 16)
            - 'files': List of 16 HDF5 file paths (complete subband group)
            - 'days_ago': Days since transit
            - 'has_ms': Boolean indicating if MS already exists
        """
        import numpy as np
        from collections import defaultdict
        from dsa110_contimg.calibration.schedule import cal_in_datetime

        # Load RA/Dec for calibrator
        ra_deg, dec_deg = self._load_radec(calibrator_name)

        # First, scan directory for all complete groups
        groups_dict = defaultdict(dict)
        for root, dirs, files in os.walk(os.fspath(self.input_dir)):
            for fn in files:
                if not fn.endswith(".hdf5") or "_sb" not in fn:
                    continue
                full_path = os.path.join(root, fn)
                # Extract group ID (timestamp part before _sb)
                base = os.path.basename(fn)
                if "_sb" not in base:
                    continue
                group_id = base.split("_sb")[0]
                # Extract subband code
                sb_part = base.rsplit("_sb", 1)[1].split(".")[0]
                if sb_part.startswith("sb"):
                    sb_code = sb_part
                else:
                    sb_code = f"sb{sb_part.zfill(2)}"

                groups_dict[group_id][sb_code] = full_path

        # Filter to complete 16-subband groups
        complete_groups = {}
        expected_sb = [f"sb{idx:02d}" for idx in range(16)]
        for group_id, sb_map in groups_dict.items():
            if set(sb_map.keys()) == set(expected_sb):
                # Sort by subband code
                complete_groups[group_id] = [sb_map[sb] for sb in sorted(expected_sb)]

        if not complete_groups:
            logger.debug(f"No complete 16-subband groups found in {self.input_dir}")
            return []

        # Find transits first, then check if groups contain them
        transits = previous_transits(ra_deg, start_time=Time.now(), n=max_days_back)
        available_transits = []
        filelength = 5 * u.min  # Typical observation file length

        # Calculate cutoff time for filtering old groups
        cutoff_time = Time.now() - max_days_back * u.day

        for transit in transits:
            # Search for groups in a window around the transit
            half_window = window_minutes // 2
            t0 = (
                (transit - half_window * u.min)
                .to_datetime()
                .strftime("%Y-%m-%d %H:%M:%S")
            )
            t1 = (
                (transit + half_window * u.min)
                .to_datetime()
                .strftime("%Y-%m-%d %H:%M:%S")
            )

            # Find groups in this window
            # Use 1-second tolerance to match pipeline standard (filename precision is to the second)
            groups = find_subband_groups(
                os.fspath(self.input_dir),
                t0,
                t1,
                tolerance_s=1.0,  # 1-second tolerance matches filename precision (YYYY-MM-DDTHH:MM:SS)
            )
            if not groups:
                continue

            # Check each group to see if transit falls within its observation window
            for group_files in groups:
                base = os.path.basename(group_files[0])
                group_id = base.split("_sb")[0]

                try:
                    # Parse timestamp from group ID (this is the start time)
                    group_start = Time(group_id)

                    # Skip if too old
                    if group_start < cutoff_time:
                        continue

                    # Get actual mid-time and declination from file
                    try:
                        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
                            _peek_uvh5_phase_and_midtime,
                        )

                        _, pt_dec_rad, mid_mjd = _peek_uvh5_phase_and_midtime(
                            group_files[0]
                        )
                        # Check if mid_mjd is valid (not None and not 0.0)
                        if mid_mjd is not None and mid_mjd > 0:
                            pt_dec_deg = (
                                pt_dec_rad.to(u.deg).value
                                if pt_dec_rad is not None
                                else None
                            )
                            group_mid = Time(mid_mjd, format="mjd")
                        else:
                            # Invalid mid_mjd, fallback to group_start
                            group_mid = group_start
                            pt_dec_deg = (
                                pt_dec_rad.to(u.deg).value
                                if pt_dec_rad is not None
                                else None
                            )
                    except Exception:
                        # Fallback: use group_start as mid-time, skip dec check
                        group_mid = group_start
                        pt_dec_deg = None

                    # Check if this transit falls within group's observation window
                    transit_in_window = cal_in_datetime(
                        group_id,
                        transit,
                        duration=0 * u.min,  # Transit must be within file
                        filelength=filelength,
                    )

                    if not transit_in_window:
                        continue

                    # Check declination match (only if transit time matches)
                    # Transit time matching is the primary indicator; declination is secondary
                    if pt_dec_deg is not None:
                        dec_match = abs(pt_dec_deg - dec_deg) <= 2.0
                        if not dec_match:
                            # Log warning but don't filter out - transit time match is more reliable
                            logger.warning(
                                f"Group {group_id} transit time matches but declination mismatch: "
                                f"file dec={pt_dec_deg:.2f}°, expected {dec_deg:.2f}° "
                                f"(diff={abs(pt_dec_deg - dec_deg):.2f}°). "
                                f"Trusting transit time match."
                            )

                    # Verify complete 16-subband group
                    sb_codes = sorted(
                        os.path.basename(p).rsplit("_sb", 1)[1].split(".")[0]
                        for p in group_files
                    )
                    # Check that we have exactly 16 files and all subband codes are valid (00-15)
                    expected_codes = {f"{i:02d}" for i in range(16)}
                    full = len(group_files) == 16 and set(sb_codes) == expected_codes

                    if not full:
                        continue

                    # Sort files by subband number (0-15) for proper spectral order
                    # This ensures files are in correct order even if they have different timestamps
                    def sort_by_subband(fpath):
                        fname = os.path.basename(fpath)
                        # Extract subband number from filename (e.g., "2025-10-29T13:54:17_sb03.hdf5" -> 3)
                        if "_sb" in fname:
                            sb_part = fname.rsplit("_sb", 1)[1].split(".")[0]
                            try:
                                return int(sb_part)
                            except ValueError:
                                pass
                        return 999  # Put files without subband code at end

                    # CRITICAL: DSA-110 subbands use DESCENDING frequency order (sb00=highest, sb15=lowest).
                    # For proper frequency ordering (ascending, low to high), REVERSE the sort.
                    group_files_sorted = sorted(
                        group_files, key=sort_by_subband, reverse=True
                    )

                    dt_min = abs((group_mid - transit).to(u.min).value)

                    available_transits.append(
                        {
                            "transit_iso": transit.isot,
                            "transit_mjd": transit.mjd,
                            "group_id": group_id,
                            "group_mid_iso": group_mid.isot,
                            "delta_minutes": dt_min,
                            "subband_count": len(group_files_sorted),
                            "files": group_files_sorted,  # List of 16 HDF5 file paths sorted by subband number
                            "days_ago": (Time.now() - transit).to(u.day).value,
                            "has_ms": self.has_ms_for_transit(
                                calibrator_name, transit, tolerance_minutes=5.0
                            ),
                        }
                    )

                    # Only take first matching group per transit
                    break

                except Exception as e:
                    logger.debug(f"Failed to process group {group_id}: {e}")
                    continue

        # Sort by most recent first (by transit time)
        available_transits.sort(key=lambda x: x["transit_mjd"], reverse=True)

        return available_transits

    def locate_group(
        self, transit_info: dict, *, dec_tolerance_deg: float = 2.0
    ) -> Optional[List[str]]:
        """Locate subband group for transit.

        Args:
            transit_info: Transit info from find_transit()
            dec_tolerance_deg: Declination tolerance

        Returns:
            List of file paths or None if not found
        """
        if "files" in transit_info:
            return transit_info["files"]

        # Fallback: search using transit time window
        # Use 1-second tolerance to match pipeline standard (filename precision is to the second)
        groups = find_subband_groups(
            os.fspath(self.input_dir),
            transit_info["start_iso"],
            transit_info["end_iso"],
            tolerance_s=1.0,  # 1-second tolerance matches filename precision (YYYY-MM-DDTHH:MM:SS)
        )

        if not groups:
            return None

        # Return first complete group
        return groups[0] if groups else None

    def convert_group(
        self, file_list: List[str], output_ms: Path, *, stage_to_tmpfs: bool = True
    ) -> None:
        """Convert group to MS.

        Args:
            file_list: List of subband file paths
            output_ms: Output MS path
            stage_to_tmpfs: Whether to stage to tmpfs

        Raises:
            ConversionError: If conversion fails
        """
        # Ensure output directory exists
        output_ms.parent.mkdir(parents=True, exist_ok=True)

        # Determine scratch directory
        scratch_dir = None
        if stage_to_tmpfs:
            tmpfs_path = Path("/dev/shm")
            if tmpfs_path.exists():
                scratch_dir = str(tmpfs_path / "dsa110-contimg" / "conversion")

        if self.scratch_dir:
            scratch_dir = str(self.scratch_dir)

        # Convert
        try:
            write_ms_from_subbands(
                file_list, os.fspath(output_ms), scratch_dir=scratch_dir
            )
        except Exception as e:
            logger.error(f"Conversion failed: {e}", exc_info=True)
            raise ConversionError(f"Failed to convert subband group to MS: {e}") from e

    def _register_ms_in_db(
        self,
        ms_path: Path,
        transit_info: dict,
        *,
        status: str = "converted",
        stage: str = "converted",
    ) -> None:
        """Register MS in products database."""
        conn = ensure_products_db(self.products_db)

        # Extract time range from MS using standardized utility
        from dsa110_contimg.utils.time_utils import extract_ms_time_range

        start_mjd, end_mjd, mid_mjd = extract_ms_time_range(os.fspath(ms_path))

        # Use transit time if MS extraction fails
        if mid_mjd is None:
            mid_mjd = Time(transit_info["transit_iso"]).mjd

        ms_index_upsert(
            conn,
            os.fspath(ms_path),
            start_mjd=start_mjd,
            end_mjd=end_mjd,
            mid_mjd=mid_mjd,
            status=status,
            stage=stage,
            processed_at=time.time(),
        )
        conn.commit()
        conn.close()

    def generate_from_transit(
        self,
        calibrator_name: str,
        transit_time: Optional[Time] = None,
        *,
        window_minutes: int = 60,
        max_days_back: int = 14,
        dec_tolerance_deg: float = 2.0,
        auto_naming: bool = True,
        output_name: Optional[str] = None,
        configure_for_imaging: bool = True,
        register_in_db: bool = True,
        stage_to_tmpfs: bool = True,
    ) -> CalibratorMSResult:
        """Generate MS from calibrator transit.

        Args:
            calibrator_name: Name of calibrator (e.g., "0834+555")
            transit_time: Optional specific transit time
            window_minutes: Search window around transit
            max_days_back: Maximum days to search back
            dec_tolerance_deg: Declination tolerance
            auto_naming: Whether to auto-generate output filename
            output_name: Optional explicit output filename
            configure_for_imaging: Whether to configure MS for imaging
            register_in_db: Whether to register MS in products database
            stage_to_tmpfs: Whether to stage to tmpfs

        Returns:
            CalibratorMSResult with success status and details
        """
        progress = ProgressReporter(verbose=self.verbose)
        metrics = {}

        try:
            # Step 0: Validate inputs
            progress.info("Validating inputs...")
            self._validate_inputs(
                calibrator_name, transit_time, window_minutes, max_days_back
            )
            progress.success("Inputs validated")

            # Step 1: Check if MS already exists for this transit
            if transit_time is not None:
                progress.info("Checking for existing MS for this transit...")
                existing = self.find_existing_ms_for_transit(
                    calibrator_name, transit_time, tolerance_minutes=window_minutes / 2
                )
                if existing:
                    progress.success(f"Found existing MS: {existing['ms_path']}")
                    return CalibratorMSResult(
                        success=True,
                        ms_path=existing["ms_path"],
                        transit_info=None,  # Would need to reconstruct from transit_time
                        group_id=None,
                        already_exists=True,
                        metrics={
                            "exist_reason": "database_query",
                            "status": existing["status"],
                        },
                        progress_summary=progress.get_summary(),
                    )

            # Step 2: Find transit
            progress.info(f"Finding transit for {calibrator_name}...")
            transit_info = self.find_transit(
                calibrator_name,
                transit_time=transit_time,
                window_minutes=window_minutes,
                max_days_back=max_days_back,
            )

            if not transit_info:
                error_msg = f"No transit found for {calibrator_name} within {max_days_back} days"
                progress.error(error_msg)
                raise TransitNotFoundError(error_msg)

            progress.success(f"Found transit: {transit_info['transit_iso']}")
            metrics["transit_found"] = True
            metrics["transit_time"] = transit_info["transit_iso"]

            # Step 3: Check if MS exists for this transit (by transit time)
            transit_time_obj = Time(transit_info["transit_iso"])
            existing = self.find_existing_ms_for_transit(
                calibrator_name, transit_time_obj, tolerance_minutes=window_minutes / 2
            )
            if existing:
                progress.success(
                    f"Found existing MS for transit: {existing['ms_path']}"
                )
                return CalibratorMSResult(
                    success=True,
                    ms_path=existing["ms_path"],
                    transit_info=transit_info,
                    group_id=transit_info["group_id"],
                    already_exists=True,
                    metrics={
                        "exist_reason": "database_query",
                        "status": existing["status"],
                    },
                    progress_summary=progress.get_summary(),
                )

            # Step 4: Locate group
            progress.info("Locating subband group...")
            file_list = self.locate_group(
                transit_info, dec_tolerance_deg=dec_tolerance_deg
            )

            if not file_list:
                error_msg = f"No complete subband group found for transit"
                progress.error(error_msg)
                raise GroupNotFoundError(error_msg)

            progress.success(f"Found {len(file_list)} subband files")
            metrics["subbands"] = len(file_list)

            # Step 5: Derive output path
            ms_path = self._derive_output_path(
                calibrator_name,
                transit_info,
                auto_naming=auto_naming,
                output_name=output_name,
            )

            # Step 6: Check if already exists (by path)
            progress.info(f"Checking for existing MS: {ms_path}")
            exists, exist_info = self._check_existing_ms(ms_path, transit_info)

            if exists:
                progress.success(f"MS already exists (reason: {exist_info['reason']})")
                metrics["already_exists"] = True
                metrics["exist_reason"] = exist_info["reason"]

                return CalibratorMSResult(
                    success=True,
                    ms_path=ms_path,
                    transit_info=transit_info,
                    group_id=transit_info["group_id"],
                    already_exists=True,
                    metrics=metrics,
                    progress_summary=progress.get_summary(),
                )

            # Step 7: Convert
            progress.info(f"Converting {len(file_list)} subbands to MS...")
            convert_start = time.time()

            try:
                self.convert_group(file_list, ms_path, stage_to_tmpfs=stage_to_tmpfs)
            except ConversionError:
                raise  # Re-raise conversion errors
            except Exception as e:
                raise ConversionError(f"Conversion failed: {e}") from e

            convert_time = time.time() - convert_start
            progress.success(f"Conversion completed in {convert_time:.1f}s")
            metrics["conversion_time_seconds"] = convert_time

            # Step 8: Configure for imaging
            if configure_for_imaging:
                progress.info("Configuring MS for imaging...")
                configure_ms_for_imaging(os.fspath(ms_path))
                progress.success("MS configured for imaging")
                metrics["configured"] = True

            # Step 9: Register in database
            if register_in_db:
                progress.info("Registering MS in products database...")
                self._register_ms_in_db(ms_path, transit_info)
                progress.success("MS registered in database")
                metrics["registered"] = True

            progress.success(f"MS ready: {ms_path}")

            return CalibratorMSResult(
                success=True,
                ms_path=ms_path,
                transit_info=transit_info,
                group_id=transit_info["group_id"],
                already_exists=False,
                metrics=metrics,
                progress_summary=progress.get_summary(),
            )

        except (
            ValidationError,
            TransitNotFoundError,
            GroupNotFoundError,
            ConversionError,
            CalibratorNotFoundError,
        ) as e:
            error_msg = str(e)
            progress.error(error_msg)
            logger.error(error_msg, exc_info=True)
            return CalibratorMSResult(
                success=False,
                ms_path=None,
                transit_info=None,
                group_id=None,
                already_exists=False,
                error=error_msg,
                progress_summary=progress.get_summary(),
            )
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            progress.error(error_msg)
            logger.error(error_msg, exc_info=True)
            return CalibratorMSResult(
                success=False,
                ms_path=None,
                transit_info=None,
                group_id=None,
                already_exists=False,
                error=error_msg,
                progress_summary=progress.get_summary(),
            )
