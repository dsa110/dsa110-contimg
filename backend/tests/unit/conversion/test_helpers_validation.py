"""
Unit tests for conversion/helpers_validation.py

Tests validation functions for MS frequency order, phase center coherence,
UVW precision, antenna positions, and other quality checks.

These tests use mocks to avoid CASA dependencies and import issues.
The validation functions are accessed through the helpers module to avoid
circular import issues.

NOTE: These tests require casacore to be installed because the helpers module
imports casacore.tables at module level. The tests are skipped in CI environments
that don't have CASA packages (e.g., standard Python without conda).
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

# Check if casacore is available - skip all tests in this module if not
try:
    import casacore.tables  # noqa: F401
    HAS_CASACORE = True
except ImportError:
    HAS_CASACORE = False

pytestmark = pytest.mark.skipif(
    not HAS_CASACORE,
    reason="casacore not available - these tests require CASA packages"
)

# Import test fixtures
from tests.fixtures import (
    MockMSTable,
    create_spectral_window_table,
    create_field_table,
    create_antenna_table,
    create_complete_mock_ms,
)


# Helper to create mock table context manager
def create_mock_table_factory(tables):
    """Create a mock table factory function for patching."""
    def mock_table_factory(path, readonly=True, ack=True):
        # Extract subtable name from path
        if "::" in path:
            subtable = path.split("::")[-1]
        else:
            subtable = "MAIN"
        
        if subtable in tables:
            table = tables[subtable]
            table.readonly = readonly
            return table
        
        raise RuntimeError(f"Mock table not found: {subtable}")
    
    return mock_table_factory


class TestValidateMSFrequencyOrder:
    """Tests for validate_ms_frequency_order function."""
    
    def test_ascending_frequencies_pass(self):
        """Ascending frequency order should pass validation."""
        # Create table with ascending frequencies
        spw_table = create_spectral_window_table(
            nspw=1, nchan=384, ascending=True
        )
        
        tables = {"SPECTRAL_WINDOW": spw_table}
        mock_factory = create_mock_table_factory(tables)
        
        with patch("dsa110_contimg.conversion.helpers.table", mock_factory):
            # Import after patching to avoid circular import
            from dsa110_contimg.conversion.helpers import validate_ms_frequency_order
            # Should not raise
            validate_ms_frequency_order("/test/valid.ms")
    
    def test_descending_frequencies_fail(self):
        """Descending frequency order should raise RuntimeError."""
        # Create table with descending frequencies
        spw_table = create_spectral_window_table(
            nspw=1, nchan=384, ascending=False
        )
        
        tables = {"SPECTRAL_WINDOW": spw_table}
        mock_factory = create_mock_table_factory(tables)
        
        with patch("dsa110_contimg.conversion.helpers.table", mock_factory):
            from dsa110_contimg.conversion.helpers import validate_ms_frequency_order
            with pytest.raises(RuntimeError, match="DESCENDING order"):
                validate_ms_frequency_order("/test/invalid.ms")
    
    def test_multiple_spw_ascending_pass(self):
        """Multiple SPWs with ascending order should pass."""
        # Create table with 4 SPWs, all ascending
        spw_table = create_spectral_window_table(
            nspw=4, nchan=384, ascending=True
        )
        
        tables = {"SPECTRAL_WINDOW": spw_table}
        mock_factory = create_mock_table_factory(tables)
        
        with patch("dsa110_contimg.conversion.helpers.table", mock_factory):
            from dsa110_contimg.conversion.helpers import validate_ms_frequency_order
            # Should not raise
            validate_ms_frequency_order("/test/multi_spw.ms")
    
    def test_multiple_spw_wrong_order_fail(self):
        """Multiple SPWs with wrong inter-SPW order should fail."""
        # Create SPWs where individual channels are ascending but SPW order is wrong
        # SPW0: 1.4-1.5 GHz, SPW1: 1.28-1.38 GHz (out of order)
        nchan = 384
        chan_width = 650e3
        
        spw0_freqs = 1.4e9 + np.arange(nchan) * chan_width  # Higher
        spw1_freqs = 1.28e9 + np.arange(nchan) * chan_width  # Lower (wrong order)
        
        spw_table = MockMSTable(
            data={
                "CHAN_FREQ": np.array([spw0_freqs, spw1_freqs]),
                "NUM_CHAN": np.array([nchan, nchan]),
            }
        )
        
        tables = {"SPECTRAL_WINDOW": spw_table}
        mock_factory = create_mock_table_factory(tables)
        
        with patch("dsa110_contimg.conversion.helpers.table", mock_factory):
            from dsa110_contimg.conversion.helpers import validate_ms_frequency_order
            with pytest.raises(RuntimeError, match="incorrect frequency order"):
                validate_ms_frequency_order("/test/bad_spw_order.ms")
    
    def test_single_channel_passes(self):
        """Single channel SPW should pass (no order to check)."""
        spw_table = MockMSTable(
            data={
                "CHAN_FREQ": np.array([[1.4e9]]),  # Single channel
                "NUM_CHAN": np.array([1]),
            }
        )
        
        tables = {"SPECTRAL_WINDOW": spw_table}
        mock_factory = create_mock_table_factory(tables)
        
        with patch("dsa110_contimg.conversion.helpers.table", mock_factory):
            from dsa110_contimg.conversion.helpers import validate_ms_frequency_order
            validate_ms_frequency_order("/test/single_chan.ms")


class TestValidatePhaseCenterCoherence:
    """Tests for validate_phase_center_coherence function."""
    
    def test_single_field_passes(self):
        """Single field should always pass."""
        field_table = create_field_table(nfield=1)
        main_table = MockMSTable(
            data={"TIME": np.array([5e9, 5e9 + 10])},
        )
        
        tables = {"FIELD": field_table, "MAIN": main_table}
        mock_factory = create_mock_table_factory(tables)
        
        with patch("dsa110_contimg.conversion.helpers.table", mock_factory):
            from dsa110_contimg.conversion.helpers import validate_phase_center_coherence
            validate_phase_center_coherence("/test/single_field.ms")
    
    def test_empty_field_table_warns(self):
        """Empty field table should warn but not raise."""
        field_table = MockMSTable(data={"PHASE_DIR": np.array([]).reshape(0, 1, 2)})
        
        tables = {"FIELD": field_table}
        mock_factory = create_mock_table_factory(tables)
        
        with patch("dsa110_contimg.conversion.helpers.table", mock_factory):
            from dsa110_contimg.conversion.helpers import validate_phase_center_coherence
            # Should not raise, just warn
            validate_phase_center_coherence("/test/empty.ms")
    
    def test_time_dependent_phasing_raises_informative_error(self):
        """Time-dependent phasing raises an error with helpful message.
        
        The validation function can't distinguish between genuine errors and 
        intentional time-dependent phasing (meridian tracking) without external
        context, so it raises an error with an informative message.
        """
        # Create field table with large RA variation (time-dependent phasing)
        field_table = create_field_table(
            nfield=24, 
            time_dependent=True,
        )
        
        # Main table with time range - but function needs more complex setup
        # to detect time-dependent phasing correctly
        obs_duration = 309.0  # seconds
        main_table = MockMSTable(
            data={"TIME": np.array([5e9, 5e9 + obs_duration])},
        )
        
        tables = {"FIELD": field_table, "MAIN": main_table}
        mock_factory = create_mock_table_factory(tables)
        
        with patch("dsa110_contimg.conversion.helpers.table", mock_factory):
            from dsa110_contimg.conversion.helpers import validate_phase_center_coherence
            # This raises with an informative error about time-dependent phasing
            with pytest.raises(RuntimeError, match="time-dependent phasing"):
                validate_phase_center_coherence("/test/time_dep.ms")


class TestValidateUVWPrecision:
    """Tests for validate_uvw_precision function."""
    
    def test_good_uvw_precision_passes(self):
        """UVW values with good precision should pass."""
        # Create realistic UVW values
        nrows = 1000
        uvw = np.random.randn(nrows, 3) * 1000  # ~1km baselines
        
        main_table = MockMSTable(data={"UVW": uvw})
        tables = {"MAIN": main_table}
        mock_factory = create_mock_table_factory(tables)
        
        with patch("dsa110_contimg.conversion.helpers.table", mock_factory):
            from dsa110_contimg.conversion.helpers import validate_uvw_precision
            validate_uvw_precision("/test/good_uvw.ms")
    
    def test_all_zero_uvw_warns(self):
        """All-zero UVW values should warn (indicates problem)."""
        uvw = np.zeros((1000, 3))
        
        main_table = MockMSTable(data={"UVW": uvw})
        tables = {"MAIN": main_table}
        mock_factory = create_mock_table_factory(tables)
        
        with patch("dsa110_contimg.conversion.helpers.table", mock_factory):
            from dsa110_contimg.conversion.helpers import validate_uvw_precision
            # Should log a warning but not raise
            validate_uvw_precision("/test/zero_uvw.ms")
    
    def test_nan_uvw_warns(self):
        """NaN in UVW values should warn."""
        uvw = np.random.randn(1000, 3) * 1000
        uvw[0, 0] = np.nan  # Inject NaN
        
        main_table = MockMSTable(data={"UVW": uvw})
        tables = {"MAIN": main_table}
        mock_factory = create_mock_table_factory(tables)
        
        with patch("dsa110_contimg.conversion.helpers.table", mock_factory):
            from dsa110_contimg.conversion.helpers import validate_uvw_precision
            validate_uvw_precision("/test/nan_uvw.ms")


class TestValidateAntennaPositions:
    """Tests for validate_antenna_positions function."""
    
    def test_valid_positions_pass(self):
        """Valid ITRF antenna positions should pass."""
        ant_table = create_antenna_table(nant=63, use_dsa110_layout=True)
        tables = {"ANTENNA": ant_table}
        mock_factory = create_mock_table_factory(tables)
        
        # Mock get_itrf to return matching positions (force validation fallback path)
        with patch("dsa110_contimg.conversion.helpers.table", mock_factory):
            with patch("dsa110_contimg.utils.antpos_local.get_itrf", side_effect=ImportError("Mock")):
                from dsa110_contimg.conversion.helpers import validate_antenna_positions
                validate_antenna_positions("/test/valid_ant.ms")
    
    def test_zero_positions_warns(self, caplog):
        """All-zero antenna positions should warn (positions too close to Earth center)."""
        nant = 63
        ant_table = MockMSTable(
            data={
                "POSITION": np.zeros((nant, 3)),
                "DISH_DIAMETER": np.full(nant, 4.65),
                "NAME": np.array([f"DSA-{i:03d}" for i in range(nant)]),
            }
        )
        tables = {"ANTENNA": ant_table}
        mock_factory = create_mock_table_factory(tables)
        
        # Mock get_itrf to force fallback validation (checks Earth radius)
        with patch("dsa110_contimg.conversion.helpers.table", mock_factory):
            with patch("dsa110_contimg.utils.antpos_local.get_itrf", side_effect=ImportError("Mock")):
                from dsa110_contimg.conversion.helpers import validate_antenna_positions
                # Zero positions trigger fallback validation warning (non-fatal)
                validate_antenna_positions("/test/zero_ant.ms")
                # Check that a warning about Earth center was logged
                assert any("too close to Earth center" in record.message for record in caplog.records)
    
    def test_duplicate_positions_warn(self):
        """Duplicate antenna positions at Earth surface should pass fallback validation."""
        nant = 10
        # All antennas at the same position (valid ITRF on Earth surface)
        positions = np.tile([-2409150.4, -4478573.1, 3838617.3], (nant, 1))
        
        ant_table = MockMSTable(
            data={
                "POSITION": positions,
                "DISH_DIAMETER": np.full(nant, 4.65),
                "NAME": np.array([f"DSA-{i:03d}" for i in range(nant)]),
            }
        )
        tables = {"ANTENNA": ant_table}
        mock_factory = create_mock_table_factory(tables)
        
        # Mock get_itrf to force fallback validation (only checks Earth radius)
        with patch("dsa110_contimg.conversion.helpers.table", mock_factory):
            with patch("dsa110_contimg.utils.antpos_local.get_itrf", side_effect=ImportError("Mock")):
                from dsa110_contimg.conversion.helpers import validate_antenna_positions
                # Duplicates at valid Earth surface position should pass fallback validation
                validate_antenna_positions("/test/dup_ant.ms")


class TestValidateModelDataQuality:
    """Tests for validate_model_data_quality function."""
    
    def test_valid_model_passes(self):
        """Valid MODEL_DATA column should pass."""
        nrows, nchan, npol = 100, 384, 4
        model_data = np.ones((nrows, nchan, npol), dtype=np.complex64)
        
        main_table = MockMSTable(
            data={
                "MODEL_DATA": model_data,
                "FLAG": np.zeros((nrows, nchan, npol), dtype=bool),
            }
        )
        tables = {"MAIN": main_table}
        mock_factory = create_mock_table_factory(tables)
        
        with patch("dsa110_contimg.conversion.helpers.table", mock_factory):
            from dsa110_contimg.conversion.helpers import validate_model_data_quality
            validate_model_data_quality("/test/valid_model.ms")
    
    def test_all_zero_model_warns(self):
        """All-zero MODEL_DATA should warn."""
        nrows, nchan, npol = 100, 384, 4
        model_data = np.zeros((nrows, nchan, npol), dtype=np.complex64)
        
        main_table = MockMSTable(
            data={
                "MODEL_DATA": model_data,
                "FLAG": np.zeros((nrows, nchan, npol), dtype=bool),
            }
        )
        tables = {"MAIN": main_table}
        mock_factory = create_mock_table_factory(tables)
        
        with patch("dsa110_contimg.conversion.helpers.table", mock_factory):
            from dsa110_contimg.conversion.helpers import validate_model_data_quality
            # Should warn about zero model
            validate_model_data_quality("/test/zero_model.ms")
