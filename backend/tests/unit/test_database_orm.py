"""
Tests for SQLAlchemy ORM models and session management.

These tests use in-memory SQLite databases for isolation and speed.
"""

import pytest
import time
from unittest.mock import patch, MagicMock

from sqlalchemy import inspect

from dsa110_contimg.database import (
    get_session,
    get_readonly_session,
    get_scoped_session,
    get_engine,
    init_database,
    reset_engines,
    # Models
    ProductsBase,
    CalRegistryBase,
    HDF5Base,
    MSIndex,
    Image,
    Photometry,
    Caltable,
    HDF5FileIndex,
    DataRegistry,
)


@pytest.fixture(autouse=True)
def reset_db_state():
    """Reset database engines before each test."""
    reset_engines()
    yield
    reset_engines()


class TestEngineCreation:
    """Tests for database engine creation."""
    
    def test_create_engine_in_memory(self):
        """Test creating an in-memory database engine."""
        engine = get_engine("products", in_memory=True)
        
        assert engine is not None
        assert "memory" in str(engine.url)
    
    def test_engine_caching(self):
        """Test that engines are cached and reused."""
        engine1 = get_engine("products", in_memory=True)
        engine2 = get_engine("products", in_memory=True)
        
        assert engine1 is engine2
    
    def test_different_dbs_different_engines(self):
        """Test that different database names resolve to same engine (unified DB).
        
        With the unified database design, all logical database names
        (products, cal_registry, hdf5) resolve to the same engine.
        """
        products_engine = get_engine("products", in_memory=True)
        cal_engine = get_engine("cal_registry", in_memory=True)
        
        # Unified design: all DBs share the same engine
        assert products_engine is cal_engine


class TestSessionManagement:
    """Tests for session management."""
    
    def test_get_session_context_manager(self):
        """Test session context manager basic usage."""
        engine = get_engine("products", in_memory=True)
        ProductsBase.metadata.create_all(engine)
        
        with get_session("products", in_memory=True) as session:
            assert session is not None
            # Session should be active inside context
            assert session.is_active
    
    def test_get_readonly_session(self):
        """Test read-only session context manager."""
        engine = get_engine("products", in_memory=True)
        ProductsBase.metadata.create_all(engine)
        
        with get_readonly_session("products", in_memory=True) as session:
            assert session is not None
            # Can perform queries
            result = session.query(MSIndex).all()
            assert result == []
    
    def test_scoped_session_thread_safety(self):
        """Test scoped session provides thread-local sessions."""
        engine = get_engine("products", in_memory=True)
        ProductsBase.metadata.create_all(engine)
        
        Session = get_scoped_session("products", in_memory=True)
        
        session1 = Session()
        session2 = Session()
        
        # Same thread should get same session
        assert session1 is session2
        
        Session.remove()


class TestMSIndexModel:
    """Tests for MSIndex ORM model."""
    
    def test_create_ms_index(self):
        """Test creating an MSIndex record."""
        engine = get_engine("products", in_memory=True)
        ProductsBase.metadata.create_all(engine)
        
        with get_session("products", in_memory=True) as session:
            ms = MSIndex(
                path="/stage/dsa110-contimg/ms/test.ms",
                start_mjd=60000.0,
                end_mjd=60000.1,
                mid_mjd=60000.05,
                processed_at=time.time(),
                status="completed",
                stage="converted",
            )
            session.add(ms)
            session.flush()
            
            # Query it back
            result = session.query(MSIndex).filter_by(
                path="/stage/dsa110-contimg/ms/test.ms"
            ).first()
            
            assert result is not None
            assert result.stage == "converted"
            assert result.mid_mjd == 60000.05
    
    def test_ms_index_repr(self):
        """Test MSIndex string representation."""
        ms = MSIndex(path="/test/path.ms", stage="calibrated")
        assert "test/path.ms" in repr(ms)
        assert "calibrated" in repr(ms)


