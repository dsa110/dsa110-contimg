"""
Monolithic MS writer using pyuvdata.

This strategy writes the entire merged UVData object to a Measurement Set
in a single step using `pyuvdata.UVData.write_ms()`.
"""

from .base import MSWriter


class PyuvdataMonolithicWriter(MSWriter):
    """Writes a merged UVData object directly to a single MS."""

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
