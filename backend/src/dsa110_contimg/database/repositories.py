"""
SQLAlchemy-based repository classes for DSA-110 Continuum Imaging Pipeline.

This module provides repository classes that use SQLAlchemy ORM for database
operations, replacing the raw SQL implementation in api/repositories.py.

Usage:
    from dsa110_contimg.database.repositories import (
        ImageRepository, MSRepository, CaltableRepository
    )
    
    # Query images
    repo = ImageRepository()
    images = repo.list_all(limit=100)
    image = repo.get_by_id(123)
    
    # Query with session context
    with repo.session_context() as session:
        images = repo.list_by_type(session, "dirty")

Note:
    These repositories are designed to be drop-in replacements for the
    existing api/repositories.py classes, maintaining API compatibility
    while switching to ORM-based queries.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Generator, Dict, Any

from sqlalchemy.orm import Session, joinedload

from .session import get_session, get_readonly_session, get_scoped_session
from .models import (
    MSIndex, Image, Photometry, Caltable, HDF5FileIndex,
    DataRegistry, CalibratorTransit, TransientCandidate,
    BatchJob, BatchJobItem, MonitoringSource,
)


class BaseRepository:
    """
    Base class for all repositories.
    
    Provides common session management and utility methods.
    """
    
    # Override in subclasses to specify the database
    database_name: str = "products"
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the repository.
        
        Args:
            db_path: Optional custom database path (for testing).
                     If None, uses the default path from environment/config.
        """
        self._custom_db_path = db_path
    
    @contextmanager
    def session_context(self) -> Generator[Session, None, None]:
        """
        Get a session context manager for this repository's database.
        
        Yields:
            SQLAlchemy Session instance
        """
        with get_session(self.database_name) as session:
            yield session
    
    @contextmanager
    def readonly_session_context(self) -> Generator[Session, None, None]:
        """
        Get a read-only session context manager.
        
        Yields:
            SQLAlchemy Session instance
        """
        with get_readonly_session(self.database_name) as session:
            yield session


class ImageRepository(BaseRepository):
    """
    Repository for querying image data using SQLAlchemy ORM.
    """
    
    database_name = "products"
    
    def get_by_id(self, image_id: int | str) -> Optional[Image]:
        """
        Get image by ID or path.
        
        Args:
            image_id: Integer ID or string path
            
        Returns:
            Image model instance or None
        """
        with self.readonly_session_context() as session:
            # Try as integer ID first
            try:
                id_int = int(image_id)
                image = session.query(Image).filter(
                    Image.id == id_int
                ).first()
            except (ValueError, TypeError):
                # Try as path
                image = session.query(Image).filter(
                    Image.path == str(image_id)
                ).first()
            
            if image:
                # Detach from session for return
                session.expunge(image)
            
            return image
    
    def get_by_path(self, path: str) -> Optional[Image]:
        """
        Get image by file path.
        
        Args:
            path: Full path to image file
            
        Returns:
            Image model instance or None
        """
        with self.readonly_session_context() as session:
            image = session.query(Image).filter(
                Image.path == path
            ).first()
            
            if image:
                session.expunge(image)
            
            return image
    
    def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by_created: bool = True,
    ) -> List[Image]:
        """
        Get all images with pagination.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            order_by_created: If True, order by created_at descending
            
        Returns:
            List of Image model instances
        """
        with self.readonly_session_context() as session:
            query = session.query(Image)
            
            if order_by_created:
                query = query.order_by(Image.created_at.desc())
            
            query = query.limit(limit).offset(offset)
            
            images = query.all()
            
            # Detach all from session
            for img in images:
                session.expunge(img)
            
            return images
    
    def list_by_type(
        self,
        image_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Image]:
        """
        Get images by type (dirty, clean, residual, etc.).
        
        Args:
            image_type: Image type to filter by
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of Image model instances
        """
        with self.readonly_session_context() as session:
            images = session.query(Image).filter(
                Image.type == image_type
            ).order_by(
                Image.created_at.desc()
            ).limit(limit).offset(offset).all()
            
            for img in images:
                session.expunge(img)
            
            return images
    
    def list_by_ms_path(self, ms_path: str) -> List[Image]:
        """
        Get all images for a measurement set.
        
        Args:
            ms_path: Path to the measurement set
            
        Returns:
            List of Image model instances
        """
        with self.readonly_session_context() as session:
            images = session.query(Image).filter(
                Image.ms_path == ms_path
            ).order_by(
                Image.created_at.desc()
            ).all()
            
            for img in images:
                session.expunge(img)
            
            return images
    
    def add(self, image: Image) -> Image:
        """
        Add a new image record.
        
        Args:
            image: Image model instance to add
            
        Returns:
            The added Image instance with ID populated
        """
        with self.session_context() as session:
            session.add(image)
            session.flush()  # Get the ID
            session.expunge(image)
            return image
    
    def count(self, image_type: Optional[str] = None) -> int:
        """
        Count images, optionally filtered by type.
        
        Args:
            image_type: Optional type filter
            
        Returns:
            Count of matching images
        """
        with self.readonly_session_context() as session:
            query = session.query(Image)
            if image_type:
                query = query.filter(Image.type == image_type)
            return query.count()


