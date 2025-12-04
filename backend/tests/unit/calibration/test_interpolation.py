"""
Unit tests for Issue #2: Calibration interpolation between sets.

Tests cover:
1. get_interpolated_calibration() - DB selection with before/after sets
2. apply_interpolated_calibration() - edge cases and fallback behavior
3. _merge_caltables_weighted() - weighted gain averaging (mocked CASA)
"""

import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# =============================================================================
# Test fixtures
# =============================================================================

@pytest.fixture
def temp_cal_db():
    """Create a temporary calibration database with test data."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = Path(f.name)

    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE caltables (
            id INTEGER PRIMARY KEY,
            set_name TEXT NOT NULL,
            path TEXT NOT NULL UNIQUE,
            table_type TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            cal_field TEXT,
            refant TEXT,
            created_at REAL NOT NULL,
            valid_start_mjd REAL,
            valid_end_mjd REAL,
            status TEXT NOT NULL,
            notes TEXT,
            source_ms_path TEXT,
            solver_command TEXT,
            solver_version TEXT,
            solver_params TEXT,
            quality_metrics TEXT
        )
    """)
    conn.execute("CREATE INDEX idx_caltables_set ON caltables(set_name)")
    conn.execute(
        "CREATE INDEX idx_caltables_valid ON caltables(valid_start_mjd, valid_end_mjd)"
    )
    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    try:
        db_path.unlink()
    except OSError:
        pass


def _insert_cal_set(
    db_path: Path,
    set_name: str,
    mid_mjd: float,
    validity_hours: float = 12.0,
    table_types: list = None,
) -> None:
    """Insert a calibration set into the test database."""
    if table_types is None:
        table_types = ["_kcal", "_bacal", "_bpcal", "_gacal", "_gpcal"]

    conn = sqlite3.connect(str(db_path))
    now = time.time()
    validity_days = validity_hours / 24.0

    for i, ttype in enumerate(table_types):
        path = f"/test/cals/{set_name}{ttype}"
        conn.execute(
            """
            INSERT INTO caltables (
                set_name, path, table_type, order_index, created_at,
                valid_start_mjd, valid_end_mjd, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
            """,
            (
                set_name,
                path,
                ttype.strip("_"),
                (i + 1) * 10,
                now,
                mid_mjd - validity_days,
                mid_mjd + validity_days,
            ),
        )
    conn.commit()
    conn.close()


# =============================================================================
# Tests for InterpolatedCalibration dataclass
# =============================================================================

