"""
HTTPS/TLS and security configuration for the DSA-110 API.

Provides:
- TLS certificate configuration
- Security headers middleware
- HSTS support
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class TLSConfig:
    """TLS/SSL certificate configuration."""

    enabled: bool = False
    cert_file: Optional[Path] = None
    key_file: Optional[Path] = None
    ca_file: Optional[Path] = None

    @classmethod
    def from_env(cls) -> "TLSConfig":
        """Create TLS config from environment variables."""
        enabled = os.getenv("DSA110_TLS_ENABLED", "false").lower() == "true"

        cert_path = os.getenv("DSA110_TLS_CERT")
        key_path = os.getenv("DSA110_TLS_KEY")
        ca_path = os.getenv("DSA110_TLS_CA")

        return cls(
            enabled=enabled,
            cert_file=Path(cert_path) if cert_path else None,
            key_file=Path(key_path) if key_path else None,
            ca_file=Path(ca_path) if ca_path else None,
        )

    def validate(self) -> list:
        """Validate TLS configuration. Returns list of errors."""
        errors = []
        if self.enabled:
            if not self.cert_file or not self.cert_file.exists():
                errors.append(f"TLS cert file not found: {self.cert_file}")
            if not self.key_file or not self.key_file.exists():
                errors.append(f"TLS key file not found: {self.key_file}")
        return errors

    def get_uvicorn_ssl_kwargs(self) -> dict:
        """Get SSL kwargs for uvicorn."""
        if not self.enabled:
            return {}

        kwargs = {}
        if self.cert_file:
            kwargs["ssl_certfile"] = str(self.cert_file)
        if self.key_file:
            kwargs["ssl_keyfile"] = str(self.key_file)
        if self.ca_file:
            kwargs["ssl_ca_certs"] = str(self.ca_file)

        return kwargs


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security (HSTS) when in production
    - Content-Security-Policy
    - Referrer-Policy
    """

    def __init__(
        self,
        app,
        enable_hsts: bool = False,
        hsts_max_age: int = 31536000,  # 1 year
        enable_csp: bool = True,
    ):
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.hsts_max_age = hsts_max_age
        self.enable_csp = enable_csp

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # XSS protection (legacy, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS (only when enabled - typically in production with HTTPS)
        if self.enable_hsts:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains"
            )

        # Content Security Policy (for API, be restrictive)
        if self.enable_csp:
            # API endpoints generally shouldn't serve scripts
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
            )

        return response


class CachingHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add caching headers based on response type.

    Supports:
    - Cache-Control headers for different content types
    - ETag generation (placeholder for hash-based implementation)
    - Vary headers for content negotiation
    """

    # Default cache durations in seconds
    CACHE_DURATIONS = {
        "static": 86400,  # 1 day for static files
        "list": 60,  # 1 minute for list endpoints
        "detail": 300,  # 5 minutes for detail endpoints
        "none": 0,  # No caching
    }

    def __init__(
        self,
        app,
        default_max_age: int = 0,
        private: bool = True,
    ):
        super().__init__(app)
        self.default_max_age = default_max_age
        self.private = private

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Skip if already has Cache-Control
        if "Cache-Control" in response.headers:
            return response

        # Determine cache strategy based on path and method
        path = request.url.path
        method = request.method

        # No caching for write operations
        if method not in ("GET", "HEAD"):
            response.headers["Cache-Control"] = "no-store"
            return response

        # Determine cache duration based on endpoint type
        max_age = self._get_cache_duration(path)

        if max_age == 0:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        else:
            privacy = "private" if self.private else "public"
            response.headers["Cache-Control"] = f"{privacy}, max-age={max_age}"

        # Add Vary header for content negotiation
        response.headers["Vary"] = "Accept, Accept-Encoding, Authorization"

        return response

    def _get_cache_duration(self, path: str) -> int:
        """Determine cache duration based on path."""
        # Health endpoints - no caching
        if "/health" in path:
            return 0

        # Metrics - no caching
        if "/metrics" in path:
            return 0

        # Jobs/queue - no caching (dynamic state)
        if "/jobs" in path or "/queue" in path:
            return 0

        # Static files - long cache
        if path.endswith((".fits", ".png", ".jpg")):
            return self.CACHE_DURATIONS["static"]

        # List endpoints - short cache
        if path.endswith(("/images", "/sources", "/ms")):
            return self.CACHE_DURATIONS["list"]

        # Detail endpoints - medium cache
        if any(x in path for x in ["/images/", "/sources/", "/ms/"]):
            return self.CACHE_DURATIONS["detail"]

        return self.default_max_age


def generate_etag(content: bytes) -> str:
    """Generate ETag from content hash."""
    import hashlib

    return f'"{hashlib.md5(content).hexdigest()}"'


def check_etag_match(request_etag: Optional[str], response_etag: str) -> bool:
    """Check if client ETag matches response ETag."""
    if not request_etag:
        return False

    # Handle weak ETags
    request_etag = request_etag.replace("W/", "")
    response_etag = response_etag.replace("W/", "")

    return request_etag.strip('"') == response_etag.strip('"')


# Configuration for production deployment
PRODUCTION_NGINX_CONFIG = """
# Nginx configuration for DSA-110 API with TLS
# Place in /etc/nginx/sites-available/dsa110-api

server {
    listen 80;
    server_name api.dsa110.example.org;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.dsa110.example.org;

    # TLS certificates (use Let's Encrypt or institutional CA)
    ssl_certificate /etc/letsencrypt/live/api.dsa110.example.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.dsa110.example.org/privkey.pem;

    # Modern TLS configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
"""
