#!/opt/miniforge/envs/casa6/bin/python
"""
Build VLA calibrator SQLite database from the official VLA calibrator manual.

This module parses the VLA calibrator text file format and creates a SQLite
database optimized for fast spatial queries during calibrator selection.

The database is the ONLY permissible source for VLA calibrator information
in the pipeline. Direct access to raw text files or archive directories
is strictly prohibited.

Schema:
  - calibrators(name PRIMARY KEY, ra_deg, dec_deg, position_code, alt_name)
  - fluxes(name, band, flux_jy, quality_codes, PRIMARY KEY(name, band))
  - meta(key PRIMARY KEY, value)

Views:
  - vla_20cm: calibrators with 20cm flux measurements

Usage:
  python -m dsa110_contimg.catalog.build_vla_calibrators \\
    --source /path/to/vlacalibrators.txt \\
    --out /data/dsa110-contimg/state/catalogs/vla_calibrators.sqlite3

  # Or to download from NRAO and build:
  python -m dsa110_contimg.catalog.build_vla_calibrators --download
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import re
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.request import urlopen

import astropy.units as u
from astropy.coordinates import SkyCoord

logger = logging.getLogger(__name__)

# Default output location
DEFAULT_OUTPUT_DB = Path("/data/dsa110-contimg/state/catalogs/vla_calibrators.sqlite3")

# NRAO VLA calibrator manual URL (for --download option)
VLA_CALIBRATOR_URL = "https://www.vla.nrao.edu/astro/calib/manual/csource.txt"

# Band name mapping
BAND_MAPPING = {
    "90cm": ("P", 0.33e9),
    "20cm": ("L", 1.4e9),
    "6cm": ("C", 5.0e9),
    "3.7cm": ("X", 8.4e9),
    "2cm": ("U", 15.0e9),
    "1.3cm": ("K", 22.0e9),
    "0.7cm": ("Q", 43.0e9),
}


def _hash_file(path: Path) -> Tuple[str, int, int]:
    """Compute SHA256 hash, size, and mtime of a file."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return (h.hexdigest(), path.stat().st_size, int(path.stat().st_mtime))
    except Exception:
        return ("", 0, 0)


def _parse_ra_dec(ra_str: str, dec_str: str) -> Tuple[float, float]:
    """Parse VLA calibrator RA/Dec strings to degrees.

    Args:
        ra_str: RA string like "00h05m04.363531s"
        dec_str: Dec string like "54d28'24.926230\"" or "-06d23'35.335300\""

    Returns:
        Tuple of (ra_deg, dec_deg)
    """
    # Clean up the strings
    ra_str = ra_str.strip()
    dec_str = dec_str.strip().rstrip('"').rstrip("'")

    try:
        # Try using astropy SkyCoord
        coord = SkyCoord(ra_str, dec_str, unit=(u.hourangle, u.deg))
        return float(coord.ra.deg), float(coord.dec.deg)
    except Exception:
        pass

    # Manual parsing fallback
    # RA: "00h05m04.363531s" -> hours, minutes, seconds
    ra_match = re.match(r"(\d+)h(\d+)m([\d.]+)s", ra_str)
    if ra_match:
        h, m, s = ra_match.groups()
        ra_deg = (float(h) + float(m) / 60 + float(s) / 3600) * 15.0
    else:
        raise ValueError(f"Cannot parse RA: {ra_str}")

    # Dec: "54d28'24.926230\"" or "-06d23'35.335300\""
    dec_match = re.match(r"([+-]?\d+)d(\d+)'([\d.]+)", dec_str)
    if dec_match:
        d, m, s = dec_match.groups()
        sign = -1 if d.startswith("-") else 1
        dec_deg = sign * (abs(float(d)) + float(m) / 60 + float(s) / 3600)
    else:
        raise ValueError(f"Cannot parse Dec: {dec_str}")

    return ra_deg, dec_deg