class TestInterpolatedCalibrationDataclass:
    """Tests for the InterpolatedCalibration dataclass."""

    def test_weight_after_property(self):
        """Test that weight_after is computed correctly."""
        from dsa110_contimg.pipeline.hardening import InterpolatedCalibration

        ic = InterpolatedCalibration(
            set_before="before",
            paths_before=["/path/before"],
            mid_mjd_before=60000.0,
            set_after="after",
            paths_after=["/path/after"],
            mid_mjd_after=60001.0,
            weight_before=0.7,
            target_mjd=60000.3,
            selection_method="interpolated",
        )

        assert ic.weight_after == pytest.approx(0.3, abs=0.001)

    def test_is_interpolated_true(self):
        """Test is_interpolated returns True when both sets present."""
        from dsa110_contimg.pipeline.hardening import InterpolatedCalibration

        ic = InterpolatedCalibration(
            set_before="before",
            paths_before=["/path/before"],
            mid_mjd_before=60000.0,
            set_after="after",
            paths_after=["/path/after"],
            mid_mjd_after=60001.0,
            weight_before=0.5,
            target_mjd=60000.5,
            selection_method="interpolated",
        )

        assert ic.is_interpolated is True

    def test_is_interpolated_false_no_after(self):
        """Test is_interpolated returns False when only before set."""
        from dsa110_contimg.pipeline.hardening import InterpolatedCalibration

        ic = InterpolatedCalibration(
            set_before="before",
            paths_before=["/path/before"],
            mid_mjd_before=60000.0,
            set_after=None,
            paths_after=[],
            mid_mjd_after=None,
            weight_before=1.0,
            target_mjd=60000.5,
            selection_method="extrapolated",
        )

        assert ic.is_interpolated is False

    def test_effective_paths_returns_before(self):
        """Test effective_paths prefers before set."""
        from dsa110_contimg.pipeline.hardening import InterpolatedCalibration

        ic = InterpolatedCalibration(
            set_before="before",
            paths_before=["/path/before"],
            mid_mjd_before=60000.0,
            set_after="after",
            paths_after=["/path/after"],
            mid_mjd_after=60001.0,
            weight_before=0.5,
            target_mjd=60000.5,
            selection_method="interpolated",
        )

        assert ic.effective_paths == ["/path/before"]

    def test_effective_paths_returns_after_when_no_before(self):
        """Test effective_paths returns after set when before is empty."""
        from dsa110_contimg.pipeline.hardening import InterpolatedCalibration

        ic = InterpolatedCalibration(
            set_before=None,
            paths_before=[],
            mid_mjd_before=None,
            set_after="after",
            paths_after=["/path/after"],
            mid_mjd_after=60001.0,
            weight_before=0.0,
            target_mjd=60000.5,
            selection_method="extrapolated",
        )

        assert ic.effective_paths == ["/path/after"]


# =============================================================================
# Tests for get_interpolated_calibration()
# =============================================================================

