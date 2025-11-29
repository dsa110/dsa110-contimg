"""
Data access layer for the DSA-110 Continuum Imaging Pipeline API.

This module provides repository classes for querying images, measurement sets,
sources, and pipeline jobs from the products database.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from astropy.io import fits


# Database path configuration
DEFAULT_DB_PATH = "/data/dsa110-contimg/state/products.sqlite3"
CAL_REGISTRY_DB_PATH = "/data/dsa110-contimg/state/cal_registry.sqlite3"


@dataclass
class ImageRecord:
    """Image metadata record."""
    id: int
    path: str
    ms_path: str
    created_at: float
    type: str
    beam_major_arcsec: Optional[float] = None
    noise_jy: Optional[float] = None
    pbcor: int = 0
    format: str = "fits"
    beam_minor_arcsec: Optional[float] = None
    beam_pa_deg: Optional[float] = None
    dynamic_range: Optional[float] = None
    field_name: Optional[str] = None
    center_ra_deg: Optional[float] = None
    center_dec_deg: Optional[float] = None
    imsize_x: Optional[int] = None
    imsize_y: Optional[int] = None
    cellsize_arcsec: Optional[float] = None
    freq_ghz: Optional[float] = None
    bandwidth_mhz: Optional[float] = None
    integration_sec: Optional[float] = None
    
    # Derived from ms_index
    cal_table: Optional[str] = None
    qa_grade: Optional[str] = None
    qa_summary: Optional[str] = None
    run_id: Optional[str] = None


@dataclass
class MSRecord:
    """Measurement Set metadata record."""
    path: str
    start_mjd: Optional[float] = None
    end_mjd: Optional[float] = None
    mid_mjd: Optional[float] = None
    processed_at: Optional[float] = None
    status: Optional[str] = None
    stage: Optional[str] = None
    stage_updated_at: Optional[float] = None
    cal_applied: int = 0
    imagename: Optional[str] = None
    ra_deg: Optional[float] = None
    dec_deg: Optional[float] = None
    field_name: Optional[str] = None
    pointing_ra_deg: Optional[float] = None
    pointing_dec_deg: Optional[float] = None
    
    # Derived fields
    calibrator_tables: List[dict] = None
    qa_grade: Optional[str] = None
    qa_summary: Optional[str] = None
    run_id: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class SourceRecord:
    """Source catalog record."""
    id: str
    name: Optional[str] = None
    ra_deg: float = 0.0
    dec_deg: float = 0.0
    contributing_images: List[dict] = None
    latest_image_id: Optional[str] = None


@dataclass
class JobRecord:
    """Pipeline job record."""
    run_id: str
    input_ms_path: Optional[str] = None
    cal_table_path: Optional[str] = None
    phase_center_ra: Optional[float] = None
    phase_center_dec: Optional[float] = None
    qa_grade: Optional[str] = None
    qa_summary: Optional[str] = None
    output_image_id: Optional[int] = None
    started_at: Optional[datetime] = None


def get_db_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Get a database connection with proper timeout and WAL mode."""
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrent access
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


