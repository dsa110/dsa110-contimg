from typing import Dict

from dsa110_contimg.calibration.applycal import apply_to_target
from dsa110_contimg.calibration.imaging import quick_image


def run(ctx: Dict) -> Dict:
    """Apply calibration to target MS and optionally image.

    Expected ctx keys:
      - ms_target: str
      - target_fields: list[str]
      - calib.tables: list[str] (ordered)
      - outdir: str (for images)
      - make_image: bool (optional)
    """
    make_image = ctx.get('make_image', True)
    for t in ctx['target_fields']:
        apply_to_target(ctx['ms_target'], field=t, gaintables=ctx['calib']['tables'])
        if make_image:
            quick_image(ctx['ms_target'], imagename=f"{ctx['outdir']}/{t}", field=t)
    return ctx


