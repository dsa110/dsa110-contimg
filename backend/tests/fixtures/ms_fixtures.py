"""
Test fixtures for MS (Measurement Set) data structures.

These fixtures provide mock MS tables and utilities for testing CASA-dependent
code without requiring actual MS files or casacore installation.

Usage:
    from tests.fixtures.ms_fixtures import (
        create_temp_ms_structure,
        MockMSTable,
        mock_spectral_window_table,
    )
"""

import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
from unittest.mock import MagicMock, patch
import numpy as np


@dataclass
class MockMSTable:
    """
    Mock casacore table that can be used as a context manager.
    
    Supports common table operations like getcol, putcol, nrows, etc.
    
    Example:
        table = MockMSTable(data={"CHAN_FREQ": freq_array})
        with table:
            freqs = table.getcol("CHAN_FREQ")
    """
    
    data: Dict[str, np.ndarray] = field(default_factory=dict)
    readonly: bool = True
    _closed: bool = False
    
    def getcol(self, colname: str, startrow: int = 0, nrow: int = -1) -> np.ndarray:
        """Get column data."""
        if colname not in self.data:
            raise RuntimeError(f"Column {colname} not found")
        
        col_data = self.data[colname]
        if nrow == -1:
            return col_data[startrow:]
        return col_data[startrow:startrow + nrow]
    
    def putcol(self, colname: str, value: np.ndarray, startrow: int = 0) -> None:
        """Put column data."""
        if self.readonly:
            raise RuntimeError("Table is read-only")
        self.data[colname] = value
    
    def nrows(self) -> int:
        """Return number of rows."""
        if not self.data:
            return 0
        return len(next(iter(self.data.values())))
    
    def colnames(self) -> List[str]:
        """Return column names."""
        return list(self.data.keys())
    
    def close(self) -> None:
        """Close the table."""
        self._closed = True
    
    def flush(self) -> None:
        """Flush changes (no-op for mock)."""
        pass
    
    def __enter__(self) -> "MockMSTable":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.close()
        return False


