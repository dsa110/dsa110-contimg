"""
Contract tests for UVH5 → Measurement Set conversion.

These tests verify that the conversion pipeline produces valid,
standards-compliant Measurement Sets that can be used with CASA.

Contract guarantees:
1. Output MS exists and has correct directory structure
2. All required MS tables are present (MAIN, ANTENNA, SPECTRAL_WINDOW, etc.)
3. Data shapes are correct (Nbaselines × Nchannels × Npols)
4. Antenna positions are DSA-110 specific
5. Frequency array covers expected bandwidth
6. UVW coordinates are physically reasonable
7. MS can be opened by casatools without error
"""

import os
from pathlib import Path
from typing import List

import numpy as np
import pytest


class TestMSStructureContract:
    """Verify MS directory structure and required tables."""

    def test_ms_directory_exists(self, synthetic_ms: Path):
        """Contract: Output MS must exist as a directory."""
        assert synthetic_ms.exists(), f"MS not created at {synthetic_ms}"
        assert synthetic_ms.is_dir(), "MS must be a directory, not a file"

    def test_required_tables_present(self, synthetic_ms: Path):
        """Contract: MS must contain all required CASA tables."""
        required_tables = [
            "ANTENNA",
            "DATA_DESCRIPTION",
            "FEED",
            "FIELD",
            "FLAG_CMD",
            "HISTORY",
            "OBSERVATION",
            "POINTING",
            "POLARIZATION",
            "PROCESSOR",
            "SPECTRAL_WINDOW",
            "STATE",
        ]
        
        for table_name in required_tables:
            table_path = synthetic_ms / table_name
            assert table_path.exists(), f"Required table {table_name} not found"

    def test_main_table_has_data(self, synthetic_ms: Path):
        """Contract: Main table must contain visibility data."""
        try:
            from casacore.tables import table
        except ImportError:
            pytest.skip("casacore not available")
        
        with table(str(synthetic_ms), readonly=True) as tb:
            nrows = tb.nrows()
            assert nrows > 0, "Main table has no rows"
            
            # Verify required columns exist
            required_cols = ["DATA", "FLAG", "UVW", "TIME", "ANTENNA1", "ANTENNA2"]
            actual_cols = tb.colnames()
            for col in required_cols:
                assert col in actual_cols, f"Required column {col} not in main table"


class TestAntennaContract:
    """Verify antenna information matches DSA-110 specifications."""

    @pytest.mark.parametrize("expected_antennas", [63])
    def test_antenna_count(self, synthetic_ms: Path, expected_antennas: int):
        """Contract: MS must have correct number of DSA-110 antennas."""
        try:
            from casacore.tables import table
        except ImportError:
            pytest.skip("casacore not available")
        
        with table(str(synthetic_ms / "ANTENNA"), readonly=True) as tb:
            nants = tb.nrows()
            assert nants == expected_antennas, f"Expected {expected_antennas} antennas, got {nants}"

    def test_antenna_positions_itrf(self, synthetic_ms: Path):
        """Contract: Antenna positions must be valid ITRF coordinates."""
        try:
            from casacore.tables import table
        except ImportError:
            pytest.skip("casacore not available")
        
        with table(str(synthetic_ms / "ANTENNA"), readonly=True) as tb:
            positions = tb.getcol("POSITION")
            
            # Verify shape: (Nants, 3)
            assert positions.ndim == 2, "Positions must be 2D array"
            assert positions.shape[1] == 3, "Positions must have X, Y, Z"
            
            # ITRF coordinates for OVRO should be approximately:
            # X: -2.4M meters, Y: -4.5M meters, Z: 3.8M meters
            mean_pos = np.mean(positions, axis=0)
            assert -3e6 < mean_pos[0] < -2e6, f"X coord {mean_pos[0]} not near OVRO"
            assert -5e6 < mean_pos[1] < -4e6, f"Y coord {mean_pos[1]} not near OVRO"
            assert 3e6 < mean_pos[2] < 4e6, f"Z coord {mean_pos[2]} not near OVRO"

    def test_antenna_diameters(self, synthetic_ms: Path):
        """Contract: All antennas must have DSA-110 dish diameter."""
        try:
            from casacore.tables import table
        except ImportError:
            pytest.skip("casacore not available")
        
        expected_diameter = 4.65  # meters
        tolerance = 0.1  # 10cm tolerance
        
        with table(str(synthetic_ms / "ANTENNA"), readonly=True) as tb:
            if "DISH_DIAMETER" in tb.colnames():
                diameters = tb.getcol("DISH_DIAMETER")
                assert np.allclose(diameters, expected_diameter, atol=tolerance), \
                    f"Dish diameters should be {expected_diameter}m"


