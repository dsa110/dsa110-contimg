# -*- coding: utf-8 -*-
"""
Tests for field naming utilities.
"""

from unittest.mock import MagicMock, call, patch

import numpy as np
import pytest


@pytest.fixture
def mock_casacore():
    """Mock casacore.tables module - import happens inside function."""
    # We need to mock at the import level, not at module attribute level
    with patch("casacore.tables") as mock:
        mock_table = MagicMock()
        mock.table = mock_table
        yield mock_table


def test_rename_calibrator_field_basic(mock_casacore, tmp_path):
    """Test basic field renaming with time suffix."""
    from dsa110_contimg.calibration.field_naming import rename_calibrator_field

    # Setup mock FIELD table
    ms_path = str(tmp_path / "test.ms")
    mock_field_tb = MagicMock()
    mock_field_names = ["meridian_icrs_t0", "meridian_icrs_t1", "meridian_icrs_t2"]
    mock_field_tb.getcol.return_value = mock_field_names.copy()
    mock_casacore.return_value.__enter__.return_value = mock_field_tb

    # Rename field 1 to "3C286_t1"
    rename_calibrator_field(ms_path, "3C286", 1, include_time_suffix=True)

    # Verify table opened with readonly=False
    mock_casacore.assert_called_once_with(f"{ms_path}::FIELD", readonly=False)

    # Verify getcol called
    mock_field_tb.getcol.assert_called_once_with("NAME")

    # Verify field name updated
    expected_names = ["meridian_icrs_t0", "3C286_t1", "meridian_icrs_t2"]
    mock_field_tb.putcol.assert_called_once_with("NAME", expected_names)


def test_rename_calibrator_field_no_suffix(mock_casacore, tmp_path):
    """Test field renaming without time suffix."""
    from dsa110_contimg.calibration.field_naming import rename_calibrator_field

    ms_path = str(tmp_path / "test.ms")
    mock_field_tb = MagicMock()
    mock_field_names = ["meridian_icrs_t0", "meridian_icrs_t1"]
    mock_field_tb.getcol.return_value = mock_field_names.copy()
    mock_casacore.return_value.__enter__.return_value = mock_field_tb

    # Rename field 0 to just "J1331+3030" (no time suffix)
    rename_calibrator_field(ms_path, "J1331+3030", 0, include_time_suffix=False)

    # Verify field name updated without suffix
    expected_names = ["J1331+3030", "meridian_icrs_t1"]
    mock_field_tb.putcol.assert_called_once_with("NAME", expected_names)


def test_rename_calibrator_field_out_of_range(mock_casacore, tmp_path, caplog):
    """Test field renaming with invalid field index."""
    from dsa110_contimg.calibration.field_naming import rename_calibrator_field

    ms_path = str(tmp_path / "test.ms")
    mock_field_tb = MagicMock()
    mock_field_names = ["meridian_icrs_t0", "meridian_icrs_t1"]
    mock_field_tb.getcol.return_value = mock_field_names
    mock_casacore.return_value.__enter__.return_value = mock_field_tb

    # Try to rename field 5 (out of range)
    rename_calibrator_field(ms_path, "3C286", 5)

    # Verify putcol NOT called (field index invalid)
    mock_field_tb.putcol.assert_not_called()

    # Verify warning logged
    assert "out of range" in caplog.text.lower()


def test_rename_calibrator_fields_from_catalog_success(tmp_path):
    """Test auto-detection and renaming from catalog."""
    from dsa110_contimg.calibration.field_naming import (
        rename_calibrator_fields_from_catalog,
    )

    ms_path = str(tmp_path / "test.ms")

    # Mock select_bandpass_from_catalog to return known calibrator
    mock_select = MagicMock(
        return_value=(
            "17",  # field_sel_str
            [17],  # indices
            np.array([0.1, 0.2, 0.5]),  # wflux
            ("3C286", 202.78, 30.51, 7.5),  # cal_info
            17,  # peak_field
        )
    )

    # Mock rename_calibrator_field
    mock_rename = MagicMock()

    # Patch the imported function, not the module attribute
    with patch(
        "dsa110_contimg.calibration.selection.select_bandpass_from_catalog",
        mock_select,
    ):
        with patch(
            "dsa110_contimg.calibration.field_naming.rename_calibrator_field",
            mock_rename,
        ):
            result = rename_calibrator_fields_from_catalog(ms_path)

    # Verify result
    assert result is not None
    cal_name, field_idx = result
    assert cal_name == "3C286"
    assert field_idx == 17

    # Verify rename called with correct parameters
    mock_rename.assert_called_once_with(ms_path, "3C286", 17, include_time_suffix=True)


def test_rename_calibrator_fields_from_catalog_no_match(tmp_path, caplog):
    """Test auto-detection when no calibrator found."""
    from dsa110_contimg.calibration.field_naming import (
        rename_calibrator_fields_from_catalog,
    )

    ms_path = str(tmp_path / "test.ms")

    # Mock select_bandpass_from_catalog to raise exception (no calibrator)
    mock_select = MagicMock(side_effect=RuntimeError("No calibrator found"))

    # Patch the imported function, not the module attribute
    with patch(
        "dsa110_contimg.calibration.selection.select_bandpass_from_catalog",
        mock_select,
    ):
        result = rename_calibrator_fields_from_catalog(ms_path)

    # Verify result is None (no calibrator found)
    assert result is None

    # Verify warning logged
    assert "could not auto-detect" in caplog.text.lower()


def test_rename_preserves_time_index_information():
    """Test that time suffix preserves which timestamp contained calibrator."""
    from dsa110_contimg.calibration.field_naming import rename_calibrator_field

    # Mock casacore at import level
    with patch("casacore.tables") as mock_cas:
        mock_tb = MagicMock()
        # Create 24 fields (typical drift-scan)
        mock_field_names = [f"meridian_icrs_t{i}" for i in range(24)]
        mock_tb.getcol.return_value = mock_field_names.copy()
        mock_cas.table.return_value.__enter__.return_value = mock_tb

        # Rename field 17 (calibrator at t=17 * 12.88s = 219 seconds)
        rename_calibrator_field("/tmp/test.ms", "3C286", 17)

        # Verify putcol called with "3C286_t17"
        called_names = mock_tb.putcol.call_args[0][1]
        assert called_names[17] == "3C286_t17"

        # Verify other fields unchanged
        for i in range(24):
            if i != 17:
                assert called_names[i] == f"meridian_icrs_t{i}"
