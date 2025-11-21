"""Configuration helpers for the API layer."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ApiConfig:
    """Runtime configuration for the monitoring API."""

    registry_db: Path
    queue_db: Path
    products_db: Path
    expected_subbands: int = 16

    @classmethod
    def from_env(cls) -> "ApiConfig":
        """Build configuration from environment variables with sane defaults."""

        def safe_int(env_var: str, default: str, min_val: int = 1, max_val: int = 32) -> int:
            """Safely convert environment variable to integer with validation."""
            value_str = os.getenv(env_var, default)
            try:
                value = int(value_str)
                if value < min_val or value > max_val:
                    raise ValueError(f"{env_var}={value} must be between {min_val} and {max_val}")
                return value
            except ValueError as e:
                if "invalid literal" in str(e) or "could not convert" in str(e):
                    raise ValueError(
                        f"Invalid integer value for {env_var}: '{value_str}'. "
                        f"Expected integer between {min_val} and {max_val}."
                    ) from e
                raise

        base_state = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
        registry_default = base_state / "cal_registry.sqlite3"
        queue_default = base_state / "ingest.sqlite3"
        products_default = base_state / "products.sqlite3"

        return cls(
            registry_db=Path(os.getenv("CAL_REGISTRY_DB", registry_default)),
            queue_db=Path(os.getenv("PIPELINE_QUEUE_DB", queue_default)),
            products_db=Path(os.getenv("PIPELINE_PRODUCTS_DB", products_default)),
            expected_subbands=safe_int("PIPELINE_EXPECTED_SUBBANDS", "16"),
        )