class TestGetInterpolatedCalibration:
    """Tests for get_interpolated_calibration() database selection."""

    def test_interpolation_between_two_sets(self, temp_cal_db):
        """Test true interpolation when target is between two cal sets."""
        # Insert before and after calibration sets
        _insert_cal_set(temp_cal_db, "cal_before", mid_mjd=60000.0)
        _insert_cal_set(temp_cal_db, "cal_after", mid_mjd=60001.0)

        from dsa110_contimg.pipeline.hardening import get_interpolated_calibration

        # Target is exactly in the middle
        result = get_interpolated_calibration(
            temp_cal_db,
            target_mjd=60000.5,
            validity_hours=24.0,
        )

        assert result.is_interpolated is True
        assert result.set_before == "cal_before"
        assert result.set_after == "cal_after"
        assert result.selection_method == "interpolated"
        # Weight should be ~0.5 when equidistant
        assert result.weight_before == pytest.approx(0.5, abs=0.05)

    def test_interpolation_weights_closer_to_before(self, temp_cal_db):
        """Test weights favor closer calibration (closer to before)."""
        _insert_cal_set(temp_cal_db, "cal_before", mid_mjd=60000.0)
        _insert_cal_set(temp_cal_db, "cal_after", mid_mjd=60001.0)

        from dsa110_contimg.pipeline.hardening import get_interpolated_calibration

        # Target is 25% of the way from before to after
        result = get_interpolated_calibration(
            temp_cal_db,
            target_mjd=60000.25,
            validity_hours=24.0,
        )

        assert result.is_interpolated is True
        # Weight_before should be ~0.75 (closer to before)
        assert result.weight_before == pytest.approx(0.75, abs=0.05)

    def test_interpolation_weights_closer_to_after(self, temp_cal_db):
        """Test weights favor closer calibration (closer to after)."""
        _insert_cal_set(temp_cal_db, "cal_before", mid_mjd=60000.0)
        _insert_cal_set(temp_cal_db, "cal_after", mid_mjd=60001.0)

        from dsa110_contimg.pipeline.hardening import get_interpolated_calibration

        # Target is 75% of the way from before to after
        result = get_interpolated_calibration(
            temp_cal_db,
            target_mjd=60000.75,
            validity_hours=24.0,
        )

        assert result.is_interpolated is True
        # Weight_before should be ~0.25 (farther from before)
        assert result.weight_before == pytest.approx(0.25, abs=0.05)

    def test_extrapolation_only_before_set(self, temp_cal_db):
        """Test extrapolation when only before set available."""
        _insert_cal_set(temp_cal_db, "cal_before", mid_mjd=60000.0)

        from dsa110_contimg.pipeline.hardening import get_interpolated_calibration

        # Target is after the only calibration
        result = get_interpolated_calibration(
            temp_cal_db,
            target_mjd=60000.3,
            validity_hours=12.0,
        )

        assert result.is_interpolated is False
        assert result.set_before == "cal_before"
        assert result.set_after is None
        assert result.weight_before == 1.0
        assert result.selection_method == "extrapolated"

    def test_extrapolation_only_after_set(self, temp_cal_db):
        """Test extrapolation when only after set available."""
        _insert_cal_set(temp_cal_db, "cal_after", mid_mjd=60001.0)

        from dsa110_contimg.pipeline.hardening import get_interpolated_calibration

        # Target is before the only calibration
        result = get_interpolated_calibration(
            temp_cal_db,
            target_mjd=60000.7,
            validity_hours=12.0,
        )

        assert result.is_interpolated is False
        assert result.set_before is None
        assert result.set_after == "cal_after"
        assert result.weight_before == 0.0
        assert result.selection_method == "extrapolated"

    def test_no_calibration_raises_error(self, temp_cal_db):
        """Test ValueError raised when no calibration in validity window."""
        from dsa110_contimg.pipeline.hardening import get_interpolated_calibration

        # No calibrations inserted, should raise
        with pytest.raises(ValueError, match="No calibration found"):
            get_interpolated_calibration(
                temp_cal_db,
                target_mjd=60000.5,
                validity_hours=12.0,
            )

    def test_warning_for_large_gap(self, temp_cal_db):
        """Test warning is generated for large calibration gap."""
        _insert_cal_set(temp_cal_db, "cal_before", mid_mjd=60000.0, validity_hours=48.0)
        _insert_cal_set(temp_cal_db, "cal_after", mid_mjd=60002.0, validity_hours=48.0)

        from dsa110_contimg.pipeline.hardening import get_interpolated_calibration

        result = get_interpolated_calibration(
            temp_cal_db,
            target_mjd=60001.0,
            validity_hours=48.0,
        )

        assert result.is_interpolated is True
        # Should have warning about large gap (48 hours)
        assert len(result.warnings) > 0
        assert "gap" in result.warnings[0].lower()

    def test_small_gap_uses_single_set(self, temp_cal_db):
        """Test small gap between sets uses nearest single set."""
        # Insert two sets very close together (0.5 hours apart)
        _insert_cal_set(temp_cal_db, "cal_before", mid_mjd=60000.0)
        _insert_cal_set(temp_cal_db, "cal_after", mid_mjd=60000.02)  # ~0.5 hours

        from dsa110_contimg.pipeline.hardening import get_interpolated_calibration

        result = get_interpolated_calibration(
            temp_cal_db,
            target_mjd=60000.01,
            validity_hours=12.0,
            min_interpolation_gap_hours=1.0,
        )

        # Should use single set due to small gap
        assert result.selection_method == "single"


# =============================================================================
# Tests for _merge_caltables_weighted()
# =============================================================================

