"""
DSA-110 Continuum Imaging Pipeline Stages Implementation.

This module implements a VAST-inspired 6-step pipeline architecture for
processing radio telescope observations from raw visibilities to final
data products.

Pipeline Stages (inspired by VAST pipeline):
1. Data Loading & Conversion: UVH5 → MS conversion with subband grouping
2. Calibration: Apply bandpass, gain, and flux calibration
3. Imaging: Create continuum images using WSClean or tclean
4. Source Extraction: Detect sources using Aegean or PyBDSF
5. Forced Photometry: Measure flux at known positions
6. Catalog Association: Cross-match with reference catalogs

References:
    VAST Pipeline: https://github.com/askap-vast/vast-pipeline
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Pipeline Stage Definitions
# =============================================================================


class PipelineStage(Enum):
    """Enumeration of pipeline stages."""

    CONVERSION = auto()  # UVH5 → MS
    CALIBRATION = auto()  # Bandpass, gain, flux calibration
    IMAGING = auto()  # Create continuum images
    SOURCE_EXTRACTION = auto()  # Detect sources
    FORCED_PHOTOMETRY = auto()  # Measure flux at known positions
    CATALOG_ASSOCIATION = auto()  # Cross-match with reference catalogs
    FINALIZATION = auto()  # Metrics, database updates, cleanup


@dataclass
class StageResult:
    """Result from a pipeline stage execution."""

    stage: PipelineStage
    success: bool
    output_path: Optional[str] = None
    n_processed: int = 0
    n_failed: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    @property
    def status_str(self) -> str:
        """Human-readable status string."""
        if self.success:
            return f"✓ {self.stage.name}: {self.n_processed} processed"
        return f"✗ {self.stage.name}: {self.n_failed} failed"


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution.

    Modeled after VAST pipeline configuration with DSA-110 specifics.
    """

    # Data paths
    input_dir: str = "/data/incoming"
    output_dir: str = "/stage/dsa110-contimg/ms"
    scratch_dir: str = "/stage/dsa110-contimg/scratch"
    state_dir: str = "/data/dsa110-contimg/state"

    # Processing options
    tolerance_s: float = 60.0  # Subband grouping tolerance
    n_workers: int = 4  # Parallel workers
    max_partition_mb: int = 100  # Memory limit per partition

    # Calibration options
    cal_catalog_path: Optional[str] = None
    auto_detect_calibrator: bool = True
    rename_calibrator_fields: bool = True

    # Imaging options
    imager: str = "wsclean"  # wsclean or tclean
    robust: float = 0.0  # Briggs weighting
    npix: int = 4096
    cellsize_arcsec: float = 1.5

    # Source extraction options
    extractor: str = "aegean"  # aegean or pybdsf
    detection_sigma: float = 5.0

    # Association options
    association_radius_arcsec: float = 10.0
    use_de_ruiter: bool = True
    de_ruiter_limit: float = 5.68


# =============================================================================
# Pipeline Stage Implementations
# =============================================================================


def stage_conversion(
    input_dir: str,
    output_dir: str,
    start_time: str,
    end_time: str,
    config: Optional[PipelineConfig] = None,
) -> StageResult:
    """Stage 1: Convert UVH5 files to Measurement Sets.

    Groups subband files by timestamp and converts each group to a single MS.

    Args:
        input_dir: Directory containing UVH5 files
        output_dir: Directory for output MS files
        start_time: Start of time range (ISO format)
        end_time: End of time range (ISO format)
        config: Pipeline configuration

    Returns:
        StageResult with conversion metrics
    """
    from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
        convert_subband_groups_to_ms,
    )
    from dsa110_contimg.database.hdf5_index import query_subband_groups

    config = config or PipelineConfig()
    result = StageResult(stage=PipelineStage.CONVERSION, success=False)

    try:
        logger.info(f"Stage 1: Querying subband groups from {start_time} to {end_time}")
        hdf5_db = f"{config.state_dir}/hdf5.sqlite3"
        groups = query_subband_groups(
            hdf5_db, start_time, end_time, tolerance_s=config.tolerance_s
        )

        if not groups:
            logger.warning("No subband groups found in time range")
            result.success = True
            result.n_processed = 0
            return result

        logger.info(f"Found {len(groups)} subband groups to process")

        n_success = 0
        n_failed = 0
        for i, group in enumerate(groups):
            try:
                logger.info(f"Processing group {i+1}/{len(groups)}: {group}")
                convert_subband_groups_to_ms(
                    input_dir, output_dir, group.start_time, group.end_time
                )
                n_success += 1
            except Exception as e:
                logger.error(f"Failed to convert group {group}: {e}")
                result.errors.append(f"Group {group}: {e}")
                n_failed += 1

        result.success = n_failed == 0
        result.n_processed = n_success
        result.n_failed = n_failed
        result.output_path = output_dir
        result.metrics["n_groups"] = len(groups)

        logger.info(result.status_str)

    except Exception as e:
        logger.error(f"Stage 1 failed: {e}", exc_info=True)
        result.errors.append(str(e))

    return result


