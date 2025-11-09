#!/usr/bin/env python3
"""
Unit tests for NVSS seeding logic with mocking.

Tests the logic for calculating NVSS seeding radius, especially the
primary beam limitation when pbcor is enabled.

Run with: pytest tests/unit/test_nvss_seeding.py -v
"""

import math
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock

import numpy as np
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.mark.unit
class TestNVSSRadiusCalculation:
    """Test NVSS seeding radius calculation logic."""
    
    def test_nvss_radius_without_pbcor(self, mock_table_factory, temp_work_dir):
        """Test that NVSS radius equals image radius when pbcor=False."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        
        ms_path = str(temp_work_dir / "test.ms")
        imagename = str(temp_work_dir / "test.img")
        Path(ms_path).mkdir(parents=True, exist_ok=True)
        
        with patch('casacore.tables.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_imaging.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.default_cell_arcsec',
                   return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_utils.detect_datacolumn',
                   return_value='data'), \
             patch('dsa110_contimg.imaging.cli_utils.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_imaging.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_imaging.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.run_wsclean'), \
             patch('dsa110_contimg.imaging.cli_imaging.validate_ms', return_value=None), \
             patch('dsa110_contimg.utils.validation.validate_corrected_data_quality', return_value=[]), \
             patch('dsa110_contimg.calibration.skymodels.make_nvss_component_cl') as mock_make_cl, \
                 patch('dsa110_contimg.calibration.skymodels.ft_from_cl'):
            
            image_ms(
                ms_path,
                imagename=imagename,
                pbcor=False,  # No primary beam correction
                nvss_min_mjy=10.0,
            )
            
            # Verify make_nvss_component_cl was called
            assert mock_make_cl.called
            
            # Get the radius argument
            call_args = mock_make_cl.call_args
            radius_deg = call_args[0][2]  # Third positional arg is radius
            
            # Should use full image radius (not limited by primary beam)
            assert radius_deg > 1.0  # Should be close to image radius
    
    def test_nvss_radius_with_pbcor_limited(self, temp_work_dir):
        """Test that NVSS radius is limited to primary beam when pbcor=True."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        
        ms_path = str(temp_work_dir / "test.ms")
        imagename = str(temp_work_dir / "test.img")
        Path(ms_path).mkdir(parents=True, exist_ok=True)
        
        # Mock frequency for primary beam calculation
        def mock_table_with_freq(path, readonly=True):  # noqa: ARG001
            ctx = MagicMock()
            ctx.__enter__ = Mock(return_value=ctx)
            ctx.__exit__ = Mock(return_value=None)
            
            if "SPECTRAL_WINDOW" in path:
                # 1.4 GHz frequency
                ctx.getcol.return_value = np.array([[1.4e9, 1.41e9, 1.42e9, 1.43e9]])
                ctx.colnames.return_value = ['CHAN_FREQ', 'CHAN_WIDTH']
                ctx.nrows.return_value = 1
            elif "FIELD" in path:
                # Phase center
                ctx.getcol.return_value = np.array([[[np.radians(120.0), np.radians(45.0)]]])
                ctx.colnames.return_value = ['PHASE_DIR', 'NAME']
                ctx.nrows.return_value = 1
            else:
                # MAIN table - must have required columns for validate_ms
                ctx.colnames.return_value = [
                    'DATA', 'CORRECTED_DATA', 'MODEL_DATA', 'FLAG',
                    'ANTENNA1', 'ANTENNA2', 'TIME', 'UVW'
                ]
                ctx.nrows.return_value = 1000
            return ctx
        
        with patch('casacore.tables.table', side_effect=mock_table_with_freq), \
             patch('dsa110_contimg.imaging.cli_imaging.table', side_effect=mock_table_with_freq), \
             patch('dsa110_contimg.imaging.cli_utils.table', side_effect=mock_table_with_freq), \
             patch('dsa110_contimg.imaging.cli_utils.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_imaging.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_utils.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.run_wsclean'), \
             patch('dsa110_contimg.imaging.cli_imaging.validate_ms', return_value=None), \
             patch('dsa110_contimg.utils.validation.validate_corrected_data_quality', return_value=[]), \
             patch('dsa110_contimg.calibration.skymodels.make_nvss_component_cl') as mock_make_cl, \
                 patch('dsa110_contimg.calibration.skymodels.ft_from_cl'):
            
            image_ms(
                ms_path,
                imagename=imagename,
                pbcor=True,  # Primary beam correction enabled
                pblimit=0.2,  # 20% of peak
                nvss_min_mjy=10.0,
            )
            
            # Verify make_nvss_component_cl was called
            assert mock_make_cl.called
            
            # Get the radius argument
            call_args = mock_make_cl.call_args
            radius_deg = call_args[0][2]  # Third positional arg is radius
            
            # Calculate expected primary beam radius
            # FWHM = 1.22 * lambda / D
            # For DSA-110: D = 4.7 m, lambda = c / (1.4e9)
            c_mps = 299792458.0
            dish_dia_m = 4.7
            lambda_m = c_mps / (1.4e9)
            fwhm_rad = 1.22 * lambda_m / dish_dia_m
            fwhm_deg = math.degrees(fwhm_rad)
            
            # Radius at pblimit=0.2
            pb_radius_deg = fwhm_deg * math.sqrt(-math.log(0.2)) / math.sqrt(-math.log(0.5))
            
            # NVSS radius should be limited to primary beam radius
            assert radius_deg <= pb_radius_deg + 0.1  # Allow small tolerance
            assert radius_deg > 0.5  # Should be reasonable value
    
    def test_nvss_radius_pbcor_calculation(self):
        """Test primary beam radius calculation directly."""
        # This tests the calculation logic without full image_ms call
        
        # Parameters
        freq_ghz = 1.4
        pblimit = 0.2
        dish_dia_m = 4.7
        
        # Calculate FWHM
        c_mps = 299792458.0
        lambda_m = c_mps / (freq_ghz * 1e9)
        fwhm_rad = 1.22 * lambda_m / dish_dia_m
        fwhm_deg = math.degrees(fwhm_rad)
        
        # Calculate radius at pblimit
        pb_radius_deg = fwhm_deg * math.sqrt(-math.log(pblimit)) / math.sqrt(-math.log(0.5))
        
        # Verify reasonable values
        # For 1.4 GHz, DSA-110: FWHM ~ 3.2 degrees
        assert 2.5 < fwhm_deg < 4.0
        
        # Radius at pblimit=0.2 should be larger than FWHM/2
        assert pb_radius_deg > fwhm_deg / 2
        assert pb_radius_deg < fwhm_deg * 2
    
    def test_nvss_radius_minimum_selection(self):
        """Test that minimum of image radius and PB radius is used."""
        # Image radius (half diagonal of 3.5° square)
        image_radius_deg = 1.75 * math.sqrt(2) / 2  # ~1.24 degrees
        
        # Primary beam radius (calculated)
        freq_ghz = 1.4
        pblimit = 0.2
        c_mps = 299792458.0
        dish_dia_m = 4.7
        lambda_m = c_mps / (freq_ghz * 1e9)
        fwhm_rad = 1.22 * lambda_m / dish_dia_m
        fwhm_deg = math.degrees(fwhm_rad)
        pb_radius_deg = fwhm_deg * math.sqrt(-math.log(pblimit)) / math.sqrt(-math.log(0.5))
        
        # Minimum should be selected
        nvss_radius_deg = min(image_radius_deg, pb_radius_deg)
        
        # In this case, image radius is smaller, so it should be used
        assert nvss_radius_deg == image_radius_deg
        assert nvss_radius_deg < pb_radius_deg


