"""
Adapter layer for backward compatibility with existing workflow execution.

Provides a bridge between the new pipeline framework and the existing
`run_workflow_job()` function, allowing gradual migration.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict

from dsa110_contimg.database.jobs import (
    append_job_log,
    ensure_jobs_table,
    update_job_status,
)
from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.state import SQLiteStateRepository
from dsa110_contimg.pipeline.workflows import standard_imaging_workflow

logger = logging.getLogger(__name__)


class LegacyWorkflowAdapter:
    """Adapter to run new pipeline with legacy job tracking.

    This adapter allows the new pipeline framework to work with the
    existing database schema and API, enabling gradual migration.
    """

    def __init__(self, products_db: Path):
        """Initialize adapter.

        Args:
            products_db: Path to products database
        """
        self.products_db = products_db
        self.state_repository = SQLiteStateRepository(products_db)

    def run_workflow_job(self, job_id: int, params: Dict[str, Any]) -> None:
        """Run workflow job using new pipeline framework.

        This method replaces the existing `run_workflow_job()` function
        but maintains the same interface for backward compatibility.

        Args:
            job_id: Job ID from database
            params: Job parameters (legacy format)
        """
        import sqlite3

        conn = sqlite3.connect(str(self.products_db))
        ensure_jobs_table(conn)

        try:
            # Update job status to running
            update_job_status(conn, job_id, "running", started_at=time.time())
            append_job_log(conn, job_id, "=== Starting Pipeline Workflow (New Framework) ===\n")
            append_job_log(
                conn,
                job_id,
                f"Time range: {params['start_time']} to {params['end_time']}\n\n",
            )
            conn.commit()

            # Convert legacy params to PipelineConfig
            config = PipelineConfig.from_dict(params)

            # Extract calibration parameters from legacy params
            # These are used by CalibrationSolveStage
            calibration_params = {}
            calibration_keys = [
                "field",
                "refant",
                "solve_delay",
                "solve_bandpass",
                "solve_gains",
                "model_source",
                "gain_solint",
                "gain_calmode",
                "bp_combine_field",
                "prebp_phase",
                "flag_autocorr",
                "do_flagging",
                "use_existing_tables",
                "existing_k_table",
                "existing_bp_table",
                "existing_g_table",
                "k_combine_spw",
                "k_t_slow",
                "k_t_fast",
                "k_uvrange",
                "k_minsnr",
                "k_skip_slow",
                "gain_t_short",
                "gain_uvrange",
                "gain_minsnr",
                "fast",
            ]
            for key in calibration_keys:
                if key in params:
                    calibration_params[key] = params[key]

            # Create pipeline context
            context = PipelineContext(
                config=config,
                job_id=job_id,
                inputs={
                    "start_time": params["start_time"],
                    "end_time": params["end_time"],
                    "calibration_params": calibration_params,
                },
                state_repository=self.state_repository,
            )

            # Create workflow
            workflow = standard_imaging_workflow(config)

            # Execute pipeline
            result = workflow.execute(context)

            # Update job status based on result
            if result.status.value == "completed":
                # Collect artifacts from outputs
                artifacts = []
                if "ms_path" in result.context.outputs:
                    artifacts.append(result.context.outputs["ms_path"])
                if "image_path" in result.context.outputs:
                    artifacts.append(result.context.outputs["image_path"])

                update_job_status(
                    conn,
                    job_id,
                    "done",
                    finished_at=time.time(),
                    artifacts=json.dumps(artifacts),
                )
                append_job_log(
                    conn,
                    job_id,
                    f"\n✓ Pipeline completed successfully\n"
                    f"Duration: {result.total_duration_seconds:.2f} seconds\n"
                    f"Artifacts: {', '.join(artifacts)}\n",
                )
            elif result.status.value == "partial":
                update_job_status(conn, job_id, "failed", finished_at=time.time())
                append_job_log(
                    conn,
                    job_id,
                    f"\n⚠ Pipeline completed with partial failures\n"
                    f"Duration: {result.total_duration_seconds:.2f} seconds\n",
                )
            else:  # failed
                error_msg = "Pipeline execution failed"
                for stage_name, stage_result in result.stage_results.items():
                    if stage_result.status.value == "failed" and stage_result.error:
                        error_msg = f"Stage '{stage_name}' failed: {stage_result.error}"
                        break

                update_job_status(conn, job_id, "failed", finished_at=time.time())
                append_job_log(
                    conn,
                    job_id,
                    f"\n✗ Pipeline failed: {error_msg}\n"
                    f"Duration: {result.total_duration_seconds:.2f} seconds\n",
                )

            conn.commit()

        except Exception as e:
            logger.exception(f"Workflow job {job_id} failed")
            append_job_log(conn, job_id, f"\nERROR: {e}\n")
            update_job_status(conn, job_id, "failed", finished_at=time.time())
            conn.commit()
            raise

        finally:
            conn.close()
            self.state_repository.close()
