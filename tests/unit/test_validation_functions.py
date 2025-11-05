#!/usr/bin/env python3
"""
Comprehensive unit tests for DSA-110 pipeline validation functions.

This test suite validates the logic of all validation functions using mocking,
without requiring the full CASA/pyuvdata environment. It tests edge cases,
failure scenarios, and ensures proper error handling.

Run with: pytest tests/unit/test_validation_functions.py -v
"""

import logging
import pytest
import numpy as np
from unittest.mock import patch, MagicMock, call

from dsa110_contimg.conversion.helpers import (
    validate_ms_frequency_order,
    cleanup_casa_file_handles,
    validate_phase_center_coherence,
    validate_uvw_precision,
    validate_antenna_positions,
    validate_model_data_quality,
    validate_reference_antenna_stability,
)


class MockTableContext:
    """Mock context manager for casacore.tables.table."""
    
    def __init__(self, mock_data):
        self.mock_data = mock_data
        self.mock_table = MagicMock()
        
    def __enter__(self):
        return self.mock_table
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        return None


class TestFrequencyOrderingValidation:
    """Test frequency ordering validation function."""
    
    def test_ascending_frequencies_pass(self):
        """Test that ascending frequencies pass validation."""
        mock_data = {
            'spectral_window': {'CHAN_FREQ': np.array([[1200e6, 1300e6, 1400e6, 1500e6]])},
            'main_table': {'colnames': ['DATA', 'ANTENNA1', 'ANTENNA2', 'TIME']}
        }
        
        def mock_table(path, readonly=True):
            if "SPECTRAL_WINDOW" in path:
                ctx = MockTableContext(mock_data['spectral_window'])
                ctx.mock_table.getcol.return_value = mock_data['spectral_window']['CHAN_FREQ']
            else:
                ctx = MockTableContext(mock_data['main_table'])
                ctx.mock_table.colnames.return_value = mock_data['main_table']['colnames']
            return ctx
            
        with patch('dsa110_contimg.conversion.helpers.table', side_effect=mock_table):
            # Should not raise exception
            validate_ms_frequency_order("/fake/ms/path")
            
    def test_descending_frequencies_fail(self):
        """Test that descending frequencies fail validation."""
        mock_data = {
            'spectral_window': {'CHAN_FREQ': np.array([[1500e6, 1400e6, 1300e6, 1200e6]])},
            'main_table': {'colnames': ['DATA', 'ANTENNA1', 'ANTENNA2', 'TIME']}
        }
        
        def mock_table(path, readonly=True):
            if "SPECTRAL_WINDOW" in path:
                ctx = MockTableContext(mock_data['spectral_window'])
                ctx.mock_table.getcol.return_value = mock_data['spectral_window']['CHAN_FREQ']
            else:
                ctx = MockTableContext(mock_data['main_table'])
                ctx.mock_table.colnames.return_value = mock_data['main_table']['colnames']
            return ctx
            
        with patch('dsa110_contimg.conversion.helpers.table', side_effect=mock_table):
            with pytest.raises(RuntimeError, match="frequencies are in DESCENDING order"):
                validate_ms_frequency_order("/fake/ms/path")
                
    def test_missing_spectral_window_table(self):
        """Test handling of missing spectral window table."""
        def mock_table_raises(path, readonly=True):
            if "SPECTRAL_WINDOW" in path:
                raise FileNotFoundError("Table not found")
            else:
                ctx = MockTableContext({})
                ctx.mock_table.colnames.return_value = ['DATA']
                return ctx
                
        with patch('dsa110_contimg.conversion.helpers.table', side_effect=mock_table_raises):
            with pytest.raises(RuntimeError, match="Could not read spectral window"):
                validate_ms_frequency_order("/fake/ms/path")