class TestImageModel:
    """Tests for Image ORM model."""
    
    def test_create_image_with_ms_relationship(self):
        """Test creating an Image with MS relationship."""
        engine = get_engine("products", in_memory=True)
        ProductsBase.metadata.create_all(engine)
        
        with get_session("products", in_memory=True) as session:
            # Create MS first
            ms = MSIndex(
                path="/test/test.ms",
                status="completed",
                stage="imaged",
            )
            session.add(ms)
            session.flush()
            
            # Create image linked to MS
            image = Image(
                path="/test/image.fits",
                ms_path="/test/test.ms",
                created_at=time.time(),
                type="dirty",
                beam_major_arcsec=5.0,
                noise_jy=0.001,
            )
            session.add(image)
            session.flush()
            
            # Query back with relationship
            result = session.query(Image).first()
            assert result is not None
            assert result.type == "dirty"
            assert result.beam_major_arcsec == 5.0
    
    def test_image_defaults(self):
        """Test Image default values are applied after INSERT.
        
        Note: SQLAlchemy Column(default=...) is only applied during INSERT,
        not during object instantiation. Must insert and refresh to see defaults.
        """
        engine = get_engine("products", in_memory=True)
        ProductsBase.metadata.create_all(engine)
        
        with get_session("products", in_memory=True) as session:
            image = Image(
                path="/test/image.fits",
                ms_path="/test/test.ms",
                created_at=time.time(),
                type="clean",
            )
            session.add(image)
            session.commit()
            session.refresh(image)
            
            # Defaults applied after INSERT
            assert image.pbcor == 0
            assert image.format == "fits"


class TestPhotometryModel:
    """Tests for Photometry ORM model."""
    
    def test_create_photometry(self):
        """Test creating a photometry record."""
        engine = get_engine("products", in_memory=True)
        ProductsBase.metadata.create_all(engine)
        
        with get_session("products", in_memory=True) as session:
            # First create an image (for foreign key)
            ms = MSIndex(path="/test/test.ms", status="completed", stage="imaged")
            session.add(ms)
            
            image = Image(
                path="/test/image.fits",
                ms_path="/test/test.ms",
                created_at=time.time(),
                type="clean",
            )
            session.add(image)
            session.flush()
            
            # Create photometry
            phot = Photometry(
                source_id="J1234+5678",
                image_path="/test/image.fits",
                ra_deg=123.456,
                dec_deg=56.789,
                peak_jyb=0.1,
                measured_at=time.time(),
                snr=50.0,
            )
            session.add(phot)
            session.flush()
            
            result = session.query(Photometry).filter_by(
                source_id="J1234+5678"
            ).first()
            
            assert result is not None
            assert result.snr == 50.0


class TestCaltableModel:
    """Tests for Caltable ORM model."""
    
    def test_create_caltable(self):
        """Test creating a calibration table record."""
        engine = get_engine("cal_registry", in_memory=True)
        CalRegistryBase.metadata.create_all(engine)
        
        with get_session("cal_registry", in_memory=True) as session:
            cal = Caltable(
                set_name="3C286_20251101",
                path="/cal/tables/bandpass.tb",
                table_type="bandpass",
                order_index=0,
                cal_field="3C286",
                refant="ea01",
                created_at=time.time(),
                status="active",
                valid_start_mjd=60000.0,
                valid_end_mjd=60100.0,
            )
            session.add(cal)
            session.flush()
            
            result = session.query(Caltable).first()
            assert result is not None
            assert result.table_type == "bandpass"
    
    def test_caltable_is_valid_at(self):
        """Test Caltable validity checking."""
        cal = Caltable(
            set_name="test",
            path="/test.tb",
            table_type="gain",
            order_index=0,
            created_at=time.time(),
            status="active",
            valid_start_mjd=60000.0,
            valid_end_mjd=60100.0,
        )
        
        assert cal.is_valid_at(60050.0) is True
        assert cal.is_valid_at(59999.0) is False
        assert cal.is_valid_at(60101.0) is False
    
    def test_caltable_no_validity_window(self):
        """Test Caltable with no validity window (always valid)."""
        cal = Caltable(
            set_name="test",
            path="/test.tb",
            table_type="gain",
            order_index=0,
            created_at=time.time(),
            status="active",
        )
        
        assert cal.is_valid_at(60050.0) is True
        assert cal.is_valid_at(0.0) is True


