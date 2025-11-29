"""
Multi-wavelength catalog search tools.

Repurposed from vast-mw (https://github.com/askap-vast/vast-mw) by David Kaplan.
Provides unified access to various astronomical catalogs (Gaia, Simbad, NVSS, etc.)
for source cross-matching and classification.
"""

import logging
import sys
import urllib.parse
import warnings
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import numpy as np
from astropy import units as u
from astropy.coordinates import EarthLocation, SkyCoord, get_body, solar_system_ephemeris
from astropy.table import Column, Table
from astropy.time import Time

logger = logging.getLogger(__name__)

# Lazy imports for network-dependent modules
# These are imported on first use to avoid network calls at module load time
_astroquery_loaded = False
Casda = None
Gaia = None
Simbad = None
Vizier = None
psrqpy = None
vo = None
requests = None


def _ensure_astroquery():
    """Lazily load astroquery and related modules."""
    global _astroquery_loaded, Casda, Gaia, Simbad, Vizier, psrqpy, vo, requests
    if _astroquery_loaded:
        return
    
    import requests as _requests
    import psrqpy as _psrqpy
    import pyvo as _vo
    from astroquery.casda import Casda as _Casda
    from astroquery.gaia import Gaia as _Gaia
    from astroquery.simbad import Simbad as _Simbad
    from astroquery.vizier import Vizier as _Vizier
    
    requests = _requests
    psrqpy = _psrqpy
    vo = _vo
    Casda = _Casda
    Gaia = _Gaia
    Simbad = _Simbad
    Vizier = _Vizier
    
    # Configure Gaia
    Gaia.MAIN_GAIA_TABLE = GAIA_MAIN_TABLE
    
    # Configure Simbad (done below after constant definitions)
    _astroquery_loaded = True


# Constants
GAIA_MAIN_TABLE = "gaiadr3.gaia_source"
PULSAR_SCRAPER_URL = "https://pulsar.cgca-hub.org/api"
SIMBAD_URL = "https://simbad.u-strasbg.fr/simbad/sim-id"
GAIA_URL = "https://gaia.ari.uni-heidelberg.de/singlesource.html"
VIZIER_URL = "https://vizier.cds.unistra.fr/viz-bin/VizieR-5"

# Lazy-initialized Simbad client (initialized on first use)
_cSimbad = None


def _get_simbad_client():
    """Get or create the configured Simbad client."""
    global _cSimbad
    if _cSimbad is None:
        _ensure_astroquery()
        _cSimbad = Simbad()
        _cSimbad.add_votable_fields("pmra", "pmdec")
    return _cSimbad


def format_radec(coord: SkyCoord) -> str:
    """Return coordinates as 'HHhMMmSS.SSs DDdMMmSS.Ss'"""
    sra = coord.icrs.ra.to_string(u.hour, decimal=False, sep="hms", precision=2)
    sdec = coord.icrs.dec.to_string(
        u.degree, decimal=False, sep="dms", precision=1, pad=True, alwayssign=True
    )
    return f"{sra}, {sdec}"


def check_gaia(
    source: SkyCoord, t: Time = None, radius: u.Quantity = 15 * u.arcsec
) -> Dict[str, u.Quantity]:
    """Check a source against Gaia, correcting for proper motion."""
    _ensure_astroquery()
    if t is None:
        if source.obstime is None:
            logger.error(
                "Must supply either SkyCoord with obstime or separate time for coordinate check"
            )
            return {}
        t = source.obstime

    try:
        q = Gaia.cone_search(coordinate=source, radius=radius)
        r = q.get_results()
    except Exception as e:
        logger.warning(f"Gaia query failed: {e}")
        return {}

    separations = {}
    if len(r) > 0:
        designation = "DESIGNATION" if "DESIGNATION" in r.colnames else "designation"
    else:
        return {}

    for i in range(len(r)):
        try:
            gaia_source = SkyCoord(
                r[i]["ra"] * u.deg,
                r[i]["dec"] * u.deg,
                pm_ra_cosdec=r[i]["pmra"] * u.mas / u.yr,
                pm_dec=r[i]["pmdec"] * u.mas / u.yr,
                distance=(
                    (r[i]["parallax"] * u.mas).to(u.kpc, equivalencies=u.parallax())
                    if r[i]["parallax"] > 0
                    else 1 * u.kpc
                ),
                obstime=Time(r[0]["ref_epoch"], format="decimalyear"),
            )
            sep = gaia_source.apply_space_motion(t).separation(source).arcsec * u.arcsec
            separations[r[i][designation]] = sep
        except Exception as e:
            logger.warning(f"Error processing Gaia source {i}: {e}")
            continue

    return separations


