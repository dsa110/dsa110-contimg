from typing import Dict

from astropy.time import Time
from dsa110_contimg.calibration.schedule import next_transit_time, pick_best_observation


def run(ctx: Dict) -> Dict:
    """Compute transit time and select best observation near transit.

    Expected ctx keys:
      - cal_ra_deg: float (RA of selected calibrator in degrees)
      - date: str (YYYY-MM-DD)
      - observations: list of (obs_id, start_mjd, end_mjd)
    Writes ctx['calib']['transit_time_mjd'] and ctx['calib']['best_obs']
    """
    start_mjd = Time(ctx['date'] + 'T00:00:00', scale='utc').mjd
    ttran = next_transit_time(ctx['cal_ra_deg'], start_mjd)
    ctx.setdefault('calib', {})
    ctx['calib']['transit_time_mjd'] = float(ttran.mjd)
    ctx['calib']['best_obs'] = pick_best_observation(ctx['observations'], ttran)
    return ctx


