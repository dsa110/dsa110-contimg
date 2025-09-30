import os
import csv
from dataclasses import dataclass
from typing import List, Optional

from astropy.coordinates import SkyCoord
from astropy import units as u


CACHE_DIR = 'data/catalog_cache'
NVSS_CSV = os.path.join(CACHE_DIR, 'nvss.csv')
VLASS_CSV = os.path.join(CACHE_DIR, 'vlass.csv')
SEED_CSV = os.path.join(CACHE_DIR, 'seed.csv')


@dataclass
class CachedSource:
    name: str
    ra_deg: float
    dec_deg: float
    flux_jy_ref: Optional[float]
    ref_freq_hz: Optional[float]
    spectral_index: Optional[float]
    catalog: str


class CalibratorCache:
    def __init__(self, cache_dir: str = CACHE_DIR) -> None:
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def write_csv(self, path: str, rows: List[CachedSource]) -> None:
        with open(path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['name','ra_deg','dec_deg','flux_jy_ref','ref_freq_hz','spectral_index','catalog'])
            for r in rows:
                w.writerow([r.name, r.ra_deg, r.dec_deg, r.flux_jy_ref or '', r.ref_freq_hz or '', r.spectral_index or '', r.catalog])

    def read_csv(self, path: str) -> List[CachedSource]:
        if not os.path.exists(path):
            return []
        out: List[CachedSource] = []
        with open(path, 'r', newline='') as f:
            for i, row in enumerate(csv.DictReader(f)):
                try:
                    out.append(CachedSource(
                        name=row['name'],
                        ra_deg=float(row['ra_deg']),
                        dec_deg=float(row['dec_deg']),
                        flux_jy_ref=float(row['flux_jy_ref']) if row['flux_jy_ref'] else None,
                        ref_freq_hz=float(row['ref_freq_hz']) if row['ref_freq_hz'] else None,
                        spectral_index=float(row['spectral_index']) if row['spectral_index'] else None,
                        catalog=row.get('catalog',''),
                    ))
                except Exception:
                    continue
        return out

    def cone_search(self, ra_deg: float, dec_deg: float, radius_deg: float, min_flux_jy: float = 0.0) -> List[CachedSource]:
        """
        Search seed, NVSS and VLASS CSVs for sources in a cone and flux cut.
        """
        center = SkyCoord(ra=ra_deg*u.deg, dec=dec_deg*u.deg, frame='icrs')
        rows: List[CachedSource] = []
        for path in (SEED_CSV, NVSS_CSV, VLASS_CSV):
            for src in self.read_csv(path):
                try:
                    if src.flux_jy_ref is not None and src.flux_jy_ref < min_flux_jy:
                        continue
                    sc = SkyCoord(ra=src.ra_deg*u.deg, dec=src.dec_deg*u.deg)
                    if sc.separation(center).deg <= radius_deg:
                        rows.append(src)
                except Exception:
                    continue
        # De-dupe by name+catalog
        seen = set()
        uniq: List[CachedSource] = []
        for s in rows:
            key = (s.catalog, s.name)
            if key in seen:
                continue
            seen.add(key)
            uniq.append(s)
        return uniq
