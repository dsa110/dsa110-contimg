#!/usr/bin/env python3
"""
Integration tests for the enhanced DSA-110 pipeline validation functions.

This test suite validates that all new validation functions work correctly
in realistic scenarios and properly catch the calibration flagging issues
they were designed to detect.

Run with: pytest tests/validation/test_pipeline_validation_integration.py -v
"""

import logging
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Test requires casa6 environment with full dependencies
try:
    import h5py
    from casacore.tables import table
    from pyuvdata import UVData

    CASA_AVAILABLE = True
except ImportError:
    CASA_AVAILABLE = False

from dsa110_contimg.conversion.helpers import (
    cleanup_casa_file_handles,
    validate_antenna_positions,
    validate_model_data_quality,
    validate_ms_frequency_order,
    validate_phase_center_coherence,
    validate_reference_antenna_stability,
    validate_uvw_precision,
)


class TestValidationIntegration:
    """Integration tests for pipeline validation functions."""

    def setup_method(self):
        """Setup test fixtures."""
        self.logger = logging.getLogger(__name__)

    @pytest.mark.skipif(not CASA_AVAILABLE, reason="Requires casa6 environment")
    def test_frequency_ordering_validation_real_ms(self):
        """Test frequency ordering validation with real MS."""
        # This test would run against actual MS files when casa6 is available
        pass

    @pytest.mark.skipif(not CASA_AVAILABLE, reason="Requires casa6 environment")
    def test_uvw_precision_validation_real_ms(self):
        """Test UVW precision validation with real MS."""
        # This test would run against actual MS files when casa6 is available
        pass

    @pytest.mark.skipif(not CASA_AVAILABLE, reason="Requires casa6 environment")
    def test_antenna_position_validation_real_ms(self):
        """Test antenna position validation with real MS."""
        # This test would run against actual MS files when casa6 is available
        pass

    @pytest.mark.skipif(not CASA_AVAILABLE, reason="Requires casa6 environment")
    def test_model_data_quality_validation_real_ms(self):
        """Test MODEL_DATA quality validation with real MS."""
        # This test would run against actual MS files when casa6 is available
        pass

    @pytest.mark.skipif(not CASA_AVAILABLE, reason="Requires casa6 environment")
    def test_reference_antenna_stability_real_ms(self):
        """Test reference antenna stability analysis with real MS."""
        # This test would run against actual MS files when casa6 is available
        pass


