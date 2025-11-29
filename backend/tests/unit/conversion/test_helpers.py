from unittest.mock import MagicMock, patch
import pytest


def test_phase_to_meridian(monkeypatch):
    """Test phase_to_meridian calls the underlying UVData method."""
    # We patch set_antenna_positions to avoid it reading the antenna CSV
    # and comparing antenna counts with the mock
    with patch("dsa110_contimg.conversion.helpers_coordinates.set_antenna_positions"):
        with patch("dsa110_contimg.conversion.helpers_coordinates._ensure_antenna_diameters"):
            # Import here so patches are in effect
            from dsa110_contimg.conversion.helpers_coordinates import phase_to_meridian
            
            # Mock the UVData object with minimal required attributes
            mock_uvdata = MagicMock()
            mock_uvdata.time_array = [2460000.5]  # Single time
            mock_uvdata.extra_keywords = {}
            mock_uvdata.phase_center_catalog = {}
            mock_uvdata._add_phase_center = MagicMock(return_value=0)
            mock_uvdata.phase_center_id_array = None
            mock_uvdata.Nblts = 1
            
            # Call the function - should complete without error
            phase_to_meridian(mock_uvdata)

            # Assert that phase center was added
            mock_uvdata._add_phase_center.assert_called()