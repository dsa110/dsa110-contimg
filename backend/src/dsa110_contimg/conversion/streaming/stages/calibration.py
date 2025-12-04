"""
Calibration stage: Solve and apply calibration to Measurement Sets.

This stage handles:
- Detecting calibrator observations
- Solving for calibration solutions (bandpass, gain)
- Registering solutions in the calibration registry
- Applying calibration to target observations
"""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import SubbandGroup, ConversionResult

logger = logging.getLogger(__name__)


@dataclass
class CalibrationResult:
    """Result of calibration operations."""
    
    success: bool
    ms_path: str
    is_calibrator: bool = False
    calibration_solved: bool = False
    calibration_applied: bool = False
    gaintables: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    elapsed_seconds: float = 0.0


@dataclass
class CalibrationConfig:
    """Configuration for the calibration stage."""

    registry_db: Path
    enable_solving: bool = True
    enable_applying: bool = True
    do_k_calibration: bool = False
    validity_hours: float = 12.0
    use_interpolation: bool = True
    fence_timeout_seconds: float = 60.0
    # Alias for backwards compatibility
    fence_timeout: float = 60.0  # Deprecated, use fence_timeout_seconds

    def __post_init__(self) -> None:
        """Handle deprecated field aliases."""
        # Use fence_timeout if fence_timeout_seconds is default
        if self.fence_timeout_seconds == 60.0 and self.fence_timeout != 60.0:
            self.fence_timeout_seconds = self.fence_timeout


