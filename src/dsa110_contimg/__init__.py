# DSA110 Pipeline Package

# CRITICAL: Enforce casa6 Python version on package import
# This ensures NO other Python version can be used
import sys
from pathlib import Path

# Only check if not already checked (avoid recursion)
if not hasattr(sys, "_dsa110_python_checked"):
    try:
        from dsa110_contimg.utils.python_version_guard import enforce_casa6_python

        enforce_casa6_python()
        sys._dsa110_python_checked = True
    except ImportError:
        # If guard module doesn't exist yet, do basic check
        required_version = (3, 11, 13)
        required_path = "/opt/miniforge/envs/casa6/bin/python"
        if sys.version_info[:3] != required_version or not sys.executable.startswith(
            "/opt/miniforge/envs/casa6"
        ):
            print(
                f"\n{'='*80}\n"
                f"CRITICAL ERROR: Wrong Python Version\n"
                f"{'='*80}\n"
                f"Required: Python 3.11.13 (casa6) at {required_path}\n"
                f"Detected: Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} at {sys.executable}\n"
                f"\nThis pipeline REQUIRES casa6 Python 3.11.13.\n"
                f"Source: source /data/dsa110-contimg/scripts/dev/developer-setup.sh\n"
                f"{'='*80}\n",
                file=sys.stderr,
            )
            sys.exit(1)
        sys._dsa110_python_checked = True
