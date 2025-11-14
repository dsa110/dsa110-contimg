"""
Build per-declination strip SQLite databases from source catalogs.

These databases are optimized for fast spatial queries during long-term
drift scan operations at fixed declinations.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord


def build_nvss_strip_db(
    dec_center: float,
    dec_range: Tuple[float, float],
    output_path: Optional[str | os.PathLike[str]] = None,
    nvss_csv_path: Optional[str] = None,
    min_flux_mjy: Optional[float] = None,
) -> Path:
    """Build SQLite database for NVSS sources in a declination strip.

    Args:
        dec_center: Center declination in degrees
        dec_range: Tuple of (dec_min, dec_max) in degrees
        output_path: Output SQLite database path (auto-generated if None)
        nvss_csv_path: Path to full NVSS CSV catalog (downloaded if None)
        min_flux_mjy: Minimum flux threshold in mJy (None = no threshold)

    Returns:
        Path to created SQLite database
    """
    dec_min, dec_max = dec_range

    # Resolve output path
    if output_path is None:
        dec_rounded = round(dec_center, 1)
        db_name = f"nvss_dec{dec_rounded:+.1f}.sqlite3"
        output_path = Path("state/catalogs") / db_name

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load NVSS catalog
    if nvss_csv_path is None:
        from dsa110_contimg.calibration.catalogs import read_nvss_catalog

        df_full = read_nvss_catalog()
    else:
        from dsa110_contimg.calibration.catalogs import read_nvss_catalog

        # If CSV path provided, we'd need to read it differently
        # For now, use the cached read function
        df_full = read_nvss_catalog()

    # Filter to declination strip
    dec_col = "dec" if "dec" in df_full.columns else "dec_deg"
    df_strip = df_full[(df_full[dec_col] >= dec_min) & (df_full[dec_col] <= dec_max)].copy()

    print(f"Filtered NVSS catalog: {len(df_full)} → {len(df_strip)} sources")
    print(f"Declination range: {dec_min:.6f} to {dec_max:.6f} degrees")

    # Apply flux threshold if specified
    if min_flux_mjy is not None:
        flux_col = "flux_20_cm" if "flux_20_cm" in df_strip.columns else "flux_mjy"
        if flux_col in df_strip.columns:
            flux_val = pd.to_numeric(df_strip[flux_col], errors="coerce")
            df_strip = df_strip[flux_val >= min_flux_mjy].copy()
            print(f"After flux cut ({min_flux_mjy} mJy): {len(df_strip)} sources")

    # Standardize column names
    ra_col = "ra" if "ra" in df_strip.columns else "ra_deg"
    dec_col = "dec" if "dec" in df_strip.columns else "dec_deg"
    flux_col = "flux_20_cm" if "flux_20_cm" in df_strip.columns else "flux_mjy"

    # Ensure flux is in mJy
    df_strip["ra_deg"] = pd.to_numeric(df_strip[ra_col], errors="coerce")
    df_strip["dec_deg"] = pd.to_numeric(df_strip[dec_col], errors="coerce")

    if flux_col in df_strip.columns:
        df_strip["flux_mjy"] = pd.to_numeric(df_strip[flux_col], errors="coerce")
    else:
        df_strip["flux_mjy"] = None

    # Create SQLite database
    print(f"Creating SQLite database: {output_path}")

    with sqlite3.connect(str(output_path)) as conn:
        # Create sources table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ra_deg REAL NOT NULL,
                dec_deg REAL NOT NULL,
                flux_mjy REAL,
                UNIQUE(ra_deg, dec_deg)
            )
        """
        )

        # Create spatial index
        conn.execute("CREATE INDEX IF NOT EXISTS idx_radec ON sources(ra_deg, dec_deg)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dec ON sources(dec_deg)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_flux ON sources(flux_mjy)")

        # Clear existing data
        conn.execute("DELETE FROM sources")

        # Insert sources
        insert_data = []
        for _, row in df_strip.iterrows():
            ra = float(row["ra_deg"])
            dec = float(row["dec_deg"])
            flux = float(row["flux_mjy"]) if pd.notna(row.get("flux_mjy")) else None

            if np.isfinite(ra) and np.isfinite(dec):
                insert_data.append((ra, dec, flux))

        conn.executemany(
            "INSERT OR IGNORE INTO sources(ra_deg, dec_deg, flux_mjy) VALUES(?, ?, ?)",
            insert_data,
        )

        # Create metadata table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
        )

        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_center', ?)",
            (str(dec_center),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_min', ?)",
            (str(dec_min),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_max', ?)",
            (str(dec_max),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('build_time_iso', ?)",
            (datetime.now(timezone.utc).isoformat(),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('n_sources', ?)",
            (str(len(insert_data)),),
        )
        if min_flux_mjy is not None:
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('min_flux_mjy', ?)",
                (str(min_flux_mjy),),
            )

        conn.commit()

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"✓ Database created: {output_path}")
    print(f"  Size: {file_size_mb:.2f} MB")
    print(f"  Sources: {len(insert_data)}")

    return output_path


def build_first_strip_db(
    dec_center: float,
    dec_range: Tuple[float, float],
    first_catalog_path: Optional[str] = None,
    output_path: Optional[str | os.PathLike[str]] = None,
    min_flux_mjy: Optional[float] = None,
    cache_dir: str = ".cache/catalogs",
) -> Path:
    """Build SQLite database for FIRST sources in a declination strip.

    Args:
        dec_center: Center declination in degrees
        dec_range: Tuple of (dec_min, dec_max) in degrees
        first_catalog_path: Optional path to FIRST catalog (CSV/FITS).
                           If None, attempts to auto-download/cache like NVSS.
        output_path: Output SQLite database path (auto-generated if None)
        min_flux_mjy: Minimum flux threshold in mJy (None = no threshold)
        cache_dir: Directory for caching catalog files (if auto-downloading)

    Returns:
        Path to created SQLite database
    """
    from dsa110_contimg.calibration.catalogs import read_first_catalog
    from dsa110_contimg.catalog.build_master import _normalize_columns

    dec_min, dec_max = dec_range

    # Resolve output path
    if output_path is None:
        dec_rounded = round(dec_center, 1)
        db_name = f"first_dec{dec_rounded:+.1f}.sqlite3"
        output_path = Path("state/catalogs") / db_name

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load FIRST catalog (auto-downloads if needed, similar to NVSS)
    df_full = read_first_catalog(cache_dir=cache_dir, first_catalog_path=first_catalog_path)

    # Normalize column names (similar to build_master.py)
    FIRST_CANDIDATES = {
        "ra": ["ra", "ra_deg", "raj2000"],
        "dec": ["dec", "dec_deg", "dej2000"],
        "flux": [
            "peak_flux",
            "peak_mjy_per_beam",
            "flux_peak",
            "flux",
            "total_flux",
            "fpeak",
        ],
        "maj": ["deconv_maj", "maj", "fwhm_maj", "deconvolved_major", "maj_deconv"],
        "min": ["deconv_min", "min", "fwhm_min", "deconvolved_minor", "min_deconv"],
    }

    col_map = _normalize_columns(df_full, FIRST_CANDIDATES)

    # Standardize column names
    ra_col = col_map.get("ra", "ra")
    dec_col = col_map.get("dec", "dec")
    flux_col = col_map.get("flux", None)
    maj_col = col_map.get("maj", None)
    min_col = col_map.get("min", None)

    # Filter to declination strip
    df_strip = df_full[
        (pd.to_numeric(df_full[dec_col], errors="coerce") >= dec_min)
        & (pd.to_numeric(df_full[dec_col], errors="coerce") <= dec_max)
    ].copy()

    print(f"Filtered FIRST catalog: {len(df_full)} → {len(df_strip)} sources")
    print(f"Declination range: {dec_min:.6f} to {dec_max:.6f} degrees")

    # Apply flux threshold if specified
    if min_flux_mjy is not None and flux_col:
        flux_val = pd.to_numeric(df_strip[flux_col], errors="coerce")
        # Convert to mJy if needed (assume > 1000 means Jy, otherwise mJy)
        if len(flux_val) > 0 and flux_val.max() > 1000:
            flux_val = flux_val * 1000.0  # Convert Jy to mJy
        df_strip = df_strip[flux_val >= min_flux_mjy].copy()
        print(f"After flux cut ({min_flux_mjy} mJy): {len(df_strip)} sources")

    # Create SQLite database
    print(f"Creating SQLite database: {output_path}")

    with sqlite3.connect(str(output_path)) as conn:
        # Create sources table with FIRST-specific columns
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ra_deg REAL NOT NULL,
                dec_deg REAL NOT NULL,
                flux_mjy REAL,
                maj_arcsec REAL,
                min_arcsec REAL,
                UNIQUE(ra_deg, dec_deg)
            )
        """
        )

        # Create spatial index
        conn.execute("CREATE INDEX IF NOT EXISTS idx_radec ON sources(ra_deg, dec_deg)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dec ON sources(dec_deg)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_flux ON sources(flux_mjy)")

        # Clear existing data
        conn.execute("DELETE FROM sources")

        # Insert sources
        insert_data = []
        for _, row in df_strip.iterrows():
            ra = pd.to_numeric(row[ra_col], errors="coerce")
            dec = pd.to_numeric(row[dec_col], errors="coerce")

            if not (np.isfinite(ra) and np.isfinite(dec)):
                continue

            # Handle flux
            flux = None
            if flux_col and flux_col in row.index:
                flux_val = pd.to_numeric(row[flux_col], errors="coerce")
                if np.isfinite(flux_val):
                    # Convert to mJy if needed (assume > 1000 means Jy, otherwise mJy)
                    flux_val_float = float(flux_val)
                    if flux_val_float > 1000:
                        flux = flux_val_float * 1000.0  # Convert Jy to mJy
                    else:
                        flux = flux_val_float

            # Handle size
            maj = None
            if maj_col and maj_col in row.index:
                maj_val = pd.to_numeric(row[maj_col], errors="coerce")
                if np.isfinite(maj_val):
                    maj = float(maj_val)

            min_val = None
            if min_col and min_col in row.index:
                min_val_num = pd.to_numeric(row[min_col], errors="coerce")
                if np.isfinite(min_val_num):
                    min_val = float(min_val_num)

            insert_data.append((ra, dec, flux, maj, min_val))

        conn.executemany(
            "INSERT OR IGNORE INTO sources(ra_deg, dec_deg, flux_mjy, maj_arcsec, min_arcsec) VALUES(?, ?, ?, ?, ?)",
            insert_data,
        )

        # Create metadata table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
        )

        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_center', ?)",
            (str(dec_center),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_min', ?)",
            (str(dec_min),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_max', ?)",
            (str(dec_max),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('build_time_iso', ?)",
            (datetime.now(timezone.utc).isoformat(),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('n_sources', ?)",
            (str(len(insert_data)),),
        )
        source_file_str = (
            str(first_catalog_path) if first_catalog_path else "auto-downloaded/cached"
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('source_file', ?)",
            (source_file_str,),
        )
        if min_flux_mjy is not None:
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('min_flux_mjy', ?)",
                (str(min_flux_mjy),),
            )

        conn.commit()

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"✓ Database created: {output_path}")
    print(f"  Size: {file_size_mb:.2f} MB")
    print(f"  Sources: {len(insert_data)}")

    return output_path


def build_rax_strip_db(
    dec_center: float,
    dec_range: Tuple[float, float],
    rax_catalog_path: Optional[str] = None,
    output_path: Optional[str | os.PathLike[str]] = None,
    min_flux_mjy: Optional[float] = None,
    cache_dir: str = ".cache/catalogs",
) -> Path:
    """Build SQLite database for RAX sources in a declination strip.

    Args:
        dec_center: Center declination in degrees
        dec_range: Tuple of (dec_min, dec_max) in degrees
        rax_catalog_path: Optional path to RAX catalog (CSV/FITS).
                         If None, attempts to find cached catalog.
        output_path: Output SQLite database path (auto-generated if None)
        min_flux_mjy: Minimum flux threshold in mJy (None = no threshold)
        cache_dir: Directory for caching catalog files

    Returns:
        Path to created SQLite database
    """
    from dsa110_contimg.calibration.catalogs import read_rax_catalog
    from dsa110_contimg.catalog.build_master import _normalize_columns

    dec_min, dec_max = dec_range

    # Resolve output path
    if output_path is None:
        dec_rounded = round(dec_center, 1)
        db_name = f"rax_dec{dec_rounded:+.1f}.sqlite3"
        output_path = Path("state/catalogs") / db_name

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load RAX catalog (uses cached or provided path)
    df_full = read_rax_catalog(cache_dir=cache_dir, rax_catalog_path=rax_catalog_path)

    # Normalize column names (RAX typically similar to NVSS structure)
    RAX_CANDIDATES = {
        "ra": ["ra", "ra_deg", "raj2000", "ra_hms"],
        "dec": ["dec", "dec_deg", "dej2000", "dec_dms"],
        "flux": ["flux", "flux_mjy", "flux_jy", "peak_flux", "fpeak", "s1.4"],
    }

    col_map = _normalize_columns(df_full, RAX_CANDIDATES)

    # Standardize column names
    ra_col = col_map.get("ra", "ra")
    dec_col = col_map.get("dec", "dec")
    flux_col = col_map.get("flux", None)

    # Filter to declination strip
    df_strip = df_full[
        (pd.to_numeric(df_full[dec_col], errors="coerce") >= dec_min)
        & (pd.to_numeric(df_full[dec_col], errors="coerce") <= dec_max)
    ].copy()

    print(f"Filtered RAX catalog: {len(df_full)} → {len(df_strip)} sources")
    print(f"Declination range: {dec_min:.6f} to {dec_max:.6f} degrees")

    # Apply flux threshold if specified
    if min_flux_mjy is not None and flux_col:
        flux_val = pd.to_numeric(df_strip[flux_col], errors="coerce")
        # Convert to mJy if needed (assume > 1000 means Jy, otherwise mJy)
        if len(flux_val) > 0 and flux_val.max() > 1000:
            flux_val = flux_val * 1000.0  # Convert Jy to mJy
        df_strip = df_strip[flux_val >= min_flux_mjy].copy()
        print(f"After flux cut ({min_flux_mjy} mJy): {len(df_strip)} sources")

    # Create SQLite database
    print(f"Creating SQLite database: {output_path}")

    with sqlite3.connect(str(output_path)) as conn:
        # Create sources table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ra_deg REAL NOT NULL,
                dec_deg REAL NOT NULL,
                flux_mjy REAL,
                UNIQUE(ra_deg, dec_deg)
            )
        """
        )

        # Create spatial index
        conn.execute("CREATE INDEX IF NOT EXISTS idx_radec ON sources(ra_deg, dec_deg)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dec ON sources(dec_deg)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_flux ON sources(flux_mjy)")

        # Clear existing data
        conn.execute("DELETE FROM sources")

        # Insert sources
        insert_data = []
        for _, row in df_strip.iterrows():
            ra = pd.to_numeric(row[ra_col], errors="coerce")
            dec = pd.to_numeric(row[dec_col], errors="coerce")

            if not (np.isfinite(ra) and np.isfinite(dec)):
                continue

            # Handle flux
            flux = None
            if flux_col and flux_col in row.index:
                flux_val = pd.to_numeric(row[flux_col], errors="coerce")
                if np.isfinite(flux_val):
                    # Convert to mJy if needed (assume > 1000 means Jy, otherwise mJy)
                    flux_val_float = float(flux_val)
                    if flux_val_float > 1000:
                        flux = flux_val_float * 1000.0  # Convert Jy to mJy
                    else:
                        flux = flux_val_float

            insert_data.append((ra, dec, flux))

        conn.executemany(
            "INSERT OR IGNORE INTO sources(ra_deg, dec_deg, flux_mjy) VALUES(?, ?, ?)",
            insert_data,
        )

        # Create metadata table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
        )

        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_center', ?)",
            (str(dec_center),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_min', ?)",
            (str(dec_min),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_max', ?)",
            (str(dec_max),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('build_time_iso', ?)",
            (datetime.now(timezone.utc).isoformat(),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('n_sources', ?)",
            (str(len(insert_data)),),
        )
        source_file_str = str(rax_catalog_path) if rax_catalog_path else "auto-downloaded/cached"
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('source_file', ?)",
            (source_file_str,),
        )
        if min_flux_mjy is not None:
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('min_flux_mjy', ?)",
                (str(min_flux_mjy),),
            )

        conn.commit()

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"✓ Database created: {output_path}")
    print(f"  Size: {file_size_mb:.2f} MB")
    print(f"  Sources: {len(insert_data)}")

    return output_path


