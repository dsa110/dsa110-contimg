"""
Unit tests for API authentication.

Tests the authentication module including:
- API key validation
- JWT token handling
- Auth context extraction
- Protected endpoint access
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Import auth module
import sys
sys.path.insert(0, str(__file__).rsplit("/tests", 1)[0] + "/src")

from dsa110_contimg.api.auth import (
    AuthContext,
    generate_api_key,
    hash_api_key,
    verify_api_key,
    get_api_keys,
    get_auth_context,
    require_auth,
    require_write_access,
    decode_jwt,
    create_jwt,
)


class TestApiKeyGeneration:
    """Tests for API key generation and hashing."""
    
    def test_generate_api_key_format(self):
        """Generated keys should have dsa110_ prefix."""
        key = generate_api_key()
        assert key.startswith("dsa110_")
        assert len(key) > 20  # Reasonable length
    
    def test_generate_api_key_unique(self):
        """Each generated key should be unique."""
        keys = [generate_api_key() for _ in range(10)]
        assert len(set(keys)) == 10
    
    def test_hash_api_key_deterministic(self):
        """Same key should produce same hash."""
        key = "dsa110_testkey123"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        assert hash1 == hash2
    
    def test_hash_api_key_different_for_different_keys(self):
        """Different keys should produce different hashes."""
        hash1 = hash_api_key("dsa110_key1")
        hash2 = hash_api_key("dsa110_key2")
        assert hash1 != hash2


class TestApiKeyValidation:
    """Tests for API key validation."""
    
    def test_verify_api_key_valid(self):
        """Valid API key should be accepted."""
        test_key = "dsa110_testkey123"
        with patch.dict(os.environ, {"DSA110_API_KEYS": test_key}):
            assert verify_api_key(test_key) is True
    
    def test_verify_api_key_invalid(self):
        """Invalid API key should be rejected."""
        with patch.dict(os.environ, {"DSA110_API_KEYS": "dsa110_validkey"}):
            assert verify_api_key("dsa110_invalidkey") is False
    
    def test_verify_api_key_no_keys_configured(self):
        """Should reject all keys when none configured."""
        with patch.dict(os.environ, {"DSA110_API_KEYS": ""}):
            assert verify_api_key("dsa110_anykey") is False
    
    def test_verify_api_key_multiple_keys(self):
        """Should accept any of multiple configured keys."""
        with patch.dict(os.environ, {"DSA110_API_KEYS": "key1,key2,key3"}):
            assert verify_api_key("key1") is True
            assert verify_api_key("key2") is True
            assert verify_api_key("key3") is True
            assert verify_api_key("key4") is False
    
    def test_get_api_keys_parses_env(self):
        """Should parse comma-separated keys from environment."""
        with patch.dict(os.environ, {"DSA110_API_KEYS": "key1, key2 , key3"}):
            keys = get_api_keys()
            assert keys == ["key1", "key2", "key3"]
    
    def test_get_api_keys_empty(self):
        """Should return empty list when not configured."""
        with patch.dict(os.environ, {"DSA110_API_KEYS": ""}):
            keys = get_api_keys()
            assert keys == []


class TestAuthContext:
    """Tests for AuthContext dataclass."""
    
    def test_auth_context_api_key_allows_write(self):
        """API key auth should allow write access."""
        ctx = AuthContext(authenticated=True, method="api_key", key_id="12345678")
        assert ctx.is_write_allowed is True
    
    def test_auth_context_jwt_with_write_scope(self):
        """JWT with write scope should allow write."""
        ctx = AuthContext(
            authenticated=True,
            method="jwt",
            claims={"sub": "user", "scopes": ["read", "write"]}
        )
        assert ctx.is_write_allowed is True
    
    def test_auth_context_jwt_without_write_scope(self):
        """JWT without write scope should deny write."""
        ctx = AuthContext(
            authenticated=True,
            method="jwt",
            claims={"sub": "user", "scopes": ["read"]}
        )
        assert ctx.is_write_allowed is False
    
    def test_auth_context_jwt_admin_scope(self):
        """JWT with admin scope should allow write."""
        ctx = AuthContext(
            authenticated=True,
            method="jwt",
            claims={"sub": "admin", "scopes": ["admin"]}
        )
        assert ctx.is_write_allowed is True
    
    def test_auth_context_unauthenticated(self):
        """Unauthenticated context should deny write."""
        ctx = AuthContext(authenticated=False, method="none")
        assert ctx.is_write_allowed is False
    
    def test_auth_context_disabled_mode(self):
        """Disabled auth should allow write."""
        ctx = AuthContext(authenticated=True, method="disabled")
        assert ctx.is_write_allowed is True


class TestJWT:
    """Tests for JWT handling."""
    
    def test_create_jwt_requires_secret(self):
        """Should raise error if JWT_SECRET not configured."""
        with patch.dict(os.environ, {"DSA110_JWT_SECRET": ""}):
            with pytest.raises(ValueError, match="JWT_SECRET not configured"):
                create_jwt("testuser")
    
    @pytest.mark.skipif(
        not pytest.importorskip("jwt", reason="PyJWT not installed"),
        reason="PyJWT not installed"
    )
    def test_create_and_decode_jwt(self):
        """Created JWT should be decodable."""
        secret = "testsecret123"
        with patch.dict(os.environ, {"DSA110_JWT_SECRET": secret}):
            # Reimport to pick up the new env var
            from dsa110_contimg.api import auth
            from importlib import reload
            reload(auth)
            
            token = auth.create_jwt("testuser", scopes=["read", "write"])
            claims = auth.decode_jwt(token)
            
            assert claims is not None
            assert claims["sub"] == "testuser"
            assert "read" in claims["scopes"]
            assert "write" in claims["scopes"]
    
    def test_decode_jwt_no_secret(self):
        """Should return None if JWT_SECRET not configured."""
        with patch.dict(os.environ, {"DSA110_JWT_SECRET": ""}):
            result = decode_jwt("sometoken")
            assert result is None
    
    def test_decode_jwt_invalid_token(self):
        """Should return None for invalid token."""
        with patch.dict(os.environ, {"DSA110_JWT_SECRET": "secret"}):
            result = decode_jwt("invalid.token.here")
            assert result is None


class TestAuthDependencies:
    """Tests for FastAPI auth dependencies."""
    
    @pytest.mark.asyncio
    async def test_require_auth_raises_401(self):
        """Should raise 401 for unauthenticated requests."""
        unauth_ctx = AuthContext(authenticated=False, method="none")
        
        with pytest.raises(HTTPException) as exc_info:
            await require_auth(unauth_ctx)
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["code"] == "UNAUTHORIZED"
    
    @pytest.mark.asyncio
    async def test_require_auth_passes_authenticated(self):
        """Should pass through authenticated context."""
        auth_ctx = AuthContext(authenticated=True, method="api_key", key_id="12345678")
        
        result = await require_auth(auth_ctx)
        assert result is auth_ctx
    
    @pytest.mark.asyncio
    async def test_require_write_access_raises_403(self):
        """Should raise 403 for read-only JWT."""
        readonly_ctx = AuthContext(
            authenticated=True,
            method="jwt",
            claims={"scopes": ["read"]}
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await require_write_access(readonly_ctx)
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "FORBIDDEN"
    
    @pytest.mark.asyncio
    async def test_require_write_access_passes_api_key(self):
        """Should pass through API key auth."""
        auth_ctx = AuthContext(authenticated=True, method="api_key", key_id="12345678")
        
        result = await require_write_access(auth_ctx)
        assert result is auth_ctx


class TestAuthDisabled:
    """Tests for disabled auth mode."""
    
    @pytest.mark.asyncio
    async def test_auth_disabled_allows_all(self):
        """Disabled auth should allow all requests."""
        with patch.dict(os.environ, {"DSA110_AUTH_DISABLED": "true"}):
            # Need to reimport to pick up env change
            from dsa110_contimg.api import auth
            from importlib import reload
            reload(auth)
            
            # Create mock request
            mock_request = MagicMock()
            
            ctx = await auth.get_auth_context(mock_request, None, None)
            assert ctx.authenticated is True
            assert ctx.method == "disabled"
