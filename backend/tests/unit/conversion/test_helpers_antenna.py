"""
Unit tests for conversion/helpers_antenna.py

Tests antenna position setting and validation functions.

These tests use mocks to avoid dependencies on actual CASA/station coordinate files.
Functions are imported through the helpers module to avoid potential circular imports.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from types import ModuleType, SimpleNamespace
import sys

from tests.fixtures import (
    MockUVData,
    create_mock_uvdata,
    mock_antenna_positions,
)


class TestSetAntennaPositions:
    """Tests for set_antenna_positions function."""
    
    def test_sets_itrf_positions(self):
        """Should set antenna positions from DSA-110 station coordinates."""
        # Create mock UVData
        mock_uvdata = create_mock_uvdata(nants=63)
        
        # Store original positions
        original_positions = mock_uvdata.antenna_positions.copy()
        
        # Patch the get_itrf function in helpers_antenna module
        with patch("dsa110_contimg.conversion.helpers_antenna.get_itrf") as mock_get_itrf:
            # Mock the station coordinates
            mock_df = MagicMock()
            mock_df.__getitem__ = MagicMock(side_effect=lambda key: {
                "x_m": np.arange(63) * 10.0 - 2409150.0,
                "y_m": np.arange(63) * 10.0 - 4478573.0,
                "z_m": np.arange(63) * 10.0 + 3838617.0,
            }[key])
            mock_get_itrf.return_value = mock_df
            
            from dsa110_contimg.conversion.helpers_antenna import set_antenna_positions
            
            # Call should update positions
            set_antenna_positions(mock_uvdata)
            
            # Verify get_itrf was called
            mock_get_itrf.assert_called_once()
    
    def test_handles_missing_antennas(self):
        """Should handle case where UVData has fewer antennas than station file."""
        mock_uvdata = create_mock_uvdata(nants=10)  # Fewer antennas
        
        with patch("dsa110_contimg.conversion.helpers_antenna.get_itrf") as mock_get_itrf:
            mock_df = MagicMock()
            # Return more antennas than UVData has
            mock_df.__getitem__ = MagicMock(side_effect=lambda key: {
                "x_m": np.arange(63) * 10.0,
                "y_m": np.arange(63) * 10.0,
                "z_m": np.arange(63) * 10.0,
            }[key])
            mock_df.__len__ = MagicMock(return_value=63)
            mock_get_itrf.return_value = mock_df
            
            from dsa110_contimg.conversion.helpers_antenna import set_antenna_positions
            
            # Should not raise
            set_antenna_positions(mock_uvdata)


class TestEnsureAntennaDiameters:
    """Tests for _ensure_antenna_diameters function."""
    
    def test_sets_default_diameter(self):
        """Should set antenna diameters to DSA-110 value (4.65m)."""
        mock_uvdata = MagicMock()
        mock_uvdata.Nants_telescope = 63
        mock_uvdata.antenna_diameters = None
        
        from dsa110_contimg.conversion.helpers_antenna import _ensure_antenna_diameters
        
        _ensure_antenna_diameters(mock_uvdata)
        
        # Check diameters were set
        assert mock_uvdata.antenna_diameters is not None
        assert len(mock_uvdata.antenna_diameters) == 63
        assert all(d == 4.65 for d in mock_uvdata.antenna_diameters)
    
    def test_preserves_existing_diameters(self):
        """Should not modify if diameters already set."""
        mock_uvdata = MagicMock()
        mock_uvdata.Nants_telescope = 63
        existing_diameters = np.full(63, 5.0)  # Custom diameter
        mock_uvdata.antenna_diameters = existing_diameters
        
        from dsa110_contimg.conversion.helpers_antenna import _ensure_antenna_diameters
        
        _ensure_antenna_diameters(mock_uvdata)
        
        # Should be unchanged
        np.testing.assert_array_equal(mock_uvdata.antenna_diameters, existing_diameters)
    
    def test_fixes_wrong_length(self):
        """Should fix antenna_diameters if wrong length."""
        mock_uvdata = MagicMock()
        mock_uvdata.Nants_telescope = 63
        mock_uvdata.antenna_diameters = np.array([4.65, 4.65])  # Wrong length
        
        from dsa110_contimg.conversion.helpers_antenna import _ensure_antenna_diameters
        
        _ensure_antenna_diameters(mock_uvdata)
        
        # Should be corrected
        assert len(mock_uvdata.antenna_diameters) == 63


class TestAntennaPositionHelpers:
    """Tests for antenna position helper utilities."""
    
    def test_mock_antenna_positions_shape(self):
        """mock_antenna_positions should return correct shape."""
        positions = mock_antenna_positions(nants=63)
        
        assert positions.shape == (63, 3)
    
    def test_mock_antenna_positions_near_ovro(self):
        """Mock positions should be near OVRO coordinates."""
        positions = mock_antenna_positions(nants=63)
        
        # OVRO approximate ITRF coordinates
        ovro_x = -2409150.402
        ovro_y = -4478573.118
        ovro_z = 3838617.339
        
        # All antennas should be within ~2km of OVRO
        for pos in positions:
            dist = np.sqrt(
                (pos[0] - ovro_x)**2 + 
                (pos[1] - ovro_y)**2 + 
                (pos[2] - ovro_z)**2
            )
            assert dist < 2000, f"Antenna position too far from OVRO: {dist}m"
    
    def test_mock_positions_reproducible(self):
        """Mock positions should be reproducible (seeded)."""
        pos1 = mock_antenna_positions(nants=10)
        pos2 = mock_antenna_positions(nants=10)
        
        np.testing.assert_array_almost_equal(pos1, pos2)