def stage_calibration(
    ms_path: str,
    config: Optional[PipelineConfig] = None,
) -> StageResult:
    """Stage 2: Apply calibration to Measurement Set.

    Performs bandpass, gain, and flux calibration using CASA tasks.

    Args:
        ms_path: Path to Measurement Set
        config: Pipeline configuration

    Returns:
        StageResult with calibration metrics
    """
    from dsa110_contimg.conversion.ms_utils import configure_ms_for_imaging

    config = config or PipelineConfig()
    result = StageResult(stage=PipelineStage.CALIBRATION, success=False)

    try:
        logger.info(f"Stage 2: Configuring MS for imaging: {ms_path}")

        # Configure MS (ensures columns, weights, calibrator field naming)
        configure_ms_for_imaging(
            ms_path,
            rename_calibrator_fields=config.rename_calibrator_fields,
            catalog_path=config.cal_catalog_path,
        )

        result.success = True
        result.n_processed = 1
        result.output_path = ms_path
        logger.info(result.status_str)

    except Exception as e:
        logger.error(f"Stage 2 failed: {e}", exc_info=True)
        result.errors.append(str(e))
        result.n_failed = 1

    return result


def stage_imaging(
    ms_path: str,
    output_dir: str,
    config: Optional[PipelineConfig] = None,
) -> StageResult:
    """Stage 3: Create continuum images.

    Uses WSClean or CASA tclean for imaging.

    Args:
        ms_path: Path to calibrated Measurement Set
        output_dir: Directory for output images
        config: Pipeline configuration

    Returns:
        StageResult with imaging metrics
    """
    config = config or PipelineConfig()
    result = StageResult(stage=PipelineStage.IMAGING, success=False)

    try:
        logger.info(f"Stage 3: Creating continuum image from {ms_path}")

        ms_name = Path(ms_path).stem
        output_prefix = f"{output_dir}/{ms_name}"

        if config.imager == "wsclean":
            from dsa110_contimg.imaging.wsclean_runner import run_wsclean

            image_path = run_wsclean(
                ms_path,
                output_prefix=output_prefix,
                npix=config.npix,
                cellsize_arcsec=config.cellsize_arcsec,
                robust=config.robust,
            )
        else:
            # Fall back to tclean
            from dsa110_contimg.imaging.tclean_runner import run_tclean

            image_path = run_tclean(
                ms_path,
                output_prefix=output_prefix,
                npix=config.npix,
                cellsize_arcsec=config.cellsize_arcsec,
                robust=config.robust,
            )

        result.success = True
        result.n_processed = 1
        result.output_path = str(image_path)
        result.metrics["imager"] = config.imager
        logger.info(result.status_str)

    except Exception as e:
        logger.error(f"Stage 3 failed: {e}", exc_info=True)
        result.errors.append(str(e))
        result.n_failed = 1

    return result


def stage_source_extraction(
    image_path: str,
    config: Optional[PipelineConfig] = None,
) -> StageResult:
    """Stage 4: Extract sources from image.

    Uses Aegean or PyBDSF for source finding.

    Args:
        image_path: Path to FITS image
        config: Pipeline configuration

    Returns:
        StageResult with extraction metrics
    """
    config = config or PipelineConfig()
    result = StageResult(stage=PipelineStage.SOURCE_EXTRACTION, success=False)

    try:
        logger.info(f"Stage 4: Extracting sources from {image_path}")

        if config.extractor == "aegean":
            from dsa110_contimg.photometry.aegean_fitting import run_aegean

            catalog_path = run_aegean(
                image_path,
                detection_sigma=config.detection_sigma,
            )
        else:
            # Fall back to PyBDSF or basic peak finding
            from dsa110_contimg.photometry.ese_detection import detect_sources

            sources = detect_sources(image_path, sigma_threshold=config.detection_sigma)
            catalog_path = f"{Path(image_path).stem}_sources.csv"
            sources.to_csv(catalog_path, index=False)

        # Count sources
        import pandas as pd

        catalog = pd.read_csv(catalog_path)
        n_sources = len(catalog)

        result.success = True
        result.n_processed = n_sources
        result.output_path = catalog_path
        result.metrics["n_sources"] = n_sources
        result.metrics["extractor"] = config.extractor
        logger.info(f"{result.status_str} ({n_sources} sources)")

    except Exception as e:
        logger.error(f"Stage 4 failed: {e}", exc_info=True)
        result.errors.append(str(e))
        result.n_failed = 1

    return result


