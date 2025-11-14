import gzip
import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.request import urlretrieve

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import Angle, SkyCoord
from astropy.time import Time

from .schedule import DSA110_LOCATION

logger = logging.getLogger(__name__)

NVSS_URL = "https://heasarc.gsfc.nasa.gov/FTP/heasarc/dbase/tdat_files/heasarc_nvss.tdat.gz"

# FIRST catalog URLs (if available)
# Note: FIRST catalog is typically available as FITS files from NRAO
# Users may need to download manually or provide path
# Example, verify actual URL
FIRST_CATALOG_BASE_URL = "https://third.ucllnl.org/first/catalogs/"

# RAX catalog URL (DSA-110 specific, may need to be provided manually)
# RAX catalog location to be determined based on DSA-110 data access


def resolve_vla_catalog_path(
    explicit_path: Optional[str | os.PathLike[str]] = None, prefer_sqlite: bool = True
) -> Path:
    """Resolve the path to the VLA calibrator catalog using a consistent precedence order.

    This function provides a single source of truth for locating the VLA calibrator catalog,
    following this precedence:
    1. Explicit path provided as argument (highest priority)
    2. VLA_CATALOG environment variable
    3. If prefer_sqlite=True (default), try SQLite database first:
       - state/catalogs/vla_calibrators.sqlite3 (relative to project root)
       - /data/dsa110-contimg/state/catalogs/vla_calibrators.sqlite3
    4. Standard CSV locations relative to project root:
       - /data/dsa110-contimg/data/catalogs/VLA_calibrators_parsed.csv
       - /data/dsa110-contimg/data/catalogs/vla_calibrators_parsed.csv
       - references/dsa110-contimg-main-legacy/data/catalogs/vla_calibrators_parsed.csv
       - data-samples/catalogs/vla_calibrators_parsed.csv
       - sim-data-samples/catalogs/vla_calibrators_parsed.csv

    Args:
        explicit_path: Optional explicit path to catalog (overrides all defaults)
        prefer_sqlite: If True, prefer SQLite database over CSV (default: True)

    Returns:
        Path object pointing to the catalog file (CSV or SQLite)

    Raises:
        FileNotFoundError: If no catalog file can be found at any location

    Examples:
        >>> # Use default resolution (prefers SQLite)
        >>> path = resolve_vla_catalog_path()

        >>> # Override with explicit path
        >>> path = resolve_vla_catalog_path("/custom/path/to/catalog.csv")

        >>> # Prefer CSV instead of SQLite
        >>> path = resolve_vla_catalog_path(prefer_sqlite=False)

        >>> # Override with environment variable
        >>> import os
        >>> os.environ["VLA_CATALOG"] = "/custom/path.csv"
        >>> path = resolve_vla_catalog_path()
    """
    # 1. Explicit path takes highest priority
    if explicit_path:
        path = Path(explicit_path)
        if path.exists():
            return path
        raise FileNotFoundError(f"Explicit catalog path does not exist: {explicit_path}")

    # 2. Check environment variable
    env_path = os.getenv("VLA_CATALOG")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path
        # Don't raise here - fall through to standard locations as fallback

    # 3. Try SQLite database first if preferred
    if prefer_sqlite:
        sqlite_candidates = []
        try:
            # Try to find project root
            current_file = Path(__file__).resolve()
            potential_root = current_file.parents[3]
            if (potential_root / "src" / "dsa110_contimg").exists():
                sqlite_candidates.append(
                    potential_root / "state" / "catalogs" / "vla_calibrators.sqlite3"
                )
        except Exception:
            pass

        # Also try common absolute paths
        for root_str in ["/data/dsa110-contimg", "/app"]:
            root_path = Path(root_str)
            if root_path.exists():
                sqlite_candidates.append(
                    root_path / "state" / "catalogs" / "vla_calibrators.sqlite3"
                )

        # Try relative to current working directory
        sqlite_candidates.append(Path.cwd() / "state" / "catalogs" / "vla_calibrators.sqlite3")

        # Try absolute path
        sqlite_candidates.append(
            Path("/data/dsa110-contimg/state/catalogs/vla_calibrators.sqlite3")
        )

        for candidate in sqlite_candidates:
            if candidate.exists():
                return candidate

    # 4. Try standard CSV locations (relative to common project roots)
    # Try to find project root by looking for known markers
    candidates = []

    # Try to find project root
    project_roots = []
    try:
        # If we're in the package, try to find project root
        # catalogs.py → calibration → dsa110_contimg → src → project root
        current_file = Path(__file__).resolve()
        # Go up from catalogs.py to src/dsa110_contimg/calibration/catalogs.py
        # This gets us to: src/dsa110_contimg/calibration/
        # We want to go up 3 levels to reach project root
        potential_root = current_file.parents[3]
        if (potential_root / "src" / "dsa110_contimg").exists():
            project_roots.append(potential_root)
    except Exception:
        pass

    # Also try common absolute paths
    for root_str in ["/data/dsa110-contimg", "/app"]:
        root_path = Path(root_str)
        if root_path.exists():
            project_roots.append(root_path)

    # Build candidate paths
    for root in project_roots:
        candidates.extend(
            [
                root / "data" / "catalogs" / "VLA_calibrators_parsed.csv",
                root / "data" / "catalogs" / "vla_calibrators_parsed.csv",
                root
                / "references"
                / "dsa110-contimg-main-legacy"
                / "data"
                / "catalogs"
                / "vla_calibrators_parsed.csv",
                root / "data-samples" / "catalogs" / "vla_calibrators_parsed.csv",
                root / "sim-data-samples" / "catalogs" / "vla_calibrators_parsed.csv",
            ]
        )

    # Also try relative to current working directory
    cwd = Path.cwd()
    candidates.extend(
        [
            cwd / "data" / "catalogs" / "VLA_calibrators_parsed.csv",
            cwd / "data" / "catalogs" / "vla_calibrators_parsed.csv",
            cwd
            / "references"
            / "dsa110-contimg-main-legacy"
            / "data"
            / "catalogs"
            / "vla_calibrators_parsed.csv",
            cwd / "data-samples" / "catalogs" / "vla_calibrators_parsed.csv",
            cwd / "sim-data-samples" / "catalogs" / "vla_calibrators_parsed.csv",
        ]
    )

    # Try absolute paths directly
    candidates.extend(
        [
            Path("/data/dsa110-contimg/data/catalogs/VLA_calibrators_parsed.csv"),
            Path("/data/dsa110-contimg/data/catalogs/vla_calibrators_parsed.csv"),
            Path(
                "/data/dsa110-contimg/references/dsa110-contimg-main-legacy/data/catalogs/vla_calibrators_parsed.csv"
            ),
        ]
    )

    # Find first existing candidate
    for candidate in candidates:
        if candidate.exists():
            return candidate

    # If nothing found, raise with helpful error
    raise FileNotFoundError(
        f"VLA calibrator catalog not found. Searched:\n"
        f"  - Environment variable VLA_CATALOG: {env_path or '(not set)'}\n"
        f"  - {len(candidates)} standard locations\n"
        f"  - Current working directory: {cwd}\n"
        f"Set VLA_CATALOG environment variable or provide explicit path."
    )


