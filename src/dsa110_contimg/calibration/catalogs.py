import os
import gzip
from urllib.request import urlretrieve
from pathlib import Path
from typing import Optional, Tuple, List

import numpy as np
import pandas as pd
from astropy.coordinates import Angle, SkyCoord
import astropy.units as u
from astropy.time import Time

from .schedule import OVRO

NVSS_URL = (
    "https://heasarc.gsfc.nasa.gov/FTP/heasarc/dbase/tdat_files/heasarc_nvss.tdat.gz"
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


def read_vla_calibrator_catalog(
    path: str, cache_dir: Optional[str] = None
) -> pd.DataFrame:
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
                ra_deg = Angle(ra_str).to_value(u.deg)
                dec_deg = Angle(dec_str).to_value(u.deg)
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
                        code_a, code_b, code_c, code_d = toks[2], toks[3], toks[4], toks[5]
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
    name_col = cols.get('j2000_name') or cols.get('name') or list(df.columns)[0]
    ra_col = cols.get('ra_j2000') or cols.get('ra') or cols.get('raj2000') or cols.get('ra_hms')
    dec_col = cols.get('dec_j2000') or cols.get('dec') or cols.get('dej2000') or cols.get('dec_dms')
    ra_deg_col = next((c for c in df.columns if 'ra_deg' in c.lower()), None)
    dec_deg_col = next((c for c in df.columns if 'dec_deg' in c.lower()), None)

    def _to_deg(ra_val, dec_val) -> Tuple[float, float]:
        from astropy.coordinates import SkyCoord
        import astropy.units as u
        # try sexagesimal first
        try:
            sc = SkyCoord(str(ra_val).strip() + ' ' + str(dec_val).strip(), unit=(u.hourangle, u.deg), frame='icrs')
            return float(sc.ra.deg), float(sc.dec.deg)
        except Exception:
            try:
                sc = SkyCoord(str(ra_val).strip() + ' ' + str(dec_val).strip(), unit=(u.deg, u.deg), frame='icrs')
                return float(sc.ra.deg), float(sc.dec.deg)
            except Exception:
                return float('nan'), float('nan')

    out = []
    for _, r in df.iterrows():
        name = str(r.get(name_col, '')).strip()
        if ra_deg_col and dec_deg_col:
            ra_deg = pd.to_numeric(r[ra_deg_col], errors='coerce')
            dec_deg = pd.to_numeric(r[dec_deg_col], errors='coerce')
        elif ra_col and dec_col:
            ra_deg, dec_deg = _to_deg(r.get(ra_col, ''), r.get(dec_col, ''))
        else:
            ra_deg, dec_deg = float('nan'), float('nan')
        out.append({'name': name, 'ra_deg': ra_deg, 'dec_deg': dec_deg})
    out_df = pd.DataFrame(out).set_index('name')
    return out_df


def read_vla_parsed_catalog_with_flux(path: str, band: str = '20cm') -> pd.DataFrame:
    """Read a parsed VLA calibrator CSV and return RA/Dec in degrees and flux in Jy for a given band.

    Expected columns include J2000_NAME, RA_J2000, DEC_J2000, BAND, FLUX_JY.
    Returns a DataFrame indexed by name with columns ra_deg, dec_deg, flux_jy.
    """
    df = pd.read_csv(path)
    # Filter band if present
    if 'BAND' in df.columns:
        df = df[df['BAND'].astype(str).str.lower() == band.lower()].copy()
    # Normalize coordinates
    cols = {c.lower(): c for c in df.columns}
    name_col = cols.get('j2000_name') or cols.get('name') or list(df.columns)[0]
    ra_col = cols.get('ra_j2000') or cols.get('ra')
    dec_col = cols.get('dec_j2000') or cols.get('dec')
    # Optional spectral index columns
    sidx_col = cols.get('sidx') or cols.get('spectral_index')
    sidx_f0_col = cols.get('sidx_f0_ghz') or cols.get('nu0') or cols.get('si_freq')
    out = []
    for _, r in df.iterrows():
        name = str(r.get(name_col, '')).strip()
        ra = r.get(ra_col, '')
        dec = r.get(dec_col, '')
        try:
            sc = SkyCoord(str(ra).strip() + ' ' + str(dec).strip(), unit=(u.hourangle, u.deg), frame='icrs')
            ra_deg = float(sc.ra.deg)
            dec_deg = float(sc.dec.deg)
        except Exception:
            # Try degrees
            try:
                sc = SkyCoord(float(ra) * u.deg, float(dec) * u.deg, frame='icrs')
                ra_deg = float(sc.ra.deg)
                dec_deg = float(sc.dec.deg)
            except Exception:
                continue
        try:
            flux_jy = float(r.get('FLUX_JY', r.get('flux_jy', 'nan')))
        except Exception:
            flux_jy = float('nan')
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
        out.append({'name': name, 'ra_deg': ra_deg, 'dec_deg': dec_deg, 'flux_jy': flux_jy,
                    'sidx': sidx, 'sidx_f0_hz': sidx_f0_hz})
    odf = pd.DataFrame(out).set_index('name')
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
    ra = pd.to_numeric(cal_df['ra_deg'], errors='coerce')
    dec = pd.to_numeric(cal_df['dec_deg'], errors='coerce')
    # Small-angle approximation for speed
    cosd = max(np.cos(np.deg2rad(pointing_dec_deg)), 1e-3)
    sep = np.hypot((ra - pointing_ra_deg) * cosd, (dec - pointing_dec_deg))
    sel = cal_df.copy()
    sel['sep'] = sep
    sel = sel[sel['sep'] <= radius_deg]
    if sel.empty:
        return None
    row = sel.sort_values('sep').iloc[0]
    name = str(row.name)
    return name, float(row['ra_deg']), float(row['dec_deg']), float(row.get('flux_jy', np.nan))


def get_calibrator_radec(df: pd.DataFrame, name: str) -> Tuple[float, float]:
    """Lookup a calibrator by name (index) and return (ra_deg, dec_deg)."""
    if name in df.index:
        row = df.loc[name]
        return float(row['ra_deg']), float(row['dec_deg'])
    # Fallback: try case-insensitive and stripped
    key = name.strip().upper()
    for idx in df.index:
        if str(idx).strip().upper() == key:
            row = df.loc[idx]
            return float(row['ra_deg']), float(row['dec_deg'])
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
    # Compute meridian RA at OVRO (HA=0) and fixed pointing declination
    # Use simple LST→RA equivalence; rely on existing helper in schedule via next_transit_time logic
    # For robustness, we compute LST from astropy Time directly here
    t = Time(mid_mjd, format='mjd', scale='utc', location=OVRO)
    ra_meridian = t.sidereal_time('apparent').to_value(u.deg)
    dec_meridian = float(pt_dec.to_value(u.deg))

    # Filter by radius window (approximate RA window scaled by cos(dec))
    df = catalog_df.copy()
    if 'ra_deg' not in df.columns or 'dec_deg' not in df.columns:
        raise ValueError("catalog_df must contain 'ra_deg' and 'dec_deg' columns")
    ra = pd.to_numeric(df['ra_deg'], errors='coerce')
    dec = pd.to_numeric(df['dec_deg'], errors='coerce')
    cosd = max(np.cos(np.deg2rad(dec_meridian)), 1e-3)
    dra = radius_deg / cosd
    sel = df[(dec >= dec_meridian - radius_deg) & (dec <= dec_meridian + radius_deg) &
             (ra >= ra_meridian - dra) & (ra <= ra_meridian + dra)].copy()
    if sel.empty:
        return []

    # Compute separation and primary-beam weighted flux if flux column present
    sep = np.hypot((sel['ra_deg'] - ra_meridian) * cosd, (sel['dec_deg'] - dec_meridian))
    sel['sep_deg'] = sep
    if 'flux_20_cm' in sel.columns:
        # weighted flux ~ PB(resp)*flux (Jy)
        w = []
        for _, r in sel.iterrows():
            resp = airy_primary_beam_response(
                np.deg2rad(ra_meridian), np.deg2rad(dec_meridian),
                np.deg2rad(r['ra_deg']), np.deg2rad(r['dec_deg']),
                freq_ghz,
            )
            w.append(resp * float(r['flux_20_cm']) / 1e3)
        sel['weighted_flux'] = w
        sel = sel.sort_values(['weighted_flux', 'sep_deg'], ascending=[False, True])
    else:
        sel = sel.sort_values(['sep_deg'], ascending=[True])

    out: List[dict] = []
    for name, r in sel.head(top_n).iterrows():
        out.append({
            'name': name if isinstance(name, str) else str(name),
            'ra_deg': float(r['ra_deg']),
            'dec_deg': float(r['dec_deg']),
            'sep_deg': float(r['sep_deg']),
            'weighted_flux': float(r.get('weighted_flux', np.nan)),
        })
    return out


def airy_primary_beam_response(
    ant_ra: float, ant_dec: float, src_ra: float, src_dec: float, freq_GHz: float, dish_dia_m: float = 4.7
) -> float:
    """Approximate primary beam response using an Airy pattern.

    Returns a scalar response in [0, 1]. Coordinates in radians.
    """
    # Offset angle approximation on the sky
    dra = (src_ra - ant_ra) * np.cos(ant_dec)
    ddec = src_dec - ant_dec
    theta = np.sqrt(dra * dra + ddec * ddec)
    # First-null approximation: 1.22 * lambda / D
    lam_m = (3e8 / (freq_GHz * 1e9))
    x = np.pi * dish_dia_m * np.sin(theta) / lam_m
    # Avoid division by zero
    x = np.where(x == 0, 1e-12, x)
    resp = (2 * (np.sin(x) - x * np.cos(x)) / (x * x)) ** 2
    # Clamp numeric noise
    return float(np.clip(resp, 0.0, 1.0))


def generate_caltable(
    vla_df: pd.DataFrame,
    pt_dec: u.Quantity,
    csv_path: str,
    radius: u.Quantity = 2.5 * u.deg,
    min_weighted_flux: u.Quantity = 1.0 * u.Jy,
    min_percent_flux: float = 0.15,
) -> str:
    """Build a declination-specific calibrator table and save to CSV.

    Weighted by primary beam response at 1.4 GHz.
    """
    pt_dec_deg = pt_dec.to_value(u.deg)
    # ensure numeric
    vla_df = vla_df.copy()
    vla_df["ra"] = pd.to_numeric(vla_df["ra"], errors="coerce")
    vla_df["dec"] = pd.to_numeric(vla_df["dec"], errors="coerce")
    vla_df["flux_20_cm"] = pd.to_numeric(vla_df["flux_20_cm"], errors="coerce")

    cal_df = vla_df[
        (vla_df["dec"] < (pt_dec_deg + radius.to_value(u.deg)))
        & (vla_df["dec"] > (pt_dec_deg - radius.to_value(u.deg)))
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
            (vla_df["dec"] < (pt_dec_deg + radius.to_value(u.deg)))
            & (vla_df["dec"] > (pt_dec_deg - radius.to_value(u.deg)))
            & (vla_df["ra"] < row["ra"] + radius.to_value(u.deg) / max(np.cos(np.deg2rad(pt_dec_deg)), 1e-3))
            & (vla_df["ra"] > row["ra"] - radius.to_value(u.deg) / max(np.cos(np.deg2rad(pt_dec_deg)), 1e-3))
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
        (cal_df["weighted_flux"] > min_weighted_flux.to_value(u.Jy))
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
    out = out[["ra(deg)", "dec(deg)", "flux (Jy)", "weighted_flux", "percent_flux", "code_20_cm"]]
    out.to_csv(csv_path, index=True)
    return csv_path


def update_caltable(
    vla_df: pd.DataFrame, pt_dec: u.Quantity, out_dir: str = ".cache/catalogs"
) -> str:
    """Ensure a declination-specific caltable exists; return its path."""
    os.makedirs(out_dir, exist_ok=True)
    decsign = "+" if pt_dec.to_value(u.deg) >= 0 else "-"
    decval = f"{abs(pt_dec.to_value(u.deg)):05.1f}".replace(".", "p")
    csv_path = str(Path(out_dir) / f"calibrator_sources_dec{decsign}{decval}.csv")
    if not os.path.exists(csv_path):
        generate_caltable(vla_df=vla_df, pt_dec=pt_dec, csv_path=csv_path)
    return csv_path
