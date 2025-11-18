# pylint: disable=no-member  # astropy.units uses dynamic attributes (deg, min, day, etc.)
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
from typing import Dict, List, Optional, Tuple

import astropy.units as u  # pylint: disable=no-member
import pandas as pd
from astropy.time import Time

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
from dsa110_contimg.conversion.strategies.direct_subband import (
    write_ms_from_subbands,
)
from dsa110_contimg.database.hdf5_index import query_subband_groups
from dsa110_contimg.database.products import (
    ensure_products_db,
    ms_index_upsert,
)

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


@dataclass
class GenerateMSConfig:
    """Configuration for MS generation from transit."""

    window_minutes: int = 60
    max_days_back: int = 14
    dec_tolerance_deg: float = 2.5
    auto_naming: bool = True
    output_name: Optional[str] = None
    configure_for_imaging: bool = True
    register_in_db: bool = True
    stage_to_tmpfs: bool = True


class CalibratorMSGenerator:
    """Service for generating MS files from calibrator transits.

    Example Usage:
        >>> gen = CalibratorMSGenerator(
        ...     input_dir=Path('/data/incoming'),
        ...     output_dir=Path('/stage/dsa110-contimg/ms/calibrators'),
        ...     products_db=Path('/data/dsa110-contimg/state/products.sqlite3'),
        ...     hdf5_db=Path('/data/dsa110-contimg/state/hdf5.sqlite3'),
        ...     catalogs=[Path('/data/dsa110-contimg/state/catalogs/vla_calibrators.sqlite3')]
        ... )
        >>> result = gen.generate_from_transit(
        ...     calibrator_name='0834+555',
        ...     transit_time=Time('2025-10-02T01:12:00'),
        ...     window_minutes=12
        ... )

    Note: calibrator_name is passed to generate_from_transit(), NOT to __init__()
    """

    def __init__(
        self,
        *,
        input_dir: Path,
        output_dir: Path,
        products_db: Path,
        hdf5_db: Optional[Path] = None,
        catalogs: List[Path],
        scratch_dir: Optional[Path] = None,
        verbose: bool = True,
        dec_tolerance_deg: float = 2.5,
    ):
        """Initialize generator with configuration.

        Args:
            input_dir: Directory containing UVH5 files
            output_dir: Directory for output MS files
            products_db: Path to products database
            hdf5_db: Path to HDF5 file index database (default: infer from environment or use products_db)
            catalogs: List of calibrator catalog paths (SQLite databases, CSV fallback disabled)
            scratch_dir: Optional scratch directory for staging
            verbose: Whether to print progress messages (NOTE: not used by convert_subband_groups_to_ms)
            dec_tolerance_deg: Declination tolerance in degrees (default: 2.5)
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.products_db = Path(products_db)

        # Determine HDF5 database path
        if hdf5_db is not None:
            self.hdf5_db = Path(hdf5_db)
        else:
            # Try to infer from environment variable
            import os

            hdf5_db_env = os.getenv("HDF5_DB_PATH")
            if hdf5_db_env:
                self.hdf5_db = Path(hdf5_db_env)
            else:
                # Default to hdf5.sqlite3 in same directory as products_db
                # This is the correct default since HDF5 index is in a separate database
                products_db_path = Path(products_db)
                self.hdf5_db = products_db_path.parent / "hdf5.sqlite3"

        self.catalogs = [Path(c) for c in catalogs]
        self.scratch_dir = Path(scratch_dir) if scratch_dir else None
        self.verbose = verbose
        self.dec_tolerance_deg = dec_tolerance_deg

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_config(cls, config: CalibratorMSConfig, verbose: bool = True) -> CalibratorMSGenerator:
        """Create generator from configuration."""
        return cls(
            input_dir=config.input_dir,
            output_dir=config.output_dir,
            products_db=config.products_db,
            catalogs=config.catalogs,
            scratch_dir=config.scratch_dir,
            verbose=verbose,
            dec_tolerance_deg=config.default_dec_tolerance_deg,
        )

    def _validate_calibrator_name(self, calibrator_name: str) -> None:
        """Validate calibrator name.

        Raises:
            ValidationError: If calibrator name is invalid
        """
        if not calibrator_name or not calibrator_name.strip():
            raise ValidationError("Calibrator name cannot be empty")

    def _validate_window_minutes(self, window_minutes: int) -> None:
        """Validate window_minutes parameter.

        Raises:
            ValidationError: If window_minutes is invalid
        """
        if window_minutes <= 0:
            raise ValidationError(f"window_minutes must be positive, got {window_minutes}")

    def _validate_max_days_back(self, max_days_back: int) -> None:
        """Validate max_days_back parameter.

        Raises:
            ValidationError: If max_days_back is invalid
        """
        if max_days_back <= 0:
            raise ValidationError(f"max_days_back must be positive, got {max_days_back}")

    def _validate_transit_time(self, transit_time: Optional[Time]) -> None:
        """Validate transit_time parameter.

        Raises:
            ValidationError: If transit_time is invalid
        """
        if transit_time is not None and transit_time > Time.now():
            raise ValidationError(f"transit_time cannot be in the future: {transit_time}")

    def _validate_input_directory(self) -> None:
        """Validate input directory exists and is a directory.

        Raises:
            ValidationError: If input directory is invalid
        """
        if not self.input_dir.exists():
            raise ValidationError(f"Input directory does not exist: {self.input_dir}")

        if not self.input_dir.is_dir():
            raise ValidationError(f"Input directory is not a directory: {self.input_dir}")

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
        self._validate_calibrator_name(calibrator_name)
        self._validate_window_minutes(window_minutes)
        self._validate_max_days_back(max_days_back)
        self._validate_transit_time(transit_time)
        self._validate_input_directory()

    def _load_catalog_dataframe(self, catalog_path: Path) -> Optional[pd.DataFrame]:
        """Load catalog as DataFrame from SQLite or CSV.

        Args:
            catalog_path: Path to catalog file

        Returns:
            DataFrame if successfully loaded, None otherwise
        """
        from dsa110_contimg.calibration.catalogs import (  # read_vla_parsed_catalog_csv,  # DISABLED: CSV fallback should not be used
            load_vla_catalog_from_sqlite,
        )

        if not catalog_path.exists():
            return None

        try:
            # Handle SQLite database (preferred and REQUIRED)
            if str(catalog_path).endswith(".sqlite3"):
                return load_vla_catalog_from_sqlite(str(catalog_path))

            # CSV fallback DISABLED - SQLite database should be properly populated instead
            # If you're seeing this error, the SQLite database needs to be populated with
            # calibrators for the declination range of your observations.
            logger.error(
                f"CSV catalog fallback is disabled. Only SQLite databases are supported: {catalog_path}"
            )
            logger.error(
                "Please ensure /data/dsa110-contimg/state/catalogs/vla_calibrators.sqlite3 "
                "is populated with calibrators for your observation declinations."
            )
            return None

            # OLD CSV CODE (disabled):
            # return read_vla_parsed_catalog_csv(catalog_path)
        except Exception as e:
            logger.debug(f"Failed to read catalog {catalog_path}: {e}")
            return None

    def _extract_coordinates_from_row(self, row: pd.Series) -> Optional[Tuple[float, float]]:
        """Extract RA/Dec coordinates from a catalog row.

        Args:
            row: Pandas Series or DataFrame row

        Returns:
            Tuple of (ra, dec) in degrees if valid, None otherwise
        """
        import numpy as np

        # Handle both Series and DataFrame cases
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]

        try:
            ra = float(row["ra_deg"])
            dec = float(row["dec_deg"])
        except (TypeError, KeyError):
            # Try attribute access for Series
            try:
                ra = float(row.ra_deg)
                dec = float(row.dec_deg)
            except (TypeError, AttributeError):
                return None

        # Validate coordinates are finite
        if np.isfinite(ra) and np.isfinite(dec):
            return ra, dec

        return None

    def _load_radec(self, name: str) -> Tuple[float, float]:
        """Load RA/Dec for calibrator from catalogs.

        Always prefers SQLite database over CSV files. Iterates through catalogs
        in order until the calibrator is found.

        Args:
            name: Calibrator name to look up

        Returns:
            Tuple of (ra_deg, dec_deg)

        Raises:
            CalibratorNotFoundError: If calibrator not found in any catalog
        """
        for catalog_path in self.catalogs:
            df = self._load_catalog_dataframe(catalog_path)
            if df is None:
                continue

            if name not in df.index:
                continue

            row = df.loc[name]
            coords = self._extract_coordinates_from_row(row)
            if coords is not None:
                return coords

        raise CalibratorNotFoundError(f"Calibrator {name} not found in catalogs: {self.catalogs}")

    def _calculate_transit_window(self, transit: Time, window_minutes: int) -> Tuple[str, str]:
        """Calculate search window around a transit time.

        Args:
            transit: Transit time
            window_minutes: Search window in minutes

        Returns:
            Tuple of (start_time_str, end_time_str) in format "YYYY-MM-DD HH:MM:SS"
        """
        half = window_minutes // 2
        t0 = (
            (transit - half * u.min).to_datetime().strftime("%Y-%m-%d %H:%M:%S")
        )  # pylint: disable=no-member
        t1 = (
            (transit + half * u.min).to_datetime().strftime("%Y-%m-%d %H:%M:%S")
        )  # pylint: disable=no-member
        return t0, t1

    def _get_transit_times(
        self, ra_deg: float, transit_time: Optional[Time], max_days_back: int
    ) -> List[Time]:
        """Get list of transit times to search.

        Args:
            ra_deg: Right ascension in degrees
            transit_time: Optional specific transit time to use
            max_days_back: Maximum days to search back

        Returns:
            List of transit times
        """
        if transit_time is None:
            return previous_transits(ra_deg, start_time=Time.now(), n=max_days_back)
        return [transit_time]

    def _log_search_window(self, transit: Time, t0: str, t1: str, window_minutes: int) -> None:
        """Log search window information.

        Args:
            transit: Transit time
            t0: Start time string
            t1: End time string
            window_minutes: Search window in minutes
        """
        t0_date = t0.split()[0]
        t0_time = t0.split()[1] if len(t0.split()) > 1 else ""
        t1_time = t1.split()[1] if len(t1.split()) > 1 else ""

        if t0.split()[0] == t1.split()[0]:
            logger.info(
                f"Search window: {t0_date} {t0_time} to {t1_time} "
                f"(±{window_minutes // 2} minutes around transit at {transit.to_datetime().strftime('%H:%M:%S')}). "
                f"Selecting group closest to transit time..."
            )
        else:
            logger.info(
                f"Search window: {t0} to {t1} (±{window_minutes // 2} minutes around transit). "
                f"Selecting group closest to transit time..."
            )

    def _find_best_candidate_group(
        self, groups: List[List[str]], transit: Time
    ) -> Optional[Tuple[float, List[str], Time]]:
        """Find the group whose mid-time is closest to transit.

        Args:
            groups: List of file groups
            transit: Transit time

        Returns:
            Tuple of (delta_minutes, best_group, mid_time) or None if no valid candidates
        """
        candidates = []
        for g in groups:
            base = os.path.basename(g[0])
            ts_str = base.split("_sb")[0]
            try:
                mid = Time(ts_str)
                dt_min = abs((mid - transit).to(u.min)).value  # pylint: disable=no-member
                candidates.append((dt_min, g, mid))
            except Exception:
                continue

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0])
        return candidates[0]

    def _is_complete_subband_group(self, group: List[str]) -> Tuple[bool, List[str]]:
        """Check if group has complete 16 subbands and return sorted files.

        Args:
            group: List of file paths

        Returns:
            Tuple of (is_complete, sorted_files)
        """
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            _extract_subband_code,
        )

        sb_codes = sorted(_extract_subband_code(os.path.basename(p)) for p in group)

        def sort_by_subband(fpath):
            sb_code = _extract_subband_code(os.path.basename(fpath))
            if sb_code:
                sb_num = int(sb_code.replace("sb", ""))
                return sb_num
            return 999

        group_sorted = sorted(group, key=sort_by_subband, reverse=True)
        is_complete = len(group) == 16 and all(code and code.startswith("sb") for code in sb_codes)

        return is_complete, group_sorted

    def _calculate_primary_beam_metrics(
        self,
        group_file: str,
        ra_deg: float,
        dec_deg: float,
        freq_ghz: float,
    ) -> Dict[str, float]:
        """Calculate primary beam metrics for calibrator validation.

        Args:
            group_file: Path to first file in group
            ra_deg: Calibrator RA in degrees
            dec_deg: Calibrator Dec in degrees
            freq_ghz: Frequency in GHz

        Returns:
            Dictionary with metrics (pb_response, sep_deg, pt_ra_deg, pt_dec_deg)
        """
        import numpy as np
        from astropy.coordinates import SkyCoord

        from dsa110_contimg.calibration.catalogs import (
            airy_primary_beam_response,
        )
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            _peek_uvh5_phase_and_midtime,
        )

        pt_ra_rad, pt_dec_rad, _ = _peek_uvh5_phase_and_midtime(group_file)
        pt_ra_deg = float(pt_ra_rad.to_value(u.deg))  # pylint: disable=no-member
        pt_dec_deg = float(pt_dec_rad.to_value(u.deg))  # pylint: disable=no-member

        cal_ra_rad = np.deg2rad(ra_deg)
        cal_dec_rad = np.deg2rad(dec_deg)
        pt_ra_rad_val = float(pt_ra_rad.to_value(u.rad))
        pt_dec_rad_val = float(pt_dec_rad.to_value(u.rad))

        pb_response = airy_primary_beam_response(
            pt_ra_rad_val, pt_dec_rad_val, cal_ra_rad, cal_dec_rad, freq_ghz
        )

        pt_coord = SkyCoord(ra=pt_ra_rad_val * u.rad, dec=pt_dec_rad_val * u.rad)
        cal_coord = SkyCoord(ra=cal_ra_rad * u.rad, dec=cal_dec_rad * u.rad)
        sep = pt_coord.separation(cal_coord)
        sep_deg = float(sep.to_value(u.deg))  # pylint: disable=no-member

        return {
            "pb_response": pb_response,
            "sep_deg": sep_deg,
            "pt_ra_deg": pt_ra_deg,
            "pt_dec_deg": pt_dec_deg,
        }

    def _validate_primary_beam(
        self,
        group_file: str,
        ra_deg: float,
        dec_deg: float,
        min_pb_response: float,
        freq_ghz: float,
    ) -> Optional[Dict[str, float]]:
        """Validate that calibrator is in primary beam.

        Args:
            group_file: Path to first file in group
            ra_deg: Calibrator RA in degrees
            dec_deg: Calibrator Dec in degrees
            min_pb_response: Minimum primary beam response required
            freq_ghz: Frequency in GHz

        Returns:
            Dictionary with validation results (pb_response, sep_deg, pt_ra_deg, pt_dec_deg) or None if invalid
        """
        metrics = self._calculate_primary_beam_metrics(group_file, ra_deg, dec_deg, freq_ghz)

        if metrics["pb_response"] < min_pb_response:
            return None

        return metrics

    def _log_found_groups(
        self,
        groups: List[List[str]],
        transit: Time,
        t0: str,
        t1: str,
        window_minutes: int,
    ) -> None:
        """Log information about found groups for a transit.

        Args:
            groups: List of group file lists
            transit: Transit time
            t0: Start time string
            t1: End time string
            window_minutes: Search window in minutes
        """
        total_files = sum(len(g) for g in groups)
        logger.info(
            f"Found {len(groups)} complete 16-subband group(s) ({total_files} total files) "
            f"for transit {transit.isot}"
        )
        self._log_search_window(transit, t0, t1, window_minutes)

    def _log_primary_beam_rejection(
        self,
        transit: Time,
        calibrator_name: str,
        ra_deg: float,
        dec_deg: float,
        metrics: dict,
        min_pb_response: float,
    ) -> None:
        """Log primary beam validation failure.

        Args:
            transit: Transit time
            calibrator_name: Calibrator name
            ra_deg: Calibrator RA in degrees
            dec_deg: Calibrator Dec in degrees
            metrics: Primary beam metrics dict
            min_pb_response: Minimum required PB response
        """
        logger.warning(
            f"REJECTING transit {transit.isot}: Calibrator {calibrator_name} "
            f"is NOT in primary beam\n"
            f"  Calibrator: RA={ra_deg:.4f}°, Dec={dec_deg:.4f}°\n"
            f"  Pointing: RA={metrics['pt_ra_deg']:.4f}°, Dec={metrics['pt_dec_deg']:.4f}°\n"
            f"  Separation: {metrics['sep_deg']:.4f}° ({metrics['sep_deg'] * 60:.1f} arcmin)\n"
            f"  Primary beam response: {metrics['pb_response']:.4f} (minimum required: {min_pb_response:.2f})\n"
            f"  This group will be skipped - calibrator is outside usable beam."
        )

    def _log_primary_beam_success(
        self,
        transit: Time,
        gbest: List[str],
        dt_min: float,
        pb_validation: dict,
        ra_deg: float,
        dec_deg: float,
    ) -> None:
        """Log successful primary beam validation.

        Args:
            transit: Transit time
            gbest: Best candidate group file list
            dt_min: Time difference in minutes
            pb_validation: Primary beam validation dict
            ra_deg: Calibrator RA in degrees
            dec_deg: Calibrator Dec in degrees
        """
        logger.info(
            f"✓ Found complete 16-subband group for transit {transit.isot}: "
            f"{os.path.basename(gbest[0]).split('_sb')[0]} "
            f"({dt_min:.1f} min from transit)"
        )
        logger.info(
            f"✓ Pointing validation PASSED: Calibrator in primary beam\n"
            f"  Pointing: RA={pb_validation['pt_ra_deg']:.4f}°, Dec={pb_validation['pt_dec_deg']:.4f}°\n"
            f"  Calibrator: RA={ra_deg:.4f}°, Dec={dec_deg:.4f}°\n"
            f"  Separation: {pb_validation['sep_deg']:.4f}° ({pb_validation['sep_deg'] * 60:.1f} arcmin)\n"
            f"  Primary beam response: {pb_validation['pb_response']:.4f}"
        )

    def _build_transit_result_dict(
        self,
        calibrator_name: str,
        transit: Time,
        t0: str,
        t1: str,
        gbest: List[str],
        mid: Time,
        dt_min: float,
        gbest_sorted: List[str],
        pb_validation: dict,
        dec_deg: float,
    ) -> dict:
        """Build transit result dictionary.

        Args:
            calibrator_name: Calibrator name
            transit: Transit time
            t0: Start time string
            t1: End time string
            gbest: Best candidate group file list
            mid: Group mid-time
            dt_min: Time difference in minutes
            gbest_sorted: Sorted group file list
            pb_validation: Primary beam validation dict
            dec_deg: Calibrator declination in degrees

        Returns:
            Transit info dictionary
        """
        return {
            "name": calibrator_name,
            "transit_iso": transit.isot,
            "start_iso": t0,
            "end_iso": t1,
            "group_id": os.path.basename(gbest[0]).split("_sb")[0],
            "mid_iso": mid.isot,
            "delta_minutes": dt_min,
            "files": gbest_sorted,
            "pointing_dec_deg": pb_validation["pt_dec_deg"],
            "calibrator_dec_deg": dec_deg,
            "separation_deg": pb_validation["sep_deg"],
            "pb_response": pb_validation["pb_response"],
        }

    def _process_single_transit(
        self,
        t: Time,
        calibrator_name: str,
        ra_deg: float,
        dec_deg: float,
        window_minutes: int,
        min_pb_response: float,
        freq_ghz: float,
    ) -> Optional[dict]:
        """Process a single transit to find matching group.

        Args:
            t: Transit time
            calibrator_name: Name of calibrator
            ra_deg: Calibrator RA in degrees
            dec_deg: Calibrator Dec in degrees
            window_minutes: Search window in minutes
            min_pb_response: Minimum primary beam response
            freq_ghz: Frequency in GHz

        Returns:
            Transit info dict if found, None otherwise
        """
        t0, t1 = self._calculate_transit_window(t, window_minutes)
        groups = query_subband_groups(self.hdf5_db, t0, t1, tolerance_s=1.0)

        if not groups:
            return None

        self._log_found_groups(groups, t, t0, t1, window_minutes)

        candidate_result = self._find_best_candidate_group(groups, t)
        if not candidate_result:
            return None

        dt_min, gbest, mid = candidate_result

        is_complete, gbest_sorted = self._is_complete_subband_group(gbest)
        if not is_complete:
            logger.info(
                f"Skipping transit {t.isot}: found group with {len(gbest)} subbands "
                f"(need 16 complete), best candidate: {os.path.basename(gbest[0])}"
            )
            return None

        # Check declination match first (enforced with tolerance)
        pt_dec_deg = None
        try:
            from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
                _peek_uvh5_phase_and_midtime,
            )

            _, pt_dec_rad, _ = _peek_uvh5_phase_and_midtime(gbest[0])
            pt_dec_deg = float(pt_dec_rad.to_value(u.deg)) if pt_dec_rad is not None else None
        except Exception:
            pass

        if pt_dec_deg is not None:
            if not self._check_declination_match(
                gbest[0],
                pt_dec_deg,
                dec_deg,
                dec_tolerance_deg=self.dec_tolerance_deg,
            ):
                logger.warning(
                    f"Transit {t.isot}: Declination mismatch for group {os.path.basename(gbest[0])}, "
                    f"rejecting transit match."
                )
                return None

        pb_validation = self._validate_primary_beam(
            gbest[0], ra_deg, dec_deg, min_pb_response, freq_ghz
        )
        if not pb_validation:
            metrics = self._calculate_primary_beam_metrics(gbest[0], ra_deg, dec_deg, freq_ghz)
            self._log_primary_beam_rejection(
                t, calibrator_name, ra_deg, dec_deg, metrics, min_pb_response
            )
            logger.warning(
                f"Transit {t.isot}: Primary beam response {metrics['pb_response']:.4f} "
                f"below minimum {min_pb_response:.2f}, rejecting transit match."
            )
            return None

        # Log primary beam response (even if above threshold, for monitoring)
        pb_metrics = self._calculate_primary_beam_metrics(gbest[0], ra_deg, dec_deg, freq_ghz)
        if pb_metrics["pb_response"] < 0.3:
            logger.warning(
                f"Transit {t.isot}: Primary beam response {pb_metrics['pb_response']:.4f} "
                f"is below 30% threshold (but above minimum {min_pb_response:.2f}). "
                f"Flagging for review."
            )

        self._log_primary_beam_success(t, gbest, dt_min, pb_validation, ra_deg, dec_deg)

        return self._build_transit_result_dict(
            calibrator_name,
            t,
            t0,
            t1,
            gbest,
            mid,
            dt_min,
            gbest_sorted,
            pb_validation,
            dec_deg,
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
        transits = self._get_transit_times(ra_deg, transit_time, max_days_back)

        for t in transits:
            result = self._process_single_transit(
                t,
                calibrator_name,
                ra_deg,
                dec_deg,
                window_minutes,
                min_pb_response,
                freq_ghz,
            )
            if result:
                return result

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
            transit_iso = transit_info["transit_iso"].replace(":", "-").replace("T", "_")
            return self.output_dir / f"{cal_safe}_{transit_iso}.ms"

        # Fallback: use group ID
        return self.output_dir / f"{transit_info['group_id']}.ms"

    def _check_existing_ms(self, ms_path: Path, transit_info: dict) -> Tuple[bool, Optional[dict]]:
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
            return True, {
                "reason": "database",
                "status": row[1],
                "stage": row[2],
            }

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

    def _resolve_transit_time(
        self,
        calibrator_name: str,
        transit_time: Optional[Time],
        tolerance_minutes: float,
        max_days_back: int,
    ) -> Optional[Time]:
        """Resolve transit time, finding latest if not provided.

        Args:
            calibrator_name: Name of calibrator
            transit_time: Optional transit time
            tolerance_minutes: Time tolerance in minutes
            max_days_back: Maximum days to search back

        Returns:
            Transit time or None if not found
        """
        if transit_time is not None:
            return transit_time

        transit_info = self.find_transit(
            calibrator_name,
            transit_time=None,
            window_minutes=int(tolerance_minutes * 2),
            max_days_back=max_days_back,
        )
        if not transit_info:
            return None
        return Time(transit_info["transit_iso"])

    def _query_ms_by_time_range(self, transit_time: Time, tolerance_minutes: float) -> List[tuple]:
        """Query MS files in database by time range.

        Args:
            transit_time: Transit time
            tolerance_minutes: Time tolerance in minutes

        Returns:
            List of (path, status, stage, mid_mjd, processed_at) tuples
        """
        conn = ensure_products_db(self.products_db)
        transit_mjd = transit_time.mjd
        tol_mjd = tolerance_minutes / (24 * 60)

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
        return rows

    def _match_calibrator_in_path(self, path: Path, calibrator_name: str) -> bool:
        """Check if calibrator name matches in MS file path.

        Args:
            path: MS file path
            calibrator_name: Calibrator name to match

        Returns:
            True if calibrator name found in path, False otherwise
        """
        cal_patterns = [
            calibrator_name.replace("+", "_").replace("-", "_"),
            calibrator_name.replace("+", "_"),
            calibrator_name.replace("-", "_"),
            calibrator_name,
        ]

        path_str = Path(path).stem.lower()
        for pattern in cal_patterns:
            if pattern.lower() in path_str:
                return True
        return False

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
        transit_time = self._resolve_transit_time(
            calibrator_name, transit_time, tolerance_minutes, max_days_back
        )
        if transit_time is None:
            return None

        rows = self._query_ms_by_time_range(transit_time, tolerance_minutes)
        if not rows:
            return None

        for row in rows:
            path, status, stage, mid_mjd, processed_at = row
            if self._match_calibrator_in_path(Path(path), calibrator_name):
                return {
                    "ms_path": Path(path),
                    "status": status,
                    "stage": stage,
                    "mid_mjd": mid_mjd,
                    "processed_at": processed_at,
                }

        return None

    def list_ms_for_calibrator(self, calibrator_name: str, *, limit: int = 10) -> List[dict]:
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

    def _calculate_search_window(self, max_days_back: int) -> Tuple[str, str, Time]:
        """Calculate time range for HDF5 index query.

        Args:
            max_days_back: Maximum days to search back

        Returns:
            Tuple of (start_time_str, end_time_str, cutoff_time)
        """
        now = Time.now()
        start_time = (
            (now - max_days_back * u.day).to_datetime().strftime("%Y-%m-%d %H:%M:%S")
        )  # pylint: disable=no-member
        end_time = now.to_datetime().strftime("%Y-%m-%d %H:%M:%S")
        cutoff_time = now - max_days_back * u.day  # pylint: disable=no-member
        return start_time, end_time, cutoff_time

    def _query_hdf5_groups_in_window(self, transit: Time, window_minutes: int) -> List[List[str]]:
        """Query database for HDF5 groups in a window around a transit.

        Args:
            transit: Transit time
            window_minutes: Window size in minutes

        Returns:
            List of group file lists
        """
        half_window = window_minutes // 2
        t0 = (
            (transit - half_window * u.min).to_datetime().strftime("%Y-%m-%d %H:%M:%S")
        )  # pylint: disable=no-member
        t1 = (
            (transit + half_window * u.min).to_datetime().strftime("%Y-%m-%d %H:%M:%S")
        )  # pylint: disable=no-member

        groups = query_subband_groups(self.hdf5_db, t0, t1, tolerance_s=1.0)
        return groups if groups else []

    def _extract_group_time_and_dec(
        self, group_files: List[str], group_id: str
    ) -> Tuple[Time, Optional[float]]:
        """Extract group mid-time and declination from HDF5 file.

        Args:
            group_files: List of HDF5 file paths
            group_id: Group identifier (used as fallback for time)

        Returns:
            Tuple of (group_mid_time, declination_deg or None)
        """
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            _peek_uvh5_phase_and_midtime,
        )

        group_start = Time(group_id)

        try:
            _, pt_dec_rad, mid_mjd = _peek_uvh5_phase_and_midtime(group_files[0])
            # Check if mid_mjd is valid (not None and not 0.0)
            if mid_mjd is not None and mid_mjd > 0:
                pt_dec_deg = (
                    pt_dec_rad.to(u.deg).value if pt_dec_rad is not None else None
                )  # pylint: disable=no-member
                group_mid = Time(mid_mjd, format="mjd")
            else:
                # Invalid mid_mjd, fallback to group_start
                group_mid = group_start
                pt_dec_deg = (
                    pt_dec_rad.to(u.deg).value if pt_dec_rad is not None else None
                )  # pylint: disable=no-member
        except Exception:
            # Fallback: use group_start as mid-time, skip dec check
            group_mid = group_start
            pt_dec_deg = None

        return group_mid, pt_dec_deg

    def _validate_transit_in_window(
        self, group_id: str, transit: Time, filelength: u.Quantity
    ) -> bool:
        """Check if transit falls within group's observation window.

        Args:
            group_id: Group identifier
            transit: Transit time
            filelength: Typical observation file length

        Returns:
            True if transit is within window, False otherwise
        """
        from dsa110_contimg.calibration.schedule import cal_in_datetime

        return cal_in_datetime(
            group_id,
            transit,
            duration=0 * u.min,  # Transit must be within file  # pylint: disable=no-member
            filelength=filelength,
        )

    def _check_declination_match(
        self,
        group_id: str,
        pt_dec_deg: Optional[float],
        dec_deg: float,
        dec_tolerance_deg: float = 2.5,
    ) -> bool:
        """Check declination match with tolerance.

        Args:
            group_id: Group identifier for logging
            pt_dec_deg: Declination from file (degrees) or None
            dec_deg: Expected declination (degrees)
            dec_tolerance_deg: Declination tolerance in degrees (default: 2.5)

        Returns:
            True if declination is within tolerance, False otherwise
        """
        if pt_dec_deg is None:
            logger.warning(f"Group {group_id}: Could not determine declination from file")
            return False

        dec_diff = abs(pt_dec_deg - dec_deg)
        dec_match = dec_diff <= dec_tolerance_deg

        if not dec_match:
            logger.warning(
                f"Group {group_id} declination mismatch: "
                f"file dec={pt_dec_deg:.2f}°, expected {dec_deg:.2f}° "
                f"(diff={dec_diff:.2f}°, tolerance=±{dec_tolerance_deg:.2f}°). "
                f"Rejecting transit match."
            )
        else:
            logger.debug(
                f"Group {group_id} declination match: "
                f"file dec={pt_dec_deg:.2f}°, expected {dec_deg:.2f}° "
                f"(diff={dec_diff:.2f}°, within ±{dec_tolerance_deg:.2f}° tolerance)"
            )

        return dec_match

    def _validate_complete_subband_group(self, group_files: List[str]) -> bool:
        """Verify group has complete 16-subband coverage.

        Args:
            group_files: List of HDF5 file paths

        Returns:
            True if group has exactly 16 files with valid subband codes (00-15)
        """
        sb_codes = sorted(
            os.path.basename(p).rsplit("_sb", 1)[1].split(".")[0] for p in group_files
        )
        expected_codes = {f"{i:02d}" for i in range(16)}
        return len(group_files) == 16 and set(sb_codes) == expected_codes

    def _sort_files_by_subband(self, group_files: List[str]) -> List[str]:
        """Sort files by subband number for proper spectral order.

        Args:
            group_files: List of HDF5 file paths

        Returns:
            Sorted list of file paths (descending subband order for ascending frequency)
        """

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
        return sorted(group_files, key=sort_by_subband, reverse=True)

    def _match_transit_to_group(
        self,
        transit: Time,
        group_files: List[str],
        group_id: str,
        dec_deg: float,
        cutoff_time: Time,
        filelength: u.Quantity,
    ) -> Optional[dict]:
        """Check if a transit matches a group and extract group metadata.

        Args:
            transit: Transit time
            group_files: List of HDF5 file paths for the group
            group_id: Group identifier
            dec_deg: Expected declination in degrees
            cutoff_time: Cutoff time for filtering old groups
            filelength: Typical observation file length

        Returns:
            Transit info dict if match found, None otherwise
        """
        try:
            # Parse timestamp from group ID (this is the start time)
            group_start = Time(group_id)

            # Skip if too old
            if group_start < cutoff_time:
                return None

            # Get actual mid-time and declination from file
            group_mid, pt_dec_deg = self._extract_group_time_and_dec(group_files, group_id)

            # Check if this transit falls within group's observation window
            if not self._validate_transit_in_window(group_id, transit, filelength):
                return None

            # Check declination match (enforced with tolerance)
            if not self._check_declination_match(
                group_id,
                pt_dec_deg,
                dec_deg,
                dec_tolerance_deg=self.dec_tolerance_deg,
            ):
                return None

            # Verify complete 16-subband group
            if not self._validate_complete_subband_group(group_files):
                return None

            # Sort files by subband number for proper spectral order
            group_files_sorted = self._sort_files_by_subband(group_files)

            dt_min = abs((group_mid - transit).to(u.min).value)  # pylint: disable=no-member

            return {
                "group_id": group_id,
                "group_mid": group_mid,
                "group_files_sorted": group_files_sorted,
                "delta_minutes": dt_min,
            }

        except Exception as e:
            logger.debug(f"Failed to process group {group_id}: {e}")
            return None

    def _enrich_transit_info(
        self,
        transit: Time,
        calibrator_name: str,
        group_info: dict,
    ) -> dict:
        """Enrich transit info with additional metadata.

        Args:
            transit: Transit time
            calibrator_name: Name of calibrator
            group_info: Group info dict from _match_transit_to_group

        Returns:
            Complete transit info dict
        """
        return {
            "transit_iso": transit.isot,
            "transit_mjd": transit.mjd,
            "group_id": group_info["group_id"],
            "group_mid_iso": group_info["group_mid"].isot,
            "delta_minutes": group_info["delta_minutes"],
            "subband_count": len(group_info["group_files_sorted"]),
            "files": group_info["group_files_sorted"],
            "days_ago": (Time.now() - transit).to(u.day).value,  # pylint: disable=no-member
            "has_ms": self.has_ms_for_transit(calibrator_name, transit, tolerance_minutes=5.0),
        }

    def _convert_groups_list_to_dict(self, complete_groups_list: List[List[str]]) -> dict:
        """Convert list of group file lists to dict keyed by group_id.

        Args:
            complete_groups_list: List of group file lists from database query

        Returns:
            Dict mapping group_id to list of file paths
        """
        complete_groups = {}
        for group_files in complete_groups_list:
            if not group_files:
                continue
            # Extract group_id from first file
            base = os.path.basename(group_files[0])
            if "_sb" not in base:
                continue
            group_id = base.split("_sb")[0]
            complete_groups[group_id] = group_files
        return complete_groups

    def _find_matching_group_for_transit(
        self,
        transit: Time,
        groups: List[List[str]],
        dec_deg: float,
        cutoff_time: Time,
        filelength: u.Quantity,
        calibrator_name: str,
    ) -> Optional[dict]:
        """Find first matching group for a transit.

        Args:
            transit: Transit time
            groups: List of group file lists
            dec_deg: Expected declination in degrees
            cutoff_time: Cutoff time for filtering old groups
            filelength: Typical observation file length
            calibrator_name: Name of calibrator

        Returns:
            Transit info dict if match found, None otherwise
        """
        for group_files in groups:
            base = os.path.basename(group_files[0])
            group_id = base.split("_sb")[0]

            # Match transit to group
            group_info = self._match_transit_to_group(
                transit=transit,
                group_files=group_files,
                group_id=group_id,
                dec_deg=dec_deg,
                cutoff_time=cutoff_time,
                filelength=filelength,
            )

            if group_info:
                # Enrich with additional metadata
                return self._enrich_transit_info(
                    transit=transit,
                    calibrator_name=calibrator_name,
                    group_info=group_info,
                )

        return None

    def _process_transits_for_available_data(
        self,
        transits: List[Time],
        calibrator_name: str,
        dec_deg: float,
        cutoff_time: Time,
        filelength: u.Quantity,
        window_minutes: int,
    ) -> List[dict]:
        """Process transits to find available data groups.

        Args:
            transits: List of transit times
            calibrator_name: Name of calibrator
            dec_deg: Declination in degrees
            cutoff_time: Cutoff time for filtering old groups
            filelength: Typical observation file length
            window_minutes: Search window in minutes

        Returns:
            List of transit info dicts with available data
        """
        available_transits = []
        for transit in transits:
            groups = self._query_hdf5_groups_in_window(transit, window_minutes)
            if not groups:
                continue

            transit_info = self._find_matching_group_for_transit(
                transit=transit,
                groups=groups,
                dec_deg=dec_deg,
                cutoff_time=cutoff_time,
                filelength=filelength,
                calibrator_name=calibrator_name,
            )

            if transit_info:
                available_transits.append(transit_info)

        available_transits.sort(key=lambda x: x["transit_mjd"], reverse=True)
        return available_transits

    def list_available_transits(
        self,
        calibrator_name: str,
        *,
        max_days_back: int = 30,
        window_minutes: int = 60,
    ) -> List[dict]:
        """List all available transits for a calibrator that have data in input directory.

        This method first checks for pre-calculated transit times in the cache.
        If cache is available and recent, uses cached results. Otherwise, calculates
        transit times on-demand.

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
        # Try to use stored transit times from database first
        try:
            from dsa110_contimg.conversion.transit_precalc import (
                get_calibrator_transits,
            )

            # Convert max_days_back to min_transit_mjd (search back from now)
            min_transit_mjd = Time.now().mjd - max_days_back
            # Get connection to products database
            products_db_conn = ensure_products_db(self.products_db)
            stored_transits = get_calibrator_transits(
                products_db=products_db_conn,
                calibrator_name=calibrator_name,
                min_transit_mjd=min_transit_mjd,
                has_data=True,
            )

            if stored_transits:
                logger.debug(
                    f"Using {len(stored_transits)} stored transit times from database for {calibrator_name}"
                )
                # Convert stored format to expected format
                ra_deg, dec_deg = self._load_radec(calibrator_name)
                results = []

                for stored in stored_transits:
                    # Need to get group files for stored transit
                    # For now, fall back to on-demand calculation if files are needed
                    # But we can return basic transit info from database
                    results.append(
                        {
                            "transit_iso": stored["transit_iso"],
                            "transit_mjd": stored["transit_mjd"],
                            "group_id": stored["group_id"],
                            "group_mid_iso": stored["group_mid_iso"],
                            "delta_minutes": stored["delta_minutes"],
                            "subband_count": 16,  # Assumed from stored data
                            "files": [],  # Will be populated on-demand if needed
                            "days_ago": (Time.now().mjd - stored["transit_mjd"]),
                            "has_ms": False,  # Will be checked on-demand
                            "pb_response": stored["pb_response"],
                            "dec_match": stored["dec_match"],
                        }
                    )

                # If we have enough stored info, return it
                # Otherwise fall through to on-demand calculation
                if len(results) > 0:
                    return results
        except Exception as e:
            logger.debug(
                f"Could not use stored transit times from database: {e}. Calculating on-demand."
            )

        # Fall back to on-demand calculation
        ra_deg, dec_deg = self._load_radec(calibrator_name)
        start_time, end_time, cutoff_time = self._calculate_search_window(max_days_back)

        complete_groups_list = query_subband_groups(
            self.hdf5_db, start_time, end_time, tolerance_s=1.0
        )

        if not complete_groups_list:
            logger.debug(
                f"No complete 16-subband groups found in database for time range "
                f"{start_time} to {end_time}. Consider running index_hdf5_files() "
                f"to index the input directory."
            )
            return []

        transits = previous_transits(ra_deg, start_time=Time.now(), n=max_days_back)
        filelength = 5 * u.min  # Typical observation file length  # pylint: disable=no-member

        return self._process_transits_for_available_data(
            transits,
            calibrator_name,
            dec_deg,
            cutoff_time,
            filelength,
            window_minutes,
        )

    def locate_group(
        self, transit_info: dict, *, dec_tolerance_deg: float = 2.5
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
        groups = query_subband_groups(
            self.hdf5_db,
            transit_info["start_iso"],
            transit_info["end_iso"],
            # 1-second tolerance matches filename precision (YYYY-MM-DDTHH:MM:SS)
            tolerance_s=1.0,
        )

        if not groups:
            return None

        # Return first complete group
        return groups[0] if groups else None

    def convert_group(
        self,
        file_list: List[str],
        output_ms: Path,
        *,
        stage_to_tmpfs: bool = True,
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
            write_ms_from_subbands(file_list, os.fspath(output_ms), scratch_dir=scratch_dir)
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

    def _validate_and_check_existing_ms(
        self,
        calibrator_name: str,
        transit_time: Optional[Time],
        config: GenerateMSConfig,
        progress: ProgressReporter,
    ) -> Optional[CalibratorMSResult]:
        """Validate inputs and check for existing MS.

        Args:
            calibrator_name: Name of calibrator
            transit_time: Optional specific transit time
            config: Generation configuration
            progress: Progress reporter

        Returns:
            CalibratorMSResult if existing MS found, None otherwise
        """
        progress.info("Validating inputs...")
        self._validate_inputs(
            calibrator_name,
            transit_time,
            config.window_minutes,
            config.max_days_back,
        )
        progress.success("Inputs validated")

        if transit_time is not None:
            progress.info("Checking for existing MS for this transit...")
            existing = self.find_existing_ms_for_transit(
                calibrator_name,
                transit_time,
                tolerance_minutes=config.window_minutes / 2,
            )
            if existing:
                progress.success(f"Found existing MS: {existing['ms_path']}")
                return CalibratorMSResult(
                    success=True,
                    ms_path=existing["ms_path"],
                    transit_info=None,
                    group_id=None,
                    already_exists=True,
                    metrics={
                        "exist_reason": "database_query",
                        "status": existing["status"],
                    },
                    progress_summary=progress.get_summary(),
                )
        return None

    def _check_existing_ms_for_transit_info(
        self,
        calibrator_name: str,
        transit_info: dict,
        config: GenerateMSConfig,
        progress: ProgressReporter,
    ) -> Optional[Tuple[dict, List[str]]]:
        """Check for existing MS for transit info.

        Args:
            calibrator_name: Name of calibrator
            transit_info: Transit info dictionary
            config: Generation configuration
            progress: Progress reporter

        Returns:
            Tuple of (transit_info_with_existing, []) if found, None otherwise
        """
        transit_time_obj = Time(transit_info["transit_iso"])
        existing = self.find_existing_ms_for_transit(
            calibrator_name,
            transit_time_obj,
            tolerance_minutes=config.window_minutes / 2,
        )
        if existing:
            progress.success(f"Found existing MS for transit: {existing['ms_path']}")
            return (
                {
                    **transit_info,
                    "existing_ms": existing,
                },
                [],
            )
        return None

    def _find_transit_and_group(
        self,
        calibrator_name: str,
        transit_time: Optional[Time],
        config: GenerateMSConfig,
        progress: ProgressReporter,
    ) -> Tuple[dict, List[str]]:
        """Find transit and locate subband group.

        Args:
            calibrator_name: Name of calibrator
            transit_time: Optional specific transit time
            config: Generation configuration
            progress: Progress reporter

        Returns:
            Tuple of (transit_info, file_list)

        Raises:
            TransitNotFoundError: If no transit found
            GroupNotFoundError: If no complete group found
        """
        progress.info(f"Finding transit for {calibrator_name}...")
        transit_info = self.find_transit(
            calibrator_name,
            transit_time=transit_time,
            window_minutes=config.window_minutes,
            max_days_back=config.max_days_back,
        )

        if not transit_info:
            error_msg = (
                f"No transit found for {calibrator_name} " f"within {config.max_days_back} days"
            )
            progress.error(error_msg)
            raise TransitNotFoundError(error_msg)

        progress.success(f"Found transit: {transit_info['transit_iso']}")

        existing_result = self._check_existing_ms_for_transit_info(
            calibrator_name, transit_info, config, progress
        )
        if existing_result:
            return existing_result

        progress.info("Locating subband group...")
        file_list = self.locate_group(transit_info, dec_tolerance_deg=config.dec_tolerance_deg)

        if not file_list:
            error_msg = "No complete subband group found for transit"
            progress.error(error_msg)
            raise GroupNotFoundError(error_msg)

        progress.success(f"Found {len(file_list)} subband files")
        return transit_info, file_list

    def _handle_existing_ms(
        self,
        ms_path: Path,
        transit_info: dict,
        metrics: dict,
        progress: ProgressReporter,
    ) -> Optional[CalibratorMSResult]:
        """Handle case where MS already exists.

        Args:
            ms_path: MS file path
            transit_info: Transit information dictionary
            metrics: Metrics dictionary to update
            progress: Progress reporter

        Returns:
            CalibratorMSResult if MS exists, None otherwise
        """
        exists, exist_info = self._check_existing_ms(ms_path, transit_info)
        if not exists:
            return None

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

    def _perform_conversion(
        self,
        file_list: List[str],
        ms_path: Path,
        config: GenerateMSConfig,
        progress: ProgressReporter,
        metrics: dict,
    ) -> None:
        """Perform HDF5 to MS conversion.

        Args:
            file_list: List of subband file paths
            ms_path: Output MS file path
            config: Generation configuration
            progress: Progress reporter
            metrics: Metrics dictionary to update
        """
        progress.info(f"Converting {len(file_list)} subbands to MS...")
        convert_start = time.time()

        try:
            self.convert_group(file_list, ms_path, stage_to_tmpfs=config.stage_to_tmpfs)
        except ConversionError:
            raise
        except Exception as e:
            raise ConversionError(f"Conversion failed: {e}") from e

        convert_time = time.time() - convert_start
        progress.success(f"Conversion completed in {convert_time:.1f}s")
        metrics["conversion_time_seconds"] = convert_time

    def _post_process_ms(
        self,
        ms_path: Path,
        transit_info: dict,
        config: GenerateMSConfig,
        progress: ProgressReporter,
        metrics: dict,
    ) -> None:
        """Post-process MS (configure for imaging, register in DB).

        Args:
            ms_path: MS file path
            transit_info: Transit information dictionary
            config: Generation configuration
            progress: Progress reporter
            metrics: Metrics dictionary to update
        """
        if config.configure_for_imaging:
            progress.info("Configuring MS for imaging...")
            configure_ms_for_imaging(os.fspath(ms_path))
            progress.success("MS configured for imaging")
            metrics["configured"] = True

        if config.register_in_db:
            progress.info("Registering MS in products database...")
            self._register_ms_in_db(ms_path, transit_info)
            progress.success("MS registered in database")
            metrics["registered"] = True

    def _execute_conversion_workflow(
        self,
        calibrator_name: str,
        transit_info: dict,
        file_list: List[str],
        config: GenerateMSConfig,
        progress: ProgressReporter,
        metrics: dict,
    ) -> CalibratorMSResult:
        """Execute the conversion workflow.

        Args:
            calibrator_name: Name of calibrator
            transit_info: Transit information dictionary
            file_list: List of subband file paths
            config: Generation configuration
            progress: Progress reporter
            metrics: Metrics dictionary to update

        Returns:
            CalibratorMSResult with conversion results
        """
        ms_path = self._derive_output_path(
            calibrator_name,
            transit_info,
            auto_naming=config.auto_naming,
            output_name=config.output_name,
        )

        progress.info(f"Checking for existing MS: {ms_path}")
        existing_result = self._handle_existing_ms(ms_path, transit_info, metrics, progress)
        if existing_result:
            return existing_result

        self._perform_conversion(file_list, ms_path, config, progress, metrics)
        self._post_process_ms(ms_path, transit_info, config, progress, metrics)

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

    def generate_from_transit(
        self,
        calibrator_name: str,
        transit_time: Optional[Time] = None,
        *,
        window_minutes: int = 60,
        max_days_back: int = 14,
        dec_tolerance_deg: float = 2.5,
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
        config = GenerateMSConfig(
            window_minutes=window_minutes,
            max_days_back=max_days_back,
            dec_tolerance_deg=dec_tolerance_deg,
            auto_naming=auto_naming,
            output_name=output_name,
            configure_for_imaging=configure_for_imaging,
            register_in_db=register_in_db,
            stage_to_tmpfs=stage_to_tmpfs,
        )
        progress = ProgressReporter(verbose=self.verbose)
        metrics = {}

        try:
            existing_result = self._validate_and_check_existing_ms(
                calibrator_name, transit_time, config, progress
            )
            if existing_result:
                return existing_result

            transit_info, file_list = self._find_transit_and_group(
                calibrator_name, transit_time, config, progress
            )

            if "existing_ms" in transit_info:
                existing = transit_info["existing_ms"]
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

            metrics["transit_found"] = True
            metrics["transit_time"] = transit_info["transit_iso"]
            metrics["subbands"] = len(file_list)

            return self._execute_conversion_workflow(
                calibrator_name,
                transit_info,
                file_list,
                config,
                progress,
                metrics,
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
