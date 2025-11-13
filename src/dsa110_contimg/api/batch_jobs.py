"""Batch job processing and quality assessment utilities."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def create_batch_job(
    conn: sqlite3.Connection, job_type: str, ms_paths: List[str], params: Dict[str, Any]
) -> int:
    """Create a batch job in the database."""
    # Input validation
    if not isinstance(job_type, str) or not job_type.strip():
        raise ValueError("job_type must be a non-empty string")
    if not isinstance(ms_paths, list):
        raise ValueError("ms_paths must be a list")
    if not all(isinstance(p, str) and p.strip() for p in ms_paths):
        raise ValueError("All ms_paths must be non-empty strings")
    if not isinstance(params, dict):
        raise ValueError("params must be a dictionary")

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO batch_jobs (type, created_at, status, total_items, completed_items, failed_items, params)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_type,
            datetime.utcnow().timestamp(),
            "pending",
            len(ms_paths),
            0,
            0,
            str(params),
        ),
    )
    batch_id = cursor.lastrowid

    # Insert batch items
    for ms_path in ms_paths:
        cursor.execute(
            """
            INSERT INTO batch_job_items (batch_id, ms_path, status)
            VALUES (?, ?, ?)
            """,
            (batch_id, ms_path, "pending"),
        )

    conn.commit()
    return batch_id


def create_batch_conversion_job(
    conn: sqlite3.Connection,
    job_type: str,
    time_windows: List[Dict[str, str]],
    params: Dict[str, Any],
) -> int:
    """Create a batch conversion job in the database.

    Args:
        conn: Database connection
        job_type: Job type (e.g., "batch_convert")
        time_windows: List of time window dicts with "start_time" and "end_time"
        params: Shared parameters for all conversion jobs

    Returns:
        Batch job ID
    """
    # Input validation
    if not isinstance(job_type, str) or not job_type.strip():
        raise ValueError("job_type must be a non-empty string")
    if not isinstance(time_windows, list):
        raise ValueError("time_windows must be a list")
    if not all(
        isinstance(tw, dict)
        and "start_time" in tw
        and "end_time" in tw
        and isinstance(tw["start_time"], str)
        and isinstance(tw["end_time"], str)
        for tw in time_windows
    ):
        raise ValueError(
            "All time_windows must be dicts with 'start_time' and 'end_time' strings"
        )
    if not isinstance(params, dict):
        raise ValueError("params must be a dictionary")

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO batch_jobs (type, created_at, status, total_items, completed_items, failed_items, params)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_type,
            datetime.utcnow().timestamp(),
            "pending",
            len(time_windows),
            0,
            0,
            str(params),
        ),
    )
    batch_id = cursor.lastrowid

    # Insert batch items using time window identifiers
    for tw in time_windows:
        # Use time window as identifier (format: "time_window_{start}_{end}")
        time_window_id = f"time_window_{tw['start_time']}_{tw['end_time']}"
        cursor.execute(
            """
            INSERT INTO batch_job_items (batch_id, ms_path, status)
            VALUES (?, ?, ?)
            """,
            (batch_id, time_window_id, "pending"),
        )

    conn.commit()
    return batch_id


def create_batch_publish_job(
    conn: sqlite3.Connection,
    job_type: str,
    data_ids: List[str],
    params: Dict[str, Any],
) -> int:
    """Create a batch publish job in the database.

    Args:
        conn: Database connection
        job_type: Job type (e.g., "batch_publish")
        data_ids: List of data instance IDs to publish
        params: Shared parameters for all publish jobs (e.g., products_base)

    Returns:
        Batch job ID
    """
    # Input validation
    if not isinstance(job_type, str) or not job_type.strip():
        raise ValueError("job_type must be a non-empty string")
    if not isinstance(data_ids, list):
        raise ValueError("data_ids must be a list")
    if not all(isinstance(did, str) and did.strip() for did in data_ids):
        raise ValueError("All data_ids must be non-empty strings")
    if not isinstance(params, dict):
        raise ValueError("params must be a dictionary")

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO batch_jobs (type, created_at, status, total_items, completed_items, failed_items, params)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_type,
            datetime.utcnow().timestamp(),
            "pending",
            len(data_ids),
            0,
            0,
            str(params),
        ),
    )
    batch_id = cursor.lastrowid

    # Insert batch items using data_ids
    for data_id in data_ids:
        cursor.execute(
            """
            INSERT INTO batch_job_items (batch_id, ms_path, status)
            VALUES (?, ?, ?)
            """,
            (batch_id, data_id, "pending"),
        )

    conn.commit()
    return batch_id


def create_batch_photometry_job(
    conn: sqlite3.Connection,
    job_type: str,
    fits_paths: List[str],
    coordinates: List[dict],
    params: Dict[str, Any],
    data_id: Optional[str] = None,
) -> int:
    """Create a batch photometry job in the database.

    Args:
        conn: Database connection
        job_type: Job type (e.g., "batch_photometry")
        fits_paths: List of FITS image paths to process
        coordinates: List of coordinate dicts with ra_deg and dec_deg
        params: Shared parameters for all photometry jobs
        data_id: Optional data ID to link photometry job to data registry

    Returns:
        Batch job ID
    """
    # Ensure batch_jobs table exists
    # ensure_products_db creates this table, but we need to ensure it exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS batch_jobs (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            created_at REAL NOT NULL,
            status TEXT NOT NULL,
            total_items INTEGER NOT NULL,
            completed_items INTEGER DEFAULT 0,
            failed_items INTEGER DEFAULT 0,
            params TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS batch_job_items (
            id INTEGER PRIMARY KEY,
            batch_id INTEGER NOT NULL,
            ms_path TEXT NOT NULL,
            job_id INTEGER,
            status TEXT NOT NULL,
            error TEXT,
            started_at REAL,
            completed_at REAL,
            FOREIGN KEY (batch_id) REFERENCES batch_jobs(id)
        )
    """)
    # Migrate existing tables to add data_id column if it doesn't exist
    try:
        conn.execute("SELECT data_id FROM batch_job_items LIMIT 1")
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        try:
            conn.execute("ALTER TABLE batch_job_items ADD COLUMN data_id TEXT DEFAULT NULL")
        except sqlite3.OperationalError:
            pass  # Column may already exist from concurrent creation
    conn.commit()

    # Input validation
    if not isinstance(job_type, str) or not job_type.strip():
        raise ValueError("job_type must be a non-empty string")
    if not isinstance(fits_paths, list):
        raise ValueError("fits_paths must be a list")
    if not all(isinstance(fp, str) and fp.strip() for fp in fits_paths):
        raise ValueError("All fits_paths must be non-empty strings")
    if not isinstance(coordinates, list):
        raise ValueError("coordinates must be a list")
    if not isinstance(params, dict):
        raise ValueError("params must be a dictionary")

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO batch_jobs (type, created_at, status, total_items, completed_items, failed_items, params)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_type,
            datetime.utcnow().timestamp(),
            "pending",
            # Total items = images * coordinates
            len(fits_paths) * len(coordinates),
            0,
            0,
            json.dumps(params) if isinstance(params, dict) else str(params),
        ),
    )
    batch_id = cursor.lastrowid

    # Insert batch items (one per image-coordinate pair)
    for fits_path in fits_paths:
        for coord in coordinates:
            # Use fits_path as ms_path identifier (for compatibility with batch_job_items schema)
            item_id = f"{fits_path}:{coord['ra_deg']}:{coord['dec_deg']}"
            cursor.execute(
                """
                INSERT INTO batch_job_items (batch_id, ms_path, status, data_id)
                VALUES (?, ?, ?, ?)
                """,
                (batch_id, item_id, "pending", data_id),
            )

    conn.commit()
    return batch_id


