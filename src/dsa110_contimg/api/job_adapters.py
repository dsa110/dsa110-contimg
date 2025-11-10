"""Job adapters using new pipeline framework.

These adapters replace the legacy subprocess-based job functions with
direct calls to the new pipeline framework stages.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List

import structlog

from dsa110_contimg.database.jobs import (
    append_job_log,
    create_job,
    get_job,
    update_job_status,
)
from dsa110_contimg.database.products import ensure_jobs_table, ensure_products_db
from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages_impl import (
    CalibrationSolveStage,
    CalibrationStage,
    ConversionStage,
    ImagingStage,
)
from dsa110_contimg.pipeline.state import SQLiteStateRepository

logger = structlog.get_logger(__name__)


def _log_to_db(conn, job_id: int, message: str) -> None:
    """Helper to append log message to database."""
    append_job_log(conn, job_id, message)
    conn.commit()


def run_convert_job(job_id: int, params: dict, products_db: Path) -> None:
    """Run conversion job using new pipeline framework.

    Args:
        job_id: Job ID from database
        params: Job parameters
        products_db: Path to products database
    """
    conn = ensure_products_db(products_db)
    ensure_jobs_table(conn)

    try:
        update_job_status(conn, job_id, "running", started_at=time.time())
        _log_to_db(conn, job_id, "=== Starting Conversion (New Pipeline) ===\n")

        # Convert params to PipelineConfig
        config = PipelineConfig.from_dict(params)

        # Create context
        state_repository = SQLiteStateRepository(products_db)
        context = PipelineContext(
            config=config,
            job_id=job_id,
            inputs={
                "start_time": params["start_time"],
                "end_time": params["end_time"],
            },
            state_repository=state_repository,
        )

        # Run conversion stage
        stage = ConversionStage(config)
        is_valid, error_msg = stage.validate(context)
        if not is_valid:
            from dsa110_contimg.utils.exceptions import ValidationError

            raise ValidationError(
                errors=[f"Validation failed: {error_msg}"],
                context={
                    "job_id": job_id,
                    "start_time": params.get("start_time"),
                    "end_time": params.get("end_time"),
                    "stage": "conversion",
                },
                suggestion="Check conversion parameters and input paths",
            )

        _log_to_db(
            conn,
            job_id,
            f"Converting UVH5 → MS: {params['start_time']} to {params['end_time']}\n",
        )
        context = stage.execute(context)

        # Update job with results
        ms_path = context.outputs.get("ms_path")
        if ms_path:
            artifacts = [ms_path]
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE jobs SET artifacts = ?, status = 'done', finished_at = ? WHERE id = ?",
                (json.dumps(artifacts), time.time(), job_id),
            )
            conn.commit()
            _log_to_db(conn, job_id, f"✓ Conversion complete: {ms_path}\n")
        else:
            from dsa110_contimg.utils.exceptions import ConversionError

            raise ConversionError(
                message="Conversion produced no MS file",
                context={
                    "job_id": job_id,
                    "start_time": params.get("start_time"),
                    "end_time": params.get("end_time"),
                },
                suggestion="Check conversion stage output and logs",
            )

    except (
        ValueError,
        RuntimeError,
        OSError,
        FileNotFoundError,
        ValidationError,
        ConversionError,
    ) as e:
        # Catch specific exceptions that can occur during conversion
        logger.exception("Conversion job failed", job_id=job_id, error=str(e))
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, f"ERROR: {str(e)}\n")
        update_job_status(conn, job_id, "failed", finished_at=time.time())
        conn.commit()
    except Exception as e:
        # Catch-all for unexpected exceptions
        logger.exception(
            "Conversion job failed with unexpected error", job_id=job_id, error=str(e)
        )
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, f"ERROR: {str(e)}\n")
        update_job_status(conn, job_id, "failed", finished_at=time.time())
        conn.commit()
    finally:
        conn.close()


def run_calibrate_job(
    job_id: int, ms_path: str, params: dict, products_db: Path
) -> None:
    """Run calibration solve job using new pipeline framework.

    Args:
        job_id: Job ID from database
        ms_path: Path to Measurement Set
        params: Calibration parameters
        products_db: Path to products database
    """
    conn = ensure_products_db(products_db)
    ensure_jobs_table(conn)

    try:
        update_job_status(conn, job_id, "running", started_at=time.time())
        _log_to_db(conn, job_id, "=== Starting Calibration Solve (New Pipeline) ===\n")

        # Convert params to PipelineConfig
        config = PipelineConfig.from_dict(params)

        # Create context with MS path already available
        state_repository = SQLiteStateRepository(products_db)
        context = PipelineContext(
            config=config,
            job_id=job_id,
            inputs={
                "calibration_params": params,
            },
            outputs={
                "ms_path": ms_path,
            },
            state_repository=state_repository,
        )

        # Run calibration solve stage
        stage = CalibrationSolveStage(config)
        is_valid, error_msg = stage.validate(context)
        if not is_valid:
            from dsa110_contimg.utils.exceptions import ValidationError

            raise ValidationError(
                errors=[f"Validation failed: {error_msg}"],
                context={
                    "job_id": job_id,
                    "ms_path": ms_path,
                    "stage": "calibration_solve",
                },
                suggestion="Check calibration parameters and MS path",
            )

        _log_to_db(conn, job_id, f"Solving calibration for: {ms_path}\n")
        context = stage.execute(context)

        # Update job with results
        cal_tables = context.outputs.get("calibration_tables", [])
        if cal_tables:
            artifacts = [ms_path] + cal_tables
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE jobs SET artifacts = ?, status = 'done', finished_at = ? WHERE id = ?",
                (json.dumps(artifacts), time.time(), job_id),
            )
            conn.commit()
            _log_to_db(
                conn,
                job_id,
                f"✓ Calibration solve complete. Generated {len(cal_tables)} tables.\n",
            )
        else:
            _log_to_db(
                conn,
                job_id,
                "⚠ No calibration tables generated (may have used existing tables)\n",
            )
            update_job_status(conn, job_id, "done", finished_at=time.time())
            conn.commit()

    except (ValueError, RuntimeError, OSError, FileNotFoundError) as e:
        # Catch specific exceptions that can occur during calibration
        logger.exception("Calibration solve job failed", job_id=job_id, error=str(e))
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, f"ERROR: {str(e)}\n")
        update_job_status(conn, job_id, "failed", finished_at=time.time())
        conn.commit()
    except Exception as e:
        # Catch-all for unexpected exceptions
        logger.exception(
            "Calibration solve job failed with unexpected error",
            job_id=job_id,
            error=str(e),
        )
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, f"ERROR: {str(e)}\n")
        update_job_status(conn, job_id, "failed", finished_at=time.time())
        conn.commit()
    finally:
        conn.close()


def run_apply_job(job_id: int, ms_path: str, params: dict, products_db: Path) -> None:
    """Run calibration apply job using new pipeline framework.

    Args:
        job_id: Job ID from database
        ms_path: Path to Measurement Set
        params: Apply parameters (gaintables)
        products_db: Path to products database
    """
    conn = ensure_products_db(products_db)
    ensure_jobs_table(conn)

    try:
        update_job_status(conn, job_id, "running", started_at=time.time())
        _log_to_db(conn, job_id, "=== Starting Calibration Apply (New Pipeline) ===\n")

        # Convert params to PipelineConfig
        config = PipelineConfig.from_dict(params)

        # Create context
        state_repository = SQLiteStateRepository(products_db)
        context = PipelineContext(
            config=config,
            job_id=job_id,
            outputs={
                "ms_path": ms_path,
            },
            state_repository=state_repository,
        )

        # Run calibration apply stage
        stage = CalibrationStage(config)
        is_valid, error_msg = stage.validate(context)
        if not is_valid:
            from dsa110_contimg.utils.exceptions import ValidationError

            raise ValidationError(
                errors=[f"Validation failed: {error_msg}"],
                context={
                    "job_id": job_id,
                    "ms_path": ms_path,
                    "stage": "calibration_apply",
                },
                suggestion="Check calibration parameters and MS path",
            )

        _log_to_db(conn, job_id, f"Applying calibration to: {ms_path}\n")
        context = stage.execute(context)

        # Update job status
        update_job_status(conn, job_id, "done", finished_at=time.time())
        artifacts = [ms_path]
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE jobs SET artifacts = ? WHERE id = ?",
            (json.dumps(artifacts), job_id),
        )
        conn.commit()
        _log_to_db(conn, job_id, "✓ Calibration apply complete\n")

    except (ValueError, RuntimeError, OSError, FileNotFoundError) as e:
        # Catch specific exceptions that can occur during calibration apply
        logger.exception("Calibration apply job failed", job_id=job_id, error=str(e))
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, f"ERROR: {str(e)}\n")
        update_job_status(conn, job_id, "failed", finished_at=time.time())
        conn.commit()
    except Exception as e:
        # Catch-all for unexpected exceptions
        logger.exception(
            "Calibration apply job failed with unexpected error",
            job_id=job_id,
            error=str(e),
        )
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, f"ERROR: {str(e)}\n")
        update_job_status(conn, job_id, "failed", finished_at=time.time())
        conn.commit()
    finally:
        conn.close()


def run_image_job(job_id: int, ms_path: str, params: dict, products_db: Path) -> None:
    """Run imaging job using new pipeline framework.

    Args:
        job_id: Job ID from database
        ms_path: Path to Measurement Set
        params: Imaging parameters
        products_db: Path to products database
    """
    conn = ensure_products_db(products_db)
    ensure_jobs_table(conn)

    try:
        update_job_status(conn, job_id, "running", started_at=time.time())
        _log_to_db(conn, job_id, "=== Starting Imaging (New Pipeline) ===\n")

        # Convert params to PipelineConfig
        config = PipelineConfig.from_dict(params)

        # Create context
        state_repository = SQLiteStateRepository(products_db)
        context = PipelineContext(
            config=config,
            job_id=job_id,
            outputs={
                "ms_path": ms_path,
            },
            state_repository=state_repository,
        )

        # Run imaging stage
        stage = ImagingStage(config)
        is_valid, error_msg = stage.validate(context)
        if not is_valid:
            from dsa110_contimg.utils.exceptions import ValidationError

            raise ValidationError(
                errors=[f"Validation failed: {error_msg}"],
                context={"job_id": job_id, "ms_path": ms_path, "stage": "imaging"},
                suggestion="Check imaging parameters and MS path",
            )

        _log_to_db(conn, job_id, f"Imaging: {ms_path}\n")
        context = stage.execute(context)

        # Update job with results
        image_path = context.outputs.get("image_path")
        if image_path:
            artifacts = [ms_path, image_path]
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE jobs SET artifacts = ?, status = 'done', finished_at = ? WHERE id = ?",
                (json.dumps(artifacts), time.time(), job_id),
            )
            conn.commit()
            _log_to_db(conn, job_id, f"✓ Imaging complete: {image_path}\n")
        else:
            from dsa110_contimg.utils.exceptions import ImagingError

            raise ImagingError(
                message="Imaging produced no image file",
                context={"job_id": job_id, "ms_path": ms_path},
                suggestion="Check imaging stage output and logs",
            )

    except (ValueError, RuntimeError, OSError, FileNotFoundError, ImagingError) as e:
        # Catch specific exceptions that can occur during imaging
        logger.exception("Imaging job failed", job_id=job_id, error=str(e))
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, f"ERROR: {str(e)}\n")
        update_job_status(conn, job_id, "failed", finished_at=time.time())
        conn.commit()
    finally:
        conn.close()


def run_batch_calibrate_job(
    batch_id: int, ms_paths: List[str], params: dict, products_db: Path
) -> None:
    """Process batch calibration job using new pipeline framework.

    Args:
        batch_id: Batch job ID
        ms_paths: List of MS paths to process
        params: Calibration parameters
        products_db: Path to products database
    """
    from dsa110_contimg.api.batch_jobs import update_batch_item

    conn = ensure_products_db(products_db)

    try:
        conn.execute(
            "UPDATE batch_jobs SET status = 'running' WHERE id = ?", (batch_id,)
        )
        conn.commit()

        for ms_path in ms_paths:
            # Check if batch was cancelled
            cursor = conn.execute(
                "SELECT status FROM batch_jobs WHERE id = ?", (batch_id,)
            )
            batch_status = cursor.fetchone()[0]
            if batch_status == "cancelled":
                break

            try:
                # Create individual calibration job
                individual_job_id = create_job(conn, "calibrate", ms_path, params)
                conn.commit()

                # Update batch item status
                update_batch_item(conn, batch_id, ms_path, individual_job_id, "running")
                conn.commit()

                # Run calibration job using new framework
                run_calibrate_job(individual_job_id, ms_path, params, products_db)

                # Check job result
                jd = get_job(conn, individual_job_id)
                if jd["status"] == "done":
                    update_batch_item(
                        conn, batch_id, ms_path, individual_job_id, "done"
                    )
                else:
                    update_batch_item(
                        conn,
                        batch_id,
                        ms_path,
                        individual_job_id,
                        "failed",
                        error=jd.get("logs", "")[-500:],
                    )
                conn.commit()

            except Exception as e:
                update_batch_item(conn, batch_id, ms_path, None, "failed", error=str(e))
                conn.commit()

    except Exception as e:
        conn = ensure_products_db(products_db)
        conn.execute(
            "UPDATE batch_jobs SET status = 'failed' WHERE id = ?", (batch_id,)
        )
        conn.commit()
    finally:
        conn.close()


def run_batch_apply_job(
    batch_id: int, ms_paths: List[str], params: dict, products_db: Path
) -> None:
    """Process batch apply job using new pipeline framework.

    Args:
        batch_id: Batch job ID
        ms_paths: List of MS paths to process
        params: Apply parameters
        products_db: Path to products database
    """
    from dsa110_contimg.api.batch_jobs import update_batch_item

    conn = ensure_products_db(products_db)

    try:
        conn.execute(
            "UPDATE batch_jobs SET status = 'running' WHERE id = ?", (batch_id,)
        )
        conn.commit()

        for ms_path in ms_paths:
            cursor = conn.execute(
                "SELECT status FROM batch_jobs WHERE id = ?", (batch_id,)
            )
            batch_status = cursor.fetchone()[0]
            if batch_status == "cancelled":
                break

            try:
                individual_job_id = create_job(conn, "apply", ms_path, params)
                conn.commit()

                update_batch_item(conn, batch_id, ms_path, individual_job_id, "running")
                conn.commit()

                run_apply_job(individual_job_id, ms_path, params, products_db)

                jd = get_job(conn, individual_job_id)
                if jd["status"] == "done":
                    update_batch_item(
                        conn, batch_id, ms_path, individual_job_id, "done"
                    )
                else:
                    update_batch_item(
                        conn,
                        batch_id,
                        ms_path,
                        individual_job_id,
                        "failed",
                        error=jd.get("logs", "")[-500:],
                    )
                conn.commit()

            except Exception as e:
                update_batch_item(conn, batch_id, ms_path, None, "failed", error=str(e))
                conn.commit()

    except Exception as e:
        conn = ensure_products_db(products_db)
        conn.execute(
            "UPDATE batch_jobs SET status = 'failed' WHERE id = ?", (batch_id,)
        )
        conn.commit()
    finally:
        conn.close()


def run_batch_image_job(
    batch_id: int, ms_paths: List[str], params: dict, products_db: Path
) -> None:
    """Process batch imaging job using new pipeline framework.

    Args:
        batch_id: Batch job ID
        ms_paths: List of MS paths to process
        params: Imaging parameters
        products_db: Path to products database
    """
    from dsa110_contimg.api.batch_jobs import update_batch_item

    conn = ensure_products_db(products_db)

    try:
        conn.execute(
            "UPDATE batch_jobs SET status = 'running' WHERE id = ?", (batch_id,)
        )
        conn.commit()

        for ms_path in ms_paths:
            cursor = conn.execute(
                "SELECT status FROM batch_jobs WHERE id = ?", (batch_id,)
            )
            batch_status = cursor.fetchone()[0]
            if batch_status == "cancelled":
                break

            try:
                individual_job_id = create_job(conn, "image", ms_path, params)
                conn.commit()

                update_batch_item(conn, batch_id, ms_path, individual_job_id, "running")
                conn.commit()

                run_image_job(individual_job_id, ms_path, params, products_db)

                jd = get_job(conn, individual_job_id)
                if jd["status"] == "done":
                    update_batch_item(
                        conn, batch_id, ms_path, individual_job_id, "done"
                    )
                else:
                    update_batch_item(
                        conn,
                        batch_id,
                        ms_path,
                        individual_job_id,
                        "failed",
                        error=jd.get("logs", "")[-500:],
                    )
                conn.commit()

            except Exception as e:
                update_batch_item(conn, batch_id, ms_path, None, "failed", error=str(e))
                conn.commit()

    except Exception as e:
        conn = ensure_products_db(products_db)
        conn.execute(
            "UPDATE batch_jobs SET status = 'failed' WHERE id = ?", (batch_id,)
        )
        conn.commit()
    finally:
        conn.close()
