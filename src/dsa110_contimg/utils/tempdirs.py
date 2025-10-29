"""
Temporary directory helpers for CASA/casacore workflows.

Goals:
- Ensure casacore TempLattice* files and other scratch artifacts are written
  under a fast scratch path (e.g., /scratch/dsa110-contimg), not the repo.
- Optionally change the working directory to the intended output directory so
  libraries that default to CWD for temp files do not pollute the repo.

Usage:
    from dsa110_contimg.utils.tempdirs import prepare_temp_environment
    prepare_temp_environment(preferred_root='/scratch/dsa110-contimg', cwd_to=out_dir)

This sets common temp environment variables (TMPDIR, TMP, TEMP, CASA_TMPDIR)
and creates the directories if needed. It also changes CWD to `cwd_to` when
provided.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def derive_default_scratch_root() -> Path:
    """Return the preferred scratch root for temporary files.

    Order of precedence:
    - ENV CONTIMG_SCRATCH_DIR (if set)
    - /scratch/dsa110-contimg
    - /tmp (last resort)
    """
    env = os.getenv("CONTIMG_SCRATCH_DIR")
    if env:
        return Path(env)
    # Prefer project scratch, fall back to /tmp if not writable
    p = Path("/scratch/dsa110-contimg")
    try:
        p.mkdir(parents=True, exist_ok=True)
        return p
    except Exception:
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
    except Exception:
        # Best effort: fall back to /tmp
        tmp = Path("/tmp")
        tmp.mkdir(parents=True, exist_ok=True)

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
        except Exception:
            # If chdir fails, continue; env vars will still help
            pass

    return tmp


__all__ = ["prepare_temp_environment", "derive_default_scratch_root"]

