from unittest.mock import MagicMock
import pytest
from dsa110_contimg.conversion.helpers_coordinates import phase_to_meridian

def test_phase_to_meridian(monkeypatch):
    # Mock the UVData object
    mock_uvdata = MagicMock()
    mock_uvdata.phase_to_meridian = MagicMock()

    # Call the function with the mocked UVData
    phase_to_meridian(mock_uvdata)

    # Assert that the phase_to_meridian method was called
    mock_uvdata.phase_to_meridian.assert_called_once()