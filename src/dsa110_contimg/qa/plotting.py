"""
Headless plotting utilities for CASA-based pipelines.

Features:
- Forces headless operation (no GUI): sets QT_QPA_PLATFORM=offscreen,
  unsets DISPLAY.
- Attempts to start a virtual display via pyvirtualdisplay if needed.
- Wraps casaplotms.plotms with showgui=False and plotfile targeting.
- Supports multiple output formats per plot (e.g., PNG, PDF) via
  QA_PLOT_FORMATS.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


def _ensure_headless() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if os.environ.get("DISPLAY"):
        os.environ.pop("DISPLAY", None)


def _start_virtual_display(qa_root: Optional[str] = None) -> Optional[Any]:
    try:
        from pyvirtualdisplay import Display  # type: ignore

        display = Display(visible=0, size=(1600, 1200))
        display.start()
        if qa_root:
            note = os.path.join(qa_root, "VIRTUAL_DISPLAY_STARTED.txt")
            with open(note, "w", encoding="utf-8") as f:
                f.write("pyvirtualdisplay started for headless plotting.\n")
        return display
    except Exception:
        if qa_root:
            note = os.path.join(qa_root, "PLOTS_VDISPLAY_UNAVAILABLE.txt")
            with open(note, "w", encoding="utf-8") as f:
                f.write("pyvirtualdisplay not available; proceeding without.\n")
        return None


def _import_plotms() -> Optional[Any]:
    try:
        from casaplotms import plotms  # type: ignore

        return plotms
    except Exception:
        return None


def get_output_formats() -> List[str]:
    fmt_env = os.environ.get("QA_PLOT_FORMATS", "png")
    fmts = [f.strip().lower() for f in fmt_env.split(",") if f.strip()]
    # Allow only known safe formats
    allowed = {"png", "jpg", "jpeg", "pdf"}
    out = [f for f in fmts if f in allowed]
    return out or ["png"]


def plotms_headless(
    vis: str,
    qa_root: str,
    filename_base: str,
    *,
    xaxis: str,
    yaxis: str,
    coloraxis: str = "spw",
    avgchannel: str = "64",
    avgtime: str = "",
    avgscan: bool = False,
    extra_params: Optional[Dict[str, Any]] = None,
) -> List[str]:
    _ensure_headless()
    display = None
    artifacts: List[str] = []

    plotms = _import_plotms()
    if plotms is None:
        note = os.path.join(qa_root, "PLOTS_SKIPPED_NO_CASAPLOTMS.txt")
        with open(note, "w", encoding="utf-8") as f:
            f.write("plotms not importable; install casaplotms.\n")
        return [note]

    # Try to start a virtual display when none present
    if not os.environ.get("DISPLAY"):
        display = _start_virtual_display(qa_root)

    try:
        formats = get_output_formats()
        # Use plotms expformat and include extension in plotfile for clarity
        out_base = os.path.join(qa_root, f"{filename_base}")
        for fmt in formats:
            out_path = f"{out_base}.{fmt}"
            params: Dict[str, Any] = {
                "vis": vis,
                "xaxis": xaxis,
                "yaxis": yaxis,
                "coloraxis": coloraxis,
                "avgchannel": avgchannel,
                "avgtime": avgtime,
                "avgscan": avgscan,
                "plotfile": out_path,
                "expformat": fmt,
                "showgui": False,
                "overwrite": True,
            }
            if extra_params:
                params.update(extra_params)
            plotms(**params)
            artifacts.append(out_path)
        return artifacts
    except Exception as e:
        note = os.path.join(qa_root, "PLOTS_SKIPPED_ERROR.txt")
        with open(note, "w", encoding="utf-8") as f:
            f.write(f"plotms failed headlessly: {e}\n")
        return [note]
    finally:
        try:
            if display is not None:
                display.stop()
        except Exception:
            pass


def standard_visibility_plots(vis: str, qa_root: str) -> List[str]:
    artifacts: List[str] = []
    artifacts.extend(
        plotms_headless(
            vis=vis,
            qa_root=qa_root,
            filename_base="amp_vs_time",
            xaxis="time",
            yaxis="amp",
            coloraxis="spw",
            avgchannel="64",
        )
    )
    artifacts.extend(
        plotms_headless(
            vis=vis,
            qa_root=qa_root,
            filename_base="phase_vs_freq",
            xaxis="freq",
            yaxis="phase",
            coloraxis="baseline",
            avgtime="30s",
        )
    )
    artifacts.extend(
        plotms_headless(
            vis=vis,
            qa_root=qa_root,
            filename_base="uv_amp",
            xaxis="uvdist",
            yaxis="amp",
            coloraxis="spw",
            avgscan=True,
        )
    )
    return artifacts


__all__ = [
    "plotms_headless",
    "standard_visibility_plots",
    "get_output_formats",
]