class ImageRepository:
    """Repository for querying image data."""
    
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
    
    def get_by_id(self, image_id: str) -> Optional[ImageRecord]:
        """Get image by ID (can be integer ID or path)."""
        conn = get_db_connection(self.db_path)
        try:
            # Try as integer ID first
            try:
                id_int = int(image_id)
                cursor = conn.execute(
                    "SELECT * FROM images WHERE id = ?",
                    (id_int,)
                )
            except ValueError:
                # Try as path
                cursor = conn.execute(
                    "SELECT * FROM images WHERE path = ?",
                    (image_id,)
                )
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Create record from row
            record = ImageRecord(
                id=row["id"],
                path=row["path"],
                ms_path=row["ms_path"],
                created_at=row["created_at"],
                type=row["type"],
                beam_major_arcsec=row["beam_major_arcsec"],
                noise_jy=row["noise_jy"],
                pbcor=row["pbcor"],
                format=row.get("format", "fits"),
                beam_minor_arcsec=row.get("beam_minor_arcsec"),
                beam_pa_deg=row.get("beam_pa_deg"),
                dynamic_range=row.get("dynamic_range"),
                field_name=row.get("field_name"),
                center_ra_deg=row.get("center_ra_deg"),
                center_dec_deg=row.get("center_dec_deg"),
                imsize_x=row.get("imsize_x"),
                imsize_y=row.get("imsize_y"),
                cellsize_arcsec=row.get("cellsize_arcsec"),
                freq_ghz=row.get("freq_ghz"),
                bandwidth_mhz=row.get("bandwidth_mhz"),
                integration_sec=row.get("integration_sec"),
            )
            
            # Try to get MS metadata for additional fields
            ms_cursor = conn.execute(
                "SELECT stage, status FROM ms_index WHERE path = ?",
                (record.ms_path,)
            )
            ms_row = ms_cursor.fetchone()
            if ms_row:
                record.qa_grade = self._stage_to_qa_grade(ms_row["stage"], ms_row["status"])
                record.qa_summary = self._generate_qa_summary(record)
            
            # Generate run_id from path or MS path
            record.run_id = self._generate_run_id(record.ms_path)
            
            # Try to get calibration table
            record.cal_table = self._find_cal_table(record.ms_path)
            
            return record
        finally:
            conn.close()
    
    def _stage_to_qa_grade(self, stage: Optional[str], status: Optional[str]) -> str:
        """Convert stage/status to QA grade."""
        if not stage:
            return "fail"
        if stage in ["imaged", "mosaicked", "cataloged"]:
            return "good"
        if stage in ["calibrated"]:
            return "warn"
        return "fail"
    
    def _generate_qa_summary(self, record: ImageRecord) -> str:
        """Generate QA summary from image metadata."""
        parts = []
        if record.noise_jy:
            parts.append(f"RMS {record.noise_jy*1000:.2f} mJy")
        if record.dynamic_range:
            parts.append(f"DR {record.dynamic_range:.0f}")
        if record.beam_major_arcsec:
            parts.append(f"Beam {record.beam_major_arcsec:.1f}\"")
        return ", ".join(parts) if parts else "No QA metrics available"
    
    def _generate_run_id(self, ms_path: str) -> str:
        """Generate run ID from MS path."""
        # Extract timestamp from MS path (e.g., "2025-10-31T13:49:06.ms" -> "job-20251031-134906")
        basename = Path(ms_path).stem
        # Try to extract ISO timestamp
        if "T" in basename:
            timestamp_part = basename.split("T")[0] + "-" + basename.split("T")[1].replace(":", "").split(".")[0]
            return f"job-{timestamp_part}"
        return f"job-{basename}"
    
    def _find_cal_table(self, ms_path: str) -> Optional[str]:
        """Find calibration table for MS."""
        # Check if cal_registry database exists
        if not os.path.exists(CAL_REGISTRY_DB_PATH):
            return None
        
        try:
            cal_conn = get_db_connection(CAL_REGISTRY_DB_PATH)
            cursor = cal_conn.execute(
                "SELECT path FROM caltables WHERE source_ms_path = ? ORDER BY created_at DESC LIMIT 1",
                (ms_path,)
            )
            row = cursor.fetchone()
            cal_conn.close()
            return row["path"] if row else None
        except Exception:
            return None


