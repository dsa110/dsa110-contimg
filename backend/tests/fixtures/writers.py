"""
Testing-only MS writers for DSA-110 Continuum Imaging Pipeline.

These writers are NOT for production use. They are intended for:
- Unit tests with small synthetic datasets (≤2 subbands)
- Integration tests that don't require full parallel processing
- Quick validation of conversion logic

For production, use DirectSubbandWriter from:
    dsa110_contimg.conversion.strategies.writers
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyuvdata import UVData


class PyuvdataMonolithicWriter:
    """
    Writes a merged UVData object directly to a single MS using pyuvdata.

    **TESTING ONLY:** This writer is intended for testing scenarios with ≤2 subbands.
    Production processing always uses 16 subbands and should use DirectSubbandWriter
    (parallel-subband) instead.

    This writer loads all subbands into memory and writes them in a single operation,
    which is inefficient for production use with 16 subbands.

    Args:
        uv: The UVData object containing the visibilities to write.
        ms_path: The full path to the output Measurement Set.
        **kwargs: Additional options (ignored for this simple writer).

    Example:
        >>> from pyuvdata import UVData
        >>> from tests.fixtures.writers import PyuvdataMonolithicWriter
        >>> 
        >>> uv = UVData()
        >>> uv.read("test_data.uvh5")
        >>> writer = PyuvdataMonolithicWriter(uv, "/tmp/test.ms")
        >>> writer.write()
        'pyuvdata'
    """

    def __init__(self, uv: "UVData", ms_path: str, **kwargs: Any) -> None:
        self.uv = uv
        self.ms_path = ms_path
        self.kwargs = kwargs

    def write(self) -> str:
        """
        Execute the pyuvdata write.

        Returns:
            Writer type string: 'pyuvdata'
        """
        self.uv.write_ms(
            self.ms_path,
            clobber=True,
            run_check=False,
            check_extra=False,
            run_check_acceptability=False,
            strict_uvw_antpos_check=False,
            check_autos=False,
            fix_autos=False,
            force_phase=True,
        )
        return "pyuvdata"

    def get_files_to_process(self):
        """Return None - this writer uses in-memory UVData, not file list."""
        return None


# Convenience alias
PyuvdataWriter = PyuvdataMonolithicWriter


def get_test_writer(writer_type: str) -> type:
    """
    Get a testing writer class by type name.

    Args:
        writer_type: Writer type ('pyuvdata')

    Returns:
        Writer class (not instance)

    Raises:
        ValueError: If writer_type is unknown
    """
    writers = {
        "pyuvdata": PyuvdataMonolithicWriter,
        "pyuvdata-monolithic": PyuvdataMonolithicWriter,
    }

    if writer_type not in writers:
        raise ValueError(
            f"Unknown test writer type: {writer_type}. "
            f"Available: {list(writers.keys())}. "
            f"For production writers, use dsa110_contimg.conversion.strategies.writers"
        )

    return writers[writer_type]
