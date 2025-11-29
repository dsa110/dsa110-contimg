"""
Tests for SQLAlchemy-based repository classes.

These tests use in-memory SQLite databases for isolation and speed.
"""

import pytest
import time

from dsa110_contimg.database import (
    get_engine,
    get_session,
    reset_engines,
    ProductsBase,
    CalRegistryBase,
    HDF5Base,
    DataRegistryBase,
    MSIndex,
    Image,
    Photometry,
    Caltable,
    HDF5FileIndex,
    DataRegistry,
)
from dsa110_contimg.database.repositories import (
    ImageRepository,
    MSRepository,
    CaltableRepository,
    PhotometryRepository,
    HDF5IndexRepository,
    DataRegistryRepository,
)


@pytest.fixture(autouse=True)
def reset_db_state():
    """Reset database engines before each test."""
    reset_engines()
    yield
    reset_engines()


@pytest.fixture
def products_db():
    """Create and initialize products database for testing."""
    engine = get_engine("products", in_memory=True)
    ProductsBase.metadata.create_all(engine)
    return engine


@pytest.fixture
def cal_registry_db():
    """Create and initialize cal_registry database for testing."""
    engine = get_engine("cal_registry", in_memory=True)
    CalRegistryBase.metadata.create_all(engine)
    return engine


@pytest.fixture
def hdf5_db():
    """Create and initialize hdf5 database for testing."""
    engine = get_engine("hdf5", in_memory=True)
    HDF5Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def data_registry_db():
    """Create and initialize data_registry database for testing."""
    engine = get_engine("data_registry", in_memory=True)
    DataRegistryBase.metadata.create_all(engine)
    return engine


@pytest.fixture
def sample_ms_data(products_db):
    """Create sample MS data for testing."""
    with get_session("products", in_memory=True) as session:
        # Create several MS records
        for i in range(5):
            ms = MSIndex(
                path=f"/stage/ms/test_{i}.ms",
                start_mjd=60000.0 + i,
                end_mjd=60000.1 + i,
                mid_mjd=60000.05 + i,
                processed_at=time.time() - i * 3600,
                status="completed" if i < 3 else "pending",
                stage="imaged" if i < 2 else "calibrated",
            )
            session.add(ms)
    
    return products_db


@pytest.fixture
def sample_image_data(sample_ms_data):
    """Create sample image data for testing."""
    with get_session("products", in_memory=True) as session:
        # Create images for the first 3 MS files
        for i in range(3):
            for img_type in ["dirty", "clean"]:
                image = Image(
                    path=f"/stage/images/test_{i}_{img_type}.fits",
                    ms_path=f"/stage/ms/test_{i}.ms",
                    created_at=time.time() - i * 3600,
                    type=img_type,
                    beam_major_arcsec=5.0 + i,
                    noise_jy=0.001 * (i + 1),
                )
                session.add(image)
    
    return sample_ms_data


class TestImageRepository:
    """Tests for ImageRepository."""
    
    def test_list_all_empty(self, products_db):
        """Test listing images when database is empty."""
        repo = ImageRepository()
        
        # Patch to use in-memory database
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "dsa110_contimg.database.repositories.get_session",
                lambda db_name, in_memory=False: get_session(db_name, in_memory=True)
            )
            mp.setattr(
                "dsa110_contimg.database.repositories.get_readonly_session",
                lambda db_name, in_memory=False: get_session(db_name, in_memory=True)
            )
            
            images = repo.list_all()
            assert images == []
    
    def test_list_all_with_data(self, sample_image_data):
        """Test listing images with data."""
        # Directly query for now since we're testing the ORM
        with get_session("products", in_memory=True) as session:
            images = session.query(Image).order_by(
                Image.created_at.desc()
            ).all()
            
            assert len(images) == 6  # 3 MS * 2 types
    
    def test_filter_by_type(self, sample_image_data):
        """Test filtering images by type."""
        with get_session("products", in_memory=True) as session:
            dirty_images = session.query(Image).filter(
                Image.type == "dirty"
            ).all()
            
            assert len(dirty_images) == 3
            for img in dirty_images:
                assert img.type == "dirty"
    
    def test_get_by_id(self, sample_image_data):
        """Test getting image by ID."""
        with get_session("products", in_memory=True) as session:
            # Get first image
            first = session.query(Image).first()
            assert first is not None
            
            # Query by ID
            result = session.query(Image).filter(
                Image.id == first.id
            ).first()
            
            assert result is not None
            assert result.path == first.path
    
    def test_get_by_path(self, sample_image_data):
        """Test getting image by path."""
        with get_session("products", in_memory=True) as session:
            result = session.query(Image).filter(
                Image.path == "/stage/images/test_0_dirty.fits"
            ).first()
            
            assert result is not None
            assert result.type == "dirty"


