from typing import List, Optional

from casatasks import flagdata


def reset_flags(ms: str) -> None:
    flagdata(vis=ms, mode="unflag")


def flag_zeros(ms: str, datacolumn: str = "data") -> None:
    flagdata(vis=ms, mode="clip", datacolumn=datacolumn, clipzeros=True)


def flag_rfi(ms: str, datacolumn: str = "data") -> None:
    # Two-stage RFI flagging using flagdata modes (tfcrop then rflag)
    flagdata(
        vis=ms,
        mode="tfcrop",
        datacolumn=datacolumn,
        timecutoff=4.0,
        freqcutoff=4.0,
        timefit="line",
        freqfit="poly",
        maxnpieces=5,
        winsize=3,
        extendflags=False,
    )
    flagdata(
        vis=ms,
        mode="rflag",
        datacolumn=datacolumn,
        timedevscale=4.0,
        freqdevscale=4.0,
        extendflags=False,
    )


def flag_antenna(ms: str, antenna: str, datacolumn: str = "data", pol: Optional[str] = None) -> None:
    antenna_sel = antenna if pol is None else f"{antenna}&{pol}"
    flagdata(vis=ms, mode="manual", antenna=antenna_sel, datacolumn=datacolumn)


def flag_baselines(ms: str, uvrange: str = "2~50m", datacolumn: str = "data") -> None:
    flagdata(vis=ms, mode="manual", uvrange=uvrange, datacolumn=datacolumn)


def flag_manual(ms: str, selectexpr: str, datacolumn: str = "data") -> None:
    flagdata(vis=ms, mode="manual", datacolumn=datacolumn, **{"antenna": selectexpr})


