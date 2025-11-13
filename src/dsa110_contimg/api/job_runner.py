"""Job runner for background calibration, apply, and imaging tasks.

This module now uses the new pipeline framework for all job execution.
Legacy subprocess-based implementations have been archived to
archive/legacy/api/job_runner_legacy.py.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List

# Import all job functions from the new adapters
from dsa110_contimg.api.job_adapters import (
    run_apply_job,
    run_batch_apply_job,
    run_batch_calibrate_job,
    run_batch_convert_job,
    run_batch_ese_detect_job,
    run_batch_image_job,
    run_batch_photometry_job,
    run_batch_publish_job,
    run_calibrate_job,
    run_convert_job,
    run_ese_detect_job,
    run_image_job,
    run_mosaic_create_job,
)

# Keep helper functions that may still be used
from dsa110_contimg.database.products import ensure_products_db

# Import workflow adapter
from dsa110_contimg.pipeline.adapter import LegacyWorkflowAdapter


def _python_cmd_for_jobs() -> list[str]:
    """Decide how to invoke Python for job subprocesses.

    This is a utility function used by health checks and other diagnostic tools.
    It's not part of the legacy job runner - it's a general utility.

    Priority:
      1) CONTIMG_JOB_PY (absolute path to interpreter)
      2) CONTIMG_CONDA_ENV (use conda run -n <env> python)
      3) sys.executable (current interpreter)
    """
    job_py = os.environ.get("CONTIMG_JOB_PY")
    if job_py:
        return [job_py]
    conda_env = os.environ.get("CONTIMG_CONDA_ENV")
    if conda_env:
        return ["conda", "run", "-n", conda_env, "python"]
    return [sys.executable]


def _src_path_for_env() -> str:
    """Compute repository src path to export into PYTHONPATH for child processes.

    This is a utility function used by health checks and other diagnostic tools.
    It's not part of the legacy job runner - it's a general utility.
    """
    try:
        # job_runner.py → api → dsa110_contimg → src
        src_dir = Path(__file__).resolve().parents[2]
        return str(src_dir)
    except Exception:
        for p in ("/app/src", "/data/dsa110-contimg/src"):
            if Path(p).exists():
                return p
        return ""


def list_caltables(ms_path: str) -> List[str]:
    """Discover calibration tables associated with an MS."""
    from pathlib import Path

    ms_dir = Path(ms_path).parent
    ms_stem = Path(ms_path).stem

    artifacts = []
    for suffix in [".kcal", ".bpcal", ".gpcal", "_kcal", "_bpcal", "_gpcal"]:
        pattern = f"{ms_stem}*{suffix}"
        for p in ms_dir.glob(pattern):
            if p.is_dir() or p.is_file():
                artifacts.append(str(p))
    return artifacts


def run_workflow_job(job_id: int, params: dict, products_db: Path) -> None:
    """Run full pipeline workflow: Convert → Calibrate → Image.

    This function uses the new pipeline framework by default.
    The new framework provides better error handling, retry policies,
    and observability compared to the legacy subprocess-based execution.

    Args:
        job_id: Job ID from database
        params: Job parameters
        products_db: Path to products database
    """
    adapter = LegacyWorkflowAdapter(products_db)
    adapter.run_workflow_job(job_id, params)


# Export all functions
__all__ = [
    "run_convert_job",
    "run_calibrate_job",
    "run_apply_job",
    "run_image_job",
    "run_workflow_job",
    "run_ese_detect_job",
    "run_batch_calibrate_job",
    "run_batch_apply_job",
    "run_batch_convert_job",
    "run_batch_image_job",
    "run_batch_photometry_job",
    "run_batch_publish_job",
    "run_batch_ese_detect_job",
    "run_mosaic_create_job",
    "list_caltables",
    "_python_cmd_for_jobs",  # Utility function for health checks
    "_src_path_for_env",  # Utility function for health checks
]