def read_nvss_catalog(cache_dir: str = ".cache/catalogs") -> pd.DataFrame:
    """Download (if needed) and parse the NVSS catalog to a DataFrame.

    Returns flux_20_cm in mJy to match historical conventions.
    """
    os.makedirs(cache_dir, exist_ok=True)
    gz_path = str(Path(cache_dir) / "heasarc_nvss.tdat.gz")
    txt_path = str(Path(cache_dir) / "heasarc_nvss.tdat")

    if not os.path.exists(txt_path):
        if not os.path.exists(gz_path):
            urlretrieve(NVSS_URL, gz_path)
        with gzip.open(gz_path, "rb") as f_in, open(txt_path, "wb") as f_out:
            f_out.write(f_in.read())

    df = pd.read_csv(
        txt_path,
        sep="|",
        skiprows=67,
        names=[
            "ra",
            "dec",
            "lii",
            "bii",
            "ra_error",
            "dec_error",
            "flux_20_cm",
            "flux_20_cm_error",
            "limit_major_axis",
            "major_axis",
            "major_axis_error",
            "limit_minor_axis",
            "minor_axis",
            "minor_axis_error",
            "position_angle",
            "position_angle_error",
            "residual_code",
            "residual_flux",
            "pol_flux",
            "pol_flux_error",
            "pol_angle",
            "pol_angle_error",
            "field_name",
            "x_pixel",
            "y_pixel",
            "extra",
        ],
    )
    if len(df) > 0:
        df = df.iloc[:-1]  # drop trailer row
    if "extra" in df.columns:
        df = df.drop(columns=["extra"])  # trailing blank
    return df


def read_first_catalog(
    cache_dir: str = ".cache/catalogs",
    first_catalog_path: Optional[str] = None,
    use_astroquery: bool = True,
) -> pd.DataFrame:
    """Download (if needed) and parse the FIRST catalog to a DataFrame.

    If first_catalog_path is provided, reads from that file directly.
    Otherwise, attempts to download via astroquery (Vizier) or uses cached file.

    Args:
        cache_dir: Directory to cache downloaded catalog files
        first_catalog_path: Optional explicit path to FIRST catalog file (CSV/FITS)
        use_astroquery: If True, try astroquery.vizier first (default: True)

    Returns:
        DataFrame with FIRST catalog data

    Note:
        FIRST catalog is available via Vizier. If astroquery is not available,
        falls back to cached file or raises error with instructions.
    """
    from dsa110_contimg.catalog.build_master import _read_table

    # If explicit path provided, use it directly
    if first_catalog_path:
        if not os.path.exists(first_catalog_path):
            raise FileNotFoundError(f"FIRST catalog file not found: {first_catalog_path}")
        return _read_table(first_catalog_path)

    # Try astroquery first if enabled
    if use_astroquery:
        try:
            import astropy.units as u
            from astropy.coordinates import SkyCoord
            from astroquery.vizier import Vizier

            # Configure Vizier for large queries
            Vizier.ROW_LIMIT = -1  # No row limit
            Vizier.TIMEOUT = 300  # 5 minute timeout for large catalogs

            # Query FIRST catalog from Vizier
            # FIRST catalog name in Vizier: "VIII/92/first14"
            print("Querying FIRST catalog via Vizier...")
            catalog_list = Vizier.query_catalog("VIII/92/first14")  # pylint: disable=no-member

            if catalog_list:
                # Convert first catalog to DataFrame
                df = catalog_list[0].to_pandas()
                print(f"Downloaded {len(df)} sources from FIRST via Vizier")

                # Cache the result
                os.makedirs(cache_dir, exist_ok=True)
                cache_path = Path(cache_dir) / "first_catalog_from_vizier.csv"
                df.to_csv(cache_path, index=False)
                print(f"Cached FIRST catalog to: {cache_path}")

                return df
        except ImportError:
            if use_astroquery:
                print("Warning: astroquery not available. Install with: pip install astroquery")
                print("Falling back to cached file...")
        except Exception as e:
            print(f"Warning: Failed to query FIRST via Vizier: {e}")
            print("Falling back to cached file...")

    # Try to find cached FIRST catalog
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = Path(cache_dir) / "first_catalog"

    # Try common extensions (check vizier cache first)
    for ext in [".csv", ".fits", ".fits.gz", ".csv.gz"]:
        cached_file = cache_path.with_suffix(ext)
        if cached_file.exists():
            return _read_table(str(cached_file))

    # Also check for vizier cache
    vizier_cache = Path(cache_dir) / "first_catalog_from_vizier.csv"
    if vizier_cache.exists():
        return _read_table(str(vizier_cache))

    # If not found, raise error with helpful message
    raise FileNotFoundError(
        f"FIRST catalog not found. Options:\n"
        f"  1. Install astroquery: pip install astroquery\n"
        f"  2. Provide path via first_catalog_path argument\n"
        f"  3. Download FIRST catalog and place it in {cache_dir}/first_catalog.fits\n"
        f"FIRST catalog can be obtained from: https://third.ucllnl.org/first/catalogs/"
    )


def read_rax_catalog(
    cache_dir: str = ".cache/catalogs",
    rax_catalog_path: Optional[str] = None,
    use_astroquery: bool = False,
) -> pd.DataFrame:
    """Download (if needed) and parse the RAX catalog to a DataFrame.

    If rax_catalog_path is provided, reads from that file directly.
    Otherwise, attempts to find cached file or raises error.

    Args:
        cache_dir: Directory to cache downloaded catalog files
        rax_catalog_path: Optional explicit path to RAX catalog file (CSV/FITS)
        use_astroquery: If True, try astroquery.vizier (default: False, RAX not in Vizier)

    Returns:
        DataFrame with RAX catalog data

    Note:
        RAX catalog is DSA-110 specific and not available via Vizier.
        Provide the path manually or ensure the catalog is cached in the cache_dir.
    """
    from dsa110_contimg.catalog.build_master import _read_table

    # If explicit path provided, use it directly
    if rax_catalog_path:
        if not os.path.exists(rax_catalog_path):
            raise FileNotFoundError(f"RAX catalog file not found: {rax_catalog_path}")
        return _read_table(rax_catalog_path)

    # Try astroquery if enabled (though RAX is unlikely to be in Vizier)
    if use_astroquery:
        try:
            from astroquery.vizier import Vizier

            print("Warning: RAX catalog is DSA-110 specific and not available via Vizier.")
            print("Falling back to cached file...")
        except ImportError:
            pass

    # Try to find cached RAX catalog
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = Path(cache_dir) / "rax_catalog"

    # Try common extensions
    for ext in [".fits", ".csv", ".fits.gz", ".csv.gz"]:
        cached_file = cache_path.with_suffix(ext)
        if cached_file.exists():
            return _read_table(str(cached_file))

    # If not found, raise error with helpful message
    raise FileNotFoundError(
        f"RAX catalog not found. Please provide path via rax_catalog_path argument, "
        f"or place RAX catalog file in {cache_dir}/rax_catalog.fits or .csv\n"
        f"RAX catalog is DSA-110 specific and should be obtained from DSA-110 data sources."
    )


def read_vla_calibrator_catalog(path: str, cache_dir: Optional[str] = None) -> pd.DataFrame:
    """Parse the NRAO VLA calibrator list from a local text file.

    This follows the structure used in historical VLA calibrator files:
    - A header line per source: "<source> ... <ra> <dec> ..."
      where RA/Dec are sexagesimal strings parseable by astropy Angle.
    - Followed by 4 lines of other metadata.
    - Followed by a block of frequency lines until a blank line; the line
      containing "20cm " includes 4 code tokens and a flux (Jy).
    """
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)

    records = []
    with open(path, encoding="utf-8") as f:
        # Skip the first 3 lines if they are header text (as in many files)
        header_peek = [f.readline() for _ in range(3)]
        # Continue reading entries
        while True:
            line = f.readline()
            if not line:
                break
            if not line.strip():
                continue
            parts = line.split()
            # Expect at least: source, ?, ?, ra, dec
            if len(parts) < 5:
                continue
            try:
                source = parts[0]
                ra_str = parts[3]
                dec_str = parts[4]
                ra_deg = Angle(ra_str).to_value(u.deg)  # pylint: disable=no-member
                dec_deg = Angle(dec_str).to_value(u.deg)  # pylint: disable=no-member
            except Exception:
                continue

            # Skip 4 lines per entry as per file layout
            for _ in range(4):
                _ = f.readline()

            flux_20_cm = None
            code_20_cm = None
            # Read frequency block until blank
            while True:
                pos = f.tell()
                fl = f.readline()
                if (not fl) or fl.isspace():
                    break
                if "20cm " in fl:
                    toks = fl.split()
                    try:
                        # Expected format: "20cm <...> <code_a> <code_b> <code_c> <code_d> <flux> ..."
                        code_a, code_b, code_c, code_d = (
                            toks[2],
                            toks[3],
                            toks[4],
                            toks[5],
                        )
                        flux_20_cm = toks[6]
                        code_20_cm = code_a + code_b + code_c + code_d
                    except Exception:
                        # Fallback: last token as flux
                        flux_20_cm = toks[-1]
                        code_20_cm = None
            # Position now at blank; continue
            if flux_20_cm not in [None, "?"]:
                try:
                    flux_mJy = 1000.0 * float(flux_20_cm)
                except Exception:
                    flux_mJy = np.nan
                records.append(
                    {
                        "source": source,
                        "ra": ra_deg,
                        "dec": dec_deg,
                        "flux_20_cm": flux_mJy,
                        "code_20_cm": code_20_cm,
                    }
                )

    df = pd.DataFrame.from_records(records)
    if not df.empty:
        df = df.set_index("source")
    return df


