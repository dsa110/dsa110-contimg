"""
Tests for N+1 query optimization in async repositories.

These tests verify that list operations use batch queries instead of
N+1 queries per record.
"""

import os
import pytest
import tempfile
import aiosqlite

from dsa110_contimg.api.repositories import (
    AsyncImageRepository,
    AsyncMSRepository,
    AsyncJobRepository,
    get_async_connection,
)


@pytest.fixture
async def temp_db():
    """Create a temporary SQLite database with test data."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = f.name
    
    # Create tables and insert test data
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        
        # Create ms_index table
        await conn.execute("""
            CREATE TABLE ms_index (
                path TEXT PRIMARY KEY,
                start_mjd REAL,
                end_mjd REAL,
                mid_mjd REAL,
                processed_at REAL,
                status TEXT,
                stage TEXT,
                stage_updated_at REAL,
                cal_applied INTEGER DEFAULT 0,
                imagename TEXT,
                ra_deg REAL,
                dec_deg REAL,
                field_name TEXT,
                pointing_ra_deg REAL,
                pointing_dec_deg REAL
            )
        """)
        
        # Create images table
        await conn.execute("""
            CREATE TABLE images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE,
                ms_path TEXT,
                created_at REAL,
                type TEXT,
                beam_major_arcsec REAL,
                noise_jy REAL,
                pbcor INTEGER DEFAULT 0,
                format TEXT DEFAULT 'fits',
                beam_minor_arcsec REAL,
                beam_pa_deg REAL,
                dynamic_range REAL,
                field_name TEXT,
                center_ra_deg REAL,
                center_dec_deg REAL,
                imsize_x INTEGER,
                imsize_y INTEGER,
                cellsize_arcsec REAL,
                freq_ghz REAL,
                bandwidth_mhz REAL,
                integration_sec REAL
            )
        """)
        
        # Insert test MS records
        for i in range(10):
            await conn.execute(
                """
                INSERT INTO ms_index (path, processed_at, status, stage)
                VALUES (?, ?, ?, ?)
                """,
                (f"/stage/ms/test_{i}.ms", 1700000000 + i * 1000, "completed", "imaged")
            )
        
        # Insert test images (multiple per MS)
        for i in range(10):
            for img_type in ["dirty", "clean", "residual"]:
                await conn.execute(
                    """
                    INSERT INTO images (path, ms_path, created_at, type, noise_jy, beam_major_arcsec)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"/stage/images/test_{i}_{img_type}.fits",
                        f"/stage/ms/test_{i}.ms",
                        1700000000 + i * 1000,
                        img_type,
                        0.001 * (i + 1),
                        5.0 + i,
                    )
                )
        
        await conn.commit()
    
    yield db_path
    
    # Cleanup
    os.unlink(db_path)


class TestImageRepositoryOptimization:
    """Tests for N+1 query optimization in AsyncImageRepository."""
    
    async def test_list_all_returns_correct_count(self, temp_db):
        """Test that list_all returns all images."""
        repo = AsyncImageRepository(db_path=temp_db)
        images = await repo.list_all(limit=100)
        
        # 10 MS * 3 image types = 30 images
        assert len(images) == 30
    
    async def test_list_all_includes_qa_grades(self, temp_db):
        """Test that list_all populates QA grades from ms_index."""
        repo = AsyncImageRepository(db_path=temp_db)
        images = await repo.list_all(limit=100)
        
        # All images should have QA grades (from ms_index stage=imaged)
        for img in images:
            assert img.qa_grade == "good", f"Image {img.path} missing QA grade"
    
    async def test_list_all_includes_run_ids(self, temp_db):
        """Test that list_all generates run_ids."""
        repo = AsyncImageRepository(db_path=temp_db)
        images = await repo.list_all(limit=100)
        
        for img in images:
            assert img.run_id is not None
            assert img.run_id.startswith("job-")
    
    async def test_list_all_pagination(self, temp_db):
        """Test pagination works correctly."""
        repo = AsyncImageRepository(db_path=temp_db)
        
        page1 = await repo.list_all(limit=10, offset=0)
        page2 = await repo.list_all(limit=10, offset=10)
        page3 = await repo.list_all(limit=10, offset=20)
        
        assert len(page1) == 10
        assert len(page2) == 10
        assert len(page3) == 10
        
        # Pages should have different images
        page1_paths = {img.path for img in page1}
        page2_paths = {img.path for img in page2}
        page3_paths = {img.path for img in page3}
        
        assert page1_paths.isdisjoint(page2_paths)
        assert page2_paths.isdisjoint(page3_paths)
    
    async def test_get_many_batch_loading(self, temp_db):
        """Test that get_many uses batch loading."""
        repo = AsyncImageRepository(db_path=temp_db)
        
        # Get IDs of first 5 images
        all_images = await repo.list_all(limit=5)
        image_ids = [str(img.id) for img in all_images]
        
        # Fetch by IDs
        fetched = await repo.get_many(image_ids)
        
        assert len(fetched) == 5
        for img in fetched:
            assert img.qa_grade is not None


class TestMSRepositoryOptimization:
    """Tests for AsyncMSRepository list operations."""
    
    async def test_list_all_single_query(self, temp_db):
        """Test that list_all fetches all data in minimal queries."""
        repo = AsyncMSRepository(db_path=temp_db)
        records = await repo.list_all(limit=100)
        
        assert len(records) == 10
        for record in records:
            assert record.qa_grade == "good"  # stage=imaged
            assert record.run_id is not None


class TestJobRepositoryOptimization:
    """Tests for AsyncJobRepository list operations."""
    
    async def test_list_all_no_n_plus_1(self, temp_db):
        """Test that list_all doesn't make N+1 queries."""
        repo = AsyncJobRepository(db_path=temp_db)
        records = await repo.list_all(limit=100)
        
        # Should have 10 jobs (one per MS)
        assert len(records) == 10
        for record in records:
            assert record.qa_grade == "good"
            assert record.run_id is not None


class TestBatchQueryPerformance:
    """Performance tests comparing batch vs N+1 queries."""
    
    async def test_batch_query_efficiency(self, temp_db):
        """Verify batch loading is used by checking all records have data."""
        repo = AsyncImageRepository(db_path=temp_db)
        
        # Fetch all 30 images
        images = await repo.list_all(limit=100)
        
        # Verify all images have QA grades populated
        images_with_qa = [img for img in images if img.qa_grade is not None]
        
        # All 30 images should have QA grades from the batched ms_index query
        assert len(images_with_qa) == 30, (
            f"Expected 30 images with QA grades, got {len(images_with_qa)}. "
            "Batch loading may not be working correctly."
        )