class MSRepository(BaseRepository):
    """
    Repository for querying Measurement Set data.
    """
    
    database_name = "products"
    
    def get_by_path(self, ms_path: str) -> Optional[MSIndex]:
        """
        Get MS metadata by path.
        
        Args:
            ms_path: Full path to the MS
            
        Returns:
            MSIndex model instance or None
        """
        with self.readonly_session_context() as session:
            ms = session.query(MSIndex).filter(
                MSIndex.path == ms_path
            ).first()
            
            if ms:
                session.expunge(ms)
            
            return ms
    
    def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
        stage: Optional[str] = None,
    ) -> List[MSIndex]:
        """
        Get all MS records with optional filtering.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            status: Optional status filter
            stage: Optional stage filter
            
        Returns:
            List of MSIndex model instances
        """
        with self.readonly_session_context() as session:
            query = session.query(MSIndex)
            
            if status:
                query = query.filter(MSIndex.status == status)
            if stage:
                query = query.filter(MSIndex.stage == stage)
            
            query = query.order_by(
                MSIndex.processed_at.desc()
            ).limit(limit).offset(offset)
            
            records = query.all()
            
            for rec in records:
                session.expunge(rec)
            
            return records
    
    def list_by_stage(self, stage: str) -> List[MSIndex]:
        """
        Get all MS records at a specific stage.
        
        Args:
            stage: Pipeline stage (e.g., 'converted', 'calibrated')
            
        Returns:
            List of MSIndex model instances
        """
        return self.list_all(stage=stage, limit=10000)
    
    def list_pending(self) -> List[MSIndex]:
        """
        Get all pending MS records.
        
        Returns:
            List of MSIndex model instances with status='pending'
        """
        return self.list_all(status="pending", limit=10000)
    
    def update_stage(
        self,
        ms_path: str,
        stage: str,
        status: Optional[str] = None,
    ) -> bool:
        """
        Update the stage (and optionally status) of an MS record.
        
        Args:
            ms_path: Path to the MS
            stage: New pipeline stage
            status: Optional new status
            
        Returns:
            True if updated, False if MS not found
        """
        import time
        
        with self.session_context() as session:
            ms = session.query(MSIndex).filter(
                MSIndex.path == ms_path
            ).first()
            
            if not ms:
                return False
            
            ms.stage = stage
            ms.stage_updated_at = time.time()
            
            if status:
                ms.status = status
            
            return True
    
    def add(self, ms: MSIndex) -> MSIndex:
        """
        Add a new MS record.
        
        Args:
            ms: MSIndex model instance to add
            
        Returns:
            The added MSIndex instance
        """
        with self.session_context() as session:
            session.add(ms)
            session.flush()
            session.expunge(ms)
            return ms