def load_vla_catalog(
    explicit_path: Optional[str | os.PathLike[str]] = None, prefer_sqlite: bool = True
) -> pd.DataFrame:
    """Load the VLA calibrator catalog using automatic path resolution.

    This is a convenience wrapper that automatically finds and loads the catalog using
    the standard resolution order. Supports both SQLite database and CSV formats.

    Args:
        explicit_path: Optional explicit path to catalog (overrides all defaults)
        prefer_sqlite: If True, prefer SQLite database over CSV (default: True)

    Returns:
        DataFrame with calibrator catalog (indexed by J2000_NAME, columns include ra_deg, dec_deg, etc.)

    Examples:
        >>> # Use default resolution (prefers SQLite)
        >>> df = load_vla_catalog()

        >>> # Override with explicit path
        >>> df = load_vla_catalog("/custom/path/to/catalog.csv")

        >>> # Force CSV instead of SQLite
        >>> df = load_vla_catalog(prefer_sqlite=False)
    """
    catalog_path = resolve_vla_catalog_path(explicit_path, prefer_sqlite=prefer_sqlite)

    # Load from SQLite if it's a .sqlite3 file
    if str(catalog_path).endswith(".sqlite3"):
        return load_vla_catalog_from_sqlite(str(catalog_path))
    else:
        return read_vla_parsed_catalog_csv(str(catalog_path))


def load_vla_catalog_from_sqlite(db_path: str) -> pd.DataFrame:
    """Load VLA calibrator catalog from SQLite database.

    Args:
        db_path: Path to SQLite database

    Returns:
        DataFrame with calibrator catalog (indexed by name, columns include ra_deg, dec_deg, flux_jy)
    """
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        # Load from calibrators table (or vla_20cm view if available)
        try:
            df = pd.read_sql_query("SELECT name, ra_deg, dec_deg, flux_jy FROM vla_20cm", conn)
        except Exception:
            # Fallback to calibrators table if view doesn't exist
            df = pd.read_sql_query("SELECT name, ra_deg, dec_deg FROM calibrators", conn)
            df["flux_jy"] = None

        df = df.set_index("name")
        return df
    finally:
        conn.close()


def read_vla_parsed_catalog_csv(path: str) -> pd.DataFrame:
    """Read a CSV VLA calibrator catalog (parsed) and normalize RA/Dec columns to degrees.

    Expected columns (case-insensitive, best-effort):
    - 'J2000_NAME' (used as index)
    - RA in sexagesimal (e.g., 'RA_J2000') or degrees (e.g., 'RA_deg')
    - DEC in sexagesimal (e.g., 'DEC_J2000') or degrees (e.g., 'DEC_deg')
    """
    df = pd.read_csv(path)
    # Identify columns heuristically
    cols = {c.lower(): c for c in df.columns}
    name_col = cols.get("j2000_name") or cols.get("name") or list(df.columns)[0]
    ra_col = cols.get("ra_j2000") or cols.get("ra") or cols.get("raj2000") or cols.get("ra_hms")
    dec_col = cols.get("dec_j2000") or cols.get("dec") or cols.get("dej2000") or cols.get("dec_dms")
    ra_deg_col = next((c for c in df.columns if "ra_deg" in c.lower()), None)
    dec_deg_col = next((c for c in df.columns if "dec_deg" in c.lower()), None)

    def _to_deg(ra_val, dec_val) -> Tuple[float, float]:
        import astropy.units as u
        from astropy.coordinates import SkyCoord

        # try sexagesimal first
        try:
            sc = SkyCoord(
                str(ra_val).strip() + " " + str(dec_val).strip(),
                unit=(u.hourangle, u.deg),  # pylint: disable=no-member
                frame="icrs",
            )
            return float(sc.ra.deg), float(sc.dec.deg)
        except Exception:
            try:
                sc = SkyCoord(
                    str(ra_val).strip() + " " + str(dec_val).strip(),
                    unit=(u.deg, u.deg),  # pylint: disable=no-member
                    frame="icrs",
                )
                return float(sc.ra.deg), float(sc.dec.deg)
            except Exception:
                return float("nan"), float("nan")

    out = []
    for _, r in df.iterrows():
        name = str(r.get(name_col, "")).strip()
        if ra_deg_col and dec_deg_col:
            ra_deg = pd.to_numeric(r[ra_deg_col], errors="coerce")
            dec_deg = pd.to_numeric(r[dec_deg_col], errors="coerce")
        elif ra_col and dec_col:
            ra_deg, dec_deg = _to_deg(r.get(ra_col, ""), r.get(dec_col, ""))
        else:
            ra_deg, dec_deg = float("nan"), float("nan")
        out.append({"name": name, "ra_deg": ra_deg, "dec_deg": dec_deg})
    out_df = pd.DataFrame(out).set_index("name")
    return out_df


def read_vla_parsed_catalog_with_flux(path: str, band: str = "20cm") -> pd.DataFrame:
    """Read a parsed VLA calibrator CSV and return RA/Dec in degrees and flux in Jy for a given band.

    Expected columns include J2000_NAME, RA_J2000, DEC_J2000, BAND, FLUX_JY.
    Returns a DataFrame indexed by name with columns ra_deg, dec_deg, flux_jy.
    """
    df = pd.read_csv(path)
    # Filter band if present
    if "BAND" in df.columns:
        df = df[df["BAND"].astype(str).str.lower() == band.lower()].copy()
    # Normalize coordinates
    cols = {c.lower(): c for c in df.columns}
    name_col = cols.get("j2000_name") or cols.get("name") or list(df.columns)[0]
    ra_col = cols.get("ra_j2000") or cols.get("ra")
    dec_col = cols.get("dec_j2000") or cols.get("dec")
    # Optional spectral index columns
    sidx_col = cols.get("sidx") or cols.get("spectral_index")
    sidx_f0_col = cols.get("sidx_f0_ghz") or cols.get("nu0") or cols.get("si_freq")
    out = []
    for _, r in df.iterrows():
        name = str(r.get(name_col, "")).strip()
        ra = r.get(ra_col, "")
        dec = r.get(dec_col, "")
        try:
            sc = SkyCoord(
                str(ra).strip() + " " + str(dec).strip(),
                unit=(u.hourangle, u.deg),  # pylint: disable=no-member
                frame="icrs",
            )
            ra_deg = float(sc.ra.deg)
            dec_deg = float(sc.dec.deg)
        except Exception:
            # Try degrees
            try:
                sc = SkyCoord(
                    float(ra) * u.deg, float(dec) * u.deg, frame="icrs"  # pylint: disable=no-member
                )
                ra_deg = float(sc.ra.deg)
                dec_deg = float(sc.dec.deg)
            except Exception:
                continue
        try:
            flux_jy = float(r.get("FLUX_JY", r.get("flux_jy", "nan")))
        except Exception:
            flux_jy = float("nan")
        sidx = None
        sidx_f0_hz = None
        if sidx_col is not None:
            try:
                sidx = float(r.get(sidx_col))
            except Exception:
                sidx = None
        if sidx_f0_col is not None:
            try:
                f0 = float(r.get(sidx_f0_col))
                # If in GHz convert to Hz (assume GHz unless very large)
                sidx_f0_hz = f0 * 1e9 if f0 < 1e6 else f0
            except Exception:
                sidx_f0_hz = None
        out.append(
            {
                "name": name,
                "ra_deg": ra_deg,
                "dec_deg": dec_deg,
                "flux_jy": flux_jy,
                "sidx": sidx,
                "sidx_f0_hz": sidx_f0_hz,
            }
        )
    odf = pd.DataFrame(out).set_index("name")
    return odf


