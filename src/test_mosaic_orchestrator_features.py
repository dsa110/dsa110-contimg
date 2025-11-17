#!/opt/miniforge/envs/casa6/bin/python
"""Tests for new MosaicOrchestrator features.

Tests the following new features:
1. Interactive transit selection with quality metrics
2. Enhanced preview mode
3. Time range override
4. Quality-based transit filtering
5. Batch processing
6. Check for existing mosaics with --overwrite flag
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from astropy.time import Time, TimeDelta

from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator


class TestCheckExistingMosaic:
    """Tests for check_existing_mosaic method."""

    def test_check_existing_mosaic_not_found(self, tmp_path):
        """Test that check_existing_mosaic returns None when no mosaic exists."""
        products_db = tmp_path / "products.sqlite3"
        orchestrator = MosaicOrchestrator(products_db_path=products_db)
        
        start_time = Time("2025-01-01T00:00:00", format="isot", scale="utc")
        end_time = Time("2025-01-01T00:12:00", format="isot", scale="utc")
        
        result = orchestrator.check_existing_mosaic(
            calibrator_name="0834+555",
            start_time=start_time,
            end_time=end_time,
            timespan_minutes=12,
        )
        
        assert result is None

    def test_check_existing_mosaic_found(self, tmp_path):
        """Test that check_existing_mosaic returns mosaic info when found."""
        products_db = tmp_path / "products.sqlite3"
        orchestrator = MosaicOrchestrator(products_db_path=products_db)
        
        # Create database and insert test mosaic
        conn = orchestrator.products_db
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mosaics (
                id INTEGER PRIMARY KEY,
                name TEXT,
                path TEXT,
                created_at REAL,
                start_mjd REAL,
                end_mjd REAL,
                center_ra_deg REAL,
                center_dec_deg REAL,
                n_images INTEGER
            )
        """)
        
        start_time = Time("2025-01-01T00:00:00", format="isot", scale="utc")
        end_time = Time("2025-01-01T00:12:00", format="isot", scale="utc")
        
        cursor.execute("""
            INSERT INTO mosaics (name, path, created_at, start_mjd, end_mjd, 
                               center_ra_deg, center_dec_deg, n_images)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "test_mosaic",
            "/stage/test/mosaic.fits",
            start_time.unix,
            start_time.mjd,
            end_time.mjd,
            120.0,
            55.0,
            3
        ))
        conn.commit()
        
        result = orchestrator.check_existing_mosaic(
            calibrator_name="0834+555",
            start_time=start_time,
            end_time=end_time,
            timespan_minutes=12,
        )
        
        assert result is not None
        assert result["name"] == "test_mosaic"
        assert result["path"] == "/stage/test/mosaic.fits"
        assert result["n_images"] == 3


class TestListAvailableTransitsWithQuality:
    """Tests for list_available_transits_with_quality method."""

    @patch('dsa110_contimg.mosaic.orchestrator.CalibratorService')
    def test_list_available_transits_with_quality(self, mock_cal_service, tmp_path):
        """Test listing transits with quality metrics."""
        products_db = tmp_path / "products.sqlite3"
        orchestrator = MosaicOrchestrator(products_db_path=products_db)
        
        # Mock calibrator service
        mock_transits = [
            {
                "transit_iso": "2025-01-01T00:00:00",
                "pb_response": 0.9,
                "group_id": "group1",
                "files": 5,
            }
        ]
        orchestrator.calibrator_service = Mock()
        orchestrator.calibrator_service.list_available_transits = Mock(
            return_value=mock_transits
        )
        
        # Create ms_index table
        conn = orchestrator.products_db
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ms_index (
                id INTEGER PRIMARY KEY,
                mid_mjd REAL,
                status TEXT
            )
        """)
        conn.commit()
        
        result = orchestrator.list_available_transits_with_quality(
            calibrator_name="0834+555",
            max_days_back=60,
        )
        
        assert len(result) > 0
        assert "ms_count" in result[0]
        assert "transit_time" in result[0]

    def test_list_available_transits_with_quality_filtering(self, tmp_path):
        """Test quality filtering in list_available_transits_with_quality."""
        products_db = tmp_path / "products.sqlite3"
        orchestrator = MosaicOrchestrator(products_db_path=products_db)
        
        # Mock calibrator service with multiple transits
        mock_transits = [
            {
                "transit_iso": "2025-01-01T00:00:00",
                "pb_response": 0.9,
                "group_id": "group1",
                "files": 5,
            },
            {
                "transit_iso": "2025-01-02T00:00:00",
                "pb_response": 0.5,  # Below threshold
                "group_id": "group2",
                "files": 2,
            }
        ]
        orchestrator.calibrator_service = Mock()
        orchestrator.calibrator_service.list_available_transits = Mock(
            return_value=mock_transits
        )
        
        # Create ms_index table
        conn = orchestrator.products_db
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ms_index (
                id INTEGER PRIMARY KEY,
                mid_mjd REAL,
                status TEXT
            )
        """)
        conn.commit()
        
        # Filter by PB response
        result = orchestrator.list_available_transits_with_quality(
            calibrator_name="0834+555",
            max_days_back=60,
            min_pb_response=0.8,
        )
        
        # Should only return transit with PB response >= 0.8
        assert len(result) == 1
        assert result[0]["pb_response"] >= 0.8


class TestTimeRangeOverride:
    """Tests for time range override functionality."""

    def test_find_transit_centered_window_with_time_override(self, tmp_path):
        """Test that time range override works in find_transit_centered_window."""
        products_db = tmp_path / "products.sqlite3"
        orchestrator = MosaicOrchestrator(products_db_path=products_db)
        
        start_time = Time("2025-01-01T10:00:00", format="isot", scale="utc")
        end_time = Time("2025-01-01T10:12:00", format="isot", scale="utc")
        
        result = orchestrator.find_transit_centered_window(
            calibrator_name="0834+555",
            timespan_minutes=12,
            start_time=start_time,
            end_time=end_time,
        )
        
        assert result is not None
        assert abs((result["start_time"] - start_time).to("sec").value) < 1.0
        assert abs((result["end_time"] - end_time).to("sec").value) < 1.0


class TestBatchProcessing:
    """Tests for batch processing functionality."""

    @patch('dsa110_contimg.mosaic.orchestrator.CalibratorService')
    def test_create_mosaics_batch_all_transits(self, mock_cal_service, tmp_path):
        """Test batch processing with all transits."""
        products_db = tmp_path / "products.sqlite3"
        orchestrator = MosaicOrchestrator(products_db_path=products_db)
        
        # Mock calibrator service
        mock_transits = [
            {
                "transit_iso": "2025-01-01T00:00:00",
                "pb_response": 0.9,
                "group_id": "group1",
                "files": 5,
            },
            {
                "transit_iso": "2025-01-02T00:00:00",
                "pb_response": 0.8,
                "group_id": "group2",
                "files": 4,
            }
        ]
        orchestrator.calibrator_service = Mock()
        orchestrator.calibrator_service.list_available_transits = Mock(
            return_value=mock_transits
        )
        
        # Mock create_mosaic_centered_on_calibrator to avoid actual execution
        with patch.object(orchestrator, 'create_mosaic_centered_on_calibrator') as mock_create:
            mock_create.return_value = "/stage/test/mosaic.fits"
            
            result = orchestrator.create_mosaics_batch(
                calibrator_name="0834+555",
                all_transits=True,
                timespan_minutes=12,
                wait_for_published=False,
            )
            
            # Should process all transits
            assert len(result) == 2
            assert all(r["status"] == "success" for r in result)

    def test_create_mosaics_batch_transit_indices(self, tmp_path):
        """Test batch processing with specific transit indices."""
        products_db = tmp_path / "products.sqlite3"
        orchestrator = MosaicOrchestrator(products_db_path=products_db)
        
        # Mock calibrator service
        mock_transits = [
            {
                "transit_iso": "2025-01-01T00:00:00",
                "pb_response": 0.9,
                "group_id": "group1",
                "files": 5,
            },
            {
                "transit_iso": "2025-01-02T00:00:00",
                "pb_response": 0.8,
                "group_id": "group2",
                "files": 4,
            },
            {
                "transit_iso": "2025-01-03T00:00:00",
                "pb_response": 0.7,
                "group_id": "group3",
                "files": 3,
            }
        ]
        orchestrator.calibrator_service = Mock()
        orchestrator.calibrator_service.list_available_transits = Mock(
            return_value=mock_transits
        )
        
        # Mock create_mosaic_centered_on_calibrator
        with patch.object(orchestrator, 'create_mosaic_centered_on_calibrator') as mock_create:
            mock_create.return_value = "/stage/test/mosaic.fits"
            
            result = orchestrator.create_mosaics_batch(
                calibrator_name="0834+555",
                transit_indices=[0, 2],  # Process first and third transit
                timespan_minutes=12,
                wait_for_published=False,
            )
            
            # Should process only specified transits
            assert len(result) == 2
            assert result[0]["transit_index"] == 0
            assert result[1]["transit_index"] == 2

    def test_create_mosaics_batch_index_out_of_range(self, tmp_path):
        """Test batch processing handles out-of-range indices gracefully."""
        products_db = tmp_path / "products.sqlite3"
        orchestrator = MosaicOrchestrator(products_db_path=products_db)
        
        # Mock calibrator service with one transit
        mock_transits = [
            {
                "transit_iso": "2025-01-01T00:00:00",
                "pb_response": 0.9,
                "group_id": "group1",
                "files": 5,
            }
        ]
        orchestrator.calibrator_service = Mock()
        orchestrator.calibrator_service.list_available_transits = Mock(
            return_value=mock_transits
        )
        
        result = orchestrator.create_mosaics_batch(
            calibrator_name="0834+555",
            transit_indices=[0, 5],  # Index 5 is out of range
            timespan_minutes=12,
            wait_for_published=False,
        )
        
        # Should handle out-of-range index gracefully
        assert len(result) == 2
        assert result[0]["status"] == "success"
        assert result[1]["status"] == "skipped"
        assert "Index out of range" in result[1]["error"]


class TestOverwriteFlag:
    """Tests for --overwrite flag functionality."""

    def test_existing_mosaic_check_without_overwrite(self, tmp_path):
        """Test that existing mosaic check stops execution without overwrite flag."""
        products_db = tmp_path / "products.sqlite3"
        orchestrator = MosaicOrchestrator(products_db_path=products_db)
        
        # Create database and insert test mosaic
        conn = orchestrator.products_db
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mosaics (
                id INTEGER PRIMARY KEY,
                name TEXT,
                path TEXT,
                created_at REAL,
                start_mjd REAL,
                end_mjd REAL,
                center_ra_deg REAL,
                center_dec_deg REAL,
                n_images INTEGER
            )
        """)
        
        start_time = Time("2025-01-01T00:00:00", format="isot", scale="utc")
        end_time = Time("2025-01-01T00:12:00", format="isot", scale="utc")
        
        cursor.execute("""
            INSERT INTO mosaics (name, path, created_at, start_mjd, end_mjd, 
                               center_ra_deg, center_dec_deg, n_images)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "test_mosaic",
            "/stage/test/mosaic.fits",
            start_time.unix,
            start_time.mjd,
            end_time.mjd,
            120.0,
            55.0,
            3
        ))
        conn.commit()
        
        # Mock other methods to avoid actual execution
        with patch.object(orchestrator, 'find_transit_centered_window') as mock_find:
            mock_find.return_value = {
                "transit_time": start_time,
                "start_time": start_time,
                "end_time": end_time,
            }
            
            with patch.object(orchestrator, 'ensure_ms_files_in_window') as mock_ensure:
                mock_ensure.return_value = []
                
                # Try to create mosaic without overwrite flag
                result = orchestrator.create_mosaic_centered_on_calibrator(
                    calibrator_name="0834+555",
                    timespan_minutes=12,
                    wait_for_published=False,
                    dry_run=False,
                    overwrite=False,
                )
                
                # Should return None due to existing mosaic
                assert result is None

    def test_existing_mosaic_check_with_overwrite(self, tmp_path):
        """Test that existing mosaic check allows execution with overwrite flag."""
        products_db = tmp_path / "products.sqlite3"
        orchestrator = MosaicOrchestrator(products_db_path=products_db)
        
        # Create database and insert test mosaic
        conn = orchestrator.products_db
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mosaics (
                id INTEGER PRIMARY KEY,
                name TEXT,
                path TEXT,
                created_at REAL,
                start_mjd REAL,
                end_mjd REAL,
                center_ra_deg REAL,
                center_dec_deg REAL,
                n_images INTEGER
            )
        """)
        
        start_time = Time("2025-01-01T00:00:00", format="isot", scale="utc")
        end_time = Time("2025-01-01T00:12:00", format="isot", scale="utc")
        
        cursor.execute("""
            INSERT INTO mosaics (name, path, created_at, start_mjd, end_mjd, 
                               center_ra_deg, center_dec_deg, n_images)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "test_mosaic",
            "/stage/test/mosaic.fits",
            start_time.unix,
            start_time.mjd,
            end_time.mjd,
            120.0,
            55.0,
            3
        ))
        conn.commit()
        
        # Mock other methods
        with patch.object(orchestrator, 'find_transit_centered_window') as mock_find:
            mock_find.return_value = {
                "transit_time": start_time,
                "start_time": start_time,
                "end_time": end_time,
            }
            
            with patch.object(orchestrator, 'ensure_ms_files_in_window') as mock_ensure:
                mock_ensure.return_value = []
                
                with patch.object(orchestrator, '_execute_mosaic_creation') as mock_exec:
                    mock_exec.return_value = "/stage/test/new_mosaic.fits"
                    
                    # Try to create mosaic with overwrite flag
                    result = orchestrator.create_mosaic_centered_on_calibrator(
                        calibrator_name="0834+555",
                        timespan_minutes=12,
                        wait_for_published=False,
                        dry_run=False,
                        overwrite=True,
                    )
                    
                    # Should proceed with creation
                    assert result is not None
                    assert mock_exec.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

