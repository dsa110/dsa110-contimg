import math
from dataclasses import dataclass
from typing import List, Optional, Iterable

from astropy.coordinates import SkyCoord
from astropy import units as u
from astroquery.vizier import Vizier

from .calibrator_cache import CalibratorCache


# VizieR catalogs
# NVSS (1.4 GHz): VIII/65/nvss
# FIRST (1.4 GHz): VIII/92/first14
# TGSS ADR1 (150 MHz): J/A+A/598/A78
# VLASS Quick Look (3 GHz): J/ApJS/264/31 (VLASS1QLCIR)
DEFAULT_VIZIER_CATALOG = "VIII/65/nvss"
CATALOG_IDS = {
    'nvss': "VIII/65/nvss",
    'first': "VIII/92/first14",
    'tgss': "J/A+A/598/A78",
    'vlass': "J/ApJS/264/31",
}


@dataclass
class CalibratorCandidate:
    name: str
    ra_deg: float
    dec_deg: float
    flux_jy_ref: Optional[float]
    ref_freq_hz: Optional[float]
    spectral_index: Optional[float]
    separation_deg: float
    provenance: str


class CalibratorFinder:
    def __init__(self, catalog: Optional[str] = DEFAULT_VIZIER_CATALOG, use_cache: bool = True, allow_online_fallback: bool = True,
                 catalogs: Optional[Iterable[str]] = None) -> None:
        # If multiple catalogs are provided, use them; otherwise fall back to single catalog
        self.catalog = catalog
        self.catalogs = [c.lower() for c in catalogs] if catalogs else None
        self.use_cache = use_cache
        self.allow_online_fallback = allow_online_fallback
        Vizier.ROW_LIMIT = -1
        self._cache = CalibratorCache()

    def _from_cache(self, ra_deg: float, dec_deg: float, radius_deg: float, min_flux_jy: float) -> List[CalibratorCandidate]:
        cands: List[CalibratorCandidate] = []
        for src in self._cache.cone_search(ra_deg, dec_deg, radius_deg, min_flux_jy=min_flux_jy):
            center = SkyCoord(ra=ra_deg*u.deg, dec=dec_deg*u.deg)
            sc = SkyCoord(ra=src.ra_deg*u.deg, dec=src.dec_deg*u.deg)
            sep = sc.separation(center).deg
            cands.append(CalibratorCandidate(
                name=src.name,
                ra_deg=src.ra_deg,
                dec_deg=src.dec_deg,
                flux_jy_ref=src.flux_jy_ref,
                ref_freq_hz=src.ref_freq_hz,
                spectral_index=src.spectral_index,
                separation_deg=sep,
                provenance=f"cache:{src.catalog}"
            ))
        return cands

    def _estimate_flux_at_1p4(self, flux_jy: float, freq_hz: float, alpha: float = -0.7) -> float:
        # S ~ nu^alpha, convert to 1.4 GHz
        if flux_jy is None or freq_hz is None:
            return flux_jy
        return float(flux_jy * (1.4e9 / freq_hz) ** alpha)

    def _query_vizier_catalog(self, cat_id: str, center: SkyCoord, radius_deg: float, min_flux_jy: float) -> List[CalibratorCandidate]:
        viz = Vizier(columns=['*'])
        try:
            res = viz.query_region(center, radius=radius_deg * u.deg, catalog=cat_id)
        except Exception:
            return []
        if not res:
            return []
        table = res[0]
        cols = set(table.colnames)
        cands: List[CalibratorCandidate] = []
        for row in table:
            try:
                # Robust RA/Dec parsing: handle numeric degrees or sexagesimal strings
                if ('RAJ2000' not in cols) or ('DEJ2000' not in cols):
                    continue
                ra_val = row['RAJ2000']
                dec_val = row['DEJ2000']
                ra: float
                dec: float
                try:
                    ra = float(ra_val)
                    dec = float(dec_val)
                    sc = SkyCoord(ra=ra * u.deg, dec=dec * u.deg)
                except Exception:
                    sc = SkyCoord(ra=str(ra_val), dec=str(dec_val), unit=(u.hourangle, u.deg), frame='icrs')
                    ra = float(sc.ra.deg)
                    dec = float(sc.dec.deg)
                sep = sc.separation(center).deg
                name = None
                flux_jy = None
                ref_freq = None
                prov = None
                # NVSS
                if cat_id == CATALOG_IDS['nvss']:
                    name = str(row['NVSS']) if 'NVSS' in cols else 'NVSS'
                    if 'S1.4' in cols and row['S1.4'] is not None:
                        flux_jy = float(row['S1.4']) / 1000.0
                        ref_freq = 1.4e9
                    prov = 'online:NVSS'
                # FIRST
                elif cat_id == CATALOG_IDS['first']:
                    name = str(row['Name']) if 'Name' in cols else 'FIRST'
                    # FIRST integrated flux (mJy) column often 'Fint'
                    if 'Fint' in cols and row['Fint'] is not None:
                        flux_jy = float(row['Fint']) / 1000.0
                        ref_freq = 1.4e9
                    prov = 'online:FIRST'
                # TGSS ADR1 (150 MHz)
                elif cat_id == CATALOG_IDS['tgss']:
                    name = str(row['TGSSADR1']) if 'TGSSADR1' in cols else 'TGSS'
                    if 'S150' in cols and row['S150'] is not None:
                        flux_jy = float(row['S150']) / 1000.0
                        ref_freq = 150e6
                    prov = 'online:TGSS'
                # VLASS QL (3 GHz)
                elif cat_id == CATALOG_IDS['vlass']:
                    name = str(row['VLASS1QLCIR']) if 'VLASS1QLCIR' in cols else 'VLASS'
                    # Try total flux columns (mJy): 'Stotal' or 'Fint'
                    if 'Stotal' in cols and row['Stotal'] is not None:
                        flux_jy = float(row['Stotal']) / 1000.0
                        ref_freq = 3.0e9
                    elif 'Fint' in cols and row['Fint'] is not None:
                        flux_jy = float(row['Fint']) / 1000.0
                        ref_freq = 3.0e9
                    prov = 'online:VLASS'
                if flux_jy is None:
                    continue
                # Convert to 1.4 GHz reference for ranking if needed
                flux_1p4 = flux_jy if (ref_freq == 1.4e9) else self._estimate_flux_at_1p4(flux_jy, ref_freq)
                if flux_1p4 < min_flux_jy:
                    continue
                cands.append(CalibratorCandidate(
                    name=name,
                    ra_deg=ra,
                    dec_deg=dec,
                    flux_jy_ref=flux_1p4,
                    ref_freq_hz=1.4e9,
                    spectral_index=(-0.7 if (ref_freq and ref_freq != 1.4e9) else None),
                    separation_deg=sep,
                    provenance=prov
                ))
            except Exception:
                continue
        return cands

    def _from_online(self, ra_deg: float, dec_deg: float, radius_deg: float, min_flux_jy: float) -> List[CalibratorCandidate]:
        center = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame='icrs')
        catalogs = self.catalogs if self.catalogs else [self.catalog or DEFAULT_VIZIER_CATALOG]
        vizier_ids = []
        for c in catalogs:
            if c in CATALOG_IDS:
                vizier_ids.append(CATALOG_IDS[c])
            else:
                vizier_ids.append(c)  # assume raw VizieR id
        merged: List[CalibratorCandidate] = []
        for cid in vizier_ids:
            merged.extend(self._query_vizier_catalog(cid, center, radius_deg, min_flux_jy))
        return merged

    def find_nearby(self,
                    ra_deg: float,
                    dec_deg: float,
                    radius_deg: float = 3.0,
                    min_flux_jy: float = 0.2) -> List[CalibratorCandidate]:
        cands: List[CalibratorCandidate] = []
        if self.use_cache:
            cands.extend(self._from_cache(ra_deg, dec_deg, radius_deg, min_flux_jy))
        if self.allow_online_fallback:
            cands.extend(self._from_online(ra_deg, dec_deg, radius_deg, min_flux_jy))
        cands.sort(key=lambda c: (- (c.flux_jy_ref or 0.0), c.separation_deg))
        return cands
