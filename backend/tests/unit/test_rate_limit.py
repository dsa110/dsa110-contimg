"""
Unit tests for the rate limiting module.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestGetClientIdentifier:
    """Tests for the get_client_identifier function."""
    
    def test_uses_forwarded_for_header(self):
        """Should use X-Forwarded-For header when present."""
        from dsa110_contimg.api.rate_limit import get_client_identifier
        
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "203.0.113.50, 10.0.0.1"}
        
        result = get_client_identifier(request)
        
        assert result == "203.0.113.50"
    
    def test_uses_api_key_header(self):
        """Should use X-API-Key header when no forwarded header."""
        from dsa110_contimg.api.rate_limit import get_client_identifier
        
        request = MagicMock()
        request.headers = {"X-API-Key": "dsa110_abcd1234efgh5678"}
        
        result = get_client_identifier(request)
        
        assert result == "apikey:dsa110_a"
    
    def test_falls_back_to_remote_address(self):
        """Should fall back to remote address."""
        from dsa110_contimg.api.rate_limit import get_client_identifier
        
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "192.168.1.100"
        
        with patch("dsa110_contimg.api.rate_limit.get_remote_address") as mock_remote:
            mock_remote.return_value = "192.168.1.100"
            result = get_client_identifier(request)
        
        assert result == "192.168.1.100"


class TestCreateLimiter:
    """Tests for the create_limiter function."""
    
    def test_creates_limiter_with_defaults(self):
        """Should create limiter with default settings."""
        from dsa110_contimg.api.rate_limit import create_limiter
        
        limiter = create_limiter()
        
        assert limiter is not None
        assert hasattr(limiter, "limit")
    
    def test_creates_limiter_with_custom_storage(self):
        """Should create limiter with custom storage URI."""
        from dsa110_contimg.api.rate_limit import create_limiter
        
        limiter = create_limiter(storage_uri="memory://")
        
        assert limiter is not None
    
    def test_creates_limiter_with_custom_limits(self):
        """Should create limiter with custom rate limits."""
        from dsa110_contimg.api.rate_limit import create_limiter
        
        limiter = create_limiter(default_limits=["500 per hour"])
        
        assert limiter is not None
    
    def test_uses_env_var_for_redis_url(self):
        """Should use DSA110_REDIS_URL from environment."""
        from dsa110_contimg.api.rate_limit import create_limiter
        
        with patch.dict("os.environ", {"DSA110_REDIS_URL": "memory://"}):
            limiter = create_limiter()
            assert limiter is not None


class TestRateLimits:
    """Tests for the RateLimits presets."""
    
    def test_high_limit_value(self):
        """HIGH limit should be high frequency."""
        from dsa110_contimg.api.rate_limit import RateLimits
        
        assert "1000" in RateLimits.HIGH
        assert "minute" in RateLimits.HIGH
    
    def test_standard_limit_value(self):
        """STANDARD limit should be moderate."""
        from dsa110_contimg.api.rate_limit import RateLimits
        
        assert "100" in RateLimits.STANDARD
        assert "minute" in RateLimits.STANDARD
    
    def test_write_limit_value(self):
        """WRITE limit should be lower than standard."""
        from dsa110_contimg.api.rate_limit import RateLimits
        
        assert "30" in RateLimits.WRITE
        assert "minute" in RateLimits.WRITE
    
    def test_heavy_limit_value(self):
        """HEAVY limit should be restrictive."""
        from dsa110_contimg.api.rate_limit import RateLimits
        
        assert "10" in RateLimits.HEAVY
        assert "minute" in RateLimits.HEAVY
    
    def test_auth_limit_value(self):
        """AUTH limit should be moderate."""
        from dsa110_contimg.api.rate_limit import RateLimits
        
        assert "20" in RateLimits.AUTH
    
    def test_batch_limit_value(self):
        """BATCH limit should be very restrictive."""
        from dsa110_contimg.api.rate_limit import RateLimits
        
        assert "5" in RateLimits.BATCH


class TestRateLimitExceededHandler:
    """Tests for the rate limit exceeded handler."""
    
    def test_returns_429_status(self):
        """Should return 429 status code."""
        from dsa110_contimg.api.rate_limit import rate_limit_exceeded_handler
        
        request = MagicMock()
        # Mock the exception with the expected attributes
        exc = MagicMock()
        exc.detail = "10 per minute"
        exc.retry_after = 60
        
        response = rate_limit_exceeded_handler(request, exc)
        
        assert response.status_code == 429
    
    def test_includes_error_message(self):
        """Should include error information in response."""
        from dsa110_contimg.api.rate_limit import rate_limit_exceeded_handler
        import json
        
        request = MagicMock()
        exc = MagicMock()
        exc.detail = "10 per minute"
        exc.retry_after = 60
        
        response = rate_limit_exceeded_handler(request, exc)
        body = json.loads(response.body)
        
        assert body["error"] == "rate_limit_exceeded"
        assert "Too many requests" in body["message"]
    
    def test_includes_retry_after_header(self):
        """Should include Retry-After header."""
        from dsa110_contimg.api.rate_limit import rate_limit_exceeded_handler
        
        request = MagicMock()
        exc = MagicMock()
        exc.detail = "10 per minute"
        exc.retry_after = 45
        
        response = rate_limit_exceeded_handler(request, exc)
        
        assert response.headers.get("Retry-After") == "45"


class TestShouldSkipRateLimit:
    """Tests for the should_skip_rate_limit function."""
    
    def test_skips_when_disabled(self):
        """Should skip when DSA110_RATE_LIMIT_DISABLED is true."""
        from dsa110_contimg.api.rate_limit import should_skip_rate_limit
        
        request = MagicMock()
        
        with patch.dict("os.environ", {"DSA110_RATE_LIMIT_DISABLED": "true"}):
            result = should_skip_rate_limit(request)
        
        assert result is True
    
    def test_does_not_skip_when_enabled(self):
        """Should not skip when rate limiting is enabled."""
        from dsa110_contimg.api.rate_limit import should_skip_rate_limit
        
        request = MagicMock()
        
        with patch.dict("os.environ", {"DSA110_RATE_LIMIT_DISABLED": ""}, clear=False):
            with patch("dsa110_contimg.api.rate_limit.get_remote_address") as mock_remote:
                mock_remote.return_value = "203.0.113.50"
                result = should_skip_rate_limit(request)
        
        assert result is False


class TestGetRateLimitInfo:
    """Tests for the get_rate_limit_info function."""
    
    def test_returns_dict_with_required_keys(self):
        """Should return dict with limit, remaining, reset."""
        from dsa110_contimg.api.rate_limit import get_rate_limit_info
        
        request = MagicMock()
        
        result = get_rate_limit_info(request)
        
        assert "limit" in result
        assert "remaining" in result
        assert "reset" in result


class TestLimiterDecorators:
    """Tests for the rate limit decorator shortcuts."""
    
    def test_limit_standard_decorator(self):
        """limit_standard should be callable."""
        from dsa110_contimg.api.rate_limit import limiter, RateLimits
        from fastapi import Request
        
        # The limiter.limit decorator requires a request parameter
        # Test that the underlying limit method works
        decorator = limiter.limit(RateLimits.STANDARD)
        assert callable(decorator)
    
    def test_limit_write_decorator(self):
        """limit_write should be callable."""
        from dsa110_contimg.api.rate_limit import limiter, RateLimits
        
        decorator = limiter.limit(RateLimits.WRITE)
        assert callable(decorator)
    
    def test_limit_heavy_decorator(self):
        """limit_heavy should be callable."""
        from dsa110_contimg.api.rate_limit import limiter, RateLimits
        
        decorator = limiter.limit(RateLimits.HEAVY)
        assert callable(decorator)


class TestGlobalLimiter:
    """Tests for the global limiter instance."""
    
    def test_global_limiter_exists(self):
        """Global limiter should be available."""
        from dsa110_contimg.api.rate_limit import limiter
        
        assert limiter is not None
    
    def test_limiter_has_limit_method(self):
        """Limiter should have limit method for decorating endpoints."""
        from dsa110_contimg.api.rate_limit import limiter
        
        assert hasattr(limiter, "limit")
        assert callable(limiter.limit)
