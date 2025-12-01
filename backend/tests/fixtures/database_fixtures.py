"""
Database fixtures for integration tests.

Provides SQLite databases pre-populated with test data for integration testing
the API endpoints against realistic data.

Usage:
    from tests.fixtures.database_fixtures import (
        create_test_products_db,
        create_test_cal_registry_db,
        sample_image_records,
        sample_source_records,
    )
"""

import os
import sqlite3
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Generator, List, Optional
import uuid


@dataclass
class SampleImage:
    """Sample image record for testing."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    path: str = "/stage/dsa110-contimg/images/test_image.fits"
    ms_path: str = "/stage/dsa110-contimg/ms/test_obs.ms"
    cal_table: str = "/stage/dsa110-contimg/cal/test.bcal"
    center_ra_deg: float = 180.0
    center_dec_deg: float = 37.0
    qa_grade: str = "A"
    qa_summary: str = "Good image quality"
    run_id: str = field(default_factory=lambda: f"run_{uuid.uuid4().hex[:8]}")
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class SampleSource:
    """Sample source record for testing."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "J1234+5678"
    ra_deg: float = 123.4
    dec_deg: float = 56.78
    latest_image_id: Optional[str] = None
    contributing_images: str = "[]"  # JSON array


@dataclass
class SampleJob:
    """Sample job record for testing."""
    run_id: str = field(default_factory=lambda: f"run_{uuid.uuid4().hex[:8]}")
    input_ms_path: str = "/stage/dsa110-contimg/ms/test_obs.ms"
    cal_table_path: str = "/stage/dsa110-contimg/cal/test.bcal"
    phase_center_ra: float = 180.0
    phase_center_dec: float = 37.0
    qa_grade: str = "B"
    qa_summary: str = "Acceptable quality"
    started_at: float = field(default_factory=lambda: datetime.now().timestamp())
    finished_at: Optional[float] = None
    status: str = "completed"


@dataclass
class SampleCalTable:
    """Sample calibration table record for testing."""
    path: str = "/stage/dsa110-contimg/cal/test.bcal"
    table_type: str = "bandpass"
    set_name: str = "cal_set_001"
    cal_field: str = "3C286"
    refant: str = "DSA-001"
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    source_ms_path: str = "/stage/dsa110-contimg/ms/cal_obs.ms"
    status: str = "active"
    notes: str = "Standard calibration"


def sample_image_records(count: int = 5) -> List[SampleImage]:
    """Generate sample image records."""
    images = []
    base_time = datetime.now() - timedelta(days=count)
    
    for i in range(count):
        img = SampleImage(
            path=f"/stage/dsa110-contimg/images/image_{i:03d}.fits",
            ms_path=f"/stage/dsa110-contimg/ms/obs_{i:03d}.ms",
            cal_table=f"/stage/dsa110-contimg/cal/cal_{i:03d}.bcal",
            center_ra_deg=180.0 + i * 0.5,
            center_dec_deg=37.0 + i * 0.1,
            qa_grade=["A", "B", "C", "A", "B"][i % 5],
            created_at=(base_time + timedelta(days=i)).timestamp(),
        )
        images.append(img)
    
    return images


def sample_source_records(count: int = 10) -> List[SampleSource]:
    """Generate sample source records."""
    sources = []
    
    for i in range(count):
        src = SampleSource(
            name=f"J{1200 + i:04d}+{3700 + i * 10:04d}",
            ra_deg=120.0 + i * 0.1,
            dec_deg=37.0 + i * 0.01,
        )
        sources.append(src)
    
    return sources


def sample_job_records(count: int = 5) -> List[SampleJob]:
    """Generate sample job records."""
    jobs = []
    base_time = datetime.now() - timedelta(days=count)
    
    for i in range(count):
        started = base_time + timedelta(days=i)
        finished = started + timedelta(minutes=30)
        
        job = SampleJob(
            input_ms_path=f"/stage/dsa110-contimg/ms/obs_{i:03d}.ms",
            cal_table_path=f"/stage/dsa110-contimg/cal/cal_{i:03d}.bcal",
            phase_center_ra=180.0 + i * 0.5,
            phase_center_dec=37.0 + i * 0.1,
            qa_grade=["A", "B", "C", "A", "B"][i % 5],
            started_at=started.timestamp(),
            finished_at=finished.timestamp(),
            status="completed" if i < count - 1 else "running",
        )
        jobs.append(job)
    
    return jobs


def sample_cal_table_records(count: int = 3) -> List[SampleCalTable]:
    """Generate sample calibration table records."""
    tables = []
    calibrators = ["3C286", "3C48", "3C147"]
    table_types = ["bandpass", "gain", "delay"]
    
    for i in range(count):
        cal = SampleCalTable(
            path=f"/stage/dsa110-contimg/cal/cal_{i:03d}.{table_types[i % 3][0]}cal",
            table_type=table_types[i % 3],
            set_name=f"cal_set_{i:03d}",
            cal_field=calibrators[i % 3],
        )
        tables.append(cal)
    
    return tables


