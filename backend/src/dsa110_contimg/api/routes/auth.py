"""
Authentication routes for the DSA-110 API.

Provides login, logout, token refresh, and user info endpoints
for the frontend authentication system.

Endpoints:
    POST /auth/login     - Authenticate with username/password
    POST /auth/logout    - Invalidate current session
    POST /auth/refresh   - Refresh access token
    GET  /auth/me        - Get current user info
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

from ..auth import (
    create_jwt,
    decode_jwt,
    get_auth_context,
    AuthContext,
    require_auth,
    get_jwt_secret,
    is_auth_disabled,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# Request/Response Models
# =============================================================================


class LoginRequest(BaseModel):
    """Login request with credentials."""

    username: str = Field(..., min_length=1, max_length=100, description="Username")
    password: str = Field(..., min_length=1, description="Password")
    remember_me: bool = Field(default=False, description="Extend token lifetime")


class TokenResponse(BaseModel):
    """Token response after successful authentication."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="Refresh token for extended sessions")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class UserResponse(BaseModel):
    """User information response."""

    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    role: str = Field(..., description="User role (viewer/operator/admin)")
    full_name: Optional[str] = Field(None, description="Full name")
    created_at: Optional[str] = Field(None, description="Account creation timestamp")
    last_login: Optional[str] = Field(None, description="Last login timestamp")


class LoginResponse(BaseModel):
    """Full login response with user and tokens."""

    user: UserResponse
    tokens: TokenResponse


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str = Field(..., description="Refresh token")


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
    success: bool = True


# =============================================================================
# User Storage (In-memory for now, can be migrated to database)
# =============================================================================

# Password hashing using hashlib (no external dependencies)
def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hash a password with salt using SHA-256."""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return hashed.hex(), salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    """Verify a password against its hash."""
    new_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(new_hash, hashed)


# In-memory user store for demo/development
# In production, this would be backed by a database
_users_db: dict[str, dict] = {}
_refresh_tokens: dict[str, dict] = {}  # refresh_token -> {user_id, expires_at}


def _initialize_demo_users():
    """Initialize demo users for development."""
    demo_users = [
        {
            "id": "user-001",
            "username": "admin",
            "email": "admin@dsa110.caltech.edu",
            "role": "admin",
            "full_name": "System Administrator",
            "password": "admin",
        },
        {
            "id": "user-002",
            "username": "operator",
            "email": "operator@dsa110.caltech.edu",
            "role": "operator",
            "full_name": "Pipeline Operator",
            "password": "operator",
        },
        {
            "id": "user-003",
            "username": "viewer",
            "email": "viewer@dsa110.caltech.edu",
            "role": "viewer",
            "full_name": "Read-only User",
            "password": "viewer",
        },
    ]

    for user in demo_users:
        password = user.pop("password")
        hashed, salt = hash_password(password)
        user["password_hash"] = hashed
        user["password_salt"] = salt
        user["created_at"] = "2024-01-01T00:00:00Z"
        user["last_login"] = None
        _users_db[user["username"]] = user


# Initialize demo users on module load
_initialize_demo_users()


def get_user_by_username(username: str) -> Optional[dict]:
    """Get user by username."""
    return _users_db.get(username)


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Get user by ID."""
    for user in _users_db.values():
        if user["id"] == user_id:
            return user
    return None


def update_last_login(username: str) -> None:
    """Update user's last login timestamp."""
    if username in _users_db:
        _users_db[username]["last_login"] = datetime.utcnow().isoformat() + "Z"


def create_refresh_token(user_id: str, expires_hours: int = 720) -> str:
    """Create a refresh token for a user (default 30 days)."""
    token = secrets.token_urlsafe(32)
    expires_at = time.time() + (expires_hours * 3600)
    _refresh_tokens[token] = {"user_id": user_id, "expires_at": expires_at}
    return token


def validate_refresh_token(token: str) -> Optional[str]:
    """Validate a refresh token and return user_id if valid."""
    data = _refresh_tokens.get(token)
    if not data:
        return None
    if time.time() > data["expires_at"]:
        # Token expired, remove it
        del _refresh_tokens[token]
        return None
    return data["user_id"]


def invalidate_refresh_token(token: str) -> bool:
    """Invalidate a refresh token."""
    if token in _refresh_tokens:
        del _refresh_tokens[token]
        return True
    return False


# =============================================================================
# Route Handlers
# =============================================================================