def parse_vla_calibrators(source_path: Path) -> Tuple[List[Dict], List[Dict]]:
    """Parse VLA calibrator text file.

    Args:
        source_path: Path to vlacalibrators.txt file

    Returns:
        Tuple of (calibrators_list, fluxes_list)
    """
    calibrators = []
    fluxes = []

    with open(source_path, "r") as f:
        content = f.read()

    # Split into calibrator blocks (each starts with J2000 position line)
    # Pattern: name J2000 code RA Dec [ref] [altname]
    j2000_pattern = re.compile(
        r"^(\S+)\s+J2000\s+(\S)\s+"  # name, equinox, position_code
        r"(\d+h\d+m[\d.]+s)\s+"  # RA
        r"([+-]?\d+d\d+\'[\d.]+\"?)",  # Dec
        re.MULTILINE,
    )

    # Band flux pattern: "20cm L X X X X 0.52"
    band_pattern = re.compile(
        r"^\s*(\d+\.?\d*cm)\s+(\S)\s+(\S)\s+(\S)\s+(\S)\s+(\S)\s+([\d.]+)", re.MULTILINE
    )

    # Find all J2000 entries
    matches = list(j2000_pattern.finditer(content))

    for i, match in enumerate(matches):
        name = match.group(1)
        position_code = match.group(2)
        ra_str = match.group(3)
        dec_str = match.group(4)

        try:
            ra_deg, dec_deg = _parse_ra_dec(ra_str, dec_str)
        except Exception as e:
            logger.warning(f"Skipping {name}: {e}")
            continue

        # Get the rest of the line for alt_name
        line_end = content[match.end() :].split("\n")[0]
        alt_name_match = re.search(r"\s+\S+\s+(\S+)\s*$", match.group(0) + line_end)
        alt_name = alt_name_match.group(1) if alt_name_match else None

        calibrators.append(
            {
                "name": name,
                "ra_deg": ra_deg,
                "dec_deg": dec_deg,
                "position_code": position_code,
                "alt_name": alt_name,
            }
        )

        # Find flux entries between this calibrator and the next
        block_start = match.end()
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        block = content[block_start:block_end]

        for flux_match in band_pattern.finditer(block):
            band = flux_match.group(1)
            band_code = flux_match.group(2)
            qual_a = flux_match.group(3)
            qual_b = flux_match.group(4)
            qual_c = flux_match.group(5)
            qual_d = flux_match.group(6)
            flux_jy = float(flux_match.group(7))

            fluxes.append(
                {
                    "name": name,
                    "band": band,
                    "band_code": band_code,
                    "flux_jy": flux_jy,
                    "quality_a": qual_a,
                    "quality_b": qual_b,
                    "quality_c": qual_c,
                    "quality_d": qual_d,
                    "quality_codes": f"{qual_a}{qual_b}{qual_c}{qual_d}",
                }
            )

    logger.info(f"Parsed {len(calibrators)} calibrators with {len(fluxes)} flux entries")
    return calibrators, fluxes


def build_vla_calibrator_db(
    source_path: Path,
    output_path: Path = DEFAULT_OUTPUT_DB,
    *,
    min_flux_jy: float = 0.0,
) -> Path:
    """Build VLA calibrator SQLite database.

    Args:
        source_path: Path to vlacalibrators.txt source file
        output_path: Output SQLite database path
        min_flux_jy: Minimum flux threshold (default: include all)

    Returns:
        Path to created database
    """
    calibrators, fluxes = parse_vla_calibrators(source_path)

    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build database
    with sqlite3.connect(output_path) as conn:
        # Create schema
        conn.execute("""
            CREATE TABLE IF NOT EXISTS calibrators (
                name TEXT PRIMARY KEY,
                ra_deg REAL NOT NULL,
                dec_deg REAL NOT NULL,
                position_code TEXT,
                alt_name TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS fluxes (
                name TEXT NOT NULL,
                band TEXT NOT NULL,
                band_code TEXT,
                flux_jy REAL NOT NULL,
                freq_hz REAL,
                quality_codes TEXT,
                PRIMARY KEY(name, band),
                FOREIGN KEY(name) REFERENCES calibrators(name) ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Clear existing data
        conn.execute("DELETE FROM fluxes")
        conn.execute("DELETE FROM calibrators")

        # Insert calibrators
        for cal in calibrators:
            conn.execute(
                """INSERT OR REPLACE INTO calibrators
                   (name, ra_deg, dec_deg, position_code, alt_name)
                   VALUES (?, ?, ?, ?, ?)""",
                (cal["name"], cal["ra_deg"], cal["dec_deg"], cal["position_code"], cal["alt_name"]),
            )

        # Insert fluxes
        for flux in fluxes:
            if flux["flux_jy"] >= min_flux_jy:
                # Get frequency from band mapping
                freq_hz = BAND_MAPPING.get(flux["band"], (None, None))[1]
                conn.execute(
                    """INSERT OR REPLACE INTO fluxes
                       (name, band, band_code, flux_jy, freq_hz, quality_codes)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        flux["name"],
                        flux["band"],
                        flux["band_code"],
                        flux["flux_jy"],
                        freq_hz,
                        flux["quality_codes"],
                    ),
                )

        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cal_radec ON calibrators(ra_deg, dec_deg)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cal_dec ON calibrators(dec_deg)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_flux_band ON fluxes(band)")

        # Create views
        conn.execute("DROP VIEW IF EXISTS vla_20cm")
        conn.execute("""
            CREATE VIEW vla_20cm AS
            SELECT c.name, c.ra_deg, c.dec_deg, c.position_code, c.alt_name,
                   f.flux_jy, f.quality_codes
            FROM calibrators c
            JOIN fluxes f ON c.name = f.name
            WHERE f.band = '20cm'
        """)

        # Store provenance
        sha, size, mtime = _hash_file(source_path)
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('build_time_iso', ?)",
            (datetime.now(timezone.utc).isoformat(),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('source_path', ?)", (str(source_path),)
        )
        conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('source_sha256', ?)", (sha,))
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('source_size', ?)", (str(size),)
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('calibrator_count', ?)",
            (str(len(calibrators)),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('flux_entry_count', ?)",
            (str(len(fluxes)),),
        )

        conn.commit()

    logger.info(f"Built VLA calibrator database: {output_path}")
    logger.info(f"  Calibrators: {len(calibrators)}")
    logger.info(f"  Flux entries: {len(fluxes)}")

    return output_path


