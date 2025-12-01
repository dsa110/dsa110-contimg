"""
Tests for the shared business logic module.

Tests the centralized business logic functions that were extracted from
repository classes to eliminate duplication.
"""

import pytest

from dsa110_contimg.api.business_logic import (
    stage_to_qa_grade,
    generate_image_qa_summary,
    generate_ms_qa_summary,
    generate_run_id,
)
from dsa110_contimg.api.repositories import ImageRecord, MSRecord


class TestStageToQaGrade:
    """Tests for stage_to_qa_grade function."""

    def test_imaged_returns_good(self):
        """Imaged stage should return 'good' grade."""
        assert stage_to_qa_grade("imaged") == "good"

    def test_mosaicked_returns_good(self):
        """Mosaicked stage should return 'good' grade."""
        assert stage_to_qa_grade("mosaicked") == "good"

    def test_cataloged_returns_good(self):
        """Cataloged stage should return 'good' grade."""
        assert stage_to_qa_grade("cataloged") == "good"

    def test_calibrated_returns_warn(self):
        """Calibrated stage should return 'warn' grade."""
        assert stage_to_qa_grade("calibrated") == "warn"

    def test_none_returns_fail(self):
        """None stage should return 'fail' grade."""
        assert stage_to_qa_grade(None) == "fail"

    def test_empty_string_returns_fail(self):
        """Empty string stage should return 'fail' grade."""
        assert stage_to_qa_grade("") == "fail"

    def test_unknown_stage_returns_fail(self):
        """Unknown stage should return 'fail' grade."""
        assert stage_to_qa_grade("unknown") == "fail"
        assert stage_to_qa_grade("processing") == "fail"
        assert stage_to_qa_grade("pending") == "fail"

    def test_status_parameter_ignored(self):
        """Status parameter is reserved for future use, currently ignored."""
        # Status shouldn't affect the result
        assert stage_to_qa_grade("imaged", "success") == "good"
        assert stage_to_qa_grade("imaged", "error") == "good"
        assert stage_to_qa_grade(None, "success") == "fail"


class TestGenerateImageQaSummary:
    """Tests for generate_image_qa_summary function."""

    def test_full_metrics(self):
        """Record with all metrics should include all parts."""
        record = ImageRecord(
            id=1,
            path="/test/image.fits",
            ms_path="/test/data.ms",
            created_at=1234567890.0,
            type="continuum",
            noise_jy=0.001,
            dynamic_range=500.0,
            beam_major_arcsec=5.0,
        )
        summary = generate_image_qa_summary(record)
        assert "RMS 1.00 mJy" in summary
        assert "DR 500" in summary
        assert "Beam 5.0\"" in summary

    def test_only_noise(self):
        """Record with only noise should show just RMS."""
        record = ImageRecord(
            id=1,
            path="/test/image.fits",
            ms_path="/test/data.ms",
            created_at=1234567890.0,
            type="continuum",
            noise_jy=0.002,
        )
        summary = generate_image_qa_summary(record)
        assert "RMS 2.00 mJy" in summary
        assert "DR" not in summary
        assert "Beam" not in summary

    def test_only_dynamic_range(self):
        """Record with only dynamic range should show just DR."""
        record = ImageRecord(
            id=1,
            path="/test/image.fits",
            ms_path="/test/data.ms",
            created_at=1234567890.0,
            type="continuum",
            dynamic_range=1000.0,
        )
        summary = generate_image_qa_summary(record)
        assert "DR 1000" in summary
        assert "RMS" not in summary

    def test_only_beam(self):
        """Record with only beam should show just beam."""
        record = ImageRecord(
            id=1,
            path="/test/image.fits",
            ms_path="/test/data.ms",
            created_at=1234567890.0,
            type="continuum",
            beam_major_arcsec=3.5,
        )
        summary = generate_image_qa_summary(record)
        assert "Beam 3.5\"" in summary
        assert "RMS" not in summary
        assert "DR" not in summary

    def test_no_metrics(self):
        """Record with no metrics should show default message."""
        record = ImageRecord(
            id=1,
            path="/test/image.fits",
            ms_path="/test/data.ms",
            created_at=1234567890.0,
            type="continuum",
        )
        summary = generate_image_qa_summary(record)
        assert summary == "No QA metrics available"

    def test_zero_values_not_shown(self):
        """Zero values should not be included in summary."""
        record = ImageRecord(
            id=1,
            path="/test/image.fits",
            ms_path="/test/data.ms",
            created_at=1234567890.0,
            type="continuum",
            noise_jy=0.0,
            dynamic_range=0.0,
            beam_major_arcsec=0.0,
        )
        summary = generate_image_qa_summary(record)
        assert summary == "No QA metrics available"


