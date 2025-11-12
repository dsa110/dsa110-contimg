"""Optimized conftest for mosaic tests - mocks CASA imports early."""

import sys
from unittest.mock import MagicMock, Mock

# Mock CASA modules BEFORE any imports to speed up tests
sys.modules["casatasks"] = MagicMock()
sys.modules["casatools"] = MagicMock()
sys.modules["casacore"] = MagicMock()
sys.modules["casacore.images"] = MagicMock()
sys.modules["casacore.images.image"] = MagicMock()

# Create mock classes
MockCASAImage = MagicMock
MockLinearmosaic = MagicMock

# Patch common CASA functions
if "casatasks" in sys.modules:
    sys.modules["casatasks"].importfits = MagicMock()
    sys.modules["casatasks"].exportfits = MagicMock()
    sys.modules["casatasks"].imregrid = MagicMock()
    sys.modules["casatasks"].immath = MagicMock()

if "casatools" in sys.modules:
    sys.modules["casatools"].linearmosaic = MagicMock(return_value=MagicMock())
