"""
Authentication and authorization for the DSA-110 API.
Implements JWT token-based authentication with role-based access control (RBAC).
"""

from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-secret-key-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# HTTP Bearer token scheme
security = HTTPBearer()


# User roles
class UserRole:
    OBSERVER = "observer"
    OPERATOR = "operator"
    SCIENTIST = "scientist"
    ADMIN = "admin"

    @staticmethod
    def get_hierarchy(role: str) -> int:
        """Get role hierarchy level (higher = more permissions)."""
        hierarchy = {
            UserRole.OBSERVER: 1,
            UserRole.OPERATOR: 2,
            UserRole.SCIENTIST: 3,
            UserRole.ADMIN: 4,
        }
        return hierarchy.get(role, 0)

    @staticmethod
    def has_permission(user_role: str, required_role: str) -> bool:
        """Check if user role has permission for required role."""
        return UserRole.get_hierarchy(user_role) >= UserRole.get_hierarchy(
            required_role
        )


# Pydantic models
class User(BaseModel):
    username: str
    email: Optional[str] = None
    role: str
    created_at: Optional[datetime] = None


class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str
    role: str = UserRole.OBSERVER


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


# Database helper
def get_users_db_path() -> Path:
    """Get path to users database."""
    state_dir = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
    return state_dir / "users.sqlite3"


def init_users_db():
    """Initialize users database."""
    db_path = get_users_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(str(db_path))) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'observer',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_username ON users(username)
        """
        )
        conn.commit()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_user(
    username: str,
    password: str,
    email: Optional[str] = None,
    role: str = UserRole.OBSERVER,
) -> User:
    """Create a new user."""
    init_users_db()
    db_path = get_users_db_path()

    password_hash = get_password_hash(password)

    with closing(sqlite3.connect(str(db_path))) as conn:
        try:
            conn.execute(
                """
                INSERT INTO users (username, email, password_hash, role)
                VALUES (?, ?, ?, ?)
            """,
                (username, email, password_hash, role),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )

    return User(username=username, email=email, role=role, created_at=datetime.utcnow())


def get_user_by_username(username: str) -> Optional[User]:
    """Get user by username."""
    init_users_db()
    db_path = get_users_db_path()

    with closing(sqlite3.connect(str(db_path))) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT username, email, role, created_at
            FROM users
            WHERE username = ?
        """,
            (username,),
        ).fetchone()

        if row:
            return User(
                username=row["username"],
                email=row["email"],
                role=row["role"],
                created_at=(
                    datetime.fromisoformat(row["created_at"])
                    if row["created_at"]
                    else None
                ),
            )
    return None


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate a user."""
    init_users_db()
    db_path = get_users_db_path()

    with closing(sqlite3.connect(str(db_path))) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT username, email, password_hash, role, created_at
            FROM users
            WHERE username = ?
        """,
            (username,),
        ).fetchone()

        if not row:
            return None

        if not verify_password(password, row["password_hash"]):
            return None

        # Update last login
        conn.execute(
            """
            UPDATE users
            SET last_login = CURRENT_TIMESTAMP
            WHERE username = ?
        """,
            (username,),
        )
        conn.commit()

        return User(
            username=row["username"],
            email=row["email"],
            role=row["role"],
            created_at=(
                datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
            ),
        )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role", UserRole.OBSERVER)
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return TokenData(username=username, role=role)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Get current authenticated user."""
    token_data = verify_token(credentials.credentials)
    user = get_user_by_username(token_data.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


def require_role(required_role: str):
    """Dependency to require a specific role."""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not UserRole.has_permission(current_user.role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role} role or higher",
            )
        return current_user

    return role_checker
