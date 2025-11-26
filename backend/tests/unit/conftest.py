"""Unit test configuration and fixtures.

This module patches expensive imports before any test modules are loaded.
The key is using sys.modules to pre-install mocks BEFORE imports happen.

NOTE: Be careful not to mock modules that are being tested. Only mock
external heavy dependencies that aren't the subject of the tests.
"""

import sys
from unittest.mock import MagicMock

# =============================================================================
# PRE-IMPORT MOCKING: Install mocks into sys.modules BEFORE any imports happen
# =============================================================================
# This is critical - patch() won't work because the module is imported
# before the patch is applied. Instead, we pre-populate sys.modules.
#
# IMPORTANT: Only mock modules that are IMPORTED BY code under test, not
# modules that ARE the code under test. For example:
# - Mock calibrator_ms_service because orchestrator.py imports it
# - DON'T mock streaming_mosaic because test_streaming_mosaic_manager_unit.py tests it

def _install_mock_if_missing(module_path: str) -> MagicMock:
    """Install a MagicMock into sys.modules if not already present."""
    if module_path not in sys.modules:
        mock = MagicMock()
        sys.modules[module_path] = mock
        return mock
    return sys.modules[module_path]

# Mock heavy calibrator imports (CASA dependencies) - used by orchestrator.py
_install_mock_if_missing("dsa110_contimg.conversion.calibrator_ms_service")

# Mock photometry manager (heavy dependencies) - used by orchestrator.py
_install_mock_if_missing("dsa110_contimg.photometry.manager")