class TestGenerateMsQaSummary:
    """Tests for generate_ms_qa_summary function."""

    def test_calibrated_with_stage(self):
        """Record with calibration and stage should show both."""
        record = MSRecord(
            path="/test/data.ms",
            cal_applied=1,
            stage="imaged",
        )
        summary = generate_ms_qa_summary(record)
        assert "Calibrated" in summary
        assert "Stage: imaged" in summary

    def test_only_calibrated(self):
        """Record with only calibration should show just 'Calibrated'."""
        record = MSRecord(
            path="/test/data.ms",
            cal_applied=1,
        )
        summary = generate_ms_qa_summary(record)
        assert summary == "Calibrated"

    def test_only_stage(self):
        """Record with only stage should show just stage."""
        record = MSRecord(
            path="/test/data.ms",
            stage="calibrated",
        )
        summary = generate_ms_qa_summary(record)
        assert summary == "Stage: calibrated"

    def test_no_info(self):
        """Record with no info should show default message."""
        record = MSRecord(
            path="/test/data.ms",
        )
        summary = generate_ms_qa_summary(record)
        assert summary == "No QA info"

    def test_cal_applied_zero_not_shown(self):
        """cal_applied=0 should not show 'Calibrated'."""
        record = MSRecord(
            path="/test/data.ms",
            cal_applied=0,
            stage="pending",
        )
        summary = generate_ms_qa_summary(record)
        assert "Calibrated" not in summary
        assert "Stage: pending" in summary


class TestGenerateRunId:
    """Tests for generate_run_id function."""

    def test_iso_timestamp_path(self):
        """Path with ISO timestamp should generate proper run ID."""
        run_id = generate_run_id("/data/2024-01-15T12:30:45.ms")
        assert run_id == "job-2024-01-15-123045"

    def test_iso_timestamp_with_colons(self):
        """Colons in time should be removed."""
        run_id = generate_run_id("/data/2024-01-15T12:30:00.ms")
        assert run_id == "job-2024-01-15-123000"

    def test_timestamp_with_decimals(self):
        """Decimal seconds should be truncated."""
        run_id = generate_run_id("/data/2024-01-15T12:30:45.123456.ms")
        assert run_id == "job-2024-01-15-123045"

    def test_simple_basename(self):
        """Path without timestamp should use basename."""
        run_id = generate_run_id("/data/observation.ms")
        assert run_id == "job-observation"

    def test_deeply_nested_path(self):
        """Deeply nested path should extract just basename."""
        run_id = generate_run_id("/data/archive/2024/01/15/observation.ms")
        assert run_id == "job-observation"

    def test_path_without_extension(self):
        """Path without extension should work."""
        run_id = generate_run_id("/data/2024-01-15T12:30:00")
        assert run_id == "job-2024-01-15-123000"

    def test_relative_path(self):
        """Relative path should work."""
        run_id = generate_run_id("observation.ms")
        assert run_id == "job-observation"

    def test_timestamp_different_formats(self):
        """Different timestamp formats should be handled."""
        # Standard ISO format
        assert generate_run_id("/data/2024-12-01T08:15:30.ms") == "job-2024-12-01-081530"
        
        # With microseconds
        assert generate_run_id("/data/2024-12-01T08:15:30.123.ms") == "job-2024-12-01-081530"

    def test_empty_path_components(self):
        """Edge case with T in non-timestamp context."""
        # If there's a T but it's not a timestamp, still handles it
        run_id = generate_run_id("/data/TEST_file.ms")
        # Should try to parse as timestamp, may produce odd result but shouldn't crash
        assert run_id.startswith("job-")
