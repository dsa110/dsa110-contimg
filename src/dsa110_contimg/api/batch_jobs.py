"""Batch job processing and quality assessment utilities."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


def create_batch_job(conn: sqlite3.Connection, job_type: str, ms_paths: List[str], params: Dict[str, Any]) -> int:
    """Create a batch job in the database."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO batch_jobs (type, created_at, status, total_items, completed_items, failed_items, params)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (job_type, datetime.utcnow().timestamp(), "pending", len(ms_paths), 0, 0, str(params))
    )
    batch_id = cursor.lastrowid
    
    # Insert batch items
    for ms_path in ms_paths:
        cursor.execute(
            """
            INSERT INTO batch_job_items (batch_id, ms_path, status)
            VALUES (?, ?, ?)
            """,
            (batch_id, ms_path, "pending")
        )
    
    conn.commit()
    return batch_id


def update_batch_item(conn: sqlite3.Connection, batch_id: int, ms_path: str, job_id: Optional[int], status: str, error: Optional[str] = None):
    """Update a batch job item status."""
    cursor = conn.cursor()
    timestamp = datetime.utcnow().timestamp()
    
    if status == "running":
        cursor.execute(
            """
            UPDATE batch_job_items
            SET job_id = ?, status = ?, started_at = ?
            WHERE batch_id = ? AND ms_path = ?
            """,
            (job_id, status, timestamp, batch_id, ms_path)
        )
    elif status in ("done", "failed", "cancelled"):
        cursor.execute(
            """
            UPDATE batch_job_items
            SET status = ?, completed_at = ?, error = ?
            WHERE batch_id = ? AND ms_path = ?
            """,
            (status, timestamp, error, batch_id, ms_path)
        )
    
    # Update batch job counts
    cursor.execute(
        """
        SELECT COUNT(*) FROM batch_job_items WHERE batch_id = ? AND status = 'done'
        """,
        (batch_id,)
    )
    completed = cursor.fetchone()[0]
    
    cursor.execute(
        """
        SELECT COUNT(*) FROM batch_job_items WHERE batch_id = ? AND status = 'failed'
        """,
        (batch_id,)
    )
    failed = cursor.fetchone()[0]
    
    # Determine overall batch status
    cursor.execute(
        """
        SELECT COUNT(*) FROM batch_job_items WHERE batch_id = ? AND status IN ('pending', 'running')
        """,
        (batch_id,)
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
        (completed, failed, batch_status, batch_id)
    )
    
    conn.commit()


def extract_calibration_qa(ms_path: str, job_id: int, caltables: Dict[str, str]) -> Dict[str, Any]:
    """Extract QA metrics from calibration tables."""
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
                snr = tb.getcol("SNR") if tb.colnames().count("SNR") > 0 else None
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
            qa_metrics["dynamic_range"] = qa_metrics["peak_flux"] / qa_metrics["rms_noise"]
        
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
        return {"ms_path": ms_path, "job_id": job_id, "image_path": image_path, "overall_quality": "unknown"}


def generate_image_thumbnail(image_path: str, output_path: Optional[str] = None, size: int = 512) -> Optional[str]:
    """Generate a PNG thumbnail of a CASA image."""
    try:
        from casatools import image
        import numpy as np
        from PIL import Image
        
        ia = image()
        ia.open(image_path)
        
        # Get image data (first Stokes, first channel)
        data = ia.getchunk()
        if data.ndim >= 2:
            img_data = data[:, :, 0, 0] if data.ndim == 4 else data[:, :, 0] if data.ndim == 3 else data
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
        pil_img = Image.fromarray(img_8bit, mode='L')
        pil_img.thumbnail((size, size), Image.Resampling.LANCZOS)
        
        # Save thumbnail
        if output_path is None:
            output_path = str(Path(image_path).with_suffix('.thumb.png'))
        
        pil_img.save(output_path, 'PNG')
        return output_path
    except Exception as e:
        logger.error(f"Failed to generate thumbnail for {image_path}: {e}")
        return None