class MSRepository:
    """Repository for querying Measurement Set data."""
    
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
    
    def get_metadata(self, ms_path: str) -> Optional[MSRecord]:
        """Get MS metadata by path."""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT * FROM ms_index WHERE path = ?",
                (ms_path,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            
            record = MSRecord(
                path=row["path"],
                start_mjd=row.get("start_mjd"),
                end_mjd=row.get("end_mjd"),
                mid_mjd=row.get("mid_mjd"),
                processed_at=row.get("processed_at"),
                status=row.get("status"),
                stage=row.get("stage"),
                stage_updated_at=row.get("stage_updated_at"),
                cal_applied=row.get("cal_applied", 0),
                imagename=row.get("imagename"),
                ra_deg=row.get("ra_deg"),
                dec_deg=row.get("dec_deg"),
                field_name=row.get("field_name"),
                pointing_ra_deg=row.get("pointing_ra_deg"),
                pointing_dec_deg=row.get("pointing_dec_deg"),
            )
            
            # Get calibration tables
            record.calibrator_tables = self._get_calibrator_matches(ms_path)
            
            # Generate QA info
            record.qa_grade = self._stage_to_qa_grade(record.stage, record.status)
            record.qa_summary = self._generate_qa_summary(record)
            
            # Generate run_id
            record.run_id = self._generate_run_id(ms_path)
            
            # Convert processed_at to datetime
            if record.processed_at:
                record.created_at = datetime.fromtimestamp(record.processed_at)
            
            return record
        finally:
            conn.close()
    
    def _get_calibrator_matches(self, ms_path: str) -> List[dict]:
        """Get calibration tables for MS."""
        if not os.path.exists(CAL_REGISTRY_DB_PATH):
            return []
        
        try:
            cal_conn = get_db_connection(CAL_REGISTRY_DB_PATH)
            cursor = cal_conn.execute(
                "SELECT path, table_type FROM caltables WHERE source_ms_path = ? ORDER BY order_index",
                (ms_path,)
            )
            matches = [
                {"cal_table": row["path"], "type": row["table_type"]}
                for row in cursor.fetchall()
            ]
            cal_conn.close()
            return matches
        except Exception:
            return []
    
    def _stage_to_qa_grade(self, stage: Optional[str], status: Optional[str]) -> str:
        """Convert stage/status to QA grade."""
        if not stage:
            return "fail"
        if stage in ["imaged", "mosaicked", "cataloged"]:
            return "good"
        if stage in ["calibrated"]:
            return "warn"
        return "fail"
    
    def _generate_qa_summary(self, record: MSRecord) -> str:
        """Generate QA summary from MS metadata."""
        parts = []
        if record.cal_applied:
            parts.append("Calibrated")
        if record.stage:
            parts.append(f"Stage: {record.stage}")
        return ", ".join(parts) if parts else "No QA info"
    
    def _generate_run_id(self, ms_path: str) -> str:
        """Generate run ID from MS path."""
        basename = Path(ms_path).stem
        if "T" in basename:
            timestamp_part = basename.split("T")[0] + "-" + basename.split("T")[1].replace(":", "").split(".")[0]
            return f"job-{timestamp_part}"
        return f"job-{basename}"


class SourceRepository:
    """Repository for querying source catalog data."""
    
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
    
    def get_by_id(self, source_id: str) -> Optional[SourceRecord]:
        """Get source by ID."""
        conn = get_db_connection(self.db_path)
        try:
            # Get source from photometry table
            cursor = conn.execute(
                "SELECT source_id, ra_deg, dec_deg FROM photometry WHERE source_id = ? LIMIT 1",
                (source_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            
            record = SourceRecord(
                id=row["source_id"],
                name=row["source_id"],  # Use ID as name
                ra_deg=row["ra_deg"],
                dec_deg=row["dec_deg"],
            )
            
            # Get contributing images
            img_cursor = conn.execute(
                """
                SELECT DISTINCT p.image_path, i.id, i.ms_path, i.created_at
                FROM photometry p
                LEFT JOIN images i ON p.image_path = i.path
                WHERE p.source_id = ?
                ORDER BY i.created_at DESC
                """,
                (source_id,)
            )
            
            contributing = []
            latest_id = None
            for img_row in img_cursor.fetchall():
                if img_row["id"]:
                    if latest_id is None:
                        latest_id = str(img_row["id"])
                    
                    contributing.append({
                        "image_id": str(img_row["id"]),
                        "path": img_row["image_path"],
                        "ms_path": img_row["ms_path"],
                        "qa_grade": "good",  # Could be derived from stage
                        "created_at": datetime.fromtimestamp(img_row["created_at"]) if img_row["created_at"] else None,
                    })
            
            record.contributing_images = contributing
            record.latest_image_id = latest_id
            
            return record
        finally:
            conn.close()


class JobRepository:
    """Repository for querying pipeline job data."""
    
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
    
    def get_by_run_id(self, run_id: str) -> Optional[JobRecord]:
        """Get job by run ID."""
        conn = get_db_connection(self.db_path)
        try:
            # Extract timestamp from run_id (e.g., "job-20251031-134906" -> "2025-10-31T13:49:06")
            # This is a reverse operation of _generate_run_id
            if run_id.startswith("job-"):
                timestamp_part = run_id[4:]  # Remove "job-" prefix
                # Try to find matching MS
                cursor = conn.execute(
                    "SELECT * FROM ms_index WHERE path LIKE ? LIMIT 1",
                    (f"%{timestamp_part[:10]}%",)  # Match date part
                )
                row = cursor.fetchone()
                
                if row:
                    # Get associated image
                    img_cursor = conn.execute(
                        "SELECT id FROM images WHERE ms_path = ? ORDER BY created_at DESC LIMIT 1",
                        (row["path"],)
                    )
                    img_row = img_cursor.fetchone()
                    
                    # Get calibration table
                    cal_table = None
                    if os.path.exists(CAL_REGISTRY_DB_PATH):
                        try:
                            cal_conn = get_db_connection(CAL_REGISTRY_DB_PATH)
                            cal_cursor = cal_conn.execute(
                                "SELECT path FROM caltables WHERE source_ms_path = ? ORDER BY created_at DESC LIMIT 1",
                                (row["path"],)
                            )
                            cal_row = cal_cursor.fetchone()
                            if cal_row:
                                cal_table = cal_row["path"]
                            cal_conn.close()
                        except Exception:
                            pass
                    
                    record = JobRecord(
                        run_id=run_id,
                        input_ms_path=row["path"],
                        cal_table_path=cal_table,
                        phase_center_ra=row.get("pointing_ra_deg") or row.get("ra_deg"),
                        phase_center_dec=row.get("pointing_dec_deg") or row.get("dec_deg"),
                        qa_grade=self._stage_to_qa_grade(row.get("stage"), row.get("status")),
                        qa_summary=f"Stage: {row.get('stage', 'unknown')}",
                        output_image_id=img_row["id"] if img_row else None,
                        started_at=datetime.fromtimestamp(row["processed_at"]) if row.get("processed_at") else None,
                    )
                    return record
            
            return None
        finally:
            conn.close()
    
    def _stage_to_qa_grade(self, stage: Optional[str], status: Optional[str]) -> str:
        """Convert stage/status to QA grade."""
        if not stage:
            return "fail"
        if stage in ["imaged", "mosaicked", "cataloged"]:
            return "good"
        if stage in ["calibrated"]:
            return "warn"
        return "fail"