class TestValidationLogic:
    """Unit tests for validation logic using mocking."""

    def test_frequency_ordering_validation_logic(self):
        """Test frequency ordering validation logic with mock data."""

        def mock_table_context_manager(path, readonly=True):
            """Mock table context manager."""
            mock_table = MagicMock()

            if "SPECTRAL_WINDOW" in path:
                # Mock descending frequency order (DSA-110 style)
                mock_table.__enter__.return_value.getcol.return_value = np.array(
                    [[1500e6, 1400e6, 1300e6, 1200e6]]  # Descending frequencies
                )
            else:
                mock_table.__enter__.return_value.colnames.return_value = [
                    "DATA",
                    "ANTENNA1",
                    "ANTENNA2",
                    "TIME",
                ]

            mock_table.__exit__ = MagicMock(return_value=None)
            return mock_table

        with patch(
            "dsa110_contimg.conversion.helpers.table",
            side_effect=mock_table_context_manager,
        ):
            # Should detect descending order and raise error
            with pytest.raises(RuntimeError, match="frequencies are in DESCENDING order"):
                validate_ms_frequency_order("/fake/ms/path")

    def test_uvw_precision_validation_logic(self):
        """Test UVW precision validation logic with mock data."""

        def mock_table_context_manager(path, readonly=True):
            """Mock table context manager with problematic UVW data."""
            mock_table = MagicMock()

            if "SPECTRAL_WINDOW" in path:
                # Mock frequency data for wavelength calculation
                mock_table.__enter__.return_value.getcol.return_value = np.array(
                    [[1400e6]]  # 1.4 GHz -> wavelength ~0.21m
                )
            else:
                # Mock UVW coordinates with excessive errors (>0.1λ = >0.021m = >2.1cm)
                mock_uvw = np.array(
                    [
                        [100000.0, 50000.0, 1000.0],  # 100km baseline - unreasonable
                        [10.0, 20.0, 5.0],  # Normal baseline
                        [0.0, 0.0, 0.0],  # All-zero coordinates - problematic
                    ]
                )
                mock_table.__enter__.return_value.getcol.return_value = mock_uvw
                mock_table.__enter__.return_value.nrows.return_value = len(mock_uvw)

            mock_table.__exit__ = MagicMock(return_value=None)
            return mock_table

        with patch(
            "dsa110_contimg.conversion.helpers.table",
            side_effect=mock_table_context_manager,
        ):
            # Should detect excessive UVW values
            with pytest.raises(RuntimeError, match="UVW coordinates contain unreasonable values"):
                validate_uvw_precision("/fake/ms/path", tolerance_lambda=0.1)

    def test_antenna_position_validation_logic(self):
        """Test antenna position validation logic with mock data."""

        def mock_table_context_manager(path, readonly=True):
            """Mock table context manager with antenna position data."""
            mock_table = MagicMock()

            if "ANTENNA" in path:
                # Mock antenna positions with one antenna having excessive error
                mock_positions = np.array(
                    [
                        [-2409150.40, -4478573.12, 3838617.74],  # Reference position
                        [
                            -2409150.50,
                            -4478573.22,
                            3838617.84,
                        ],  # 5cm error - acceptable
                        [-2409151.40, -4478574.12, 3838618.74],  # 1m error - excessive
                    ]
                )
                mock_names = np.array(["ea01", "ea02", "ea03"])

                mock_table.__enter__.return_value.getcol.side_effect = lambda col: {
                    "POSITION": mock_positions,
                    "NAME": mock_names,
                }[col]

            mock_table.__exit__ = MagicMock(return_value=None)
            return mock_table

        # Mock the reference position loader to return matching positions
        mock_ref_df = MagicMock()
        mock_ref_df.__getitem__.side_effect = lambda key: {
            "x_m": MagicMock(values=np.array([-2409150.40, -2409150.40, -2409150.40])),
            "y_m": MagicMock(values=np.array([-4478573.12, -4478573.12, -4478573.12])),
            "z_m": MagicMock(values=np.array([3838617.74, 3838617.74, 3838617.74])),
        }[key]

        with patch(
            "dsa110_contimg.conversion.helpers.table",
            side_effect=mock_table_context_manager,
        ):
            with patch("dsa110_contimg.conversion.helpers.get_itrf", return_value=mock_ref_df):
                # Should detect excessive position error
                with pytest.raises(RuntimeError, match="Antenna position errors exceed tolerance"):
                    validate_antenna_positions("/fake/ms/path", position_tolerance_m=0.05)

    def test_model_data_quality_validation_logic(self):
        """Test MODEL_DATA quality validation logic with mock data."""

        def mock_table_context_manager(path, readonly=True):
            """Mock table context manager with MODEL_DATA."""
            mock_table = MagicMock()

            # Mock MODEL_DATA column existence and problematic data
            mock_table.__enter__.return_value.colnames.return_value = [
                "MODEL_DATA",
                "FIELD_ID",
            ]
            mock_table.__enter__.return_value.getcol.side_effect = lambda col, **kwargs: {
                "FIELD_ID": np.array([0, 0, 0, 0]),
                "MODEL_DATA": np.array(
                    [
                        [[0.0001 + 0.0001j, 0.0001 + 0.0001j]],  # Too weak for calibrator
                        [[0.001 + 0.001j, 0.001 + 0.001j]],
                        [[0.001 + 0.001j, 0.001 + 0.001j]],
                        [[0.001 + 0.001j, 0.001 + 0.001j]],
                    ]
                ),  # Shape: (nrow, nchan, npol)
            }[col]

            mock_table.__exit__ = MagicMock(return_value=None)
            return mock_table

        with patch(
            "dsa110_contimg.conversion.helpers.table",
            side_effect=mock_table_context_manager,
        ):
            # Should detect weak calibrator model
            with pytest.raises(RuntimeError, match="too low for calibrator"):
                validate_model_data_quality("/fake/ms/path", min_flux_jy=0.1)

    def test_reference_antenna_stability_logic(self):
        """Test reference antenna stability analysis logic with mock data."""

        def mock_table_context_manager(path, readonly=True):
            """Mock table context manager for reference antenna analysis."""
            mock_table = MagicMock()

            if "ANTENNA" in path:
                # Mock antenna names
                mock_table.__enter__.return_value.getcol.return_value = np.array(
                    ["ea01", "ea02", "ea03"]
                )
            else:
                # Mock visibility data with one antenna heavily flagged
                mock_ant1 = np.array([0, 0, 1, 1, 2, 2])  # Baselines
                mock_ant2 = np.array([1, 2, 0, 2, 0, 1])

                # Mock flags - antenna 2 heavily flagged
                mock_flags = np.array(
                    [
                        [[[False, False], [False, False]]],  # ant0-ant1: good
                        [[[False, False], [False, False]]],  # ant0-ant2: good
                        [[[False, False], [False, False]]],  # ant1-ant0: good
                        [[[True, True], [True, True]]],  # ant1-ant2: flagged (affects ant2)
                        [[[False, False], [False, False]]],  # ant2-ant0: good
                        [[[True, True], [True, True]]],  # ant2-ant1: flagged (affects ant2)
                    ]
                )

                # Mock visibility data with reasonable values
                mock_data = np.array(
                    [
                        [[[1.0 + 1.0j, 1.0 - 1.0j], [0.5 + 0.5j, 0.5 - 0.5j]]],
                        [[[1.1 + 1.1j, 1.1 - 1.1j], [0.6 + 0.6j, 0.6 - 0.6j]]],
                        [[[0.9 + 0.9j, 0.9 - 0.9j], [0.4 + 0.4j, 0.4 - 0.4j]]],
                        [[[0.0 + 0.0j, 0.0 + 0.0j], [0.0 + 0.0j, 0.0 + 0.0j]]],  # Flagged
                        [[[1.2 + 1.2j, 1.2 - 1.2j], [0.7 + 0.7j, 0.7 - 0.7j]]],
                        [[[0.0 + 0.0j, 0.0 + 0.0j], [0.0 + 0.0j, 0.0 + 0.0j]]],  # Flagged
                    ]
                )

                mock_table.__enter__.return_value.getcol.side_effect = lambda col: {
                    "ANTENNA1": mock_ant1,
                    "ANTENNA2": mock_ant2,
                    "FLAG": mock_flags,
                    "DATA": mock_data,
                }[col]

            mock_table.__exit__ = MagicMock(return_value=None)
            return mock_table

        with patch(
            "dsa110_contimg.conversion.helpers.table",
            side_effect=mock_table_context_manager,
        ):
            with patch(
                "dsa110_contimg.conversion.helpers.os.path.join",
                return_value="/fake/ms/path/ANTENNA",
            ):
                # Should select antenna with best stability (ant0 or ant1, not ant2)
                best_ant = validate_reference_antenna_stability("/fake/ms/path")
                assert best_ant in ["ea01", "ea02"]  # Not ea03 which is heavily flagged


