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


class DirectSubbandWriter(MSWriter):
    """
    Parallel MS writer for DSA-110 subband UVH5 files.

    Creates per-subband MS files in parallel, concatenates them,
    and merges all SPWs into a single SPW Measurement Set.

    This is the **production** writer for DSA-110 continuum imaging.

    Args:
        uv: UVData object (used for metadata, not data - data read from file_list)
        ms_path: Output Measurement Set path
        file_list: List of UVH5 subband file paths (required)
        scratch_dir: Directory for temporary files
        max_workers: Maximum parallel workers (default: 4)
        stage_to_tmpfs: Whether to stage to /dev/shm (default: False)
        tmpfs_path: Path to tmpfs mount (default: /dev/shm)
        merge_spws: Whether to merge SPWs after concat (default: False)
    """

    def __init__(self, uv: "UVData", ms_path: str, **kwargs: Any) -> None:
        super().__init__(uv, ms_path, **kwargs)
        self.file_list: List[str] = self.kwargs.get("file_list", [])
        if not self.file_list:
            raise ValueError("DirectSubbandWriter requires 'file_list' in kwargs.")
        self.scratch_dir: Optional[str] = self.kwargs.get("scratch_dir")
        self.max_workers: int = self.kwargs.get("max_workers", 4)
        self.stage_to_tmpfs: bool = bool(self.kwargs.get("stage_to_tmpfs", False))
        self.tmpfs_path: str = str(self.kwargs.get("tmpfs_path", "/dev/shm"))
        self.merge_spws: bool = bool(self.kwargs.get("merge_spws", False))
        self.remove_sigma_spectrum: bool = bool(
            self.kwargs.get("remove_sigma_spectrum", True)
        )

    def get_files_to_process(self) -> Optional[List[str]]:
        return self.file_list

    def write(self) -> str:
        """Execute the parallel subband write and concatenation.
        
        Returns:
            Writer type string: 'parallel-subband'
        """
        # Import here to avoid circular imports and heavy dependencies at module load
        from .direct_subband import write_parallel_subbands
        
        write_parallel_subbands(
            file_list=self.file_list,
            ms_path=self.ms_path,
            scratch_dir=self.scratch_dir,
            max_workers=self.max_workers,
            stage_to_tmpfs=self.stage_to_tmpfs,
            tmpfs_path=self.tmpfs_path,
            merge_spws=self.merge_spws,
            remove_sigma_spectrum=self.remove_sigma_spectrum,
        )
        return "parallel-subband"


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