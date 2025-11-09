#!/usr/bin/env python3
"""
Comprehensive unit tests for imaging functions with mocking.

This test suite demonstrates how to test imaging logic without running
actual CASA/WSClean operations. All external dependencies are mocked.

Run with: pytest tests/unit/test_imaging_mocked.py -v
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock

import numpy as np
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.mark.unit
class TestImageMSLogic:
    """Test image_ms function logic with mocked dependencies."""
    
    def test_quality_tier_development_cell_size(self, mock_table_factory, temp_work_dir):
        """Test that development tier uses 4x coarser cell size."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        
        ms_path = str(temp_work_dir / "test.ms")
        imagename = str(temp_work_dir / "test.img")
        
        # Create a dummy MS directory (validate_ms checks if it exists)
        Path(ms_path).mkdir(parents=True, exist_ok=True)
        
        # Mock MS structure with default cell size calculation
        with patch('casacore.tables.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_imaging.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_imaging.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_utils.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.run_wsclean') as mock_wsclean, \
             patch('dsa110_contimg.imaging.cli_imaging.validate_ms', return_value=None), \
             patch('dsa110_contimg.utils.validation.validate_corrected_data_quality', return_value=[]):
            
            # Call with development tier
            image_ms(
                ms_path,
                imagename=imagename,
                quality_tier="development",
                cell_arcsec=None,  # Use default
            )
            
            # Verify WSClean was called with 4x coarser cell size (2.0 * 4 = 8.0)
            assert mock_wsclean.called
            call_args = mock_wsclean.call_args
            assert call_args[1]['cell_arcsec'] == 8.0  # 4x coarser
    
    def test_quality_tier_development_iterations(self, mock_table_factory, temp_work_dir):
        """Test that development tier limits iterations to 300."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        
        ms_path = str(temp_work_dir / "test.ms")
        imagename = str(temp_work_dir / "test.img")
        
        # Create a dummy MS directory
        Path(ms_path).mkdir(parents=True, exist_ok=True)
        
        with patch('casacore.tables.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_imaging.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_imaging.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_utils.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.run_wsclean') as mock_wsclean, \
             patch('dsa110_contimg.imaging.cli_imaging.validate_ms', return_value=None), \
             patch('dsa110_contimg.utils.validation.validate_corrected_data_quality', return_value=[]):
            
            # Call with development tier and high niter
            image_ms(
                ms_path,
                imagename=imagename,
                quality_tier="development",
                niter=5000,  # High value that should be capped
            )
            
            # Verify iterations were capped at 300
            call_args = mock_wsclean.call_args
            assert call_args[1]['niter'] == 300
    
    def test_quality_tier_standard_no_changes(self, mock_table_factory, temp_work_dir):
        """Test that standard tier doesn't modify parameters."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        
        ms_path = str(temp_work_dir / "test.ms")
        imagename = str(temp_work_dir / "test.img")
        
        # Create a dummy MS directory
        Path(ms_path).mkdir(parents=True, exist_ok=True)
        
        with patch('casacore.tables.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_imaging.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_imaging.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_utils.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.run_wsclean') as mock_wsclean, \
             patch('dsa110_contimg.imaging.cli_imaging.validate_ms', return_value=None), \
             patch('dsa110_contimg.utils.validation.validate_corrected_data_quality', return_value=[]):
            
            # Call with standard tier
            image_ms(
                ms_path,
                imagename=imagename,
                quality_tier="standard",
                cell_arcsec=2.0,
                niter=1000,
            )
            
            # Verify parameters unchanged
            call_args = mock_wsclean.call_args
            assert call_args[1]['cell_arcsec'] == 2.0
            assert call_args[1]['niter'] == 1000
    
    def test_datacolumn_detection_corrected(self, mock_table_factory, temp_work_dir):
        """Test that CORRECTED_DATA is selected when available."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        
        ms_path = str(temp_work_dir / "test.ms")
        imagename = str(temp_work_dir / "test.img")
        
        # Create a dummy MS directory
        Path(ms_path).mkdir(parents=True, exist_ok=True)
        
        with patch('casacore.tables.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_imaging.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_imaging.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_utils.detect_datacolumn', return_value='corrected'), \
             patch('dsa110_contimg.imaging.cli_imaging.detect_datacolumn', return_value='corrected'), \
             patch('dsa110_contimg.imaging.cli_imaging.run_wsclean') as mock_wsclean, \
             patch('dsa110_contimg.imaging.cli_imaging.validate_ms', return_value=None), \
             patch('dsa110_contimg.utils.validation.validate_corrected_data_quality', return_value=[]):
            
            image_ms(ms_path, imagename=imagename)
            
            # Verify WSClean called with corrected datacolumn
            call_args = mock_wsclean.call_args
            assert call_args[1]['datacolumn'] == 'corrected'
    
    def test_datacolumn_detection_data_fallback(self, mock_table_factory, temp_work_dir):
        """Test that DATA is used when CORRECTED_DATA not available."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        
        ms_path = str(temp_work_dir / "test.ms")
        imagename = str(temp_work_dir / "test.img")
        
        # Create a dummy MS directory
        Path(ms_path).mkdir(parents=True, exist_ok=True)
        
        with patch('casacore.tables.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_imaging.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_imaging.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_utils.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.run_wsclean') as mock_wsclean, \
             patch('dsa110_contimg.imaging.cli_imaging.validate_ms', return_value=None), \
             patch('dsa110_contimg.utils.validation.validate_corrected_data_quality', return_value=[]):
            
            image_ms(ms_path, imagename=imagename)
            
            # Verify WSClean called with data datacolumn
            call_args = mock_wsclean.call_args
            assert call_args[1]['datacolumn'] == 'data'