def check_pulsarscraper(
    source: SkyCoord, radius: u.Quantity = 15 * u.arcsec
) -> Dict[str, u.Quantity]:
    """Check a source against the Pulsar survey scraper."""
    _ensure_astroquery()  # For requests
    try:
        response = requests.get(
            PULSAR_SCRAPER_URL,
            params={
                "type": "search",
                "ra": source.ra.deg,
                "dec": source.dec.deg,
                "radius": radius.to_value(u.deg),
            },
            timeout=10,
        )
        if not response.ok:
            logger.error(
                f"Unable to query pulsarsurveyscraper: received code={response.status_code} ({response.reason})"
            )
            return {}

        out = {}
        data = response.json()
        for k in data:
            if k.startswith("search") or k.startswith("nmatches"):
                continue
            # The key structure might vary, handle carefully
            try:
                survey = data[k].get("survey", {}).get("value", "unknown")
                dist_val = data[k].get("distance", {}).get("value", 0)
                out[f"{k}[{survey}]"] = (dist_val * u.deg).to(u.arcsec)
            except (KeyError, TypeError):
                continue
        return out
    except Exception as e:
        logger.warning(f"Pulsar scraper query failed: {e}")
        return {}


def check_simbad(
    source: SkyCoord, t: Time = None, radius: u.Quantity = 15 * u.arcsec
) -> Dict[str, u.Quantity]:
    """Check a source against Simbad, correcting for proper motion."""
    _ensure_astroquery()
    if t is None:
        if source.obstime is None:
            logger.error(
                "Must supply either SkyCoord with obstime or separate time for coordinate check"
            )
            return {}
        t = source.obstime

    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            r = _get_simbad_client().query_region(source, radius=radius)
    except Exception as e:
        logger.warning(f"Simbad query failed: {e}")
        return {}

    if r is None:
        return {}

    ra_col, dec_col, pmra_col, pmdec_col = "RA", "DEC", "PMRA", "PMDEC"
    if "RA" not in r.colnames:
        ra_col, dec_col, pmra_col, pmdec_col = "ra", "dec", "pmra", "pmdec"

    separations = {}
    for i in range(len(r)):
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                simbad_source = SkyCoord(
                    r[i][ra_col],
                    r[i][dec_col],
                    unit=("hour", "deg"),
                    pm_ra_cosdec=r[i][pmra_col] * u.mas / u.yr,
                    pm_dec=r[i][pmdec_col] * u.mas / u.yr,
                    obstime=Time(2000, format="decimalyear"),
                )
                sep = simbad_source.apply_space_motion(t).separation(source).arcsec * u.arcsec
                separations[r[i]["MAIN_ID"]] = sep
        except Exception:
            # If proper motion is missing or other error, just calculate static separation
            try:
                simbad_source = SkyCoord(r[i][ra_col], r[i][dec_col], unit=("hour", "deg"))
                sep = simbad_source.separation(source).arcsec * u.arcsec
                separations[r[i]["MAIN_ID"]] = sep
            except Exception as e:
                logger.warning(f"Error processing Simbad source {i}: {e}")
                continue

    return separations