class TestMSRepository:
    """Tests for MSRepository."""
    
    def test_list_all(self, sample_ms_data):
        """Test listing all MS records."""
        with get_session("products", in_memory=True) as session:
            records = session.query(MSIndex).order_by(
                MSIndex.processed_at.desc()
            ).all()
            
            assert len(records) == 5
    
    def test_filter_by_status(self, sample_ms_data):
        """Test filtering MS by status."""
        with get_session("products", in_memory=True) as session:
            completed = session.query(MSIndex).filter(
                MSIndex.status == "completed"
            ).all()
            
            assert len(completed) == 3
    
    def test_filter_by_stage(self, sample_ms_data):
        """Test filtering MS by stage."""
        with get_session("products", in_memory=True) as session:
            imaged = session.query(MSIndex).filter(
                MSIndex.stage == "imaged"
            ).all()
            
            assert len(imaged) == 2
    
    def test_update_stage(self, sample_ms_data):
        """Test updating MS stage."""
        with get_session("products", in_memory=True) as session:
            ms = session.query(MSIndex).filter(
                MSIndex.path == "/stage/ms/test_0.ms"
            ).first()
            
            assert ms is not None
            ms.stage = "mosaicked"
            ms.stage_updated_at = time.time()
        
        # Verify update persisted
        with get_session("products", in_memory=True) as session:
            ms = session.query(MSIndex).filter(
                MSIndex.path == "/stage/ms/test_0.ms"
            ).first()
            
            assert ms.stage == "mosaicked"


class TestCaltableRepository:
    """Tests for CaltableRepository."""
    
    def test_create_and_query(self, cal_registry_db):
        """Test creating and querying calibration tables."""
        with get_session("cal_registry", in_memory=True) as session:
            # Create cal tables
            for i, table_type in enumerate(["bandpass", "gain", "flux"]):
                cal = Caltable(
                    set_name="3C286_test",
                    path=f"/cal/{table_type}.tb",
                    table_type=table_type,
                    order_index=i,
                    cal_field="3C286",
                    created_at=time.time(),
                    status="active",
                    valid_start_mjd=60000.0,
                    valid_end_mjd=60100.0,
                )
                session.add(cal)
        
        # Query back
        with get_session("cal_registry", in_memory=True) as session:
            cals = session.query(Caltable).filter(
                Caltable.set_name == "3C286_test"
            ).order_by(Caltable.order_index).all()
            
            assert len(cals) == 3
            assert cals[0].table_type == "bandpass"
            assert cals[1].table_type == "gain"
            assert cals[2].table_type == "flux"
    
    def test_find_valid_for_mjd(self, cal_registry_db):
        """Test finding valid calibration tables for a given MJD."""
        with get_session("cal_registry", in_memory=True) as session:
            # Create cal tables with different validity windows
            cal1 = Caltable(
                set_name="set1",
                path="/cal/early.tb",
                table_type="bandpass",
                order_index=0,
                created_at=time.time(),
                status="active",
                valid_start_mjd=60000.0,
                valid_end_mjd=60050.0,
            )
            cal2 = Caltable(
                set_name="set2",
                path="/cal/late.tb",
                table_type="bandpass",
                order_index=0,
                created_at=time.time(),
                status="active",
                valid_start_mjd=60050.0,
                valid_end_mjd=60100.0,
            )
            session.add_all([cal1, cal2])
        
        # Query for MJD 60025 (should get cal1)
        with get_session("cal_registry", in_memory=True) as session:
            valid_cals = session.query(Caltable).filter(
                Caltable.status == "active",
                Caltable.valid_start_mjd <= 60025.0,
                Caltable.valid_end_mjd >= 60025.0,
            ).all()
            
            assert len(valid_cals) == 1
            assert valid_cals[0].path == "/cal/early.tb"