def nearest_calibrator_within_radius(
    pointing_ra_deg: float,
    pointing_dec_deg: float,
    cal_df: pd.DataFrame,
    radius_deg: float,
) -> Optional[Tuple[str, float, float, float]]:
    """Return (name, ra_deg, dec_deg, flux_jy) of nearest calibrator within radius.

    cal_df must have columns ra_deg, dec_deg, and optionally flux_jy.
    """
    if cal_df.empty:
        return None
    ra = pd.to_numeric(cal_df["ra_deg"], errors="coerce")
    dec = pd.to_numeric(cal_df["dec_deg"], errors="coerce")
    # Small-angle approximation for speed
    cosd = max(np.cos(np.deg2rad(pointing_dec_deg)), 1e-3)
    sep = np.hypot((ra - pointing_ra_deg) * cosd, (dec - pointing_dec_deg))
    sel = cal_df.copy()
    sel["sep"] = sep
    sel = sel[sel["sep"] <= radius_deg]
    if sel.empty:
        return None
    row = sel.sort_values("sep").iloc[0]
    name = str(row.name)
    return (
        name,
        float(row["ra_deg"]),
        float(row["dec_deg"]),
        float(row.get("flux_jy", np.nan)),
    )


def get_calibrator_radec(df: pd.DataFrame, name: str) -> Tuple[float, float]:
    """Lookup a calibrator by name (index) and return (ra_deg, dec_deg)."""
    if name in df.index:
        row = df.loc[name]
        # Handle case where multiple rows match (duplicates) - take first
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        # Handle Series - extract scalar value
        ra_val = row["ra_deg"]
        dec_val = row["dec_deg"]
        if isinstance(ra_val, pd.Series):
            ra_val = ra_val.iloc[0]
        if isinstance(dec_val, pd.Series):
            dec_val = dec_val.iloc[0]
        return float(ra_val), float(dec_val)
    # Fallback: try case-insensitive and stripped
    key = name.strip().upper()
    for idx in df.index:
        if str(idx).strip().upper() == key:
            row = df.loc[idx]
            # Handle case where multiple rows match (duplicates) - take first
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            ra_val = row["ra_deg"]
            dec_val = row["dec_deg"]
            if isinstance(ra_val, pd.Series):
                ra_val = ra_val.iloc[0]
            if isinstance(dec_val, pd.Series):
                dec_val = dec_val.iloc[0]
            return float(ra_val), float(dec_val)
    raise KeyError(f"Calibrator '{name}' not found in catalog")


def calibrator_match(
    catalog_df: pd.DataFrame,
    pt_dec: u.Quantity,
    mid_mjd: float,
    *,
    radius_deg: float = 1.0,
    freq_ghz: float = 1.4,
    top_n: int = 3,
) -> List[dict]:
    """Return top-N calibrators within `radius_deg` of the meridian pointing at `mid_mjd`.

    Input catalog must have columns 'ra_deg' and 'dec_deg' (see read_vla_parsed_catalog_csv).
    Results sorted by weighted_flux (primary beam at freq_ghz) descending, then separation.
    """
    # Compute meridian RA at DSA-110 (HA=0) and fixed pointing declination
    # Use simple LST→RA equivalence; rely on existing helper in schedule via next_transit_time logic
    # For robustness, we compute LST from astropy Time directly here
    t = Time(mid_mjd, format="mjd", scale="utc", location=DSA110_LOCATION)
    ra_meridian = t.sidereal_time("apparent").to_value(u.deg)  # pylint: disable=no-member
    dec_meridian = float(pt_dec.to_value(u.deg))  # pylint: disable=no-member

    # Filter by radius window (approximate RA window scaled by cos(dec))
    df = catalog_df.copy()
    if "ra_deg" not in df.columns or "dec_deg" not in df.columns:
        raise ValueError("catalog_df must contain 'ra_deg' and 'dec_deg' columns")
    ra = pd.to_numeric(df["ra_deg"], errors="coerce")
    dec = pd.to_numeric(df["dec_deg"], errors="coerce")
    cosd = max(np.cos(np.deg2rad(dec_meridian)), 1e-3)
    dra = radius_deg / cosd
    sel = df[
        (dec >= dec_meridian - radius_deg)
        & (dec <= dec_meridian + radius_deg)
        & (ra >= ra_meridian - dra)
        & (ra <= ra_meridian + dra)
    ].copy()
    if sel.empty:
        return []

    # Compute separation and primary-beam weighted flux if flux column present
    sep = np.hypot((sel["ra_deg"] - ra_meridian) * cosd, (sel["dec_deg"] - dec_meridian))
    sel["sep_deg"] = sep

    # Determine flux column to use (prefer flux_20_cm, fallback to flux_jy)
    flux_col = None
    flux_scale = 1.0  # Default: already in Jy
    if "flux_20_cm" in sel.columns:
        flux_col = "flux_20_cm"
        flux_scale = 1e-3  # Convert mJy to Jy
    elif "flux_jy" in sel.columns:
        flux_col = "flux_jy"
        flux_scale = 1.0  # Already in Jy

    if flux_col is not None:
        # weighted flux ~ PB(resp)*flux (Jy)
        w = []
        for _, r in sel.iterrows():
            resp = airy_primary_beam_response(
                np.deg2rad(ra_meridian),
                np.deg2rad(dec_meridian),
                np.deg2rad(r["ra_deg"]),
                np.deg2rad(r["dec_deg"]),
                freq_ghz,
            )
            flux_val = float(r[flux_col]) if pd.notna(r[flux_col]) else 0.0
            w.append(resp * flux_val * flux_scale)
        sel["weighted_flux"] = w
        sel = sel.sort_values(["weighted_flux", "sep_deg"], ascending=[False, True])
    else:
        sel = sel.sort_values(["sep_deg"], ascending=[True])

    out: List[dict] = []
    for name, r in sel.head(top_n).iterrows():
        out.append(
            {
                "name": name if isinstance(name, str) else str(name),
                "ra_deg": float(r["ra_deg"]),
                "dec_deg": float(r["dec_deg"]),
                "sep_deg": float(r["sep_deg"]),
                "weighted_flux": float(r.get("weighted_flux", np.nan)),
            }
        )
    return out


def airy_primary_beam_response(
    ant_ra: float,
    ant_dec: float,
    src_ra: float,
    src_dec: float,
    freq_GHz: float,
    dish_dia_m: float = 4.7,
) -> float:
    """Approximate primary beam response using an Airy pattern.

    Returns a scalar response in [0, 1]. Coordinates in radians.
    """
    # Offset angle approximation on the sky
    dra = (src_ra - ant_ra) * np.cos(ant_dec)
    ddec = src_dec - ant_dec
    theta = np.sqrt(dra * dra + ddec * ddec)

    # Handle zero separation case (source at phase center)
    if theta == 0.0 or theta < 1e-10:
        return 1.0

    # First-null approximation: 1.22 * lambda / D
    lam_m = 3e8 / (freq_GHz * 1e9)
    x = np.pi * dish_dia_m * np.sin(theta) / lam_m
    # Avoid division by zero (but we already handled theta == 0 above)
    if x == 0.0 or x < 1e-10:
        return 1.0
    resp = (2 * (np.sin(x) - x * np.cos(x)) / (x * x)) ** 2
    # Clamp numeric noise
    return float(np.clip(resp, 0.0, 1.0))