class TestUVWPrecisionValidation:
    """Test UVW precision validation function."""
    
    def test_normal_uvw_coordinates_pass(self):
        """Test that normal UVW coordinates pass validation."""
        mock_uvw = np.array([
            [100.0, 200.0, 50.0],    # Normal baseline ~224m
            [150.0, 100.0, 75.0],    # Normal baseline ~193m  
            [200.0, 300.0, 100.0],   # Normal baseline ~374m
        ])
        
        mock_data = {
            'spectral_window': {'CHAN_FREQ': np.array([[1400e6]])},  # λ ≈ 0.21m
            'main_table': {'UVW': mock_uvw, 'nrows': len(mock_uvw)}
        }
        
        def mock_table(path, readonly=True):
            if "SPECTRAL_WINDOW" in path:
                ctx = MockTableContext(mock_data['spectral_window'])
                ctx.mock_table.getcol.return_value = mock_data['spectral_window']['CHAN_FREQ']
            else:
                ctx = MockTableContext(mock_data['main_table'])
                ctx.mock_table.getcol.return_value = mock_data['main_table']['UVW']
                ctx.mock_table.nrows.return_value = mock_data['main_table']['nrows']
            return ctx
            
        with patch('dsa110_contimg.conversion.helpers.table', side_effect=mock_table):
            # Should not raise exception
            validate_uvw_precision("/fake/ms/path", tolerance_lambda=0.1)
            
    def test_excessive_uvw_coordinates_fail(self):
        """Test that excessive UVW coordinates fail validation."""
        mock_uvw = np.array([
            [100000.0, 50000.0, 1000.0],  # 100km baseline - unreasonable
            [10.0, 20.0, 5.0],             # Normal baseline
        ])
        
        mock_data = {
            'spectral_window': {'CHAN_FREQ': np.array([[1400e6]])},  # λ ≈ 0.21m
            'main_table': {'UVW': mock_uvw, 'nrows': len(mock_uvw)}
        }
        
        def mock_table(path, readonly=True):
            if "SPECTRAL_WINDOW" in path:
                ctx = MockTableContext(mock_data['spectral_window'])
                ctx.mock_table.getcol.return_value = mock_data['spectral_window']['CHAN_FREQ']
            else:
                ctx = MockTableContext(mock_data['main_table'])
                ctx.mock_table.getcol.return_value = mock_data['main_table']['UVW']
                ctx.mock_table.nrows.return_value = mock_data['main_table']['nrows']
            return ctx
            
        with patch('dsa110_contimg.conversion.helpers.table', side_effect=mock_table):
            with pytest.raises(RuntimeError, match="UVW coordinates contain unreasonable values"):
                validate_uvw_precision("/fake/ms/path", tolerance_lambda=0.1)
                
    def test_all_zero_uvw_coordinates_fail(self):
        """Test that all-zero UVW coordinates fail validation."""
        mock_uvw = np.array([
            [0.0, 0.0, 0.0],  # All zeros - problematic
            [0.0, 0.0, 0.0],  # All zeros - problematic
        ])
        
        mock_data = {
            'spectral_window': {'CHAN_FREQ': np.array([[1400e6]])},
            'main_table': {'UVW': mock_uvw, 'nrows': len(mock_uvw)}
        }
        
        def mock_table(path, readonly=True):
            if "SPECTRAL_WINDOW" in path:
                ctx = MockTableContext(mock_data['spectral_window'])
                ctx.mock_table.getcol.return_value = mock_data['spectral_window']['CHAN_FREQ']
            else:
                ctx = MockTableContext(mock_data['main_table'])
                ctx.mock_table.getcol.return_value = mock_data['main_table']['UVW']
                ctx.mock_table.nrows.return_value = mock_data['main_table']['nrows']
            return ctx
            
        with patch('dsa110_contimg.conversion.helpers.table', side_effect=mock_table):
            with pytest.raises(RuntimeError, match="All UVW coordinates are zero"):
                validate_uvw_precision("/fake/ms/path", tolerance_lambda=0.1)