@pytest.mark.unit
class TestRunWSCleanLogic:
    """Test run_wsclean function logic with mocked subprocess."""
    
    def test_wsclean_always_reorders(self, mock_wsclean_subprocess, temp_work_dir):
        """Test that WSClean always includes -reorder flag."""
        from dsa110_contimg.imaging.cli_imaging import run_wsclean
        
        ms_path = "/fake/test.ms"
        imagename = str(temp_work_dir / "test.img")
        
        with patch('subprocess.run', side_effect=mock_wsclean_subprocess) as mock_subprocess, \
             patch('shutil.which', return_value='/usr/bin/wsclean'):
            
            run_wsclean(
                ms_path=ms_path,
                imagename=imagename,
                datacolumn="data",
                field="",
                imsize=1024,
                cell_arcsec=2.0,
                weighting="briggs",
                robust=0.0,
                specmode="mfs",
                deconvolver="hogbom",
                nterms=1,
                niter=1000,
                threshold="0.0Jy",
                pbcor=True,
                uvrange="",
                pblimit=0.2,
                quality_tier="development",
            )
            
            # Verify subprocess was called
            assert mock_subprocess.called
            
            # Get the command that was executed
            call_args = mock_subprocess.call_args
            cmd = call_args[0][0]
            
            # Verify -reorder is in the command (regardless of quality tier)
            assert '-reorder' in cmd
    
    def test_wsclean_development_tier_memory(self, mock_wsclean_subprocess, temp_work_dir):
        """Test that development tier uses appropriate memory settings."""
        from dsa110_contimg.imaging.cli_imaging import run_wsclean
        
        ms_path = "/fake/test.ms"
        imagename = str(temp_work_dir / "test.img")
        
        with patch('subprocess.run', side_effect=mock_wsclean_subprocess) as mock_subprocess, \
             patch('shutil.which', return_value='/usr/bin/wsclean'), \
             patch.dict(os.environ, {}, clear=True):  # Clear WSCLEAN_ABS_MEM
            
            run_wsclean(
                ms_path=ms_path,
                imagename=imagename,
                datacolumn="data",
                field="",
                imsize=1024,
                cell_arcsec=2.0,
                weighting="briggs",
                robust=0.0,
                specmode="mfs",
                deconvolver="hogbom",
                nterms=1,
                niter=1000,
                threshold="0.0Jy",
                pbcor=True,
                uvrange="",
                pblimit=0.2,
                quality_tier="development",
            )
            
            # Get the command
            call_args = mock_subprocess.call_args
            cmd = call_args[0][0]
            
            # Verify memory setting for development tier (default 16GB)
            abs_mem_idx = cmd.index('-abs-mem')
            assert abs_mem_idx >= 0
            abs_mem_value = cmd[abs_mem_idx + 1]
            assert abs_mem_value == "16"  # Default for development tier
    
    def test_wsclean_command_structure(self, mock_wsclean_subprocess, temp_work_dir):
        """Test that WSClean command has correct structure."""
        from dsa110_contimg.imaging.cli_imaging import run_wsclean
        
        ms_path = "/fake/test.ms"
        imagename = str(temp_work_dir / "test.img")
        
        with patch('subprocess.run', side_effect=mock_wsclean_subprocess) as mock_subprocess, \
             patch('shutil.which', return_value='/usr/bin/wsclean'):
            
            run_wsclean(
                ms_path=ms_path,
                imagename=imagename,
                datacolumn="data",
                field="",
                imsize=2048,
                cell_arcsec=1.0,
                weighting="briggs",
                robust=0.5,
                specmode="mfs",
                deconvolver="hogbom",
                nterms=1,
                niter=1000,
                threshold="0.1Jy",
                pbcor=True,
                uvrange=">1klambda",
                pblimit=0.2,
                quality_tier="standard",
            )
            
            # Get the command
            call_args = mock_subprocess.call_args
            cmd = call_args[0][0]
            
            # Verify essential parameters are present
            assert '-name' in cmd
            assert '-size' in cmd
            assert '-scale' in cmd
            assert '-weight' in cmd
            assert '-niter' in cmd
            assert '-abs-mem' in cmd
            
            # Verify values
            name_idx = cmd.index('-name')
            assert cmd[name_idx + 1] == imagename
            
            size_idx = cmd.index('-size')
            assert cmd[size_idx + 1] == '2048'
            assert cmd[size_idx + 2] == '2048'


