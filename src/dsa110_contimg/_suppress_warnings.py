"""
Suppress known warnings from dependencies.
This module should be imported FIRST in any entry point.
"""

import warnings

# Suppress CASA's pkg_resources deprecation warning
# This is a CASA internal issue - they use deprecated setuptools APIs
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API",
    category=UserWarning,
    module="casaconfig.private.measures_update",
)

# Also catch it at the import statement level
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API",
    category=UserWarning,
)
