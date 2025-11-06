#!/usr/bin/env python3
"""
Unit tests for quality tier logic.

Tests the different quality tier behaviors (development, standard, high_precision)
and their parameter modifications.

Run with: pytest tests/unit/test_quality_tier.py -v
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock

import numpy as np
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.mark.unit
class TestQualityTierDevelopment:
    """Test development quality tier behavior."""
    
    def test_development_tier_cell_size_multiplier(self, mock_table_factory):
        """Test that development tier multiplies cell size by 4x."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        
        ms_path = "/fake/test.ms"
        imagename = "/fake/test.img"
        default_cell = 2.0
        
        with patch('casacore.tables.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.default_cell_arcsec', return_value=default_cell), \
             patch('dsa110_contimg.imaging.cli_utils.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.run_wsclean') as mock_wsclean, \
             patch('dsa110_contimg.utils.validation.validate_ms'), \
             patch('dsa110_contimg.utils.validation.validate_corrected_data_quality'):
            
            # Call with development tier and default cell size
            image_ms(
                ms_path,
                imagename=imagename,
                quality_tier="development",
                cell_arcsec=None,  # Use default
            )
            
            # Verify cell size was multiplied by 4
            call_args = mock_wsclean.call_args
            assert call_args[1]['cell_arcsec'] == default_cell * 4.0
    
    def test_development_tier_cell_size_custom_not_multiplied(self, mock_table_factory):
        """Test that custom cell size is not multiplied in development tier."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        
        ms_path = "/fake/test.ms"
        imagename = "/fake/test.img"
        custom_cell = 5.0
        
        with patch('casacore.tables.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_utils.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.run_wsclean') as mock_wsclean, \
             patch('dsa110_contimg.utils.validation.validate_ms'), \
             patch('dsa110_contimg.utils.validation.validate_corrected_data_quality'):
            
            # Call with development tier and custom cell size
            image_ms(
                ms_path,
                imagename=imagename,
                quality_tier="development",
                cell_arcsec=custom_cell,  # Custom value
            )
            
            # Verify custom cell size was NOT multiplied
            call_args = mock_wsclean.call_args
            assert call_args[1]['cell_arcsec'] == custom_cell
    
    def test_development_tier_iteration_limit(self, mock_table_factory):
        """Test that development tier limits iterations to 300."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        
        ms_path = "/fake/test.ms"
        imagename = "/fake/test.img"
        
        with patch('casacore.tables.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_utils.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.run_wsclean') as mock_wsclean, \
             patch('dsa110_contimg.utils.validation.validate_ms'), \
             patch('dsa110_contimg.utils.validation.validate_corrected_data_quality'):
            
            # Call with high iteration count
            image_ms(
                ms_path,
                imagename=imagename,
                quality_tier="development",
                niter=5000,
            )
            
            # Verify iterations were capped at 300
            call_args = mock_wsclean.call_args
            assert call_args[1]['niter'] == 300
    
    def test_development_tier_nvss_threshold(self, mock_table_factory):
        """Test that development tier sets NVSS threshold to 10 mJy."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        
        ms_path = "/fake/test.ms"
        imagename = "/fake/test.img"
        
        with patch('casacore.tables.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_utils.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.run_wsclean'), \
             patch('dsa110_contimg.utils.validation.validate_ms'), \
             patch('dsa110_contimg.utils.validation.validate_corrected_data_quality'), \
             patch('dsa110_contimg.calibration.skymodels.make_nvss_component_cl') as mock_make_cl, \
             patch('dsa110_contimg.calibration.skymodels.ft_from_cl'), \
             patch('os.path.exists', return_value=True):
            
            def mock_table_with_phase_center(path, readonly=True):
                ctx = MagicMock()
                ctx.__enter__ = Mock(return_value=ctx)
                ctx.__exit__ = Mock(return_value=None)
                if "FIELD" in path:
                    ctx.getcol.return_value = np.array([[[np.radians(120.0), np.radians(45.0)]]])
                elif "SPECTRAL_WINDOW" in path:
                    ctx.getcol.return_value = np.array([[1.4e9, 1.41e9, 1.42e9, 1.43e9]])
                else:
                    ctx.colnames.return_value = []
                    ctx.nrows.return_value = 1000
                return ctx
            
            with patch('casacore.tables.table', side_effect=mock_table_with_phase_center):
                # Call with development tier and no explicit NVSS threshold
                image_ms(
                    ms_path,
                    imagename=imagename,
                    quality_tier="development",
                    nvss_min_mjy=None,  # Should default to 10.0
                )
                
                # Verify NVSS was called with 10 mJy threshold
                assert mock_make_cl.called
                call_args = mock_make_cl.call_args
                assert call_args[1]['min_mjy'] == 10.0


@pytest.mark.unit
class TestQualityTierStandard:
    """Test standard quality tier behavior."""
    
    def test_standard_tier_no_modifications(self, mock_table_factory):
        """Test that standard tier doesn't modify parameters."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        
        ms_path = "/fake/test.ms"
        imagename = "/fake/test.img"
        
        with patch('casacore.tables.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_utils.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.run_wsclean') as mock_wsclean, \
             patch('dsa110_contimg.utils.validation.validate_ms'), \
             patch('dsa110_contimg.utils.validation.validate_corrected_data_quality'):
            
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


