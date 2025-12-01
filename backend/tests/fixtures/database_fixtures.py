"""Database fixtures for testing.

This module provides test fixtures that create properly-structured SQLite databases
matching the production schema. It imports schema definitions from the shared
schema module to ensure test and production schemas stay in sync.

Usage:
    @pytest.fixture
    async def products_db(tmp_path):
        db_path = tmp_path / "products.sqlite3"
        async with aiosqlite.connect(db_path) as conn:
            await create_products_schema(conn)
            await populate_products_db(conn, sample_image_records())
        return db_path
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    import aiosqlite

# Import shared schema definitions - single source of truth
from dsa110_contimg.database.schema import (
    PRODUCTS_TABLES,
    PRODUCTS_INDEXES,
    CAL_REGISTRY_TABLES,
    CAL_REGISTRY_INDEXES,
)

__all__ = [
    # Schema functions
    "create_products_schema",
    "create_cal_registry_schema",
    # Data classes
    "SampleImage",
    "SampleSource",
    "SampleJob",
    "SampleCalTable",
    "SampleMSIndex",
    "SamplePhotometry",
    # Sample data generators
    "sample_image_records",
    "sample_source_records",
    "sample_job_records",
    "sample_caltable_records",
    "sample_ms_index_records",
    "sample_photometry_records",
    # Population functions (async)
    "populate_products_db",
    "populate_cal_registry_db",
    "create_populated_products_db",
    "create_populated_cal_registry_db",
    # Context managers (sync, for integration tests)
    "create_test_products_db",
    "create_test_cal_registry_db",
    "create_test_database_environment",
]


# =============================================================================
# Async Schema Creation Functions
# =============================================================================


async def create_products_schema(conn: "aiosqlite.Connection") -> None:
    """Create all products database tables and indexes (async version).

    Args:
        conn: Active aiosqlite connection.
    """
    for create_sql in PRODUCTS_TABLES.values():
        await conn.execute(create_sql)
    for index_sql in PRODUCTS_INDEXES:
        await conn.execute(index_sql)
    await conn.commit()


async def create_cal_registry_schema(conn: "aiosqlite.Connection") -> None:
    """Create all calibration registry tables and indexes (async version).

    Args:
        conn: Active aiosqlite connection.
    """
    for create_sql in CAL_REGISTRY_TABLES.values():
        await conn.execute(create_sql)
    for index_sql in CAL_REGISTRY_INDEXES:
        await conn.execute(index_sql)
    await conn.commit()


# =============================================================================
# Sample Data Classes
# =============================================================================


@dataclass
class SampleImage:
    """Sample image record for testing.
    
    Matches the schema in dsa110_contimg.database.schema.PRODUCTS_TABLES['images'].
    """

    id: int
    path: str  # Matches schema: path TEXT NOT NULL UNIQUE
    ms_path: str
    created_at: float  # Matches schema: REAL NOT NULL (MJD or Unix timestamp)
    type: str = "continuum"
    beam_major_arcsec: float | None = None
    beam_minor_arcsec: float | None = None
    beam_pa_deg: float | None = None
    noise_jy: float | None = None
    dynamic_range: float | None = None
    pbcor: int = 0
    format: str = "fits"
    field_name: str | None = None
    center_ra_deg: float | None = None
    center_dec_deg: float | None = None
    imsize_x: int | None = None
    imsize_y: int | None = None
    cellsize_arcsec: float | None = None
    freq_ghz: float | None = None
    bandwidth_mhz: float | None = None
    integration_sec: float | None = None


@dataclass
class SampleSource:
    """Sample source record for testing.
    
    Matches the schema in dsa110_contimg.database.schema.PRODUCTS_TABLES['sources'].
    """

    id: str  # TEXT PRIMARY KEY
    ra_deg: float
    dec_deg: float
    name: str | None = None
    catalog_match: str | None = None
    source_type: str | None = None
    first_detected_mjd: float | None = None
    last_detected_mjd: float | None = None
    detection_count: int = 1


@dataclass
class SampleJob:
    """Sample batch job record for testing.
    
    Matches the schema in dsa110_contimg.database.schema.PRODUCTS_TABLES['batch_jobs'].
    Schema: id, type, created_at, status, total_items, completed_items, failed_items, params
    """

    id: int  # INTEGER PRIMARY KEY (not UUID)
    type: str = "imaging"  # TEXT NOT NULL (job type: imaging, calibration, photometry)
    created_at: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    status: str = "pending"  # TEXT NOT NULL DEFAULT 'pending'
    total_items: int = 0  # INTEGER NOT NULL DEFAULT 0
    completed_items: int = 0  # INTEGER DEFAULT 0
    failed_items: int = 0  # INTEGER DEFAULT 0
    params: str | None = None  # TEXT (JSON parameters)


@dataclass
class SampleCalTable:
    """Sample calibration table record for testing.
    
    Matches the schema in dsa110_contimg.database.schema.CAL_REGISTRY_TABLES['caltables'].
    """

    path: str  # TEXT PRIMARY KEY
    table_type: str  # TEXT NOT NULL
    set_name: str | None = None
    cal_field: str | None = None
    refant: str | None = None
    created_at: float | None = None
    source_ms_path: str | None = None
    status: str = "active"
    notes: str | None = None
    order_index: int = 0


@dataclass
class SampleMSIndex:
    """Sample MS index record for testing.
    
    Matches the schema in dsa110_contimg.database.schema.PRODUCTS_TABLES['ms_index'].
    """

    path: str  # TEXT PRIMARY KEY
    start_mjd: float | None = None
    end_mjd: float | None = None
    mid_mjd: float | None = None
    processed_at: float | None = None
    status: str | None = None
    stage: str | None = None
    stage_updated_at: float | None = None
    cal_applied: int = 0
    imagename: str | None = None
    ra_deg: float | None = None
    dec_deg: float | None = None
    field_name: str | None = None
    pointing_ra_deg: float | None = None
    pointing_dec_deg: float | None = None


@dataclass
class SamplePhotometry:
    """Sample photometry record for testing.
    
    Matches the schema in dsa110_contimg.database.schema.PRODUCTS_TABLES['photometry'].
    """

    id: int
    source_id: str  # TEXT NOT NULL
    image_path: str  # TEXT NOT NULL
    ra_deg: float
    dec_deg: float
    mjd: float | None = None
    flux_jy: float | None = None
    flux_err_jy: float | None = None
    peak_jyb: float | None = None
    peak_err_jyb: float | None = None
    snr: float | None = None
    local_rms: float | None = None


# =============================================================================
# Sample Data Generators
# =============================================================================


def sample_image_records(count: int = 5) -> Iterator[SampleImage]:
    """Generate sample image records for testing.

    Args:
        count: Number of records to generate.

    Yields:
        SampleImage instances with realistic test data.
    """
    base_time = datetime.utcnow().timestamp()
    for i in range(count):
        yield SampleImage(
            id=i + 1,
            path=f"/stage/dsa110-contimg/images/obs_{i:04d}.fits",
            ms_path=f"/stage/dsa110-contimg/ms/obs_{i:04d}.ms",
            created_at=base_time - i * 3600,
            type="continuum",
            beam_major_arcsec=30.0,
            beam_minor_arcsec=25.0,
            beam_pa_deg=45.0,
            noise_jy=0.001 + i * 0.0001,
            dynamic_range=100.0 + i * 10,
            pbcor=1,
            format="fits",
            field_name=f"field_{i}",
            center_ra_deg=180.0 + i * 0.5,
            center_dec_deg=37.0,
            imsize_x=4096,
            imsize_y=4096,
            cellsize_arcsec=2.0,
            freq_ghz=1.4,
            bandwidth_mhz=256.0,
            integration_sec=300.0,
        )


def sample_source_records(count: int = 10) -> Iterator[SampleSource]:
    """Generate sample source records for testing.

    Args:
        count: Number of records to generate.

    Yields:
        SampleSource instances with realistic test data.
    """
    base_ra = 180.0  # degrees
    base_dec = 37.0  # degrees (DSA-110 declination)
    base_mjd = 60000.0  # ~2023
    for i in range(count):
        yield SampleSource(
            id=f"src_{i:05d}",
            name=f"J{int(base_ra/15):02d}{int((base_ra%15)*4):02d}+{int(base_dec):02d}{int((base_dec%1)*60):02d}_{i}",
            ra_deg=base_ra + i * 0.01,
            dec_deg=base_dec + i * 0.01,
            catalog_match="NVSS" if i % 2 == 0 else None,
            source_type="point" if i % 3 == 0 else "extended",
            first_detected_mjd=base_mjd,
            last_detected_mjd=base_mjd + i,
            detection_count=i + 1,
        )


def sample_job_records(count: int = 3) -> Iterator[SampleJob]:
    """Generate sample batch job records for testing.

    Args:
        count: Number of records to generate.

    Yields:
        SampleJob instances with varying statuses.
    """
    statuses = ["pending", "running", "completed", "failed"]
    job_types = ["imaging", "calibration", "photometry"]
    base_time = datetime.utcnow().timestamp()
    for i in range(count):
        status = statuses[i % len(statuses)]
        total = 10
        completed = total if status == "completed" else (5 if status == "running" else 0)
        failed = 2 if status == "failed" else 0

        yield SampleJob(
            id=i + 1,  # INTEGER PRIMARY KEY
            type=job_types[i % len(job_types)],
            created_at=base_time - i * 3600,
            status=status,
            total_items=total,
            completed_items=completed,
            failed_items=failed,
            params='{"test": true}' if i % 2 == 0 else None,
        )


def sample_caltable_records(count: int = 5) -> Iterator[SampleCalTable]:
    """Generate sample calibration table records for testing.

    Args:
        count: Number of records to generate.

    Yields:
        SampleCalTable instances with realistic test data.
    """
    cal_types = ["bandpass", "gain", "delay", "flux"]
    base_time = datetime.utcnow().timestamp()
    for i in range(count):
        cal_type = cal_types[i % len(cal_types)]
        yield SampleCalTable(
            path=f"/stage/dsa110-contimg/cal/obs_{i:04d}.{cal_type[:1]}cal",
            table_type=cal_type,
            set_name=f"calset_{i // 2}",
            cal_field="3C286" if cal_type == "flux" else f"field_{i}",
            refant="ea01",
            created_at=base_time - i * 3600,
            source_ms_path=f"/stage/dsa110-contimg/ms/obs_{i:04d}.ms",
            status="active",
            notes=f"Test calibration table {i}",
            order_index=i,
        )


def sample_ms_index_records(count: int = 5) -> Iterator[SampleMSIndex]:
    """Generate sample MS index records for testing.

    Args:
        count: Number of records to generate.

    Yields:
        SampleMSIndex instances with realistic test data.
    """
    base_mjd = 60000.0  # ~2023
    for i in range(count):
        start = base_mjd + i
        end = start + 0.003  # ~5 minutes in MJD
        mid = (start + end) / 2
        yield SampleMSIndex(
            path=f"/stage/dsa110-contimg/ms/obs_{i:04d}.ms",
            start_mjd=start,
            end_mjd=end,
            mid_mjd=mid,
            processed_at=datetime.utcnow().timestamp(),
            status="complete",
            stage="imaged",
            stage_updated_at=datetime.utcnow().timestamp(),
            cal_applied=1,
            imagename=f"obs_{i:04d}.fits",
            ra_deg=180.0 + i * 0.5,
            dec_deg=37.0,
            field_name=f"field_{i}",
            pointing_ra_deg=180.0 + i * 0.5,
            pointing_dec_deg=37.0,
        )


def sample_photometry_records(count: int = 10, source_id: str = "src_00000") -> Iterator[SamplePhotometry]:
    """Generate sample photometry records for testing.

    Args:
        count: Number of records to generate.
        source_id: Source ID to associate records with.

    Yields:
        SamplePhotometry instances with realistic test data.
    """
    base_ra = 180.0
    base_dec = 37.0
    base_mjd = 60000.0
    for i in range(count):
        yield SamplePhotometry(
            id=i + 1,
            source_id=source_id,
            image_path=f"/stage/dsa110-contimg/images/obs_{i:04d}.fits",
            ra_deg=base_ra + i * 0.001,
            dec_deg=base_dec + i * 0.001,
            mjd=base_mjd + i,
            flux_jy=0.01 + i * 0.005,
            flux_err_jy=0.001,
            peak_jyb=0.012 + i * 0.005,
            peak_err_jyb=0.001,
            snr=20.0 + i * 5,
            local_rms=0.0005,
        )


# =============================================================================
# Database Population Functions
# =============================================================================


async def populate_products_db(
    conn: "aiosqlite.Connection",
    images: Iterator[SampleImage] | None = None,
    sources: Iterator[SampleSource] | None = None,
    jobs: Iterator[SampleJob] | None = None,
    ms_records: Iterator[SampleMSIndex] | None = None,
    photometry_records: Iterator[SamplePhotometry] | None = None,
) -> None:
    """Populate a products database with sample data.

    Args:
        conn: Active aiosqlite connection.
        images: Image records to insert (default: 5 sample records).
        sources: Source records to insert (default: 10 sample records).
        jobs: Job records to insert (default: 3 sample records).
        ms_records: MS index records to insert (default: 5 sample records).
        photometry_records: Photometry records to insert (default: 10 sample records).
    """
    # Default sample data
    if images is None:
        images = sample_image_records()
    if sources is None:
        sources = sample_source_records()
    if jobs is None:
        jobs = sample_job_records()
    if ms_records is None:
        ms_records = sample_ms_index_records()
    if photometry_records is None:
        photometry_records = sample_photometry_records()

    # Insert images
    for img in images:
        await conn.execute(
            """
            INSERT INTO images (
                id, path, ms_path, created_at, type, beam_major_arcsec, beam_minor_arcsec,
                beam_pa_deg, noise_jy, dynamic_range, pbcor, format, field_name,
                center_ra_deg, center_dec_deg, imsize_x, imsize_y, cellsize_arcsec,
                freq_ghz, bandwidth_mhz, integration_sec
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                img.id, img.path, img.ms_path, img.created_at, img.type,
                img.beam_major_arcsec, img.beam_minor_arcsec, img.beam_pa_deg,
                img.noise_jy, img.dynamic_range, img.pbcor, img.format,
                img.field_name, img.center_ra_deg, img.center_dec_deg,
                img.imsize_x, img.imsize_y, img.cellsize_arcsec,
                img.freq_ghz, img.bandwidth_mhz, img.integration_sec,
            ),
        )

    # Insert sources
    for src in sources:
        await conn.execute(
            """
            INSERT INTO sources (
                id, name, ra_deg, dec_deg, catalog_match, source_type,
                first_detected_mjd, last_detected_mjd, detection_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                src.id, src.name, src.ra_deg, src.dec_deg, src.catalog_match,
                src.source_type, src.first_detected_mjd, src.last_detected_mjd,
                src.detection_count,
            ),
        )

    # Insert jobs
    for job in jobs:
        await conn.execute(
            """
            INSERT INTO batch_jobs (
                id, type, created_at, status, total_items, completed_items,
                failed_items, params
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.id, job.type, job.created_at, job.status, job.total_items,
                job.completed_items, job.failed_items, job.params,
            ),
        )

    # Insert MS index records
    for ms in ms_records:
        await conn.execute(
            """
            INSERT INTO ms_index (
                path, start_mjd, end_mjd, mid_mjd, processed_at, status, stage,
                stage_updated_at, cal_applied, imagename, ra_deg, dec_deg,
                field_name, pointing_ra_deg, pointing_dec_deg
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ms.path, ms.start_mjd, ms.end_mjd, ms.mid_mjd, ms.processed_at,
                ms.status, ms.stage, ms.stage_updated_at, ms.cal_applied,
                ms.imagename, ms.ra_deg, ms.dec_deg, ms.field_name,
                ms.pointing_ra_deg, ms.pointing_dec_deg,
            ),
        )

    # Insert photometry records
    for phot in photometry_records:
        await conn.execute(
            """
            INSERT INTO photometry (
                id, source_id, image_path, ra_deg, dec_deg, mjd, flux_jy,
                flux_err_jy, peak_jyb, peak_err_jyb, snr, local_rms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                phot.id, phot.source_id, phot.image_path, phot.ra_deg, phot.dec_deg,
                phot.mjd, phot.flux_jy, phot.flux_err_jy, phot.peak_jyb,
                phot.peak_err_jyb, phot.snr, phot.local_rms,
            ),
        )

    await conn.commit()


