"""Unit test configuration and fixtures.

This module patches expensive imports before any test modules are loaded.
"""

from unittest.mock import patch

# Patch CalibratorMSGenerator before any test imports MosaicOrchestrator
# This avoids ~9.6s import overhead from heavy CASA/astropy dependencies
_calibrator_patcher = patch('dsa110_contimg.conversion.calibrator_ms_service.CalibratorMSGenerator')
_calibrator_patcher.start()

