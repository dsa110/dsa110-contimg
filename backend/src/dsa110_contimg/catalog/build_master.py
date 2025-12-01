#!/opt/miniforge/envs/casa6/bin/python
# pylint: disable=no-member  # astropy.units uses dynamic attributes (deg, arcsec, etc.)
"""
Build a master reference catalog by crossmatching NVSS with VLASS and FIRST.

Outputs an SQLite DB at state/catalogs/master_sources.sqlite3 (by default)
containing one row per NVSS source with optional VLASS/FIRST matches and
derived spectral index and compactness/confusion flags.

Usage examples:

  python -m dsa110_contimg.catalog.build_master \
      --nvss /data/catalogs/NVSS.csv \
      --vlass /data/catalogs/VLASS.csv \
      --first /data/catalogs/FIRST.csv \
      --out state/catalogs/master_sources.sqlite3 \
      --match-radius-arcsec 7.5 \
      --export-view final_references --export-csv state/catalogs/final_refs.csv

Notes:
- This tool is intentionally tolerant of column naming. It attempts to map
  common column names for RA/Dec/flux/SNR in each survey. If your files use
  different names, you can provide explicit mappings via --map-<cat>-<field>.
- Input formats: CSV/TSV (auto-delimited) or FITS (via astropy.table).
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import math
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import astropy.units as u  # pylint: disable=no-member
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord
from astropy.table import Table

logger = logging.getLogger(__name__)


# ----------------------------- IO helpers ---------------------------------


FITS_SUFFIXES = (".fits", ".fit", ".fz", ".fits.gz", ".fit.gz")


def _read_table(path: str) -> pd.DataFrame:
    """Read a catalog (CSV/TSV/FITS) into a pandas DataFrame.

    Delimiter is auto-detected for text. FITS loaded via astropy.table.
    """
    path = os.fspath(path)
    lower = path.lower()
    if lower.endswith(FITS_SUFFIXES):
        t = Table.read(path)
        return t.to_pandas()
    # text
    return pd.read_csv(path, sep=None, engine="python")


def _normalize_columns(df: pd.DataFrame, mapping: Dict[str, Iterable[str]]) -> Dict[str, str]:
    """Return a mapping of canonical->actual column names found in df.

    mapping: {canonical: [candidate1, candidate2, ...]}
    """
    result: Dict[str, str] = {}
    cols = {c.lower(): c for c in df.columns}
    for canon, cands in mapping.items():
        chosen: Optional[str] = None
        for cand in cands:
            key = cand.lower()
            if key in cols:
                chosen = cols[key]
                break
        if chosen is not None:
            result[canon] = chosen
    return result


def _skycoord_from_df(df: pd.DataFrame, ra_col: str, dec_col: str) -> SkyCoord:
    return SkyCoord(ra=df[ra_col].values * u.deg, dec=df[dec_col].values * u.deg, frame="icrs")


# ---------------------------- Crossmatching --------------------------------


@dataclass
class SourceRow:
    ra_deg: float
    dec_deg: float
    s_nvss: Optional[float]
    snr_nvss: Optional[float]
    s_vlass: Optional[float]
    alpha: Optional[float]
    resolved_flag: int
    confusion_flag: int


def _compute_alpha(
    s1: Optional[float], nu1_hz: float, s2: Optional[float], nu2_hz: float
) -> Optional[float]:
    if s1 is None or s2 is None:
        return None
    if s1 <= 0 or s2 <= 0:
        return None
    try:
        return float(math.log(s2 / s1) / math.log(nu2_hz / nu1_hz))
    except Exception:
        return None


def _crossmatch(
    df_nvss: pd.DataFrame,
    df_vlass: Optional[pd.DataFrame],
    df_first: Optional[pd.DataFrame],
    *,
    maps: Dict[str, Dict[str, str]],
    match_radius_arcsec: float,
    scale_nvss_to_jy: float,
    scale_vlass_to_jy: float,
) -> pd.DataFrame:
    """Crossmatch NVSS with optional VLASS and FIRST; compute alpha/flags.

    Returns a DataFrame with canonical columns ready to write to SQLite.
    """
    # Canonical column names we will emit
    out_rows: list[SourceRow] = []

    # Build SkyCoord for NVSS
    n_ra = maps["nvss"]["ra"]
    n_dec = maps["nvss"]["dec"]
    nvss_sc = _skycoord_from_df(df_nvss, n_ra, n_dec)

    # Flux/SNR columns (optional)
    n_flux = maps["nvss"].get("flux")
    n_snr = maps["nvss"].get("snr")

    # Prepare VLASS coord and flux if provided
    vlass_sc = None
    v_flux_col = None
    if (
        df_vlass is not None
        and "vlass" in maps
        and "ra" in maps["vlass"]
        and "dec" in maps["vlass"]
    ):
        vlass_sc = _skycoord_from_df(df_vlass, maps["vlass"]["ra"], maps["vlass"]["dec"])
        v_flux_col = maps["vlass"].get("flux")

    # Prepare FIRST coord and morphology if provided
    first_sc = None
    f_maj = f_min = None
    if (
        df_first is not None
        and "first" in maps
        and "ra" in maps["first"]
        and "dec" in maps["first"]
    ):
        first_sc = _skycoord_from_df(df_first, maps["first"]["ra"], maps["first"]["dec"])
        f_maj = maps["first"].get("maj")
        f_min = maps["first"].get("min")

    radius = match_radius_arcsec * u.arcsec

    # Pre-index matches for VLASS and FIRST using astropy search_around_sky
    v_idx_by_n: Dict[int, list[int]] = {}
    if vlass_sc is not None:
        idx_nv, idx_v, sep2d, _ = nvss_sc.search_around_sky(vlass_sc, radius)
        # For each match, map NVSS index -> list of VLASS indices within radius
        for i_n, i_v in zip(idx_nv, idx_v):
            v_idx_by_n.setdefault(int(i_n), []).append(int(i_v))

    f_idx_by_n: Dict[int, list[int]] = {}
    if first_sc is not None:
        idx_nv, idx_f, sep2d, _ = nvss_sc.search_around_sky(first_sc, radius)
        for i_n, i_f in zip(idx_nv, idx_f):
            f_idx_by_n.setdefault(int(i_n), []).append(int(i_f))

    # Iterate NVSS rows and assemble outputs
    for i in range(len(df_nvss)):
        ra = float(df_nvss.at[i, n_ra])
        dec = float(df_nvss.at[i, n_dec])
        s_nv = None
        snr_nv = None
        if n_flux and n_flux in df_nvss.columns:
            try:
                s_nv = float(df_nvss.at[i, n_flux]) * float(scale_nvss_to_jy)
            except Exception:
                s_nv = None
        if n_snr and n_snr in df_nvss.columns:
            try:
                snr_nv = float(df_nvss.at[i, n_snr])
            except Exception:
                snr_nv = None

        # VLASS match: choose single best (closest) if multiple; flag confusion if >1
        s_vl = None
        confusion = 0
        if vlass_sc is not None:
            cand = v_idx_by_n.get(i, [])
            if len(cand) > 1:
                confusion = 1
            if len(cand) >= 1:
                # pick closest by angular sep
                seps = SkyCoord(ra=ra * u.deg, dec=dec * u.deg).separation(vlass_sc[cand])
                j = int(cand[int(np.argmin(seps.to_value(u.arcsec)))])
                if v_flux_col and v_flux_col in df_vlass.columns:
                    try:
                        s_vl = float(df_vlass.at[j, v_flux_col]) * float(scale_vlass_to_jy)
                    except Exception:
                        s_vl = None

        # FIRST compactness: treat as resolved if deconvolved major/minor above thresholds
        resolved = 0
        if first_sc is not None:
            cand = f_idx_by_n.get(i, [])
            if len(cand) > 1:
                confusion = 1
            if len(cand) >= 1 and (f_maj or f_min):
                seps = SkyCoord(ra=ra * u.deg, dec=dec * u.deg).separation(first_sc[cand])
                j = int(cand[int(np.argmin(seps.to_value(u.arcsec)))])
                maj = None
                mn = None
                try:
                    if f_maj and f_maj in df_first.columns:
                        maj = float(df_first.at[j, f_maj])
                    if f_min and f_min in df_first.columns:
                        mn = float(df_first.at[j, f_min])
                except Exception:
                    maj = None
                    mn = None
                # Heuristic: resolved if either axis > 6 arcsec (FIRST beam ~5")
                if (maj is not None and maj > 6.0) or (mn is not None and mn > 6.0):
                    resolved = 1

        alpha = _compute_alpha(s_nv, 1.4e9, s_vl, 3.0e9)

        out_rows.append(
            SourceRow(
                ra_deg=ra,
                dec_deg=dec,
                s_nvss=s_nv,
                snr_nvss=snr_nv,
                s_vlass=s_vl,
                alpha=alpha,
                resolved_flag=int(resolved),
                confusion_flag=int(confusion),
            )
        )

    # Assemble output DataFrame
    out = pd.DataFrame(
        {
            "ra_deg": [r.ra_deg for r in out_rows],
            "dec_deg": [r.dec_deg for r in out_rows],
            "s_nvss": [r.s_nvss for r in out_rows],
            "snr_nvss": [r.snr_nvss for r in out_rows],
            "s_vlass": [r.s_vlass for r in out_rows],
            "alpha": [r.alpha for r in out_rows],
            "resolved_flag": [r.resolved_flag for r in out_rows],
            "confusion_flag": [r.confusion_flag for r in out_rows],
        }
    )
    # Assign source_id monotonically (NVSS row index surrogate)
    out.insert(0, "source_id", np.arange(len(out), dtype=int))
    return out


# ---------------------------- DB persistence -------------------------------


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_sqlite(
    out: pd.DataFrame,
    db_path: Path,
    *,
    goodref_snr_min: float = 50.0,
    goodref_alpha_min: float = -1.2,
    goodref_alpha_max: float = 0.2,
    finalref_snr_min: float = 80.0,
    finalref_ids: Optional[Iterable[int]] = None,
    materialize_final: bool = False,
    meta_extra: Optional[Dict[str, str]] = None,
) -> None:
    _ensure_dir(db_path)
    with sqlite3.connect(os.fspath(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_id INTEGER PRIMARY KEY,
                ra_deg REAL NOT NULL,
                dec_deg REAL NOT NULL,
                s_nvss REAL,
                snr_nvss REAL,
                s_vlass REAL,
                alpha REAL,
                resolved_flag INTEGER NOT NULL,
                confusion_flag INTEGER NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sources_radec ON sources(ra_deg, dec_deg)")
        # Overwrite (replace on conflict by recreating contents)
        conn.execute("DELETE FROM sources")
        out.to_sql("sources", conn, if_exists="append", index=False)
        # meta table for provenance
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        # Persist thresholds and provenance in meta
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('goodref_snr_min', ?)",
            (str(goodref_snr_min),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('goodref_alpha_min', ?)",
            (str(goodref_alpha_min),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('goodref_alpha_max', ?)",
            (str(goodref_alpha_max),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('finalref_snr_min', ?)",
            (str(finalref_snr_min),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('build_time_iso', ?)",
            (datetime.now(timezone.utc).isoformat(),),
        )
        if meta_extra:
            for k, v in meta_extra.items():
                conn.execute(
                    "INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)",
                    (str(k), str(v)),
                )
        # Create/replace a view for good reference sources
        try:
            conn.execute("DROP VIEW IF EXISTS good_references")
        except Exception:
            pass
        conn.execute(
            f"""
            CREATE VIEW good_references AS
            SELECT * FROM sources
            WHERE snr_nvss IS NOT NULL AND snr_nvss > {goodref_snr_min}
              AND resolved_flag = 0 AND confusion_flag = 0
              AND alpha IS NOT NULL AND alpha BETWEEN {goodref_alpha_min} AND {goodref_alpha_max}
            """
        )
        # Optional: stable IDs constraint for final references
        if finalref_ids is not None:
            try:
                conn.execute("DROP TABLE IF EXISTS stable_ids")
            except Exception:
                pass
            conn.execute("CREATE TABLE IF NOT EXISTS stable_ids(source_id INTEGER PRIMARY KEY)")
            rows = [(int(i),) for i in finalref_ids if i is not None]
            if rows:
                conn.executemany("INSERT OR IGNORE INTO stable_ids(source_id) VALUES(?)", rows)
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('finalref_ids_count', ?)",
                (str(len(rows)),),
            )
        else:
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('finalref_ids_count', '0')"
            )
        # Create final_references view: stricter SNR and (optionally) membership in stable_ids
        try:
            conn.execute("DROP VIEW IF EXISTS final_references")
        except Exception:
            pass
        if finalref_ids is not None:
            conn.execute(
                f"""
                CREATE VIEW final_references AS
                SELECT s.* FROM sources s
                JOIN stable_ids t ON t.source_id = s.source_id
                WHERE s.snr_nvss IS NOT NULL AND s.snr_nvss > {finalref_snr_min}
                  AND s.resolved_flag = 0 AND s.confusion_flag = 0
                  AND s.alpha IS NOT NULL AND s.alpha BETWEEN {goodref_alpha_min} AND {goodref_alpha_max}
                """
            )
        else:
            conn.execute(
                f"""
                CREATE VIEW final_references AS
                SELECT * FROM sources
                WHERE snr_nvss IS NOT NULL AND snr_nvss > {finalref_snr_min}
                  AND resolved_flag = 0 AND confusion_flag = 0
                  AND alpha IS NOT NULL AND alpha BETWEEN {goodref_alpha_min} AND {goodref_alpha_max}
                """
            )
        # Optionally materialize final_references into a table snapshot
        if materialize_final:
            try:
                conn.execute("DROP TABLE IF EXISTS final_references_table")
            except Exception:
                pass
            conn.execute("CREATE TABLE final_references_table AS SELECT * FROM final_references")


# ----------------------------- Column maps ---------------------------------


NVSS_CANDIDATES = {
    "ra": ["ra", "raj2000", "ra_deg"],
    "dec": ["dec", "dej2000", "dec_deg"],
    "flux": ["s1.4", "flux", "flux_jy", "peak_flux", "spk", "s_pk"],
    "snr": ["snr", "s/n", "snratio"],
}

VLASS_CANDIDATES = {
    "ra": ["ra", "ra_deg", "raj2000"],
    "dec": ["dec", "dec_deg", "dej2000"],
    # Prefer peak flux density for compactness comparisons
    "flux": ["peak_flux", "peak_mjy_per_beam", "flux_peak", "flux", "total_flux"],
}

FIRST_CANDIDATES = {
    "ra": ["ra", "ra_deg", "raj2000"],
    "dec": ["dec", "dec_deg", "dej2000"],
    # deconvolved major/minor FWHM in arcsec if present
    "maj": ["deconv_maj", "maj", "fwhm_maj", "deconvolved_major"],
    "min": ["deconv_min", "min", "fwhm_min", "deconvolved_minor"],
}


# ------------------------------- CLI ---------------------------------------


def build_master(
    nvss_path: str,
    *,
    vlass_path: Optional[str] = None,
    first_path: Optional[str] = None,
    out_db: str = "state/catalogs/master_sources.sqlite3",
    match_radius_arcsec: float = 7.5,
    map_nvss: Optional[Dict[str, str]] = None,
    map_vlass: Optional[Dict[str, str]] = None,
    map_first: Optional[Dict[str, str]] = None,
    nvss_flux_unit: str = "jy",
    vlass_flux_unit: str = "jy",
    goodref_snr_min: float = 50.0,
    goodref_alpha_min: float = -1.2,
    goodref_alpha_max: float = 0.2,
    finalref_snr_min: float = 80.0,
    finalref_ids_file: Optional[str] = None,
    materialize_final: bool = False,
) -> Path:
    df_nvss = _read_table(nvss_path)
    df_vlass = _read_table(vlass_path) if vlass_path else None
    df_first = _read_table(first_path) if first_path else None

    # Resolve column names
    nv_map = _normalize_columns(df_nvss, NVSS_CANDIDATES)
    if map_nvss:
        nv_map.update(map_nvss)
    v_map: Dict[str, str] = {}
    if df_vlass is not None:
        v_map = _normalize_columns(df_vlass, VLASS_CANDIDATES)
        if map_vlass:
            v_map.update(map_vlass)
    f_map: Dict[str, str] = {}
    if df_first is not None:
        f_map = _normalize_columns(df_first, FIRST_CANDIDATES)
        if map_first:
            f_map.update(map_first)

    # Unit scales to Jy
    def _scale(unit: str) -> float:
        u = unit.lower()
        if u in ("jy",):
            return 1.0
        if u in ("mjy",):
            return 1e-3
        if u in ("ujy", "µjy", "uJy"):
            return 1e-6
        # default assume already Jy
        return 1.0

    out = _crossmatch(
        df_nvss,
        df_vlass,
        df_first,
        maps={"nvss": nv_map, "vlass": v_map, "first": f_map},
        match_radius_arcsec=match_radius_arcsec,
        scale_nvss_to_jy=_scale(nvss_flux_unit),
        scale_vlass_to_jy=_scale(vlass_flux_unit),
    )

    # Build meta provenance: file hashes and row counts
    def _hash(path: Optional[str]) -> Tuple[str, int, int]:
        if not path:
            return ("", 0, 0)
        h = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            size = os.path.getsize(path)
            mtime = int(os.path.getmtime(path))
            return (h.hexdigest(), int(size), mtime)
        except Exception:
            return ("", 0, 0)

    meta_extra: Dict[str, str] = {}
    hv, sv, mv = _hash(nvss_path)
    meta_extra.update(
        {
            "nvss_path": os.fspath(nvss_path),
            "nvss_sha256": hv,
            "nvss_size": str(sv),
            "nvss_mtime": str(mv),
            "nvss_rows": str(len(df_nvss)),
        }
    )
    if vlass_path:
        hv, sv, mv = _hash(vlass_path)
        meta_extra.update(
            {
                "vlass_path": os.fspath(vlass_path),
                "vlass_sha256": hv,
                "vlass_size": str(sv),
                "vlass_mtime": str(mv),
                "vlass_rows": str(len(df_vlass) if df_vlass is not None else 0),
            }
        )
    if first_path:
        hv, sv, mv = _hash(first_path)
        meta_extra.update(
            {
                "first_path": os.fspath(first_path),
                "first_sha256": hv,
                "first_size": str(sv),
                "first_mtime": str(mv),
                "first_rows": str(len(df_first) if df_first is not None else 0),
            }
        )

    # Optional final reference IDs
    final_ids: Optional[list[int]] = None
    if finalref_ids_file:
        try:
            with open(finalref_ids_file, "r", encoding="utf-8") as f:
                final_ids = [
                    int(x.strip()) for x in f if x.strip() and not x.strip().startswith("#")
                ]
        except Exception:
            final_ids = None

    out_db_path = Path(out_db)
    _write_sqlite(
        out,
        out_db_path,
        goodref_snr_min=goodref_snr_min,
        goodref_alpha_min=goodref_alpha_min,
        goodref_alpha_max=goodref_alpha_max,
        finalref_snr_min=finalref_snr_min,
        finalref_ids=final_ids,
        materialize_final=materialize_final,
        meta_extra=meta_extra,
    )
    return out_db_path


def _add_map_args(p: argparse.ArgumentParser, prefix: str) -> None:
    p.add_argument(f"--map-{prefix}-ra", dest=f"map_{prefix}_ra")
    p.add_argument(f"--map-{prefix}-dec", dest=f"map_{prefix}_dec")
    p.add_argument(f"--map-{prefix}-flux", dest=f"map_{prefix}_flux")
    if prefix == "first":
        p.add_argument(f"--map-{prefix}-maj", dest=f"map_{prefix}_maj")
        p.add_argument(f"--map-{prefix}-min", dest=f"map_{prefix}_min")


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Build master catalog (NVSS + VLASS/FIRST)")
    ap.add_argument("--nvss", required=True, help="Path to NVSS catalog (CSV/FITS)")
    ap.add_argument("--vlass", help="Path to VLASS catalog (CSV/FITS)")
    ap.add_argument("--first", help="Path to FIRST catalog (CSV/FITS)")
    ap.add_argument(
        "--out",
        default="state/catalogs/master_sources.sqlite3",
        help="Output SQLite DB path",
    )
    ap.add_argument("--match-radius-arcsec", type=float, default=7.5)
    ap.add_argument(
        "--nvss-flux-unit",
        choices=["jy", "mjy", "ujy"],
        default="jy",
        help="Units of NVSS flux column (converted to Jy)",
    )
    ap.add_argument(
        "--vlass-flux-unit",
        choices=["jy", "mjy", "ujy"],
        default="jy",
        help="Units of VLASS flux column (converted to Jy)",
    )
    ap.add_argument(
        "--goodref-snr-min",
        type=float,
        default=50.0,
        help="SNR threshold for good reference view",
    )
    ap.add_argument(
        "--goodref-alpha-min",
        type=float,
        default=-1.2,
        help="Min alpha for good reference view",
    )
    ap.add_argument(
        "--goodref-alpha-max",
        type=float,
        default=0.2,
        help="Max alpha for good reference view",
    )
    ap.add_argument(
        "--finalref-snr-min",
        type=float,
        default=80.0,
        help="SNR threshold for final references view",
    )
    ap.add_argument(
        "--finalref-ids",
        help="Optional file with source_id list (one per line) to define long-term stable set",
    )
    ap.add_argument(
        "--materialize-final",
        action="store_true",
        help="Create final_references_table materialized from view",
    )
    # Optional export helpers
    ap.add_argument(
        "--export-view",
        choices=[
            "sources",
            "good_references",
            "final_references",
            "final_references_table",
        ],
        help="Optionally export a table/view to CSV after building the DB",
    )
    ap.add_argument(
        "--export-csv",
        help="Path to CSV to write for --export-view (defaults to <out>_<view>.csv)",
    )
    _add_map_args(ap, "nvss")
    _add_map_args(ap, "vlass")
    _add_map_args(ap, "first")
    args = ap.parse_args(argv)

    map_nv = {
        k.split("map_nvss_")[1]: v for k, v in vars(args).items() if k.startswith("map_nvss_") and v
    }
    map_vl = {
        k.split("map_vlass_")[1]: v
        for k, v in vars(args).items()
        if k.startswith("map_vlass_") and v
    }
    map_fi = {
        k.split("map_first_")[1]: v
        for k, v in vars(args).items()
        if k.startswith("map_first_") and v
    }

    try:
        outp = build_master(
            args.nvss,
            vlass_path=args.vlass,
            first_path=args.first,
            out_db=args.out,
            match_radius_arcsec=args.match_radius_arcsec,
            map_nvss=map_nv or None,
            map_vlass=map_vl or None,
            map_first=map_fi or None,
            nvss_flux_unit=args.nvss_flux_unit,
            vlass_flux_unit=args.vlass_flux_unit,
            goodref_snr_min=args.goodref_snr_min,
            goodref_alpha_min=args.goodref_alpha_min,
            goodref_alpha_max=args.goodref_alpha_max,
            finalref_snr_min=args.finalref_snr_min,
            finalref_ids_file=args.finalref_ids,
            materialize_final=args.materialize_final,
        )
        logger.info(f"Wrote master catalog to: {outp}")
        print(f"Wrote master catalog to: {outp}")  # User-facing output
        # Optional export
        if args.export_view:
            # CRITICAL: Whitelist allowed view/table names to prevent SQL injection
            ALLOWED_EXPORT_VIEWS = {
                "sources",
                "good_references",
                "final_references",
                "final_references_table",
            }
            if args.export_view not in ALLOWED_EXPORT_VIEWS:
                raise ValueError(
                    f"Invalid export view: {args.export_view}. "
                    f"Allowed views: {', '.join(sorted(ALLOWED_EXPORT_VIEWS))}"
                )
            try:
                import pandas as _pd

                with sqlite3.connect(os.fspath(outp)) as _conn:
                    # Safe: view name is whitelisted, query is parameterized
                    df = _pd.read_sql_query(f"SELECT * FROM {args.export_view}", _conn)
                export_path = (
                    Path(args.export_csv)
                    if args.export_csv
                    else Path(outp)
                    .with_suffix("")
                    .with_name(f"{Path(outp).stem}_{args.export_view}.csv")
                )
                export_path.parent.mkdir(parents=True, exist_ok=True)
                df.to_csv(export_path, index=False)
                logger.info(f"Exported {args.export_view} to: {export_path}")
                print(f"Exported {args.export_view} to: {export_path}")  # User-facing output
            except Exception as _e:
                logger.error(f"Export failed: {_e}", exc_info=True)
                print(f"Export failed: {_e}")  # User-facing error
        return 0
    except Exception as e:
        logger.error(f"Failed to build master catalog: {e}", exc_info=True)
        print(f"Failed to build master catalog: {e}")  # User-facing error
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