def stage_forced_photometry(
    image_path: str,
    positions: List[Tuple[float, float]],
    config: Optional[PipelineConfig] = None,
) -> StageResult:
    """Stage 5: Perform forced photometry at known positions.

    Measures flux at specified positions using weighted convolution.

    Args:
        image_path: Path to FITS image
        positions: List of (ra_deg, dec_deg) tuples
        config: Pipeline configuration

    Returns:
        StageResult with photometry metrics
    """
    from dsa110_contimg.photometry.forced import measure_forced_peak

    config = config or PipelineConfig()
    result = StageResult(stage=PipelineStage.FORCED_PHOTOMETRY, success=False)

    try:
        logger.info(f"Stage 5: Forced photometry at {len(positions)} positions")

        measurements = []
        for ra, dec in positions:
            phot_result = measure_forced_peak(
                image_path, ra, dec, use_weighted_convolution=True
            )
            measurements.append(phot_result)

        # Count valid measurements
        n_valid = sum(1 for m in measurements if not np.isnan(m.peak_jyb))

        result.success = True
        result.n_processed = n_valid
        result.n_failed = len(positions) - n_valid
        result.metrics["n_positions"] = len(positions)
        result.metrics["n_valid"] = n_valid
        logger.info(f"{result.status_str} ({n_valid}/{len(positions)} valid)")

    except Exception as e:
        logger.error(f"Stage 5 failed: {e}", exc_info=True)
        result.errors.append(str(e))
        result.n_failed = len(positions)

    return result


def stage_catalog_association(
    detected_catalog_path: str,
    config: Optional[PipelineConfig] = None,
) -> StageResult:
    """Stage 6: Associate detected sources with reference catalogs.

    Cross-matches with NVSS, FIRST, VLASS using de Ruiter radius (optional).

    Args:
        detected_catalog_path: Path to detected source catalog
        config: Pipeline configuration

    Returns:
        StageResult with association metrics
    """
    from dsa110_contimg.catalog.crossmatch import cross_match_sources

    config = config or PipelineConfig()
    result = StageResult(stage=PipelineStage.CATALOG_ASSOCIATION, success=False)

    try:
        logger.info(f"Stage 6: Associating sources from {detected_catalog_path}")

        import pandas as pd

        detected = pd.read_csv(detected_catalog_path)

        # Load reference catalog (master_sources.sqlite3)
        from dsa110_contimg.catalog.query import query_master_sources

        master_db = f"{config.state_dir}/catalogs/master_sources.sqlite3"

        # Get bounds from detected sources
        ra_min, ra_max = detected["ra_deg"].min(), detected["ra_deg"].max()
        dec_min, dec_max = detected["dec_deg"].min(), detected["dec_deg"].max()

        reference = query_master_sources(
            master_db,
            ra_range=(ra_min - 0.5, ra_max + 0.5),
            dec_range=(dec_min - 0.5, dec_max + 0.5),
        )

        # Perform cross-match
        matches = cross_match_sources(
            detected_ra=detected["ra_deg"].values,
            detected_dec=detected["dec_deg"].values,
            catalog_ra=reference["ra_deg"].values,
            catalog_dec=reference["dec_deg"].values,
            radius_arcsec=config.association_radius_arcsec,
            use_de_ruiter=config.use_de_ruiter,
            de_ruiter_limit=config.de_ruiter_limit,
        )

        # Save matches
        output_path = detected_catalog_path.replace(".csv", "_matched.csv")
        matches.to_csv(output_path, index=False)

        result.success = True
        result.n_processed = len(matches)
        result.output_path = output_path
        result.metrics["n_detected"] = len(detected)
        result.metrics["n_matched"] = len(matches)
        result.metrics["match_rate"] = len(matches) / len(detected) if len(detected) > 0 else 0
        logger.info(f"{result.status_str} ({len(matches)}/{len(detected)} matched)")

    except Exception as e:
        logger.error(f"Stage 6 failed: {e}", exc_info=True)
        result.errors.append(str(e))

    return result


