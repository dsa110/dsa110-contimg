"""
CASA initialization utilities.

Sets up CASA environment variables before importing CASA modules to avoid warnings.
This should be imported before any CASA imports.
"""
import os
import warnings
from pathlib import Path

# Suppress SWIG-generated deprecation warnings from casacore
# These warnings come from SWIG bindings missing __module__ attributes
# Fixed in SWIG 4.4+ but not yet widely released
# See: https://github.com/swig/swig/issues/2881
# Note: Warnings emitted during import time (<frozen importlib._bootstrap>) may
# still appear. For complete suppression, use command-line flag:
# python -W ignore::DeprecationWarning script.py
warnings.filterwarnings(
    'ignore',
    category=DeprecationWarning,
    message=r'.*builtin type (SwigPyPacked|SwigPyObject|swigvarlink) has no __module__ attribute.*'
)

# Note: FITS card format INFO messages from casacore C++ code cannot be suppressed
# via Python logging. These messages appear when FITS card values exceed FITS fixed
# format display precision (e.g., CDELT1 = -0.000555555555555556 exceeds 20 chars).
# The values are read correctly despite the warning. These are harmless INFO messages
# from casacore's C++ FITS reader and can be safely ignored.
#
# Note: imregrid WARN messages from CASA C++ code also cannot be suppressed:
# - "_doImagesOverlap" warning: Expected for large images (>1 deg), overlap checking skipped
# - "regrid" warning: Expected for undersampled beams, potential flux loss during regridding
# These are informational warnings about data characteristics, not code errors.


def ensure_casa_path() -> None:
    """
    Set CASAPATH environment variable and ensure casacore can find data tables.

    CASA looks for data tables (Observatories, etc.) in CASAPATH/data/geodetic/.
    However, casacore (the Python bindings) also looks in:
    $PYTHON_PREFIX/lib/python3.X/site-packages/casacore/data/geodetic/

    This function:
    1. Sets CASAPATH to point to the CASA data directory
    2. Creates symlinks so casacore can find the data tables

    This prevents warnings about missing Observatories table.
    """
    # Set CASAPATH if not already set
    if 'CASAPATH' not in os.environ:
        # Try common CASA installation paths
        possible_paths = [
            '/opt/miniforge/envs/casa6/share/casa',
            '/opt/casa/share/casa',
            os.path.expanduser('~/.casa'),
        ]

        for casa_path in possible_paths:
            if os.path.exists(casa_path):
                # Verify geodetic data exists
                geodetic_path = os.path.join(casa_path, 'data', 'geodetic')
                if os.path.exists(geodetic_path):
                    os.environ['CASAPATH'] = casa_path
                    break

    # Ensure casacore can find the data tables
    # casacore looks in site-packages/casacore/data/ even though CASAPATH is set
    casa_path = os.environ.get('CASAPATH')
    if casa_path:
        geodetic_src = os.path.join(casa_path, 'data', 'geodetic')
        ephemerides_src = os.path.join(casa_path, 'data', 'ephemerides')

        # Find where casacore is installed
        try:
            import casacore
            casacore_path = os.path.dirname(casacore.__file__)
            casacore_data_dir = os.path.join(
                os.path.dirname(casacore_path), 'casacore', 'data')

            # Create data directory if it doesn't exist
            os.makedirs(casacore_data_dir, exist_ok=True)

            # Create symlinks for geodetic and ephemerides data
            geodetic_dest = os.path.join(casacore_data_dir, 'geodetic')
            ephemerides_dest = os.path.join(casacore_data_dir, 'ephemerides')

            if os.path.exists(geodetic_src) and not os.path.exists(geodetic_dest):
                try:
                    os.symlink(geodetic_src, geodetic_dest)
                except (OSError, PermissionError):
                    # Symlink creation failed (might not have permissions or already exists)
                    pass

            if os.path.exists(ephemerides_src) and not os.path.exists(ephemerides_dest):
                try:
                    os.symlink(ephemerides_src, ephemerides_dest)
                except (OSError, PermissionError):
                    # Symlink creation failed
                    pass
        except (ImportError, AttributeError):
            # casacore not available or path detection failed
            pass


# Auto-initialize when module is imported
ensure_casa_path()
