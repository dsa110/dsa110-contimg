from typing import Dict

import astropy.units as u
from dsa110_contimg.calibration.catalogs import read_vla_calibrator_catalog, update_caltable


def run(ctx: Dict) -> Dict:
    """Build declination-specific calibrator CSV and store its path in context.

    Expected ctx keys:
      - vla_catalog_path: str (path to VLA calibrator text file)
      - pt_dec_deg: float (pointing declination in degrees)
    Writes ctx['calib']['caltable_csv']
    """
    vla_df = read_vla_calibrator_catalog(ctx['vla_catalog_path'])
    pt_dec = float(ctx['pt_dec_deg']) * u.deg
    ctx.setdefault('calib', {})
    ctx['calib']['caltable_csv'] = update_caltable(vla_df, pt_dec)
    return ctx