@pytest.mark.unit
class TestQualityTierHighPrecision:
    """Test high_precision quality tier behavior."""
    
    def test_high_precision_tier_iterations(self, mock_table_factory):
        """Test that high_precision tier uses high iteration count."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        
        ms_path = "/fake/test.ms"
        imagename = "/fake/test.img"
        
        with patch('casacore.tables.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_utils.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.run_wsclean') as mock_wsclean, \
             patch('dsa110_contimg.utils.validation.validate_ms'), \
             patch('dsa110_contimg.utils.validation.validate_corrected_data_quality'):
            
            # Call with high_precision tier
            image_ms(
                ms_path,
                imagename=imagename,
                quality_tier="high_precision",
                niter=2000,
            )
            
            # Verify high iteration count is used
            call_args = mock_wsclean.call_args
            assert call_args[1]['niter'] == 2000  # Should not be capped
    
    def test_high_precision_tier_nvss_threshold(self, mock_table_factory):
        """Test that high_precision tier uses lower NVSS threshold (5 mJy)."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        
        ms_path = "/fake/test.ms"
        imagename = "/fake/test.img"
        
        def mock_table_with_phase_center(path, readonly=True):
            ctx = MagicMock()
            ctx.__enter__ = Mock(return_value=ctx)
            ctx.__exit__ = Mock(return_value=None)
            if "FIELD" in path:
                ctx.getcol.return_value = np.array([[[np.radians(120.0), np.radians(45.0)]]])
            elif "SPECTRAL_WINDOW" in path:
                ctx.getcol.return_value = np.array([[1.4e9, 1.41e9, 1.42e9, 1.43e9]])
            else:
                ctx.colnames.return_value = []
                ctx.nrows.return_value = 1000
            return ctx
        
        with patch('casacore.tables.table', side_effect=mock_table_with_phase_center), \
             patch('dsa110_contimg.imaging.cli_utils.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_utils.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.run_wsclean'), \
             patch('dsa110_contimg.utils.validation.validate_ms'), \
             patch('dsa110_contimg.utils.validation.validate_corrected_data_quality'), \
             patch('dsa110_contimg.calibration.skymodels.make_nvss_component_cl') as mock_make_cl, \
             patch('dsa110_contimg.calibration.skymodels.ft_from_cl'), \
             patch('os.path.exists', return_value=True):
            
            # Call with high_precision tier and no explicit NVSS threshold
            image_ms(
                ms_path,
                imagename=imagename,
                quality_tier="high_precision",
                nvss_min_mjy=None,  # Should default to 5.0
            )
            
            # Verify NVSS was called with 5 mJy threshold
            assert mock_make_cl.called
            call_args = mock_make_cl.call_args
            assert call_args[1]['min_mjy'] == 5.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

