"""
Suppress known deprecation warnings from CASA dependencies.
Import this at the top of scripts that use CASA.
"""

import warnings

# Suppress pkg_resources deprecation warning from casaconfig
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API",
    category=UserWarning,
    module="casaconfig.private.measures_update",
)
