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
from typing import Any, Dict, List, Optional, Tuple

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
        
        # Use group timestamp for start/end if not provided
        if start_time is None:
            start_time = group_id.replace("T", " ")
        if end_time is None:
            end_time = start_time

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

            # Note: The orchestrator signature is:
            # convert_subband_groups_to_ms(input_dir, output_dir, start_time, end_time, ...)
            # It does NOT take scratch_dir or expected_subbands
            results = convert_subband_groups_to_ms(
                input_dir=str(self.config.input_dir),
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