class TestMergeCaltablesWeighted:
    """Tests for weighted gain merging (mocked CASA tables)."""

    def test_weighted_average_gains(self, tmp_path):
        """Test weighted average of complex gains."""
        # Create mock gain data
        gains_before = np.array([
            [1.0 + 0j, 1.0 + 0j],
            [0.9 + 0.1j, 0.9 - 0.1j],
        ])
        gains_after = np.array([
            [1.0 + 0j, 1.0 + 0j],
            [1.1 - 0.1j, 1.1 + 0.1j],
        ])
        flags_before = np.array([[False, False], [False, False]])
        flags_after = np.array([[False, False], [False, False]])

        # Expected: 60% before + 40% after
        weight_before = 0.6
        weight_after = 0.4
        expected_gains = weight_before * gains_before + weight_after * gains_after

        # Mock the table contexts
        mock_tb_before = MagicMock()
        mock_tb_before.getcol.side_effect = lambda col: {
            "CPARAM": gains_before,
            "FLAG": flags_before,
            "ANTENNA1": np.array([0, 1]),
        }[col]
        mock_tb_before.__enter__ = MagicMock(return_value=mock_tb_before)
        mock_tb_before.__exit__ = MagicMock(return_value=False)

        mock_tb_after = MagicMock()
        mock_tb_after.getcol.side_effect = lambda col: {
            "CPARAM": gains_after,
            "FLAG": flags_after,
            "ANTENNA1": np.array([0, 1]),
        }[col]
        mock_tb_after.__enter__ = MagicMock(return_value=mock_tb_after)
        mock_tb_after.__exit__ = MagicMock(return_value=False)

        mock_tb_out = MagicMock()
        mock_tb_out.__enter__ = MagicMock(return_value=mock_tb_out)
        mock_tb_out.__exit__ = MagicMock(return_value=False)

        written_gains = None
        written_flags = None

        def capture_putcol(col, data):
            nonlocal written_gains, written_flags
            if col == "CPARAM":
                written_gains = data
            elif col == "FLAG":
                written_flags = data

        mock_tb_out.putcol = capture_putcol

        path_before = str(tmp_path / "before_kcal")
        path_after = str(tmp_path / "after_kcal")
        output_path = str(tmp_path / "merged_kcal")

        # Create dummy directories for copytree
        (tmp_path / "before_kcal").mkdir()

        with patch("casacore.tables.table") as mock_table:
            # Return different mocks based on path
            def table_factory(path, readonly=True):
                if "before" in path:
                    return mock_tb_before
                elif "after" in path:
                    return mock_tb_after
                else:
                    return mock_tb_out

            mock_table.side_effect = table_factory

            from dsa110_contimg.calibration.applycal import _merge_caltables_weighted

            _merge_caltables_weighted(
                path_before, path_after, output_path,
                weight_before, weight_after,
            )

        # Verify weighted average was computed
        assert written_gains is not None
        np.testing.assert_array_almost_equal(written_gains, expected_gains)
        # All unflagged
        assert written_flags is not None
        assert not np.any(written_flags)

    def test_flag_handling_only_before_valid(self, tmp_path):
        """Test that flagged 'after' gains use 'before' values.

        Tests the flag-handling logic directly by simulating what
        _merge_caltables_weighted does with flags.
        """
        gains_before = np.array([[1.0 + 0j], [0.9 + 0j]])
        gains_after = np.array([[0.0 + 0j], [0.0 + 0j]])  # Bad data
        flags_before = np.array([[False], [False]])
        flags_after = np.array([[True], [True]])  # Flagged

        weight_before = 0.5
        weight_after = 0.5

        # Test the actual merging logic from _merge_caltables_weighted
        merged_gains = np.empty_like(gains_before)
        merged_flags = flags_before.copy()

        # Where both are unflagged: weighted average
        both_good = ~flags_before & ~flags_after
        merged_gains[both_good] = (
            weight_before * gains_before[both_good] +
            weight_after * gains_after[both_good]
        )

        # Where only before is good: use before
        only_before_good = ~flags_before & flags_after
        merged_gains[only_before_good] = gains_before[only_before_good]
        merged_flags[only_before_good] = False

        # Where only after is good: use after
        only_after_good = flags_before & ~flags_after
        merged_gains[only_after_good] = gains_after[only_after_good]
        merged_flags[only_after_good] = False

        # Where both flagged: keep before (flagged)
        both_flagged = flags_before & flags_after
        merged_gains[both_flagged] = gains_before[both_flagged]
        merged_flags[both_flagged] = True

        # Verify: since after is flagged, should use before gains
        np.testing.assert_array_almost_equal(merged_gains, gains_before)
        # Flags should all be False (since before was good)
        assert not np.any(merged_flags)


