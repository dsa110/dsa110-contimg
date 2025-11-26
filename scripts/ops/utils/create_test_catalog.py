#!/opt/miniforge/envs/casa6/bin/python
"""
Create a test master_sources.sqlite3 database for development/testing.

This creates a minimal catalog with a few reference sources for testing
the photometry normalization without requiring the full NVSS catalog download.
"""

import os
import sqlite3
from pathlib import Path


def create_test_catalog(db_path: str = "state/catalogs/master_sources.sqlite3"):
    """Create a test catalog database with minimal reference sources."""

    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # Create database with test data
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create the main sources table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            source_id INTEGER PRIMARY KEY,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            s_nvss REAL,
            snr_nvss REAL,
            s_vlass REAL,
            alpha REAL,
            resolved_flag INTEGER DEFAULT 0,
            confusion_flag INTEGER DEFAULT 0
        )
    """)

    # Insert test reference sources (bright, stable sources for differential photometry)
    test_sources = [
        # Format: source_id, ra_deg, dec_deg, s_nvss, snr_nvss, s_vlass, alpha, resolved_flag, confusion_flag
        (1, 187.5, 12.4, 0.145, 25.0, 0.098, -0.7, 0, 0),  # Bright reference source
        (2, 187.6, 12.5, 0.089, 22.0, 0.067, -0.5, 0, 0),  # Medium reference source
        (3, 187.4, 12.3, 0.067, 18.0, 0.045, -0.8, 0, 0),  # Fainter reference source
        (4, 187.7, 12.6, 0.123, 28.0, 0.087, -0.6, 0, 0),  # Another bright reference
        (5, 187.3, 12.2, 0.045, 15.0, 0.032, -0.9, 0, 0),  # Faint reference source
    ]

    cursor.executemany(
        "INSERT INTO sources (source_id, ra_deg, dec_deg, s_nvss, snr_nvss, s_vlass, alpha, resolved_flag, confusion_flag) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        test_sources
    )

    # Create the good_references view (high SNR, reasonable spectral index)
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS good_references AS
        SELECT * FROM sources
        WHERE snr_nvss >= 15.0
        AND (alpha IS NULL OR (alpha >= -1.2 AND alpha <= 0.5))
        AND resolved_flag = 0
        AND confusion_flag = 0
    """)

    # Create the final_references view (stricter criteria)
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS final_references AS
        SELECT * FROM sources
        WHERE snr_nvss >= 20.0
        AND s_nvss >= 0.05
        AND (alpha IS NULL OR (alpha >= -1.0 AND alpha <= 0.2))
        AND resolved_flag = 0
        AND confusion_flag = 0
    """)

    # Create metadata table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cursor.execute("""
        INSERT OR REPLACE INTO meta (key, value) VALUES
        ('build_time_iso', '2025-10-26T10:00:00Z'),
        ('description', 'Test catalog with 5 reference sources for development'),
        ('nvss_sources', '5'),
        ('goodref_snr_min', '15.0'),
        ('finalref_snr_min', '20.0')
    """)

    conn.commit()
    conn.close()

    print(f"✓ Created test catalog database: {db_path}")
    print("✓ Added 5 reference sources for testing")
    print("✓ Created good_references and final_references views")
    print("✓ Ready for photometry normalization testing")

    return db_path

if __name__ == "__main__":
    create_test_catalog()
