"""
Async data access layer for the DSA-110 Continuum Imaging Pipeline API.

This module provides async repository classes using aiosqlite for non-blocking
database operations.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

import aiosqlite

from .business_logic import (
    generate_image_qa_summary,
    generate_ms_qa_summary,
    generate_run_id,
    stage_to_qa_grade,
)
from .config import get_config
from .exceptions import (
    DatabaseConnectionError,
)
from .interfaces import (
    AsyncImageRepositoryProtocol,
    AsyncJobRepositoryProtocol,
    AsyncMSRepositoryProtocol,
    AsyncSourceRepositoryProtocol,
)

# =============================================================================
# Helper functions
# =============================================================================


def safe_row_get(row: sqlite3.Row, key: str, default: Optional[Any] = None) -> Any:
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


# =============================================================================
# Configuration helpers
# =============================================================================


def _get_default_db_path() -> str:
    """Get default database path from config (lazy-loaded)."""
    return str(get_config().database.products_path)


def _get_cal_registry_path() -> str:
    """Get calibration registry path from config (lazy-loaded)."""
    return str(get_config().database.cal_registry_path)


# =============================================================================
# Data records
# =============================================================================


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


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Get a sync database connection with proper timeout and WAL mode.

    Args:
        db_path: Database path, defaults to products DB from config
    """
    if db_path is None:
        db_path = _get_default_db_path()
    config = get_config()
    conn = sqlite3.connect(db_path, timeout=config.timeouts.db_connection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


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
            self._conn = await aiosqlite.connect(self.db_path, timeout=self.timeout)
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
    db_path: Optional[str] = None, timeout: float = 30.0
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


class AsyncImageRepository(AsyncImageRepositoryProtocol):
    """Async repository for querying image data.

    Implements AsyncImageRepositoryProtocol with aiosqlite.
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
                cursor = await conn.execute("SELECT * FROM images WHERE id = ?", (id_int,))
            except ValueError:
                # Try as path
                cursor = await conn.execute("SELECT * FROM images WHERE path = ?", (image_id,))

            row = await cursor.fetchone()
            if not row:
                return None

            record = self._row_to_record(row)

            # Try to get MS metadata for additional fields
            ms_cursor = await conn.execute(
                "SELECT stage, status FROM ms_index WHERE path = ?", (record.ms_path,)
            )
            ms_row = await ms_cursor.fetchone()
            if ms_row:
                record.qa_grade = stage_to_qa_grade(ms_row["stage"], ms_row["status"])
                record.qa_summary = generate_image_qa_summary(record)

            record.run_id = generate_run_id(record.ms_path)
            record.cal_table = await self._find_cal_table(record.ms_path)

            return record

    async def list_all(self, limit: int = 100, offset: int = 0) -> List[ImageRecord]:
        """Get all images with pagination.

        Optimized to batch fetch QA grades from ms_index in a single query
        instead of N+1 queries per image.
        """
        from .query_batch import SQLITE_MAX_PARAMS, chunk_list

        async with get_async_connection(self.db_path) as conn:
            cursor = await conn.execute(
                "SELECT * FROM images ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)
            )
            records = []
            async for row in cursor:
                record = self._row_to_record(row)
                record.run_id = generate_run_id(record.ms_path)
                records.append(record)

            # Batch fetch QA grades from ms_index (eliminates N+1 queries)
            if records:
                ms_paths = list(set(r.ms_path for r in records if r.ms_path))
                ms_grades = {}
                for chunk in chunk_list(ms_paths, SQLITE_MAX_PARAMS):
                    placeholders = ",".join("?" for _ in chunk)
                    ms_cursor = await conn.execute(
                        f"SELECT path, stage, status FROM ms_index WHERE path IN ({placeholders})",
                        tuple(chunk),
                    )
                    async for ms_row in ms_cursor:
                        ms_grades[ms_row["path"]] = stage_to_qa_grade(
                            ms_row["stage"], ms_row["status"]
                        )

                # Apply QA grades to records
                for record in records:
                    if record.ms_path in ms_grades:
                        record.qa_grade = ms_grades[record.ms_path]

            return records

    async def count(self) -> int:
        """Get total count of images."""
        async with get_async_connection(self.db_path) as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM images")
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_many(self, image_ids: List[str]) -> List[ImageRecord]:
        """Get multiple images by IDs in a single batch query.

        This is more efficient than calling get_by_id multiple times,
        as it uses a single query with IN clause.

        Args:
            image_ids: List of image IDs (can be integer IDs or paths)

        Returns:
            List of ImageRecords (may be fewer than requested if some not found)
        """
        if not image_ids:
            return []

        from .query_batch import SQLITE_MAX_PARAMS, chunk_list

        # Separate integer IDs from paths
        int_ids = []
        path_ids = []
        for image_id in image_ids:
            try:
                int_ids.append(int(image_id))
            except ValueError:
                path_ids.append(image_id)

        records = []
        async with get_async_connection(self.db_path) as conn:
            # Fetch by integer IDs in batches
            for chunk in chunk_list(int_ids, SQLITE_MAX_PARAMS):
                placeholders = ",".join("?" for _ in chunk)
                cursor = await conn.execute(
                    f"SELECT * FROM images WHERE id IN ({placeholders})", tuple(chunk)
                )
                async for row in cursor:
                    record = self._row_to_record(row)
                    record.run_id = generate_run_id(record.ms_path)
                    records.append(record)

            # Fetch by paths in batches
            for chunk in chunk_list(path_ids, SQLITE_MAX_PARAMS):
                placeholders = ",".join("?" for _ in chunk)
                cursor = await conn.execute(
                    f"SELECT * FROM images WHERE path IN ({placeholders})", tuple(chunk)
                )
                async for row in cursor:
                    record = self._row_to_record(row)
                    record.run_id = generate_run_id(record.ms_path)
                    records.append(record)

            # Batch fetch QA grades from ms_index
            if records:
                ms_paths = list(set(r.ms_path for r in records if r.ms_path))
                ms_grades = {}
                for chunk in chunk_list(ms_paths, SQLITE_MAX_PARAMS):
                    placeholders = ",".join("?" for _ in chunk)
                    cursor = await conn.execute(
                        f"SELECT path, stage, status FROM ms_index WHERE path IN ({placeholders})",
                        tuple(chunk),
                    )
                    async for row in cursor:
                        ms_grades[row["path"]] = stage_to_qa_grade(row["stage"], row["status"])

                # Apply QA grades to records
                for record in records:
                    if record.ms_path in ms_grades:
                        record.qa_grade = ms_grades[record.ms_path]

        return records

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

    async def _find_cal_table(self, ms_path: str) -> Optional[str]:
        """Find calibration table for MS."""
        if not os.path.exists(self.cal_db_path):
            return None

        try:
            async with get_async_connection(self.cal_db_path) as conn:
                cursor = await conn.execute(
                    "SELECT path FROM caltables WHERE source_ms_path = ? ORDER BY created_at DESC LIMIT 1",
                    (ms_path,),
                )
                row = await cursor.fetchone()
                return row["path"] if row else None
        except DatabaseConnectionError:
            return None


# =============================================================================
# Async MS Repository
# =============================================================================


class AsyncMSRepository(AsyncMSRepositoryProtocol):
    """Async repository for querying MS metadata.

    Implements AsyncMSRepositoryProtocol with aiosqlite.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _get_default_db_path()
        self.cal_db_path = _get_cal_registry_path()

    async def get_metadata(self, ms_path: str) -> Optional[MSRecord]:
        """Get MS metadata by path."""
        async with get_async_connection(self.db_path) as conn:
            cursor = await conn.execute("SELECT * FROM ms_index WHERE path = ?", (ms_path,))
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
            record.qa_grade = stage_to_qa_grade(record.stage, record.status)
            record.qa_summary = generate_ms_qa_summary(record)
            record.run_id = generate_run_id(ms_path)

            if record.processed_at:
                record.created_at = datetime.fromtimestamp(record.processed_at)

            return record

    async def list_all(self, limit: int = 100, offset: int = 0) -> List[MSRecord]:
        """Get all MS records with pagination."""
        async with get_async_connection(self.db_path) as conn:
            cursor = await conn.execute(
                "SELECT * FROM ms_index ORDER BY processed_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
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
                record.qa_grade = stage_to_qa_grade(record.stage, record.status)
                record.run_id = generate_run_id(record.path)
                records.append(record)
            return records

    async def get_many(self, ms_paths: List[str]) -> Dict[str, MSRecord]:
        """Get multiple MS records by paths in a single batch query.

        This is more efficient than calling get_metadata multiple times,
        as it uses a single query with IN clause.

        Args:
            ms_paths: List of MS paths to fetch

        Returns:
            Dict mapping path to MSRecord
        """
        if not ms_paths:
            return {}

        from .query_batch import SQLITE_MAX_PARAMS, chunk_list

        result: Dict[str, MSRecord] = {}
        async with get_async_connection(self.db_path) as conn:
            for chunk in chunk_list(ms_paths, SQLITE_MAX_PARAMS):
                placeholders = ",".join("?" for _ in chunk)
                cursor = await conn.execute(
                    f"SELECT * FROM ms_index WHERE path IN ({placeholders})", tuple(chunk)
                )
                async for row in cursor:
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
                    record.qa_grade = stage_to_qa_grade(record.stage, record.status)
                    record.qa_summary = generate_ms_qa_summary(record)
                    record.run_id = generate_run_id(record.path)
                    if record.processed_at:
                        record.created_at = datetime.fromtimestamp(record.processed_at)
                    result[record.path] = record

        return result

    async def _get_calibrator_matches(self, ms_path: str) -> List[dict]:
        """Get calibration tables for MS."""
        if not os.path.exists(self.cal_db_path):
            return []

        try:
            async with get_async_connection(self.cal_db_path) as conn:
                cursor = await conn.execute(
                    "SELECT path, table_type FROM caltables WHERE source_ms_path = ? ORDER BY order_index",
                    (ms_path,),
                )
                matches = []
                async for row in cursor:
                    matches.append({"cal_table": row["path"], "type": row["table_type"]})
                return matches
        except DatabaseConnectionError:
            return []


# =============================================================================
# Async Source Repository
# =============================================================================


class AsyncSourceRepository(AsyncSourceRepositoryProtocol):
    """Async repository for querying source catalog data.

    Implements AsyncSourceRepositoryProtocol with aiosqlite.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _get_default_db_path()

    async def get_by_id(self, source_id: str) -> Optional[SourceRecord]:
        """Get source by ID."""
        async with get_async_connection(self.db_path) as conn:
            cursor = await conn.execute(
                "SELECT source_id, ra_deg, dec_deg FROM photometry WHERE source_id = ? LIMIT 1",
                (source_id,),
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

            # Get contributing images with flux data for lightcurve display
            img_cursor = await conn.execute(
                """
                SELECT DISTINCT p.image_path, p.flux_jy, p.flux_err_jy, p.measured_at,
                       i.id, i.ms_path, i.created_at
                FROM photometry p
                LEFT JOIN images i ON p.image_path = i.path
                WHERE p.source_id = ?
                ORDER BY p.measured_at DESC
                """,
                (source_id,),
            )

            contributing = []
            latest_id = None
            async for img_row in img_cursor:
                if img_row["id"]:
                    if latest_id is None:
                        latest_id = str(img_row["id"])

                    # Use measured_at from photometry if available, fall back to image created_at
                    timestamp = img_row["measured_at"] or img_row["created_at"]
                    created_at = datetime.fromtimestamp(timestamp) if timestamp else None

                    contributing.append(
                        {
                            "image_id": str(img_row["id"]),
                            "path": img_row["image_path"],
                            "ms_path": img_row["ms_path"],
                            "qa_grade": "good",
                            "created_at": created_at,
                            "flux_jy": img_row["flux_jy"],
                            "flux_error_jy": img_row["flux_err_jy"],
                        }
                    )

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
                WHERE source_id IS NOT NULL
                GROUP BY source_id
                ORDER BY source_id
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            records = []
            async for row in cursor:
                records.append(
                    SourceRecord(
                        id=row["source_id"],
                        name=row["source_id"],
                        ra_deg=row["ra_deg"],
                        dec_deg=row["dec_deg"],
                        contributing_images=[{}] * row["num_images"],
                        latest_image_id=None,
                    )
                )
            return records

    async def get_lightcurve(
        self, source_id: str, start_mjd: Optional[float] = None, end_mjd: Optional[float] = None
    ) -> List[dict]:
        """Get lightcurve data points for a source.

        Args:
            source_id: The source identifier
            start_mjd: Optional start MJD for filtering
            end_mjd: Optional end MJD for filtering

        Returns:
            List of data point dicts with mjd, flux_jy, flux_err_jy, snr, image_path

        Note:
            The photometry table stores measured_at as Unix timestamp.
            We convert to MJD for the API response (MJD = Unix/86400 + 40587).
        """
        from astropy.time import Time

        async with get_async_connection(self.db_path) as conn:
            # Schema: measured_at (Unix timestamp), flux_jy, flux_err_jy, peak_flux_jy, snr
            query = """
                SELECT measured_at, flux_jy, flux_err_jy, peak_flux_jy, snr, image_path
                FROM photometry
                WHERE source_id IS NOT NULL
                  AND source_id = ?
            """
            params: List[Any] = [source_id]

            # Convert MJD filter bounds to Unix timestamps
            if start_mjd is not None:
                start_unix = Time(start_mjd, format="mjd").unix
                query += " AND measured_at >= ?"
                params.append(start_unix)
            if end_mjd is not None:
                end_unix = Time(end_mjd, format="mjd").unix
                query += " AND measured_at <= ?"
                params.append(end_unix)

            query += " ORDER BY measured_at"

            cursor = await conn.execute(query, params)
            data_points = []
            async for row in cursor:
                # Convert Unix timestamp to MJD for API response
                unix_ts = row["measured_at"]
                if unix_ts is None:
                    continue  # Skip rows with no timestamp
                mjd = Time(float(unix_ts), format="unix").mjd

                data_points.append(
                    {
                        "mjd": mjd,
                        "flux_jy": row["flux_jy"] or row["peak_flux_jy"],
                        "flux_err_jy": row["flux_err_jy"],
                        "snr": row["snr"],
                        "image_path": row["image_path"],
                    }
                )
            return data_points

    async def get_many(self, source_ids: List[str]) -> List[SourceRecord]:
        """Get multiple sources by IDs in a single batch query.

        Args:
            source_ids: List of source IDs to fetch

        Returns:
            List of SourceRecords
        """
        if not source_ids:
            return []

        from .query_batch import SQLITE_MAX_PARAMS, chunk_list

        records = []
        async with get_async_connection(self.db_path) as conn:
            for chunk in chunk_list(source_ids, SQLITE_MAX_PARAMS):
                placeholders = ",".join("?" for _ in chunk)
                cursor = await conn.execute(
                    f"""
                    SELECT source_id, ra_deg, dec_deg, COUNT(*) as num_images
                    FROM photometry
                WHERE source_id IS NOT NULL
                    WHERE source_id IN ({placeholders})
                    GROUP BY source_id
                    """,
                    tuple(chunk),
                )
                async for row in cursor:
                    records.append(
                        SourceRecord(
                            id=row["source_id"],
                            name=row["source_id"],
                            ra_deg=row["ra_deg"],
                            dec_deg=row["dec_deg"],
                            contributing_images=[{}] * row["num_images"],
                            latest_image_id=None,
                        )
                    )

        return records


# =============================================================================
# Async Job Repository
# =============================================================================


class AsyncJobRepository(AsyncJobRepositoryProtocol):
    """Async repository for querying pipeline job data.

    Implements AsyncJobRepositoryProtocol with aiosqlite.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _get_default_db_path()
        self.cal_db_path = _get_cal_registry_path()

    async def get_by_run_id(self, run_id: str) -> Optional[JobRecord]:
        """Get job by run ID."""
        async with get_async_connection(self.db_path) as conn:
            if run_id.startswith("job-"):
                timestamp_part = run_id[4:]
                cursor = await conn.execute(
                    "SELECT * FROM ms_index WHERE path LIKE ? LIMIT 1",
                    (f"%{timestamp_part[:10]}%",),
                )
                row = await cursor.fetchone()

                if row:
                    img_cursor = await conn.execute(
                        "SELECT id FROM images WHERE ms_path = ? ORDER BY created_at DESC LIMIT 1",
                        (row["path"],),
                    )
                    img_row = await img_cursor.fetchone()

                    cal_table = await self._find_cal_table(row["path"])

                    record = JobRecord(
                        run_id=run_id,
                        input_ms_path=row["path"],
                        cal_table_path=cal_table,
                        phase_center_ra=safe_row_get(row, "pointing_ra_deg")
                        or safe_row_get(row, "ra_deg"),
                        phase_center_dec=safe_row_get(row, "pointing_dec_deg")
                        or safe_row_get(row, "dec_deg"),
                        qa_grade=stage_to_qa_grade(
                            safe_row_get(row, "stage"), safe_row_get(row, "status")
                        ),
                        qa_summary=f"Stage: {safe_row_get(row, 'stage', 'unknown')}",
                        output_image_id=img_row["id"] if img_row else None,
                        started_at=datetime.fromtimestamp(row["processed_at"])
                        if safe_row_get(row, "processed_at")
                        else None,
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
                (limit, offset),
            )
            records = []
            async for row in cursor:
                run_id = generate_run_id(row["path"])
                records.append(
                    JobRecord(
                        run_id=run_id,
                        input_ms_path=row["path"],
                        phase_center_ra=safe_row_get(row, "pointing_ra_deg")
                        or safe_row_get(row, "ra_deg"),
                        phase_center_dec=safe_row_get(row, "pointing_dec_deg")
                        or safe_row_get(row, "dec_deg"),
                        qa_grade=stage_to_qa_grade(
                            safe_row_get(row, "stage"), safe_row_get(row, "status")
                        ),
                        started_at=datetime.fromtimestamp(row["processed_at"])
                        if safe_row_get(row, "processed_at")
                        else None,
                    )
                )
            return records

    async def _find_cal_table(self, ms_path: str) -> Optional[str]:
        """Find calibration table for MS."""
        if not os.path.exists(self.cal_db_path):
            return None

        try:
            async with get_async_connection(self.cal_db_path) as conn:
                cursor = await conn.execute(
                    "SELECT path FROM caltables WHERE source_ms_path = ? ORDER BY created_at DESC LIMIT 1",
                    (ms_path,),
                )
                row = await cursor.fetchone()
                return row["path"] if row else None
        except DatabaseConnectionError:
            return None

    async def get_many(self, run_ids: List[str]) -> List[JobRecord]:
        """Get multiple jobs by run IDs in a single batch query.

        Args:
            run_ids: List of run IDs to fetch

        Returns:
            List of JobRecords
        """
        if not run_ids:
            return []

        from .query_batch import SQLITE_MAX_PARAMS, chunk_list

        # Extract timestamp patterns from run_ids for LIKE matching
        timestamp_patterns = []
        for run_id in run_ids:
            if run_id.startswith("job-"):
                timestamp_part = run_id[4:][:10]  # Get date part
                timestamp_patterns.append(f"%{timestamp_part}%")

        if not timestamp_patterns:
            return []

        records = []
        run_id_map = {}  # Map path to run_id

        async with get_async_connection(self.db_path) as conn:
            # Batch fetch by patterns
            for chunk in chunk_list(timestamp_patterns, SQLITE_MAX_PARAMS // 2):
                # Build OR conditions for LIKE patterns
                conditions = " OR ".join("path LIKE ?" for _ in chunk)
                cursor = await conn.execute(
                    f"""
                    SELECT path, processed_at, stage, status,
                           pointing_ra_deg, pointing_dec_deg, ra_deg, dec_deg
                    FROM ms_index
                    WHERE {conditions}
                    """,
                    tuple(chunk),
                )
                async for row in cursor:
                    generated_run_id = generate_run_id(row["path"])
                    # Only include if it matches one of the requested run_ids
                    if generated_run_id in run_ids:
                        records.append(
                            JobRecord(
                                run_id=generated_run_id,
                                input_ms_path=row["path"],
                                phase_center_ra=safe_row_get(row, "pointing_ra_deg")
                                or safe_row_get(row, "ra_deg"),
                                phase_center_dec=safe_row_get(row, "pointing_dec_deg")
                                or safe_row_get(row, "dec_deg"),
                                qa_grade=stage_to_qa_grade(
                                    safe_row_get(row, "stage"), safe_row_get(row, "status")
                                ),
                                started_at=datetime.fromtimestamp(row["processed_at"])
                                if safe_row_get(row, "processed_at")
                                else None,
                            )
                        )

        return records
