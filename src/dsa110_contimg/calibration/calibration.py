from typing import List, Optional

import numpy as np
from casatasks import bandpass as casa_bandpass
from casatasks import gaincal as casa_gaincal
from casatasks import setjy as casa_setjy
from casatasks import fluxscale as casa_fluxscale


def solve_delay(
    ms: str,
    cal_field: str,
    refant: str,
    table_prefix: Optional[str] = None,
    combine_spw: bool = False,
    t_slow: str = "inf",
    t_fast: Optional[str] = "60s",
) -> List[str]:
    """Solve delay (K) on slow and optional fast timescales using CASA gaincal.

    Uses casatasks.gaincal with gaintype='K' to avoid explicit casatools calibrater
    usage, which can be unstable in some Jupyter environments.
    """
    # Do not combine across fields during delay solving; it can destabilize
    # metadata handling when multiple FIELD phase centers are present.
    combine = "scan,obs,spw" if combine_spw else "scan,obs"
    if table_prefix is None:
        table_prefix = f"{ms.rstrip('.ms')}_{cal_field}"

    tables: List[str] = []

    # Slow (infinite) delay solve
    casa_gaincal(
        vis=ms,
        caltable=f"{table_prefix}_kcal",
        field=cal_field,
        solint=t_slow,
        refant=refant,
        gaintype="K",
        combine=combine,
    )
    tables.append(f"{table_prefix}_kcal")

    # Optional fast (short) delay solve
    if t_fast:
        casa_gaincal(
            vis=ms,
            caltable=f"{table_prefix}_2kcal",
            field=cal_field,
            solint=t_fast,
            refant=refant,
            gaintype="K",
            combine=combine,
        )
        tables.append(f"{table_prefix}_2kcal")

    return tables


def solve_bandpass(
    ms: str,
    cal_field: str,
    refant: str,
    ktable: str,
    table_prefix: Optional[str] = None,
    set_model: bool = True,
    model_standard: str = "Perley-Butler 2017",
) -> List[str]:
    """Solve bandpass in two stages: amplitude (bacal) then phase (bpcal)."""
    if table_prefix is None:
        table_prefix = f"{ms.rstrip('.ms')}_{cal_field}"

    if set_model:
        casa_setjy(vis=ms, field=cal_field, standard=model_standard)

    casa_bandpass(
        vis=ms,
        caltable=f"{table_prefix}_bacal",
        field=cal_field,
        solint="inf",
        combine="scan",
        refant=refant,
        solnorm=True,
        bandtype="B",
        gaintable=[ktable],
    )

    casa_bandpass(
        vis=ms,
        caltable=f"{table_prefix}_bpcal",
        field=cal_field,
        solint="inf",
        combine="scan",
        refant=refant,
        solnorm=True,
        bandtype="B",
        gaintable=[ktable, f"{table_prefix}_bacal"],
    )

    return [f"{table_prefix}_bacal", f"{table_prefix}_bpcal"]


def solve_gains(
    ms: str,
    cal_field: str,
    refant: str,
    ktable: str,
    bptables: List[str],
    table_prefix: Optional[str] = None,
    t_short: str = "60s",
    do_fluxscale: bool = False,
) -> List[str]:
    """Solve gain amplitude and phase; optionally short-timescale and fluxscale."""
    if table_prefix is None:
        table_prefix = f"{ms.rstrip('.ms')}_{cal_field}"

    gaintable = [ktable] + bptables
    casa_gaincal(
        vis=ms,
        caltable=f"{table_prefix}_gacal",
        field=cal_field,
        solint="inf",
        refant=refant,
        gaintype="G",
        calmode="a",
        gaintable=gaintable,
    )
    gaintable2 = gaintable + [f"{table_prefix}_gacal"]
    casa_gaincal(
        vis=ms,
        caltable=f"{table_prefix}_gpcal",
        field=cal_field,
        solint="inf",
        refant=refant,
        gaintype="G",
        calmode="p",
        gaintable=gaintable2,
    )

    out = [f"{table_prefix}_gacal", f"{table_prefix}_gpcal"]

    if t_short:
        casa_gaincal(
            vis=ms,
            caltable=f"{table_prefix}_2gcal",
            field=cal_field,
            solint=t_short,
            refant=refant,
            gaintype="G",
            calmode="ap",
            gaintable=gaintable2,
        )
        out.append(f"{table_prefix}_2gcal")

    if do_fluxscale:
        casa_fluxscale(
            vis=ms,
            caltable=f"{table_prefix}_gacal",
            fluxtable=f"{table_prefix}_flux.cal",
            reference=cal_field,
        )
        out.append(f"{table_prefix}_flux.cal")

    return out
