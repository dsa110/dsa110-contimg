"""
Measurement Set writing strategies for DSA-110 Continuum Imaging Pipeline.

Production writers for converting UVH5 subband files to Measurement Sets.

For testing-only writers (e.g., PyuvdataMonolithicWriter), see:
    backend/tests/fixtures/writers.py
"""

import abc
from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:
    from pyuvdata import UVData


class MSWriter(abc.ABC):
    """Abstract base class for a Measurement Set writer strategy."""

    def __init__(self, uv: "UVData", ms_path: str, **kwargs: Any) -> None:
        """
        Initialize the writer.

        Args:
            uv: The UVData object containing the visibilities to write.
            ms_path: The full path to the output Measurement Set.
            **kwargs: Writer-specific options.
        """
        self.uv = uv
        self.ms_path = ms_path
        self.kwargs = kwargs

    @abc.abstractmethod
    def write(self) -> str:
        """
        Execute the writing strategy.

        Returns:
            The type of writer used (e.g., 'parallel-subband').
        """
        ...

    def get_files_to_process(self) -> Optional[List[str]]:
        """Return a list of raw files needed for this writer, if applicable."""
        return None


# Import the full implementation from direct_subband
# This avoids code duplication and circular imports
from .direct_subband import DirectSubbandWriter

# Backwards compatibility alias
ParallelSubbandWriter = DirectSubbandWriter


def get_writer(writer_type: str) -> type:
    """
    Get a writer class by type name.

    Args:
        writer_type: Writer type ('parallel-subband', 'auto')
                    For testing writers, import from backend/tests/fixtures/writers.py

    Returns:
        Writer class (not instance)

    Raises:
        ValueError: If writer_type is unknown
    """
    writers = {
        "parallel-subband": DirectSubbandWriter,
        "direct-subband": DirectSubbandWriter,
        "auto": DirectSubbandWriter,  # Auto defaults to production writer
    }
    
    if writer_type == "pyuvdata":
        raise ValueError(
            "PyuvdataWriter is for testing only. "
            "Import from backend/tests/fixtures/writers.py instead."
        )
    
    if writer_type not in writers:
        raise ValueError(
            f"Unknown writer type: {writer_type}. "
            f"Available: {list(writers.keys())}"
        )
    
    return writers[writer_type]