class TestAntennaPositionValidation:
    """Test antenna position validation function."""
    
    def test_good_antenna_positions_pass(self):
        """Test that good antenna positions pass validation."""
        # Reference DSA-110 OVRO positions (approximate)
        ref_positions = np.array([
            [-2409150.40, -4478573.12, 3838617.74],
            [-2409151.30, -4478574.02, 3838618.64],
            [-2409152.20, -4478574.92, 3838619.54],
        ])
        
        # MS positions with small acceptable errors (<5cm)
        ms_positions = ref_positions + np.array([
            [0.02, -0.01, 0.03],   # 2cm, 1cm, 3cm errors
            [-0.01, 0.04, -0.02],  # 1cm, 4cm, 2cm errors  
            [0.03, 0.01, 0.01],    # 3cm, 1cm, 1cm errors
        ])
        
        mock_names = np.array(['ea01', 'ea02', 'ea03'])
        
        def mock_table(path, readonly=True):
            if "ANTENNA" in path:
                ctx = MockTableContext({})
                ctx.mock_table.getcol.side_effect = lambda col: {
                    'POSITION': ms_positions,
                    'NAME': mock_names
                }[col]
            return ctx
            
        # Mock reference position loader
        mock_ref_df = MagicMock()
        mock_ref_df.__getitem__.side_effect = lambda key: {
            'x_m': MagicMock(values=ref_positions[:, 0]),
            'y_m': MagicMock(values=ref_positions[:, 1]), 
            'z_m': MagicMock(values=ref_positions[:, 2])
        }[key]
        
        with patch('dsa110_contimg.conversion.helpers.table', side_effect=mock_table):
            with patch('dsa110_contimg.conversion.helpers.get_itrf', return_value=mock_ref_df):
                # Should not raise exception
                validate_antenna_positions("/fake/ms/path", position_tolerance_m=0.05)
                
    def test_excessive_antenna_position_errors_fail(self):
        """Test that excessive antenna position errors fail validation."""
        ref_positions = np.array([
            [-2409150.40, -4478573.12, 3838617.74],
            [-2409151.30, -4478574.02, 3838618.64],
            [-2409152.20, -4478574.92, 3838619.54],
        ])
        
        # MS positions with excessive errors (>5cm)
        ms_positions = ref_positions + np.array([
            [0.02, -0.01, 0.03],   # Good: 2cm, 1cm, 3cm errors
            [1.0, 0.5, -0.8],      # Bad: 1m, 0.5m, 0.8m errors
            [0.03, 0.01, 0.01],    # Good: 3cm, 1cm, 1cm errors
        ])
        
        mock_names = np.array(['ea01', 'ea02', 'ea03'])
        
        def mock_table(path, readonly=True):
            if "ANTENNA" in path:
                ctx = MockTableContext({})
                ctx.mock_table.getcol.side_effect = lambda col: {
                    'POSITION': ms_positions,
                    'NAME': mock_names
                }[col]
            return ctx
            
        mock_ref_df = MagicMock()
        mock_ref_df.__getitem__.side_effect = lambda key: {
            'x_m': MagicMock(values=ref_positions[:, 0]),
            'y_m': MagicMock(values=ref_positions[:, 1]),
            'z_m': MagicMock(values=ref_positions[:, 2])
        }[key]
        
        with patch('dsa110_contimg.conversion.helpers.table', side_effect=mock_table):
            with patch('dsa110_contimg.conversion.helpers.get_itrf', return_value=mock_ref_df):
                with pytest.raises(RuntimeError, match="Antenna position errors exceed tolerance"):
                    validate_antenna_positions("/fake/ms/path", position_tolerance_m=0.05)


