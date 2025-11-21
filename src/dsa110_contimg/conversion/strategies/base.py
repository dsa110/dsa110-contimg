"""
Base classes for Measurement Set writers.

This module defines the abstract base class for all MS writing strategies.
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
            The type of writer used (e.g., 'pyuvdata', 'dask-ms').
        """
        raise NotImplementedError

    def get_files_to_process(self) -> Optional[List[str]]:
        """Return a list of raw files needed for this writer, if applicable."""
        return None
