from typing import Dict, List

from dsa110_contimg.calibration.calibration import solve_delay, solve_bandpass, solve_gains


def run(ctx: Dict) -> Dict:
    """Run K/B/G solves on the chosen calibrator MS.

    Expected ctx keys:
      - calib.ms_cal: str (path to calibrator MS)
      - cal_field: str (calibrator field name/id)
      - refant: str
    Writes ctx['calib']['tables'] in application order
    """
    ms_cal = ctx['calib']['ms_cal']
    cal_field = ctx['cal_field']
    refant = ctx['refant']
    ktabs = solve_delay(ms_cal, cal_field, refant)
    bptabs = solve_bandpass(ms_cal, cal_field, refant, ktabs[0])
    gtabs = solve_gains(ms_cal, cal_field, refant, ktabs[0], bptabs, do_fluxscale=False)
    ctx['calib']['tables'] = ktabs[:1] + bptabs + gtabs
    return ctx