class CaltableRepository(BaseRepository):
    """
    Repository for querying calibration table data.
    """
    
    database_name = "cal_registry"
    
    def get_by_id(self, cal_id: int) -> Optional[Caltable]:
        """
        Get calibration table by ID.
        
        Args:
            cal_id: Calibration table ID
            
        Returns:
            Caltable model instance or None
        """
        with self.readonly_session_context() as session:
            cal = session.query(Caltable).filter(
                Caltable.id == cal_id
            ).first()
            
            if cal:
                session.expunge(cal)
            
            return cal
    
    def get_by_path(self, path: str) -> Optional[Caltable]:
        """
        Get calibration table by path.
        
        Args:
            path: Full path to calibration table
            
        Returns:
            Caltable model instance or None
        """
        with self.readonly_session_context() as session:
            cal = session.query(Caltable).filter(
                Caltable.path == path
            ).first()
            
            if cal:
                session.expunge(cal)
            
            return cal
    
    def list_for_ms(self, ms_path: str) -> List[Caltable]:
        """
        Get all calibration tables for a measurement set.
        
        Args:
            ms_path: Path to the measurement set
            
        Returns:
            List of Caltable model instances ordered by order_index
        """
        with self.readonly_session_context() as session:
            cals = session.query(Caltable).filter(
                Caltable.source_ms_path == ms_path
            ).order_by(
                Caltable.order_index
            ).all()
            
            for cal in cals:
                session.expunge(cal)
            
            return cals
    
    def list_by_set(self, set_name: str) -> List[Caltable]:
        """
        Get all calibration tables in a set.
        
        Args:
            set_name: Calibration set name
            
        Returns:
            List of Caltable model instances ordered by order_index
        """
        with self.readonly_session_context() as session:
            cals = session.query(Caltable).filter(
                Caltable.set_name == set_name
            ).order_by(
                Caltable.order_index
            ).all()
            
            for cal in cals:
                session.expunge(cal)
            
            return cals
    
    def find_valid_for_mjd(
        self,
        mjd: float,
        table_type: Optional[str] = None,
    ) -> List[Caltable]:
        """
        Find calibration tables valid at a given MJD.
        
        Args:
            mjd: Modified Julian Date
            table_type: Optional filter by table type
            
        Returns:
            List of valid Caltable model instances
        """
        with self.readonly_session_context() as session:
            query = session.query(Caltable).filter(
                Caltable.status == "active"
            )
            
            if table_type:
                query = query.filter(Caltable.table_type == table_type)
            
            # Filter by validity window
            query = query.filter(
                (Caltable.valid_start_mjd == None) | (Caltable.valid_start_mjd <= mjd),
                (Caltable.valid_end_mjd == None) | (Caltable.valid_end_mjd >= mjd),
            )
            
            cals = query.order_by(Caltable.created_at.desc()).all()
            
            for cal in cals:
                session.expunge(cal)
            
            return cals
    
    def add(self, caltable: Caltable) -> Caltable:
        """
        Add a new calibration table record.
        
        Args:
            caltable: Caltable model instance to add
            
        Returns:
            The added Caltable instance with ID populated
        """
        with self.session_context() as session:
            session.add(caltable)
            session.flush()
            session.expunge(caltable)
            return caltable