def generate_caltable(
    vla_df: pd.DataFrame,
    pt_dec: u.Quantity,
    csv_path: str,
    radius: u.Quantity = 2.5 * u.deg,  # pylint: disable=no-member
    min_weighted_flux: u.Quantity = 1.0 * u.Jy,  # pylint: disable=no-member
    min_percent_flux: float = 0.15,
) -> str:
    """Build a declination-specific calibrator table and save to CSV.

    Weighted by primary beam response at 1.4 GHz.
    """
    pt_dec_deg = pt_dec.to_value(u.deg)  # pylint: disable=no-member
    # ensure numeric
    vla_df = vla_df.copy()
    vla_df["ra"] = pd.to_numeric(vla_df["ra"], errors="coerce")
    vla_df["dec"] = pd.to_numeric(vla_df["dec"], errors="coerce")
    vla_df["flux_20_cm"] = pd.to_numeric(vla_df["flux_20_cm"], errors="coerce")

    cal_df = vla_df[
        (vla_df["dec"] < (pt_dec_deg + radius.to_value(u.deg)))  # pylint: disable=no-member
        & (vla_df["dec"] > (pt_dec_deg - radius.to_value(u.deg)))  # pylint: disable=no-member
        & (vla_df["flux_20_cm"] > 1000.0)
    ].copy()
    if cal_df.empty:
        # Still write an empty CSV to satisfy pipeline expectations
        cal_df.to_csv(csv_path, index=True)
        return csv_path

    # Compute weighted flux per calibrator and field flux
    cal_df["weighted_flux"] = 0.0
    cal_df["field_flux"] = 0.0

    ant_ra = 0.0  # use RA=self for beam centering approximation; drop explicit RA dependence
    ant_dec = np.deg2rad(pt_dec_deg)
    for name, row in cal_df.iterrows():
        src_ra = np.deg2rad(row["ra"]) if np.isfinite(row["ra"]) else 0.0
        src_dec = np.deg2rad(row["dec"]) if np.isfinite(row["dec"]) else ant_dec
        resp = airy_primary_beam_response(ant_ra, ant_dec, src_ra, src_dec, 1.4)
        cal_df.at[name, "weighted_flux"] = (row["flux_20_cm"] / 1e3) * resp

        # Field: local patch of radius scaled by cos(dec)
        field = vla_df[
            (vla_df["dec"] < (pt_dec_deg + radius.to_value(u.deg)))  # pylint: disable=no-member
            & (vla_df["dec"] > (pt_dec_deg - radius.to_value(u.deg)))  # pylint: disable=no-member
            & (
                vla_df["ra"]
                < row["ra"]
                + radius.to_value(u.deg)
                / max(np.cos(np.deg2rad(pt_dec_deg)), 1e-3)  # pylint: disable=no-member
            )
            & (
                vla_df["ra"]
                > row["ra"]
                - radius.to_value(u.deg)
                / max(np.cos(np.deg2rad(pt_dec_deg)), 1e-3)  # pylint: disable=no-member
            )
        ].copy()
        wsum = 0.0
        for _, crow in field.iterrows():
            f_ra = np.deg2rad(crow["ra"]) if np.isfinite(crow["ra"]) else 0.0
            f_dec = np.deg2rad(crow["dec"]) if np.isfinite(crow["dec"]) else ant_dec
            wsum += (crow["flux_20_cm"] / 1e3) * airy_primary_beam_response(
                ant_ra, ant_dec, f_ra, f_dec, 1.4
            )
        cal_df.at[name, "field_flux"] = wsum

    cal_df["percent_flux"] = cal_df["weighted_flux"] / cal_df["field_flux"].replace(0, np.nan)

    sel = cal_df[
        (cal_df["weighted_flux"] > min_weighted_flux.to_value(u.Jy))  # pylint: disable=no-member
        & (cal_df["percent_flux"] > min_percent_flux)
    ].copy()

    # Fallback: if selection empty, choose top by weighted flux within dec band
    if sel.empty:
        sel = cal_df.sort_values("weighted_flux", ascending=False).head(10).copy()
        # If any field_flux is zero (rare), set percent_flux=1 for ranking purposes
        z = sel["field_flux"] == 0
        sel.loc[z, "percent_flux"] = 1.0

    # Reformat columns and units
    out = sel.copy()
    out["flux (Jy)"] = out["flux_20_cm"] / 1e3
    out = out.rename(columns={"code_20_cm": "code_20_cm", "ra": "ra(deg)", "dec": "dec(deg)"})
    out = out[
        [
            "ra(deg)",
            "dec(deg)",
            "flux (Jy)",
            "weighted_flux",
            "percent_flux",
            "code_20_cm",
        ]
    ]
    out.to_csv(csv_path, index=True)
    return csv_path


def update_caltable(
    vla_df: pd.DataFrame, pt_dec: u.Quantity, out_dir: str = ".cache/catalogs"
) -> str:
    """Ensure a declination-specific caltable exists; return its path."""
    os.makedirs(out_dir, exist_ok=True)
    decsign = "+" if pt_dec.to_value(u.deg) >= 0 else "-"  # pylint: disable=no-member
    decval = f"{abs(pt_dec.to_value(u.deg)):05.1f}".replace(".", "p")  # pylint: disable=no-member
    csv_path = str(Path(out_dir) / f"calibrator_sources_dec{decsign}{decval}.csv")
    if not os.path.exists(csv_path):
        generate_caltable(vla_df=vla_df, pt_dec=pt_dec, csv_path=csv_path)
    return csv_path