class TestPhotometryRepository:
    """Tests for PhotometryRepository."""
    
    def test_create_and_query_lightcurve(self, sample_image_data):
        """Test creating and querying lightcurve data."""
        with get_session("products", in_memory=True) as session:
            # Create photometry entries
            for i in range(5):
                phot = Photometry(
                    source_id="J1234+5678",
                    image_path=f"/stage/images/test_0_clean.fits",
                    ra_deg=123.456,
                    dec_deg=56.789,
                    peak_jyb=0.1 + i * 0.01,
                    measured_at=time.time(),
                    snr=50.0 - i,
                    mjd=60000.0 + i,
                    flux_jy=0.1 + i * 0.01,
                )
                session.add(phot)
        
        # Query lightcurve
        with get_session("products", in_memory=True) as session:
            lightcurve = session.query(Photometry).filter(
                Photometry.source_id == "J1234+5678"
            ).order_by(Photometry.mjd).all()
            
            assert len(lightcurve) == 5
            assert lightcurve[0].mjd < lightcurve[-1].mjd
    
    def test_aggregate_sources(self, sample_image_data):
        """Test aggregating sources with counts."""
        from sqlalchemy import func
        
        with get_session("products", in_memory=True) as session:
            # Create photometry for multiple sources
            for source_idx in range(3):
                for i in range(source_idx + 1):  # 1, 2, 3 entries per source
                    phot = Photometry(
                        source_id=f"J{source_idx:04d}+0000",
                        image_path=f"/stage/images/test_0_clean.fits",
                        ra_deg=100.0 + source_idx,
                        dec_deg=0.0,
                        peak_jyb=0.1,
                        measured_at=time.time(),
                        mjd=60000.0 + i,
                    )
                    session.add(phot)
        
        # Query with aggregation
        with get_session("products", in_memory=True) as session:
            results = session.query(
                Photometry.source_id,
                func.count(Photometry.id).label("count"),
            ).group_by(
                Photometry.source_id
            ).all()
            
            counts = {r.source_id: r.count for r in results}
            assert counts.get("J0000+0000") == 1
            assert counts.get("J0001+0000") == 2
            assert counts.get("J0002+0000") == 3