class TestSpectralWindowContract:
    """Verify spectral window configuration."""

    def test_frequency_coverage(self, synthetic_ms: Path):
        """Contract: MS must cover DSA-110 frequency range (1.28-1.53 GHz)."""
        try:
            from casacore.tables import table
        except ImportError:
            pytest.skip("casacore not available")
        
        with table(str(synthetic_ms / "SPECTRAL_WINDOW"), readonly=True) as tb:
            chan_freqs = tb.getcol("CHAN_FREQ")
            
            # Flatten if 2D (nspw, nchan)
            all_freqs = chan_freqs.flatten()
            
            min_freq_ghz = np.min(all_freqs) / 1e9
            max_freq_ghz = np.max(all_freqs) / 1e9
            
            # DSA-110 operates 1.28-1.53 GHz
            assert min_freq_ghz >= 1.2, f"Min freq {min_freq_ghz} GHz below expected"
            assert max_freq_ghz <= 1.6, f"Max freq {max_freq_ghz} GHz above expected"
            assert max_freq_ghz - min_freq_ghz >= 0.2, "Bandwidth too narrow"

    def test_channel_count(self, synthetic_ms: Path):
        """Contract: MS must have expected channel count."""
        try:
            from casacore.tables import table
        except ImportError:
            pytest.skip("casacore not available")
        
        with table(str(synthetic_ms / "SPECTRAL_WINDOW"), readonly=True) as tb:
            num_chan = tb.getcol("NUM_CHAN")
            total_chans = np.sum(num_chan)
            
            # Full 16 subbands × 384 channels = 6144 channels
            # But our minimal fixture may have fewer
            assert total_chans >= 384, f"Expected at least 384 channels, got {total_chans}"


class TestDataContract:
    """Verify visibility data integrity."""

    def test_data_shape(self, synthetic_ms: Path):
        """Contract: DATA column must have correct shape."""
        try:
            from casacore.tables import table
        except ImportError:
            pytest.skip("casacore not available")
        
        with table(str(synthetic_ms), readonly=True) as tb:
            # Read first row to check shape
            data = tb.getcol("DATA", startrow=0, nrow=1)
            
            # Shape should be (1, Nchan, Npol) for single row
            assert data.ndim == 3, f"DATA should be 3D, got {data.ndim}D"
            
            nchan = data.shape[1]
            npol = data.shape[2]
            
            # DSA-110 has 4 polarizations
            assert npol == 4, f"Expected 4 pols, got {npol}"
            
            # Channels should be multiple of 384
            assert nchan >= 384, f"Expected at least 384 channels, got {nchan}"

    def test_data_is_complex(self, synthetic_ms: Path):
        """Contract: Visibility data must be complex."""
        try:
            from casacore.tables import table
        except ImportError:
            pytest.skip("casacore not available")
        
        with table(str(synthetic_ms), readonly=True) as tb:
            data = tb.getcol("DATA", startrow=0, nrow=1)
            assert np.iscomplexobj(data), "DATA must be complex"

    def test_uvw_physically_reasonable(self, synthetic_ms: Path):
        """Contract: UVW coordinates must be physically reasonable."""
        try:
            from casacore.tables import table
        except ImportError:
            pytest.skip("casacore not available")
        
        with table(str(synthetic_ms), readonly=True) as tb:
            uvw = tb.getcol("UVW")
            
            # UVW should be in meters, DSA-110 baselines up to ~1.5 km
            max_baseline = 1500  # meters
            
            u_max = np.max(np.abs(uvw[:, 0]))
            v_max = np.max(np.abs(uvw[:, 1]))
            w_max = np.max(np.abs(uvw[:, 2]))
            
            assert u_max < max_baseline, f"U coord {u_max}m exceeds max baseline"
            assert v_max < max_baseline, f"V coord {v_max}m exceeds max baseline"
            assert w_max < max_baseline, f"W coord {w_max}m exceeds max baseline"

    def test_no_all_nan_visibilities(self, synthetic_ms: Path):
        """Contract: Data should not be all NaN."""
        try:
            from casacore.tables import table
        except ImportError:
            pytest.skip("casacore not available")
        
        with table(str(synthetic_ms), readonly=True) as tb:
            data = tb.getcol("DATA")
            
            # Check for all-NaN data
            nan_fraction = np.sum(np.isnan(data)) / data.size
            assert nan_fraction < 0.5, f"Too many NaN values: {nan_fraction:.1%}"