@pytest.mark.unit
class TestImagingUtils:
    """Test imaging utility functions with mocking."""
    
    def test_detect_datacolumn_corrected_exists(self, temp_work_dir):
        """Test detect_datacolumn when CORRECTED_DATA exists with non-zero values."""
        from dsa110_contimg.imaging.cli_utils import detect_datacolumn
        
        ms_path = str(temp_work_dir / "test.ms")
        Path(ms_path).mkdir(parents=True, exist_ok=True)
        
        # Create mock table that returns CORRECTED_DATA with non-zero values
        def mock_table_with_corrected(path, readonly=True):
            ctx = MagicMock()
            ctx.__enter__ = Mock(return_value=ctx)
            ctx.__exit__ = Mock(return_value=None)
            
            # Return non-zero corrected data
            corrected_data = np.random.random((100, 1, 4)) + 1j * np.random.random((100, 1, 4))
            flags = np.zeros((100, 1, 4), dtype=bool)
            
            def mock_getcol(colname, start=0, n=100):
                if colname == 'CORRECTED_DATA':
                    return corrected_data
                elif colname == 'FLAG':
                    return flags
                return np.array([])
            
            ctx.getcol = Mock(side_effect=mock_getcol)
            ctx.colnames.return_value = ['DATA', 'CORRECTED_DATA', 'FLAG']
            ctx.nrows.return_value = 1000
            return ctx
        
        with patch('dsa110_contimg.imaging.cli_utils.table', side_effect=mock_table_with_corrected):
            result = detect_datacolumn(ms_path)
            assert result == 'corrected'
    
    def test_detect_datacolumn_data_fallback(self, temp_work_dir):
        """Test detect_datacolumn falls back to DATA when CORRECTED_DATA missing."""
        from dsa110_contimg.imaging.cli_utils import detect_datacolumn
        
        ms_path = str(temp_work_dir / "test.ms")
        Path(ms_path).mkdir(parents=True, exist_ok=True)
        
        # Create mock table without CORRECTED_DATA
        def mock_table_no_corrected(path, readonly=True):
            ctx = MagicMock()
            ctx.__enter__ = Mock(return_value=ctx)
            ctx.__exit__ = Mock(return_value=None)
            ctx.colnames.return_value = ['DATA', 'FLAG']  # No CORRECTED_DATA
            return ctx
        
        with patch('dsa110_contimg.imaging.cli_utils.table', side_effect=mock_table_no_corrected):
            result = detect_datacolumn(ms_path)
            assert result == 'data'
    
    def test_default_cell_arcsec_calculation(self, temp_work_dir):
        """Test default cell size calculation."""
        from dsa110_contimg.imaging.cli_utils import default_cell_arcsec
        
        ms_path = str(temp_work_dir / "test.ms")
        Path(ms_path).mkdir(parents=True, exist_ok=True)
        
        # Mock UVW and frequency data
        def mock_table_with_uvw(path, readonly=True):
            ctx = MagicMock()
            ctx.__enter__ = Mock(return_value=ctx)
            ctx.__exit__ = Mock(return_value=None)
            
            if "SPECTRAL_WINDOW" in path:
                ctx.getcol.return_value = np.array([[1.4e9, 1.41e9, 1.42e9, 1.43e9]])
            elif "DATA_DESCRIPTION" in path:
                ctx.getcol.return_value = np.array([0])  # SPECTRAL_WINDOW_ID
            elif "MAIN" in path or path == ms_path:
                ctx.getcol.return_value = np.array([[1000.0, 500.0, 200.0]])  # UVW
                ctx.nrows.return_value = 1000
            return ctx
        
        with patch('casacore.tables.table', side_effect=mock_table_with_uvw), \
             patch('daskms.xds_from_ms', side_effect=ImportError("daskms not available")):
            cell = default_cell_arcsec(ms_path)
            # Should return a reasonable cell size (0.1 to 60 arcsec)
            assert 0.1 <= cell <= 60.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