def query_nvss_sources(
    ra_deg: float,
    dec_deg: float,
    radius_deg: float,
    min_flux_mjy: Optional[float] = None,
    max_sources: Optional[int] = None,
    catalog_path: Optional[str | os.PathLike[str]] = None,
    use_csv_fallback: bool = False,
) -> pd.DataFrame:
    """Query NVSS catalog for sources within a radius using SQLite database.

    This function requires SQLite databases for optimal performance (~170× faster than CSV).
    CSV fallback is available but disabled by default. Set use_csv_fallback=True to enable.

    Args:
        ra_deg: Field center RA in degrees
        dec_deg: Field center Dec in degrees
        radius_deg: Search radius in degrees
        min_flux_mjy: Minimum flux in mJy (optional)
        max_sources: Maximum number of sources to return (optional)
        catalog_path: Explicit path to SQLite database (overrides auto-resolution)
        use_csv_fallback: If True, fall back to CSV when SQLite fails (default: False)

    Returns:
        DataFrame with columns: ra_deg, dec_deg, flux_mjy
    """
    import sqlite3

    # Try SQLite first (much faster)
    db_path = None

    # 1. Explicit path provided
    if catalog_path:
        db_path = Path(catalog_path)
        if not db_path.exists():
            db_path = None

    # 2. Auto-resolve based on declination strip
    if db_path is None:
        dec_rounded = round(float(dec_deg), 1)
        db_name = f"nvss_dec{dec_rounded:+.1f}.sqlite3"

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
                db_path = candidate
                break

        # If exact match not found, try to find nearest declination match (within 1.0 degree tolerance)
        if db_path is None:
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
            for catalog_dir in catalog_dirs:
                if not catalog_dir.exists():
                    continue
                # Find all nvss_dec*.sqlite3 files
                for nvss_file in catalog_dir.glob("nvss_dec*.sqlite3"):
                    try:
                        # Extract declination from filename: nvss_dec+54.6.sqlite3 -> 54.6
                        dec_str = nvss_file.stem.replace("nvss_dec", "").replace("+", "")
                        file_dec = float(dec_str)
                        diff = abs(file_dec - float(dec_deg))
                        if diff < best_diff and diff <= 1.0:  # Within 1 degree tolerance
                            best_diff = diff
                            best_match = nvss_file
                    except (ValueError, AttributeError):
                        continue

            if best_match is not None:
                db_path = best_match

    # Query SQLite if available
    if db_path is not None:
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row

            try:
                # Approximate box search (faster than exact angular separation)
                # Account for RA wrapping at dec
                cos_dec = max(np.cos(np.radians(dec_deg)), 1e-3)
                ra_half = radius_deg / cos_dec
                dec_half = radius_deg

                # Build query with spatial index
                where_clauses = [
                    "ra_deg BETWEEN ? AND ?",
                    "dec_deg BETWEEN ? AND ?",
                ]
                params = [
                    ra_deg - ra_half,
                    ra_deg + ra_half,
                    dec_deg - dec_half,
                    dec_deg + dec_half,
                ]

                if min_flux_mjy is not None:
                    where_clauses.append("flux_mjy >= ?")
                    params.append(min_flux_mjy)

                query = f"""
                SELECT ra_deg, dec_deg, flux_mjy
                FROM sources
                WHERE {' AND '.join(where_clauses)}
                ORDER BY flux_mjy DESC
                """

                if max_sources:
                    query += f" LIMIT {max_sources}"

                rows = conn.execute(query, params).fetchall()

                if not rows:
                    return pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])

                df = pd.DataFrame([dict(row) for row in rows])

                # Exact angular separation filter (post-query refinement)
                if len(df) > 0:
                    sc = SkyCoord(
                        ra=df["ra_deg"].values * u.deg,  # pylint: disable=no-member
                        dec=df["dec_deg"].values * u.deg,  # pylint: disable=no-member
                        frame="icrs",
                    )
                    center = SkyCoord(
                        ra_deg * u.deg, dec_deg * u.deg, frame="icrs"
                    )  # pylint: disable=no-member
                    sep = sc.separation(center).deg
                    df = df[sep <= radius_deg].copy()

                    # Re-apply flux filter if needed (for exact separation)
                    if min_flux_mjy is not None and len(df) > 0:
                        df = df[df["flux_mjy"] >= min_flux_mjy].copy()

                    # Re-apply limit if needed
                    if max_sources and len(df) > max_sources:
                        df = df.head(max_sources)

                return df

            finally:
                conn.close()

        except Exception as e:
            # SQLite query failed
            if use_csv_fallback:
                print(
                    "Note: CSV catalog is available as an alternative. "
                    "Set use_csv_fallback=True to enable CSV fallback (slower, ~1s vs ~0.01s)."
                )
                logger.warning(
                    f"SQLite query failed ({e}), falling back to CSV. "
                    f"This will be slower (~1s vs ~0.01s)."
                )
                # Fallback to CSV (slower but always works)
                df_full = read_nvss_catalog()

                # Convert to SkyCoord for separation calculation
                sc = SkyCoord(
                    ra=df_full["ra"].values * u.deg,  # pylint: disable=no-member
                    dec=df_full["dec"].values * u.deg,  # pylint: disable=no-member
                    frame="icrs",
                )
                center = SkyCoord(
                    ra_deg * u.deg, dec_deg * u.deg, frame="icrs"  # pylint: disable=no-member
                )  # pylint: disable=no-member
                sep = sc.separation(center).deg

                # Filter by separation
                keep = sep <= radius_deg

                # Filter by flux if specified
                if min_flux_mjy is not None:
                    flux_mjy = pd.to_numeric(df_full["flux_20_cm"], errors="coerce")
                    keep = keep & (flux_mjy >= min_flux_mjy)

                result = df_full[keep].copy()

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

                # Select only the columns we need
                if len(result) > 0:
                    result = result[["ra_deg", "dec_deg", "flux_mjy"]].copy()
                else:
                    result = pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])

                return result
            else:
                # No fallback - return empty DataFrame
                logger.error(
                    f"SQLite query failed ({e}). "
                    f"SQLite database required. CSV fallback is available but disabled. "
                    f"Set use_csv_fallback=True to enable CSV fallback."
                )
                print(
                    "Note: CSV catalog is available as an alternative. "
                    "Set use_csv_fallback=True to enable CSV fallback (slower, ~1s vs ~0.01s)."
                )
                return pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])

    # No SQLite database found and CSV fallback disabled
    if db_path is None:
        logger.error(
            "SQLite database not found. SQLite database required. "
            "CSV fallback is available but disabled. "
            "Set use_csv_fallback=True to enable CSV fallback."
        )
        print(
            "Note: CSV catalog is available as an alternative. "
            "Set use_csv_fallback=True to enable CSV fallback (slower, ~1s vs ~0.01s)."
        )
        return pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])