def check_atnf(
    source: SkyCoord, t: Time = None, radius: u.Quantity = 15 * u.arcsec
) -> Dict[str, u.Quantity]:
    """Check a source against ATNF pulsar catalog."""
    _ensure_astroquery()  # For psrqpy
    if t is None:
        if source.obstime is None:
            logger.error(
                "Must supply either SkyCoord with obstime or separate time for coordinate check"
            )
            return {}
        t = source.obstime

    try:
        r = psrqpy.QueryATNF(
            params=["JNAME", "RAJD", "DECJD", "POSEPOCH", "PMRA", "PMDEC"],
            circular_boundary=[
                source.ra.to_string(u.hour, decimal=False, sep="hms", precision=2),
                source.dec.to_string(
                    u.degree,
                    decimal=False,
                    sep="dms",
                    precision=1,
                    pad=True,
                    alwayssign=True,
                ),
                radius.to_value(u.deg),
            ],
        )
    except Exception as e:
        logger.warning(f"ATNF query failed: {e}")
        return {}

    if r is None or len(r) == 0:
        return {}

    separations = {}
    for i in range(len(r)):
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                atnf_source = SkyCoord(
                    r.table[i]["RAJD"] * u.deg,
                    r.table[i]["DECJD"] * u.deg,
                    pm_ra_cosdec=r.table[i]["PMRA"] * u.mas / u.yr,
                    pm_dec=r.table[i]["PMDEC"] * u.mas / u.yr,
                    obstime=Time(r.table[i]["POSEPOCH"], format="mjd"),
                )
                sep = atnf_source.apply_space_motion(t).separation(source).arcsec * u.arcsec
                separations[r.table[i]["JNAME"]] = sep
        except Exception:
            # Fallback if PM missing
            try:
                atnf_source = SkyCoord(r.table[i]["RAJD"] * u.deg, r.table[i]["DECJD"] * u.deg)
                sep = atnf_source.separation(source).arcsec * u.arcsec
                separations[r.table[i]["JNAME"]] = sep
            except Exception as e:
                logger.warning(f"Error processing ATNF source {i}: {e}")
                continue

    return separations


def check_planets(
    source: SkyCoord,
    t: Time = None,
    radius: u.Quantity = 1 * u.arcmin,
    obs: str = "OVRO",  # Default changed to OVRO/DSA-110 location roughly
) -> Dict[str, u.Quantity]:
    """Check a source against solar system planets."""
    if t is None:
        if source.obstime is None:
            logger.error(
                "Must supply either SkyCoord with obstime or separate time for coordinate check"
            )
            return {}
        t = source.obstime

    try:
        # OVRO location approx: 118.283 W, 37.234 N
        loc = EarthLocation.from_geodetic(
            lat=37.234 * u.deg, lon=-118.283 * u.deg, height=1222 * u.m
        )
    except Exception:
        loc = None  # Fallback

    separations = {}
    try:
        with solar_system_ephemeris.set("builtin"):
            for planet_name in solar_system_ephemeris.bodies:
                if planet_name == "earth":
                    continue
                planet = get_body(planet_name, t, loc)
                if planet.separation(source) < radius:
                    separations[planet_name] = planet.separation(source).to(u.arcsec)
    except Exception as e:
        logger.warning(f"Planet check failed: {e}")

    return separations


def _check_vizier(
    source: SkyCoord,
    catalog: str,
    name_col: str,
    radius: u.Quantity = 15 * u.arcsec,
    catalog_list: List[str] = None,
) -> Dict[str, u.Quantity]:
    """Generic Vizier check helper."""
    _ensure_astroquery()
    try:
        cat_query = catalog_list if catalog_list else catalog
        result = Vizier().query_region(source, radius=radius, catalog=cat_query)
        out = {}
        if not result:
            return out

        for r in result:
            if name_col not in r.colnames:
                continue
            names = r[name_col]
            matchpos = SkyCoord(r["RAJ2000"], r["DEJ2000"], unit=("deg", "deg"))
            # Handle unit variations if needed, but usually Vizier returns deg

            for i in range(len(r)):
                sep = matchpos[i].separation(source).to(u.arcsec)
                out[str(names[i])] = sep
        return out
    except Exception as e:
        logger.warning(f"Vizier query for {catalog} failed: {e}")
        return {}


def check_tgss(source: SkyCoord, radius: u.Quantity = 15 * u.arcsec) -> Dict[str, u.Quantity]:
    return _check_vizier(source, "J/A+A/598/A78", "TGSSADR", radius)


def check_first(source: SkyCoord, radius: u.Quantity = 15 * u.arcsec) -> Dict[str, u.Quantity]:
    return _check_vizier(source, "VIII/92/first14", "FIRST", radius)


