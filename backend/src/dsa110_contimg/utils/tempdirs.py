"""
Temporary directory helpers for CASA/casacore workflows.

Goals:
- Ensure casacore TempLattice* files and other scratch artifacts are written
  under a fast scratch path (e.g., /stage/dsa110-contimg), not the repo.
- Optionally change the working directory to the intended output directory so
  libraries that default to CWD for temp files do not pollute the repo.
- Configure CASA to write log files to a centralized location.

Usage:
    from dsa110_contimg.utils.tempdirs import prepare_temp_environment
    prepare_temp_environment(preferred_root='/stage/dsa110-contimg', cwd_to=out_dir)

This sets common temp environment variables (TMPDIR, TMP, TEMP, CASA_TMPDIR)
and creates the directories if needed. It also changes CWD to `cwd_to` when
provided.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Optional


def derive_default_scratch_root() -> Path:
    """Return the preferred scratch root for temporary files.

    Order of precedence:
    - ENV CONTIMG_SCRATCH_DIR (if set)
    - /stage/dsa110-contimg
    - /tmp (last resort)
    """
    env = os.getenv("CONTIMG_SCRATCH_DIR")
    if env:
        return Path(env)
    # Prefer project scratch, fall back to /tmp if not writable
    p = Path("/stage/dsa110-contimg")
    try:
        p.mkdir(parents=True, exist_ok=True)
        return p
    except (OSError, IOError, PermissionError):
        # Fallback to /tmp if preferred directory cannot be created
        return Path("/tmp")


def prepare_temp_environment(
    preferred_root: Optional[str | os.PathLike[str]] = None,
    *,
    cwd_to: Optional[str | os.PathLike[str]] = None,
) -> Path:
    """Prepare temp dirs and environment variables for CASA/casacore.

    - Ensures a stable temp directory under `<root>/tmp`
    - Sets TMPDIR/TMP/TEMP and CASA_TMPDIR environment variables
    - Optionally changes the current working directory to `cwd_to`

    Returns the path to the temp directory used.
    """
    root = Path(preferred_root) if preferred_root else derive_default_scratch_root()
    tmp = root / "tmp"
    try:
        tmp.mkdir(parents=True, exist_ok=True)
    except (OSError, IOError, PermissionError):
        # Best effort: fall back to /tmp
        tmp = Path("/tmp")
        try:
            tmp.mkdir(parents=True, exist_ok=True)
        except (OSError, IOError, PermissionError):
            # Last resort - /tmp should always exist
            pass

    # Set common temp envs used by Python and (some) casacore paths
    os.environ.setdefault("TMPDIR", str(tmp))
    os.environ.setdefault("TMP", str(tmp))
    os.environ.setdefault("TEMP", str(tmp))
    # CASA-specific (best-effort; not all versions honor this)
    os.environ.setdefault("CASA_TMPDIR", str(tmp))

    if cwd_to is not None:
        outdir = Path(cwd_to)
        outdir.mkdir(parents=True, exist_ok=True)
        try:
            os.chdir(outdir)
        except (OSError, IOError, PermissionError):
            # If chdir fails, continue; env vars will still help
            pass

    return tmp


def derive_casa_log_dir() -> Path:
    """Return the directory where CASA log files should be written.

    Order of precedence:
    - ENV CONTIMG_STATE_DIR/logs (if CONTIMG_STATE_DIR is set)
    - /data/dsa110-contimg/state/logs
    - /tmp (last resort)
    """
    state_dir = os.getenv("CONTIMG_STATE_DIR") or os.getenv("PIPELINE_STATE_DIR")
    if state_dir:
        log_dir = Path(state_dir) / "logs"
    else:
        log_dir = Path("/data/dsa110-contimg/state/logs")

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir
    except (OSError, IOError, PermissionError):
        # Fallback to /tmp if we can't create the preferred directory
        return Path("/tmp")


@contextmanager
def casa_log_environment():
    """Context manager that sets up CASA logging environment.

    CASA writes log files (casa-YYYYMMDD-HHMMSS.log) to the current working
    directory. This context manager temporarily changes the working directory
    to the centralized logs directory while CASA tasks execute.

    Usage:
        with casa_log_environment():
            from casatasks import tclean
            tclean(...)
    """
    log_dir = derive_casa_log_dir()
    old_cwd = os.getcwd()
    try:
        os.chdir(log_dir)
        yield log_dir
    finally:
        os.chdir(old_cwd)


def setup_casa_logging() -> Path:
    """Set up CASA logging environment variables.

    This sets the CASALOGFILE environment variable and ensures the log
    directory exists. Note that CASA primarily uses the current working
    directory for log files, so this should be used in conjunction with
    changing CWD or using casa_log_environment() context manager.

    Returns the path to the log directory.
    """
    log_dir = derive_casa_log_dir()
    # Set CASALOGFILE - some CASA versions may respect this
    os.environ["CASALOGFILE"] = str(log_dir / "casa.log")
    return log_dir


__all__ = [
    "prepare_temp_environment",
    "derive_default_scratch_root",
    "derive_casa_log_dir",
    "casa_log_environment",
    "setup_casa_logging",
]