class AuthStatusResponse(BaseModel):
    """Authentication status response."""

    auth_enabled: bool = Field(..., description="Whether authentication is enabled")
    auth_required: bool = Field(..., description="Whether auth is required for API access")


@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status() -> AuthStatusResponse:
    """
    Get authentication status.

    Returns whether authentication is enabled or disabled.
    This endpoint is always accessible without authentication.
    """
    disabled = is_auth_disabled()
    return AuthStatusResponse(
        auth_enabled=not disabled,
        auth_required=not disabled,
    )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """
    Authenticate user with username and password.

    Returns JWT access token and optional refresh token.
    """
    # Look up user
    user = get_user_by_username(request.username)
    if not user:
        logger.warning(f"Login attempt for unknown user: {request.username}")
        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_CREDENTIALS",
                "http_status": 401,
                "user_message": "Invalid username or password",
                "action": "Check your credentials and try again",
                "ref_id": "",
            },
        )

    # Verify password
    if not verify_password(
        request.password, user["password_hash"], user["password_salt"]
    ):
        logger.warning(f"Invalid password for user: {request.username}")
        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_CREDENTIALS",
                "http_status": 401,
                "user_message": "Invalid username or password",
                "action": "Check your credentials and try again",
                "ref_id": "",
            },
        )

    # Update last login
    update_last_login(request.username)

    # Determine token expiry
    expiry_hours = 720 if request.remember_me else 24  # 30 days or 1 day

    # Create JWT access token
    scopes = ["read"]
    if user["role"] in ("operator", "admin"):
        scopes.append("write")
    if user["role"] == "admin":
        scopes.append("admin")

    access_token = create_jwt(
        subject=user["id"],
        scopes=scopes,
        expiry_hours=min(expiry_hours, 24),  # Access token max 24h
    )

    # Create refresh token if remember_me
    refresh_token = None
    if request.remember_me:
        refresh_token = create_refresh_token(user["id"], expiry_hours)

    logger.info(f"User logged in: {request.username} (role={user['role']})")

    return LoginResponse(
        user=UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            role=user["role"],
            full_name=user.get("full_name"),
            created_at=user.get("created_at"),
            last_login=user.get("last_login"),
        ),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=min(expiry_hours, 24) * 3600,
        ),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    auth: AuthContext = Depends(get_auth_context),
) -> MessageResponse:
    """
    Log out the current user.

    Invalidates the refresh token if provided in the request body.
    """
    # Try to get refresh token from request body
    try:
        body = await request.json()
        refresh_token = body.get("refresh_token")
        if refresh_token:
            invalidate_refresh_token(refresh_token)
    except Exception:
        pass  # No body or invalid JSON

    logger.info(f"User logged out (method={auth.method})")
    return MessageResponse(message="Logged out successfully")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(request: RefreshRequest) -> TokenResponse:
    """
    Refresh access token using a refresh token.

    Returns a new access token. The refresh token remains valid until expiry.
    """
    # Validate refresh token
    user_id = validate_refresh_token(request.refresh_token)
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_REFRESH_TOKEN",
                "http_status": 401,
                "user_message": "Invalid or expired refresh token",
                "action": "Please log in again",
                "ref_id": "",
            },
        )

    # Get user
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "USER_NOT_FOUND",
                "http_status": 401,
                "user_message": "User account not found",
                "action": "Please log in again",
                "ref_id": "",
            },
        )

    # Create new access token
    scopes = ["read"]
    if user["role"] in ("operator", "admin"):
        scopes.append("write")
    if user["role"] == "admin":
        scopes.append("admin")

    access_token = create_jwt(
        subject=user["id"],
        scopes=scopes,
        expiry_hours=24,
    )

    logger.debug(f"Token refreshed for user: {user['username']}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=request.refresh_token,  # Return same refresh token
        token_type="Bearer",
        expires_in=24 * 3600,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    auth: AuthContext = Depends(require_auth),
) -> UserResponse:
    """
    Get the current authenticated user's information.

    Requires a valid access token.
    """
    # Get user ID from auth context
    user_id = None
    if auth.claims:
        user_id = auth.claims.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_TOKEN",
                "http_status": 401,
                "user_message": "Invalid access token",
                "action": "Please log in again",
                "ref_id": "",
            },
        )

    # Get user
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "USER_NOT_FOUND",
                "http_status": 404,
                "user_message": "User account not found",
                "action": "Please contact support",
                "ref_id": "",
            },
        )

    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        role=user["role"],
        full_name=user.get("full_name"),
        created_at=user.get("created_at"),
        last_login=user.get("last_login"),
    )
