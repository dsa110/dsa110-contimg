"""
Monolithic MS writer using pyuvdata.

**TESTING ONLY:** This writer is intended for testing scenarios with ≤2 subbands.
Production processing always uses 16 subbands and should use the parallel-subband writer.

This strategy writes the entire merged UVData object to a Measurement Set
in a single step using `pyuvdata.UVData.write_ms()`. It requires loading all
subbands into memory simultaneously, which is not efficient for production use.
"""

from .base import MSWriter


class PyuvdataMonolithicWriter(MSWriter):
    """
    Writes a merged UVData object directly to a single MS.

    **TESTING ONLY:** This writer is intended for testing scenarios with ≤2 subbands.
    Production processing always uses 16 subbands and should use DirectSubbandWriter
    (parallel-subband) instead.

    This writer loads all subbands into memory and writes them in a single operation,
    which is inefficient for production use with 16 subbands.
    """

    def write(self) -> str:
        """Execute the pyuvdata write."""
        # Allow pyuvdata to force a projection if something upstream
        # leaves the data in an unprojected state
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
