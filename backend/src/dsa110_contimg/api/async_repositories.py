"""
Async data access layer for the DSA-110 Continuum Imaging Pipeline API.

This module provides async repository classes using aiosqlite for non-blocking
database operations.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List, AsyncIterator, Any

import aiosqlite

from .config import get_config
from .exceptions import (
    DatabaseConnectionError,
    DatabaseQueryError,
    RecordNotFoundError,
)
from .interfaces import (
    ImageRepositoryInterface,
    MSRepositoryInterface,
    SourceRepositoryInterface,
    JobRepositoryInterface,
)
from .repositories import (
    ImageRecord,
    MSRecord,
    SourceRecord,
    JobRecord,
    safe_row_get,
    _get_default_db_path,
    _get_cal_registry_path,
)


# =============================================================================
# Transaction Context Manager
# =============================================================================

class AsyncTransaction:
    """
    Async context manager for database transactions.
    
    Provides automatic commit on success and rollback on failure.
    
    Usage:
        async with AsyncTransaction(db_path) as conn:
            await conn.execute("INSERT INTO ...")
            await conn.execute("UPDATE ...")
        # Auto-committed on exit
    """
    
    def __init__(self, db_path: str, timeout: float = 30.0):
        self.db_path = db_path
        self.timeout = timeout
        self._conn: Optional[aiosqlite.Connection] = None
    
    async def __aenter__(self) -> aiosqlite.Connection:
        try:
            self._conn = await aiosqlite.connect(
                self.db_path,
                timeout=self.timeout
            )
            self._conn.row_factory = aiosqlite.Row
            await self._conn.execute("PRAGMA journal_mode=WAL")
            await self._conn.execute("BEGIN TRANSACTION")
            return self._conn
        except sqlite3.Error as e:
            raise DatabaseConnectionError(self.db_path, str(e))
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            try:
                if exc_type is None:
                    await self._conn.commit()
                else:
                    await self._conn.rollback()
            finally:
                await self._conn.close()
        return False  # Don't suppress exceptions


@asynccontextmanager
async def get_async_connection(
    db_path: Optional[str] = None,
    timeout: float = 30.0
) -> AsyncIterator[aiosqlite.Connection]:
    """
    Get an async database connection with proper cleanup.
    
    Args:
        db_path: Path to SQLite database
        timeout: Connection timeout in seconds
        
    Yields:
        aiosqlite.Connection configured with WAL mode
        
    Raises:
        DatabaseConnectionError: If connection fails
    """
    if db_path is None:
        db_path = _get_default_db_path()
    try:
        conn = await aiosqlite.connect(db_path, timeout=timeout)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
        finally:
            await conn.close()
    except sqlite3.Error as e:
        raise DatabaseConnectionError(db_path, str(e))


# =============================================================================
# Async Image Repository
# =============================================================================

class AsyncImageRepository(ImageRepositoryInterface):
    """Async repository for querying image data.
    
    Implements ImageRepositoryInterface with aiosqlite.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _get_default_db_path()
        self.cal_db_path = _get_cal_registry_path()
    
    async def get_by_id(self, image_id: str) -> Optional[ImageRecord]:
        """Get image by ID (can be integer ID or path)."""
        async with get_async_connection(self.db_path) as conn:
            # Try as integer ID first
            try:
                id_int = int(image_id)
                cursor = await conn.execute(
                    "SELECT * FROM images WHERE id = ?",
                    (id_int,)
                )
            except ValueError:
                # Try as path
                cursor = await conn.execute(
                    "SELECT * FROM images WHERE path = ?",
                    (image_id,)
                )
            
            row = await cursor.fetchone()
            if not row:
                return None
            
            record = self._row_to_record(row)
            
            # Try to get MS metadata for additional fields
            ms_cursor = await conn.execute(
                "SELECT stage, status FROM ms_index WHERE path = ?",
                (record.ms_path,)
            )
            ms_row = await ms_cursor.fetchone()
            if ms_row:
                record.qa_grade = self._stage_to_qa_grade(ms_row["stage"], ms_row["status"])
                record.qa_summary = self._generate_qa_summary(record)
            
            record.run_id = self._generate_run_id(record.ms_path)
            record.cal_table = await self._find_cal_table(record.ms_path)
            
            return record
    
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[ImageRecord]:
        """Get all images with pagination."""
        async with get_async_connection(self.db_path) as conn:
            cursor = await conn.execute(
                "SELECT * FROM images ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            records = []
            async for row in cursor:
                record = self._row_to_record(row)
                record.run_id = self._generate_run_id(record.ms_path)
                
                # Get QA grade from ms_index
                ms_cursor = await conn.execute(
                    "SELECT stage, status FROM ms_index WHERE path = ?",
                    (record.ms_path,)
                )
                ms_row = await ms_cursor.fetchone()
                if ms_row:
                    record.qa_grade = self._stage_to_qa_grade(ms_row["stage"], ms_row["status"])
                records.append(record)
            return records
    
    async def count(self) -> int:
        """Get total count of images."""
        async with get_async_connection(self.db_path) as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM images")
            row = await cursor.fetchone()
            return row[0] if row else 0
    
    def _row_to_record(self, row: aiosqlite.Row) -> ImageRecord:
        """Convert database row to ImageRecord."""
        return ImageRecord(
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
        basename = Path(ms_path).stem
        if "T" in basename:
            timestamp_part = basename.split("T")[0] + "-" + basename.split("T")[1].replace(":", "").split(".")[0]
            return f"job-{timestamp_part}"
        return f"job-{basename}"
    
    async def _find_cal_table(self, ms_path: str) -> Optional[str]:
        """Find calibration table for MS."""
        if not os.path.exists(self.cal_db_path):
            return None
        
        try:
            async with get_async_connection(self.cal_db_path) as conn:
                cursor = await conn.execute(
                    "SELECT path FROM caltables WHERE source_ms_path = ? ORDER BY created_at DESC LIMIT 1",
                    (ms_path,)
                )
                row = await cursor.fetchone()
                return row["path"] if row else None
        except DatabaseConnectionError:
            return None


# =============================================================================
# Async MS Repository
# =============================================================================

class AsyncMSRepository(MSRepositoryInterface):
    """Async repository for querying Measurement Set data.
    
    Implements MSRepositoryInterface with aiosqlite.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _get_default_db_path()
        self.cal_db_path = CAL_REGISTRY_DB_PATH
    
    async def get_metadata(self, ms_path: str) -> Optional[MSRecord]:
        """Get MS metadata by path."""
        async with get_async_connection(self.db_path) as conn:
            cursor = await conn.execute(
                "SELECT * FROM ms_index WHERE path = ?",
                (ms_path,)
            )
            row = await cursor.fetchone()
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
            
            record.calibrator_tables = await self._get_calibrator_matches(ms_path)
            record.qa_grade = self._stage_to_qa_grade(record.stage, record.status)
            record.qa_summary = self._generate_qa_summary(record)
            record.run_id = self._generate_run_id(ms_path)
            
            if record.processed_at:
                record.created_at = datetime.fromtimestamp(record.processed_at)
            
            return record
    
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[MSRecord]:
        """Get all MS records with pagination."""
        async with get_async_connection(self.db_path) as conn:
            cursor = await conn.execute(
                "SELECT * FROM ms_index ORDER BY processed_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            records = []
            async for row in cursor:
                record = MSRecord(
                    path=row["path"],
                    start_mjd=safe_row_get(row, "start_mjd"),
                    end_mjd=safe_row_get(row, "end_mjd"),
                    mid_mjd=safe_row_get(row, "mid_mjd"),
                    processed_at=safe_row_get(row, "processed_at"),
                    status=safe_row_get(row, "status"),
                    stage=safe_row_get(row, "stage"),
                )
                record.qa_grade = self._stage_to_qa_grade(record.stage, record.status)
                record.run_id = self._generate_run_id(record.path)
                records.append(record)
            return records
    
    async def _get_calibrator_matches(self, ms_path: str) -> List[dict]:
        """Get calibration tables for MS."""
        if not os.path.exists(self.cal_db_path):
            return []
        
        try:
            async with get_async_connection(self.cal_db_path) as conn:
                cursor = await conn.execute(
                    "SELECT path, table_type FROM caltables WHERE source_ms_path = ? ORDER BY order_index",
                    (ms_path,)
                )
                matches = []
                async for row in cursor:
                    matches.append({"cal_table": row["path"], "type": row["table_type"]})
                return matches
        except DatabaseConnectionError:
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


# =============================================================================
# Async Source Repository
# =============================================================================

class AsyncSourceRepository(SourceRepositoryInterface):
    """Async repository for querying source catalog data.
    
    Implements SourceRepositoryInterface with aiosqlite.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _get_default_db_path()
    
    async def get_by_id(self, source_id: str) -> Optional[SourceRecord]:
        """Get source by ID."""
        async with get_async_connection(self.db_path) as conn:
            cursor = await conn.execute(
                "SELECT source_id, ra_deg, dec_deg FROM photometry WHERE source_id = ? LIMIT 1",
                (source_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            
            record = SourceRecord(
                id=row["source_id"],
                name=row["source_id"],
                ra_deg=row["ra_deg"],
                dec_deg=row["dec_deg"],
            )
            
            # Get contributing images
            img_cursor = await conn.execute(
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
            async for img_row in img_cursor:
                if img_row["id"]:
                    if latest_id is None:
                        latest_id = str(img_row["id"])
                    
                    contributing.append({
                        "image_id": str(img_row["id"]),
                        "path": img_row["image_path"],
                        "ms_path": img_row["ms_path"],
                        "qa_grade": "good",
                        "created_at": datetime.fromtimestamp(img_row["created_at"]) if img_row["created_at"] else None,
                    })
            
            record.contributing_images = contributing
            record.latest_image_id = latest_id
            
            return record
    
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[SourceRecord]:
        """Get all sources with pagination."""
        async with get_async_connection(self.db_path) as conn:
            cursor = await conn.execute(
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
            async for row in cursor:
                records.append(SourceRecord(
                    id=row["source_id"],
                    name=row["source_id"],
                    ra_deg=row["ra_deg"],
                    dec_deg=row["dec_deg"],
                    contributing_images=[{}] * row["num_images"],
                    latest_image_id=None,
                ))
            return records
    
    async def get_lightcurve(
        self,
        source_id: str,
        start_mjd: Optional[float] = None,
        end_mjd: Optional[float] = None
    ) -> List[dict]:
        """Get lightcurve data points for a source."""
        async with get_async_connection(self.db_path) as conn:
            query = """
                SELECT mjd, flux_jy, flux_err_jy, peak_jyb, peak_err_jyb, snr, image_path
                FROM photometry
                WHERE source_id = ?
            """
            params: List[Any] = [source_id]
            
            if start_mjd is not None:
                query += " AND mjd >= ?"
                params.append(start_mjd)
            if end_mjd is not None:
                query += " AND mjd <= ?"
                params.append(end_mjd)
            
            query += " ORDER BY mjd"
            
            cursor = await conn.execute(query, params)
            data_points = []
            async for row in cursor:
                data_points.append({
                    "mjd": row["mjd"],
                    "flux_jy": row["flux_jy"] or row["peak_jyb"],
                    "flux_err_jy": row["flux_err_jy"] or row["peak_err_jyb"],
                    "snr": row["snr"],
                    "image_path": row["image_path"],
                })
            return data_points


# =============================================================================
# Async Job Repository
# =============================================================================

class AsyncJobRepository(JobRepositoryInterface):
    """Async repository for querying pipeline job data.
    
    Implements JobRepositoryInterface with aiosqlite.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _get_default_db_path()
        self.cal_db_path = CAL_REGISTRY_DB_PATH
    
    async def get_by_run_id(self, run_id: str) -> Optional[JobRecord]:
        """Get job by run ID."""
        async with get_async_connection(self.db_path) as conn:
            if run_id.startswith("job-"):
                timestamp_part = run_id[4:]
                cursor = await conn.execute(
                    "SELECT * FROM ms_index WHERE path LIKE ? LIMIT 1",
                    (f"%{timestamp_part[:10]}%",)
                )
                row = await cursor.fetchone()
                
                if row:
                    img_cursor = await conn.execute(
                        "SELECT id FROM images WHERE ms_path = ? ORDER BY created_at DESC LIMIT 1",
                        (row["path"],)
                    )
                    img_row = await img_cursor.fetchone()
                    
                    cal_table = await self._find_cal_table(row["path"])
                    
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
                    return record
            
            return None
    
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[JobRecord]:
        """Get all jobs with pagination."""
        async with get_async_connection(self.db_path) as conn:
            cursor = await conn.execute(
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
            async for row in cursor:
                run_id = self._generate_run_id(row["path"])
                records.append(JobRecord(
                    run_id=run_id,
                    input_ms_path=row["path"],
                    phase_center_ra=safe_row_get(row, "pointing_ra_deg") or safe_row_get(row, "ra_deg"),
                    phase_center_dec=safe_row_get(row, "pointing_dec_deg") or safe_row_get(row, "dec_deg"),
                    qa_grade=self._stage_to_qa_grade(safe_row_get(row, "stage"), safe_row_get(row, "status")),
                    started_at=datetime.fromtimestamp(row["processed_at"]) if safe_row_get(row, "processed_at") else None,
                ))
            return records
    
    async def _find_cal_table(self, ms_path: str) -> Optional[str]:
        """Find calibration table for MS."""
        if not os.path.exists(self.cal_db_path):
            return None
        
        try:
            async with get_async_connection(self.cal_db_path) as conn:
                cursor = await conn.execute(
                    "SELECT path FROM caltables WHERE source_ms_path = ? ORDER BY created_at DESC LIMIT 1",
                    (ms_path,)
                )
                row = await cursor.fetchone()
                return row["path"] if row else None
        except DatabaseConnectionError:
            return None
    
    def _stage_to_qa_grade(self, stage: Optional[str], status: Optional[str]) -> str:
        """Convert stage/status to QA grade."""
        if not stage:
            return "fail"
        if stage in ["imaged", "mosaicked", "cataloged"]:
            return "good"
        if stage in ["calibrated"]:
            return "warn"
        return "fail"
    
    def _generate_run_id(self, ms_path: str) -> str:
        """Generate run ID from MS path."""
        basename = Path(ms_path).stem
        if "T" in basename:
            timestamp_part = basename.split("T")[0] + "-" + basename.split("T")[1].replace(":", "").split(".")[0]
            return f"job-{timestamp_part}"
        return f"job-{basename}"
