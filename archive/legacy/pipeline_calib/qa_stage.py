from typing import Dict

from dsa110_contimg.calibration.qa import save_plotms_cal_figure


def run(ctx: Dict) -> Dict:
    """Generate plotcal-based QA figures for K/B/G tables.

    Expected ctx keys:
      - calib.ms_cal: str
      - cal_field: str
      - qa_outdir: str
    Writes ctx['qa']['figures'] list
    """
    prefix = ctx['calib']['ms_cal'].rstrip('.ms') + "_{}".format(ctx['cal_field'])
    outdir = ctx['qa_outdir']
    figs = []
    for caltable, xaxis, yaxis, name in [
        ("{}_kcal".format(prefix), 'time', 'delay', 'kcal_delay.png'),
        ("{}_bacal".format(prefix), 'chan', 'amp', 'bacal_amp.png'),
        ("{}_bpcal".format(prefix), 'chan', 'phase', 'bpcal_phase.png'),
        ("{}_gacal".format(prefix), 'time', 'amp', 'gacal_amp.png'),
        ("{}_gpcal".format(prefix), 'time', 'phase', 'gpcal_phase.png'),
    ]:
        save_plotms_cal_figure(caltable, xaxis, yaxis, "{}/{}".format(outdir, name))
        figs.append("{}/{}".format(outdir, name))
    ctx.setdefault('qa', {})
    ctx['qa']['figures'] = figs
    return ctx