class TestFieldContract:
    """Verify field/phase center configuration."""

    def test_field_count(self, synthetic_ms: Path):
        """Contract: MS must have expected number of fields."""
        try:
            from casacore.tables import table
        except ImportError:
            pytest.skip("casacore not available")
        
        with table(str(synthetic_ms / "FIELD"), readonly=True) as tb:
            nfields = tb.nrows()
            
            # DSA-110 typically has 24 fields per observation
            # But our minimal fixture may have fewer
            assert nfields >= 1, "Must have at least one field"

    def test_phase_center_reasonable(self, synthetic_ms: Path):
        """Contract: Phase centers must be valid celestial coordinates."""
        try:
            from casacore.tables import table
        except ImportError:
            pytest.skip("casacore not available")
        
        with table(str(synthetic_ms / "FIELD"), readonly=True) as tb:
            phase_dir = tb.getcol("PHASE_DIR")  # Shape: (nfield, 1, 2) - RA, Dec
            
            ra_rad = phase_dir[:, 0, 0]
            dec_rad = phase_dir[:, 0, 1]
            
            # Convert to degrees
            ra_deg = np.degrees(ra_rad)
            dec_deg = np.degrees(dec_rad)
            
            # RA should be 0-360, Dec should be -90 to +90
            assert np.all((ra_deg >= 0) & (ra_deg <= 360)), "RA out of range"
            assert np.all((dec_deg >= -90) & (dec_deg <= 90)), "Dec out of range"


class TestCASACompatibility:
    """Verify MS can be used with CASA tasks."""

    def test_casatools_can_open(self, synthetic_ms: Path):
        """Contract: MS must be openable by casatools."""
        try:
            from casatools import table as tb_tool
        except ImportError:
            pytest.skip("casatools not available")
        
        tb = tb_tool()
        try:
            success = tb.open(str(synthetic_ms))
            assert success, "casatools.table failed to open MS"
            
            # Basic sanity check
            nrows = tb.nrows()
            assert nrows > 0, "casatools sees empty table"
        finally:
            tb.close()

    def test_msmetadata_can_summarize(self, synthetic_ms: Path):
        """Contract: MS must be readable by msmetadata."""
        try:
            from casatools import msmetadata as msmd_tool
        except ImportError:
            pytest.skip("casatools not available")
        
        msmd = msmd_tool()
        try:
            msmd.open(str(synthetic_ms))
            
            # These should not raise
            nants = msmd.nantennas()
            nspw = msmd.nspw()
            nfields = msmd.nfields()
            
            assert nants > 0, "No antennas found"
            assert nspw > 0, "No spectral windows found"
            assert nfields > 0, "No fields found"
        finally:
            msmd.close()