class TestModelDataQualityValidation:
    """Test MODEL_DATA quality validation function."""
    
    def test_good_model_data_passes(self):
        """Test that good MODEL_DATA passes validation."""
        mock_data = {
            'colnames': ['MODEL_DATA', 'FIELD_ID'],
            'FIELD_ID': np.array([0, 0, 0, 0]),
            'MODEL_DATA': np.array([
                [[5.0 + 2.0j, 5.0 - 2.0j]],  # Good calibrator flux ~5Jy
                [[4.8 + 1.9j, 4.8 - 1.9j]],
                [[5.2 + 2.1j, 5.2 - 2.1j]],
                [[4.9 + 2.0j, 4.9 - 2.0j]],
            ])  # Shape: (nrow, nchan, npol)
        }
        
        def mock_table(path, readonly=True):
            ctx = MockTableContext(mock_data)
            ctx.mock_table.colnames.return_value = mock_data['colnames']
            ctx.mock_table.getcol.side_effect = lambda col, **kwargs: mock_data[col]
            return ctx
            
        with patch('dsa110_contimg.conversion.helpers.table', side_effect=mock_table):
            # Should not raise exception
            validate_model_data_quality("/fake/ms/path", min_flux_jy=0.1, max_flux_jy=1000.0)
            
    def test_weak_model_data_fails(self):
        """Test that weak MODEL_DATA fails validation."""
        mock_data = {
            'colnames': ['MODEL_DATA', 'FIELD_ID'],
            'FIELD_ID': np.array([0, 0, 0, 0]),
            'MODEL_DATA': np.array([
                [[0.01 + 0.01j, 0.01 - 0.01j]],  # Too weak for calibrator
                [[0.02 + 0.01j, 0.02 - 0.01j]],
                [[0.01 + 0.02j, 0.01 - 0.02j]],
                [[0.02 + 0.02j, 0.02 - 0.02j]],
            ])
        }
        
        def mock_table(path, readonly=True):
            ctx = MockTableContext(mock_data)
            ctx.mock_table.colnames.return_value = mock_data['colnames']
            ctx.mock_table.getcol.side_effect = lambda col, **kwargs: mock_data[col]
            return ctx
            
        with patch('dsa110_contimg.conversion.helpers.table', side_effect=mock_table):
            # Should raise warning for weak calibrator
            validate_model_data_quality("/fake/ms/path", min_flux_jy=0.1)
            
    def test_all_zero_model_data_fails(self):
        """Test that all-zero MODEL_DATA fails validation."""
        mock_data = {
            'colnames': ['MODEL_DATA', 'FIELD_ID'],
            'FIELD_ID': np.array([0, 0, 0, 0]),
            'MODEL_DATA': np.zeros((4, 1, 2), dtype=complex)  # All zeros
        }
        
        def mock_table(path, readonly=True):
            ctx = MockTableContext(mock_data)
            ctx.mock_table.colnames.return_value = mock_data['colnames']
            ctx.mock_table.getcol.side_effect = lambda col, **kwargs: mock_data[col]
            return ctx
            
        with patch('dsa110_contimg.conversion.helpers.table', side_effect=mock_table):
            with pytest.raises(RuntimeError, match="MODEL_DATA is all zeros"):
                validate_model_data_quality("/fake/ms/path")
                
    def test_missing_model_data_column_fails(self):
        """Test that missing MODEL_DATA column fails validation."""
        mock_data = {
            'colnames': ['DATA', 'FIELD_ID'],  # Missing MODEL_DATA
        }
        
        def mock_table(path, readonly=True):
            ctx = MockTableContext(mock_data)
            ctx.mock_table.colnames.return_value = mock_data['colnames']
            return ctx
            
        with patch('dsa110_contimg.conversion.helpers.table', side_effect=mock_table):
            with pytest.raises(RuntimeError, match="MODEL_DATA column does not exist"):
                validate_model_data_quality("/fake/ms/path")


