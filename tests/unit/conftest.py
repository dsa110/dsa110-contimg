"""Unit test configuration and fixtures.

This module patches expensive imports before any test modules are loaded.
"""

import sys
from types import ModuleType
from unittest.mock import MagicMock


class MockModule(ModuleType):
    """A mock module that can be imported."""
    
    def __init__(self, name):
        super().__init__(name)
        self.__spec__ = MagicMock()
        self.__spec__.name = name
        self.__file__ = f"<mock {name}>"
        self.__path__ = []
    
    def __getattr__(self, name):
        # Return a MagicMock for any attribute access
        return MagicMock()


# Mock CASA modules before any imports
sys.modules['casacore'] = MockModule('casacore')
sys.modules['casacore.tables'] = MockModule('casacore.tables')
sys.modules['casatasks'] = MockModule('casatasks')
sys.modules['casatools'] = MockModule('casatools')

# Mock matplotlib to avoid heavy display dependencies
sys.modules['matplotlib'] = MockModule('matplotlib')
sys.modules['matplotlib.pyplot'] = MockModule('matplotlib.pyplot')
sys.modules['matplotlib.colors'] = MockModule('matplotlib.colors')
sys.modules['matplotlib.patches'] = MockModule('matplotlib.patches')

# Mock other heavy/optional dependencies
sys.modules['uncertainties'] = MockModule('uncertainties')
sys.modules['uncertainties.core'] = MockModule('uncertainties.core')
sys.modules['pyuvdata'] = MockModule('pyuvdata')
sys.modules['pyuvdata.utils'] = MockModule('pyuvdata.utils')
sys.modules['structlog'] = MockModule('structlog')
sys.modules['numba'] = MockModule('numba')

# Note: The original patch for CalibratorMSGenerator cannot work until
# the conversion module can be imported without CASA dependencies.
# The import error is resolved by mocking casacore modules above.
