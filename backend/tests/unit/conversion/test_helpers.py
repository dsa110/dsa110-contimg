from unittest.mock import MagicMock, patch
import pytest
import numpy as np


def test_phase_to_meridian(monkeypatch):
    """Test phase_to_meridian sets time-dependent phase centers.
    
    This test verifies that phase_to_meridian:
    1. Processes unique times in the observation
    2. Creates phase centers for each time
    3. Updates phase_center_id_array
    
    The function is complex and calls pyuvdata internals, so we patch
    the heavy compute_and_set_uvw to avoid needing real antenna positions.
    """
    # Mock pandas before any imports that might need it
    import sys
    sys.modules['pandas'] = MagicMock()
    
    # Now import the module
    from dsa110_contimg.conversion import helpers_coordinates
    
    # Patch dependencies where they're used (in helpers_coordinates module)
    # These must return None (side effects only) to avoid mock issues
    with patch.object(helpers_coordinates, "set_antenna_positions", return_value=None):
        with patch.object(helpers_coordinates, "_ensure_antenna_diameters", return_value=None):
            with patch.object(helpers_coordinates, "compute_and_set_uvw", return_value=None):
                
                # Mock the UVData object with required attributes
                mock_uvdata = MagicMock()
                mock_uvdata.time_array = np.array([2460000.5, 2460000.6])  # Two unique times
                mock_uvdata.extra_keywords = {}
                mock_uvdata.phase_center_catalog = {}
                mock_uvdata._add_phase_center = MagicMock(side_effect=[0, 1])  # Return sequential IDs
                mock_uvdata.phase_center_id_array = None
                mock_uvdata.Nblts = 2
                
                # Call the function
                helpers_coordinates.phase_to_meridian(mock_uvdata)

                # Assert that phase centers were added for each unique time
                assert mock_uvdata._add_phase_center.call_count == 2
                
                # Verify phase_center_id_array was set
                assert mock_uvdata.phase_center_id_array is not None
                
                # Verify phase metadata was updated
                assert mock_uvdata.phase_type == "phased"
                assert mock_uvdata.phase_center_frame == "icrs"
