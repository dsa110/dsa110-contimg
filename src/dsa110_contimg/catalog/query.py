"""
Generalized catalog querying interface for NVSS, FIRST, RAX, and other source catalogs.

Supports both SQLite databases (per-declination strips) and CSV fallback.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord


def resolve_catalog_path(
    catalog_type: str,
    dec_strip: Optional[float] = None,
    explicit_path: Optional[str | os.PathLike[str]] = None,
) -> Path:
    """Resolve path to a catalog (SQLite or CSV) using standard precedence.

    Args:
        catalog_type: One of "nvss", "first", "rax", "vlass", "master"
        dec_strip: Declination in degrees (for per-strip SQLite databases)
        explicit_path: Override path (highest priority)

    Returns:
        Path object pointing to catalog file

    Raises:
        FileNotFoundError: If no catalog can be found
    """
    # 1. Explicit path takes highest priority
    if explicit_path:
        path = Path(explicit_path)
        if path.exists():
            return path
        raise FileNotFoundError(f"Explicit catalog path does not exist: {explicit_path}")

    # 2. Check environment variable
    env_var = f"{catalog_type.upper()}_CATALOG"
    env_path = os.getenv(env_var)
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path

    # 3. Try per-declination SQLite database (if dec_strip provided)
    if dec_strip is not None:
        # Round to 0.1 degree precision for filename
        # Handle both scalar and array inputs
        if isinstance(dec_strip, np.ndarray):
            # Extract scalar from array (take first element if array)
            dec_strip = float(dec_strip.flat[0])
        dec_rounded = round(float(dec_strip), 1)
        # Map catalog type to database name
        db_name = f"{catalog_type}_dec{dec_rounded:+.1f}.sqlite3"

        # Try standard locations
        candidates = []
        try:
            current_file = Path(__file__).resolve()
            potential_root = current_file.parents[3]
            if (potential_root / "src" / "dsa110_contimg").exists():
                candidates.append(potential_root / "state" / "catalogs" / db_name)
        except Exception:
            pass

        for root_str in ["/data/dsa110-contimg", "/app"]:
            root_path = Path(root_str)
            if root_path.exists():
                candidates.append(root_path / "state" / "catalogs" / db_name)

        candidates.append(Path.cwd() / "state" / "catalogs" / db_name)
        candidates.append(Path("/data/dsa110-contimg/state/catalogs") / db_name)

        for candidate in candidates:
            if candidate.exists():
                return candidate

        # If exact match not found, try to find nearest declination match (within 1.0 degree tolerance)
        catalog_dirs = []
        for root_str in ["/data/dsa110-contimg", "/app"]:
            root_path = Path(root_str)
            if root_path.exists():
                catalog_dirs.append(root_path / "state" / "catalogs")
        try:
            current_file = Path(__file__).resolve()
            potential_root = current_file.parents[3]
            if (potential_root / "src" / "dsa110_contimg").exists():
                catalog_dirs.append(potential_root / "state" / "catalogs")
        except Exception:
            pass
        catalog_dirs.append(Path.cwd() / "state" / "catalogs")
        catalog_dirs.append(Path("/data/dsa110-contimg/state/catalogs"))

        best_match = None
        best_diff = float("inf")
        pattern = f"{catalog_type}_dec*.sqlite3"
        for catalog_dir in catalog_dirs:
            if not catalog_dir.exists():
                continue
            # Find all matching catalog files
            for catalog_file in catalog_dir.glob(pattern):
                try:
                    # Extract declination from filename: nvss_dec+54.6.sqlite3 -> 54.6
                    dec_str = catalog_file.stem.replace(f"{catalog_type}_dec", "").replace("+", "")
                    file_dec = float(dec_str)
                    diff = abs(file_dec - float(dec_strip))
                    if diff < best_diff and diff <= 1.0:  # Within 1 degree tolerance
                        best_diff = diff
                        best_match = catalog_file
                except (ValueError, AttributeError):
                    continue

        if best_match is not None:
            return best_match

    # 4. Try standard master catalog location
    if catalog_type == "master":
        master_candidates = [
            Path("/data/dsa110-contimg/state/catalogs/master_sources.sqlite3"),
            Path("state/catalogs/master_sources.sqlite3"),
        ]
        for candidate in master_candidates:
            if candidate.exists():
                return candidate

    # 5. Fallback: CSV (for NVSS, RAX, VLASS)
    if catalog_type in ["nvss", "rax", "vlass"]:
        # CSV fallback is handled in query_sources() function
        pass

    raise FileNotFoundError(
        f"Catalog '{catalog_type}' not found. "
        f"Searched SQLite databases and standard locations. "
        f"Set {env_var} environment variable or provide explicit path."
    )


def query_sources(
    catalog_type: str = "nvss",
    ra_center: float = 0.0,
    dec_center: float = 0.0,
    radius_deg: float = 1.5,
    *,
    dec_strip: Optional[float] = None,
    min_flux_mjy: Optional[float] = None,
    max_sources: Optional[int] = None,
    catalog_path: Optional[str | os.PathLike[str]] = None,
    **kwargs,
) -> pd.DataFrame:
    """Query sources from catalog within a field of view.

    Args:
        catalog_type: One of "nvss", "first", "rax", "vlass", "master"
        ra_center: Field center RA in degrees
        dec_center: Field center Dec in degrees
        radius_deg: Search radius in degrees
        dec_strip: Declination strip (auto-detected from dec_center if None)
        min_flux_mjy: Minimum flux in mJy (catalog-specific)
        max_sources: Maximum number of sources to return
        catalog_path: Explicit path to catalog (overrides auto-resolution)
        **kwargs: Catalog-specific query parameters

    Returns:
        DataFrame with columns: ra_deg, dec_deg, flux_mjy, and catalog-specific fields
    """
    # Auto-detect dec_strip from dec_center if not provided
    if dec_strip is None:
        # Ensure dec_center is a scalar (handle numpy arrays)
        if isinstance(dec_center, np.ndarray):
            dec_strip = float(dec_center.flat[0])
        else:
            dec_strip = float(dec_center)

    # Resolve catalog path
    try:
        catalog_file = resolve_catalog_path(
            catalog_type=catalog_type,
            dec_strip=dec_strip,
            explicit_path=catalog_path,
        )
    except FileNotFoundError:
        # Fallback to CSV for supported catalogs
        if catalog_type == "nvss":
            return _query_nvss_csv(
                ra_center=ra_center,
                dec_center=dec_center,
                radius_deg=radius_deg,
                min_flux_mjy=min_flux_mjy,
                max_sources=max_sources,
            )
        elif catalog_type == "rax":
            from dsa110_contimg.calibration.catalogs import query_rax_sources

            return query_rax_sources(
                ra_deg=ra_center,
                dec_deg=dec_center,
                radius_deg=radius_deg,
                min_flux_mjy=min_flux_mjy,
                max_sources=max_sources,
            )
        elif catalog_type == "vlass":
            from dsa110_contimg.calibration.catalogs import query_vlass_sources

            return query_vlass_sources(
                ra_deg=ra_center,
                dec_deg=dec_center,
                radius_deg=radius_deg,
                min_flux_mjy=min_flux_mjy,
                max_sources=max_sources,
            )
        raise

    # Load from SQLite
    if str(catalog_file).endswith(".sqlite3"):
        return _query_sqlite(
            catalog_type=catalog_type,
            catalog_path=str(catalog_file),
            ra_center=ra_center,
            dec_center=dec_center,
            radius_deg=radius_deg,
            min_flux_mjy=min_flux_mjy,
            max_sources=max_sources,
            **kwargs,
        )
    else:
        # CSV fallback
        return _query_csv(
            catalog_type=catalog_type,
            catalog_path=str(catalog_file),
            ra_center=ra_center,
            dec_center=dec_center,
            radius_deg=radius_deg,
            min_flux_mjy=min_flux_mjy,
            max_sources=max_sources,
            **kwargs,
        )


def _query_sqlite(
    catalog_type: str,
    catalog_path: str,
    ra_center: float,
    dec_center: float,
    radius_deg: float,
    min_flux_mjy: Optional[float] = None,
    max_sources: Optional[int] = None,
    **kwargs,
) -> pd.DataFrame:
    """Query SQLite catalog database."""
    conn = sqlite3.connect(catalog_path)
    conn.row_factory = sqlite3.Row

    try:
        # Approximate box search (faster than exact angular separation)
        dec_half = radius_deg
        ra_half = radius_deg / np.cos(np.radians(dec_center))

        # Build query based on catalog type
        if catalog_type == "nvss":
            flux_col = "flux_mjy"
            where_clauses = [
                "ra_deg BETWEEN ? AND ?",
                "dec_deg BETWEEN ? AND ?",
            ]
            if min_flux_mjy is not None:
                where_clauses.append(f"{flux_col} >= ?")

            query = f"""
            SELECT ra_deg, dec_deg, flux_mjy
            FROM sources
            WHERE {" AND ".join(where_clauses)}
            ORDER BY flux_mjy DESC
            """

            params = [
                ra_center - ra_half,
                ra_center + ra_half,
                dec_center - dec_half,
                dec_center + dec_half,
            ]
            if min_flux_mjy is not None:
                params.append(min_flux_mjy)

            if max_sources:
                query += f" LIMIT {max_sources}"

            rows = conn.execute(query, params).fetchall()

        elif catalog_type == "first":
            # FIRST catalog schema (includes major/minor axes)
            flux_col = "flux_mjy"
            where_clauses = [
                "ra_deg BETWEEN ? AND ?",
                "dec_deg BETWEEN ? AND ?",
            ]
            if min_flux_mjy is not None:
                where_clauses.append(f"{flux_col} >= ?")

            query = f"""
            SELECT ra_deg, dec_deg, flux_mjy, maj_arcsec, min_arcsec
            FROM sources
            WHERE {" AND ".join(where_clauses)}
            ORDER BY flux_mjy DESC
            """

            params = [
                ra_center - ra_half,
                ra_center + ra_half,
                dec_center - dec_half,
                dec_center + dec_half,
            ]
            if min_flux_mjy is not None:
                params.append(min_flux_mjy)

            if max_sources:
                query += f" LIMIT {max_sources}"

            rows = conn.execute(query, params).fetchall()

        elif catalog_type == "rax":
            # RAX catalog schema (similar to NVSS)
            flux_col = "flux_mjy"
            where_clauses = [
                "ra_deg BETWEEN ? AND ?",
                "dec_deg BETWEEN ? AND ?",
            ]
            if min_flux_mjy is not None:
                where_clauses.append(f"{flux_col} >= ?")

            query = f"""
            SELECT ra_deg, dec_deg, flux_mjy
            FROM sources
            WHERE {" AND ".join(where_clauses)}
            ORDER BY flux_mjy DESC
            """

            params = [
                ra_center - ra_half,
                ra_center + ra_half,
                dec_center - dec_half,
                dec_center + dec_half,
            ]
            if min_flux_mjy is not None:
                params.append(min_flux_mjy)

            if max_sources:
                query += f" LIMIT {max_sources}"

            rows = conn.execute(query, params).fetchall()

        elif catalog_type == "vlass":
            # VLASS catalog schema (similar to NVSS)
            flux_col = "flux_mjy"
            where_clauses = [
                "ra_deg BETWEEN ? AND ?",
                "dec_deg BETWEEN ? AND ?",
            ]
            if min_flux_mjy is not None:
                where_clauses.append(f"{flux_col} >= ?")

            query = f"""
            SELECT ra_deg, dec_deg, flux_mjy
            FROM sources
            WHERE {" AND ".join(where_clauses)}
            ORDER BY flux_mjy DESC
            """

            params = [
                ra_center - ra_half,
                ra_center + ra_half,
                dec_center - dec_half,
                dec_center + dec_half,
            ]
            if min_flux_mjy is not None:
                params.append(min_flux_mjy)

            if max_sources:
                query += f" LIMIT {max_sources}"

            rows = conn.execute(query, params).fetchall()

        elif catalog_type == "master":
            # Use master_sources schema
            where_clauses = [
                "ra_deg BETWEEN ? AND ?",
                "dec_deg BETWEEN ? AND ?",
            ]
            if min_flux_mjy is not None:
                where_clauses.append("s_nvss >= ?")

            query = f"""
            SELECT ra_deg, dec_deg, s_nvss * 1000.0 as flux_mjy,
                   snr_nvss, s_vlass, alpha, resolved_flag, confusion_flag
            FROM sources
            WHERE {" AND ".join(where_clauses)}
            ORDER BY snr_nvss DESC
            """

            params = [
                ra_center - ra_half,
                ra_center + ra_half,
                dec_center - dec_half,
                dec_center + dec_half,
            ]
            if min_flux_mjy is not None:
                params.append(min_flux_mjy / 1000.0)  # Convert mJy to Jy

            if max_sources:
                query += f" LIMIT {max_sources}"

            rows = conn.execute(query, params).fetchall()

        else:
            raise ValueError(
                f"Unsupported catalog type for SQLite: {catalog_type}. "
                f"Supported types: nvss, first, rax, vlass, master"
            )

        # Convert to DataFrame
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame([dict(row) for row in rows])

        # Exact angular separation filter
        if len(df) > 0:
            sc = SkyCoord(
                ra=df["ra_deg"].values * u.deg,  # pylint: disable=no-member
                dec=df["dec_deg"].values * u.deg,  # pylint: disable=no-member
                frame="icrs",
            )
            center = SkyCoord(
                ra_center * u.deg,
                dec_center * u.deg,
                frame="icrs",  # pylint: disable=no-member
            )  # pylint: disable=no-member
            sep = sc.separation(center).deg
            df = df[sep <= radius_deg].copy()

        return df

    finally:
        conn.close()


def _query_nvss_csv(
    ra_center: float,
    dec_center: float,
    radius_deg: float,
    min_flux_mjy: Optional[float] = None,
    max_sources: Optional[int] = None,
) -> pd.DataFrame:
    """Fallback: Query NVSS from CSV catalog."""
    from dsa110_contimg.calibration.catalogs import read_nvss_catalog

    df = read_nvss_catalog()
    sc = SkyCoord(
        ra=df["ra"].values * u.deg,  # pylint: disable=no-member
        dec=df["dec"].values * u.deg,  # pylint: disable=no-member
        frame="icrs",
    )
    center = SkyCoord(
        ra_center * u.deg,
        dec_center * u.deg,
        frame="icrs",  # pylint: disable=no-member
    )  # pylint: disable=no-member
    sep = sc.separation(center).deg

    keep = sep <= radius_deg
    if min_flux_mjy is not None:
        flux_mjy = pd.to_numeric(df["flux_20_cm"], errors="coerce")
        keep = keep & (flux_mjy >= min_flux_mjy)

    result = df[keep].copy()

    # Rename columns to standard format
    result = result.rename(
        columns={
            "ra": "ra_deg",
            "dec": "dec_deg",
            "flux_20_cm": "flux_mjy",
        }
    )

    # Sort by flux and limit
    if "flux_mjy" in result.columns:
        result = result.sort_values("flux_mjy", ascending=False)
    if max_sources:
        result = result.head(max_sources)

    return result


def _query_csv(
    catalog_type: str,
    catalog_path: str,
    ra_center: float,
    dec_center: float,
    radius_deg: float,
    min_flux_mjy: Optional[float] = None,
    max_sources: Optional[int] = None,
    **kwargs,
) -> pd.DataFrame:
    """Query CSV catalog (fallback)."""
    # For now, only NVSS CSV is supported
    if catalog_type != "nvss":
        raise ValueError(f"CSV fallback not implemented for {catalog_type}")

    return _query_nvss_csv(
        ra_center=ra_center,
        dec_center=dec_center,
        radius_deg=radius_deg,
        min_flux_mjy=min_flux_mjy,
        max_sources=max_sources,
    )