def query_rax_sources(
    ra_deg: float,
    dec_deg: float,
    radius_deg: float,
    min_flux_mjy: Optional[float] = None,
    max_sources: Optional[int] = None,
    catalog_path: Optional[str | os.PathLike[str]] = None,
    use_csv_fallback: bool = False,
) -> pd.DataFrame:
    """Query RACS/RAX catalog for sources within a radius using SQLite database.

    This function requires SQLite databases for optimal performance (~170× faster than CSV).
    CSV fallback is available but disabled by default. Set use_csv_fallback=True to enable.

    Args:
        ra_deg: Field center RA in degrees
        dec_deg: Field center Dec in degrees
        radius_deg: Search radius in degrees
        min_flux_mjy: Minimum flux in mJy (optional)
        max_sources: Maximum number of sources to return (optional)
        catalog_path: Explicit path to SQLite database (overrides auto-resolution)
        use_csv_fallback: If True, fall back to CSV when SQLite fails (default: False)

    Returns:
        DataFrame with columns: ra_deg, dec_deg, flux_mjy
    """
    import sqlite3

    # Try SQLite first (much faster)
    db_path = None

    # 1. Explicit path provided
    if catalog_path:
        db_path = Path(catalog_path)
        if not db_path.exists():
            db_path = None

    # 2. Auto-resolve based on declination strip
    if db_path is None:
        dec_rounded = round(float(dec_deg), 1)
        db_name = f"rax_dec{dec_rounded:+.1f}.sqlite3"

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
                db_path = candidate
                break

    # Query SQLite if available
    if db_path is not None:
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row

            try:
                # Approximate box search (faster than exact angular separation)
                cos_dec = max(np.cos(np.radians(dec_deg)), 1e-3)
                ra_half = radius_deg / cos_dec
                dec_half = radius_deg

                # Build query with spatial index
                where_clauses = [
                    "ra_deg BETWEEN ? AND ?",
                    "dec_deg BETWEEN ? AND ?",
                ]
                params = [
                    ra_deg - ra_half,
                    ra_deg + ra_half,
                    dec_deg - dec_half,
                    dec_deg + dec_half,
                ]

                if min_flux_mjy is not None:
                    where_clauses.append("flux_mjy >= ?")
                    params.append(min_flux_mjy)

                query = f"""
                SELECT ra_deg, dec_deg, flux_mjy
                FROM sources
                WHERE {' AND '.join(where_clauses)}
                ORDER BY flux_mjy DESC
                """

                if max_sources:
                    query += f" LIMIT {max_sources}"

                rows = conn.execute(query, params).fetchall()

                if not rows:
                    return pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])

                df = pd.DataFrame([dict(row) for row in rows])

                # Exact angular separation filter (post-query refinement)
                if len(df) > 0:
                    sc = SkyCoord(
                        ra=df["ra_deg"].values * u.deg,  # pylint: disable=no-member
                        dec=df["dec_deg"].values * u.deg,  # pylint: disable=no-member
                        frame="icrs",
                    )
                    center = SkyCoord(
                        ra_deg * u.deg, dec_deg * u.deg, frame="icrs"
                    )  # pylint: disable=no-member
                    sep = sc.separation(center).deg
                    df = df[sep <= radius_deg].copy()

                    # Re-apply flux filter if needed
                    if min_flux_mjy is not None and len(df) > 0:
                        df = df[df["flux_mjy"] >= min_flux_mjy].copy()

                    # Re-apply limit if needed
                    if max_sources and len(df) > max_sources:
                        df = df.head(max_sources)

                return df

            finally:
                conn.close()

        except Exception as e:
            # SQLite query failed
            if use_csv_fallback:
                print(
                    "Note: CSV catalog is available as an alternative. "
                    "Set use_csv_fallback=True to enable CSV fallback (slower, ~1s vs ~0.01s)."
                )
                logger.warning(
                    f"SQLite query failed ({e}), falling back to CSV. "
                    f"This will be slower (~1s vs ~0.01s)."
                )
                # Fallback to CSV (slower but always works)
                df_full = read_rax_catalog()

                # Normalize column names for RAX
                from dsa110_contimg.catalog.build_master import _normalize_columns

                RAX_CANDIDATES = {
                    "ra": ["ra", "ra_deg", "raj2000", "ra_hms"],
                    "dec": ["dec", "dec_deg", "dej2000", "dec_dms"],
                    "flux": ["flux", "flux_mjy", "flux_jy", "peak_flux", "fpeak", "s1.4"],
                }
                col_map = _normalize_columns(df_full, RAX_CANDIDATES)

                ra_col = col_map.get("ra", "ra")
                dec_col = col_map.get("dec", "dec")
                flux_col = col_map.get("flux", None)

                # Convert to SkyCoord for separation calculation
                ra_vals = pd.to_numeric(df_full[ra_col], errors="coerce")
                dec_vals = pd.to_numeric(df_full[dec_col], errors="coerce")
                sc = SkyCoord(
                    ra=ra_vals.values * u.deg,  # pylint: disable=no-member
                    dec=dec_vals.values * u.deg,
                    frame="icrs",
                )  # pylint: disable=no-member
                center = SkyCoord(
                    ra_deg * u.deg, dec_deg * u.deg, frame="icrs"  # pylint: disable=no-member
                )  # pylint: disable=no-member
                sep = sc.separation(center).deg

                # Filter by separation
                keep = sep <= radius_deg

                # Filter by flux if specified
                if min_flux_mjy is not None and flux_col:
                    flux_vals = pd.to_numeric(df_full[flux_col], errors="coerce")
                    # Convert to mJy if needed (assume > 1000 means Jy)
                    if len(flux_vals) > 0 and flux_vals.max() > 1000:
                        flux_vals = flux_vals * 1000.0
                    keep = keep & (flux_vals >= min_flux_mjy)

                result = df_full[keep].copy()

                # Standardize column names
                result["ra_deg"] = pd.to_numeric(result[ra_col], errors="coerce")
                result["dec_deg"] = pd.to_numeric(result[dec_col], errors="coerce")

                if flux_col and flux_col in result.columns:
                    flux_vals = pd.to_numeric(result[flux_col], errors="coerce")
                    if len(flux_vals) > 0 and flux_vals.max() > 1000:
                        result["flux_mjy"] = flux_vals * 1000.0
                    else:
                        result["flux_mjy"] = flux_vals
                else:
                    result["flux_mjy"] = None

                # Sort by flux and limit
                if "flux_mjy" in result.columns and result["flux_mjy"].notna().any():
                    result = result.sort_values("flux_mjy", ascending=False, na_position="last")
                if max_sources:
                    result = result.head(max_sources)

                # Select only the columns we need
                if len(result) > 0:
                    result = result[["ra_deg", "dec_deg", "flux_mjy"]].copy()
                else:
                    result = pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])

                return result
            else:
                # No fallback - return empty DataFrame
                logger.error(
                    f"SQLite query failed ({e}). "
                    f"SQLite database required. CSV fallback is available but disabled. "
                    f"Set use_csv_fallback=True to enable CSV fallback."
                )
                print(
                    "Note: CSV catalog is available as an alternative. "
                    "Set use_csv_fallback=True to enable CSV fallback (slower, ~1s vs ~0.01s)."
                )
                return pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])

    # No SQLite database found and CSV fallback disabled
    if db_path is None:
        logger.error(
            "SQLite database not found. SQLite database required. "
            "CSV fallback is available but disabled. "
            "Set use_csv_fallback=True to enable CSV fallback."
        )
        print(
            "Note: CSV catalog is available as an alternative. "
            "Set use_csv_fallback=True to enable CSV fallback (slower, ~1s vs ~0.01s)."
        )
        return pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])