def create_batch_ese_detect_job(
    conn: sqlite3.Connection,
    job_type: str,
    params: Dict[str, Any],
) -> int:
    """Create a batch ESE detection job in the database.

    Args:
        conn: Database connection
        job_type: Job type (e.g., "batch_ese-detect")
        params: ESE detection parameters (min_sigma, recompute, source_ids)

    Returns:
        Batch job ID
    """
    # Ensure batch_jobs table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS batch_jobs (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            created_at REAL NOT NULL,
            status TEXT NOT NULL,
            total_items INTEGER NOT NULL,
            completed_items INTEGER DEFAULT 0,
            failed_items INTEGER DEFAULT 0,
            params TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS batch_job_items (
            id INTEGER PRIMARY KEY,
            batch_id INTEGER NOT NULL,
            ms_path TEXT NOT NULL,
            job_id INTEGER,
            status TEXT NOT NULL,
            error TEXT,
            started_at REAL,
            completed_at REAL,
            FOREIGN KEY (batch_id) REFERENCES batch_jobs(id)
        )
    """)
    conn.commit()

    # Input validation
    if not isinstance(job_type, str) or not job_type.strip():
        raise ValueError("job_type must be a non-empty string")
    if not isinstance(params, dict):
        raise ValueError("params must be a dictionary")

    source_ids = params.get("source_ids")
    if source_ids is not None:
        if not isinstance(source_ids, list):
            raise ValueError("source_ids must be a list")
        if not all(isinstance(sid, str) and sid.strip() for sid in source_ids):
            raise ValueError("All source_ids must be non-empty strings")
        total_items = len(source_ids)
    else:
        # Will process all sources (single item)
        total_items = 1

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO batch_jobs (type, created_at, status, total_items, completed_items, failed_items, params)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_type,
            time.time(),
            "pending",
            total_items,
            0,
            0,
            str(params),
        ),
    )
    batch_id = cursor.lastrowid

    # Create batch job items
    if source_ids:
        for source_id in source_ids:
            cursor.execute(
                """
                INSERT INTO batch_job_items (batch_id, ms_path, status)
                VALUES (?, ?, ?)
                """,
                (batch_id, source_id, "pending"),
            )
    else:
        # Single item for "all sources"
        cursor.execute(
            """
            INSERT INTO batch_job_items (batch_id, ms_path, status)
            VALUES (?, ?, ?)
            """,
            (batch_id, "all_sources", "pending"),
        )

    conn.commit()
    return batch_id


def update_batch_conversion_item(
    conn: sqlite3.Connection,
    batch_id: int,
    time_window_id: str,
    job_id: Optional[int],
    status: str,
    error: Optional[str] = None,
):
    """Update a batch conversion job item status.

    Args:
        conn: Database connection
        batch_id: Batch job ID
        time_window_id: Time window identifier (format: "time_window_{start}_{end}")
        job_id: Individual job ID (if created)
        status: Status (pending, running, done, failed, cancelled)
        error: Error message (if failed)
    """
    # Use the same update_batch_item function but with time_window_id as ms_path
    update_batch_item(conn, batch_id, time_window_id, job_id, status, error)


def update_batch_item(
    conn: sqlite3.Connection,
    batch_id: int,
    ms_path: str,
    job_id: Optional[int],
    status: str,
    error: Optional[str] = None,
):
    """Update a batch job item status."""
    # Input validation
    if not isinstance(batch_id, int) or batch_id < 1:
        raise ValueError("batch_id must be a positive integer")
    if not isinstance(ms_path, str) or not ms_path.strip():
        raise ValueError("ms_path must be a non-empty string")
    if status not in ("pending", "running", "done", "failed", "cancelled"):
        raise ValueError(f"Invalid status: {status}")
    if job_id is not None and (not isinstance(job_id, int) or job_id < 1):
        raise ValueError("job_id must be None or a positive integer")

    cursor = conn.cursor()
    timestamp = datetime.utcnow().timestamp()

    if status == "running":
        cursor.execute(
            """
            UPDATE batch_job_items
            SET job_id = ?, status = ?, started_at = ?
            WHERE batch_id = ? AND ms_path = ?
            """,
            (job_id, status, timestamp, batch_id, ms_path),
        )
    elif status in ("done", "failed", "cancelled"):
        cursor.execute(
            """
            UPDATE batch_job_items
            SET status = ?, completed_at = ?, error = ?
            WHERE batch_id = ? AND ms_path = ?
            """,
            (status, timestamp, error, batch_id, ms_path),
        )

    # Update batch job counts
    cursor.execute(
        """
        SELECT COUNT(*) FROM batch_job_items WHERE batch_id = ? AND status = 'done'
        """,
        (batch_id,),
    )
    completed = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT COUNT(*) FROM batch_job_items WHERE batch_id = ? AND status = 'failed'
        """,
        (batch_id,),
    )
    failed = cursor.fetchone()[0]

    # Determine overall batch status
    cursor.execute(
        """
        SELECT COUNT(*) FROM batch_job_items WHERE batch_id = ? AND status IN ('pending', 'running')
        """,
        (batch_id,),
    )
    remaining = cursor.fetchone()[0]

    if remaining == 0:
        batch_status = "done" if failed == 0 else "failed"
    else:
        batch_status = "running"

    cursor.execute(
        """
        UPDATE batch_jobs
        SET completed_items = ?, failed_items = ?, status = ?
        WHERE id = ?
        """,
        (completed, failed, batch_status, batch_id),
    )

    conn.commit()