async def populate_cal_registry_db(
    conn: "aiosqlite.Connection",
    caltables: Iterator[SampleCalTable] | None = None,
) -> None:
    """Populate a cal registry database with sample data.

    Args:
        conn: Active aiosqlite connection.
        caltables: CalTable records to insert (default: 5 sample records).
    """
    if caltables is None:
        caltables = sample_caltable_records()

    for cal in caltables:
        await conn.execute(
            """
            INSERT INTO caltables (
                path, table_type, set_name, cal_field, refant, created_at,
                source_ms_path, status, notes, order_index
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cal.path, cal.table_type, cal.set_name, cal.cal_field, cal.refant,
                cal.created_at, cal.source_ms_path, cal.status, cal.notes,
                cal.order_index,
            ),
        )

    await conn.commit()


async def create_populated_products_db(db_path: Path) -> Path:
    """Create a products database with schema and sample data.

    Args:
        db_path: Path to create the database at.

    Returns:
        Path to the created database.
    """
    import aiosqlite

    async with aiosqlite.connect(db_path) as conn:
        await create_products_schema(conn)
        await populate_products_db(conn)

    return db_path


async def create_populated_cal_registry_db(db_path: Path) -> Path:
    """Create a cal registry database with schema and sample data.

    Args:
        db_path: Path to create the database at.

    Returns:
        Path to the created database.
    """
    import aiosqlite

    async with aiosqlite.connect(db_path) as conn:
        await create_cal_registry_schema(conn)
        await populate_cal_registry_db(conn)

    return db_path


# =============================================================================
# Synchronous Context Manager Helpers (for integration tests)
# =============================================================================


import contextlib
import sqlite3
import tempfile
import shutil


def _create_products_schema_sync(conn: sqlite3.Connection) -> None:
    """Create all products database tables and indexes (sync version)."""
    cursor = conn.cursor()
    for create_sql in PRODUCTS_TABLES.values():
        cursor.execute(create_sql)
    for index_sql in PRODUCTS_INDEXES:
        cursor.execute(index_sql)
    conn.commit()


def _create_cal_registry_schema_sync(conn: sqlite3.Connection) -> None:
    """Create all calibration registry tables and indexes (sync version)."""
    cursor = conn.cursor()
    for create_sql in CAL_REGISTRY_TABLES.values():
        cursor.execute(create_sql)
    for index_sql in CAL_REGISTRY_INDEXES:
        cursor.execute(index_sql)
    conn.commit()


def _populate_products_db_sync(conn: sqlite3.Connection) -> None:
    """Populate products database with sample data (sync version)."""
    cursor = conn.cursor()
    
    # Insert images
    for img in sample_image_records():
        cursor.execute(
            """
            INSERT INTO images (
                id, path, ms_path, created_at, type, beam_major_arcsec, beam_minor_arcsec,
                beam_pa_deg, noise_jy, dynamic_range, pbcor, format, field_name,
                center_ra_deg, center_dec_deg, imsize_x, imsize_y, cellsize_arcsec,
                freq_ghz, bandwidth_mhz, integration_sec
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                img.id, img.path, img.ms_path, img.created_at, img.type,
                img.beam_major_arcsec, img.beam_minor_arcsec, img.beam_pa_deg,
                img.noise_jy, img.dynamic_range, img.pbcor, img.format,
                img.field_name, img.center_ra_deg, img.center_dec_deg,
                img.imsize_x, img.imsize_y, img.cellsize_arcsec,
                img.freq_ghz, img.bandwidth_mhz, img.integration_sec,
            ),
        )

    # Insert sources
    for src in sample_source_records():
        cursor.execute(
            """
            INSERT INTO sources (
                id, name, ra_deg, dec_deg, catalog_match, source_type,
                first_detected_mjd, last_detected_mjd, detection_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                src.id, src.name, src.ra_deg, src.dec_deg, src.catalog_match,
                src.source_type, src.first_detected_mjd, src.last_detected_mjd,
                src.detection_count,
            ),
        )

    # Insert jobs
    for job in sample_job_records():
        cursor.execute(
            """
            INSERT INTO batch_jobs (
                id, type, created_at, status, total_items, completed_items,
                failed_items, params
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.id, job.type, job.created_at, job.status, job.total_items,
                job.completed_items, job.failed_items, job.params,
            ),
        )

    # Insert MS index records
    for ms in sample_ms_index_records():
        cursor.execute(
            """
            INSERT INTO ms_index (
                path, start_mjd, end_mjd, mid_mjd, processed_at, status, stage,
                stage_updated_at, cal_applied, imagename, ra_deg, dec_deg,
                field_name, pointing_ra_deg, pointing_dec_deg
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ms.path, ms.start_mjd, ms.end_mjd, ms.mid_mjd, ms.processed_at,
                ms.status, ms.stage, ms.stage_updated_at, ms.cal_applied,
                ms.imagename, ms.ra_deg, ms.dec_deg, ms.field_name,
                ms.pointing_ra_deg, ms.pointing_dec_deg,
            ),
        )

    # Insert photometry records
    for phot in sample_photometry_records():
        cursor.execute(
            """
            INSERT INTO photometry (
                id, source_id, image_path, ra_deg, dec_deg, mjd, flux_jy,
                flux_err_jy, peak_jyb, peak_err_jyb, snr, local_rms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                phot.id, phot.source_id, phot.image_path, phot.ra_deg, phot.dec_deg,
                phot.mjd, phot.flux_jy, phot.flux_err_jy, phot.peak_jyb,
                phot.peak_err_jyb, phot.snr, phot.local_rms,
            ),
        )

    conn.commit()


