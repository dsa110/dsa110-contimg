"""
Unit tests for the API error envelope module.
"""

import pytest
from dsa110_contimg.api.errors import (
    ErrorCode,
    ErrorEnvelope,
    make_error,
    cal_table_missing,
    cal_apply_failed,
    image_not_found,
    ms_not_found,
    source_not_found,
    validation_failed,
    db_unavailable,
    internal_error,
    DOC_ANCHORS,
)


class TestErrorEnvelope:
    """Tests for ErrorEnvelope dataclass."""
    
    def test_creates_envelope_with_required_fields(self):
        """Test basic envelope creation."""
        envelope = ErrorEnvelope(
            code="TEST_ERROR",
            http_status=400,
            user_message="Test error message",
            action="Test action",
        )
        
        assert envelope.code == "TEST_ERROR"
        assert envelope.http_status == 400
        assert envelope.user_message == "Test error message"
        assert envelope.action == "Test action"
        assert envelope.ref_id == ""
        assert envelope.details == {}
        assert envelope.trace_id  # Should be auto-generated
        assert len(envelope.trace_id) == 12
    
    def test_auto_populates_doc_anchor(self):
        """Test that doc_anchor is auto-populated for known codes."""
        envelope = ErrorEnvelope(
            code=ErrorCode.CAL_TABLE_MISSING.value,
            http_status=400,
            user_message="Cal table missing",
            action="Re-run calibration",
        )
        
        assert envelope.doc_anchor == "calibration_missing_table"
    
    def test_preserves_explicit_doc_anchor(self):
        """Test that explicit doc_anchor is preserved."""
        envelope = ErrorEnvelope(
            code=ErrorCode.CAL_TABLE_MISSING.value,
            http_status=400,
            user_message="Cal table missing",
            action="Re-run calibration",
            doc_anchor="custom_anchor",
        )
        
        assert envelope.doc_anchor == "custom_anchor"
    
    def test_to_dict_excludes_none_values(self):
        """Test that to_dict removes None values."""
        envelope = ErrorEnvelope(
            code="TEST_ERROR",
            http_status=400,
            user_message="Test",
            action="Test",
            doc_anchor=None,
        )
        
        result = envelope.to_dict()
        
        assert "doc_anchor" not in result
        assert "code" in result
        assert "http_status" in result


class TestMakeError:
    """Tests for make_error factory function."""
    
    def test_creates_envelope_from_enum(self):
        """Test creating envelope with ErrorCode enum."""
        envelope = make_error(
            code=ErrorCode.MS_NOT_FOUND,
            http_status=404,
            user_message="MS not found",
            action="Check path",
        )
        
        assert envelope.code == "MS_NOT_FOUND"
        assert envelope.http_status == 404
    
    def test_creates_envelope_from_string(self):
        """Test creating envelope with string code."""
        envelope = make_error(
            code="CUSTOM_ERROR",
            http_status=500,
            user_message="Custom error",
            action="Contact support",
        )
        
        assert envelope.code == "CUSTOM_ERROR"
    
    def test_accepts_custom_trace_id(self):
        """Test that custom trace_id is used."""
        envelope = make_error(
            code="TEST",
            http_status=400,
            user_message="Test",
            action="Test",
            trace_id="custom123",
        )
        
        assert envelope.trace_id == "custom123"


class TestErrorFactoryFunctions:
    """Tests for pre-defined error factory functions."""
    
    def test_cal_table_missing(self):
        """Test cal_table_missing factory."""
        error = cal_table_missing("/data/ms/test.ms", ref_id="job-123")
        
        assert error.code == "CAL_TABLE_MISSING"
        assert error.http_status == 400
        assert "/data/ms/test.ms" in error.user_message
        assert error.ref_id == "job-123"
        assert error.details["ms_path"] == "/data/ms/test.ms"
        assert error.doc_anchor == "calibration_missing_table"
    
    def test_cal_apply_failed(self):
        """Test cal_apply_failed factory."""
        error = cal_apply_failed("/data/ms/test.ms", "Antenna mismatch", ref_id="job-456")
        
        assert error.code == "CAL_APPLY_FAILED"
        assert error.http_status == 500
        assert error.ref_id == "job-456"
        assert error.details["reason"] == "Antenna mismatch"
    
    def test_image_not_found(self):
        """Test image_not_found factory."""
        error = image_not_found("img-001")
        
        assert error.code == "IMAGE_NOT_FOUND"
        assert error.http_status == 404
        assert "img-001" in error.user_message
        assert error.details["image_id"] == "img-001"
    
    def test_ms_not_found(self):
        """Test ms_not_found factory."""
        error = ms_not_found("/data/ms/missing.ms")
        
        assert error.code == "MS_NOT_FOUND"
        assert error.http_status == 404
        assert "/data/ms/missing.ms" in error.user_message
    
    def test_source_not_found(self):
        """Test source_not_found factory."""
        error = source_not_found("src-999")
        
        assert error.code == "SOURCE_NOT_FOUND"
        assert error.http_status == 404
        assert "src-999" in error.user_message
    
    def test_validation_failed(self):
        """Test validation_failed factory."""
        errors_list = [
            {"field": "ra_deg", "message": "must be between 0 and 360"},
            {"field": "dec_deg", "message": "must be between -90 and 90"},
        ]
        error = validation_failed(errors_list)
        
        assert error.code == "VALIDATION_FAILED"
        assert error.http_status == 400
        assert error.details["validation_errors"] == errors_list
    
    def test_db_unavailable(self):
        """Test db_unavailable factory."""
        error = db_unavailable("products")
        
        assert error.code == "PRODUCTS_DB_UNAVAILABLE"
        assert error.http_status == 503
        assert "Products" in error.user_message
    
    def test_internal_error(self):
        """Test internal_error factory."""
        error = internal_error("Something went wrong")
        
        assert error.code == "INTERNAL_ERROR"
        assert error.http_status == 500
        assert error.user_message == "Something went wrong"


class TestDocAnchors:
    """Tests for documentation anchor mapping."""
    
    def test_all_common_errors_have_anchors(self):
        """Test that common error codes have doc anchors."""
        expected_codes = [
            ErrorCode.CAL_TABLE_MISSING,
            ErrorCode.CAL_APPLY_FAILED,
            ErrorCode.IMAGE_CLEAN_FAILED,
            ErrorCode.MS_NOT_FOUND,
            ErrorCode.PRODUCTS_DB_UNAVAILABLE,
        ]
        
        for code in expected_codes:
            assert code in DOC_ANCHORS, f"Missing doc anchor for {code}"
    
    def test_anchors_are_valid_slugs(self):
        """Test that all anchors are valid URL slugs."""
        import re
        slug_pattern = re.compile(r'^[a-z][a-z0-9_]*$')
        
        for code, anchor in DOC_ANCHORS.items():
            assert slug_pattern.match(anchor), f"Invalid anchor slug: {anchor}"