def build_vlass_strip_db(
    dec_center: float,
    dec_range: Tuple[float, float],
    vlass_catalog_path: Optional[str] = None,
    output_path: Optional[str | os.PathLike[str]] = None,
    min_flux_mjy: Optional[float] = None,
    cache_dir: str = ".cache/catalogs",
) -> Path:
    """Build SQLite database for VLASS sources in a declination strip.

    Args:
        dec_center: Center declination in degrees
        dec_range: Tuple of (dec_min, dec_max) in degrees
        vlass_catalog_path: Optional path to VLASS catalog (CSV/FITS).
                          If None, attempts to find cached catalog.
        output_path: Output SQLite database path (auto-generated if None)
        min_flux_mjy: Minimum flux threshold in mJy (None = no threshold)
        cache_dir: Directory for caching catalog files

    Returns:
        Path to created SQLite database
    """
    from dsa110_contimg.catalog.build_master import _normalize_columns, _read_table

    dec_min, dec_max = dec_range

    # Resolve output path
    if output_path is None:
        dec_rounded = round(dec_center, 1)
        db_name = f"vlass_dec{dec_rounded:+.1f}.sqlite3"
        output_path = Path("state/catalogs") / db_name

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load VLASS catalog
    if vlass_catalog_path:
        df_full = _read_table(vlass_catalog_path)
    else:
        # Try to find cached VLASS catalog
        cache_path = Path(cache_dir) / "vlass_catalog"
        for ext in [".csv", ".fits", ".fits.gz", ".csv.gz"]:
            candidate = cache_path.with_suffix(ext)
            if candidate.exists():
                df_full = _read_table(str(candidate))
                break
        else:
            raise FileNotFoundError(
                f"VLASS catalog not found. Provide vlass_catalog_path or place "
                f"catalog in {cache_dir}/vlass_catalog.csv or .fits"
            )

    # Normalize column names for VLASS
    VLASS_CANDIDATES = {
        "ra": ["ra", "ra_deg", "raj2000"],
        "dec": ["dec", "dec_deg", "dej2000"],
        "flux": ["peak_flux", "peak_mjy_per_beam", "flux_peak", "flux", "total_flux"],
    }

    col_map = _normalize_columns(df_full, VLASS_CANDIDATES)

    # Standardize column names
    ra_col = col_map.get("ra", "ra")
    dec_col = col_map.get("dec", "dec")
    flux_col = col_map.get("flux", None)

    # Filter to declination strip
    df_strip = df_full[
        (pd.to_numeric(df_full[dec_col], errors="coerce") >= dec_min)
        & (pd.to_numeric(df_full[dec_col], errors="coerce") <= dec_max)
    ].copy()

    print(f"Filtered VLASS catalog: {len(df_full)} → {len(df_strip)} sources")
    print(f"Declination range: {dec_min:.6f} to {dec_max:.6f} degrees")

    # Apply flux threshold if specified
    if min_flux_mjy is not None and flux_col:
        flux_val = pd.to_numeric(df_strip[flux_col], errors="coerce")
        # Convert to mJy if needed (assume > 1000 means Jy, otherwise mJy)
        if len(flux_val) > 0 and flux_val.max() > 1000:
            flux_val = flux_val * 1000.0  # Convert Jy to mJy
        df_strip = df_strip[flux_val >= min_flux_mjy].copy()
        print(f"After flux cut ({min_flux_mjy} mJy): {len(df_strip)} sources")

    # Create SQLite database
    print(f"Creating SQLite database: {output_path}")

    with sqlite3.connect(str(output_path)) as conn:
        # Create sources table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ra_deg REAL NOT NULL,
                dec_deg REAL NOT NULL,
                flux_mjy REAL,
                UNIQUE(ra_deg, dec_deg)
            )
        """
        )

        # Create spatial index
        conn.execute("CREATE INDEX IF NOT EXISTS idx_radec ON sources(ra_deg, dec_deg)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dec ON sources(dec_deg)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_flux ON sources(flux_mjy)")

        # Clear existing data
        conn.execute("DELETE FROM sources")

        # Insert sources
        insert_data = []
        for _, row in df_strip.iterrows():
            ra = pd.to_numeric(row[ra_col], errors="coerce")
            dec = pd.to_numeric(row[dec_col], errors="coerce")

            if not (np.isfinite(ra) and np.isfinite(dec)):
                continue

            # Handle flux
            flux = None
            if flux_col and flux_col in row.index:
                flux_val = pd.to_numeric(row[flux_col], errors="coerce")
                if np.isfinite(flux_val):
                    # Convert to mJy if needed (assume > 1000 means Jy, otherwise mJy)
                    flux_val_float = float(flux_val)
                    if flux_val_float > 1000:
                        flux = flux_val_float * 1000.0  # Convert Jy to mJy
                    else:
                        flux = flux_val_float

            if np.isfinite(ra) and np.isfinite(dec):
                insert_data.append((ra, dec, flux))

        conn.executemany(
            "INSERT OR IGNORE INTO sources(ra_deg, dec_deg, flux_mjy) VALUES(?, ?, ?)",
            insert_data,
        )

        # Create metadata table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
        )

        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_center', ?)",
            (str(dec_center),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_min', ?)",
            (str(dec_min),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_max', ?)",
            (str(dec_max),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('build_time_iso', ?)",
            (datetime.now(timezone.utc).isoformat(),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('n_sources', ?)",
            (str(len(insert_data)),),
        )
        source_file_str = (
            str(vlass_catalog_path) if vlass_catalog_path else "auto-downloaded/cached"
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('source_file', ?)",
            (source_file_str,),
        )
        if min_flux_mjy is not None:
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('min_flux_mjy', ?)",
                (str(min_flux_mjy),),
            )

        conn.commit()

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"✓ Database created: {output_path}")
    print(f"  Size: {file_size_mb:.2f} MB")
    print(f"  Sources: {len(insert_data)}")

    return output_path


def build_vlass_strip_db(
    dec_center: float,
    dec_range: Tuple[float, float],
    vlass_catalog_path: Optional[str] = None,
    output_path: Optional[str | os.PathLike[str]] = None,
    min_flux_mjy: Optional[float] = None,
    cache_dir: str = ".cache/catalogs",
) -> Path:
    """Build SQLite database for VLASS sources in a declination strip.

    Args:
        dec_center: Center declination in degrees
        dec_range: Tuple of (dec_min, dec_max) in degrees
        vlass_catalog_path: Optional path to VLASS catalog (CSV/FITS).
                          If None, attempts to find cached catalog.
        output_path: Output SQLite database path (auto-generated if None)
        min_flux_mjy: Minimum flux threshold in mJy (None = no threshold)
        cache_dir: Directory for caching catalog files

    Returns:
        Path to created SQLite database
    """
    from dsa110_contimg.catalog.build_master import _normalize_columns, _read_table

    dec_min, dec_max = dec_range

    # Resolve output path
    if output_path is None:
        dec_rounded = round(dec_center, 1)
        db_name = f"vlass_dec{dec_rounded:+.1f}.sqlite3"
        output_path = Path("state/catalogs") / db_name

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load VLASS catalog
    if vlass_catalog_path:
        df_full = _read_table(vlass_catalog_path)
    else:
        # Try to find cached VLASS catalog
        cache_path = Path(cache_dir) / "vlass_catalog"
        for ext in [".csv", ".fits", ".fits.gz", ".csv.gz"]:
            candidate = cache_path.with_suffix(ext)
            if candidate.exists():
                df_full = _read_table(str(candidate))
                break
        else:
            raise FileNotFoundError(
                f"VLASS catalog not found. Provide vlass_catalog_path or place "
                f"catalog in {cache_dir}/vlass_catalog.csv or .fits"
            )

    # Normalize column names for VLASS
    VLASS_CANDIDATES = {
        "ra": ["ra", "ra_deg", "raj2000"],
        "dec": ["dec", "dec_deg", "dej2000"],
        "flux": ["peak_flux", "peak_mjy_per_beam", "flux_peak", "flux", "total_flux"],
    }

    col_map = _normalize_columns(df_full, VLASS_CANDIDATES)

    # Standardize column names
    ra_col = col_map.get("ra", "ra")
    dec_col = col_map.get("dec", "dec")
    flux_col = col_map.get("flux", None)

    # Filter to declination strip
    df_strip = df_full[
        (pd.to_numeric(df_full[dec_col], errors="coerce") >= dec_min)
        & (pd.to_numeric(df_full[dec_col], errors="coerce") <= dec_max)
    ].copy()

    print(f"Filtered VLASS catalog: {len(df_full)} → {len(df_strip)} sources")
    print(f"Declination range: {dec_min:.6f} to {dec_max:.6f} degrees")

    # Apply flux threshold if specified
    if min_flux_mjy is not None and flux_col:
        flux_val = pd.to_numeric(df_strip[flux_col], errors="coerce")
        # Convert to mJy if needed (assume > 1000 means Jy, otherwise mJy)
        if len(flux_val) > 0 and flux_val.max() > 1000:
            flux_val = flux_val * 1000.0  # Convert Jy to mJy
        df_strip = df_strip[flux_val >= min_flux_mjy].copy()
        print(f"After flux cut ({min_flux_mjy} mJy): {len(df_strip)} sources")

    # Create SQLite database
    print(f"Creating SQLite database: {output_path}")

    with sqlite3.connect(str(output_path)) as conn:
        # Create sources table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ra_deg REAL NOT NULL,
                dec_deg REAL NOT NULL,
                flux_mjy REAL,
                UNIQUE(ra_deg, dec_deg)
            )
        """
        )

        # Create spatial index
        conn.execute("CREATE INDEX IF NOT EXISTS idx_radec ON sources(ra_deg, dec_deg)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dec ON sources(dec_deg)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_flux ON sources(flux_mjy)")

        # Clear existing data
        conn.execute("DELETE FROM sources")

        # Insert sources
        insert_data = []
        for _, row in df_strip.iterrows():
            ra = pd.to_numeric(row[ra_col], errors="coerce")
            dec = pd.to_numeric(row[dec_col], errors="coerce")

            if not (np.isfinite(ra) and np.isfinite(dec)):
                continue

            # Handle flux
            flux = None
            if flux_col and flux_col in row.index:
                flux_val = pd.to_numeric(row[flux_col], errors="coerce")
                if np.isfinite(flux_val):
                    # Convert to mJy if needed (assume > 1000 means Jy, otherwise mJy)
                    flux_val_float = float(flux_val)
                    if flux_val_float > 1000:
                        flux = flux_val_float * 1000.0  # Convert Jy to mJy
                    else:
                        flux = flux_val_float

            if np.isfinite(ra) and np.isfinite(dec):
                insert_data.append((ra, dec, flux))

        conn.executemany(
            "INSERT OR IGNORE INTO sources(ra_deg, dec_deg, flux_mjy) VALUES(?, ?, ?)",
            insert_data,
        )

        # Create metadata table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
        )

        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_center', ?)",
            (str(dec_center),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_min', ?)",
            (str(dec_min),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_max', ?)",
            (str(dec_max),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('build_time_iso', ?)",
            (datetime.now(timezone.utc).isoformat(),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('n_sources', ?)",
            (str(len(insert_data)),),
        )
        source_file_str = (
            str(vlass_catalog_path) if vlass_catalog_path else "auto-downloaded/cached"
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('source_file', ?)",
            (source_file_str,),
        )
        if min_flux_mjy is not None:
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('min_flux_mjy', ?)",
                (str(min_flux_mjy),),
            )

        conn.commit()

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"✓ Database created: {output_path}")
    print(f"  Size: {file_size_mb:.2f} MB")
    print(f"  Sources: {len(insert_data)}")

    return output_path
