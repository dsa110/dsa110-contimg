"""
Data access layer for the DSA-110 Continuum Imaging Pipeline API.

This module provides repository classes for querying images, measurement sets,
sources, and pipeline jobs from the products database.
"""

from __future__ import annotations

import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass

from astropy.io import fits

from .config import get_config


# Get database paths from configuration
_config = get_config()
DEFAULT_DB_PATH = str(_config.database.products_path)
CAL_REGISTRY_DB_PATH = str(_config.database.cal_registry_path)


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
    qa_metrics: Optional[dict] = None
    qa_flags: Optional[List[dict]] = None
    qa_timestamp: Optional[float] = None
    n_sources: Optional[int] = None
    peak_flux_jy: Optional[float] = None
    theoretical_noise_jy: Optional[float] = None


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
    qa_metrics: Optional[dict] = None
    qa_flags: Optional[List[dict]] = None
    qa_timestamp: Optional[float] = None


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
    queue_status: Optional[str] = None
    config: Optional[dict] = None
    job_id: Optional[int] = None
    qa_flags: Optional[List[dict]] = None


def get_db_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Get a database connection with proper timeout and WAL mode."""
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrent access
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def safe_row_get(row: sqlite3.Row, key: str, default: Optional[any] = None) -> any:
    """Safely get a value from a sqlite3.Row object.
    
    Args:
        row: The SQLite row to extract value from
        key: The column name to retrieve
        default: Default value if key doesn't exist
        
    Returns:
        The value at the given key, or default if not found
    """
    try:
        return row[key]
    except (KeyError, IndexError):
        return default


_ALLOWED_QA_TABLES = {"image_qa", "calibration_qa", "qa_flags"}


def _fetch_latest_qa_row(
    conn: sqlite3.Connection,
    table: str,
    key_column: str,
    key_value: str,
) -> Optional[sqlite3.Row]:
    """Fetch the latest QA row for a given key."""
    if table not in _ALLOWED_QA_TABLES:
        return None
    try:
        cursor = conn.execute(
            f"SELECT * FROM {table} WHERE {key_column} = ? ORDER BY timestamp DESC LIMIT 1",
            (key_value,),
        )
        return cursor.fetchone()
    except sqlite3.OperationalError:
        return None


def _collect_flag_rows(
    conn: sqlite3.Connection,
    table: str,
    key_column: str,
    key_value: str,
) -> List[dict]:
    """Collect all QA flag rows for a given key."""
    if table not in _ALLOWED_QA_TABLES:
        return []

    try:
        cursor = conn.execute(
            f"SELECT * FROM {table} WHERE {key_column} = ? ORDER BY timestamp DESC",
            (key_value,),
        )
    except sqlite3.OperationalError:
        return []

    flags = []
    for row in cursor.fetchall():
        row_dict = dict(row)
        row_dict.pop(key_column, None)
        row_dict.pop("timestamp", None)
        if row_dict:
            flags.append({
                "source": table,
                "details": row_dict,
            })
    return flags


def _build_flag_entries(row: sqlite3.Row, source: str) -> List[dict]:
    """Build canonical flag entries from a QA row."""
    if not row:
        return []
    entries = []
    for column in ["overall_quality", "flags_total"]:
        if column in row.keys() and row[column] is not None:
            entries.append({
                "rule": column,
                "value": row[column],
                "source": source,
            })
    return entries


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
                beam_major_arcsec=safe_row_get(row, "beam_major_arcsec"),
                noise_jy=safe_row_get(row, "noise_jy"),
                pbcor=safe_row_get(row, "pbcor", 0),
                format=safe_row_get(row, "format", "fits"),
                beam_minor_arcsec=safe_row_get(row, "beam_minor_arcsec"),
                beam_pa_deg=safe_row_get(row, "beam_pa_deg"),
                dynamic_range=safe_row_get(row, "dynamic_range"),
                field_name=safe_row_get(row, "field_name"),
                center_ra_deg=safe_row_get(row, "center_ra_deg"),
                center_dec_deg=safe_row_get(row, "center_dec_deg"),
                imsize_x=safe_row_get(row, "imsize_x"),
                imsize_y=safe_row_get(row, "imsize_y"),
                cellsize_arcsec=safe_row_get(row, "cellsize_arcsec"),
                freq_ghz=safe_row_get(row, "freq_ghz"),
                bandwidth_mhz=safe_row_get(row, "bandwidth_mhz"),
                integration_sec=safe_row_get(row, "integration_sec"),
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

            # Attach QA metrics/flags from QA tables
            qa_row = _fetch_latest_qa_row(conn, "image_qa", "image_path", record.path)
            if not qa_row and record.ms_path:
                qa_row = _fetch_latest_qa_row(conn, "image_qa", "ms_path", record.ms_path)

            if qa_row:
                metrics = {}
                for key in ["rms_noise", "dynamic_range", "beam_major", "beam_minor", "beam_pa"]:
                    if key in qa_row.keys() and qa_row[key] is not None:
                        metrics[key] = qa_row[key]
                record.qa_metrics = metrics or None
                record.noise_jy = record.noise_jy or safe_row_get(qa_row, "rms_noise")
                record.dynamic_range = record.dynamic_range or safe_row_get(qa_row, "dynamic_range")
                record.beam_major_arcsec = safe_row_get(qa_row, "beam_major") or record.beam_major_arcsec
                record.beam_minor_arcsec = safe_row_get(qa_row, "beam_minor") or record.beam_minor_arcsec
                record.beam_pa_deg = safe_row_get(qa_row, "beam_pa") or record.beam_pa_deg
                record.n_sources = safe_row_get(qa_row, "num_sources")
                record.peak_flux_jy = safe_row_get(qa_row, "peak_flux")
                record.qa_timestamp = safe_row_get(qa_row, "timestamp")
                record.qa_flags = _build_flag_entries(qa_row, "image_qa")

            extra_flags = _collect_flag_rows(conn, "qa_flags", "image_path", record.path)
            if not extra_flags and record.ms_path:
                extra_flags = _collect_flag_rows(conn, "qa_flags", "ms_path", record.ms_path)
            if extra_flags:
                record.qa_flags = (record.qa_flags or []) + extra_flags

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



    def list_all(self, limit: int = 100, offset: int = 0) -> list[ImageRecord]:
        """Get all images with pagination."""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT * FROM images ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            records = []
            for row in cursor.fetchall():
                record = ImageRecord(
                    id=row["id"],
                    path=row["path"],
                    ms_path=row["ms_path"],
                    created_at=row["created_at"],
                    type=row["type"],
                    beam_major_arcsec=safe_row_get(row, "beam_major_arcsec"),
                    noise_jy=safe_row_get(row, "noise_jy"),
                    pbcor=safe_row_get(row, "pbcor", 0),
                    format=safe_row_get(row, "format", "fits"),
                )
                # Generate run_id and qa_grade
                record.run_id = self._generate_run_id(record.ms_path)
                # Get QA grade from ms_index
                ms_cursor = conn.execute(
                    "SELECT stage, status FROM ms_index WHERE path = ?",
                    (record.ms_path,)
                )
                ms_row = ms_cursor.fetchone()
                if ms_row:
                    record.qa_grade = self._stage_to_qa_grade(ms_row["stage"], ms_row["status"])
                records.append(record)
            return records
        finally:
            conn.close()



    def list_all(self, limit: int = 100, offset: int = 0) -> list[ImageRecord]:
        """Get all images with pagination."""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT * FROM images ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            records = []
            for row in cursor.fetchall():
                record = ImageRecord(
                    id=row["id"],
                    path=row["path"],
                    ms_path=row["ms_path"],
                    created_at=row["created_at"],
                    type=row["type"],
                    beam_major_arcsec=safe_row_get(row, "beam_major_arcsec"),
                    noise_jy=safe_row_get(row, "noise_jy"),
                    pbcor=safe_row_get(row, "pbcor", 0),
                    format=safe_row_get(row, "format", "fits"),
                )
                # Generate run_id and qa_grade
                record.run_id = self._generate_run_id(record.ms_path)
                # Get QA grade from ms_index
                ms_cursor = conn.execute(
                    "SELECT stage, status FROM ms_index WHERE path = ?",
                    (record.ms_path,)
                )
                ms_row = ms_cursor.fetchone()
                if ms_row:
                    record.qa_grade = self._stage_to_qa_grade(ms_row["stage"], ms_row["status"])
                records.append(record)
            return records
        finally:
            conn.close()


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
                start_mjd=safe_row_get(row, "start_mjd"),
                end_mjd=safe_row_get(row, "end_mjd"),
                mid_mjd=safe_row_get(row, "mid_mjd"),
                processed_at=safe_row_get(row, "processed_at"),
                status=safe_row_get(row, "status"),
                stage=safe_row_get(row, "stage"),
                stage_updated_at=safe_row_get(row, "stage_updated_at"),
                cal_applied=safe_row_get(row, "cal_applied", 0),
                imagename=safe_row_get(row, "imagename"),
                ra_deg=safe_row_get(row, "ra_deg"),
                dec_deg=safe_row_get(row, "dec_deg"),
                field_name=safe_row_get(row, "field_name"),
                pointing_ra_deg=safe_row_get(row, "pointing_ra_deg"),
                pointing_dec_deg=safe_row_get(row, "pointing_dec_deg"),
            )
            
            # Get calibration tables
            record.calibrator_tables = self._get_calibrator_matches(ms_path)

            # Attach QA metrics and flags from calibration QA
            qa_row = _fetch_latest_qa_row(conn, "calibration_qa", "ms_path", ms_path)
            if qa_row:
                metrics = {}
                for key in ["overall_quality", "k_metrics", "bp_metrics", "g_metrics", "flags_total"]:
                    if key in qa_row.keys() and qa_row[key] is not None:
                        metrics[key] = qa_row[key]
                record.qa_metrics = metrics or None
                record.qa_timestamp = safe_row_get(qa_row, "timestamp")
                record.qa_flags = _build_flag_entries(qa_row, "calibration_qa")

            extra_flags = _collect_flag_rows(conn, "qa_flags", "ms_path", ms_path)
            if extra_flags:
                record.qa_flags = (record.qa_flags or []) + extra_flags
            
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



    def list_all(self, limit: int = 100, offset: int = 0) -> list[SourceRecord]:
        """Get all sources with pagination."""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT source_id, ra_deg, dec_deg, COUNT(*) as num_images
                FROM photometry
                GROUP BY source_id
                ORDER BY source_id
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )
            records = []
            for row in cursor.fetchall():
                records.append(SourceRecord(
                    id=row["source_id"],
                    name=row["source_id"],
                    ra_deg=row["ra_deg"],
                    dec_deg=row["dec_deg"],
                    contributing_images=[{}] * row["num_images"],  # Placeholder for count
                    latest_image_id=None,
                ))
            return records
        finally:
            conn.close()

    def get_lightcurve(self, source_id: str, start_mjd: Optional[float] = None, 
                       end_mjd: Optional[float] = None) -> list[dict]:
        """Get lightcurve data points for a source."""
        conn = get_db_connection(self.db_path)
        try:
            query = """
                SELECT mjd, flux_jy, flux_err_jy, peak_jyb, peak_err_jyb, snr, image_path
                FROM photometry
                WHERE source_id = ?
            """
            params = [source_id]
            
            if start_mjd is not None:
                query += " AND mjd >= ?"
                params.append(start_mjd)
            if end_mjd is not None:
                query += " AND mjd <= ?"
                params.append(end_mjd)
            
            query += " ORDER BY mjd"
            
            cursor = conn.execute(query, params)
            data_points = []
            for row in cursor.fetchall():
                data_points.append({
                    "mjd": row["mjd"],
                    "flux_jy": row["flux_jy"] or row["peak_jyb"],
                    "flux_err_jy": row["flux_err_jy"] or row["peak_err_jyb"],
                    "snr": row["snr"],
                    "image_path": row["image_path"],
                })
            return data_points
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
            if run_id.startswith("job-"):
                timestamp_part = run_id[4:]
                cursor = conn.execute(
                    "SELECT * FROM ms_index WHERE path LIKE ? LIMIT 1",
                    (f"%{timestamp_part[:10]}%",)
                )
                row = cursor.fetchone()
                
                if row:
                    img_cursor = conn.execute(
                        "SELECT id, path FROM images WHERE ms_path = ? ORDER BY created_at DESC LIMIT 1",
                        (row["path"],)
                    )
                    img_row = img_cursor.fetchone()
                    
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
                        phase_center_ra=safe_row_get(row, "pointing_ra_deg") or safe_row_get(row, "ra_deg"),
                        phase_center_dec=safe_row_get(row, "pointing_dec_deg") or safe_row_get(row, "dec_deg"),
                        qa_grade=self._stage_to_qa_grade(safe_row_get(row, "stage"), safe_row_get(row, "status")),
                        qa_summary=f"Stage: {safe_row_get(row, 'stage', 'unknown')}",
                        output_image_id=img_row["id"] if img_row else None,
                        started_at=datetime.fromtimestamp(row["processed_at"]) if safe_row_get(row, "processed_at") else None,
                    )

                    job_cursor = conn.execute(
                        "SELECT * FROM jobs WHERE run_id = ? ORDER BY created_at DESC LIMIT 1",
                        (run_id,)
                    )
                    job_row = job_cursor.fetchone()
                    if job_row:
                        record.queue_status = job_row["status"]
                        record.job_id = job_row["id"]
                        params = {}
                        try:
                            params = json.loads(job_row["params"]) if job_row["params"] else {}
                        except json.JSONDecodeError:
                            params = {}
                        record.config = params.get("config") or params

                    flags = []
                    ms_meta = MSRepository(self.db_path).get_metadata(row["path"])
                    if ms_meta and ms_meta.qa_flags:
                        flags.extend(ms_meta.qa_flags)

                    image_record = None
                    if img_row:
                        image_record = ImageRepository(self.db_path).get_by_id(str(img_row["id"]))
                    if not image_record and record.input_ms_path:
                        image_record = ImageRepository(self.db_path).get_by_id(record.input_ms_path)
                    if image_record and image_record.qa_flags:
                        flags.extend(image_record.qa_flags)

                    record.qa_flags = flags or None

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
    def list_all(self, limit: int = 100, offset: int = 0) -> list[JobRecord]:
        """Get all jobs with pagination."""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT DISTINCT path, processed_at, stage, status, 
                       pointing_ra_deg, pointing_dec_deg, ra_deg, dec_deg
                FROM ms_index 
                WHERE processed_at IS NOT NULL
                ORDER BY processed_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )
            records = []
            for row in cursor.fetchall():
                run_id = self._generate_run_id_from_path(row["path"])
                records.append(JobRecord(
                    run_id=run_id,
                    input_ms_path=row["path"],
                    phase_center_ra=safe_row_get(row, "pointing_ra_deg") or safe_row_get(row, "ra_deg"),
                    phase_center_dec=safe_row_get(row, "pointing_dec_deg") or safe_row_get(row, "dec_deg"),
                    qa_grade=self._stage_to_qa_grade(safe_row_get(row, "stage"), safe_row_get(row, "status")),
                    started_at=datetime.fromtimestamp(row["processed_at"]) if safe_row_get(row, "processed_at") else None,
                ))
            return records
        finally:
            conn.close()
    
    def _generate_run_id_from_path(self, ms_path: str) -> str:
        """Generate run ID from MS path."""
        basename = Path(ms_path).stem
        if "T" in basename:
            timestamp_part = basename.split("T")[0] + "-" + basename.split("T")[1].replace(":", "").split(".")[0]
            return f"job-{timestamp_part}"
        return f"job-{basename}"
    def list_all(self, limit: int = 100, offset: int = 0) -> list[JobRecord]:
        """Get all jobs with pagination."""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT DISTINCT path, processed_at, stage, status, 
                       pointing_ra_deg, pointing_dec_deg, ra_deg, dec_deg
                FROM ms_index 
                WHERE processed_at IS NOT NULL
                ORDER BY processed_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )
            records = []
            for row in cursor.fetchall():
                run_id = self._generate_run_id_from_path(row["path"])
                records.append(JobRecord(
                    run_id=run_id,
                    input_ms_path=row["path"],
                    phase_center_ra=safe_row_get(row, "pointing_ra_deg") or safe_row_get(row, "ra_deg"),
                    phase_center_dec=safe_row_get(row, "pointing_dec_deg") or safe_row_get(row, "dec_deg"),
                    qa_grade=self._stage_to_qa_grade(safe_row_get(row, "stage"), safe_row_get(row, "status")),
                    started_at=datetime.fromtimestamp(row["processed_at"]) if safe_row_get(row, "processed_at") else None,
                ))
            return records
        finally:
            conn.close()
    
    def _generate_run_id_from_path(self, ms_path: str) -> str:
        """Generate run ID from MS path."""
        basename = Path(ms_path).stem
        if "T" in basename:
            timestamp_part = basename.split("T")[0] + "-" + basename.split("T")[1].replace(":", "").split(".")[0]
            return f"job-{timestamp_part}"
        return f"job-{basename}"
