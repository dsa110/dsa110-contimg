#!/opt/miniforge/envs/casa6/bin/python
"""
Python version guard - ensures scripts never use Python 2.7 or 3.6.

Add this to the top of Python scripts after the shebang:
    import sys
    if sys.version_info < (3, 11):
        sys.exit("ERROR: Python 3.11+ required. Found: {}".format(sys.version))
"""

# Python 2.7 compatibility check (must be before any Python 3-only syntax)
import sys

if sys.version_info[0] < 3:
    sys.stderr.write("ERROR: Python 2.7 is forbidden in dsa110-contimg.\n")
    sys.stderr.write("Current version: {}\n".format(sys.version))
    sys.stderr.write("Required: Python 3.11+\n")
    sys.stderr.write("Use: /opt/miniforge/envs/casa6/bin/python\n")
    sys.exit(1)

import os

# Minimum required Python version
MIN_VERSION = (3, 11)
FORBIDDEN_VERSIONS = [
    (2, 7),
    (3, 6),
]


def check_python_version():
    """Check if current Python version is acceptable."""
    version = sys.version_info[:2]

    # Check for forbidden versions
    for forbidden in FORBIDDEN_VERSIONS:
        if version == forbidden:
            sys.stderr.write(
                "ERROR: Python {}.{} is forbidden in dsa110-contimg.\n".format(
                    forbidden[0], forbidden[1]
                )
            )
            sys.stderr.write("Current version: {}\n".format(sys.version))
            sys.stderr.write("Required: Python {}.{}+\n".format(MIN_VERSION[0], MIN_VERSION[1]))
            sys.stderr.write("Use: /opt/miniforge/envs/casa6/bin/python\n")
            sys.exit(1)

    # Check minimum version
    if version < MIN_VERSION:
        sys.stderr.write("ERROR: Python {}.{}+ required.\n".format(MIN_VERSION[0], MIN_VERSION[1]))
        sys.stderr.write("Current version: {}\n".format(sys.version))
        sys.stderr.write("Use: /opt/miniforge/envs/casa6/bin/python\n")
        sys.exit(1)

    # Check if we're using CASA6 Python (recommended)
    casa6_python = "/opt/miniforge/envs/casa6/bin/python"
    if sys.executable != casa6_python and os.path.exists(casa6_python):
        # This is a warning, not an error
        sys.stderr.write("WARNING: Not using CASA6 Python.\n")
        sys.stderr.write("Current: {}\n".format(sys.executable))
        sys.stderr.write("Recommended: {}\n".format(casa6_python))
        # Don't exit - just warn


if __name__ == "__main__":
    check_python_version()
    sys.stdout.write("OK: Python version OK: {}\n".format(sys.version))
