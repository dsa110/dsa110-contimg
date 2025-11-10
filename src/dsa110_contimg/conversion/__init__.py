"""Conversion stage for the DSA-110 continuum imaging pipeline.

This package provides a public API for the main conversion entry points.

**Main Entry Points:**

- `convert_single_file`: Convert a single UVH5 file to MS format
- `convert_subband_groups_to_ms`: Discover and convert complete subband groups
- `configure_ms_for_imaging`: Prepare a Measurement Set for imaging
- `CalibratorMSGenerator`: Service for generating MS from calibrator transits

**Quick Start:**

```python
from dsa110_contimg.conversion import convert_single_file, configure_ms_for_imaging

# Convert a single UVH5 file
convert_single_file("observation.uvh5", "observation.ms")

# Configure MS for imaging (usually done automatically)
configure_ms_for_imaging("observation.ms")
```

**For More Information:**

- See `DEVELOPER_GUIDE.md` for development guidelines
- See function docstrings for detailed usage examples
- See `ARCHITECTURE_OPTIMIZATION_RECOMMENDATIONS.md` for design decisions
"""

from .uvh5_to_ms import convert_single_file

# Lazy import to avoid RuntimeWarning when running hdf5_orchestrator as module
# python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator
from .ms_utils import configure_ms_for_imaging
from .merge_spws import merge_spws, merge_spws_simple, get_spw_count
from .calibrator_ms_service import CalibratorMSGenerator, CalibratorMSResult
from .config import CalibratorMSConfig
from .exceptions import (
    CalibratorMSError,
    CalibratorNotFoundError,
    ConversionError,
    GroupNotFoundError,
    TransitNotFoundError,
    ValidationError,
)
from .progress import ProgressReporter


def __getattr__(name: str):
    """Lazy import for hdf5_orchestrator to prevent RuntimeWarning when running as module."""
    if name == "convert_subband_groups_to_ms":
        from .strategies.hdf5_orchestrator import convert_subband_groups_to_ms

        return convert_subband_groups_to_ms
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "convert_single_file",
    "convert_subband_groups_to_ms",  # Lazy imported via __getattr__
    "configure_ms_for_imaging",
    "merge_spws",
    "merge_spws_simple",
    "get_spw_count",
    "CalibratorMSGenerator",
    "CalibratorMSResult",
    "CalibratorMSConfig",
    "ProgressReporter",
    "CalibratorMSError",
    "CalibratorNotFoundError",
    "ConversionError",
    "GroupNotFoundError",
    "TransitNotFoundError",
    "ValidationError",
]