class PhotometryRepository(BaseRepository):
    """
    Repository for querying photometry data.
    """
    
    database_name = "products"
    
    def get_by_source_id(self, source_id: str) -> List[Photometry]:
        """
        Get all photometry records for a source.
        
        Args:
            source_id: Unique source identifier
            
        Returns:
            List of Photometry model instances ordered by MJD
        """
        with self.readonly_session_context() as session:
            records = session.query(Photometry).filter(
                Photometry.source_id == source_id
            ).order_by(
                Photometry.mjd
            ).all()
            
            for rec in records:
                session.expunge(rec)
            
            return records
    
    def get_lightcurve(
        self,
        source_id: str,
        start_mjd: Optional[float] = None,
        end_mjd: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get lightcurve data points for a source.
        
        Args:
            source_id: Unique source identifier
            start_mjd: Optional start MJD filter
            end_mjd: Optional end MJD filter
            
        Returns:
            List of dictionaries with lightcurve data
        """
        with self.readonly_session_context() as session:
            query = session.query(Photometry).filter(
                Photometry.source_id == source_id
            )
            
            if start_mjd is not None:
                query = query.filter(Photometry.mjd >= start_mjd)
            if end_mjd is not None:
                query = query.filter(Photometry.mjd <= end_mjd)
            
            query = query.order_by(Photometry.mjd)
            
            data_points = []
            for row in query.all():
                data_points.append({
                    "mjd": row.mjd,
                    "flux_jy": row.flux_jy or row.peak_jyb,
                    "flux_err_jy": row.flux_err_jy or row.peak_err_jyb,
                    "snr": row.snr,
                    "image_path": row.image_path,
                })
            
            return data_points
    
    def list_sources(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List unique sources with aggregated info.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of dictionaries with source info
        """
        from sqlalchemy import func
        
        with self.readonly_session_context() as session:
            query = session.query(
                Photometry.source_id,
                Photometry.ra_deg,
                Photometry.dec_deg,
                func.count(Photometry.id).label("num_images"),
            ).group_by(
                Photometry.source_id
            ).order_by(
                Photometry.source_id
            ).limit(limit).offset(offset)
            
            sources = []
            for row in query.all():
                sources.append({
                    "id": row.source_id,
                    "name": row.source_id,
                    "ra_deg": row.ra_deg,
                    "dec_deg": row.dec_deg,
                    "num_images": row.num_images,
                })
            
            return sources
    
    def add(self, photometry: Photometry) -> Photometry:
        """
        Add a new photometry record.
        
        Args:
            photometry: Photometry model instance to add
            
        Returns:
            The added Photometry instance with ID populated
        """
        with self.session_context() as session:
            session.add(photometry)
            session.flush()
            session.expunge(photometry)
            return photometry


class HDF5IndexRepository(BaseRepository):
    """
    Repository for querying HDF5 file index.
    """
    
    database_name = "hdf5"
    
    def get_by_path(self, path: str) -> Optional[HDF5FileIndex]:
        """
        Get HDF5 file record by path.
        
        Args:
            path: Full path to HDF5 file
            
        Returns:
            HDF5FileIndex model instance or None
        """
        with self.readonly_session_context() as session:
            record = session.query(HDF5FileIndex).filter(
                HDF5FileIndex.path == path
            ).first()
            
            if record:
                session.expunge(record)
            
            return record
    
    def list_by_group(self, group_id: str) -> List[HDF5FileIndex]:
        """
        Get all HDF5 files in a group (observation).
        
        Args:
            group_id: Observation group identifier
            
        Returns:
            List of HDF5FileIndex model instances ordered by subband number
        """
        with self.readonly_session_context() as session:
            records = session.query(HDF5FileIndex).filter(
                HDF5FileIndex.group_id == group_id
            ).order_by(
                HDF5FileIndex.subband_num
            ).all()
            
            for rec in records:
                session.expunge(rec)
            
            return records
    
    def list_by_time_range(
        self,
        start_mjd: float,
        end_mjd: float,
        stored_only: bool = True,
    ) -> List[HDF5FileIndex]:
        """
        Get HDF5 files within a time range.
        
        Args:
            start_mjd: Start MJD
            end_mjd: End MJD
            stored_only: If True, only return files still on disk
            
        Returns:
            List of HDF5FileIndex model instances
        """
        with self.readonly_session_context() as session:
            query = session.query(HDF5FileIndex).filter(
                HDF5FileIndex.timestamp_mjd >= start_mjd,
                HDF5FileIndex.timestamp_mjd <= end_mjd,
            )
            
            if stored_only:
                query = query.filter(HDF5FileIndex.stored == 1)
            
            query = query.order_by(
                HDF5FileIndex.timestamp_mjd,
                HDF5FileIndex.subband_num,
            )
            
            records = query.all()
            
            for rec in records:
                session.expunge(rec)
            
            return records
    
    def find_complete_groups(
        self,
        start_mjd: float,
        end_mjd: float,
        required_subbands: int = 16,
    ) -> List[str]:
        """
        Find observation groups with all subbands present.
        
        Args:
            start_mjd: Start MJD
            end_mjd: End MJD
            required_subbands: Number of subbands required (default 16)
            
        Returns:
            List of complete group IDs
        """
        from sqlalchemy import func
        
        with self.readonly_session_context() as session:
            query = session.query(
                HDF5FileIndex.group_id,
                func.count(HDF5FileIndex.path).label("count"),
            ).filter(
                HDF5FileIndex.timestamp_mjd >= start_mjd,
                HDF5FileIndex.timestamp_mjd <= end_mjd,
                HDF5FileIndex.stored == 1,
            ).group_by(
                HDF5FileIndex.group_id
            ).having(
                func.count(HDF5FileIndex.path) >= required_subbands
            )
            
            return [row.group_id for row in query.all()]
    
    def add(self, record: HDF5FileIndex) -> HDF5FileIndex:
        """
        Add a new HDF5 file record.
        
        Args:
            record: HDF5FileIndex model instance to add
            
        Returns:
            The added HDF5FileIndex instance
        """
        with self.session_context() as session:
            session.add(record)
            session.flush()
            session.expunge(record)
            return record


class DataRegistryRepository(BaseRepository):
    """
    Repository for querying data registry.
    """
    
    database_name = "data_registry"
    
    def get_by_data_id(self, data_id: str) -> Optional[DataRegistry]:
        """
        Get data registry entry by data ID.
        
        Args:
            data_id: Unique data identifier
            
        Returns:
            DataRegistry model instance or None
        """
        with self.readonly_session_context() as session:
            record = session.query(DataRegistry).filter(
                DataRegistry.data_id == data_id
            ).first()
            
            if record:
                session.expunge(record)
            
            return record
    
    def list_by_status(
        self,
        status: str,
        data_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[DataRegistry]:
        """
        List data entries by status.
        
        Args:
            status: Status filter (e.g., 'staging', 'published')
            data_type: Optional type filter
            limit: Maximum number of results
            
        Returns:
            List of DataRegistry model instances
        """
        with self.readonly_session_context() as session:
            query = session.query(DataRegistry).filter(
                DataRegistry.status == status
            )
            
            if data_type:
                query = query.filter(DataRegistry.data_type == data_type)
            
            query = query.order_by(
                DataRegistry.created_at.desc()
            ).limit(limit)
            
            records = query.all()
            
            for rec in records:
                session.expunge(rec)
            
            return records
    
    def list_pending_publish(self) -> List[DataRegistry]:
        """
        Get data entries pending publication.
        
        Returns:
            List of DataRegistry model instances ready for publishing
        """
        with self.readonly_session_context() as session:
            records = session.query(DataRegistry).filter(
                DataRegistry.status == "staging",
                DataRegistry.auto_publish_enabled == 1,
                DataRegistry.finalization_status == "pending",
            ).order_by(
                DataRegistry.created_at
            ).all()
            
            for rec in records:
                session.expunge(rec)
            
            return records
    
    def update_status(
        self,
        data_id: str,
        status: str,
        published_path: Optional[str] = None,
    ) -> bool:
        """
        Update the status of a data entry.
        
        Args:
            data_id: Data identifier
            status: New status
            published_path: Optional published path (for 'published' status)
            
        Returns:
            True if updated, False if not found
        """
        import time
        
        with self.session_context() as session:
            record = session.query(DataRegistry).filter(
                DataRegistry.data_id == data_id
            ).first()
            
            if not record:
                return False
            
            record.status = status
            
            if status == "published" and published_path:
                record.published_path = published_path
                record.published_at = time.time()
            
            return True
    
    def add(self, record: DataRegistry) -> DataRegistry:
        """
        Add a new data registry entry.
        
        Args:
            record: DataRegistry model instance to add
            
        Returns:
            The added DataRegistry instance with ID populated
        """
        with self.session_context() as session:
            session.add(record)
            session.flush()
            session.expunge(record)
            return record
