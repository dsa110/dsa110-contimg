"""
Test fixtures for UVH5 and Measurement Set data structures.

These fixtures provide mock objects and test data for testing the conversion
pipeline without requiring actual UVH5 files or CASA dependencies.

Usage:
    from tests.fixtures.uvh5_fixtures import (
        mock_uvdata,
        mock_uvdata_multitime,
        mock_antenna_positions,
        MockUVData,
    )
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock
import numpy as np


# DSA-110 specific constants
DSA110_NUM_ANTENNAS = 63
DSA110_NUM_CHANNELS_PER_SUBBAND = 384
DSA110_NUM_SUBBANDS = 16
DSA110_TOTAL_CHANNELS = DSA110_NUM_CHANNELS_PER_SUBBAND * DSA110_NUM_SUBBANDS
DSA110_NUM_POLS = 4  # XX, XY, YX, YY


@dataclass
class MockAntenna:
    """Mock antenna with DSA-110 compatible properties."""
    
    index: int
    name: str
    x: float  # ITRF X coordinate (meters)
    y: float  # ITRF Y coordinate (meters)
    z: float  # ITRF Z coordinate (meters)
    diameter: float = 4.65  # DSA-110 dish diameter in meters


@dataclass 
class MockSpectralWindow:
    """Mock spectral window for testing."""
    
    spw_id: int
    num_chan: int
    ref_freq: float  # Hz
    chan_width: float  # Hz
    
    @property
    def chan_freqs(self) -> np.ndarray:
        """Generate channel frequencies."""
        return self.ref_freq + np.arange(self.num_chan) * self.chan_width


@dataclass
class MockUVData:
    """
    Mock UVData object for testing conversion routines.
    
    This provides a minimal UVData-like interface without requiring
    pyuvdata or actual data files.
    
    Attributes:
        Nants_telescope: Number of antennas in telescope
        Nfreqs: Number of frequency channels
        Npols: Number of polarizations
        Nblts: Number of baseline-times
        Ntimes: Number of unique times
        time_array: Array of observation times (JD)
        freq_array: Array of frequencies (Hz)
        antenna_positions: Antenna positions in ITRF (nants, 3)
        data_array: Visibility data (nblts, 1, nfreqs, npols) - complex
        flag_array: Flag array (nblts, 1, nfreqs, npols) - bool
        phase_center_catalog: Dict of phase centers
        phase_center_id_array: Array mapping blts to phase centers
        extra_keywords: Dict of extra metadata
    """
    
    Nants_telescope: int = DSA110_NUM_ANTENNAS
    Nfreqs: int = DSA110_NUM_CHANNELS_PER_SUBBAND
    Npols: int = DSA110_NUM_POLS
    Nblts: int = 100
    Ntimes: int = 10
    
    time_array: np.ndarray = field(default_factory=lambda: np.array([]))
    freq_array: np.ndarray = field(default_factory=lambda: np.array([]))
    antenna_positions: np.ndarray = field(default_factory=lambda: np.array([]))
    data_array: np.ndarray = field(default_factory=lambda: np.array([]))
    flag_array: np.ndarray = field(default_factory=lambda: np.array([]))
    uvw_array: np.ndarray = field(default_factory=lambda: np.array([]))
    
    # Phase center tracking
    phase_center_catalog: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    phase_center_id_array: Optional[np.ndarray] = None
    phase_type: str = "drift"
    phase_center_frame: str = ""
    
    # Metadata
    extra_keywords: Dict[str, Any] = field(default_factory=dict)
    telescope_name: str = "DSA-110"
    telescope_location: np.ndarray = field(
        default_factory=lambda: np.array([-2409150.402, -4478573.118, 3838617.339])
    )  # OVRO ITRF coordinates
    
    # Antenna metadata
    antenna_names: List[str] = field(default_factory=list)
    antenna_numbers: np.ndarray = field(default_factory=lambda: np.array([]))
    antenna_diameters: np.ndarray = field(default_factory=lambda: np.array([]))
    
    # Baseline info
    ant_1_array: np.ndarray = field(default_factory=lambda: np.array([]))
    ant_2_array: np.ndarray = field(default_factory=lambda: np.array([]))
    
    def __post_init__(self):
        """Initialize arrays if empty."""
        if self.time_array.size == 0:
            # Create time array spanning ~5 minutes
            base_jd = 2460000.5  # Arbitrary JD
            self.time_array = np.repeat(
                np.linspace(base_jd, base_jd + 5 / 1440, self.Ntimes),
                self.Nblts // self.Ntimes
            )[:self.Nblts]
        
        if self.freq_array.size == 0:
            # Create frequency array for one subband (1.28-1.53 GHz range)
            self.freq_array = np.linspace(1.28e9, 1.28e9 + 250e6, self.Nfreqs)
        
        if self.antenna_positions.size == 0:
            # Generate random antenna positions around OVRO
            self.antenna_positions = np.random.randn(self.Nants_telescope, 3) * 100
        
        if self.antenna_names == []:
            self.antenna_names = [f"DSA-{i:03d}" for i in range(self.Nants_telescope)]
            
        if self.antenna_numbers.size == 0:
            self.antenna_numbers = np.arange(self.Nants_telescope)
            
        if self.antenna_diameters.size == 0:
            self.antenna_diameters = np.full(self.Nants_telescope, 4.65)
        
        if self.data_array.size == 0:
            # Create random complex visibility data
            self.data_array = (
                np.random.randn(self.Nblts, 1, self.Nfreqs, self.Npols) +
                1j * np.random.randn(self.Nblts, 1, self.Nfreqs, self.Npols)
            ).astype(np.complex64)
        
        if self.flag_array.size == 0:
            # No flags by default
            self.flag_array = np.zeros(
                (self.Nblts, 1, self.Nfreqs, self.Npols), 
                dtype=bool
            )
            
        if self.uvw_array.size == 0:
            # Random UVW coordinates
            self.uvw_array = np.random.randn(self.Nblts, 3) * 1000
            
        if self.ant_1_array.size == 0:
            # Generate baseline pairs
            baselines = []
            for i in range(min(10, self.Nants_telescope)):
                for j in range(i + 1, min(11, self.Nants_telescope)):
                    baselines.append((i, j))
            baselines = baselines[:self.Nblts // self.Ntimes]
            self.ant_1_array = np.tile(
                [b[0] for b in baselines], self.Ntimes
            )[:self.Nblts]
            self.ant_2_array = np.tile(
                [b[1] for b in baselines], self.Ntimes
            )[:self.Nblts]
    
    def _add_phase_center(
        self,
        cat_name: str,
        cat_type: str = "sidereal",
        cat_lon: float = 0.0,
        cat_lat: float = 0.0,
        cat_frame: str = "icrs",
        cat_epoch: float = 2000.0,
        **kwargs
    ) -> int:
        """Add a phase center to the catalog."""
        cat_id = len(self.phase_center_catalog)
        self.phase_center_catalog[cat_id] = {
            "cat_name": cat_name,
            "cat_type": cat_type,
            "cat_lon": cat_lon,
            "cat_lat": cat_lat,
            "cat_frame": cat_frame,
            "cat_epoch": cat_epoch,
            **kwargs,
        }
        return cat_id
    
    def write_ms(self, path: str, **kwargs) -> None:
        """Mock MS write (does nothing)."""
        pass
    
    def read(self, path: str, **kwargs) -> None:
        """Mock read (does nothing)."""
        pass
    
    def __iadd__(self, other: "MockUVData") -> "MockUVData":
        """Mock in-place addition for subband combining."""
        # In real pyuvdata, this combines subbands
        self.Nfreqs += other.Nfreqs
        self.freq_array = np.concatenate([self.freq_array, other.freq_array])
        return self


def create_mock_uvdata(
    ntimes: int = 10,
    nfreqs: int = 384,
    nants: int = 63,
    npols: int = 4,
    start_freq_hz: float = 1.28e9,
    chan_width_hz: float = 650e3,
) -> MockUVData:
    """
    Create a MockUVData object with specified parameters.
    
    Args:
        ntimes: Number of time samples
        nfreqs: Number of frequency channels
        nants: Number of antennas
        npols: Number of polarizations
        start_freq_hz: Starting frequency in Hz
        chan_width_hz: Channel width in Hz
        
    Returns:
        MockUVData object with initialized arrays
    """
    nbaselines = nants * (nants - 1) // 2
    nblts = nbaselines * ntimes
    
    return MockUVData(
        Nants_telescope=nants,
        Nfreqs=nfreqs,
        Npols=npols,
        Nblts=nblts,
        Ntimes=ntimes,
        freq_array=start_freq_hz + np.arange(nfreqs) * chan_width_hz,
    )


def create_mock_uvdata_multitime(
    ntimes: int = 24,
    time_interval_sec: float = 12.88,
) -> MockUVData:
    """
    Create MockUVData with multiple time samples (like a drift scan).
    
    DSA-110 observations have 24 fields at 12.88 second intervals.
    
    Args:
        ntimes: Number of time samples (default 24 for full drift scan)
        time_interval_sec: Interval between samples in seconds
        
    Returns:
        MockUVData with properly spaced time samples
    """
    base_jd = 2460000.5
    time_step_jd = time_interval_sec / 86400.0
    
    nants = 63
    nbaselines = nants * (nants - 1) // 2
    nblts = nbaselines * ntimes
    
    # Create time array with proper intervals
    unique_times = base_jd + np.arange(ntimes) * time_step_jd
    time_array = np.repeat(unique_times, nbaselines)
    
    return MockUVData(
        Ntimes=ntimes,
        Nblts=nblts,
        time_array=time_array,
    )


def mock_antenna_positions(nants: int = DSA110_NUM_ANTENNAS) -> np.ndarray:
    """
    Generate mock DSA-110 antenna positions in ITRF coordinates.
    
    Creates positions clustered around OVRO location with realistic spacing.
    
    Args:
        nants: Number of antennas
        
    Returns:
        Array of shape (nants, 3) with ITRF X, Y, Z coordinates in meters
    """
    # OVRO location (approximate ITRF)
    ovro_x = -2409150.402
    ovro_y = -4478573.118
    ovro_z = 3838617.339
    
    # Generate positions within ~2km of center
    np.random.seed(42)  # Reproducible positions
    offsets = np.random.randn(nants, 3) * 500  # ~500m spread
    
    positions = np.array([
        [ovro_x, ovro_y, ovro_z]
    ]) + offsets
    
    return positions


def create_mock_casacore_table(
    data: Optional[Dict[str, np.ndarray]] = None,
    nrows: int = 10,
) -> MagicMock:
    """
    Create a mock casacore table for testing.
    
    Args:
        data: Dict of column name -> array data
        nrows: Number of rows if data not provided
        
    Returns:
        MagicMock configured as a casacore table
    """
    mock_table = MagicMock()
    mock_table.nrows.return_value = nrows
    
    if data:
        def getcol_side_effect(colname):
            if colname in data:
                return data[colname]
            raise RuntimeError(f"Column {colname} not found")
        
        mock_table.getcol.side_effect = getcol_side_effect
        mock_table.nrows.return_value = len(next(iter(data.values())))
    
    # Support context manager usage
    mock_table.__enter__ = MagicMock(return_value=mock_table)
    mock_table.__exit__ = MagicMock(return_value=False)
    
    return mock_table


def create_mock_ms_tables(
    nspw: int = 1,
    nchan: int = 384,
    nfield: int = 24,
    nant: int = 63,
    nrows: int = 1000,
    start_freq_hz: float = 1.28e9,
) -> Dict[str, MagicMock]:
    """
    Create a complete set of mock MS subtables for testing.
    
    Args:
        nspw: Number of spectral windows
        nchan: Channels per spectral window
        nfield: Number of fields
        nant: Number of antennas
        nrows: Number of rows in main table
        start_freq_hz: Starting frequency
        
    Returns:
        Dict mapping table name to mock table object
    """
    tables = {}
    
    # Main table
    tables["MAIN"] = create_mock_casacore_table(
        data={
            "TIME": np.linspace(5e9, 5e9 + 300, nrows),  # MJD seconds
            "DATA": np.random.randn(nrows, nchan, 4) + 1j * np.random.randn(nrows, nchan, 4),
            "FLAG": np.zeros((nrows, nchan, 4), dtype=bool),
            "UVW": np.random.randn(nrows, 3) * 1000,
            "ANTENNA1": np.random.randint(0, nant, nrows),
            "ANTENNA2": np.random.randint(0, nant, nrows),
            "FIELD_ID": np.random.randint(0, nfield, nrows),
            "DATA_DESC_ID": np.zeros(nrows, dtype=int),
        }
    )
    
    # SPECTRAL_WINDOW table
    chan_freqs = np.array([
        start_freq_hz + np.arange(nchan) * 650e3
        for _ in range(nspw)
    ])
    tables["SPECTRAL_WINDOW"] = create_mock_casacore_table(
        data={
            "CHAN_FREQ": chan_freqs,
            "CHAN_WIDTH": np.full((nspw, nchan), 650e3),
            "NUM_CHAN": np.full(nspw, nchan, dtype=int),
            "REF_FREQUENCY": chan_freqs[:, nchan // 2],
        }
    )
    
    # FIELD table
    phase_dirs = np.zeros((nfield, 1, 2))
    phase_dirs[:, 0, 0] = np.linspace(0, 2 * np.pi / 24, nfield)  # RA
    phase_dirs[:, 0, 1] = np.full(nfield, np.deg2rad(37.0))  # Dec
    tables["FIELD"] = create_mock_casacore_table(
        data={
            "PHASE_DIR": phase_dirs,
            "DELAY_DIR": phase_dirs.copy(),
            "REFERENCE_DIR": phase_dirs.copy(),
            "NAME": np.array([f"meridian_icrs_t{i}" for i in range(nfield)]),
        }
    )
    
    # ANTENNA table
    positions = mock_antenna_positions(nant)
    tables["ANTENNA"] = create_mock_casacore_table(
        data={
            "POSITION": positions,
            "DISH_DIAMETER": np.full(nant, 4.65),
            "NAME": np.array([f"DSA-{i:03d}" for i in range(nant)]),
            "STATION": np.array([f"ST{i:03d}" for i in range(nant)]),
        }
    )
    
    return tables


# Convenience fixtures for pytest
def mock_uvdata() -> MockUVData:
    """Return a basic MockUVData fixture."""
    return create_mock_uvdata()


def mock_uvdata_multitime() -> MockUVData:
    """Return a MockUVData with multiple times (drift scan)."""
    return create_mock_uvdata_multitime()