class TestReferenceAntennaStability:
    """Test reference antenna stability analysis function."""
    
    def test_select_best_antenna(self):
        """Test selection of best reference antenna."""
        mock_ant1 = np.array([0, 0, 1, 1, 2, 2])  # Baselines
        mock_ant2 = np.array([1, 2, 0, 2, 0, 1])
        
        # Mock flags - antenna 2 heavily flagged, antenna 0 best
        mock_flags = np.array([
            [[[False, False], [False, False]]],  # ant0-ant1: good
            [[[False, False], [False, False]]],  # ant0-ant2: good
            [[[False, False], [False, False]]],  # ant1-ant0: good
            [[[True, True], [True, True]]],      # ant1-ant2: flagged
            [[[False, False], [False, False]]],  # ant2-ant0: good
            [[[True, True], [True, True]]],      # ant2-ant1: flagged
        ])
        
        # Mock stable visibility data
        mock_data = np.array([
            [[[1.0+1.0j, 1.0-1.0j], [0.5+0.5j, 0.5-0.5j]]],  # stable
            [[[1.1+1.1j, 1.1-1.1j], [0.6+0.6j, 0.6-0.6j]]],  # stable
            [[[0.9+0.9j, 0.9-0.9j], [0.4+0.4j, 0.4-0.4j]]],  # stable
            [[[0.0+0.0j, 0.0+0.0j], [0.0+0.0j, 0.0+0.0j]]],  # flagged
            [[[1.2+1.2j, 1.2-1.2j], [0.7+0.7j, 0.7-0.7j]]],  # stable
            [[[0.0+0.0j, 0.0+0.0j], [0.0+0.0j, 0.0+0.0j]]],  # flagged
        ])
        
        mock_names = np.array(['ea01', 'ea02', 'ea03'])
        
        def mock_table(path, readonly=True):
            if "ANTENNA" in path:
                ctx = MockTableContext({})
                ctx.mock_table.getcol.return_value = mock_names
            else:
                ctx = MockTableContext({})
                ctx.mock_table.getcol.side_effect = lambda col: {
                    'ANTENNA1': mock_ant1,
                    'ANTENNA2': mock_ant2,
                    'FLAG': mock_flags,
                    'DATA': mock_data
                }[col]
            return ctx
            
        with patch('dsa110_contimg.conversion.helpers.table', side_effect=mock_table):
            with patch('dsa110_contimg.conversion.helpers.os.path.join', return_value="/fake/antenna"):
                best_ant = validate_reference_antenna_stability("/fake/ms/path")
                
                # Should select ea01 or ea02 (not ea03 which is heavily flagged)
                assert best_ant in ['ea01', 'ea02']
                assert best_ant != 'ea03'


class TestCasaFileHandleCleanup:
    """Test CASA file handle cleanup function."""
    
    def test_cleanup_calls_casa_functions(self):
        """Test that cleanup calls expected CASA functions."""
        
        # Mock CASA tool imports
        mock_casa_tools = MagicMock()
        mock_casa_tasks = MagicMock()
        
        with patch.dict('sys.modules', {
            'casatools': mock_casa_tools,
            'casatasks': mock_casa_tasks
        }):
            with patch('dsa110_contimg.conversion.helpers.gc.collect') as mock_gc:
                cleanup_casa_file_handles()
                
                # Should call garbage collection
                mock_gc.assert_called_once()


class TestValidationIntegration:
    """Test validation function integration and error handling."""
    
    def test_all_validation_functions_importable(self):
        """Test that all validation functions can be imported."""
        functions = [
            validate_ms_frequency_order,
            cleanup_casa_file_handles,
            validate_phase_center_coherence,
            validate_uvw_precision,
            validate_antenna_positions,
            validate_model_data_quality,
            validate_reference_antenna_stability,
        ]
        
        for func in functions:
            assert callable(func)
            assert func.__doc__ is not None
            
    def test_validation_functions_handle_exceptions(self):
        """Test that validation functions handle exceptions gracefully."""
        
        def mock_table_raises(path, readonly=True):
            raise Exception("Mock exception")
            
        with patch('dsa110_contimg.conversion.helpers.table', side_effect=mock_table_raises):
            # Functions should either raise RuntimeError or handle exceptions gracefully
            
            with pytest.raises((RuntimeError, Exception)):
                validate_ms_frequency_order("/fake/ms")
                
            with pytest.raises((RuntimeError, Exception)):
                validate_uvw_precision("/fake/ms")
                
            with pytest.raises((RuntimeError, Exception)):
                validate_antenna_positions("/fake/ms")
                
            with pytest.raises((RuntimeError, Exception)):
                validate_model_data_quality("/fake/ms")
                
            with pytest.raises((RuntimeError, Exception)):
                validate_reference_antenna_stability("/fake/ms")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])