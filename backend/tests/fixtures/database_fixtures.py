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
    PRODUCTS_SCHEMA_SQL,
    CAL_REGISTRY_SCHEMA_SQL,
    create_products_schema,
    create_cal_registry_schema,
)

__all__ = [
    # Schema functions (re-exported from shared module)
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
    # Population functions
    "populate_products_db",
    "populate_cal_registry_db",
    "create_populated_products_db",
    "create_populated_cal_registry_db",
]


# =============================================================================
# Sample Data Classes
# =============================================================================


@dataclass
class SampleImage:
    """Sample image record for testing."""

    id: int
    ms_path: str
    field_name: str
    image_path: str
    thumbnail_path: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    rms_noise: float | None = None
    peak_flux: float | None = None
    dynamic_range: float | None = None
    beam_major: float | None = None
    beam_minor: float | None = None
    beam_pa: float | None = None
    frequency_mhz: float | None = None
    bandwidth_mhz: float | None = None
    integration_time: float | None = None
    weighting: str | None = None
    robust: float | None = None
    niter: int | None = None
    type: str = "continuum"
    beam: str | None = None


@dataclass
class SampleSource:
    """Sample source record for testing."""

    id: int
    image_id: int
    name: str
    ra: float
    dec: float
    flux: float
    flux_err: float | None = None
    peak_flux: float | None = None
    peak_flux_err: float | None = None
    major_axis: float | None = None
    minor_axis: float | None = None
    position_angle: float | None = None
    snr: float | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class SampleJob:
    """Sample batch job record for testing."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_type: str = "imaging"
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None
    parameters: str = "{}"
    progress: float = 0.0
    total_items: int = 0
    completed_items: int = 0


@dataclass
class SampleCalTable:
    """Sample calibration table record for testing."""

    id: int
    ms_path: str
    cal_type: str
    cal_path: str
    field_name: str | None = None
    spw: str | None = None
    antenna: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    solint: str | None = None
    refant: str | None = None
    minsnr: float | None = None
    calmode: str | None = None


@dataclass
class SampleMSIndex:
    """Sample MS index record for testing."""

    id: int
    ms_path: str
    obs_id: str
    start_time: str
    end_time: str
    n_channels: int = 16384
    n_polarizations: int = 4
    n_baselines: int = 2016
    n_fields: int = 24
    total_size_bytes: int = 1000000000
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = "complete"


@dataclass
class SamplePhotometry:
    """Sample photometry record for testing."""

    id: int
    image_id: int
    source_name: str
    ra: float
    dec: float
    flux_jy: float
    flux_err_jy: float | None = None
    peak_flux_jy: float | None = None
    rms_jy: float | None = None
    snr: float | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


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
    base_time = datetime.utcnow()
    for i in range(count):
        created = (base_time - timedelta(hours=i)).isoformat()
        yield SampleImage(
            id=i + 1,
            ms_path=f"/stage/dsa110-contimg/ms/obs_{i:04d}.ms",
            field_name=f"field_{i}",
            image_path=f"/stage/dsa110-contimg/images/obs_{i:04d}.fits",
            thumbnail_path=f"/stage/dsa110-contimg/thumbnails/obs_{i:04d}.png",
            created_at=created,
            rms_noise=0.001 + i * 0.0001,
            peak_flux=0.1 + i * 0.01,
            dynamic_range=100.0 + i * 10,
            beam_major=30.0,
            beam_minor=25.0,
            beam_pa=45.0,
            frequency_mhz=1400.0,
            bandwidth_mhz=256.0,
            integration_time=300.0,
            weighting="briggs",
            robust=0.0,
            niter=10000,
            type="continuum",
            beam="30x25",
        )


def sample_source_records(count: int = 10, image_id: int = 1) -> Iterator[SampleSource]:
    """Generate sample source records for testing.

    Args:
        count: Number of records to generate.
        image_id: Image ID to associate sources with.

    Yields:
        SampleSource instances with realistic test data.
    """
    base_ra = 180.0  # degrees
    base_dec = 37.0  # degrees (DSA-110 declination)
    for i in range(count):
        yield SampleSource(
            id=i + 1,
            image_id=image_id,
            name=f"J{int(base_ra/15):02d}{int((base_ra%15)*4):02d}+{int(base_dec):02d}{int((base_dec%1)*60):02d}_{i}",
            ra=base_ra + i * 0.01,
            dec=base_dec + i * 0.01,
            flux=0.01 + i * 0.005,
            flux_err=0.001,
            peak_flux=0.012 + i * 0.005,
            peak_flux_err=0.001,
            major_axis=30.0,
            minor_axis=25.0,
            position_angle=45.0,
            snr=10.0 + i * 2,
        )


def sample_job_records(count: int = 3) -> Iterator[SampleJob]:
    """Generate sample batch job records for testing.

    Args:
        count: Number of records to generate.

    Yields:
        SampleJob instances with varying statuses.
    """
    statuses = ["pending", "running", "completed", "failed"]
    base_time = datetime.utcnow()
    for i in range(count):
        status = statuses[i % len(statuses)]
        created = (base_time - timedelta(hours=i)).isoformat()
        started = (base_time - timedelta(hours=i) + timedelta(minutes=5)).isoformat() if status != "pending" else None
        completed = (base_time - timedelta(hours=i) + timedelta(minutes=30)).isoformat() if status in ("completed", "failed") else None
        error = "Test error message" if status == "failed" else None

        yield SampleJob(
            id=str(uuid.uuid4()),
            job_type=["imaging", "calibration", "photometry"][i % 3],
            status=status,
            created_at=created,
            started_at=started,
            completed_at=completed,
            error_message=error,
            parameters='{"test": true}',
            progress=100.0 if status == "completed" else (50.0 if status == "running" else 0.0),
            total_items=10,
            completed_items=10 if status == "completed" else (5 if status == "running" else 0),
        )


def sample_caltable_records(count: int = 5) -> Iterator[SampleCalTable]:
    """Generate sample calibration table records for testing.

    Args:
        count: Number of records to generate.

    Yields:
        SampleCalTable instances with realistic test data.
    """
    cal_types = ["bandpass", "gain", "delay", "flux"]
    base_time = datetime.utcnow()
    for i in range(count):
        cal_type = cal_types[i % len(cal_types)]
        created = (base_time - timedelta(hours=i)).isoformat()
        yield SampleCalTable(
            id=i + 1,
            ms_path=f"/stage/dsa110-contimg/ms/obs_{i:04d}.ms",
            cal_type=cal_type,
            cal_path=f"/stage/dsa110-contimg/cal/obs_{i:04d}.{cal_type[:1]}cal",
            field_name="3C286" if cal_type == "flux" else f"field_{i}",
            spw="0:0~1023",
            antenna="",
            created_at=created,
            solint="inf" if cal_type == "bandpass" else "int",
            refant="ea01",
            minsnr=3.0,
            calmode="ap" if cal_type == "gain" else "p",
        )


def sample_ms_index_records(count: int = 5) -> Iterator[SampleMSIndex]:
    """Generate sample MS index records for testing.

    Args:
        count: Number of records to generate.

    Yields:
        SampleMSIndex instances with realistic test data.
    """
    base_time = datetime.utcnow()
    for i in range(count):
        start = (base_time - timedelta(hours=i)).isoformat()
        end = (base_time - timedelta(hours=i) + timedelta(minutes=5)).isoformat()
        yield SampleMSIndex(
            id=i + 1,
            ms_path=f"/stage/dsa110-contimg/ms/obs_{i:04d}.ms",
            obs_id=f"obs_{i:04d}",
            start_time=start,
            end_time=end,
            n_channels=16384,
            n_polarizations=4,
            n_baselines=2016,
            n_fields=24,
            total_size_bytes=1000000000 + i * 100000000,
            status="complete",
        )


def sample_photometry_records(count: int = 10, image_id: int = 1) -> Iterator[SamplePhotometry]:
    """Generate sample photometry records for testing.

    Args:
        count: Number of records to generate.
        image_id: Image ID to associate records with.

    Yields:
        SamplePhotometry instances with realistic test data.
    """
    base_ra = 180.0
    base_dec = 37.0
    for i in range(count):
        yield SamplePhotometry(
            id=i + 1,
            image_id=image_id,
            source_name=f"source_{i:03d}",
            ra=base_ra + i * 0.01,
            dec=base_dec + i * 0.01,
            flux_jy=0.01 + i * 0.005,
            flux_err_jy=0.001,
            peak_flux_jy=0.012 + i * 0.005,
            rms_jy=0.0005,
            snr=20.0 + i * 5,
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
                id, ms_path, field_name, image_path, thumbnail_path, created_at,
                rms_noise, peak_flux, dynamic_range, beam_major, beam_minor, beam_pa,
                frequency_mhz, bandwidth_mhz, integration_time, weighting, robust, niter,
                type, beam
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                img.id, img.ms_path, img.field_name, img.image_path, img.thumbnail_path,
                img.created_at, img.rms_noise, img.peak_flux, img.dynamic_range,
                img.beam_major, img.beam_minor, img.beam_pa, img.frequency_mhz,
                img.bandwidth_mhz, img.integration_time, img.weighting, img.robust,
                img.niter, img.type, img.beam,
            ),
        )

    # Insert sources
    for src in sources:
        await conn.execute(
            """
            INSERT INTO sources (
                id, image_id, name, ra, dec, flux, flux_err, peak_flux, peak_flux_err,
                major_axis, minor_axis, position_angle, snr, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                src.id, src.image_id, src.name, src.ra, src.dec, src.flux, src.flux_err,
                src.peak_flux, src.peak_flux_err, src.major_axis, src.minor_axis,
                src.position_angle, src.snr, src.created_at,
            ),
        )

    # Insert jobs
    for job in jobs:
        await conn.execute(
            """
            INSERT INTO batch_jobs (
                id, job_type, status, created_at, started_at, completed_at,
                error_message, parameters, progress, total_items, completed_items
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.id, job.job_type, job.status, job.created_at, job.started_at,
                job.completed_at, job.error_message, job.parameters, job.progress,
                job.total_items, job.completed_items,
            ),
        )

    # Insert MS index records
    for ms in ms_records:
        await conn.execute(
            """
            INSERT INTO ms_index (
                id, ms_path, obs_id, start_time, end_time, n_channels, n_polarizations,
                n_baselines, n_fields, total_size_bytes, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ms.id, ms.ms_path, ms.obs_id, ms.start_time, ms.end_time, ms.n_channels,
                ms.n_polarizations, ms.n_baselines, ms.n_fields, ms.total_size_bytes,
                ms.created_at, ms.status,
            ),
        )

    # Insert photometry records
    for phot in photometry_records:
        await conn.execute(
            """
            INSERT INTO photometry (
                id, image_id, source_name, ra, dec, flux_jy, flux_err_jy,
                peak_flux_jy, rms_jy, snr, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                phot.id, phot.image_id, phot.source_name, phot.ra, phot.dec,
                phot.flux_jy, phot.flux_err_jy, phot.peak_flux_jy, phot.rms_jy,
                phot.snr, phot.created_at,
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
                id, ms_path, cal_type, cal_path, field_name, spw, antenna,
                created_at, solint, refant, minsnr, calmode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cal.id, cal.ms_path, cal.cal_type, cal.cal_path, cal.field_name,
                cal.spw, cal.antenna, cal.created_at, cal.solint, cal.refant,
                cal.minsnr, cal.calmode,
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
