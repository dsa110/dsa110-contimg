"""
Unit tests for the request validation module.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError as PydanticValidationError


class TestPaginationParams:
    """Tests for PaginationParams model."""
    
    def test_default_values(self):
        """Should have default limit and offset."""
        from dsa110_contimg.api.validation import PaginationParams
        
        params = PaginationParams()
        
        assert params.limit == 50
        assert params.offset == 0
    
    def test_custom_values(self):
        """Should accept custom values."""
        from dsa110_contimg.api.validation import PaginationParams
        
        params = PaginationParams(limit=100, offset=50)
        
        assert params.limit == 100
        assert params.offset == 50
    
    def test_limit_minimum(self):
        """Limit must be at least 1."""
        from dsa110_contimg.api.validation import PaginationParams
        
        with pytest.raises(PydanticValidationError):
            PaginationParams(limit=0)
    
    def test_limit_maximum(self):
        """Limit cannot exceed 1000."""
        from dsa110_contimg.api.validation import PaginationParams
        
        with pytest.raises(PydanticValidationError):
            PaginationParams(limit=1001)
    
    def test_offset_minimum(self):
        """Offset must be non-negative."""
        from dsa110_contimg.api.validation import PaginationParams
        
        with pytest.raises(PydanticValidationError):
            PaginationParams(offset=-1)
    
    def test_rejects_extra_fields(self):
        """Should reject unknown fields."""
        from dsa110_contimg.api.validation import PaginationParams
        
        with pytest.raises(PydanticValidationError):
            PaginationParams(limit=50, unknown_field="value")


class TestDateRangeParams:
    """Tests for DateRangeParams model."""
    
    def test_empty_range(self):
        """Should allow empty date range."""
        from dsa110_contimg.api.validation import DateRangeParams
        
        params = DateRangeParams()
        
        assert params.start_date is None
        assert params.end_date is None
    
    def test_valid_range(self):
        """Should accept valid date range."""
        from dsa110_contimg.api.validation import DateRangeParams
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        
        params = DateRangeParams(start_date=start, end_date=end)
        
        assert params.start_date == start
        assert params.end_date == end
    
    def test_invalid_range(self):
        """Should reject start_date after end_date."""
        from dsa110_contimg.api.validation import DateRangeParams
        
        with pytest.raises(PydanticValidationError) as exc_info:
            DateRangeParams(
                start_date=datetime(2024, 12, 31),
                end_date=datetime(2024, 1, 1),
            )
        
        assert "start_date must be before end_date" in str(exc_info.value)


class TestImageQueryParams:
    """Tests for ImageQueryParams model."""
    
    def test_default_values(self):
        """Should have None defaults."""
        from dsa110_contimg.api.validation import ImageQueryParams
        
        params = ImageQueryParams()
        
        assert params.source is None
        assert params.min_flux is None
    
    def test_valid_flux_range(self):
        """Should accept valid flux range."""
        from dsa110_contimg.api.validation import ImageQueryParams
        
        params = ImageQueryParams(min_flux=0.1, max_flux=10.0)
        
        assert params.min_flux == 0.1
        assert params.max_flux == 10.0
    
    def test_invalid_flux_range(self):
        """Should reject min_flux > max_flux."""
        from dsa110_contimg.api.validation import ImageQueryParams
        
        with pytest.raises(PydanticValidationError) as exc_info:
            ImageQueryParams(min_flux=10.0, max_flux=1.0)
        
        assert "min_flux must be less than max_flux" in str(exc_info.value)
    
    def test_negative_flux_rejected(self):
        """Should reject negative flux values."""
        from dsa110_contimg.api.validation import ImageQueryParams
        
        with pytest.raises(PydanticValidationError):
            ImageQueryParams(min_flux=-1.0)


class TestSourceQueryParams:
    """Tests for SourceQueryParams model."""
    
    def test_valid_ra_range(self):
        """Should accept valid RA values."""
        from dsa110_contimg.api.validation import SourceQueryParams
        
        params = SourceQueryParams(ra_min=0, ra_max=360)
        
        assert params.ra_min == 0
        assert params.ra_max == 360
    
    def test_invalid_ra(self):
        """Should reject RA outside 0-360."""
        from dsa110_contimg.api.validation import SourceQueryParams
        
        with pytest.raises(PydanticValidationError):
            SourceQueryParams(ra_min=400)
    
    def test_valid_dec_range(self):
        """Should accept valid Dec values."""
        from dsa110_contimg.api.validation import SourceQueryParams
        
        params = SourceQueryParams(dec_min=-90, dec_max=90)
        
        assert params.dec_min == -90
        assert params.dec_max == 90
    
    def test_invalid_dec(self):
        """Should reject Dec outside -90 to +90."""
        from dsa110_contimg.api.validation import SourceQueryParams
        
        with pytest.raises(PydanticValidationError):
            SourceQueryParams(dec_min=-100)


class TestJobQueryParams:
    """Tests for JobQueryParams model."""
    
    def test_valid_status(self):
        """Should accept valid status values."""
        from dsa110_contimg.api.validation import JobQueryParams
        
        for status in ["pending", "running", "completed", "failed", "cancelled"]:
            params = JobQueryParams(status=status)
            assert params.status == status
    
    def test_invalid_status(self):
        """Should reject invalid status."""
        from dsa110_contimg.api.validation import JobQueryParams
        
        with pytest.raises(PydanticValidationError):
            JobQueryParams(status="invalid_status")


class TestValidateImageId:
    """Tests for validate_image_id function."""
    
    def test_valid_id(self):
        """Should accept valid image IDs."""
        from dsa110_contimg.api.validation import validate_image_id
        
        assert validate_image_id("image_2024_01_15") == "image_2024_01_15"
        assert validate_image_id("test-image") == "test-image"
        assert validate_image_id("IMG001") == "IMG001"
    
    def test_invalid_id(self):
        """Should reject invalid image IDs."""
        from dsa110_contimg.api.validation import validate_image_id, ValidationError
        
        with pytest.raises(ValidationError):
            validate_image_id("image with spaces")
        
        with pytest.raises(ValidationError):
            validate_image_id("image/path")


class TestValidateJobId:
    """Tests for validate_job_id function."""
    
    def test_valid_uuid(self):
        """Should accept valid UUIDs."""
        from dsa110_contimg.api.validation import validate_job_id
        
        uuid = "550e8400-e29b-41d4-a716-446655440000"
        assert validate_job_id(uuid) == uuid
    
    def test_invalid_uuid(self):
        """Should reject invalid UUIDs."""
        from dsa110_contimg.api.validation import validate_job_id, ValidationError
        
        with pytest.raises(ValidationError):
            validate_job_id("not-a-uuid")
        
        with pytest.raises(ValidationError):
            validate_job_id("550e8400-e29b-41d4-a716")  # Too short


class TestValidateMsPath:
    """Tests for validate_ms_path function."""
    
    def test_valid_path(self):
        """Should accept valid paths."""
        from dsa110_contimg.api.validation import validate_ms_path
        
        assert validate_ms_path("data/obs_001.ms") == "data/obs_001.ms"
    
    def test_path_traversal_rejected(self):
        """Should reject path traversal attempts."""
        from dsa110_contimg.api.validation import validate_ms_path, ValidationError
        
        with pytest.raises(ValidationError):
            validate_ms_path("../etc/passwd")
        
        with pytest.raises(ValidationError):
            validate_ms_path("/absolute/path")


class TestJobCreateRequest:
    """Tests for JobCreateRequest model."""
    
    def test_valid_request(self):
        """Should accept valid job creation request."""
        from dsa110_contimg.api.validation import JobCreateRequest
        
        request = JobCreateRequest(
            pipeline="imaging",
            parameters={"threshold": 0.5},
            priority=3,
        )
        
        assert request.pipeline == "imaging"
        assert request.parameters == {"threshold": 0.5}
        assert request.priority == 3
    
    def test_default_priority(self):
        """Should have default priority of 5."""
        from dsa110_contimg.api.validation import JobCreateRequest
        
        request = JobCreateRequest(pipeline="imaging")
        
        assert request.priority == 5
    
    def test_priority_range(self):
        """Priority must be 1-10."""
        from dsa110_contimg.api.validation import JobCreateRequest
        
        with pytest.raises(PydanticValidationError):
            JobCreateRequest(pipeline="imaging", priority=0)
        
        with pytest.raises(PydanticValidationError):
            JobCreateRequest(pipeline="imaging", priority=11)
    
    def test_empty_pipeline_rejected(self):
        """Should reject empty pipeline name."""
        from dsa110_contimg.api.validation import JobCreateRequest
        
        with pytest.raises(PydanticValidationError):
            JobCreateRequest(pipeline="")


class TestCacheInvalidateRequest:
    """Tests for CacheInvalidateRequest model."""
    
    def test_valid_request(self):
        """Should accept valid cache invalidation request."""
        from dsa110_contimg.api.validation import CacheInvalidateRequest
        
        request = CacheInvalidateRequest(keys=["images:list", "sources:123"])
        
        assert request.keys == ["images:list", "sources:123"]
    
    def test_empty_keys_rejected(self):
        """Should reject empty keys list."""
        from dsa110_contimg.api.validation import CacheInvalidateRequest
        
        with pytest.raises(PydanticValidationError):
            CacheInvalidateRequest(keys=[])
    
    def test_invalid_key_format(self):
        """Should reject invalid key formats."""
        from dsa110_contimg.api.validation import CacheInvalidateRequest
        
        with pytest.raises(PydanticValidationError):
            CacheInvalidateRequest(keys=["invalid key with space"])


class TestCoordinateValidation:
    """Tests for coordinate validation functions."""
    
    def test_validate_ra_valid(self):
        """Should accept valid RA values."""
        from dsa110_contimg.api.validation import validate_ra
        
        assert validate_ra(0) == 0
        assert validate_ra(180) == 180
        assert validate_ra(360) == 360
    
    def test_validate_ra_invalid(self):
        """Should reject invalid RA values."""
        from dsa110_contimg.api.validation import validate_ra, ValidationError
        
        with pytest.raises(ValidationError):
            validate_ra(-10)
        
        with pytest.raises(ValidationError):
            validate_ra(400)
    
    def test_validate_dec_valid(self):
        """Should accept valid Dec values."""
        from dsa110_contimg.api.validation import validate_dec
        
        assert validate_dec(-90) == -90
        assert validate_dec(0) == 0
        assert validate_dec(90) == 90
    
    def test_validate_dec_invalid(self):
        """Should reject invalid Dec values."""
        from dsa110_contimg.api.validation import validate_dec, ValidationError
        
        with pytest.raises(ValidationError):
            validate_dec(-100)
        
        with pytest.raises(ValidationError):
            validate_dec(100)
    
    def test_validate_search_radius_valid(self):
        """Should accept valid search radius."""
        from dsa110_contimg.api.validation import validate_search_radius
        
        assert validate_search_radius(1.0) == 1.0
        assert validate_search_radius(10.0) == 10.0
    
    def test_validate_search_radius_invalid(self):
        """Should reject invalid search radius."""
        from dsa110_contimg.api.validation import validate_search_radius, ValidationError
        
        with pytest.raises(ValidationError):
            validate_search_radius(0)
        
        with pytest.raises(ValidationError):
            validate_search_radius(-1)
        
        with pytest.raises(ValidationError):
            validate_search_radius(100, max_radius=10)


class TestContentValidation:
    """Tests for content validation functions."""
    
    def test_validate_json_content_type(self):
        """Should validate JSON content type."""
        from dsa110_contimg.api.validation import validate_json_content_type
        
        assert validate_json_content_type("application/json") is True
        assert validate_json_content_type("application/json; charset=utf-8") is True
        assert validate_json_content_type("text/plain") is False
        assert validate_json_content_type(None) is False
    
    def test_validate_file_extension(self):
        """Should validate file extensions."""
        from dsa110_contimg.api.validation import validate_file_extension
        
        allowed = [".fits", ".ms", ".uvh5"]
        
        assert validate_file_extension("data.fits", allowed) is True
        assert validate_file_extension("data.MS", allowed) is True
        assert validate_file_extension("data.txt", allowed) is False


class TestSortParams:
    """Tests for SortParams model."""
    
    def test_default_order(self):
        """Should default to descending order."""
        from dsa110_contimg.api.validation import SortParams, SortOrder
        
        params = SortParams()
        
        assert params.order == SortOrder.DESC
    
    def test_valid_sort_field(self):
        """Should accept valid sort field names."""
        from dsa110_contimg.api.validation import SortParams
        
        params = SortParams(sort_by="created_at")
        
        assert params.sort_by == "created_at"
    
    def test_invalid_sort_field(self):
        """Should reject invalid sort field names."""
        from dsa110_contimg.api.validation import SortParams
        
        with pytest.raises(PydanticValidationError):
            SortParams(sort_by="invalid-field")  # Contains dash


class TestCursorPaginationParams:
    """Tests for CursorPaginationParams model."""
    
    def test_default_values(self):
        """Should have default values."""
        from dsa110_contimg.api.validation import CursorPaginationParams
        
        params = CursorPaginationParams()
        
        assert params.cursor is None
        assert params.limit == 50
    
    def test_with_cursor(self):
        """Should accept cursor parameter."""
        from dsa110_contimg.api.validation import CursorPaginationParams
        
        params = CursorPaginationParams(cursor="abc123", limit=25)
        
        assert params.cursor == "abc123"
        assert params.limit == 25
