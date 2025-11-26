"""Helpers for creating fixture products databases with mosaics."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def create_products_db_with_mosaic(tmp_path: Path) -> Path:
    """Create a minimal products DB containing a single mosaic entry."""
    db_path = tmp_path / "products.sqlite3"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE mosaics (
            id INTEGER PRIMARY KEY,
            name TEXT,
            path TEXT,
            created_at REAL,
            start_mjd REAL,
            end_mjd REAL,
            integration_sec REAL,
            n_images INTEGER,
            center_ra_deg REAL,
            center_dec_deg REAL,
            dec_min_deg REAL,
            dec_max_deg REAL,
            noise_jy REAL,
            beam_major_arcsec REAL,
            beam_minor_arcsec REAL,
            beam_pa_deg REAL,
            n_sources INTEGER,
            thumbnail_path TEXT,
            status TEXT,
            method TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO mosaics (
            id, name, path, created_at, start_mjd, end_mjd, integration_sec,
            n_images, center_ra_deg, center_dec_deg, dec_min_deg, dec_max_deg,
            noise_jy, beam_major_arcsec, beam_minor_arcsec, beam_pa_deg,
            n_sources, thumbnail_path, status, method
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            "test_mosaic",
            "/stage/mosaics/test_mosaic.fits",
            1_700_000_000.0,
            60000.0,
            60000.1,
            300.0,
            4,
            150.0,
            30.0,
            29.5,
            30.5,
            0.5,
            60.0,
            55.0,
            0.0,
            12,
            "/stage/mosaics/test_mosaic_thumb.png",
            "completed",
            "mean",
        ),
    )
    conn.commit()
    conn.close()
    return db_path