def download_vla_calibrators(output_path: Optional[Path] = None) -> Path:
    """Download VLA calibrator catalog from NRAO.

    Args:
        output_path: Where to save the file (default: temp file)

    Returns:
        Path to downloaded file
    """
    logger.info(f"Downloading VLA calibrators from {VLA_CALIBRATOR_URL}")

    if output_path is None:
        output_path = Path(tempfile.mktemp(suffix=".txt"))

    with urlopen(VLA_CALIBRATOR_URL, timeout=60) as response:
        content = response.read()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(content)

    logger.info(f"Downloaded {len(content)} bytes to {output_path}")
    return output_path


def query_calibrators_by_dec(
    dec_deg: float,
    max_separation: float = 1.5,
    min_flux_jy: float = 1.0,
    band: str = "20cm",
    db_path: Path = DEFAULT_OUTPUT_DB,
) -> List[Dict]:
    """Query VLA calibrators within Dec range.

    Args:
        dec_deg: Target declination in degrees
        max_separation: Maximum Dec separation in degrees
        min_flux_jy: Minimum flux at specified band
        band: Band for flux filtering (default: 20cm)
        db_path: Path to VLA calibrator database

    Returns:
        List of calibrator dicts with name, ra_deg, dec_deg, flux_jy, separation_deg
    """
    if not db_path.exists():
        raise FileNotFoundError(
            f"VLA calibrator database not found: {db_path}. "
            f"Run: python -m dsa110_contimg.catalog.build_vla_calibrators --download"
        )

    dec_min = dec_deg - max_separation
    dec_max = dec_deg + max_separation

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """
            SELECT c.name, c.ra_deg, c.dec_deg, c.position_code, c.alt_name,
                   f.flux_jy, f.quality_codes
            FROM calibrators c
            JOIN fluxes f ON c.name = f.name
            WHERE c.dec_deg BETWEEN ? AND ?
              AND f.band = ?
              AND f.flux_jy >= ?
            ORDER BY f.flux_jy DESC
        """,
            (dec_min, dec_max, band, min_flux_jy),
        )

        results = []
        for row in cursor:
            results.append(
                {
                    "name": row["name"],
                    "ra_deg": row["ra_deg"],
                    "dec_deg": row["dec_deg"],
                    "position_code": row["position_code"],
                    "alt_name": row["alt_name"],
                    "flux_jy": row["flux_jy"],
                    "quality_codes": row["quality_codes"],
                    "separation_deg": abs(row["dec_deg"] - dec_deg),
                }
            )

    return results


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Build VLA calibrator SQLite database")
    parser.add_argument("--source", type=Path, help="Path to vlacalibrators.txt source file")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUTPUT_DB,
        help=f"Output SQLite database path (default: {DEFAULT_OUTPUT_DB})",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download VLA calibrators from NRAO and build database",
    )
    parser.add_argument(
        "--min-flux",
        type=float,
        default=0.0,
        help="Minimum flux threshold in Jy (default: include all)",
    )
    parser.add_argument(
        "--query-dec", type=float, help="Query calibrators near this Dec (test mode)"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s"
    )

    # Query mode
    if args.query_dec is not None:
        results = query_calibrators_by_dec(
            args.query_dec, max_separation=1.5, min_flux_jy=1.0, db_path=args.out
        )
        print(f"Calibrators within 1.5° of Dec={args.query_dec}°:")
        for r in results:
            print(
                f"  {r['name']}: Dec={r['dec_deg']:.3f}° "
                f"flux={r['flux_jy']:.2f}Jy sep={r['separation_deg']:.3f}°"
            )
        return 0

    # Build mode
    if args.download:
        source_path = download_vla_calibrators()
    elif args.source:
        source_path = args.source
    else:
        parser.error("Either --source or --download is required")
        return 1

    try:
        db_path = build_vla_calibrator_db(source_path, args.out, min_flux_jy=args.min_flux)
        print(f"Built VLA calibrator database: {db_path}")

        # Show summary
        with sqlite3.connect(db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM calibrators").fetchone()[0]
            flux_count = conn.execute("SELECT COUNT(*) FROM fluxes").fetchone()[0]
            l_count = conn.execute("SELECT COUNT(*) FROM fluxes WHERE band='20cm'").fetchone()[0]
            print(f"  Total calibrators: {count}")
            print(f"  Total flux entries: {flux_count}")
            print(f"  Calibrators with 20cm flux: {l_count}")

        return 0
    except Exception as e:
        logger.error(f"Build failed: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
