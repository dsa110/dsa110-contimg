"""
CASA initialization utilities.

Sets up CASA environment variables before importing CASA modules to avoid warnings.
This should be imported before any CASA imports.

CRITICAL: This module also redirects CASA log file creation. CASA writes log files
to the current working directory when any CASA module is first imported. We change
CWD to the dedicated logs directory BEFORE any CASA imports happen.
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
    "ignore",
    category=DeprecationWarning,
    message=r".*builtin type (SwigPyPacked|SwigPyObject|swigvarlink) has no __module__ attribute.*",
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


# =============================================================================
# CASA Log Directory Setup (MUST happen before any CASA imports)
# =============================================================================


def _setup_casa_log_directory_early() -> Path:
    """Set up CASA log file directory BEFORE any CASA imports.

    CASA writes log files (casa-YYYYMMDD-HHMMSS.log) to the current working
    directory when any CASA module is first imported. This function changes
    CWD to the dedicated logs directory so any log files end up there.

    This is an internal function called at module import time.
    """
    # Default path - avoid importing settings to prevent circular imports
    log_dir = Path("/data/dsa110-contimg/state/logs/casa")

    try:
        log_dir.mkdir(parents=True, exist_ok=True)

        # Set CASALOGFILE - some CASA versions may respect this
        os.environ["CASALOGFILE"] = str(log_dir / "casa.log")

        # Change CWD to logs directory so CASA writes logs there
        # This is the most reliable way to redirect CASA logs
        os.chdir(log_dir)

        return log_dir
    except (OSError, PermissionError):
        # If we can't create/access the directory, logs will go to CWD
        return Path.cwd()


# CRITICAL: Set up log directory IMMEDIATELY before any CASA imports can happen
_casa_log_dir_early = _setup_casa_log_directory_early()


# =============================================================================
# CASA Path Setup
# =============================================================================


def ensure_casa_path() -> None:
    """
    Set CASAPATH environment variable and ensure casacore can find data tables.

    CASA looks for data tables (Observatories, etc.) in CASAPATH/data/geodetic/.
    However, casacore (the Python bindings) also looks in:
    $PYTHON_PREFIX/lib/python3.X/site-packages/casacore/data/geodetic/

    This function:
    1. Sets CASAPATH to point to the CASA data directory
    2. Creates symlinks so casacore can find the data tables
    3. Ensures HOME is set correctly to prevent CASA from using /root/.casa/data

    This prevents warnings about missing Observatories table and measurespath ownership.
    """
    # CRITICAL: Ensure HOME is set correctly to prevent CASA from using /root/.casa/data
    # CASA uses $HOME/.casa/data as the default measurespath for writable measures data
    if "HOME" not in os.environ or os.environ.get("HOME") == "/root":
        # Get actual user home directory
        import pwd

        try:
            user_home = pwd.getpwuid(os.getuid()).pw_dir
            os.environ["HOME"] = user_home
        except (KeyError, ImportError):
            # Fallback to expanduser if pwd module unavailable
            user_home = os.path.expanduser("~")
            if user_home and user_home != "/root":
                os.environ["HOME"] = user_home

    # Ensure user's .casa directory exists and is writable
    user_casa_dir = os.path.join(os.environ.get("HOME", os.path.expanduser("~")), ".casa")
    user_casa_data_dir = os.path.join(user_casa_dir, "data")
    try:
        os.makedirs(user_casa_data_dir, exist_ok=True)
    except (OSError, PermissionError):
        # Non-critical - CASA will use read-only measures data from CASAPATH
        pass

    # Set CASAPATH if not already set
    if "CASAPATH" not in os.environ:
        # Try common CASA installation paths
        possible_paths = [
            "/opt/miniforge/envs/casa6/share/casa",
            "/opt/casa/share/casa",
            os.path.expanduser("~/.casa"),
        ]

        for casa_path in possible_paths:
            if os.path.exists(casa_path):
                # Verify geodetic data exists
                geodetic_path = os.path.join(casa_path, "data", "geodetic")
                if os.path.exists(geodetic_path):
                    os.environ["CASAPATH"] = casa_path
                    break

    # Ensure casacore can find the data tables
    # casacore looks in site-packages/casacore/data/ even though CASAPATH is set
    casa_path = os.environ.get("CASAPATH")
    if casa_path:
        geodetic_src = os.path.join(casa_path, "data", "geodetic")
        ephemerides_src = os.path.join(casa_path, "data", "ephemerides")

        # Find where casacore is installed (must be in casa6 environment)
        try:
            import casacore

            casacore_path = os.path.dirname(casacore.__file__)
            # casacore_path is like: /opt/miniforge/envs/casa6/lib/python3.11/site-packages/casacore
            # casacore_data_dir should be: /opt/miniforge/envs/casa6/lib/python3.11/site-packages/casacore/data
            casacore_data_dir = os.path.join(casacore_path, "data")

            # Only proceed if we're in casa6 environment (not system Python)
            # Check that casacore_path contains 'casa6' or 'miniforge' to ensure we're not in system Python
            if "casa6" in casacore_path or "miniforge" in casacore_path:
                # Create data directory if it doesn't exist
                os.makedirs(casacore_data_dir, exist_ok=True)

                # Create symlinks for geodetic and ephemerides data
                geodetic_dest = os.path.join(casacore_data_dir, "geodetic")
                ephemerides_dest = os.path.join(casacore_data_dir, "ephemerides")

                if os.path.exists(geodetic_src) and not os.path.exists(geodetic_dest):
                    try:
                        os.symlink(geodetic_src, geodetic_dest)
                    except (OSError, PermissionError):
                        # Symlink creation failed (might not have permissions or already exists)
                        # This is non-critical - CASAPATH should be sufficient
                        pass

                if os.path.exists(ephemerides_src) and not os.path.exists(ephemerides_dest):
                    try:
                        os.symlink(ephemerides_src, ephemerides_dest)
                    except (OSError, PermissionError):
                        # Symlink creation failed
                        # This is non-critical - CASAPATH should be sufficient
                        pass
            else:
                # We're in system Python - don't try to modify system paths
                # Just ensure CASAPATH is set and let casacore use it
                pass
        except (ImportError, AttributeError):
            # casacore not available or path detection failed
            pass


def setup_casa_log_directory() -> Path:
    """Set up CASA log file directory (public API).

    CASA writes log files (casa-YYYYMMDD-HHMMSS.log) to the current working
    directory when any CASA module is first imported. This function:

    1. Creates the dedicated CASA logs directory if it doesn't exist
    2. Sets CASALOGFILE environment variable (some CASA versions respect this)
    3. Changes CWD to the logs directory so any log files end up there

    Returns the logs directory path. The caller is responsible for restoring
    CWD if needed (though for log redirection, we typically don't restore).

    Note: This is called automatically at module import time via
    _setup_casa_log_directory_early(). This public function is provided
    for cases where you need to re-run the setup or get the log directory path.
    """
    # Use centralized settings if available, otherwise use default path
    try:
        from dsa110_contimg.config import settings

        log_dir = settings.paths.casa_logs_dir
    except ImportError:
        log_dir = Path("/data/dsa110-contimg/state/logs/casa")

    try:
        log_dir.mkdir(parents=True, exist_ok=True)

        # Set CASALOGFILE - some CASA versions may respect this
        os.environ["CASALOGFILE"] = str(log_dir / "casa.log")

        # Change CWD to logs directory so CASA writes logs there
        # This is the most reliable way to redirect CASA logs
        os.chdir(log_dir)

        return log_dir
    except (OSError, PermissionError):
        # If we can't create/access the directory, logs will go to CWD
        return Path.cwd()


def cleanup_stray_casa_logs(
    search_dirs: list = None,
    target_dir: Path = None,
    delete: bool = False,
) -> list:
    """Find and optionally move/delete stray CASA log files.

    Args:
        search_dirs: Directories to search for stray logs (default: backend root)
        target_dir: Directory to move logs to (default: CASA logs dir)
        delete: If True, delete logs instead of moving

    Returns:
        List of paths found/processed
    """
    import shutil

    if target_dir is None:
        try:
            from dsa110_contimg.config import settings

            target_dir = settings.paths.casa_logs_dir
        except ImportError:
            target_dir = Path("/data/dsa110-contimg/state/logs/casa")

    if search_dirs is None:
        search_dirs = [
            Path("/data/dsa110-contimg/backend"),
        ]

    found_logs = []
    for search_dir in search_dirs:
        search_dir = Path(search_dir)
        if not search_dir.exists():
            continue

        # Find casa-*.log files
        for log_path in search_dir.glob("casa-*.log"):
            # Skip if already in target directory
            if log_path.parent == target_dir:
                continue

            found_logs.append(log_path)

            if delete:
                try:
                    log_path.unlink()
                except (OSError, PermissionError):
                    pass
            elif target_dir:
                try:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(log_path), str(target_dir / log_path.name))
                except (OSError, PermissionError, shutil.Error):
                    pass

    return found_logs


# Initialize CASA path setup (log directory was already set up at the top of the file)
ensure_casa_path()
