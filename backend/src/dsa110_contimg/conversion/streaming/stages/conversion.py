"""
Conversion stage: HDF5 subband files → CASA Measurement Set.

This stage handles the core conversion from UVH5 HDF5 format to CASA MS format.
It supports both in-process and subprocess execution modes for memory isolation.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from ..models import SubbandGroup

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    """Result of a conversion operation."""

    success: bool
    ms_path: Optional[str] = None
    group_id: Optional[str] = None
    writer_type: Optional[str] = None
    elapsed_seconds: float = 0.0
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    # Extracted metadata
    ra_deg: Optional[float] = None
    dec_deg: Optional[float] = None
    mid_mjd: Optional[float] = None
    is_calibrator: bool = False


@dataclass
class ConversionConfig:
    """Configuration for the conversion stage."""

    output_dir: Path
    scratch_dir: Path
    input_dir: Optional[Path] = None  # Optional, may be derived from file paths
    products_db: Optional[Path] = None  # Optional database for recording
    expected_subbands: int = 16
    chunk_duration_minutes: float = 5.0
    execution_mode: str = "auto"  # "inprocess", "subprocess", "auto"
    memory_limit_mb: int = 16000
    omp_threads: int = 4


class ConversionStage:
    """Stage for converting HDF5 subband groups to Measurement Sets.

    This stage:
    1. Validates all subband files exist and are readable
    2. Invokes the HDF5 orchestrator to combine subbands
    3. Writes output MS to organized directory structure
    4. Records metrics for monitoring

    Example:
        >>> config = ConversionConfig(
        ...     input_dir=Path("/data/incoming"),
        ...     output_dir=Path("/data/ms"),
        ...     scratch_dir=Path("/stage/scratch"),
        ... )
        >>> stage = ConversionStage(config)
        >>> result = stage.execute(
        ...     group_id="2025-10-02T00:12:00",
        ...     file_paths=["/data/incoming/2025-10-02T00:12:00_sb00.hdf5", ...]
        ... )
        >>> if result.success:
        ...     print(f"Created MS: {result.ms_path}")
    """

    # Regex to extract timestamp from filename: 2025-10-02T00:05:18_sb00.hdf5
    _TIMESTAMP_PATTERN = __import__("re").compile(
        r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})_sb\d{2}\.hdf5$"
    )

    def __init__(self, config: ConversionConfig) -> None:
        """Initialize the conversion stage.

        Args:
            config: Conversion configuration
        """
        self.config = config
        self._execution_module_available = False

        # Check if execution module is available
        try:
            from dsa110_contimg.execution import ExecutionMode
            self._execution_module_available = True
        except ImportError:
            logger.debug("Execution module not available, using fallback")

    def _derive_time_window(
        self, group_id: str, file_paths: List[str]
    ) -> Tuple[str, str]:
        """Derive start/end time window from file paths.

        Subbands arrive at slightly different times, so we extract the
        actual timestamp range from file names.

        Args:
            group_id: Group identifier (used as fallback)
            file_paths: List of subband file paths

        Returns:
            Tuple of (start_time, end_time) in ISO format with T separator
        """
        timestamps = []

        for fp in file_paths:
            basename = os.path.basename(fp)
            match = self._TIMESTAMP_PATTERN.search(basename)
            if match:
                timestamps.append(match.group(1))

        if not timestamps:
            # Fallback to group_id
            logger.debug(f"No timestamps extracted from files, using group_id: {group_id}")
            return group_id, group_id

        # Sort timestamps and return min/max
        timestamps.sort()
        start_time = timestamps[0]
        end_time = timestamps[-1]

        logger.debug(
            f"Derived time window from {len(timestamps)} files: {start_time} to {end_time}"
        )

        return start_time, end_time

    def validate(
        self, group_id: str, file_paths: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for conversion.

        Args:
            group_id: Group identifier
            file_paths: List of subband file paths

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file_paths:
            return False, "No subband files provided"

        if len(file_paths) < self.config.expected_subbands:
            return False, (
                f"Incomplete group: {len(file_paths)}/{self.config.expected_subbands} subbands"
            )

        # Check all files exist
        missing = [p for p in file_paths if not os.path.exists(p)]
        if missing:
            return False, f"Missing files: {missing[:3]}{'...' if len(missing) > 3 else ''}"

        # Check output directory
        if not self.config.output_dir.exists():
            try:
                self.config.output_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                return False, f"Cannot create output directory: {e}"

        return True, None

    def validate_group(self, group: "SubbandGroup") -> Tuple[bool, Optional[str]]:
        """Validate a SubbandGroup for conversion.
        
        Args:
            group: SubbandGroup to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Use the group's own validation
        valid_files, invalid_files = group.validate_files()
        
        if invalid_files:
            return False, f"Invalid/missing files: {invalid_files[:3]}{'...' if len(invalid_files) > 3 else ''}"
        
        if len(valid_files) < group.expected_subbands:
            return False, (
                f"Incomplete group: {len(valid_files)}/{group.expected_subbands} subbands"
            )
        
        # Check output directory
        if not self.config.output_dir.exists():
            try:
                self.config.output_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                return False, f"Cannot create output directory: {e}"
        
        return True, None

    def execute_group(self, group: "SubbandGroup") -> "ConversionResult":
        """Execute conversion for a SubbandGroup.
        
        This is the preferred method - accepts a SubbandGroup and returns
        an updated ConversionResult with the group attached.
        
        Args:
            group: SubbandGroup to convert
            
        Returns:
            ConversionResult with success status, MS path, and updated group
        """
        from ..models import ConversionResult as ModelResult, ConversionMetrics, ProcessingState, ProcessingStage
        
        t0 = time.perf_counter()
        
        # Update group state
        group.state = ProcessingState.CONVERTING
        group.stage = ProcessingStage.VALIDATING
        
        # Validate
        is_valid, error = self.validate_group(group)
        if not is_valid:
            group.set_error("validation_failed", error)
            return ModelResult(
                success=False,
                group=group,
                error_message=error,
            )
        
        # Get file paths
        file_paths = group.file_paths_str
        
        # Derive time window
        start_time, end_time = self._derive_time_window(group.group_id, file_paths)
        
        # Store for fallback
        self._current_file_paths = file_paths
        
        # Execute conversion
        group.stage = ProcessingStage.LOADING
        if self._execution_module_available and self.config.execution_mode != "inprocess":
            legacy_result = self._execute_with_module(group.group_id, start_time, end_time)
        else:
            legacy_result = self._execute_fallback(group.group_id, start_time, end_time)
        
        elapsed = time.perf_counter() - t0
        
        # Convert legacy result to new model
        if legacy_result.success:
            group.set_completed(Path(legacy_result.ms_path))
            group.metrics = legacy_result.metrics
            
            return ModelResult(
                success=True,
                group=group,
                ms_path=Path(legacy_result.ms_path),
                elapsed_seconds=elapsed,
                metrics=ConversionMetrics(
                    total_time_s=elapsed,
                    writer_type=legacy_result.writer_type,
                ),
                ra_deg=legacy_result.ra_deg,
                dec_deg=legacy_result.dec_deg,
                mid_mjd=legacy_result.mid_mjd,
                is_calibrator=legacy_result.is_calibrator,
            )
        else:
            group.set_error("conversion_failed", legacy_result.error_message)
            return ModelResult(
                success=False,
                group=group,
                elapsed_seconds=elapsed,
                error_message=legacy_result.error_message,
            )

    def execute(
        self,
        group_id: str,
        file_paths: List[str],
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> ConversionResult:
        """Execute the conversion stage.

        Args:
            group_id: Group identifier (timestamp-based)
            file_paths: List of subband file paths
            start_time: Optional start time override
            end_time: Optional end time override

        Returns:
            ConversionResult with status and output paths
        """
        t0 = time.perf_counter()

        # Store file_paths for fallback to use
        self._current_file_paths = file_paths

        # Derive time window from file paths for accurate grouping
        # Subbands arrive at slightly different times, so we need a window
        if start_time is None or end_time is None:
            start_time, end_time = self._derive_time_window(group_id, file_paths)

        # Validate inputs
        is_valid, error = self.validate(group_id, file_paths)
        if not is_valid:
            return ConversionResult(
                success=False,
                group_id=group_id,
                error_message=error,
            )

        # Try execution module first, then fallback
        if self._execution_module_available and self.config.execution_mode != "inprocess":
            result = self._execute_with_module(group_id, start_time, end_time)
        else:
            result = self._execute_fallback(group_id, start_time, end_time)

        result.elapsed_seconds = time.perf_counter() - t0
        return result

    def _execute_with_module(
        self, group_id: str, start_time: str, end_time: str
    ) -> ConversionResult:
        """Execute using the execution module for isolation.

        Args:
            group_id: Group identifier
            start_time: Start time string
            end_time: End time string

        Returns:
            ConversionResult
        """
        try:
            from dsa110_contimg.execution import (
                ExecutionMode,
                convert_with_execution,
            )

            # Determine execution mode
            if self.config.execution_mode == "subprocess":
                mode = ExecutionMode.SUBPROCESS
            elif self.config.execution_mode == "inprocess":
                mode = ExecutionMode.INPROCESS
            else:  # auto
                mode = ExecutionMode.INPROCESS

            exec_result = convert_with_execution(
                input_dir=str(self.config.input_dir),
                output_dir=str(self.config.output_dir),
                start_time=start_time,
                end_time=end_time,
                scratch_dir=str(self.config.scratch_dir),
                mode=mode,
                memory_limit_mb=self.config.memory_limit_mb,
                omp_threads=self.config.omp_threads,
            )

            if exec_result.success:
                # Derive MS path from group_id
                base = group_id.replace(":", "-")
                ms_path = str(self.config.output_dir / f"{base}.ms")

                return ConversionResult(
                    success=True,
                    ms_path=ms_path,
                    group_id=group_id,
                    writer_type=exec_result.execution_mode,
                    metrics={
                        "total_time_s": exec_result.metrics.total_time_s if exec_result.metrics else 0,
                        "memory_peak_mb": exec_result.metrics.memory_peak_mb if exec_result.metrics else 0,
                    },
                )
            else:
                return ConversionResult(
                    success=False,
                    group_id=group_id,
                    error_message=exec_result.error_message,
                )

        except Exception as e:
            logger.error(f"Execution module failed: {e}")
            # Fall back to direct execution
            return self._execute_fallback(group_id, start_time, end_time)

    def _execute_fallback(
        self, group_id: str, start_time: str, end_time: str
    ) -> ConversionResult:
        """Execute using direct orchestrator call (fallback).

        Args:
            group_id: Group identifier
            start_time: Start time string
            end_time: End time string

        Returns:
            ConversionResult
        """
        try:
            from dsa110_contimg.conversion import convert_subband_groups_to_ms

            # Determine input_dir - either from config or from file paths
            input_dir = self.config.input_dir
            if input_dir is None:
                # Derive from the current file_paths stored in object
                if hasattr(self, '_current_file_paths') and self._current_file_paths:
                    input_dir = Path(self._current_file_paths[0]).parent
                else:
                    return ConversionResult(
                        success=False,
                        group_id=group_id,
                        error_message="Cannot determine input directory",
                    )

            # Note: The orchestrator signature is:
            # convert_subband_groups_to_ms(input_dir, output_dir, start_time, end_time, ...)
            # It does NOT take scratch_dir or expected_subbands
            results = convert_subband_groups_to_ms(
                input_dir=str(input_dir),
                output_dir=str(self.config.output_dir),
                start_time=start_time,
                end_time=end_time,
            )

            # Results is a dict with 'converted', 'skipped', 'failed' keys
            if results and results.get("converted"):
                # Get the MS path from the first converted group
                # The converted list contains group_ids, we need to derive MS path
                converted_group = results["converted"][0]
                ms_path = str(self.config.output_dir / f"{converted_group}.ms")

                return ConversionResult(
                    success=True,
                    ms_path=ms_path,
                    group_id=group_id,
                    writer_type="fallback",
                )
            else:
                error_msg = "Orchestrator returned no converted results"
                if results and results.get("failed"):
                    error_msg = f"Conversion failed: {results['failed']}"
                return ConversionResult(
                    success=False,
                    group_id=group_id,
                    error_message=error_msg,
                )

        except Exception as e:
            logger.error(f"Conversion failed for {group_id}: {e}", exc_info=True)
            return ConversionResult(
                success=False,
                group_id=group_id,
                error_message=str(e),
            )
