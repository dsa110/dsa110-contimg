"""
V2 conversion module for the DSA-110 continuum imaging pipeline.

This version uses a Strategy design pattern for creating Measurement Sets,
making the system more modular and extensible.
"""

# Lazy imports to avoid RuntimeWarning when running as module
# This prevents hdf5_orchestrator from being loaded into sys.modules
# before runpy tries to execute it as a script
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # For type checkers, provide direct imports
    from .hdf5_orchestrator import (
        _extract_subband_code,
        _load_and_merge_subbands,
        _parse_timestamp_from_filename,
        convert_subband_groups_to_ms,
        find_subband_groups,
    )

__all__ = [
    "convert_subband_groups_to_ms",
    "find_subband_groups",
    "_parse_timestamp_from_filename",
    "_extract_subband_code",
    "_load_and_merge_subbands",
    # Note: "hdf5_orchestrator" removed from __all__ to prevent RuntimeWarning
    # when running as module (python -m). Still accessible via lazy import.
]


def __getattr__(name: str):
    """Lazy import for hdf5_orchestrator functions and module.

    This lazy import prevents RuntimeWarning when running as module:
    python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator
    """
    import importlib
    import sys

    # Prevent circular import by checking module's __dict__ directly (not hasattr which triggers __getattr__)
    current_module = sys.modules.get(__name__)
    if current_module and "_importing" in current_module.__dict__:
        raise AttributeError(
            f"Circular import detected while accessing {name!r}. "
            f"Module {__name__!r} is already being imported."
        )

    if name == "hdf5_orchestrator":
        # Mark that we're importing to prevent recursion (directly in __dict__)
        if current_module:
            current_module.__dict__["_importing"] = True
        try:
            # Import directly using importlib to avoid triggering __getattr__ again
            hdf5_mod = importlib.import_module(".hdf5_orchestrator", package=__name__)
            return hdf5_mod
        finally:
            # Clear the importing flag (directly from __dict__)
            if current_module and "_importing" in current_module.__dict__:
                del current_module.__dict__["_importing"]
    elif name in __all__:
        # Import directly from hdf5_orchestrator without going through __getattr__ again
        hdf5_mod = importlib.import_module(".hdf5_orchestrator", package=__name__)

        # Create a mapping of names to functions
        _exports = {
            "convert_subband_groups_to_ms": hdf5_mod.convert_subband_groups_to_ms,
            "find_subband_groups": hdf5_mod.find_subband_groups,
            "_parse_timestamp_from_filename": hdf5_mod._parse_timestamp_from_filename,
            "_extract_subband_code": hdf5_mod._extract_subband_code,
            "_load_and_merge_subbands": hdf5_mod._load_and_merge_subbands,
        }
        return _exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
