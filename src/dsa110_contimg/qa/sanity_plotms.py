"""
Create a tiny synthetic MS with a 1 Jy point source and produce headless plots.

Usage:
  python -m qa.sanity_plotms --outdir /data/dsa110-contimg/qa/_synthetic_plotms
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Headless env
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if os.environ.get("DISPLAY"):
        os.environ.pop("DISPLAY", None)

    # CASA imports
    from casatasks import simobserve  # type: ignore  # noqa: E402
    from casatools import componentlist  # type: ignore  # noqa: E402

    try:
        from casaplotms import plotms  # type: ignore  # noqa: E402
    except Exception as e:
        p = outdir / "PLOTS_SKIPPED_NO_CASAPLOTMS.txt"
        p.write_text(f"casaplotms not importable: {e}\n", encoding="utf-8")
        return 0

    # Build a simple component list (1 Jy point)
    cl = componentlist()
    cl.addcomponent(
        dir="J2000 10h00m00.0 02d00m00.0",
        flux=1.0,
        fluxunit="Jy",
        shape="point",
        freq="1.5GHz",
    )
    # Overwrite existing component list if present
    pt_path = outdir / "pt.cl"
    try:
        if pt_path.exists():
            import shutil

            shutil.rmtree(pt_path, ignore_errors=True)
        cl.rename(str(pt_path))
    finally:
        cl.close()

    # Simulate a short observation (alma small array)
    # Run simobserve from outdir with a simple relative project name
    os.chdir(outdir)
    proj_name = "pmstest"
    simobserve(
        project=proj_name,
        complist=str(outdir / "pt.cl"),
        setpointings=True,
        direction="J2000 10h00m00.0 02d00m00.0",
        obsmode="int",
        antennalist="alma.out10.cfg",
        compwidth="2GHz",
        comp_nchan=1,
        thermalnoise="",
        totaltime="30s",
        maptype="ALMA",
        graphics="none",
        overwrite=True,
    )

    # Find the produced MS
    ms_candidates = list((outdir / proj_name).rglob("*.ms"))
    if not ms_candidates:
        (outdir / "SIMOBSERVE_FAILED.txt").write_text(
            "simobserve produced no .ms\n", encoding="utf-8"
        )
        return 1
    vis = str(ms_candidates[0])

    # Optional virtual display
    vdisplay = None
    try:
        from pyvirtualdisplay import Display  # type: ignore  # noqa: E402

        vdisplay = Display(visible=False, size=(1600, 1200))
        vdisplay.start()
    except Exception:
        pass

    # Headless plots using expformat
    try:
        base = str(outdir / "plotms_sanity")
        plotms(
            vis=vis,
            xaxis="time",
            yaxis="amp",
            plotfile=base,
            expformat="png",
            showgui=False,
            overwrite=True,
        )
        plotms(
            vis=vis,
            xaxis="freq",
            yaxis="phase",
            plotfile=base + "_freq",
            expformat="pdf",
            showgui=False,
            overwrite=True,
        )
        print("OK: wrote", base + ".png")
        print("OK: wrote", base + "_freq.pdf")
    finally:
        try:
            if vdisplay is not None:
                vdisplay.stop()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