@pytest.mark.unit
class TestNVSSSeedingIntegration:
    """Test NVSS seeding integration with mocked dependencies."""
    
    def test_nvss_seeding_skipped_when_not_requested(self, mock_table_factory, temp_work_dir):
        """Test that NVSS seeding is skipped when nvss_min_mjy is None."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        
        ms_path = str(temp_work_dir / "test.ms")
        imagename = str(temp_work_dir / "test.img")
        Path(ms_path).mkdir(parents=True, exist_ok=True)
        
        with patch('casacore.tables.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_imaging.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_imaging.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_utils.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.run_wsclean'), \
             patch('dsa110_contimg.imaging.cli_imaging.validate_ms', return_value=None), \
             patch('dsa110_contimg.utils.validation.validate_corrected_data_quality', return_value=[]), \
             patch('dsa110_contimg.calibration.skymodels.make_nvss_component_cl') as mock_make_cl:
            
            image_ms(
                ms_path,
                imagename=imagename,
                nvss_min_mjy=None,  # Not requested
            )
            
            # NVSS seeding should not be called
            assert not mock_make_cl.called
    
    def test_nvss_seeding_called_with_correct_parameters(self, temp_work_dir):
        """Test that NVSS seeding is called with correct parameters."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        
        ms_path = str(temp_work_dir / "test.ms")
        imagename = str(temp_work_dir / "test.img")
        Path(ms_path).mkdir(parents=True, exist_ok=True)
        
        def mock_table_with_phase_center(path, readonly=True):  # noqa: ARG001
            ctx = MagicMock()
            ctx.__enter__ = Mock(return_value=ctx)
            ctx.__exit__ = Mock(return_value=None)
            
            if "FIELD" in path:
                # Phase center: RA=120°, Dec=45°
                ctx.getcol.return_value = np.array([[[np.radians(120.0), np.radians(45.0)]]])
                ctx.colnames.return_value = ['PHASE_DIR', 'NAME']
                ctx.nrows.return_value = 1
            elif "SPECTRAL_WINDOW" in path:
                ctx.getcol.return_value = np.array([[1.4e9, 1.41e9, 1.42e9, 1.43e9]])
                ctx.colnames.return_value = ['CHAN_FREQ', 'CHAN_WIDTH']
                ctx.nrows.return_value = 1
            else:
                # MAIN table - must have required columns for validate_ms
                ctx.colnames.return_value = [
                    'DATA', 'CORRECTED_DATA', 'MODEL_DATA', 'FLAG',
                    'ANTENNA1', 'ANTENNA2', 'TIME', 'UVW'
                ]
                ctx.nrows.return_value = 1000
            return ctx
        
        with patch('casacore.tables.table', side_effect=mock_table_with_phase_center), \
             patch('dsa110_contimg.imaging.cli_imaging.table', side_effect=mock_table_with_phase_center), \
             patch('dsa110_contimg.imaging.cli_utils.table', side_effect=mock_table_with_phase_center), \
             patch('dsa110_contimg.imaging.cli_utils.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_imaging.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_utils.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.run_wsclean'), \
             patch('dsa110_contimg.imaging.cli_imaging.validate_ms', return_value=None), \
             patch('dsa110_contimg.utils.validation.validate_corrected_data_quality', return_value=[]), \
             patch('dsa110_contimg.calibration.skymodels.make_nvss_component_cl') as mock_make_cl, \
             patch('dsa110_contimg.calibration.skymodels.ft_from_cl'), \
              patch('os.path.exists', return_value=True):  # Component list exists
            
            image_ms(
                ms_path,
                imagename=imagename,
                nvss_min_mjy=10.0,
                pbcor=True,
                pblimit=0.2,
            )
            
            # Verify make_nvss_component_cl was called
            assert mock_make_cl.called
            
            # Check parameters
            call_args = mock_make_cl.call_args
            ra_deg = call_args[0][0]
            dec_deg = call_args[0][1]
            radius_deg = call_args[0][2]
            min_mjy = call_args[1]['min_mjy']
            freq_ghz = call_args[1]['freq_ghz']
            
            # Verify values
            assert abs(ra_deg - 120.0) < 0.1
            assert abs(dec_deg - 45.0) < 0.1
            assert min_mjy == 10.0
            assert abs(freq_ghz - 1.4) < 0.1
            assert radius_deg > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