def query_vlass_sources(
    ra_deg: float,
    dec_deg: float,
    radius_deg: float,
    min_flux_mjy: Optional[float] = None,
    max_sources: Optional[int] = None,
    catalog_path: Optional[str | os.PathLike[str]] = None,
    use_csv_fallback: bool = False,
) -> pd.DataFrame:
    """Query VLASS catalog for sources within a radius using SQLite database.

    This function requires SQLite databases for optimal performance (~170× faster than CSV).
    CSV fallback is available but disabled by default. Set use_csv_fallback=True to enable.

    Args:
        ra_deg: Field center RA in degrees
        dec_deg: Field center Dec in degrees
        radius_deg: Search radius in degrees
        min_flux_mjy: Minimum flux in mJy (optional)
        max_sources: Maximum number of sources to return (optional)
        catalog_path: Explicit path to SQLite database (overrides auto-resolution)
        use_csv_fallback: If True, fall back to CSV when SQLite fails (default: False)

    Returns:
        DataFrame with columns: ra_deg, dec_deg, flux_mjy
    """
    import sqlite3

    # Try SQLite first (much faster)
    db_path = None

    # 1. Explicit path provided
    if catalog_path:
        db_path = Path(catalog_path)
        if not db_path.exists():
            db_path = None

    # 2. Auto-resolve based on declination strip
    if db_path is None:
        dec_rounded = round(float(dec_deg), 1)
        db_name = f"vlass_dec{dec_rounded:+.1f}.sqlite3"

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
                db_path = candidate
                break

    # Query SQLite if available
    if db_path is not None:
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row

            try:
                # Approximate box search (faster than exact angular separation)
                cos_dec = max(np.cos(np.radians(dec_deg)), 1e-3)
                ra_half = radius_deg / cos_dec
                dec_half = radius_deg

                # Build query with spatial index
                where_clauses = [
                    "ra_deg BETWEEN ? AND ?",
                    "dec_deg BETWEEN ? AND ?",
                ]
                params = [
                    ra_deg - ra_half,
                    ra_deg + ra_half,
                    dec_deg - dec_half,
                    dec_deg + dec_half,
                ]

                if min_flux_mjy is not None:
                    where_clauses.append("flux_mjy >= ?")
                    params.append(min_flux_mjy)

                query = f"""
                SELECT ra_deg, dec_deg, flux_mjy
                FROM sources
                WHERE {' AND '.join(where_clauses)}
                ORDER BY flux_mjy DESC
                """

                if max_sources:
                    query += f" LIMIT {max_sources}"

                rows = conn.execute(query, params).fetchall()

                if not rows:
                    return pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])

                df = pd.DataFrame([dict(row) for row in rows])

                # Exact angular separation filter (post-query refinement)
                if len(df) > 0:
                    sc = SkyCoord(
                        ra=df["ra_deg"].values * u.deg,  # pylint: disable=no-member
                        dec=df["dec_deg"].values * u.deg,  # pylint: disable=no-member
                        frame="icrs",
                    )
                    center = SkyCoord(
                        ra_deg * u.deg, dec_deg * u.deg, frame="icrs"
                    )  # pylint: disable=no-member
                    sep = sc.separation(center).deg
                    df = df[sep <= radius_deg].copy()

                    # Re-apply flux filter if needed
                    if min_flux_mjy is not None and len(df) > 0:
                        df = df[df["flux_mjy"] >= min_flux_mjy].copy()

                    # Re-apply limit if needed
                    if max_sources and len(df) > max_sources:
                        df = df.head(max_sources)

                return df

            finally:
                conn.close()

        except Exception as e:
            # SQLite query failed
            if use_csv_fallback:
                print(
                    "Note: CSV catalog is available as an alternative. "
                    "Set use_csv_fallback=True to enable CSV fallback (slower, ~1s vs ~0.01s)."
                )
                logger.warning(
                    f"SQLite query failed ({e}), falling back to CSV. "
                    f"This will be slower (~1s vs ~0.01s)."
                )
                # Fallback to CSV (slower but always works)
                # VLASS catalog reading - need to implement read_vlass_catalog or use generic reader
                from dsa110_contimg.catalog.build_master import _read_table

                # Try to find cached VLASS catalog
                cache_dir = ".cache/catalogs"
                os.makedirs(cache_dir, exist_ok=True)
                cache_path = Path(cache_dir) / "vlass_catalog"

                # Try common extensions
                vlass_path = None
                for ext in [".csv", ".fits", ".fits.gz", ".csv.gz"]:
                    candidate = cache_path.with_suffix(ext)
                    if candidate.exists():
                        vlass_path = str(candidate)
                        break

                if vlass_path is None:
                    # Return empty DataFrame if no catalog found
                    logger.warning(
                        "VLASS catalog not found. Please provide catalog_path or place "
                        f"VLASS catalog in {cache_dir}/vlass_catalog.csv or .fits"
                    )
                    return pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])

                df_full = _read_table(vlass_path)

                # Normalize column names for VLASS
                from dsa110_contimg.catalog.build_master import _normalize_columns

                VLASS_CANDIDATES = {
                    "ra": ["ra", "ra_deg", "raj2000"],
                    "dec": ["dec", "dec_deg", "dej2000"],
                    "flux": ["peak_flux", "peak_mjy_per_beam", "flux_peak", "flux", "total_flux"],
                }
                col_map = _normalize_columns(df_full, VLASS_CANDIDATES)

                ra_col = col_map.get("ra", "ra")
                dec_col = col_map.get("dec", "dec")
                flux_col = col_map.get("flux", None)

                # Convert to SkyCoord for separation calculation
                ra_vals = pd.to_numeric(df_full[ra_col], errors="coerce")
                dec_vals = pd.to_numeric(df_full[dec_col], errors="coerce")
                sc = SkyCoord(
                    ra=ra_vals.values * u.deg,  # pylint: disable=no-member
                    dec=dec_vals.values * u.deg,
                    frame="icrs",
                )  # pylint: disable=no-member
                center = SkyCoord(
                    ra_deg * u.deg, dec_deg * u.deg, frame="icrs"  # pylint: disable=no-member
                )  # pylint: disable=no-member
                sep = sc.separation(center).deg

                # Filter by separation
                keep = sep <= radius_deg

                # Filter by flux if specified
                if min_flux_mjy is not None and flux_col:
                    flux_vals = pd.to_numeric(df_full[flux_col], errors="coerce")
                    # VLASS flux is typically in mJy, but check if conversion needed
                    if len(flux_vals) > 0 and flux_vals.max() > 1000:
                        flux_vals = flux_vals * 1000.0  # Convert Jy to mJy
                    keep = keep & (flux_vals >= min_flux_mjy)

                result = df_full[keep].copy()

                # Standardize column names
                result["ra_deg"] = pd.to_numeric(result[ra_col], errors="coerce")
                result["dec_deg"] = pd.to_numeric(result[dec_col], errors="coerce")

                if flux_col and flux_col in result.columns:
                    flux_vals = pd.to_numeric(result[flux_col], errors="coerce")
                    if len(flux_vals) > 0 and flux_vals.max() > 1000:
                        result["flux_mjy"] = flux_vals * 1000.0
                    else:
                        result["flux_mjy"] = flux_vals
                else:
                    result["flux_mjy"] = None

                # Sort by flux and limit
                if "flux_mjy" in result.columns and result["flux_mjy"].notna().any():
                    result = result.sort_values("flux_mjy", ascending=False, na_position="last")
                if max_sources:
                    result = result.head(max_sources)

                # Select only the columns we need
                if len(result) > 0:
                    result = result[["ra_deg", "dec_deg", "flux_mjy"]].copy()
                else:
                    result = pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])

                return result
            else:
                # No fallback - return empty DataFrame
                logger.error(
                    f"SQLite query failed ({e}). "
                    f"SQLite database required. CSV fallback is available but disabled. "
                    f"Set use_csv_fallback=True to enable CSV fallback."
                )
                print(
                    "Note: CSV catalog is available as an alternative. "
                    "Set use_csv_fallback=True to enable CSV fallback (slower, ~1s vs ~0.01s)."
                )
                return pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])

    # No SQLite database found and CSV fallback disabled
    if db_path is None:
        logger.error(
            "SQLite database not found. SQLite database required. "
            "CSV fallback is available but disabled. "
            "Set use_csv_fallback=True to enable CSV fallback."
        )
        print(
            "Note: CSV catalog is available as an alternative. "
            "Set use_csv_fallback=True to enable CSV fallback (slower, ~1s vs ~0.01s)."
        )
        return pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])


def query_catalog_sources(
    catalog_type: str,
    ra_deg: float,
    dec_deg: float,
    radius_deg: float,
    min_flux_mjy: Optional[float] = None,
    max_sources: Optional[int] = None,
    catalog_path: Optional[str | os.PathLike[str]] = None,
    use_csv_fallback: bool = False,
) -> pd.DataFrame:
    """Unified interface to query catalog sources (NVSS, RAX, VLASS).

    This function provides a common API for querying different radio source catalogs.
    It automatically selects the appropriate query function based on catalog_type.

    Args:
        catalog_type: One of "nvss", "rax", "vlass"
        ra_deg: Field center RA in degrees
        dec_deg: Field center Dec in degrees
        radius_deg: Search radius in degrees
        min_flux_mjy: Minimum flux in mJy (optional)
        max_sources: Maximum number of sources to return (optional)
        catalog_path: Explicit path to SQLite database (overrides auto-resolution)
        use_csv_fallback: If True, fall back to CSV when SQLite fails (default: False)

    Returns:
        DataFrame with columns: ra_deg, dec_deg, flux_mjy

    Examples:
        >>> # Query NVSS sources
        >>> df = query_catalog_sources("nvss", ra_deg=83.5, dec_deg=54.6, radius_deg=1.0)

        >>> # Query RAX sources
        >>> df = query_catalog_sources("rax", ra_deg=83.5, dec_deg=54.6, radius_deg=1.0)

        >>> # Query VLASS sources
        >>> df = query_catalog_sources("vlass", ra_deg=83.5, dec_deg=54.6, radius_deg=1.0)
    """
    catalog_type_lower = catalog_type.lower()

    if catalog_type_lower == "nvss":
        return query_nvss_sources(
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            radius_deg=radius_deg,
            min_flux_mjy=min_flux_mjy,
            max_sources=max_sources,
            catalog_path=catalog_path,
            use_csv_fallback=use_csv_fallback,
        )
    elif catalog_type_lower == "rax":
        return query_rax_sources(
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            radius_deg=radius_deg,
            min_flux_mjy=min_flux_mjy,
            max_sources=max_sources,
            catalog_path=catalog_path,
            use_csv_fallback=use_csv_fallback,
        )
    elif catalog_type_lower == "vlass":
        return query_vlass_sources(
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            radius_deg=radius_deg,
            min_flux_mjy=min_flux_mjy,
            max_sources=max_sources,
            catalog_path=catalog_path,
            use_csv_fallback=use_csv_fallback,
        )
    else:
        raise ValueError(
            f"Unsupported catalog_type: {catalog_type}. " f"Supported types: nvss, rax, vlass"
        )
