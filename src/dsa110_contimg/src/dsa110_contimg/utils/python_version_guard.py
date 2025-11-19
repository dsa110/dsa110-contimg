"""Python version guard - ensures only casa6 Python 3.11.13 is used.

This module MUST be imported at the top of all pipeline entry points
to prevent execution with incorrect Python versions.
"""

import sys
from pathlib import Path

# Required Python version for casa6
REQUIRED_VERSION = (3, 11, 13)
REQUIRED_VERSION_STR = "3.11.13"
REQUIRED_PYTHON_PATH = "/opt/miniforge/envs/casa6/bin/python"

# Casa6 environment paths (accept both miniforge for local dev and conda for Docker)
CASA6_ENV_PATHS = [
    "/opt/miniforge/envs/casa6",  # Local development (miniforge)
    "/opt/conda/envs/casa6",  # Docker container (micromamba)
]


def check_python_version():
    """Check that we're running with casa6 Python 3.11.13.

    Raises:
        SystemExit: If Python version or path is incorrect.
    """
    # Check Python version
    if sys.version_info[:3] != REQUIRED_VERSION:
        error_msg = (
            f"\n{'=' * 80}\n"
            f"CRITICAL ERROR: Wrong Python Version\n"
            f"{'=' * 80}\n"
            f"Required: Python {REQUIRED_VERSION_STR} (casa6)\n"
            f"Detected: Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}\n"
            f"Executable: {sys.executable}\n"
            f"\n"
            f"This pipeline REQUIRES casa6 Python 3.11.13.\n"
            f"\n"
            f"To fix:\n"
            f"  1. Source developer setup: source /data/dsa110-contimg/scripts/dev/developer-setup.sh\n"
            f"  2. Or activate casa6: conda activate casa6\n"
            f"  3. Verify: which python3 should show {REQUIRED_PYTHON_PATH}\n"
            f"\n"
            f"{'=' * 80}\n"
        )
        print(error_msg, file=sys.stderr)
        sys.exit(1)

    # Check Python executable path (accept both miniforge and conda paths)
    if not any(sys.executable.startswith(path) for path in CASA6_ENV_PATHS):
        error_msg = (
            f"\n{'=' * 80}\n"
            f"CRITICAL ERROR: Wrong Python Executable\n"
            f"{'=' * 80}\n"
            f"Required: Python from casa6 environment\n"
            f"Expected path: {REQUIRED_PYTHON_PATH}\n"
            f"Detected path: {sys.executable}\n"
            f"\n"
            f"This pipeline REQUIRES casa6 Python 3.11.13.\n"
            f"\n"
            f"To fix:\n"
            f"  1. Source developer setup: source /data/dsa110-contimg/scripts/dev/developer-setup.sh\n"
            f"  2. Or activate casa6: conda activate casa6\n"
            f"  3. Verify: which python3 should show {REQUIRED_PYTHON_PATH}\n"
            f"\n"
            f"{'=' * 80}\n"
        )
        print(error_msg, file=sys.stderr)
        sys.exit(1)

    # Verify casa6 environment exists (check all possible paths)
    casa6_python_found = False
    for env_path in CASA6_ENV_PATHS:
        casa6_python = Path(env_path) / "bin" / "python"
        if casa6_python.exists():
            casa6_python_found = True
            break

    if not casa6_python_found:
        error_msg = (
            f"\n{'=' * 80}\n"
            f"CRITICAL ERROR: Casa6 Environment Not Found\n"
            f"{'=' * 80}\n"
            f"Required: casa6 conda environment at one of: {', '.join(CASA6_ENV_PATHS)}\n"
            f"Detected: Environment not found\n"
            f"\n"
            f"This pipeline REQUIRES casa6 Python 3.11.13.\n"
            f"Please ensure casa6 conda environment is installed.\n"
            f"\n"
            f"{'=' * 80}\n"
        )
        print(error_msg, file=sys.stderr)
        sys.exit(1)


def enforce_casa6_python():
    """Enforce casa6 Python - call this at module import time.

    This function should be called immediately after import in critical modules.
    """
    check_python_version()


# Auto-check on import (can be disabled if needed for testing)
# Set DSA110_SKIP_PYTHON_CHECK=1 to disable
if not (Path(__file__).parent.parent.parent.parent / ".skip_python_check").exists():
    import os

    if os.environ.get("DSA110_SKIP_PYTHON_CHECK") != "1":
        check_python_version()