class TestHDF5IndexRepository:
    """Tests for HDF5IndexRepository."""
    
    def test_create_and_query_group(self, hdf5_db):
        """Test creating and querying HDF5 file groups."""
        with get_session("hdf5", in_memory=True) as session:
            # Create a complete 16-subband group
            for sb in range(16):
                record = HDF5FileIndex(
                    path=f"/data/incoming/2025-10-31T12:00:00_sb{sb:02d}.hdf5",
                    filename=f"2025-10-31T12:00:00_sb{sb:02d}.hdf5",
                    group_id="2025-10-31T12:00:00",
                    subband_code=f"sb{sb:02d}",
                    subband_num=sb,
                    timestamp_iso="2025-10-31T12:00:00",
                    timestamp_mjd=60617.5,
                    stored=1,
                )
                session.add(record)
        
        # Query group
        with get_session("hdf5", in_memory=True) as session:
            files = session.query(HDF5FileIndex).filter(
                HDF5FileIndex.group_id == "2025-10-31T12:00:00"
            ).order_by(HDF5FileIndex.subband_num).all()
            
            assert len(files) == 16
            assert files[0].subband_num == 0
            assert files[-1].subband_num == 15
    
    def test_find_complete_groups(self, hdf5_db):
        """Test finding complete subband groups."""
        from sqlalchemy import func
        
        with get_session("hdf5", in_memory=True) as session:
            # Create a complete group
            for sb in range(16):
                record = HDF5FileIndex(
                    path=f"/data/complete_sb{sb:02d}.hdf5",
                    filename=f"complete_sb{sb:02d}.hdf5",
                    group_id="complete_group",
                    subband_code=f"sb{sb:02d}",
                    subband_num=sb,
                    timestamp_iso="2025-10-31T12:00:00",
                    timestamp_mjd=60617.5,
                    stored=1,
                )
                session.add(record)
            
            # Create an incomplete group (only 8 subbands)
            for sb in range(8):
                record = HDF5FileIndex(
                    path=f"/data/incomplete_sb{sb:02d}.hdf5",
                    filename=f"incomplete_sb{sb:02d}.hdf5",
                    group_id="incomplete_group",
                    subband_code=f"sb{sb:02d}",
                    subband_num=sb,
                    timestamp_iso="2025-10-31T13:00:00",
                    timestamp_mjd=60617.55,
                    stored=1,
                )
                session.add(record)
        
        # Find complete groups
        with get_session("hdf5", in_memory=True) as session:
            complete = session.query(
                HDF5FileIndex.group_id,
                func.count(HDF5FileIndex.path).label("count"),
            ).filter(
                HDF5FileIndex.stored == 1,
            ).group_by(
                HDF5FileIndex.group_id
            ).having(
                func.count(HDF5FileIndex.path) >= 16
            ).all()
            
            group_ids = [r.group_id for r in complete]
            assert "complete_group" in group_ids
            assert "incomplete_group" not in group_ids


class TestDataRegistryRepository:
    """Tests for DataRegistryRepository."""
    
    def test_create_and_query(self, data_registry_db):
        """Test creating and querying data registry entries."""
        with get_session("data_registry", in_memory=True) as session:
            entry = DataRegistry(
                data_type="ms",
                data_id="2025-10-31T12:00:00.ms",
                base_path="/stage/dsa110-contimg/ms",
                status="staging",
                stage_path="/stage/dsa110-contimg/ms/2025-10-31T12:00:00.ms",
                created_at=time.time(),
                staged_at=time.time(),
            )
            session.add(entry)
        
        # Query back
        with get_session("data_registry", in_memory=True) as session:
            result = session.query(DataRegistry).filter(
                DataRegistry.data_id == "2025-10-31T12:00:00.ms"
            ).first()
            
            assert result is not None
            assert result.status == "staging"
    
    def test_update_status_to_published(self, data_registry_db):
        """Test updating data registry status."""
        with get_session("data_registry", in_memory=True) as session:
            entry = DataRegistry(
                data_type="image",
                data_id="test_image.fits",
                base_path="/stage/images",
                status="staging",
                stage_path="/stage/images/test_image.fits",
                created_at=time.time(),
                staged_at=time.time(),
            )
            session.add(entry)
        
        # Update status
        with get_session("data_registry", in_memory=True) as session:
            entry = session.query(DataRegistry).filter(
                DataRegistry.data_id == "test_image.fits"
            ).first()
            
            entry.status = "published"
            entry.published_path = "/products/images/test_image.fits"
            entry.published_at = time.time()
        
        # Verify update
        with get_session("data_registry", in_memory=True) as session:
            result = session.query(DataRegistry).filter(
                DataRegistry.data_id == "test_image.fits"
            ).first()
            
            assert result.status == "published"
            assert result.published_path == "/products/images/test_image.fits"
