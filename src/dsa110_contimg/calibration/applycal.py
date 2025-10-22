from typing import List, Optional, Union

from casatasks import applycal as casa_applycal


def apply_to_target(
    ms_target: str,
    field: str,
    gaintables: List[str],
    interp: Optional[List[str]] = None,
    calwt: bool = True,
    # CASA accepts a single list (applied to all tables) or a list-of-lists
    # (one mapping per gaintable). Use Union typing to document both shapes.
    spwmap: Optional[Union[List[int], List[List[int]]]] = None,
) -> None:
    """Apply calibration tables to a target MS field.

    interp defaults will be set to 'linear' matching list length.
    """
    if interp is None:
        # Prefer 'nearest' for bandpass-like tables, 'linear' for gains.
        # Heuristic by table name; callers can override explicitly.
        _defaults: List[str] = []
        for gt in gaintables:
            low = gt.lower()
            if "bpcal" in low or "bandpass" in low:
                _defaults.append("nearest")
            else:
                _defaults.append("linear")
        interp = _defaults
    kwargs = dict(
        vis=ms_target,
        field=field,
        gaintable=gaintables,
        interp=interp,
        calwt=calwt,
    )
    # Only pass spwmap if explicitly provided; CASA rejects explicit null
    if spwmap is not None:
        kwargs["spwmap"] = spwmap
    casa_applycal(**kwargs)