def create_products_schema(conn: sqlite3.Connection) -> None:
    """Create products database schema."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS images (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            ms_path TEXT,
            cal_table TEXT,
            center_ra_deg REAL,
            center_dec_deg REAL,
            qa_grade TEXT,
            qa_summary TEXT,
            run_id TEXT,
            created_at REAL
        );
        
        CREATE TABLE IF NOT EXISTS sources (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            latest_image_id TEXT,
            contributing_images TEXT,
            FOREIGN KEY (latest_image_id) REFERENCES images(id)
        );
        
        CREATE TABLE IF NOT EXISTS jobs (
            run_id TEXT PRIMARY KEY,
            input_ms_path TEXT,
            cal_table_path TEXT,
            phase_center_ra REAL,
            phase_center_dec REAL,
            qa_grade TEXT,
            qa_summary TEXT,
            started_at REAL,
            finished_at REAL,
            status TEXT
        );
        
        CREATE TABLE IF NOT EXISTS measurement_sets (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            created_at REAL,
            observation_time TEXT,
            num_channels INTEGER,
            num_antennas INTEGER,
            total_size_bytes INTEGER
        );
        
        CREATE INDEX IF NOT EXISTS idx_images_run_id ON images(run_id);
        CREATE INDEX IF NOT EXISTS idx_sources_name ON sources(name);
        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
    """)
    conn.commit()


def create_cal_registry_schema(conn: sqlite3.Connection) -> None:
    """Create calibration registry database schema."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS caltables (
            path TEXT PRIMARY KEY,
            table_type TEXT NOT NULL,
            set_name TEXT,
            cal_field TEXT,
            refant TEXT,
            created_at REAL,
            source_ms_path TEXT,
            status TEXT DEFAULT 'active',
            notes TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_caltables_type ON caltables(table_type);
        CREATE INDEX IF NOT EXISTS idx_caltables_set ON caltables(set_name);
    """)
    conn.commit()


def populate_products_db(
    conn: sqlite3.Connection,
    images: Optional[List[SampleImage]] = None,
    sources: Optional[List[SampleSource]] = None,
    jobs: Optional[List[SampleJob]] = None,
) -> None:
    """Populate products database with test data."""
    if images is None:
        images = sample_image_records()
    if sources is None:
        sources = sample_source_records()
    if jobs is None:
        jobs = sample_job_records()
    
    # Insert images
    for img in images:
        conn.execute(
            """
            INSERT OR REPLACE INTO images 
            (id, path, ms_path, cal_table, center_ra_deg, center_dec_deg, 
             qa_grade, qa_summary, run_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (img.id, img.path, img.ms_path, img.cal_table, img.center_ra_deg,
             img.center_dec_deg, img.qa_grade, img.qa_summary, img.run_id,
             img.created_at)
        )
    
    # Insert sources
    for src in sources:
        conn.execute(
            """
            INSERT OR REPLACE INTO sources
            (id, name, ra_deg, dec_deg, latest_image_id, contributing_images)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (src.id, src.name, src.ra_deg, src.dec_deg, 
             src.latest_image_id, src.contributing_images)
        )
    
    # Insert jobs
    for job in jobs:
        conn.execute(
            """
            INSERT OR REPLACE INTO jobs
            (run_id, input_ms_path, cal_table_path, phase_center_ra, phase_center_dec,
             qa_grade, qa_summary, started_at, finished_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (job.run_id, job.input_ms_path, job.cal_table_path, job.phase_center_ra,
             job.phase_center_dec, job.qa_grade, job.qa_summary, job.started_at,
             job.finished_at, job.status)
        )
    
    conn.commit()


def populate_cal_registry_db(
    conn: sqlite3.Connection,
    tables: Optional[List[SampleCalTable]] = None,
) -> None:
    """Populate calibration registry with test data."""
    if tables is None:
        tables = sample_cal_table_records()
    
    for tbl in tables:
        conn.execute(
            """
            INSERT OR REPLACE INTO caltables
            (path, table_type, set_name, cal_field, refant, created_at,
             source_ms_path, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (tbl.path, tbl.table_type, tbl.set_name, tbl.cal_field, tbl.refant,
             tbl.created_at, tbl.source_ms_path, tbl.status, tbl.notes)
        )
    
    conn.commit()


@contextmanager
def create_test_products_db(
    images: Optional[List[SampleImage]] = None,
    sources: Optional[List[SampleSource]] = None,
    jobs: Optional[List[SampleJob]] = None,
) -> Generator[Path, None, None]:
    """
    Create a temporary products database with test data.
    
    Args:
        images: Custom image records (uses defaults if None)
        sources: Custom source records (uses defaults if None)
        jobs: Custom job records (uses defaults if None)
        
    Yields:
        Path to the temporary database file
    """
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = Path(f.name)
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        
        create_products_schema(conn)
        populate_products_db(conn, images, sources, jobs)
        
        conn.close()
        yield db_path
    finally:
        if db_path.exists():
            os.unlink(db_path)


@contextmanager
def create_test_cal_registry_db(
    tables: Optional[List[SampleCalTable]] = None,
) -> Generator[Path, None, None]:
    """
    Create a temporary calibration registry database with test data.
    
    Args:
        tables: Custom calibration table records (uses defaults if None)
        
    Yields:
        Path to the temporary database file
    """
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = Path(f.name)
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        
        create_cal_registry_schema(conn)
        populate_cal_registry_db(conn, tables)
        
        conn.close()
        yield db_path
    finally:
        if db_path.exists():
            os.unlink(db_path)


@contextmanager
def create_test_database_environment() -> Generator[Dict[str, Path], None, None]:
    """
    Create a complete test database environment.
    
    Sets up both products and cal_registry databases with test data.
    
    Yields:
        Dict with 'products' and 'cal_registry' paths
    """
    with create_test_products_db() as products_path:
        with create_test_cal_registry_db() as cal_path:
            yield {
                "products": products_path,
                "cal_registry": cal_path,
            }
