"""Unit test configuration and fixtures.

This module patches expensive imports before any test modules are loaded.
The key is using sys.modules to pre-install mocks BEFORE imports happen.
"""

import sys
from unittest.mock import MagicMock

# =============================================================================
# PRE-IMPORT MOCKING: Install mocks into sys.modules BEFORE any imports happen
# =============================================================================
# This is critical - patch() won't work because the module is imported
# before the patch is applied. Instead, we pre-populate sys.modules.

def _install_mock_if_missing(module_path: str) -> MagicMock:
    """Install a MagicMock into sys.modules if not already present."""
    if module_path not in sys.modules:
        mock = MagicMock()
        sys.modules[module_path] = mock
        return mock
    return sys.modules[module_path]

# Mock heavy calibrator imports (CASA dependencies)
_install_mock_if_missing("dsa110_contimg.conversion.calibrator_ms_service")

# Mock photometry manager (heavy dependencies)
_install_mock_if_missing("dsa110_contimg.photometry.manager")

# Mock streaming mosaic (CASA dependencies)
_install_mock_if_missing("dsa110_contimg.mosaic.streaming_mosaic")

# Mock error handling (may have disk I/O)
mock_error = _install_mock_if_missing("dsa110_contimg.mosaic.error_handling")
mock_error.check_disk_space = MagicMock(return_value=(True, "OK"))

# Mock time utils
mock_time = _install_mock_if_missing("dsa110_contimg.utils.time_utils")
mock_time.extract_ms_time_range = MagicMock(return_value=(0.0, 1.0))

# Mock HDF5 index
mock_hdf5 = _install_mock_if_missing("dsa110_contimg.database.hdf5_index")
mock_hdf5.query_subband_groups = MagicMock(return_value=[])