def _populate_cal_registry_db_sync(
    conn: sqlite3.Connection,
    caltables: Iterator[SampleCalTable] | None = None,
) -> None:
    """Populate cal registry database with sample data (sync version)."""
    cursor = conn.cursor()
    
    if caltables is None:
        caltables = sample_caltable_records()

    for cal in caltables:
        cursor.execute(
            """
            INSERT INTO caltables (
                path, table_type, set_name, cal_field, refant, created_at,
                source_ms_path, status, notes, order_index
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cal.path, cal.table_type, cal.set_name, cal.cal_field, cal.refant,
                cal.created_at, cal.source_ms_path, cal.status, cal.notes,
                cal.order_index,
            ),
        )

    conn.commit()


@contextlib.contextmanager
def create_test_products_db():
    """Context manager that creates a temporary products database.
    
    Yields:
        Path to the temporary database file.
    
    Example:
        with create_test_products_db() as db_path:
            conn = sqlite3.connect(db_path)
            # ... use database ...
    """
    tmpdir = tempfile.mkdtemp(prefix="test_products_")
    db_path = Path(tmpdir) / "products.sqlite3"
    
    try:
        conn = sqlite3.connect(db_path)
        _create_products_schema_sync(conn)
        _populate_products_db_sync(conn)
        conn.close()
        yield db_path
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@contextlib.contextmanager
def create_test_cal_registry_db(caltables: Iterator[SampleCalTable] | None = None):
    """Context manager that creates a temporary cal registry database.
    
    Args:
        caltables: Optional calibration table records to insert.
    
    Yields:
        Path to the temporary database file.
    
    Example:
        with create_test_cal_registry_db() as db_path:
            conn = sqlite3.connect(db_path)
            # ... use database ...
    """
    tmpdir = tempfile.mkdtemp(prefix="test_cal_registry_")
    db_path = Path(tmpdir) / "cal_registry.sqlite3"
    
    try:
        conn = sqlite3.connect(db_path)
        _create_cal_registry_schema_sync(conn)
        _populate_cal_registry_db_sync(conn, caltables)
        conn.close()
        yield db_path
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@contextlib.contextmanager
def create_test_database_environment():
    """Context manager that creates both test databases.
    
    Yields:
        Dict with 'products' and 'cal_registry' paths.
    
    Example:
        with create_test_database_environment() as db_paths:
            products_db = db_paths["products"]
            cal_db = db_paths["cal_registry"]
    """
    tmpdir = tempfile.mkdtemp(prefix="test_env_")
    products_path = Path(tmpdir) / "products.sqlite3"
    cal_path = Path(tmpdir) / "cal_registry.sqlite3"
    
    try:
        # Create products database
        conn = sqlite3.connect(products_path)
        _create_products_schema_sync(conn)
        _populate_products_db_sync(conn)
        conn.close()
        
        # Create cal registry database
        conn = sqlite3.connect(cal_path)
        _create_cal_registry_schema_sync(conn)
        _populate_cal_registry_db_sync(conn)
        conn.close()
        
        yield {"products": products_path, "cal_registry": cal_path}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

