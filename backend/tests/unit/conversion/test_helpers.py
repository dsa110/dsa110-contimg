from unittest.mock import MagicMock, patch
import pytest
import numpy as np
import sys
from types import ModuleType, SimpleNamespace


def test_phase_to_meridian(monkeypatch):
    """Test phase_to_meridian sets time-dependent phase centers.
    
    This test verifies that phase_to_meridian:
    1. Processes unique times in the observation
    2. Creates phase centers for each time
    3. Updates phase_center_id_array
    
    The function is complex and calls pyuvdata internals, so we patch
    the heavy compute_and_set_uvw to avoid needing real antenna positions.
    """
    # Save original pandas module to restore later
    original_pandas = sys.modules.get('pandas')
    
    # Mock pandas before any imports that might need it
    # Must create a proper module with __spec__ to satisfy astropy's importlib checks
    mock_pandas = ModuleType('pandas')
    mock_pandas.__spec__ = SimpleNamespace(
        name='pandas',
        origin='mock',
        loader=None,
        submodule_search_locations=None
    )
    mock_pandas.__version__ = '2.0.0'
    sys.modules['pandas'] = mock_pandas
    
    try:
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
    finally:
        # Restore original pandas module to prevent mock leaking to other tests
        if original_pandas is not None:
            sys.modules['pandas'] = original_pandas
        elif 'pandas' in sys.modules:
            del sys.modules['pandas']
