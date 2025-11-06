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
        convert_subband_groups_to_ms,
        find_subband_groups,
        _parse_timestamp_from_filename,
        _extract_subband_code,
        _load_and_merge_subbands,
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
    if name == "hdf5_orchestrator":
        # Lazy import to avoid RuntimeWarning when running as module
        from . import hdf5_orchestrator
        return hdf5_orchestrator
    elif name in __all__:
        from .hdf5_orchestrator import (
            convert_subband_groups_to_ms,
            find_subband_groups,
            _parse_timestamp_from_filename,
            _extract_subband_code,
            _load_and_merge_subbands,
        )
        # Create a mapping of names to functions
        _exports = {
            "convert_subband_groups_to_ms": convert_subband_groups_to_ms,
            "find_subband_groups": find_subband_groups,
            "_parse_timestamp_from_filename": _parse_timestamp_from_filename,
            "_extract_subband_code": _extract_subband_code,
            "_load_and_merge_subbands": _load_and_merge_subbands,
        }
        return _exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
