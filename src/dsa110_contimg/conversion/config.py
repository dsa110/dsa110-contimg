"""
Configuration dataclasses for conversion services.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class CalibratorMSConfig:
    """Configuration for calibrator MS generation."""

    input_dir: Path
    output_dir: Path
    products_db: Path
    catalogs: List[Path]
    scratch_dir: Optional[Path] = None
    default_window_minutes: int = 60
    default_max_days_back: int = 14
    default_dec_tolerance_deg: float = 2.0
    auto_configure: bool = True
    auto_register: bool = True
    auto_stage_tmpfs: bool = True

    @classmethod
    def from_env(cls) -> CalibratorMSConfig:
        """Create config from environment variables."""
        # Use PIPELINE_STATE_DIR like the rest of the codebase
        base_state = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
        products_default = base_state / "products.sqlite3"

        # Build catalog list: ALWAYS prefer SQLite database first
        catalogs = []

        # 1. Try SQLite database first (highest priority)
        sqlite_candidates = [
            base_state / "catalogs" / "vla_calibrators.sqlite3",
            Path("/data/dsa110-contimg/state/catalogs/vla_calibrators.sqlite3"),
            Path("state/catalogs/vla_calibrators.sqlite3"),
        ]
        for sqlite_path in sqlite_candidates:
            if sqlite_path.exists():
                catalogs.append(sqlite_path)
                break  # Use first found SQLite DB

        # 2. Add CSV fallbacks (lower priority)
        catalogs.extend(
            [
                Path("/data/dsa110-contimg/data-samples/catalogs/vla_calibrators_parsed.csv"),
                Path("/data/dsa110-contimg/sim-data-samples/catalogs/vla_calibrators_parsed.csv"),
                base_state.parent
                / "references"
                / "dsa110-contimg-main-legacy"
                / "data"
                / "catalogs"
                / "vla_calibrators_parsed.csv",
            ]
        )

        return cls(
            input_dir=Path(os.getenv("CONTIMG_INPUT_DIR", "/data/incoming")),
            output_dir=Path(os.getenv("CONTIMG_OUTPUT_DIR", "/stage/dsa110-contimg/raw/ms")),
            products_db=Path(os.getenv("PIPELINE_PRODUCTS_DB", str(products_default))),
            catalogs=catalogs,
            # scratch_dir=None means "let service decide" - will use tmpfs if available,
            # otherwise falls back to output directory
            scratch_dir=(
                Path(os.getenv("CONTIMG_SCRATCH_DIR")) if os.getenv("CONTIMG_SCRATCH_DIR") else None
            ),
        )
