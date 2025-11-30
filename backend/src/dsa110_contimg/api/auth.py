"""
Authentication module for the DSA-110 API.

Provides API key and optional JWT authentication for protecting write operations.
Read operations remain public for observatory data access.

Usage:
    # In routes that require authentication:
    from .auth import require_api_key, require_write_access
    
    @router.post("/jobs/{run_id}/rerun")
    async def rerun_job(run_id: str, _: str = Depends(require_write_access)):
        ...

Environment Variables:
    DSA110_API_KEYS: Comma-separated list of valid API keys
    DSA110_API_KEY_HEADER: Header name for API key (default: X-API-Key)
    DSA110_JWT_SECRET: Secret for JWT validation (optional)
    DSA110_AUTH_DISABLED: Set to "true" to disable auth (development only)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

# Configuration from environment
API_KEY_HEADER_NAME = os.getenv("DSA110_API_KEY_HEADER", "X-API-Key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


def is_auth_disabled() -> bool:
    """Check if auth is disabled via environment."""
    return os.getenv("DSA110_AUTH_DISABLED", "").lower() == "true"


def get_jwt_secret() -> str:
    """Get JWT secret from environment."""
    return os.getenv("DSA110_JWT_SECRET", "")


def get_api_keys() -> List[str]:
    """Get valid API keys from environment."""
    keys_env = os.getenv("DSA110_API_KEYS", "")
    if not keys_env:
        return []
    return [k.strip() for k in keys_env.split(",") if k.strip()]


def generate_api_key() -> str:
    """Generate a new secure API key."""
    return f"dsa110_{secrets.token_urlsafe(32)}"


def hash_api_key(key: str) -> str:
    """Hash an API key for secure comparison."""
    return hashlib.sha256(key.encode()).hexdigest()


@dataclass
class AuthContext:
    """Authentication context for a request."""
    authenticated: bool
    method: str  # "api_key", "jwt", "none"
    key_id: Optional[str] = None  # Partial key for logging (last 8 chars)
    claims: Optional[dict] = None  # JWT claims if applicable
    
    @property
    def is_write_allowed(self) -> bool:
        """Check if this context allows write operations."""
        if not self.authenticated:
            return False
        # JWT must have "write" scope if present
        if self.method == "jwt" and self.claims:
            scopes = self.claims.get("scopes", [])
            return "write" in scopes or "admin" in scopes
        # API key auth allows all operations
        return True


# FastAPI security schemes
api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def verify_api_key(api_key: str) -> bool:
    """Verify an API key against the configured keys."""
    valid_keys = get_api_keys()
    if not valid_keys:
        logger.warning("No API keys configured - authentication will fail")
        return False
    
    # Use constant-time comparison to prevent timing attacks
    for valid_key in valid_keys:
        if secrets.compare_digest(api_key, valid_key):
            return True
    return False


def decode_jwt(token: str) -> Optional[dict]:
    """Decode and verify a JWT token."""
    jwt_secret = get_jwt_secret()
    if not jwt_secret:
        logger.warning("JWT_SECRET not configured - JWT auth disabled")
        return None
    
    try:
        import jwt
        # Add leeway to handle clock skew between token creation and verification
        payload = jwt.decode(
            token, 
            jwt_secret, 
            algorithms=[JWT_ALGORITHM],
            leeway=timedelta(seconds=10),  # Allow 10 seconds of clock skew
        )
        return payload
    except ImportError:
        logger.warning("PyJWT not installed - JWT auth disabled")
        return None
    except Exception as e:
        logger.debug(f"JWT decode failed: {e}")
        return None


def create_jwt(
    subject: str,
    scopes: List[str] = None,
    expiry_hours: int = JWT_EXPIRY_HOURS,
) -> str:
    """Create a new JWT token."""
    jwt_secret = get_jwt_secret()
    if not jwt_secret:
        raise ValueError("JWT_SECRET not configured")
    
    try:
        import jwt
    except ImportError:
        raise ImportError("PyJWT required for JWT creation: pip install PyJWT")
    
    now = datetime.utcnow()
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),  # Integer timestamps for PyJWT compatibility
        "exp": int((now + timedelta(hours=expiry_hours)).timestamp()),
        "scopes": scopes or ["read"],
    }
    
    return jwt.encode(payload, jwt_secret, algorithm=JWT_ALGORITHM)


async def get_auth_context(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> AuthContext:
    """
    Extract authentication context from request.
    
    Checks in order:
    1. API Key in header
    2. Bearer token (JWT)
    3. No authentication
    """
    # Check if auth is disabled (development mode)
    if is_auth_disabled():
        logger.debug("Authentication disabled via DSA110_AUTH_DISABLED")
        return AuthContext(authenticated=True, method="disabled")
    
    # Try API key first
    if api_key:
        if verify_api_key(api_key):
            key_id = api_key[-8:] if len(api_key) >= 8 else api_key
            logger.debug(f"Authenticated via API key ...{key_id}")
            return AuthContext(
                authenticated=True,
                method="api_key",
                key_id=key_id,
            )
        else:
            logger.warning(f"Invalid API key attempted")
    
    # Try Bearer token (JWT)
    if bearer and bearer.credentials:
        claims = decode_jwt(bearer.credentials)
        if claims:
            logger.debug(f"Authenticated via JWT for subject: {claims.get('sub')}")
            return AuthContext(
                authenticated=True,
                method="jwt",
                claims=claims,
            )
    
    # No authentication
    return AuthContext(authenticated=False, method="none")


async def require_auth(
    auth: AuthContext = Depends(get_auth_context),
) -> AuthContext:
    """
    Dependency that requires any valid authentication.
    
    Raises HTTPException 401 if not authenticated.
    """
    if not auth.authenticated:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "UNAUTHORIZED",
                "http_status": 401,
                "user_message": "Authentication required",
                "action": f"Provide a valid API key in the {API_KEY_HEADER_NAME} header",
                "ref_id": "",
            },
            headers={"WWW-Authenticate": f'ApiKey realm="DSA-110 API"'},
        )
    return auth


async def require_write_access(
    auth: AuthContext = Depends(require_auth),
) -> AuthContext:
    """
    Dependency that requires write access.
    
    Raises HTTPException 403 if authenticated but lacking write permission.
    """
    if not auth.is_write_allowed:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "FORBIDDEN",
                "http_status": 403,
                "user_message": "Write access required",
                "action": "Use an API key or token with write permissions",
                "ref_id": "",
            },
        )
    return auth


# Convenience alias
require_api_key = require_auth
