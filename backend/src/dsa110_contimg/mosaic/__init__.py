"""
Mosaicking module for DSA-110 Continuum Imaging Pipeline.

This module provides a simple, unified mosaicking system with:
- Three clear tiers: Quicklook, Science, Deep
- ABSURD-governed pipeline execution
- Unified database state
- Contract-tested with real FITS files

Architecture:
    tiers.py     - Tier definitions and selection logic
    builder.py   - Core mosaic building function
    qa.py        - Quality assessment checks
    jobs.py      - ABSURD job implementations
    pipeline.py  - Pipeline definitions (nightly, on-demand)
    api.py       - FastAPI endpoints
    schema.py    - Database schema definitions
"""

from .tiers import (
    MosaicTier,
    TierConfig,
    TIER_CONFIGS,
    select_tier_for_request,
    get_tier_config,
)
from .builder import (
    MosaicResult,
    build_mosaic,
    compute_rms,
)
from .qa import (
    QAResult,
    AstrometryResult,
    PhotometryResult,
    ArtifactResult,
    run_qa_checks,
    check_astrometry,
    check_photometry,
    check_artifacts,
)
from .jobs import (
    JobResult,
    MosaicJobConfig,
    MosaicPlanningJob,
    MosaicBuildJob,
    MosaicQAJob,
)
from .pipeline import (
    PipelineResult,
    MosaicPipelineConfig,
    run_nightly_mosaic,
    run_on_demand_mosaic,
    run_mosaic_pipeline,
)
from .schema import (
    MOSAIC_TABLES,
    MOSAIC_INDEXES,
    ensure_mosaic_tables,
    get_mosaic_schema_sql,
)
from .api import (
    router as mosaic_router,
    configure_mosaic_api,
    MosaicRequest,
    MosaicResponse,
    MosaicStatusResponse,
)

__all__ = [
    # Tiers
    "MosaicTier",
    "TierConfig",
    "TIER_CONFIGS",
    "select_tier_for_request",
    "get_tier_config",
    # Builder
    "MosaicResult",
    "build_mosaic",
    "compute_rms",
    # QA
    "QAResult",
    "AstrometryResult",
    "PhotometryResult",
    "ArtifactResult",
    "run_qa_checks",
    "check_astrometry",
    "check_photometry",
    "check_artifacts",
    # Jobs
    "JobResult",
    "MosaicJobConfig",
    "MosaicPlanningJob",
    "MosaicBuildJob",
    "MosaicQAJob",
    # Pipeline
    "PipelineResult",
    "MosaicPipelineConfig",
    "run_nightly_mosaic",
    "run_on_demand_mosaic",
    "run_mosaic_pipeline",
    # Schema
    "MOSAIC_TABLES",
    "MOSAIC_INDEXES",
    "ensure_mosaic_tables",
    "get_mosaic_schema_sql",
    # API
    "mosaic_router",
    "configure_mosaic_api",
    "MosaicRequest",
    "MosaicResponse",
    "MosaicStatusResponse",
]