def create_spectral_window_table(
    nspw: int = 1,
    nchan: int = 384,
    start_freq_hz: float = 1.28e9,
    chan_width_hz: float = 650e3,
    ascending: bool = True,
) -> MockMSTable:
    """
    Create a mock SPECTRAL_WINDOW table.
    
    Args:
        nspw: Number of spectral windows
        nchan: Channels per window
        start_freq_hz: Starting frequency
        chan_width_hz: Channel width
        ascending: If True, frequencies are ascending; if False, descending
        
    Returns:
        MockMSTable with SPECTRAL_WINDOW columns
    """
    if ascending:
        chan_freqs = np.array([
            start_freq_hz + (i * nchan * chan_width_hz) + np.arange(nchan) * chan_width_hz
            for i in range(nspw)
        ])
    else:
        # Descending order (DSA-110 raw format - sb00=highest, sb15=lowest)
        total_bw = nspw * nchan * chan_width_hz
        chan_freqs = np.array([
            (start_freq_hz + total_bw) - (i * nchan * chan_width_hz) - np.arange(nchan) * chan_width_hz
            for i in range(nspw)
        ])
    
    return MockMSTable(
        data={
            "CHAN_FREQ": chan_freqs,
            "CHAN_WIDTH": np.full((nspw, nchan), chan_width_hz),
            "NUM_CHAN": np.full(nspw, nchan, dtype=np.int32),
            "REF_FREQUENCY": chan_freqs[:, nchan // 2],
            "TOTAL_BANDWIDTH": np.full(nspw, nchan * chan_width_hz),
            "EFFECTIVE_BW": np.full((nspw, nchan), chan_width_hz),
        }
    )


def create_field_table(
    nfield: int = 24,
    base_ra_rad: float = 0.0,
    base_dec_rad: float = 0.6458,  # ~37 deg (OVRO latitude)
    ra_step_rad: float = 0.0,  # No RA stepping for fixed phase centers
    time_dependent: bool = True,
) -> MockMSTable:
    """
    Create a mock FIELD table.
    
    For DSA-110, fields represent different time samples during a drift scan.
    With time-dependent phasing, each field has a different phase center
    tracking the meridian.
    
    Args:
        nfield: Number of fields
        base_ra_rad: Base RA in radians
        base_dec_rad: Base Dec in radians
        ra_step_rad: RA step per field (for time-dependent phasing)
        time_dependent: If True, simulate time-dependent phasing with RA tracking
        
    Returns:
        MockMSTable with FIELD columns
    """
    if time_dependent:
        # RA changes by ~15 deg/hour, or 0.003636 rad/12.88s
        ra_step_rad = np.deg2rad(15.0 / 3600 * 12.88)  # 12.88s interval
    
    phase_dirs = np.zeros((nfield, 1, 2))
    phase_dirs[:, 0, 0] = base_ra_rad + np.arange(nfield) * ra_step_rad  # RA
    phase_dirs[:, 0, 1] = base_dec_rad  # Dec (constant)
    
    names = [f"meridian_icrs_t{i}" for i in range(nfield)]
    
    return MockMSTable(
        data={
            "PHASE_DIR": phase_dirs,
            "DELAY_DIR": phase_dirs.copy(),
            "REFERENCE_DIR": phase_dirs.copy(),
            "NAME": np.array(names, dtype=object),
            "NUM_POLY": np.zeros(nfield, dtype=np.int32),
            "SOURCE_ID": np.arange(nfield, dtype=np.int32),
        }
    )


def create_antenna_table(
    nant: int = 63,
    use_dsa110_layout: bool = True,
) -> MockMSTable:
    """
    Create a mock ANTENNA table.
    
    Args:
        nant: Number of antennas
        use_dsa110_layout: If True, use realistic DSA-110 positions
        
    Returns:
        MockMSTable with ANTENNA columns
    """
    # OVRO ITRF coordinates
    ovro_x = -2409150.402
    ovro_y = -4478573.118
    ovro_z = 3838617.339
    
    if use_dsa110_layout:
        np.random.seed(42)  # Reproducible
        offsets = np.random.randn(nant, 3) * 300  # ~300m spread
        positions = np.array([[ovro_x, ovro_y, ovro_z]]) + offsets
    else:
        positions = np.zeros((nant, 3))
        positions[:, 0] = ovro_x
        positions[:, 1] = ovro_y
        positions[:, 2] = ovro_z
    
    return MockMSTable(
        data={
            "POSITION": positions,
            "DISH_DIAMETER": np.full(nant, 4.65),
            "NAME": np.array([f"DSA-{i:03d}" for i in range(nant)], dtype=object),
            "STATION": np.array([f"ST{i:03d}" for i in range(nant)], dtype=object),
            "TYPE": np.array(["GROUND-BASED"] * nant, dtype=object),
            "MOUNT": np.array(["ALT-AZ"] * nant, dtype=object),
            "OFFSET": np.zeros((nant, 3)),
        }
    )


def create_main_table(
    nrows: int = 1000,
    nant: int = 63,
    nchan: int = 384,
    npol: int = 4,
    nfield: int = 24,
    obs_duration_sec: float = 309.0,  # ~5 minutes
) -> MockMSTable:
    """
    Create a mock main MS table.
    
    Args:
        nrows: Number of visibility rows
        nant: Number of antennas
        nchan: Number of channels
        npol: Number of polarizations
        nfield: Number of fields
        obs_duration_sec: Observation duration in seconds
        
    Returns:
        MockMSTable with main table columns
    """
    # Generate baseline indices
    ant1 = []
    ant2 = []
    for i in range(nant):
        for j in range(i + 1, nant):
            ant1.append(i)
            ant2.append(j)
    
    nbaselines = len(ant1)
    ntimes = max(1, nrows // nbaselines)
    
    # Time array (MJD seconds)
    base_time = 5.0e9  # Arbitrary MJD seconds
    time_step = obs_duration_sec / ntimes
    times = np.repeat(
        base_time + np.arange(ntimes) * time_step,
        nbaselines
    )[:nrows]
    
    # Baseline arrays
    ant1_arr = np.tile(ant1, ntimes)[:nrows]
    ant2_arr = np.tile(ant2, ntimes)[:nrows]
    
    # Field IDs (cycle through fields based on time)
    field_ids = (np.arange(nrows) // nbaselines) % nfield
    
    # Random visibility data
    np.random.seed(123)
    data = (
        np.random.randn(nrows, nchan, npol) + 
        1j * np.random.randn(nrows, nchan, npol)
    ).astype(np.complex64)
    
    return MockMSTable(
        data={
            "TIME": times,
            "TIME_CENTROID": times,
            "ANTENNA1": ant1_arr.astype(np.int32),
            "ANTENNA2": ant2_arr.astype(np.int32),
            "DATA": data,
            "CORRECTED_DATA": data.copy(),
            "MODEL_DATA": np.ones_like(data),
            "FLAG": np.zeros((nrows, nchan, npol), dtype=bool),
            "FLAG_ROW": np.zeros(nrows, dtype=bool),
            "UVW": np.random.randn(nrows, 3) * 1000,
            "WEIGHT": np.ones((nrows, npol), dtype=np.float32),
            "SIGMA": np.ones((nrows, npol), dtype=np.float32),
            "FIELD_ID": field_ids.astype(np.int32),
            "DATA_DESC_ID": np.zeros(nrows, dtype=np.int32),
            "SCAN_NUMBER": np.ones(nrows, dtype=np.int32),
            "INTERVAL": np.full(nrows, time_step),
            "EXPOSURE": np.full(nrows, time_step),
        },
        readonly=False,
    )


@contextmanager
def mock_ms_table_access(
    tables: Dict[str, MockMSTable],
    ms_path: str = "/mock/path/test.ms",
) -> Generator[None, None, None]:
    """
    Context manager that patches casacore.tables.table to return mock tables.
    
    Args:
        tables: Dict mapping subtable suffix to MockMSTable
                e.g., {"SPECTRAL_WINDOW": spw_table, "FIELD": field_table}
        ms_path: Path that the mock should respond to
        
    Yields:
        None - use within a with block
    
    Example:
        tables = {
            "SPECTRAL_WINDOW": create_spectral_window_table(),
            "FIELD": create_field_table(),
        }
        with mock_ms_table_access(tables, "/test/obs.ms"):
            validate_ms_frequency_order("/test/obs.ms")
    """
    def mock_table_factory(path: str, readonly: bool = True, ack: bool = True):
        # Extract subtable name from path
        # e.g., "/test/obs.ms::SPECTRAL_WINDOW" -> "SPECTRAL_WINDOW"
        if "::" in path:
            subtable = path.split("::")[-1]
        else:
            subtable = "MAIN"
        
        if subtable in tables:
            table = tables[subtable]
            table.readonly = readonly
            return table
        
        raise RuntimeError(f"Mock table not found: {subtable}")
    
    with patch("dsa110_contimg.conversion.helpers.table", mock_table_factory):
        yield


@contextmanager
def create_temp_ms_directory() -> Generator[Path, None, None]:
    """
    Create a temporary directory structure resembling an MS.
    
    This creates the directory structure but not actual CASA tables.
    Useful for testing path-based operations.
    
    Yields:
        Path to temporary MS directory
    """
    with tempfile.TemporaryDirectory(suffix=".ms") as tmpdir:
        ms_path = Path(tmpdir)
        
        # Create subdirectory structure
        for subdir in ["ANTENNA", "FIELD", "SPECTRAL_WINDOW", "DATA_DESCRIPTION"]:
            (ms_path / subdir).mkdir()
            (ms_path / subdir / "table.dat").touch()
        
        # Create main table marker
        (ms_path / "table.dat").touch()
        
        yield ms_path


def create_complete_mock_ms(
    nspw: int = 1,
    nchan: int = 384,
    nfield: int = 24,
    nant: int = 63,
    nrows: int = 1000,
    start_freq_hz: float = 1.28e9,
    ascending_freq: bool = True,
) -> Dict[str, MockMSTable]:
    """
    Create a complete set of mock MS tables.
    
    This is the primary fixture for testing MS operations.
    
    Args:
        nspw: Number of spectral windows
        nchan: Channels per window
        nfield: Number of fields
        nant: Number of antennas
        nrows: Number of main table rows
        start_freq_hz: Starting frequency
        ascending_freq: If True, frequencies are ascending
        
    Returns:
        Dict mapping table name to MockMSTable
    """
    return {
        "MAIN": create_main_table(nrows, nant, nchan, 4, nfield),
        "SPECTRAL_WINDOW": create_spectral_window_table(
            nspw, nchan, start_freq_hz, ascending=ascending_freq
        ),
        "FIELD": create_field_table(nfield),
        "ANTENNA": create_antenna_table(nant),
    }
