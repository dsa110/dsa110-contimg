"""Job adapters using new pipeline framework.

These adapters replace the legacy subprocess-based job functions with
direct calls to the new pipeline framework stages.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import List

import structlog

from dsa110_contimg.database.jobs import (
    append_job_log,
    create_job,
    ensure_jobs_table,
    get_job,
    update_job_status,
)
from dsa110_contimg.database.products import ensure_products_db, photometry_insert
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
        logger.exception("Conversion job failed with unexpected error", job_id=job_id, error=str(e))
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, f"ERROR: {str(e)}\n")
        update_job_status(conn, job_id, "failed", finished_at=time.time())
        conn.commit()
    finally:
        conn.close()


def run_calibrate_job(job_id: int, ms_path: str, params: dict, products_db: Path) -> None:
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
        conn.execute("UPDATE batch_jobs SET status = 'running' WHERE id = ?", (batch_id,))
        conn.commit()

        for ms_path in ms_paths:
            # Check if batch was cancelled
            cursor = conn.execute("SELECT status FROM batch_jobs WHERE id = ?", (batch_id,))
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
                    update_batch_item(conn, batch_id, ms_path, individual_job_id, "done")
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

    except Exception:
        conn = ensure_products_db(products_db)
        conn.execute("UPDATE batch_jobs SET status = 'failed' WHERE id = ?", (batch_id,))
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
        conn.execute("UPDATE batch_jobs SET status = 'running' WHERE id = ?", (batch_id,))
        conn.commit()

        for ms_path in ms_paths:
            cursor = conn.execute("SELECT status FROM batch_jobs WHERE id = ?", (batch_id,))
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
                    update_batch_item(conn, batch_id, ms_path, individual_job_id, "done")
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

    except Exception:
        conn = ensure_products_db(products_db)
        conn.execute("UPDATE batch_jobs SET status = 'failed' WHERE id = ?", (batch_id,))
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
        conn.execute("UPDATE batch_jobs SET status = 'running' WHERE id = ?", (batch_id,))
        conn.commit()

        for ms_path in ms_paths:
            cursor = conn.execute("SELECT status FROM batch_jobs WHERE id = ?", (batch_id,))
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
                    update_batch_item(conn, batch_id, ms_path, individual_job_id, "done")
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

    except Exception:
        conn = ensure_products_db(products_db)
        conn.execute("UPDATE batch_jobs SET status = 'failed' WHERE id = ?", (batch_id,))
        conn.commit()
    finally:
        conn.close()


def run_batch_convert_job(
    batch_id: int, time_windows: List[dict], params: dict, products_db: Path
) -> None:
    """Process batch conversion job using new pipeline framework.

    Args:
        batch_id: Batch job ID
        time_windows: List of time window dicts with "start_time" and "end_time"
        params: Conversion parameters (shared for all windows)
        products_db: Path to products database
    """
    from dsa110_contimg.api.batch_jobs import update_batch_conversion_item

    conn = ensure_products_db(products_db)

    try:
        conn.execute("UPDATE batch_jobs SET status = 'running' WHERE id = ?", (batch_id,))
        conn.commit()

        for tw in time_windows:
            # Check if batch was cancelled
            cursor = conn.execute("SELECT status FROM batch_jobs WHERE id = ?", (batch_id,))
            batch_status = cursor.fetchone()[0]
            if batch_status == "cancelled":
                break

            time_window_id = f"time_window_{tw['start_time']}_{tw['end_time']}"
            start_time = tw["start_time"]
            end_time = tw["end_time"]

            try:
                # Create conversion params for this time window
                conversion_params = params.copy()
                conversion_params["start_time"] = start_time
                conversion_params["end_time"] = end_time

                # Create individual conversion job
                # Use placeholder ms_path since conversion doesn't have MS yet
                placeholder_ms_path = f"conversion_{start_time}_{end_time}"
                individual_job_id = create_job(
                    conn, "convert", placeholder_ms_path, conversion_params
                )
                conn.commit()

                # Update batch item status
                update_batch_conversion_item(
                    conn, batch_id, time_window_id, individual_job_id, "running"
                )
                conn.commit()

                # Run conversion job using new framework
                run_convert_job(individual_job_id, conversion_params, products_db)

                # Check job result
                jd = get_job(conn, individual_job_id)
                if jd["status"] == "done":
                    update_batch_conversion_item(
                        conn, batch_id, time_window_id, individual_job_id, "done"
                    )
                else:
                    update_batch_conversion_item(
                        conn,
                        batch_id,
                        time_window_id,
                        individual_job_id,
                        "failed",
                        error=jd.get("logs", "")[-500:] if jd.get("logs") else "Conversion failed",
                    )
                conn.commit()

            except Exception as e:
                update_batch_conversion_item(
                    conn, batch_id, time_window_id, None, "failed", error=str(e)
                )
                conn.commit()

    except Exception:
        conn = ensure_products_db(products_db)
        conn.execute("UPDATE batch_jobs SET status = 'failed' WHERE id = ?", (batch_id,))
        conn.commit()
    finally:
        conn.close()


def run_mosaic_create_job(job_id: int, params: dict, products_db: Path) -> None:
    """Run mosaic creation job using MosaicOrchestrator.

    Args:
        job_id: Job ID from database
        params: Job parameters containing:
            - calibrator_name: Optional[str] (for calibrator-centered)
            - start_time: Optional[str] (for time-window)
            - end_time: Optional[str] (for time-window)
            - timespan_minutes: int (default: 50)
            - wait_for_published: bool (default: True)
        products_db: Path to products database
    """
    from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

    conn = ensure_products_db(products_db)
    ensure_jobs_table(conn)

    try:
        update_job_status(conn, job_id, "running", started_at=time.time())
        _log_to_db(conn, job_id, "=== Starting Mosaic Creation ===\n")

        # Initialize orchestrator
        orchestrator = MosaicOrchestrator(products_db_path=products_db)

        calibrator_name = params.get("calibrator_name")
        start_time = params.get("start_time")
        end_time = params.get("end_time")
        timespan_minutes = params.get("timespan_minutes", 50)
        wait_for_published = params.get("wait_for_published", True)

        # Determine which method to call
        if calibrator_name:
            _log_to_db(
                conn,
                job_id,
                f"Creating mosaic centered on calibrator: {calibrator_name}\n",
            )
            published_path = orchestrator.create_mosaic_centered_on_calibrator(
                calibrator_name=calibrator_name,
                timespan_minutes=timespan_minutes,
                wait_for_published=wait_for_published,
            )
            group_id = f"mosaic_{calibrator_name}"
        elif start_time and end_time:
            _log_to_db(
                conn,
                job_id,
                f"Creating mosaic for time window: {start_time} to {end_time}\n",
            )
            published_path = orchestrator.create_mosaic_in_time_window(
                start_time=start_time,
                end_time=end_time,
                wait_for_published=wait_for_published,
            )
            # Extract group_id from start_time
            group_id = f"mosaic_{start_time.replace(':', '-').replace('.', '-').replace('T', '_')}"
        else:
            raise ValueError("Either calibrator_name or (start_time and end_time) must be provided")

        if published_path:
            artifacts = [published_path]
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE jobs SET artifacts = ?, status = 'done', finished_at = ? WHERE id = ?",
                (json.dumps(artifacts), time.time(), job_id),
            )
            conn.commit()
            _log_to_db(conn, job_id, f"✓ Mosaic creation complete: {published_path}\n")
            # Store group_id in job params for reference
            params["group_id"] = group_id
            cursor.execute(
                "UPDATE jobs SET params = ? WHERE id = ?",
                (json.dumps(params), job_id),
            )
            conn.commit()
        else:
            raise RuntimeError("Mosaic creation failed - no path returned")

    except (ValueError, RuntimeError, OSError, FileNotFoundError) as e:
        logger.exception("Mosaic creation job failed", job_id=job_id, error=str(e))
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, f"ERROR: {str(e)}\n")
        update_job_status(conn, job_id, "failed", finished_at=time.time())
        conn.commit()
    except Exception as e:
        logger.exception(
            "Mosaic creation job failed with unexpected error",
            job_id=job_id,
            error=str(e),
        )
        conn = ensure_products_db(products_db)
        append_job_log(conn, job_id, f"ERROR: {str(e)}\n")
        update_job_status(conn, job_id, "failed", finished_at=time.time())
        conn.commit()
    finally:
        conn.close()


def run_batch_publish_job(
    batch_id: int, data_ids: List[str], params: dict, products_db: Path
) -> None:
    """Process batch publish job.

    Args:
        batch_id: Batch job ID
        data_ids: List of data instance IDs to publish
        params: Publish parameters (e.g., products_base)
        products_db: Path to products database
    """
    from dsa110_contimg.api.batch_jobs import update_batch_item
    from dsa110_contimg.database.data_registry import (
        ensure_data_registry_db,
        get_data,
        publish_data_manual,
    )

    conn = ensure_products_db(products_db)
    registry_conn = ensure_data_registry_db(products_db)

    try:
        conn.execute("UPDATE batch_jobs SET status = 'running' WHERE id = ?", (batch_id,))
        conn.commit()

        products_base = params.get("products_base")
        if products_base:
            products_base = Path(products_base)

        for data_id in data_ids:
            # Check if batch was cancelled
            cursor = conn.execute("SELECT status FROM batch_jobs WHERE id = ?", (batch_id,))
            batch_status = cursor.fetchone()[0]
            if batch_status == "cancelled":
                break

            try:
                # Update batch item status
                update_batch_item(conn, batch_id, data_id, None, "running")
                conn.commit()

                # Publish data
                success = publish_data_manual(registry_conn, data_id, products_base=products_base)

                if success:
                    get_data(registry_conn, data_id)
                    update_batch_item(conn, batch_id, data_id, None, "done")
                else:
                    record = get_data(registry_conn, data_id)
                    error_msg = (
                        getattr(record, "publish_error", None) if record else "Publish failed"
                    )
                    update_batch_item(conn, batch_id, data_id, None, "failed", error=error_msg)
                conn.commit()

            except Exception as e:
                update_batch_item(conn, batch_id, data_id, None, "failed", error=str(e))
                conn.commit()

    except Exception:
        conn = ensure_products_db(products_db)
        conn.execute("UPDATE batch_jobs SET status = 'failed' WHERE id = ?", (batch_id,))
        conn.commit()
    finally:
        conn.close()
        registry_conn.close()


def run_batch_photometry_job(
    batch_id: int,
    fits_paths: List[str],
    coordinates: List[dict],
    params: dict,
    products_db: Path,
) -> None:
    """Process batch photometry job.

    Args:
        batch_id: Batch job ID
        fits_paths: List of FITS image paths to process
        coordinates: List of coordinate dicts with ra_deg and dec_deg
        params: Photometry parameters (box_size_pix, annulus_pix, use_aegean, normalize)
        products_db: Path to products database
    """
    from dsa110_contimg.api.batch_jobs import update_batch_item
    from dsa110_contimg.photometry.forced import measure_forced_peak
    from dsa110_contimg.photometry.normalize import (
        compute_ensemble_correction,
        normalize_measurement,
        query_reference_sources,
    )

    conn = ensure_products_db(products_db)

    def _source_id_for_coord(coord: dict) -> str:
        ra_sec = int(coord["ra_deg"] * 3600)
        dec_sec = int(coord["dec_deg"] * 3600)
        ra_h = ra_sec // 3600
        ra_m = (ra_sec % 3600) // 60
        ra_s = ra_sec % 60
        dec_d = abs(dec_sec) // 3600
        dec_m = (abs(dec_sec) % 3600) // 60
        dec_s = abs(dec_sec) % 60
        dec_sign = "+" if coord["dec_deg"] >= 0 else "-"
        return f"J{ra_h:02d}{ra_m:02d}{ra_s:02d}{dec_sign}{dec_d:02d}{dec_m:02d}{dec_s:02d}"

    try:
        conn.execute("UPDATE batch_jobs SET status = 'running' WHERE id = ?", (batch_id,))
        conn.commit()

        master_sources_db = Path(
            os.getenv("MASTER_SOURCES_DB", str(products_db.parent / "master_sources.sqlite3"))
        )
        max_workers = params.get("max_workers") or min(8, (os.cpu_count() or 4))
        logger.info(
            "batch_photometry_start",
            batch_id=batch_id,
            fits=len(fits_paths),
            coords=len(coordinates),
            max_workers=max_workers,
            normalize=params.get("normalize", False),
        )

        for fits_path in fits_paths:
            # Check if batch was cancelled
            cursor = conn.execute("SELECT status FROM batch_jobs WHERE id = ?", (batch_id,))
            batch_status = cursor.fetchone()[0]
            if batch_status == "cancelled":
                break

            # Compute normalization correction if needed
            correction = None
            ref_sources = []
            if params.get("normalize", False):
                try:
                    # Use first coordinate as field center
                    ra_center = coordinates[0]["ra_deg"]
                    dec_center = coordinates[0]["dec_deg"]
                    ref_sources = query_reference_sources(
                        master_sources_db,
                        ra_center,
                        dec_center,
                        fov_radius_deg=params.get("fov_radius_deg", 1.5),
                        min_snr=params.get("min_snr", 50.0),
                        max_sources=params.get("max_sources", 20),
                    )
                    if ref_sources:
                        correction = compute_ensemble_correction(
                            fits_path,
                            ref_sources,
                            box_size_pix=params.get("box_size_pix", 5),
                            annulus_pix=params.get("annulus_pix", (12, 20)),
                            max_deviation_sigma=params.get("max_deviation_sigma", 3.0),
                        )
                except Exception as e:
                    structlog.get_logger(__name__).warning(
                        "Failed to compute normalization correction", error=str(e)
                    )

            def _measure_single(coord: dict):
                if params.get("use_aegean", False):
                    from dsa110_contimg.photometry.aegean_fitting import measure_with_aegean

                    res_local = measure_with_aegean(
                        fits_path,
                        coord["ra_deg"],
                        coord["dec_deg"],
                        use_prioritized=params.get("aegean_prioritized", False),
                        negative=params.get("aegean_negative", False),
                    )
                    raw_flux = res_local.peak_flux_jy
                    raw_error = res_local.err_peak_flux_jy
                else:
                    res_local = measure_forced_peak(
                        fits_path,
                        coord["ra_deg"],
                        coord["dec_deg"],
                        box_size_pix=params.get("box_size_pix", 5),
                        annulus_pix=params.get("annulus_pix", (12, 20)),
                        noise_map_path=params.get("noise_map_path"),
                        background_map_path=params.get("background_map_path"),
                        nbeam=params.get("nbeam", 3.0),
                        use_weighted_convolution=params.get("use_weighted_convolution", True),
                    )
                    raw_flux = res_local.peak_jyb
                    raw_error = res_local.peak_err_jyb

                # Apply normalization if requested and correction available
                if params.get("normalize", False) and correction:
                    normalized_flux, normalized_error = normalize_measurement(
                        raw_flux, raw_error, correction
                    )
                else:
                    normalized_flux = raw_flux
                    normalized_error = raw_error

                nvss_flux_mjy = None
                if params.get("normalize", False) and correction and ref_sources:
                    try:
                        from astropy import coordinates as acoords

                        target_coord = acoords.SkyCoord(
                            coord["ra_deg"], coord["dec_deg"], unit="deg", frame="icrs"
                        )
                        min_sep = None
                        closest_source = None
                        for ref in ref_sources:
                            ref_coord = acoords.SkyCoord(
                                ref["ra_deg"], ref["dec_deg"], unit="deg", frame="icrs"
                            )
                            sep = target_coord.separation(ref_coord).arcsec
                            if min_sep is None or sep < min_sep:
                                min_sep = sep
                                closest_source = ref
                        if closest_source and min_sep < 5.0:
                            nvss_flux_mjy = closest_source.get("flux_mjy")
                    except Exception:
                        pass

                return {
                    "raw_flux": raw_flux,
                    "raw_error": raw_error,
                    "normalized_flux": normalized_flux,
                    "normalized_error": normalized_error,
                    "nvss_flux_mjy": nvss_flux_mjy,
                }

            futures = {}
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for coord in coordinates:
                    item_id = f"{fits_path}:{coord['ra_deg']}:{coord['dec_deg']}"
                    update_batch_item(conn, batch_id, item_id, None, "running")
                    futures[executor.submit(_measure_single, coord)] = (coord, item_id)
                conn.commit()

                for future in as_completed(futures):
                    coord, item_id = futures[future]
                    try:
                        measurement = future.result()
                        source_id = _source_id_for_coord(coord)
                        measured_at = time.time()

                        photometry_insert(
                            conn,
                            image_path=fits_path,
                            ra_deg=coord["ra_deg"],
                            dec_deg=coord["dec_deg"],
                            nvss_flux_mjy=measurement.get("nvss_flux_mjy"),
                            peak_jyb=measurement["normalized_flux"],
                            peak_err_jyb=measurement["normalized_error"],
                            flux_jy=measurement["raw_flux"],
                            flux_err_jy=measurement["raw_error"],
                            normalized_flux_jy=measurement["normalized_flux"],
                            normalized_flux_err_jy=measurement["normalized_error"],
                            measured_at=measured_at,
                            source_id=source_id,
                        )

                        if params.get("auto_detect_ese", True):
                            try:
                                from dsa110_contimg.photometry.ese_pipeline import (
                                    auto_detect_ese_for_new_measurements,
                                )

                                min_sigma = params.get("ese_min_sigma", 5.0)
                                candidate = auto_detect_ese_for_new_measurements(
                                    products_db=products_db,
                                    source_id=source_id,
                                    min_sigma=min_sigma,
                                )
                                if candidate:
                                    logger.info(
                                        f"Auto-detected ESE candidate: {source_id} "
                                        f"(significance={candidate.get('significance', 0):.2f})"
                                    )
                            except Exception as e:
                                logger.warning(f"Auto ESE detection failed for {source_id}: {e}")

                        update_batch_item(conn, batch_id, item_id, None, "done")
                        conn.commit()

                    except Exception as e:
                        update_batch_item(conn, batch_id, item_id, None, "failed", error=str(e))
                        conn.commit()

        # Update batch job status
        cursor = conn.execute(
            """
            SELECT COUNT(*) FROM batch_job_items
            WHERE batch_id = ? AND status = 'done'
            """,
            (batch_id,),
        )
        completed = cursor.fetchone()[0]
        cursor = conn.execute(
            """
            SELECT COUNT(*) FROM batch_job_items
            WHERE batch_id = ? AND status = 'failed'
            """,
            (batch_id,),
        )
        failed = cursor.fetchone()[0]

        if failed == 0:
            status = "done"
        elif completed > 0:
            status = "partial"
        else:
            status = "failed"

        conn.execute(
            """
            UPDATE batch_jobs
            SET status = ?, completed_items = ?, failed_items = ?
            WHERE id = ?
            """,
            (status, completed, failed, batch_id),
        )
        conn.commit()

        # Update data registry photometry status if data_id is available
        try:
            # Get data_id from first batch item (all items should have same data_id)
            cursor = conn.execute(
                """
                SELECT DISTINCT data_id FROM batch_job_items
                WHERE batch_id = ? AND data_id IS NOT NULL
                LIMIT 1
                """,
                (batch_id,),
            )
            row = cursor.fetchone()
            if row:
                data_id = row[0]
                from dsa110_contimg.database.data_registry import (
                    ensure_data_registry_db,
                    update_photometry_status,
                )

                registry_db_path = Path(
                    os.getenv(
                        "DATA_REGISTRY_DB",
                        str(products_db.parent / "data_registry.sqlite3"),
                    )
                )
                registry_conn = ensure_data_registry_db(registry_db_path)
                # Map batch status to photometry status
                if status == "done":
                    photometry_status = "completed"
                elif status == "failed":
                    photometry_status = "failed"
                else:
                    photometry_status = "running"  # partial or still running

                update_photometry_status(registry_conn, data_id, photometry_status, str(batch_id))
                registry_conn.close()
        except Exception as e:
            structlog.get_logger(__name__).debug(
                f"Failed to update data registry photometry status: {e}"
            )

    except Exception:
        conn = ensure_products_db(products_db)
        conn.execute("UPDATE batch_jobs SET status = 'failed' WHERE id = ?", (batch_id,))
        conn.commit()
        # Update data registry photometry status to failed
        try:
            cursor = conn.execute(
                """
                SELECT DISTINCT data_id FROM batch_job_items
                WHERE batch_id = ? AND data_id IS NOT NULL
                LIMIT 1
                """,
                (batch_id,),
            )
            row = cursor.fetchone()
            if row:
                data_id = row[0]
                from dsa110_contimg.database.data_registry import (
                    ensure_data_registry_db,
                    update_photometry_status,
                )

                registry_db_path = Path(
                    os.getenv(
                        "DATA_REGISTRY_DB",
                        str(products_db.parent / "data_registry.sqlite3"),
                    )
                )
                registry_conn = ensure_data_registry_db(registry_db_path)
                update_photometry_status(registry_conn, data_id, "failed", str(batch_id))
                registry_conn.close()
        except Exception:
            pass  # Non-fatal
    finally:
        conn.close()


def run_ese_detect_job(job_id: int, params: dict, products_db: Path) -> None:
    """Run ESE detection job.

    Args:
        job_id: Job ID from database
        params: ESE detection parameters (min_sigma, preset, source_id, recompute)
        products_db: Path to products database
    """
    from dsa110_contimg.photometry.ese_detection import detect_ese_candidates
    from dsa110_contimg.photometry.thresholds import get_threshold_preset

    conn = ensure_products_db(products_db)
    ensure_jobs_table(conn)

    try:
        update_job_status(conn, job_id, "running", started_at=time.time())
        _log_to_db(conn, job_id, "=== Starting ESE Detection ===\n")

        # Handle preset or min_sigma
        preset = params.get("preset")
        min_sigma_param = params.get("min_sigma")

        if preset:
            thresholds = get_threshold_preset(preset)
            min_sigma = thresholds.get("min_sigma", 5.0)
            _log_to_db(
                conn,
                job_id,
                f"Using preset '{preset}': min_sigma={min_sigma}\n",
            )
        elif min_sigma_param is not None:
            min_sigma = min_sigma_param
        else:
            # Default fallback
            min_sigma = 5.0
            _log_to_db(
                conn,
                job_id,
                "No preset or min_sigma provided, using default min_sigma=5.0\n",
            )

        source_id = params.get("source_id")
        recompute = params.get("recompute", False)

        _log_to_db(
            conn,
            job_id,
            f"Parameters: min_sigma={min_sigma}, source_id={source_id}, recompute={recompute}\n",
        )

        candidates = detect_ese_candidates(
            products_db=products_db,
            min_sigma=min_sigma,
            source_id=source_id,
            recompute=recompute,
            use_composite_scoring=params.get("use_composite_scoring", False),
            scoring_weights=params.get("scoring_weights"),
        )

        _log_to_db(
            conn,
            job_id,
            f"Detected {len(candidates)} ESE candidates\n",
        )

        for cand in candidates:
            _log_to_db(
                conn,
                job_id,
                f"  - {cand['source_id']}: significance={cand['significance']:.2f}\n",
            )

        update_job_status(conn, job_id, "done", finished_at=time.time())
        _log_to_db(conn, job_id, "=== ESE Detection Complete ===\n")

    except Exception as e:
        error_msg = f"ESE detection failed: {e}"
        logger.error(error_msg, exc_info=True)
        _log_to_db(conn, job_id, f"ERROR: {error_msg}\n")
        update_job_status(conn, job_id, "failed", finished_at=time.time())
        raise
    finally:
        conn.close()


def run_batch_ese_detect_job(batch_id: int, params: dict, products_db: Path) -> None:
    """Run batch ESE detection job.

    Args:
        batch_id: Batch job ID from database
        params: Batch ESE detection parameters (min_sigma, recompute, source_ids)
        products_db: Path to products database
    """
    from dsa110_contimg.api.batch_jobs import update_batch_item
    from dsa110_contimg.photometry.ese_detection import detect_ese_candidates

    conn = ensure_products_db(products_db)

    try:
        # Update batch job status
        conn.execute("UPDATE batch_jobs SET status = 'running' WHERE id = ?", (batch_id,))
        conn.commit()

        # Handle preset or min_sigma
        preset = params.get("preset")
        min_sigma_param = params.get("min_sigma")

        if preset:
            from dsa110_contimg.photometry.thresholds import get_threshold_preset

            thresholds = get_threshold_preset(preset)
            min_sigma = thresholds.get("min_sigma", 5.0)
        elif min_sigma_param is not None:
            min_sigma = min_sigma_param
        else:
            # Default fallback
            min_sigma = 5.0

        recompute = params.get("recompute", False)
        source_ids = params.get("source_ids")
        use_parallel = params.get("use_parallel", False)

        # Use parallel processing if enabled and multiple sources
        if use_parallel and source_ids and len(source_ids) > 1:
            from dsa110_contimg.photometry.parallel import detect_ese_parallel

            try:
                update_batch_item(conn, batch_id, "all_sources", None, "running")
                detect_ese_parallel(
                    source_ids=source_ids,
                    products_db=products_db,
                    min_sigma=min_sigma,
                )
                update_batch_item(conn, batch_id, "all_sources", None, "done")
                return
            except Exception as e:
                update_batch_item(conn, batch_id, "all_sources", None, "failed", error=str(e))
                return

        if source_ids:
            # Process specific source IDs
            for source_id in source_ids:
                try:
                    update_batch_item(conn, batch_id, source_id, None, "running")
                    detect_ese_candidates(
                        products_db=products_db,
                        min_sigma=min_sigma,
                        source_id=source_id,
                        recompute=recompute,
                        use_composite_scoring=params.get("use_composite_scoring", False),
                        scoring_weights=params.get("scoring_weights"),
                    )
                    update_batch_item(conn, batch_id, source_id, None, "done")
                except Exception as e:
                    update_batch_item(conn, batch_id, source_id, None, "failed", error=str(e))
        else:
            # Process all sources
            try:
                update_batch_item(conn, batch_id, "all_sources", None, "running")
                detect_ese_candidates(
                    products_db=products_db,
                    min_sigma=min_sigma,
                    source_id=None,
                    recompute=recompute,
                    use_composite_scoring=params.get("use_composite_scoring", False),
                    scoring_weights=params.get("scoring_weights"),
                )
                update_batch_item(conn, batch_id, "all_sources", None, "done")
            except Exception as e:
                update_batch_item(conn, batch_id, "all_sources", None, "failed", error=str(e))

        # Update batch job status
        cursor = conn.execute(
            """
            SELECT COUNT(*) FROM batch_job_items
            WHERE batch_id = ? AND status = 'done'
            """,
            (batch_id,),
        )
        completed = cursor.fetchone()[0]
        cursor = conn.execute(
            """
            SELECT COUNT(*) FROM batch_job_items
            WHERE batch_id = ? AND status = 'failed'
            """,
            (batch_id,),
        )
        failed = cursor.fetchone()[0]

        if failed == 0:
            status = "done"
        elif completed > 0:
            status = "partial"
        else:
            status = "failed"

        conn.execute(
            """
            UPDATE batch_jobs
            SET status = ?, completed_items = ?, failed_items = ?
            WHERE id = ?
            """,
            (status, completed, failed, batch_id),
        )
        conn.commit()

    except Exception:
        conn = ensure_products_db(products_db)
        conn.execute("UPDATE batch_jobs SET status = 'failed' WHERE id = ?", (batch_id,))
        conn.commit()
        raise
    finally:
        conn.close()
