from pathlib import Path
from typing import List

import matplotlib
matplotlib.use("Agg")  # non-interactive
import matplotlib.pyplot as plt
import numpy as np
from casaplotms import plotms as casa_plotms


def save_plotms_cal_figure(
    caltable: str,
    xaxis: str,
    yaxis: str,
    out_png: str,
    subplot: int = 221,
) -> None:
    """Save a CASA plotms figure for a caltable to file."""
    # Ensure parent directory exists
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    # Plotms is the modern replacement for plotcal
    casa_plotms(
        vis=caltable,
        xaxis=xaxis,
        yaxis=yaxis,
        plotfile=out_png,
        overwrite=True,
        showgui=False,
        subplot=subplot
    )


def plot_delay_histogram(delays_ns: np.ndarray, out_png: str) -> None:
    plt.figure(figsize=(6, 4))
    plt.hist(delays_ns[~np.isnan(delays_ns)], bins=30, alpha=0.8)
    plt.xlabel("Delay (ns)")
    plt.ylabel("Count")
    plt.tight_layout()
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png)
    plt.close()