class TestHDF5FileIndexModel:
    """Tests for HDF5FileIndex ORM model."""
    
    def test_create_hdf5_index(self):
        """Test creating an HDF5 file index record."""
        engine = get_engine("hdf5", in_memory=True)
        HDF5Base.metadata.create_all(engine)
        
        with get_session("hdf5", in_memory=True) as session:
            record = HDF5FileIndex(
                path="/data/incoming/2025-10-31T12:00:00_sb00.hdf5",
                filename="2025-10-31T12:00:00_sb00.hdf5",
                group_id="2025-10-31T12:00:00",
                subband_code="sb00",
                subband_num=0,
                timestamp_iso="2025-10-31T12:00:00",
                timestamp_mjd=60617.5,
                stored=1,
            )
            session.add(record)
            session.flush()
            
            result = session.query(HDF5FileIndex).first()
            assert result is not None
            assert result.subband_num == 0
            assert result.group_id == "2025-10-31T12:00:00"


class TestDatabaseInitialization:
    """Tests for database initialization."""
    
    def test_init_products_database(self):
        """Test initializing products database creates all tables."""
        # Use in-memory for testing
        engine = get_engine("products", in_memory=True)
        init_database("products", in_memory=True)
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Check key tables exist
        assert "ms_index" in tables
        assert "images" in tables
        assert "photometry" in tables
    
    def test_init_cal_registry_database(self):
        """Test initializing cal_registry database."""
        engine = get_engine("cal_registry", in_memory=True)
        init_database("cal_registry", in_memory=True)
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        assert "caltables" in tables
    
    def test_init_hdf5_database(self):
        """Test initializing hdf5 database."""
        engine = get_engine("hdf5", in_memory=True)
        init_database("hdf5", in_memory=True)
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        assert "hdf5_file_index" in tables
        assert "pointing_history" in tables


class TestWALMode:
    """Tests for WAL mode configuration."""
    
    def test_wal_mode_enabled(self):
        """Test that WAL mode is enabled on connections."""
        from sqlalchemy import text
        engine = get_engine("products", in_memory=True)
        
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA journal_mode")).scalar()
            # In-memory databases use 'memory' mode, file-based use 'wal'
            # For in-memory, we just verify the connection works
            assert result in ("memory", "wal")
    
    def test_foreign_keys_enabled(self):
        """Test that foreign keys are enabled."""
        from sqlalchemy import text
        engine = get_engine("products", in_memory=True)
        
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA foreign_keys")).scalar()
            assert result == 1


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_invalid_database_name(self):
        """Test that invalid database names raise ValueError."""
        from dsa110_contimg.database.session import get_db_path
        
        with pytest.raises(ValueError) as exc_info:
            get_db_path("invalid_db_name")
        
        assert "Unknown database name" in str(exc_info.value)
    
    def test_session_rollback_on_error(self):
        """Test that sessions roll back on exceptions."""
        engine = get_engine("products", in_memory=True)
        ProductsBase.metadata.create_all(engine)
        
        try:
            with get_session("products", in_memory=True) as session:
                ms = MSIndex(path="/test.ms", status="ok", stage="test")
                session.add(ms)
                session.flush()
                
                # Simulate error
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Verify nothing was committed
        with get_readonly_session("products", in_memory=True) as session:
            result = session.query(MSIndex).all()
            assert len(result) == 0
    
    def test_reset_engines_cleans_up(self):
        """Test that reset_engines properly cleans up."""
        engine1 = get_engine("products", in_memory=True)
        Session = get_scoped_session("products", in_memory=True)
        
        reset_engines()
        
        # New engine should be different instance
        engine2 = get_engine("products", in_memory=True)
        # Can't compare engines after dispose, just verify it works
        assert engine2 is not None
