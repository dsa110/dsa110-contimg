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