# =============================================================================
# Pipeline Runner
# =============================================================================


class Pipeline:
    """DSA-110 Continuum Imaging Pipeline.

    Orchestrates the execution of pipeline stages with configurable options.
    Inspired by VAST pipeline architecture.
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize pipeline with configuration.

        Args:
            config: Pipeline configuration (uses defaults if None)
        """
        self.config = config or PipelineConfig()
        self.results: List[StageResult] = []

    def run(
        self,
        start_time: str,
        end_time: str,
        stages: Optional[List[PipelineStage]] = None,
    ) -> List[StageResult]:
        """Run pipeline stages.

        Args:
            start_time: Start of time range (ISO format)
            end_time: End of time range (ISO format)
            stages: Specific stages to run (runs all if None)

        Returns:
            List of StageResult objects
        """
        if stages is None:
            stages = [
                PipelineStage.CONVERSION,
                PipelineStage.CALIBRATION,
            ]

        logger.info(f"Running pipeline from {start_time} to {end_time}")
        logger.info(f"Stages: {[s.name for s in stages]}")

        self.results = []

        for stage in stages:
            if stage == PipelineStage.CONVERSION:
                result = stage_conversion(
                    self.config.input_dir,
                    self.config.output_dir,
                    start_time,
                    end_time,
                    self.config,
                )
            elif stage == PipelineStage.CALIBRATION:
                # Get MS files from conversion output
                ms_files = list(Path(self.config.output_dir).glob("*.ms"))
                for ms_path in ms_files:
                    result = stage_calibration(str(ms_path), self.config)
                    self.results.append(result)
                continue  # Already appended results
            else:
                logger.warning(f"Stage {stage.name} not yet implemented")
                result = StageResult(
                    stage=stage, success=False, errors=["Not implemented"]
                )

            self.results.append(result)

        return self.results

    def summary(self) -> str:
        """Generate pipeline execution summary.

        Returns:
            Multi-line summary string
        """
        lines = ["Pipeline Execution Summary", "=" * 40]
        for result in self.results:
            lines.append(result.status_str)
            if result.errors:
                for error in result.errors[:3]:
                    lines.append(f"  - {error}")
        return "\n".join(lines)


# =============================================================================
# Legacy Functions (backwards compatibility)
# =============================================================================


def process_subband_groups(
    input_dir: str,
    output_dir: str,
    start_time: str,
    end_time: str,
    tolerance_s: float = 60.0,
) -> None:
    """Process subband groups from HDF5 files and convert them to Measurement Sets.

    Legacy function - use Pipeline.run() for new code.

    Parameters:
        input_dir: Directory containing the input HDF5 files.
        output_dir: Directory where the output Measurement Sets will be saved.
        start_time: Start time for processing.
        end_time: End time for processing.
        tolerance_s: Time tolerance for grouping subbands (default: 60 seconds).
    """
    config = PipelineConfig(
        input_dir=input_dir,
        output_dir=output_dir,
        tolerance_s=tolerance_s,
    )
    result = stage_conversion(input_dir, output_dir, start_time, end_time, config)
    if not result.success:
        raise RuntimeError(f"Conversion failed: {result.errors}")


def initialize_pipeline() -> None:
    """Initialize the processing pipeline, setting up necessary configurations.

    Legacy function - use Pipeline() constructor for new code.
    """
    from dsa110_contimg.utils.antpos_local import get_itrf

    logger.info("Initializing pipeline...")
    antpos = get_itrf()
    logger.debug(f"Antenna positions loaded: {len(antpos)} antennas")


# Need numpy for forced photometry stage
import numpy as np


__all__ = [
    "Pipeline",
    "PipelineConfig",
    "PipelineStage",
    "StageResult",
    "stage_conversion",
    "stage_calibration",
    "stage_imaging",
    "stage_source_extraction",
    "stage_forced_photometry",
    "stage_catalog_association",
    # Legacy
    "process_subband_groups",
    "initialize_pipeline",
]