def check_nvss(source: SkyCoord, radius: u.Quantity = 15 * u.arcsec) -> Dict[str, u.Quantity]:
    """Check NVSS using local database if available, else Vizier."""
    # Try local database first
    try:
        from dsa110_contimg.calibration.catalogs import query_catalog_sources

        # query_catalog_sources expects degrees
        df = query_catalog_sources("nvss", source.ra.deg, source.dec.deg, radius.to(u.deg).value)

        if not df.empty:
            out = {}
            for _, row in df.iterrows():
                sc = SkyCoord(row["ra_deg"], row["dec_deg"], unit="deg")
                name = f"NVSS J{format_radec(sc)}"
                sep = sc.separation(source).to(u.arcsec)
                out[name] = sep
            return out

    except (ImportError, Exception) as e:
        logger.debug(f"Local NVSS query failed ({e}), falling back to Vizier")

    return _check_vizier(source, "VIII/65/nvss", "NVSS", radius)


def check_milliquas(source: SkyCoord, radius: u.Quantity = 15 * u.arcsec) -> Dict[str, u.Quantity]:
    return _check_vizier(source, "VII/294/catalog", "Name", radius)


def check_wiseagn(source: SkyCoord, radius: u.Quantity = 15 * u.arcsec) -> Dict[str, u.Quantity]:
    return _check_vizier(source, None, "WISEA", radius, catalog_list=["J/ApJS/234/23/c75cat"])


def check_lqac(source: SkyCoord, radius: u.Quantity = 15 * u.arcsec) -> Dict[str, u.Quantity]:
    return _check_vizier(source, None, "LQAC", radius, catalog_list=["J/A+A/624/A145/lqac5"])


def check_sdssqso(source: SkyCoord, radius: u.Quantity = 15 * u.arcsec) -> Dict[str, u.Quantity]:
    return _check_vizier(source, None, "SDSS", radius, catalog_list=["VII/289/dr16q"])


def check_vlass(source: SkyCoord, radius: u.Quantity = 15 * u.arcsec) -> Dict[str, u.Quantity]:
    """Check VLASS using local database if available, else Vizier."""
    # Try local database first
    try:
        from dsa110_contimg.calibration.catalogs import query_catalog_sources

        df = query_catalog_sources("vlass", source.ra.deg, source.dec.deg, radius.to(u.deg).value)

        if not df.empty:
            out = {}
            for _, row in df.iterrows():
                sc = SkyCoord(row["ra_deg"], row["dec_deg"], unit="deg")
                name = f"VLASS J{format_radec(sc)}"
                sep = sc.separation(source).to(u.arcsec)
                out[name] = sep
            return out

    except (ImportError, Exception) as e:
        logger.debug(f"Local VLASS query failed ({e}), falling back to Vizier")

    return _check_vizier(source, "J/ApJS/255/30/comp", "CompName", radius)


def check_all_services(
    source: SkyCoord, t: Time = None, radius: u.Quantity = 15 * u.arcsec
) -> Dict[str, Dict[str, u.Quantity]]:
    """
    Check source against all configured services.
    """
    services = {
        "Gaia": check_gaia,
        "Simbad": check_simbad,
        "Pulsar Scraper": check_pulsarscraper,
        "ATNF": check_atnf,
        "Planets": check_planets,
        "TGSS": check_tgss,
        "FIRST": check_first,
        "NVSS": check_nvss,
        "Milliquas": check_milliquas,
        "WISE AGN": check_wiseagn,
        "LQAC": check_lqac,
        "SDSS QSO": check_sdssqso,
        "VLASS": check_vlass,
    }

    results = {}
    for name, func in services.items():
        try:
            # Some functions require time 't', others don't or handle it optionally
            # Simbad, Gaia, Planets, ATNF need 't' if source.obstime is missing
            if func in [check_gaia, check_simbad, check_atnf, check_planets]:
                res = func(source, t=t, radius=radius)
            else:
                res = func(source, radius=radius)

            if res:
                results[name] = res
        except Exception as e:
            logger.warning(f"Service {name} failed: {e}")

    return results