def extract_calibration_qa(
    ms_path: str, job_id: int, caltables: Dict[str, str]
) -> Dict[str, Any]:
    """Extract QA metrics from calibration tables."""
    # Ensure CASAPATH is set before importing CASA modules
    from dsa110_contimg.utils.casa_init import ensure_casa_path

    ensure_casa_path()

    try:
        from casatools import table

        tb = table()

        qa_metrics = {
            "ms_path": ms_path,
            "job_id": job_id,
            "overall_quality": "unknown",
            "flags_total": None,
        }

        # Analyze K table if present
        if "k" in caltables and caltables["k"] and Path(caltables["k"]).exists():
            try:
                tb.open(caltables["k"])
                flags = tb.getcol("FLAG")
                snr = tb.getcol("SNR") if tb.colnames().count(
                    "SNR") > 0 else None
                tb.close()

                flag_fraction = flags.sum() / flags.size if flags.size > 0 else 1.0
                avg_snr = snr.mean() if snr is not None else None

                qa_metrics["k_metrics"] = {
                    "flag_fraction": float(flag_fraction),
                    "avg_snr": float(avg_snr) if avg_snr is not None else None,
                }
            except Exception as e:
                logger.warning(f"Failed to extract K QA for {ms_path}: {e}")

        # Analyze BP table if present
        if "bp" in caltables and caltables["bp"] and Path(caltables["bp"]).exists():
            try:
                tb.open(caltables["bp"])
                flags = tb.getcol("FLAG")
                gains = tb.getcol("CPARAM")
                tb.close()

                flag_fraction = flags.sum() / flags.size if flags.size > 0 else 1.0
                amp = abs(gains)
                amp_mean = amp.mean() if amp.size > 0 else None
                amp_std = amp.std() if amp.size > 0 else None

                qa_metrics["bp_metrics"] = {
                    "flag_fraction": float(flag_fraction),
                    "amp_mean": float(amp_mean) if amp_mean is not None else None,
                    "amp_std": float(amp_std) if amp_std is not None else None,
                }

                # Extract per-SPW statistics
                try:
                    from dsa110_contimg.qa.calibration_quality import (
                        analyze_per_spw_flagging,
                    )

                    spw_stats = analyze_per_spw_flagging(caltables["bp"])
                    qa_metrics["per_spw_stats"] = [
                        {
                            "spw_id": s.spw_id,
                            "total_solutions": s.total_solutions,
                            "flagged_solutions": s.flagged_solutions,
                            "fraction_flagged": s.fraction_flagged,
                            "n_channels": s.n_channels,
                            "channels_with_high_flagging": s.channels_with_high_flagging,
                            "avg_flagged_per_channel": s.avg_flagged_per_channel,
                            "max_flagged_in_channel": s.max_flagged_in_channel,
                            "is_problematic": bool(s.is_problematic),
                        }
                        for s in spw_stats
                    ]
                except Exception as e:
                    logger.warning(
                        f"Failed to extract per-SPW statistics for {ms_path}: {e}"
                    )
            except Exception as e:
                logger.warning(f"Failed to extract BP QA for {ms_path}: {e}")

        # Analyze G table if present
        if "g" in caltables and caltables["g"] and Path(caltables["g"]).exists():
            try:
                tb.open(caltables["g"])
                flags = tb.getcol("FLAG")
                gains = tb.getcol("CPARAM")
                tb.close()

                flag_fraction = flags.sum() / flags.size if flags.size > 0 else 1.0
                amp = abs(gains)
                amp_mean = amp.mean() if amp.size > 0 else None

                qa_metrics["g_metrics"] = {
                    "flag_fraction": float(flag_fraction),
                    "amp_mean": float(amp_mean) if amp_mean is not None else None,
                }
            except Exception as e:
                logger.warning(f"Failed to extract G QA for {ms_path}: {e}")

        # Overall quality assessment
        total_flags = []
        for key in ["k_metrics", "bp_metrics", "g_metrics"]:
            if key in qa_metrics and qa_metrics[key]:
                total_flags.append(qa_metrics[key].get("flag_fraction", 1.0))

        if total_flags:
            qa_metrics["flags_total"] = sum(total_flags) / len(total_flags)
            avg_flag = qa_metrics["flags_total"]

            if avg_flag < 0.1:
                qa_metrics["overall_quality"] = "excellent"
            elif avg_flag < 0.3:
                qa_metrics["overall_quality"] = "good"
            elif avg_flag < 0.5:
                qa_metrics["overall_quality"] = "marginal"
            else:
                qa_metrics["overall_quality"] = "poor"

        return qa_metrics
    except Exception as e:
        logger.error(f"Failed to extract calibration QA for {ms_path}: {e}")
        return {"ms_path": ms_path, "job_id": job_id, "overall_quality": "unknown"}


