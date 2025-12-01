"""
Tests for the batch QA extraction module.

Tests QA metric extraction from calibration tables and images,
using mocks for CASA dependencies.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Any, Dict

import pytest
import numpy as np

from dsa110_contimg.api.batch.qa import (
    _calculate_overall_quality,
    _extract_beam_info,
    _assess_image_quality,
)


class TestCalculateOverallQuality:
    """Tests for _calculate_overall_quality function."""

    def test_excellent_quality(self):
        """Test excellent quality determination."""
        qa_metrics = {
            "k_metrics": {"flag_fraction": 0.05},
            "bp_metrics": {"flag_fraction": 0.08},
            "g_metrics": {"flag_fraction": 0.02},
        }
        result = _calculate_overall_quality(qa_metrics)
        
        assert result["overall_quality"] == "excellent"
        assert result["flags_total"] == pytest.approx(0.05, abs=0.01)

    def test_good_quality(self):
        """Test good quality determination."""
        qa_metrics = {
            "k_metrics": {"flag_fraction": 0.2},
            "bp_metrics": {"flag_fraction": 0.25},
        }
        result = _calculate_overall_quality(qa_metrics)
        
        assert result["overall_quality"] == "good"

    def test_marginal_quality(self):
        """Test marginal quality determination."""
        qa_metrics = {
            "bp_metrics": {"flag_fraction": 0.4},
        }
        result = _calculate_overall_quality(qa_metrics)
        
        assert result["overall_quality"] == "marginal"

    def test_poor_quality(self):
        """Test poor quality determination."""
        qa_metrics = {
            "k_metrics": {"flag_fraction": 0.7},
            "bp_metrics": {"flag_fraction": 0.6},
        }
        result = _calculate_overall_quality(qa_metrics)
        
        assert result["overall_quality"] == "poor"

    def test_no_metrics_returns_empty(self):
        """Test empty metrics returns empty result."""
        qa_metrics = {}
        result = _calculate_overall_quality(qa_metrics)
        
        assert result == {}

    def test_none_metrics_ignored(self):
        """Test None metrics are ignored."""
        qa_metrics = {
            "k_metrics": None,  # Should be ignored
            "bp_metrics": {"flag_fraction": 0.05},
        }
        result = _calculate_overall_quality(qa_metrics)
        
        assert result["overall_quality"] == "excellent"

    def test_with_all_table_types(self):
        """Test averaging across all three table types."""
        qa_metrics = {
            "k_metrics": {"flag_fraction": 0.1},
            "bp_metrics": {"flag_fraction": 0.2},
            "g_metrics": {"flag_fraction": 0.3},
        }
        result = _calculate_overall_quality(qa_metrics)
        
        # Average: (0.1 + 0.2 + 0.3) / 3 = 0.2
        assert result["flags_total"] == pytest.approx(0.2, abs=0.01)
        assert result["overall_quality"] == "good"


class TestAssessImageQuality:
    """Tests for _assess_image_quality function."""

    def test_excellent_dynamic_range(self):
        """Test excellent quality with high dynamic range."""
        qa_metrics = {"dynamic_range": 2000}
        result = _assess_image_quality(qa_metrics)
        
        assert result["overall_quality"] == "excellent"

    def test_good_dynamic_range(self):
        """Test good quality with moderate dynamic range."""
        qa_metrics = {"dynamic_range": 500}
        result = _assess_image_quality(qa_metrics)
        
        assert result["overall_quality"] == "good"

    def test_marginal_dynamic_range(self):
        """Test marginal quality with low dynamic range."""
        qa_metrics = {"dynamic_range": 50}
        result = _assess_image_quality(qa_metrics)
        
        assert result["overall_quality"] == "marginal"

    def test_poor_dynamic_range(self):
        """Test poor quality with very low dynamic range."""
        qa_metrics = {"dynamic_range": 5}
        result = _assess_image_quality(qa_metrics)
        
        assert result["overall_quality"] == "poor"

    def test_no_dynamic_range(self):
        """Test no assessment when dynamic_range is missing."""
        qa_metrics = {}
        result = _assess_image_quality(qa_metrics)
        
        assert result == {}

    def test_zero_dynamic_range(self):
        """Test assessment with zero dynamic range."""
        qa_metrics = {"dynamic_range": 0}
        result = _assess_image_quality(qa_metrics)
        
        # 0 is falsy, so should return empty
        assert result == {}

    def test_negative_dynamic_range(self):
        """Test assessment with negative dynamic range (edge case)."""
        qa_metrics = {"dynamic_range": -10}
        result = _assess_image_quality(qa_metrics)
        
        # Negative is truthy, so gets assessed
        assert result["overall_quality"] == "poor"


class TestExtractBeamInfo:
    """Tests for _extract_beam_info function."""

    def test_extracts_beam_parameters(self):
        """Test beam parameter extraction."""
        mock_ia = MagicMock()
        mock_ia.restoringbeam.return_value = {
            "major": {"value": 10.5, "unit": "arcsec"},
            "minor": {"value": 5.2, "unit": "arcsec"},
            "positionangle": {"value": 45.0, "unit": "deg"},
        }
        
        result = _extract_beam_info(mock_ia)
        
        assert result["beam_major"] == 10.5
        assert result["beam_minor"] == 5.2
        assert result["beam_pa"] == 45.0

    def test_no_beam_returns_empty(self):
        """Test no beam info returns empty result."""
        mock_ia = MagicMock()
        mock_ia.restoringbeam.return_value = {}
        
        result = _extract_beam_info(mock_ia)
        
        assert result == {}

    def test_partial_beam_info(self):
        """Test partial beam info extraction."""
        mock_ia = MagicMock()
        mock_ia.restoringbeam.return_value = {
            "major": {"value": 10.0},
            # Missing minor and pa
        }
        
        result = _extract_beam_info(mock_ia)
        
        assert result["beam_major"] == 10.0
        assert "beam_minor" not in result
        assert "beam_pa" not in result

    def test_none_beam_returns_empty(self):
        """Test None beam returns empty result."""
        mock_ia = MagicMock()
        mock_ia.restoringbeam.return_value = None
        
        result = _extract_beam_info(mock_ia)
        
        assert result == {}


class TestExtractCalibrationQA:
    """Integration tests for extract_calibration_qa (require CASA mocking)."""

    def test_handles_missing_image_path(self):
        """Test extract_image_qa handles missing image path."""
        # Mock casatools.image since it's imported inside extract_image_qa
        mock_image_class = MagicMock()
        mock_image_instance = MagicMock()
        mock_image_class.return_value = mock_image_instance
        
        with patch.dict('sys.modules', {'casatools': MagicMock(image=mock_image_class)}):
            from dsa110_contimg.api.batch.qa import extract_image_qa
            
            result = extract_image_qa(
                "/path/to/ms",
                job_id=123,
                image_path="/nonexistent/path/image.fits",
            )
        
        assert result["overall_quality"] == "unknown"
        assert result["ms_path"] == "/path/to/ms"
        assert result["job_id"] == 123


class TestQualityThresholds:
    """Tests for quality threshold edge cases."""

    def test_flag_threshold_boundaries(self):
        """Test quality assessment at threshold boundaries."""
        # Test at exactly 0.1 (boundary between excellent and good)
        qa = {"k_metrics": {"flag_fraction": 0.1}}
        result = _calculate_overall_quality(qa)
        assert result["overall_quality"] == "good"  # >= 0.1 is good
        
        # Test just under 0.1
        qa = {"k_metrics": {"flag_fraction": 0.099}}
        result = _calculate_overall_quality(qa)
        assert result["overall_quality"] == "excellent"
        
        # Test at exactly 0.3 (boundary between good and marginal)
        qa = {"k_metrics": {"flag_fraction": 0.3}}
        result = _calculate_overall_quality(qa)
        assert result["overall_quality"] == "marginal"
        
        # Test at exactly 0.5 (boundary between marginal and poor)
        qa = {"k_metrics": {"flag_fraction": 0.5}}
        result = _calculate_overall_quality(qa)
        assert result["overall_quality"] == "poor"

    def test_image_threshold_boundaries(self):
        """Test image quality thresholds at boundaries."""
        # At exactly 1000 (boundary excellent/good)
        result = _assess_image_quality({"dynamic_range": 1000})
        assert result["overall_quality"] == "good"
        
        # At exactly 100 (boundary good/marginal)
        result = _assess_image_quality({"dynamic_range": 100})
        assert result["overall_quality"] == "marginal"
        
        # At exactly 10 (boundary marginal/poor)
        result = _assess_image_quality({"dynamic_range": 10})
        assert result["overall_quality"] == "poor"

    def test_dr_just_above_thresholds(self):
        """Test dynamic range just above each threshold."""
        # Just above 1000
        result = _assess_image_quality({"dynamic_range": 1001})
        assert result["overall_quality"] == "excellent"
        
        # Just above 100
        result = _assess_image_quality({"dynamic_range": 101})
        assert result["overall_quality"] == "good"
        
        # Just above 10
        result = _assess_image_quality({"dynamic_range": 11})
        assert result["overall_quality"] == "marginal"


class TestEdgeCases:
    """Tests for edge cases in QA extraction."""

    def test_empty_metrics_dict(self):
        """Test with empty metrics dictionary."""
        result = _calculate_overall_quality({})
        assert result == {}

    def test_only_k_metrics(self):
        """Test with only K table metrics."""
        qa_metrics = {"k_metrics": {"flag_fraction": 0.15}}
        result = _calculate_overall_quality(qa_metrics)
        
        assert result["flags_total"] == 0.15
        assert result["overall_quality"] == "good"

    def test_only_bp_metrics(self):
        """Test with only BP table metrics."""
        qa_metrics = {"bp_metrics": {"flag_fraction": 0.05}}
        result = _calculate_overall_quality(qa_metrics)
        
        assert result["overall_quality"] == "excellent"

    def test_only_g_metrics(self):
        """Test with only G table metrics."""
        qa_metrics = {"g_metrics": {"flag_fraction": 0.8}}
        result = _calculate_overall_quality(qa_metrics)
        
        assert result["overall_quality"] == "poor"

    def test_floating_point_precision(self):
        """Test floating point precision in calculations."""
        qa_metrics = {
            "k_metrics": {"flag_fraction": 0.1},
            "bp_metrics": {"flag_fraction": 0.1},
            "g_metrics": {"flag_fraction": 0.1},
        }
        result = _calculate_overall_quality(qa_metrics)
        
        # Should be exactly 0.1
        assert result["flags_total"] == pytest.approx(0.1, abs=1e-10)


class TestExtractCalibrationQAWithMocks:
    """Tests for extract_calibration_qa with CASA mocking."""

    @pytest.fixture
    def mock_casatools_table(self):
        """Create a mock casatools module with table class."""
        mock_table_class = MagicMock()
        mock_table_instance = MagicMock()
        mock_table_class.return_value = mock_table_instance
        return mock_table_class, mock_table_instance

    def test_extract_calibration_qa_success(self, tmp_path, mock_casatools_table):
        """Test successful extraction of calibration QA metrics."""
        mock_table_class, mock_tb = mock_casatools_table
        
        # Create fake calibration table paths
        k_table = tmp_path / "k.cal"
        k_table.mkdir()
        bp_table = tmp_path / "bp.cal"
        bp_table.mkdir()
        g_table = tmp_path / "g.cal"
        g_table.mkdir()
        
        # Set up mock table data
        mock_tb.colnames.return_value = ["FLAG", "SNR", "CPARAM"]
        mock_tb.getcol.side_effect = lambda col: {
            "FLAG": np.array([[[False, False], [True, False]]]),  # 25% flagged
            "SNR": np.array([[[10.0, 20.0], [15.0, 25.0]]]),  # avg SNR = 17.5
            "CPARAM": np.array([[[1+1j, 2+2j], [1.5+1.5j, 2.5+2.5j]]]),
        }.get(col, np.array([]))
        
        # Mock casa_init
        mock_ensure_casa = MagicMock()
        mock_casatools = MagicMock()
        mock_casatools.table = mock_table_class
        
        with patch.dict('sys.modules', {
            'casatools': mock_casatools,
        }), patch('dsa110_contimg.utils.casa_init.ensure_casa_path', mock_ensure_casa):
            from importlib import reload
            import dsa110_contimg.api.batch.qa as qa_module
            reload(qa_module)
            
            result = qa_module.extract_calibration_qa(
                ms_path="/path/to/test.ms",
                job_id=123,
                caltables={
                    "k": str(k_table),
                    "bp": str(bp_table),
                    "g": str(g_table),
                },
            )
        
        assert result["ms_path"] == "/path/to/test.ms"
        assert result["job_id"] == 123
        assert "k_metrics" in result
        assert "bp_metrics" in result
        assert "g_metrics" in result

    def test_extract_calibration_qa_no_caltables(self, mock_casatools_table):
        """Test extraction with no calibration tables."""
        mock_table_class, mock_tb = mock_casatools_table
        
        mock_ensure_casa = MagicMock()
        mock_casatools = MagicMock()
        mock_casatools.table = mock_table_class
        
        with patch.dict('sys.modules', {
            'casatools': mock_casatools,
        }), patch('dsa110_contimg.utils.casa_init.ensure_casa_path', mock_ensure_casa):
            from importlib import reload
            import dsa110_contimg.api.batch.qa as qa_module
            reload(qa_module)
            
            result = qa_module.extract_calibration_qa(
                ms_path="/path/to/test.ms",
                job_id=456,
                caltables={},
            )
        
        assert result["ms_path"] == "/path/to/test.ms"
        assert result["job_id"] == 456
        # No metrics should be present
        assert "k_metrics" not in result
        assert "bp_metrics" not in result
        assert "g_metrics" not in result

    def test_extract_calibration_qa_table_error(self, tmp_path, mock_casatools_table):
        """Test extraction handles table read errors gracefully."""
        mock_table_class, mock_tb = mock_casatools_table
        
        k_table = tmp_path / "k.cal"
        k_table.mkdir()
        
        # Simulate table open error
        mock_tb.open.side_effect = RuntimeError("Cannot open table")
        
        mock_ensure_casa = MagicMock()
        mock_casatools = MagicMock()
        mock_casatools.table = mock_table_class
        
        with patch.dict('sys.modules', {
            'casatools': mock_casatools,
        }), patch('dsa110_contimg.utils.casa_init.ensure_casa_path', mock_ensure_casa):
            from importlib import reload
            import dsa110_contimg.api.batch.qa as qa_module
            reload(qa_module)
            
            result = qa_module.extract_calibration_qa(
                ms_path="/path/to/test.ms",
                job_id=789,
                caltables={"k": str(k_table)},
            )
        
        # Should handle error gracefully
        assert result["ms_path"] == "/path/to/test.ms"
        assert result["job_id"] == 789


class TestExtractKTableQA:
    """Tests for _extract_k_table_qa function."""

    @pytest.fixture
    def mock_tb(self):
        """Create a mock table object."""
        return MagicMock()

    def test_extract_k_table_qa_success(self, tmp_path, mock_tb):
        """Test successful K table QA extraction."""
        k_table = tmp_path / "k.cal"
        k_table.mkdir()
        
        mock_tb.colnames.return_value = ["FLAG", "SNR"]
        mock_tb.getcol.side_effect = lambda col: {
            "FLAG": np.array([[[False, True], [False, False]]]),  # 25% flagged
            "SNR": np.array([[[10.0, 20.0], [15.0, 25.0]]]),  # avg SNR = 17.5
        }.get(col)
        
        # Import and test the function directly
        from dsa110_contimg.api.batch.qa import _extract_k_table_qa
        
        result = _extract_k_table_qa(
            mock_tb,
            caltables={"k": str(k_table)},
            ms_path="/path/to/test.ms",
        )
        
        assert "k_metrics" in result
        assert result["k_metrics"]["flag_fraction"] == pytest.approx(0.25)
        assert result["k_metrics"]["avg_snr"] == pytest.approx(17.5)

    def test_extract_k_table_qa_no_snr_column(self, tmp_path, mock_tb):
        """Test K table extraction when SNR column is missing."""
        k_table = tmp_path / "k.cal"
        k_table.mkdir()
        
        mock_tb.colnames.return_value = ["FLAG"]  # No SNR
        mock_tb.getcol.return_value = np.array([[[False, False], [False, False]]])
        
        from dsa110_contimg.api.batch.qa import _extract_k_table_qa
        
        result = _extract_k_table_qa(
            mock_tb,
            caltables={"k": str(k_table)},
            ms_path="/path/to/test.ms",
        )
        
        assert "k_metrics" in result
        assert result["k_metrics"]["flag_fraction"] == 0.0
        assert result["k_metrics"]["avg_snr"] is None

    def test_extract_k_table_qa_missing_table(self, mock_tb):
        """Test K table extraction when table path is missing."""
        from dsa110_contimg.api.batch.qa import _extract_k_table_qa
        
        result = _extract_k_table_qa(
            mock_tb,
            caltables={"k": "/nonexistent/k.cal"},
            ms_path="/path/to/test.ms",
        )
        
        assert result == {}

    def test_extract_k_table_qa_no_k_key(self, mock_tb):
        """Test K table extraction when 'k' key is missing."""
        from dsa110_contimg.api.batch.qa import _extract_k_table_qa
        
        result = _extract_k_table_qa(
            mock_tb,
            caltables={"bp": "/path/to/bp.cal"},
            ms_path="/path/to/test.ms",
        )
        
        assert result == {}

    def test_extract_k_table_qa_empty_k_value(self, mock_tb):
        """Test K table extraction when 'k' value is empty."""
        from dsa110_contimg.api.batch.qa import _extract_k_table_qa
        
        result = _extract_k_table_qa(
            mock_tb,
            caltables={"k": ""},
            ms_path="/path/to/test.ms",
        )
        
        assert result == {}

    def test_extract_k_table_qa_all_flagged(self, tmp_path, mock_tb):
        """Test K table extraction when all data is flagged."""
        k_table = tmp_path / "k.cal"
        k_table.mkdir()
        
        mock_tb.colnames.return_value = ["FLAG", "SNR"]
        mock_tb.getcol.side_effect = lambda col: {
            "FLAG": np.array([[[True, True], [True, True]]]),  # 100% flagged
            "SNR": np.array([[[0.0, 0.0], [0.0, 0.0]]]),
        }.get(col)
        
        from dsa110_contimg.api.batch.qa import _extract_k_table_qa
        
        result = _extract_k_table_qa(
            mock_tb,
            caltables={"k": str(k_table)},
            ms_path="/path/to/test.ms",
        )
        
        assert result["k_metrics"]["flag_fraction"] == 1.0


class TestExtractBPTableQA:
    """Tests for _extract_bp_table_qa function."""

    @pytest.fixture
    def mock_tb(self):
        """Create a mock table object."""
        return MagicMock()

    def test_extract_bp_table_qa_success(self, tmp_path, mock_tb):
        """Test successful BP table QA extraction."""
        bp_table = tmp_path / "bp.cal"
        bp_table.mkdir()
        
        mock_tb.getcol.side_effect = lambda col: {
            "FLAG": np.array([[[False, False], [True, False]]]),  # 25% flagged
            "CPARAM": np.array([[[1+1j, 2+2j], [1.5+1.5j, 2.5+2.5j]]]),
        }.get(col)
        
        from dsa110_contimg.api.batch.qa import _extract_bp_table_qa
        
        # Patch the _extract_per_spw_stats to avoid import issues
        with patch('dsa110_contimg.api.batch.qa._extract_per_spw_stats', return_value={}):
            result = _extract_bp_table_qa(
                mock_tb,
                caltables={"bp": str(bp_table)},
                ms_path="/path/to/test.ms",
            )
        
        assert "bp_metrics" in result
        assert result["bp_metrics"]["flag_fraction"] == pytest.approx(0.25)
        assert result["bp_metrics"]["amp_mean"] is not None
        assert result["bp_metrics"]["amp_std"] is not None

    def test_extract_bp_table_qa_missing_table(self, mock_tb):
        """Test BP table extraction when table path is missing."""
        from dsa110_contimg.api.batch.qa import _extract_bp_table_qa
        
        result = _extract_bp_table_qa(
            mock_tb,
            caltables={"bp": "/nonexistent/bp.cal"},
            ms_path="/path/to/test.ms",
        )
        
        assert result == {}

    def test_extract_bp_table_qa_no_bp_key(self, mock_tb):
        """Test BP table extraction when 'bp' key is missing."""
        from dsa110_contimg.api.batch.qa import _extract_bp_table_qa
        
        result = _extract_bp_table_qa(
            mock_tb,
            caltables={"k": "/path/to/k.cal"},
            ms_path="/path/to/test.ms",
        )
        
        assert result == {}

    def test_extract_bp_table_qa_empty_data(self, tmp_path, mock_tb):
        """Test BP table extraction with empty data arrays."""
        bp_table = tmp_path / "bp.cal"
        bp_table.mkdir()
        
        mock_tb.getcol.side_effect = lambda col: {
            "FLAG": np.array([]),
            "CPARAM": np.array([]),
        }.get(col)
        
        from dsa110_contimg.api.batch.qa import _extract_bp_table_qa
        
        with patch('dsa110_contimg.api.batch.qa._extract_per_spw_stats', return_value={}):
            result = _extract_bp_table_qa(
                mock_tb,
                caltables={"bp": str(bp_table)},
                ms_path="/path/to/test.ms",
            )
        
        # Should handle empty arrays
        assert "bp_metrics" in result
        assert result["bp_metrics"]["flag_fraction"] == 1.0  # Default for empty

    def test_extract_bp_table_qa_error_handling(self, tmp_path, mock_tb):
        """Test BP table extraction handles errors gracefully."""
        bp_table = tmp_path / "bp.cal"
        bp_table.mkdir()
        
        mock_tb.open.side_effect = RuntimeError("Table error")
        
        from dsa110_contimg.api.batch.qa import _extract_bp_table_qa
        
        result = _extract_bp_table_qa(
            mock_tb,
            caltables={"bp": str(bp_table)},
            ms_path="/path/to/test.ms",
        )
        
        assert result == {}


class TestExtractGTableQA:
    """Tests for _extract_g_table_qa function."""

    @pytest.fixture
    def mock_tb(self):
        """Create a mock table object."""
        return MagicMock()

    def test_extract_g_table_qa_success(self, tmp_path, mock_tb):
        """Test successful G table QA extraction."""
        g_table = tmp_path / "g.cal"
        g_table.mkdir()
        
        mock_tb.getcol.side_effect = lambda col: {
            "FLAG": np.array([[[False, False], [False, True]]]),  # 25% flagged
            "CPARAM": np.array([[[1+0j, 0.5+0j], [0.8+0j, 1.2+0j]]]),  # gains
        }.get(col)
        
        from dsa110_contimg.api.batch.qa import _extract_g_table_qa
        
        result = _extract_g_table_qa(
            mock_tb,
            caltables={"g": str(g_table)},
            ms_path="/path/to/test.ms",
        )
        
        assert "g_metrics" in result
        assert result["g_metrics"]["flag_fraction"] == pytest.approx(0.25)
        assert result["g_metrics"]["amp_mean"] is not None

    def test_extract_g_table_qa_missing_table(self, mock_tb):
        """Test G table extraction when table path is missing."""
        from dsa110_contimg.api.batch.qa import _extract_g_table_qa
        
        result = _extract_g_table_qa(
            mock_tb,
            caltables={"g": "/nonexistent/g.cal"},
            ms_path="/path/to/test.ms",
        )
        
        assert result == {}

    def test_extract_g_table_qa_no_g_key(self, mock_tb):
        """Test G table extraction when 'g' key is missing."""
        from dsa110_contimg.api.batch.qa import _extract_g_table_qa
        
        result = _extract_g_table_qa(
            mock_tb,
            caltables={"k": "/path/to/k.cal"},
            ms_path="/path/to/test.ms",
        )
        
        assert result == {}

    def test_extract_g_table_qa_empty_g_value(self, mock_tb):
        """Test G table extraction when 'g' value is empty string."""
        from dsa110_contimg.api.batch.qa import _extract_g_table_qa
        
        result = _extract_g_table_qa(
            mock_tb,
            caltables={"g": ""},
            ms_path="/path/to/test.ms",
        )
        
        assert result == {}

    def test_extract_g_table_qa_all_flagged(self, tmp_path, mock_tb):
        """Test G table extraction when all data is flagged."""
        g_table = tmp_path / "g.cal"
        g_table.mkdir()
        
        mock_tb.getcol.side_effect = lambda col: {
            "FLAG": np.array([[[True, True], [True, True]]]),  # 100% flagged
            "CPARAM": np.array([[[0+0j, 0+0j], [0+0j, 0+0j]]]),
        }.get(col)
        
        from dsa110_contimg.api.batch.qa import _extract_g_table_qa
        
        result = _extract_g_table_qa(
            mock_tb,
            caltables={"g": str(g_table)},
            ms_path="/path/to/test.ms",
        )
        
        assert result["g_metrics"]["flag_fraction"] == 1.0


class TestExtractImageQA:
    """Tests for extract_image_qa with CASA mocking."""

    def test_extract_image_qa_success(self, tmp_path):
        """Test successful image QA extraction."""
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        
        mock_image_class = MagicMock()
        mock_ia = MagicMock()
        mock_image_class.return_value = mock_ia
        
        # Setup mock responses
        mock_ia.statistics.return_value = {
            "rms": [0.001],
            "max": [1.0],
        }
        mock_ia.restoringbeam.return_value = {
            "major": {"value": 10.0, "unit": "arcsec"},
            "minor": {"value": 5.0, "unit": "arcsec"},
            "positionangle": {"value": 45.0, "unit": "deg"},
        }
        
        mock_casatools = MagicMock()
        mock_casatools.image = mock_image_class
        
        with patch.dict('sys.modules', {'casatools': mock_casatools}):
            from importlib import reload
            import dsa110_contimg.api.batch.qa as qa_module
            reload(qa_module)
            
            result = qa_module.extract_image_qa(
                ms_path="/path/to/test.ms",
                job_id=123,
                image_path=str(image_path),
            )
        
        assert result["ms_path"] == "/path/to/test.ms"
        assert result["job_id"] == 123
        assert result["rms_noise"] == 0.001
        assert result["peak_flux"] == 1.0
        assert result["dynamic_range"] == 1000.0

    def test_extract_image_qa_missing_image(self):
        """Test image QA extraction with missing image file."""
        mock_image_class = MagicMock()
        mock_casatools = MagicMock()
        mock_casatools.image = mock_image_class
        
        with patch.dict('sys.modules', {'casatools': mock_casatools}):
            from importlib import reload
            import dsa110_contimg.api.batch.qa as qa_module
            reload(qa_module)
            
            result = qa_module.extract_image_qa(
                ms_path="/path/to/test.ms",
                job_id=123,
                image_path="/nonexistent/image.fits",
            )
        
        assert result["overall_quality"] == "unknown"

    def test_extract_image_qa_zero_rms(self, tmp_path):
        """Test image QA extraction with zero RMS."""
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        
        mock_image_class = MagicMock()
        mock_ia = MagicMock()
        mock_image_class.return_value = mock_ia
        
        mock_ia.statistics.return_value = {
            "rms": [0.0],  # Zero RMS
            "max": [1.0],
        }
        mock_ia.restoringbeam.return_value = {}
        
        mock_casatools = MagicMock()
        mock_casatools.image = mock_image_class
        
        with patch.dict('sys.modules', {'casatools': mock_casatools}):
            from importlib import reload
            import dsa110_contimg.api.batch.qa as qa_module
            reload(qa_module)
            
            result = qa_module.extract_image_qa(
                ms_path="/path/to/test.ms",
                job_id=123,
                image_path=str(image_path),
            )
        
        # Should not have dynamic range when RMS is zero
        assert "dynamic_range" not in result or result.get("dynamic_range") is None

    def test_extract_image_qa_error_handling(self, tmp_path):
        """Test image QA extraction handles errors gracefully."""
        image_path = tmp_path / "test.image"
        image_path.mkdir()
        
        mock_image_class = MagicMock()
        mock_ia = MagicMock()
        mock_image_class.return_value = mock_ia
        mock_ia.open.side_effect = RuntimeError("Cannot open image")
        
        mock_casatools = MagicMock()
        mock_casatools.image = mock_image_class
        
        with patch.dict('sys.modules', {'casatools': mock_casatools}):
            from importlib import reload
            import dsa110_contimg.api.batch.qa as qa_module
            reload(qa_module)
            
            result = qa_module.extract_image_qa(
                ms_path="/path/to/test.ms",
                job_id=123,
                image_path=str(image_path),
            )
        
        assert result["overall_quality"] == "unknown"


class TestExtractPerSpwStats:
    """Tests for _extract_per_spw_stats function."""

    def test_extract_per_spw_stats_success(self, tmp_path):
        """Test successful per-SPW stats extraction."""
        bp_path = str(tmp_path / "bp.cal")
        
        # Create a mock SPW stats result
        mock_spw_stat = MagicMock()
        mock_spw_stat.spw_id = 0
        mock_spw_stat.total_solutions = 100
        mock_spw_stat.flagged_solutions = 10
        mock_spw_stat.fraction_flagged = 0.1
        mock_spw_stat.n_channels = 64
        mock_spw_stat.channels_with_high_flagging = 2
        mock_spw_stat.avg_flagged_per_channel = 0.15
        mock_spw_stat.max_flagged_in_channel = 5
        mock_spw_stat.is_problematic = False
        
        # Create mock module and function
        mock_qa_module = MagicMock()
        mock_qa_module.analyze_per_spw_flagging = MagicMock(return_value=[mock_spw_stat])
        
        with patch.dict('sys.modules', {
            'dsa110_contimg.qa': MagicMock(),
            'dsa110_contimg.qa.calibration_quality': mock_qa_module,
        }):
            from dsa110_contimg.api.batch.qa import _extract_per_spw_stats
            
            result = _extract_per_spw_stats(bp_path, "/path/to/test.ms")
        
        assert "per_spw_stats" in result
        assert len(result["per_spw_stats"]) == 1
        assert result["per_spw_stats"][0]["spw_id"] == 0
        assert result["per_spw_stats"][0]["is_problematic"] is False

    def test_extract_per_spw_stats_import_error(self, tmp_path):
        """Test per-SPW stats extraction handles import errors."""
        bp_path = str(tmp_path / "bp.cal")
        
        from dsa110_contimg.api.batch.qa import _extract_per_spw_stats
        
        # The module likely doesn't exist, so it should handle the ImportError
        result = _extract_per_spw_stats(bp_path, "/path/to/test.ms")
        
        # Should return empty dict on import error
        assert result == {}

    def test_extract_per_spw_stats_runtime_error(self, tmp_path):
        """Test per-SPW stats extraction handles runtime errors."""
        bp_path = str(tmp_path / "bp.cal")
        
        # Create mock module that raises RuntimeError
        mock_qa_module = MagicMock()
        mock_qa_module.analyze_per_spw_flagging = MagicMock(side_effect=RuntimeError("Analysis failed"))
        
        with patch.dict('sys.modules', {
            'dsa110_contimg.qa': MagicMock(),
            'dsa110_contimg.qa.calibration_quality': mock_qa_module,
        }):
            from dsa110_contimg.api.batch.qa import _extract_per_spw_stats
            
            result = _extract_per_spw_stats(bp_path, "/path/to/test.ms")
        
        assert result == {}

