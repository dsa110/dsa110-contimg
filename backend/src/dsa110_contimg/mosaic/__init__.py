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

from .api import (
    MosaicRequest,
    MosaicResponse,
    MosaicStatusResponse,
    configure_mosaic_api,
)
from .api import (
    router as mosaic_router,
)
from .builder import (
    MosaicResult,
    build_mosaic,
    compute_rms,
)
from .jobs import (
    JobResult,
    MosaicBuildJob,
    MosaicJobConfig,
    MosaicPlanningJob,
    MosaicQAJob,
)
from .orchestrator import (
    MosaicOrchestrator,
    OrchestratorConfig,
)
from .pipeline import (
    MosaicPipelineConfig,
    NightlyMosaicPipeline,
    NotificationConfig,
    OnDemandMosaicPipeline,
    PipelineResult,
    PipelineStatus,
    RetryBackoff,
    # Re-exported from pipeline framework
    RetryPolicy,
    execute_mosaic_pipeline_task,
    run_mosaic_pipeline,
    run_nightly_mosaic,
    run_on_demand_mosaic,
)
from .qa import (
    ArtifactResult,
    AstrometryResult,
    PhotometryResult,
    QAResult,
    check_artifacts,
    check_astrometry,
    check_photometry,
    run_qa_checks,
)
from .schema import (
    MOSAIC_INDEXES,
    MOSAIC_TABLES,
    ensure_mosaic_tables,
    get_mosaic_schema_sql,
)
from .tiers import (
    TIER_CONFIGS,
    MosaicTier,
    TierConfig,
    get_tier_config,
    select_tier_for_request,
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
    "PipelineStatus",
    "MosaicPipelineConfig",
    "NightlyMosaicPipeline",
    "OnDemandMosaicPipeline",
    "run_nightly_mosaic",
    "run_on_demand_mosaic",
    "run_mosaic_pipeline",
    "execute_mosaic_pipeline_task",
    "RetryPolicy",
    "RetryBackoff",
    "NotificationConfig",
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
    # Orchestrator
    "MosaicOrchestrator",
    "OrchestratorConfig",
]