def extract_image_qa(ms_path: str, job_id: int, image_path: str) -> Dict[str, Any]:
    """Extract QA metrics from an image."""
    try:
        from casatools import image

        ia = image()

        qa_metrics = {
            "ms_path": ms_path,
            "job_id": job_id,
            "image_path": image_path,
            "overall_quality": "unknown",
        }

        if not Path(image_path).exists():
            return qa_metrics

        ia.open(image_path)

        # Get image statistics
        stats = ia.statistics()
        qa_metrics["rms_noise"] = float(stats.get("rms", [0])[0])
        qa_metrics["peak_flux"] = float(stats.get("max", [0])[0])

        if qa_metrics["rms_noise"] > 0:
            qa_metrics["dynamic_range"] = (
                qa_metrics["peak_flux"] / qa_metrics["rms_noise"]
            )

        # Get beam info
        beam = ia.restoringbeam()
        if beam:
            major = beam.get("major", {})
            minor = beam.get("minor", {})
            pa = beam.get("positionangle", {})

            if "value" in major:
                qa_metrics["beam_major"] = float(major["value"])
            if "value" in minor:
                qa_metrics["beam_minor"] = float(minor["value"])
            if "value" in pa:
                qa_metrics["beam_pa"] = float(pa["value"])

        ia.close()

        # Quality assessment
        if qa_metrics.get("dynamic_range"):
            dr = qa_metrics["dynamic_range"]
            if dr > 1000:
                qa_metrics["overall_quality"] = "excellent"
            elif dr > 100:
                qa_metrics["overall_quality"] = "good"
            elif dr > 10:
                qa_metrics["overall_quality"] = "marginal"
            else:
                qa_metrics["overall_quality"] = "poor"

        return qa_metrics
    except Exception as e:
        logger.error(f"Failed to extract image QA for {ms_path}: {e}")
        return {
            "ms_path": ms_path,
            "job_id": job_id,
            "image_path": image_path,
            "overall_quality": "unknown",
        }


