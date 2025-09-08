# tests/unit/test_orchestrator.py
"""
Unit tests for the pipeline orchestrator.

This module contains unit tests for the PipelineOrchestrator class
and related functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from astropy.time import Time
from astropy.coordinates import SkyCoord
import astropy.units as u

from core.pipeline import PipelineOrchestrator, ProcessingBlock, ProcessingResult
from core.pipeline.exceptions import PipelineError


class TestProcessingBlock:
    """Test cases for ProcessingBlock class."""
    
    def test_processing_block_creation(self):
        """Test creating a ProcessingBlock."""
        start_time = Time('2023-01-01T00:00:00', format='isot', scale='utc')
        end_time = Time('2023-01-01T01:00:00', format='isot', scale='utc')
        ms_files = ['test1.ms', 'test2.ms']
        block_id = 'test_block'
        
        block = ProcessingBlock(
            start_time=start_time,
            end_time=end_time,
            ms_files=ms_files,
            block_id=block_id
        )
        
        assert block.start_time == start_time
        assert block.end_time == end_time
        assert block.ms_files == ms_files
        assert block.block_id == block_id
    
    def test_processing_block_empty_ms_files(self):
        """Test that ProcessingBlock raises error for empty MS files."""
        start_time = Time('2023-01-01T00:00:00', format='isot', scale='utc')
        end_time = Time('2023-01-01T01:00:00', format='isot', scale='utc')
        
        with pytest.raises(ValueError, match="ProcessingBlock must have at least one MS file"):
            ProcessingBlock(
                start_time=start_time,
                end_time=end_time,
                ms_files=[],
                block_id='test_block'
            )
    
    def test_processing_block_invalid_time_range(self):
        """Test that ProcessingBlock raises error for invalid time range."""
        start_time = Time('2023-01-01T01:00:00', format='isot', scale='utc')
        end_time = Time('2023-01-01T00:00:00', format='isot', scale='utc')
        
        with pytest.raises(ValueError, match="start_time must be before end_time"):
            ProcessingBlock(
                start_time=start_time,
                end_time=end_time,
                ms_files=['test.ms'],
                block_id='test_block'
            )


class TestProcessingResult:
    """Test cases for ProcessingResult class."""
    
    def test_processing_result_creation(self):
        """Test creating a ProcessingResult."""
        result = ProcessingResult(
            block_id='test_block',
            success=True,
            stage_results={'calibration': {'success': True}},
            errors=[],
            processing_time=120.5,
            output_files={'image': 'test.image'}
        )
        
        assert result.block_id == 'test_block'
        assert result.success is True
        assert result.stage_results == {'calibration': {'success': True}}
        assert result.errors == []
        assert result.processing_time == 120.5
        assert result.output_files == {'image': 'test.image'}


class TestPipelineOrchestrator:
    """Test cases for PipelineOrchestrator class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        return {
            'paths': {
                'cal_tables_dir': 'test_cal_tables',
                'skymodels_dir': 'test_skymodels',
                'images_dir': 'test_images',
                'mosaics_dir': 'test_mosaics',
                'photometry_dir': 'test_photometry'
            },
            'services': {
                'mosaic_duration_min': 60,
                'mosaic_overlap_min': 10,
                'ms_chunk_duration_min': 5
            },
            'calibration': {
                'fixed_declination_deg': 37.0,
                'gcal_refant': 'pad001',
                'gcal_mode': 'ap',
                'gcal_solint': '30min',
                'gcal_minsnr': 3.0
            },
            'imaging': {
                'deconvolver': 'hogbom',
                'gridder': 'wproject',
                'niter': 1000,
                'threshold': '1mJy',
                'image_size': [1000, 1000],
                'cell_size': '3arcsec'
            },
            'mosaicking': {
                'mosaic_type': 'optimal',
                'mosaic_nx': 2000,
                'mosaic_ny': 2000,
                'mosaic_cell': '3arcsec'
            },
            'photometry': {
                'detection': {
                    'fwhm_pixels': 3.0,
                    'threshold_sigma': 5.0
                }
            },
            'skymodel': {
                'field': {
                    'radius_deg': 0.5,
                    'n_sources': 50
                }
            }
        }
    
    @pytest.fixture
    def mock_block(self):
        """Create a mock ProcessingBlock for testing."""
        start_time = Time('2023-01-01T00:00:00', format='isot', scale='utc')
        end_time = Time('2023-01-01T01:00:00', format='isot', scale='utc')
        ms_files = ['test1.ms', 'test2.ms']
        block_id = 'test_block'
        
        return ProcessingBlock(
            start_time=start_time,
            end_time=end_time,
            ms_files=ms_files,
            block_id=block_id
        )
    
    @patch('core.pipeline.orchestrator.CalibrationStage')
    @patch('core.pipeline.orchestrator.ImagingStage')
    @patch('core.pipeline.orchestrator.MosaickingStage')
    @patch('core.pipeline.orchestrator.PhotometryStage')
    @patch('core.pipeline.orchestrator.PipelineMetrics')
    def test_orchestrator_initialization(self, mock_metrics, mock_photometry, 
                                       mock_mosaicking, mock_imaging, mock_calibration,
                                       mock_config):
        """Test orchestrator initialization."""
        # Mock the stage initialization
        mock_calibration.return_value = Mock()
        mock_imaging.return_value = Mock()
        mock_mosaicking.return_value = Mock()
        mock_photometry.return_value = Mock()
        mock_metrics.return_value = Mock()
        
        orchestrator = PipelineOrchestrator(mock_config)
        
        assert orchestrator.config == mock_config
        assert orchestrator.metrics is not None
        assert 'calibration' in orchestrator.stages
        assert 'imaging' in orchestrator.stages
        assert 'mosaicking' in orchestrator.stages
        assert 'photometry' in orchestrator.stages
    
    @patch('core.pipeline.orchestrator.CalibrationStage')
    @patch('core.pipeline.orchestrator.ImagingStage')
    @patch('core.pipeline.orchestrator.MosaickingStage')
    @patch('core.pipeline.orchestrator.PhotometryStage')
    @patch('core.pipeline.orchestrator.PipelineMetrics')
    def test_orchestrator_initialization_failure(self, mock_metrics, mock_photometry,
                                               mock_mosaicking, mock_imaging, mock_calibration,
                                               mock_config):
        """Test orchestrator initialization failure."""
        # Mock stage initialization failure
        mock_calibration.side_effect = Exception("Calibration stage failed")
        
        with pytest.raises(PipelineError, match="Stage initialization failed"):
            PipelineOrchestrator(mock_config)
    
    @patch('core.pipeline.orchestrator.CalibrationStage')
    @patch('core.pipeline.orchestrator.ImagingStage')
    @patch('core.pipeline.orchestrator.MosaickingStage')
    @patch('core.pipeline.orchestrator.PhotometryStage')
    @patch('core.pipeline.orchestrator.PipelineMetrics')
    @pytest.mark.asyncio
    async def test_process_block_success(self, mock_metrics, mock_photometry,
                                       mock_mosaicking, mock_imaging, mock_calibration,
                                       mock_config, mock_block):
        """Test successful block processing."""
        # Mock stage initialization
        mock_cal_stage = Mock()
        mock_cal_stage.setup_calibration = AsyncMock(return_value={
            'success': True,
            'bcal_table': 'test.bcal',
            'gcal_table': 'test.gcal',
            'cl_path': 'test.cl',
            'mask_path': None
        })
        
        mock_img_stage = Mock()
        mock_img_stage.process_ms = AsyncMock(return_value={
            'success': True,
            'image_path': 'test.image',
            'pb_path': 'test.pb',
            'fits_path': 'test.fits'
        })
        
        mock_mos_stage = Mock()
        mock_mos_stage.create_mosaic = AsyncMock(return_value={
            'success': True,
            'image_path': 'test_mosaic.image',
            'weight_path': 'test_mosaic.weight',
            'fits_path': 'test_mosaic.fits'
        })
        
        mock_phot_stage = Mock()
        mock_phot_stage.process_mosaic = AsyncMock(return_value={
            'success': True,
            'targets_count': 5,
            'references_count': 10
        })
        
        mock_calibration.return_value = mock_cal_stage
        mock_imaging.return_value = mock_img_stage
        mock_mosaicking.return_value = mock_mos_stage
        mock_photometry.return_value = mock_phot_stage
        mock_metrics.return_value = Mock()
        
        orchestrator = PipelineOrchestrator(mock_config)
        
        # Process the block
        result = await orchestrator.process_block(mock_block)
        
        assert result.success is True
        assert result.block_id == mock_block.block_id
        assert result.processing_time > 0
        assert len(result.errors) == 0
        assert 'mosaic_image' in result.output_files
    
    @patch('core.pipeline.orchestrator.CalibrationStage')
    @patch('core.pipeline.orchestrator.ImagingStage')
    @patch('core.pipeline.orchestrator.MosaickingStage')
    @patch('core.pipeline.orchestrator.PhotometryStage')
    @patch('core.pipeline.orchestrator.PipelineMetrics')
    @pytest.mark.asyncio
    async def test_process_block_calibration_failure(self, mock_metrics, mock_photometry,
                                                   mock_mosaicking, mock_imaging, mock_calibration,
                                                   mock_config, mock_block):
        """Test block processing with calibration failure."""
        # Mock stage initialization
        mock_cal_stage = Mock()
        mock_cal_stage.setup_calibration = AsyncMock(return_value={
            'success': False,
            'error': 'Calibration failed'
        })
        
        mock_calibration.return_value = mock_cal_stage
        mock_imaging.return_value = Mock()
        mock_mosaicking.return_value = Mock()
        mock_photometry.return_value = Mock()
        mock_metrics.return_value = Mock()
        
        orchestrator = PipelineOrchestrator(mock_config)
        
        # Process the block
        result = await orchestrator.process_block(mock_block)
        
        assert result.success is False
        assert result.block_id == mock_block.block_id
        assert len(result.errors) > 0
        assert 'Calibration setup failed' in result.errors[0]
    
    @patch('core.pipeline.orchestrator.CalibrationStage')
    @patch('core.pipeline.orchestrator.ImagingStage')
    @patch('core.pipeline.orchestrator.MosaickingStage')
    @patch('core.pipeline.orchestrator.PhotometryStage')
    @patch('core.pipeline.orchestrator.PipelineMetrics')
    def test_create_processing_block(self, mock_metrics, mock_photometry,
                                   mock_mosaicking, mock_imaging, mock_calibration,
                                   mock_config):
        """Test creating a ProcessingBlock from orchestrator."""
        # Mock stage initialization
        mock_calibration.return_value = Mock()
        mock_imaging.return_value = Mock()
        mock_mosaicking.return_value = Mock()
        mock_photometry.return_value = Mock()
        mock_metrics.return_value = Mock()
        
        orchestrator = PipelineOrchestrator(mock_config)
        
        block_end_time = Time('2023-01-01T01:00:00', format='isot', scale='utc')
        ms_files = ['test1.ms', 'test2.ms']
        
        block = orchestrator.create_processing_block(block_end_time, ms_files)
        
        assert block.end_time == block_end_time
        assert block.ms_files == ms_files
        assert block.block_id is not None
        assert block.start_time < block.end_time
