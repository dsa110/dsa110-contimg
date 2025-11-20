from __future__ import annotations

import os
import shutil
from typing import Optional

from casatasks import mstransform as casa_mstransform  # type: ignore[import]


def make_subset(
    ms_in: str,
    ms_out: str,
    *,
    datacolumn: str = "DATA",
    timebin: Optional[str] = None,
    chanbin: Optional[int] = None,
    combinespws: bool = False,
    keepflags: bool = True,
) -> str:
    """
    Create a reduced Measurement Set for fast calibration using CASA
    mstransform.

    Parameters are passed conservatively; only enabled when explicitly set.
    """
    if os.path.isdir(ms_out):
        shutil.rmtree(ms_out, ignore_errors=True)

    kwargs = dict(
        vis=ms_in,
        outputvis=ms_out,
        datacolumn=datacolumn,
        keepflags=keepflags,
    )

    if timebin:
        kwargs["timebin"] = timebin
    if chanbin and int(chanbin) > 1:
        kwargs["chanaverage"] = True
        kwargs["chanbin"] = int(chanbin)
    if combinespws:
        kwargs["combinespws"] = True
        # When combining SPWs, disable regrid unless explicitly needed
        kwargs.setdefault("regridms", False)

    casa_mstransform(**kwargs)
    return ms_out