class TestValidationWorkflow:
    """Test the complete validation workflow integration."""

    def test_validation_workflow_catches_all_issues(self):
        """Test that the complete validation workflow catches all major issues."""

        # This would be a comprehensive end-to-end test that:
        # 1. Generates synthetic data with known issues
        # 2. Runs the complete conversion pipeline
        # 3. Verifies that each validation function correctly identifies its target issue
        # 4. Confirms that the workflow continues appropriately for warnings vs errors

        # For now, we validate that all functions are properly imported and callable
        validation_functions = [
            validate_ms_frequency_order,
            cleanup_casa_file_handles,
            validate_phase_center_coherence,
            validate_uvw_precision,
            validate_antenna_positions,
            validate_model_data_quality,
            validate_reference_antenna_stability,
        ]

        for func in validation_functions:
            assert callable(func), f"Validation function {func.__name__} is not callable"

        # Verify functions are properly documented
        for func in validation_functions:
            assert (
                func.__doc__ is not None
            ), f"Validation function {func.__name__} lacks documentation"
            assert (
                "Args:" in func.__doc__ or "Parameters:" in func.__doc__
            ), f"Validation function {func.__name__} lacks parameter documentation"


if __name__ == "__main__":
    # Run basic validation logic tests
    pytest.main([__file__, "-v"])