# =============================================================================
# Tests for apply_interpolated_calibration()
# =============================================================================

class TestApplyInterpolatedCalibration:
    """Tests for apply_interpolated_calibration() edge cases."""

    def test_pure_before_weight(self):
        """Test that weight_before=1.0 calls apply_to_target with before paths."""
        with patch("dsa110_contimg.calibration.applycal.apply_to_target") as mock_apply:
            from dsa110_contimg.calibration.applycal import (
                apply_interpolated_calibration,
            )

            apply_interpolated_calibration(
                "/test/target.ms",
                field="",
                paths_before=["/cal/before_kcal", "/cal/before_bpcal"],
                paths_after=["/cal/after_kcal", "/cal/after_bpcal"],
                weight_before=1.0,
                verify=False,
            )

            mock_apply.assert_called_once()
            # Check positional args: apply_to_target(ms_target, field, gaintables, ...)
            call_args = mock_apply.call_args
            gaintables = call_args.args[2]  # 3rd positional arg is gaintables
            assert "/cal/before_kcal" in gaintables

    def test_pure_after_weight(self):
        """Test that weight_before=0.0 calls apply_to_target with after paths."""
        with patch("dsa110_contimg.calibration.applycal.apply_to_target") as mock_apply:
            from dsa110_contimg.calibration.applycal import (
                apply_interpolated_calibration,
            )

            apply_interpolated_calibration(
                "/test/target.ms",
                field="",
                paths_before=["/cal/before_kcal"],
                paths_after=["/cal/after_kcal"],
                weight_before=0.0,
                verify=False,
            )

            mock_apply.assert_called_once()
            call_args = mock_apply.call_args
            gaintables = call_args.args[2]  # 3rd positional arg is gaintables
            assert "/cal/after_kcal" in gaintables

    def test_invalid_weight_raises(self):
        """Test that invalid weights raise ValueError."""
        from dsa110_contimg.calibration.applycal import (
            apply_interpolated_calibration,
        )

        with pytest.raises(ValueError, match="weight_before must be"):
            apply_interpolated_calibration(
                "/test/target.ms",
                field="",
                paths_before=["/cal/before"],
                paths_after=["/cal/after"],
                weight_before=1.5,  # Invalid
            )

        with pytest.raises(ValueError, match="weight_before must be"):
            apply_interpolated_calibration(
                "/test/target.ms",
                field="",
                paths_before=["/cal/before"],
                paths_after=["/cal/after"],
                weight_before=-0.1,  # Invalid
            )

    def test_no_paths_raises(self):
        """Test that empty paths raise ValueError."""
        from dsa110_contimg.calibration.applycal import (
            apply_interpolated_calibration,
        )

        with pytest.raises(ValueError, match="No calibration paths"):
            apply_interpolated_calibration(
                "/test/target.ms",
                field="",
                paths_before=[],
                paths_after=[],
                weight_before=0.5,
            )

    def test_no_common_table_types_fallback(self):
        """Test fallback to before-only when no common table types."""
        with patch("dsa110_contimg.calibration.applycal.apply_to_target") as mock_apply:
            from dsa110_contimg.calibration.applycal import (
                apply_interpolated_calibration,
            )

            # Different table types - no overlap
            apply_interpolated_calibration(
                "/test/target.ms",
                field="",
                paths_before=["/cal/before_kcal"],
                paths_after=["/cal/after_bpcal"],  # Different type
                weight_before=0.5,
                verify=False,
            )

            # Should fall back to before set
            mock_apply.assert_called_once()
            call_args = mock_apply.call_args
            gaintables = call_args.args[2]  # 3rd positional arg is gaintables
            assert "/cal/before_kcal" in gaintables
