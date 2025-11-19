from dsa110_contimg.utils.runtime_safeguards import check_casa6_python


def enforce_casa6_python():
    """Enforce that the code is running in the casa6 environment."""
    if not check_casa6_python():
        import sys
        import warnings

        warnings.warn(
            f"Not running in casa6 Python environment. Current: {sys.executable}. "
            f"Some functionality may not work correctly.",
            RuntimeWarning,
        )


# Run check on import
enforce_casa6_python()
