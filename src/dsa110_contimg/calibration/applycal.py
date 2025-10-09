from typing import List, Optional

from casatasks import applycal as casa_applycal


def apply_to_target(
    ms_target: str,
    field: str,
    gaintables: List[str],
    interp: Optional[List[str]] = None,
    calwt: bool = True,
    spwmap: Optional[List[int]] = None,
) -> None:
    """Apply calibration tables to a target MS field.

    interp defaults will be set to 'linear' matching list length.
    """
    if interp is None:
        interp = ["linear"] * len(gaintables)
    casa_applycal(
        vis=ms_target,
        field=field,
        gaintable=gaintables,
        interp=interp,
        calwt=calwt,
        spwmap=spwmap,
    )