def generate_image_thumbnail(
    image_path: str, output_path: Optional[str] = None, size: int = 512
) -> Optional[str]:
    """Generate a PNG thumbnail of a CASA image."""
    try:
        import numpy as np
        from casatools import image
        from PIL import Image

        ia = image()
        ia.open(image_path)

        # Get image data (first Stokes, first channel)
        data = ia.getchunk()
        if data.ndim >= 2:
            img_data = (
                data[:, :, 0, 0]
                if data.ndim == 4
                else data[:, :, 0] if data.ndim == 3 else data
            )
        else:
            ia.close()
            return None

        ia.close()

        # Normalize and convert to 8-bit
        valid_data = img_data[np.isfinite(img_data)]
        if valid_data.size == 0:
            return None

        vmin = np.percentile(valid_data, 1)
        vmax = np.percentile(valid_data, 99.5)

        normalized = np.clip((img_data - vmin) / (vmax - vmin), 0, 1)
        img_8bit = (normalized * 255).astype(np.uint8)

        # Create PIL image and resize
        pil_img = Image.fromarray(img_8bit, mode="L")
        pil_img.thumbnail((size, size), Image.Resampling.LANCZOS)

        # Save thumbnail
        if output_path is None:
            output_path = str(Path(image_path).with_suffix(".thumb.png"))

        pil_img.save(output_path, "PNG")
        return output_path
    except Exception as e:
        logger.error(f"Failed to generate thumbnail for {image_path}: {e}")
        return None