class CalibrationStage:
    """Stage for calibration solving and application.
    
    For calibrator observations:
    - Pre-flags RFI
    - Solves for bandpass and gain
    - Registers solutions in the calibration registry
    
    For target observations:
    - Retrieves appropriate calibration from registry
    - Optionally interpolates between calibration sets
    - Applies calibration to the MS
    
    Example:
        >>> config = CalibrationConfig(
        ...     registry_db=Path("/data/state/db/pipeline.sqlite3"),
        ... )
        >>> stage = CalibrationStage(config)
        >>> result = stage.execute(
        ...     ms_path="/data/ms/2025-10-02T00:12:00.ms",
        ...     mid_mjd=60000.5,
        ... )
    """

    def __init__(self, config: CalibrationConfig) -> None:
        """Initialize the calibration stage.
        
        Args:
            config: Calibration configuration
        """
        self.config = config
        self._hardening_available = False
        
        # Check if hardening module is available
        try:
            from dsa110_contimg.pipeline.hardening import CalibrationFence
            self._hardening_available = True
        except ImportError:
            pass

    def detect_calibrator(self, ms_path: str) -> bool:
        """Detect if an MS contains a calibrator observation.
        
        Args:
            ms_path: Path to the Measurement Set
            
        Returns:
            True if MS contains calibrator data
        """
        try:
            from dsa110_contimg.calibration import has_calibrator
            return has_calibrator(ms_path)
        except (ImportError, Exception) as e:
            logger.debug(f"Calibrator detection failed: {e}")
            return False

    def solve_calibration(
        self,
        ms_path: str,
        mid_mjd: Optional[float] = None,
    ) -> Tuple[bool, Optional[str], List[str]]:
        """Solve for calibration solutions.
        
        Args:
            ms_path: Path to calibrator MS
            mid_mjd: Mid-point MJD of observation
            
        Returns:
            Tuple of (success, error_message, gaintable_paths)
        """
        try:
            from dsa110_contimg.calibration.streaming import solve_calibration_for_ms

            # Use fence for coordination if available
            fence = None
            if self._hardening_available:
                try:
                    from dsa110_contimg.pipeline.hardening import CalibrationFence
                    fence = CalibrationFence(self.config.registry_db)
                except (OSError, sqlite3.Error) as e:
                    logger.warning(f"Failed to initialize calibration fence: {e}")

            if fence is not None:
                with fence.calibrator_lock(ms_path):
                    success, error_msg = solve_calibration_for_ms(
                        ms_path, do_k=self.config.do_k_calibration
                    )
            else:
                success, error_msg = solve_calibration_for_ms(
                    ms_path, do_k=self.config.do_k_calibration
                )

            if success:
                # Get generated gaintables
                gaintables = self._find_gaintables(ms_path)
                return True, None, gaintables
            else:
                return False, error_msg, []

        except Exception as e:
            logger.error(f"Calibration solve failed: {e}", exc_info=True)
            return False, str(e), []

    def _find_gaintables(self, ms_path: str) -> List[str]:
        """Find generated gaintables for an MS.
        
        Args:
            ms_path: Path to the MS
            
        Returns:
            List of gaintable paths
        """
        gaintables = []
        ms_dir = Path(ms_path).parent
        ms_base = Path(ms_path).stem
        
        # Common gaintable suffixes
        suffixes = [".B0", ".G0", ".K0", ".Bf0", ".Gf0"]
        for suffix in suffixes:
            gt_path = ms_dir / f"{ms_base}{suffix}"
            if gt_path.exists():
                gaintables.append(str(gt_path))
                
        return gaintables

    def apply_calibration(
        self,
        ms_path: str,
        mid_mjd: Optional[float] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Apply calibration to a target MS.
        
        Args:
            ms_path: Path to target MS
            mid_mjd: Mid-point MJD of observation
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self.config.enable_applying:
            return True, None

        try:
            # Try interpolated calibration first
            if self.config.use_interpolation and mid_mjd is not None:
                success, error = self._apply_interpolated(ms_path, mid_mjd)
                if success:
                    return True, None

            # Fall back to single-set selection
            return self._apply_single_set(ms_path, mid_mjd)

        except Exception as e:
            logger.error(f"Calibration apply failed: {e}", exc_info=True)
            return False, str(e)

    def _apply_interpolated(
        self, ms_path: str, mid_mjd: float
    ) -> Tuple[bool, Optional[str]]:
        """Apply interpolated calibration between sets.
        
        Args:
            ms_path: Path to target MS
            mid_mjd: Mid-point MJD
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            from dsa110_contimg.pipeline.hardening import get_interpolated_calibration
            from dsa110_contimg.calibration.applycal import (
                apply_interpolated_calibration,
                apply_to_target,
            )

            interp_cal = get_interpolated_calibration(
                self.config.registry_db,
                float(mid_mjd),
                validity_hours=self.config.validity_hours,
            )

            if interp_cal.is_interpolated:
                logger.info(
                    f"Applying interpolated calibration "
                    f"(before={interp_cal.weight_before*100:.1f}%, "
                    f"after={interp_cal.weight_after*100:.1f}%)"
                )
                apply_interpolated_calibration(
                    ms_path,
                    field="",
                    paths_before=interp_cal.paths_before,
                    paths_after=interp_cal.paths_after,
                    weight_before=interp_cal.weight_before,
                    calwt=True,
                )
                return True, None
            elif interp_cal.effective_paths:
                logger.info(f"Using {interp_cal.selection_method} calibration")
                apply_to_target(
                    ms_path,
                    field="",
                    gaintables=interp_cal.effective_paths,
                    calwt=True,
                )
                return True, None
            else:
                return False, "No calibration available"

        except (ImportError, sqlite3.Error, ValueError, OSError) as e:
            logger.debug(f"Interpolated calibration not available: {e}")
            return False, str(e)

    def _apply_single_set(
        self, ms_path: str, mid_mjd: Optional[float]
    ) -> Tuple[bool, Optional[str]]:
        """Apply calibration from a single set.
        
        Args:
            ms_path: Path to target MS
            mid_mjd: Mid-point MJD
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            from dsa110_contimg.database import get_active_applylist
            from dsa110_contimg.calibration.applycal import apply_to_target

            applylist = get_active_applylist(
                self.config.registry_db,
                float(mid_mjd) if mid_mjd is not None else time.time() / 86400.0,
                bidirectional=True,
                validity_hours=self.config.validity_hours,
            )

            if applylist:
                apply_to_target(
                    ms_path, field="", gaintables=applylist, calwt=True
                )
                return True, None
            else:
                return False, "No calibration tables available"

        except Exception as e:
            logger.warning(f"Single-set calibration failed: {e}")
            return False, str(e)

    def execute(
        self,
        ms_path: str,
        mid_mjd: Optional[float] = None,
        is_calibrator: Optional[bool] = None,
    ) -> CalibrationResult:
        """Execute the calibration stage.
        
        Args:
            ms_path: Path to the Measurement Set
            mid_mjd: Mid-point MJD of observation
            is_calibrator: Override calibrator detection
            
        Returns:
            CalibrationResult with status and details
        """
        t0 = time.perf_counter()
        
        # Detect calibrator if not specified
        if is_calibrator is None:
            is_calibrator = self.detect_calibrator(ms_path)

        result = CalibrationResult(
            success=True,
            ms_path=ms_path,
            is_calibrator=is_calibrator,
        )

        if is_calibrator and self.config.enable_solving:
            # Solve calibration for calibrator MS
            success, error, gaintables = self.solve_calibration(ms_path, mid_mjd)
            result.calibration_solved = success
            result.gaintables = gaintables
            if not success:
                result.success = False
                result.error_message = error
        else:
            # Apply calibration to target MS
            success, error = self.apply_calibration(ms_path, mid_mjd)
            result.calibration_applied = success
            if not success:
                # Non-fatal: calibration may not be available yet
                logger.warning(f"Calibration not applied: {error}")

        result.elapsed_seconds = time.perf_counter() - t0
        return result

    def execute_group(
        self,
        group: "SubbandGroup",
        mid_mjd: Optional[float] = None,
    ) -> CalibrationResult:
        """Execute calibration for a converted SubbandGroup.
        
        This is a convenience method for the pipeline - takes a SubbandGroup
        that has already been converted (has ms_path set).
        
        Args:
            group: SubbandGroup with ms_path set from conversion
            mid_mjd: Mid-point MJD (optional, derived from group if not provided)
            
        Returns:
            CalibrationResult with status and details
        """
        from ..models import ProcessingStage
        
        if not group.ms_path:
            return CalibrationResult(
                success=False,
                ms_path="",
                error_message="Group has no MS path - run conversion first",
            )
        
        # Update group stage
        group.stage = ProcessingStage.CALIBRATING
        
        # Use group's calibrator info if available
        is_calibrator = group.has_calibrator
        
        result = self.execute(
            ms_path=str(group.ms_path),
            mid_mjd=mid_mjd,
            is_calibrator=is_calibrator,
        )
        
        # Update group with calibrator info if we detected it
        if is_calibrator is None and result.is_calibrator:
            group.has_calibrator = True
        
        return result
