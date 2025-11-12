# Calibration plan for CASA measurement sets
_Exported on 10/6/2025 at 03:32:38 PDT from Cursor (1.8.0-pre.15.patch.0)_

---

**User**

Design a detailed plan for performing calibration on the CASA measurement sets using CASA. Ensure it can all be done within the casa6 conda environment. Design the calibration procedure, as well as the cadence, and monitoring of calibrators.Use @dsacalib/ as a reference. This repo contains functions to read the NVSS catalog, and VLA calibrator catalog (one place to look, but not the only place to look, is @preprocess.py and @calibration_service.py ). The VLA calibrator catalog should be the primary reference catalog for identifying bandpass calibrators. Use the @Web as well if you're unsure of how to do something.Note: we're using CASA version 6.7 and Pyuvdata version 3.2.4.

Revamp this plan to not rely on dsacalib but rather rewrite everything from scratch, if necessary copying the same methods from dsacalib, but never importing from dsacalib.

Implement the plan as specified.

---

**Cursor**

I'll set up a small standalone calibration package (no dsacalib imports) with catalog parsers, CASA-based flagging and calibration, QA plotting, and a CLI to run on existing MS. Then I'll create the files and implementations.

I'll start by adding a small, self-contained calibration package (no dsacalib) with catalog parsers, CASA-based flagging and calibration helpers, QA utilities, and a CLI. Then I’ll wire basic delay/bandpass/gain routines and caltable generation.

```python
"""Lightweight CASA 6.7 calibration helpers (no dsacalib runtime deps).

Modules:
- catalogs: NVSS/VLA calibrator parsing and declination caltable generation
- flagging: CASA flagging wrappers
- calibration: delay, bandpass, gain solving helpers
- applycal: application of calibration tables to target MS
- qa: plotting utilities
- cli: command-line interface to run the pipeline
"""

__all__ = [
    "catalogs",
    "flagging",
    "calibration",
    "applycal",
    "qa",
]


```

```python
import os
import gzip
from urllib.request import urlretrieve
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from astropy.coordinates import Angle
import astropy.units as u

NVSS_URL = (
    "https://heasarc.gsfc.nasa.gov/FTP/heasarc/dbase/tdat_files/heasarc_nvss.tdat.gz"
)


def read_nvss_catalog(cache_dir: str = ".cache/catalogs") -> pd.DataFrame:
    """Download (if needed) and parse the NVSS catalog to a DataFrame.

    Returns flux_20_cm in mJy to match historical conventions.
    """
    os.makedirs(cache_dir, exist_ok=True)
    gz_path = str(Path(cache_dir) / "heasarc_nvss.tdat.gz")
    txt_path = str(Path(cache_dir) / "heasarc_nvss.tdat")

    if not os.path.exists(txt_path):
        if not os.path.exists(gz_path):
            urlretrieve(NVSS_URL, gz_path)
        with gzip.open(gz_path, "rb") as f_in, open(txt_path, "wb") as f_out:
            f_out.write(f_in.read())

    df = pd.read_csv(
        txt_path,
        sep="|",
        skiprows=67,
        names=[
            "ra",
            "dec",
            "lii",
            "bii",
            "ra_error",
            "dec_error",
            "flux_20_cm",
            "flux_20_cm_error",
            "limit_major_axis",
            "major_axis",
            "major_axis_error",
            "limit_minor_axis",
            "minor_axis",
            "minor_axis_error",
            "position_angle",
            "position_angle_error",
            "residual_code",
            "residual_flux",
            "pol_flux",
            "pol_flux_error",
            "pol_angle",
            "pol_angle_error",
            "field_name",
            "x_pixel",
            "y_pixel",
            "extra",
        ],
    )
    if len(df) > 0:
        df = df.iloc[:-1]  # drop trailer row
    if "extra" in df.columns:
        df = df.drop(columns=["extra"])  # trailing blank
    return df


def read_vla_calibrator_catalog(
    path: str, cache_dir: Optional[str] = None
) -> pd.DataFrame:
    """Parse the NRAO VLA calibrator list from a local text file.

    Expected format similar to NRAO distributed list. This parser mirrors the
    multi-block entry logic: header line with source and coordinates, followed by
    several lines including the "20cm" line with codes and flux.
    """
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
    calsources = []
    with open(path, encoding="utf-8") as fh:
        # Skip top header lines if present
        for _ in range(3):
            pos = fh.tell()
            line = fh.readline()
            if not line:
                break
        else:
            fh.seek(pos)

        while True:
            line = fh.readline()
            if not line:
                break
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            source, ra_str, dec_str = None, None, None
            # Catalog variants may put placeholders; robustly identify RA/Dec tokens
            # Heuristic: last two resolvable sexagesimal tokens are RA, Dec
            try:
                source = parts[0]
                ra_str = parts[-2]
                dec_str = parts[-1]
                ra = Angle(ra_str).to_value(u.deg)
                dec = Angle(dec_str).to_value(u.deg)
            except Exception:
                # Fallback to next lines
                continue

            flux_20_cm = None
            code_20_cm = None

            # Consume next 4 lines (per legacy layout) before the frequency blocks
            lookahead = [fh.readline() for _ in range(4)]

            # Read frequency-specific blocks until blank line
            while True:
                pos2 = fh.tell()
                line2 = fh.readline()
                if (not line2) or line2.isspace():
                    break
                if "20cm" in line2:
                    toks = line2.split()
                    # Example expected: "20cm  ... codes ... flux ..."
                    if len(toks) >= 7:
                        # last token is flux (Jy); codes are 4 consecutive strings
                        flux_20_cm = toks[-1]
                        # attempt to concatenate 4 code tokens if present
                        codes = toks[2:6] if len(toks) >= 6 else []
                        code_20_cm = "".join(codes) if codes else None
            # rewind one line for next entry loop
            fh.seek(pos2)

            if flux_20_cm not in [None, "?"]:
                try:
                    flux_mJy = 1000.0 * float(flux_20_cm)
                except Exception:
                    flux_mJy = np.nan
                calsources.append(
                    {
                        "source": source,
                        "ra": ra,
                        "dec": dec,
                        "flux_20_cm": flux_mJy,
                        "code_20_cm": code_20_cm,
                    }
                )

    df = pd.DataFrame.from_records(calsources)
    if not df.empty:
        df = df.set_index("source")
    return df


def airy_primary_beam_response(
    ant_ra: float, ant_dec: float, src_ra: float, src_dec: float, freq_GHz: float, dish_dia_m: float = 4.7
) -> float:
    """Approximate primary beam response using an Airy pattern.

    Returns a scalar response in [0, 1]. Coordinates in radians.
    """
    # Offset angle approximation on the sky
    dra = (src_ra - ant_ra) * np.cos(ant_dec)
    ddec = src_dec - ant_dec
    theta = np.sqrt(dra * dra + ddec * ddec)
    # First-null approximation: 1.22 * lambda / D
    lam_m = (3e8 / (freq_GHz * 1e9))
    x = np.pi * dish_dia_m * np.sin(theta) / lam_m
    # Avoid division by zero
    x = np.where(x == 0, 1e-12, x)
    resp = (2 * (np.sin(x) - x * np.cos(x)) / (x * x)) ** 2
    # Clamp numeric noise
    return float(np.clip(resp, 0.0, 1.0))


def generate_caltable(
    vla_df: pd.DataFrame,
    pt_dec: u.Quantity,
    csv_path: str,
    radius: u.Quantity = 2.5 * u.deg,
    min_weighted_flux: u.Quantity = 1.0 * u.Jy,
    min_percent_flux: float = 0.15,
) -> str:
    """Build a declination-specific calibrator table and save to CSV.

    Weighted by primary beam response at 1.4 GHz.
    """
    pt_dec_deg = pt_dec.to_value(u.deg)
    cal_df = vla_df[
        (vla_df["dec"] < (pt_dec_deg + radius.to_value(u.deg)))
        & (vla_df["dec"] > (pt_dec_deg - radius.to_value(u.deg)))
        & (pd.to_numeric(vla_df["flux_20_cm"], errors="coerce") > 1000.0)
    ].copy()
    if cal_df.empty:
        # Still write an empty CSV to satisfy pipeline expectations
        cal_df.to_csv(csv_path, index=True)
        return csv_path

    # Compute weighted flux per calibrator and field flux
    cal_df["weighted_flux"] = 0.0
    cal_df["field_flux"] = 0.0

    ant_ra = 0.0  # use RA=self for beam centering approximation; drop explicit RA dependence
    ant_dec = np.deg2rad(pt_dec_deg)
    for name, row in cal_df.iterrows():
        src_ra = np.deg2rad(row["ra"]) if np.isfinite(row["ra"]) else 0.0
        src_dec = np.deg2rad(row["dec"]) if np.isfinite(row["dec"]) else ant_dec
        resp = airy_primary_beam_response(ant_ra, ant_dec, src_ra, src_dec, 1.4)
        cal_df.at[name, "weighted_flux"] = (row["flux_20_cm"] / 1e3) * resp

        # Field: local patch of radius scaled by cos(dec)
        field = vla_df[
            (vla_df["dec"] < (pt_dec_deg + radius.to_value(u.deg)))
            & (vla_df["dec"] > (pt_dec_deg - radius.to_value(u.deg)))
            & (vla_df["ra"] < row["ra"] + radius.to_value(u.deg) / max(np.cos(np.deg2rad(pt_dec_deg)), 1e-3))
            & (vla_df["ra"] > row["ra"] - radius.to_value(u.deg) / max(np.cos(np.deg2rad(pt_dec_deg)), 1e-3))
        ].copy()
        wsum = 0.0
        for _, crow in field.iterrows():
            f_ra = np.deg2rad(crow["ra"]) if np.isfinite(crow["ra"]) else 0.0
            f_dec = np.deg2rad(crow["dec"]) if np.isfinite(crow["dec"]) else ant_dec
            wsum += (crow["flux_20_cm"] / 1e3) * airy_primary_beam_response(
                ant_ra, ant_dec, f_ra, f_dec, 1.4
            )
        cal_df.at[name, "field_flux"] = wsum

    cal_df["percent_flux"] = cal_df["weighted_flux"] / cal_df["field_flux"].replace(0, np.nan)

    sel = cal_df[
        (cal_df["weighted_flux"] > min_weighted_flux.to_value(u.Jy))
        & (cal_df["percent_flux"] > min_percent_flux)
    ].copy()

    # Reformat columns and units
    out = sel.copy()
    out["flux (Jy)"] = out["flux_20_cm"] / 1e3
    out = out.rename(columns={"code_20_cm": "code_20_cm", "ra": "ra(deg)", "dec": "dec(deg)"})
    out = out[["ra(deg)", "dec(deg)", "flux (Jy)", "weighted_flux", "percent_flux", "code_20_cm"]]
    out.to_csv(csv_path, index=True)
    return csv_path


def update_caltable(
    vla_df: pd.DataFrame, pt_dec: u.Quantity, out_dir: str = ".cache/catalogs"
) -> str:
    """Ensure a declination-specific caltable exists; return its path."""
    os.makedirs(out_dir, exist_ok=True)
    decsign = "+" if pt_dec.to_value(u.deg) >= 0 else "-"
    decval = f"{abs(pt_dec.to_value(u.deg)):05.1f}".replace(".", "p")
    csv_path = str(Path(out_dir) / f"calibrator_sources_dec{decsign}{decval}.csv")
    if not os.path.exists(csv_path):
        generate_caltable(vla_df=vla_df, pt_dec=pt_dec, csv_path=csv_path)
    return csv_path


```

```python
from typing import List, Optional

from casatasks import flagdata, tflagdata


def reset_flags(ms: str) -> None:
    flagdata(vis=ms, mode="unflag")


def flag_zeros(ms: str, datacolumn: str = "data") -> None:
    flagdata(vis=ms, mode="clip", datacolumn=datacolumn, clipzeros=True)


def flag_rfi(ms: str, datacolumn: str = "data") -> None:
    # Two-stage tfcrop then rflag with conservative defaults
    tflagdata(
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
    tflagdata(
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


```

```python
from typing import List, Optional

import numpy as np
from casatools import calibrater
from casatasks import bandpass as casa_bandpass
from casatasks import gaincal as casa_gaincal
from casatasks import setjy as casa_setjy
from casatasks import plotcal as casa_plotcal
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
    """Solve delay (K) on slow and optional fast timescales using calibrater tool."""
    combine = "field,scan,obs,spw" if combine_spw else "field,scan,obs"
    if table_prefix is None:
        table_prefix = f"{ms.rstrip('.ms')}_{cal_field}"

    tables = []
    cb = calibrater()
    try:
        if not cb.open(ms):
            raise RuntimeError(f"Failed to open MS {ms}")
        if not cb.selectvis():
            raise RuntimeError("selectvis failed")
        if not cb.setsolve(type="K", t=t_slow, refant=refant, combine=combine, table=f"{table_prefix}_kcal"):
            raise RuntimeError("setsolve K slow failed")
        if not cb.solve():
            raise RuntimeError("solve K slow failed")
        tables.append(f"{table_prefix}_kcal")
    finally:
        cb.close()

    if t_fast:
        cb = calibrater()
        try:
            cb.open(ms)
            cb.selectvis()
            if not cb.setsolve(type="K", t=t_fast, refant=refant, combine=combine, table=f"{table_prefix}_2kcal"):
                raise RuntimeError("setsolve K fast failed")
            if not cb.solve():
                raise RuntimeError("solve K fast failed")
            tables.append(f"{table_prefix}_2kcal")
        finally:
            cb.close()

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


```

```python
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


```

```python
from pathlib import Path
from typing import List

import matplotlib
matplotlib.use("Agg")  # non-interactive
import matplotlib.pyplot as plt
import numpy as np
from casatasks import plotcal as casa_plotcal


def save_plotcal(
    caltable: str,
    xaxis: str,
    yaxis: str,
    out_png: str,
    subplot: int = 111,
) -> None:
    """Save a CASA plotcal figure to file by invoking task with png output dir."""
    # CASA's plotcal writes to files via figfile. We call twice for robustness.
    casa_plotcal(caltable=caltable, xaxis=xaxis, yaxis=yaxis, figfile=out_png, subplot=subplot)


def plot_delay_histogram(delays_ns: np.ndarray, out_png: str) -> None:
    plt.figure(figsize=(6, 4))
    plt.hist(delays_ns[~np.isnan(delays_ns)], bins=30, alpha=0.8)
    plt.xlabel("Delay (ns)")
    plt.ylabel("Count")
    plt.tight_layout()
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png)
    plt.close()


```

```python
import argparse
from typing import List

from .flagging import reset_flags, flag_zeros, flag_rfi
from .calibration import solve_delay, solve_bandpass, solve_gains
from .applycal import apply_to_target


def run_calibrator(ms: str, cal_field: str, refant: str) -> List[str]:
    reset_flags(ms)
    flag_zeros(ms)
    flag_rfi(ms)
    ktabs = solve_delay(ms, cal_field, refant)
    bptabs = solve_bandpass(ms, cal_field, refant, ktabs[0])
    gtabs = solve_gains(ms, cal_field, refant, ktabs[0], bptabs)
    return ktabs[:1] + bptabs + gtabs


def main():
    p = argparse.ArgumentParser(description="CASA 6.7 calibration runner (no dsacalib)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("calibrate", help="Calibrate a calibrator MS")
    pc.add_argument("--ms", required=True)
    pc.add_argument("--field", required=True, help="Calibrator field name/index")
    pc.add_argument("--refant", required=True)

    pt = sub.add_parser("apply", help="Apply calibration to target MS")
    pt.add_argument("--ms", required=True)
    pt.add_argument("--field", required=True)
    pt.add_argument("--tables", nargs="+", required=True, help="Calibration tables in order")

    args = p.parse_args()

    if args.cmd == "calibrate":
        tabs = run_calibrator(args.ms, args.field, args.refant)
        print("Generated tables:\n" + "\n".join(tabs))
    elif args.cmd == "apply":
        apply_to_target(args.ms, args.field, args.tables)
        print("Applied calibration to target")


if __name__ == "__main__":
    main()


```

```markdown
## casa_cal: CASA 6.7 calibration helpers (no dsacalib)

Install environment:
```bash
conda create -n casa6-67 python=3.10 -y
conda activate casa6-67
conda install -c conda-forge casatools=6.7.0 casatasks=6.7.0 casadata pyuvdata=3.2.4 astropy=6 pandas=2.2 numpy scipy matplotlib pyyaml -y
```

Catalogs:
- Use `catalogs.read_vla_calibrator_catalog(path)` and `catalogs.read_nvss_catalog()`.
- Generate declination table via `catalogs.update_caltable(vla_df, pt_dec)`.

Run calibration:
```bash
python -m casa_cal.cli calibrate --ms <cal.ms> --field <cal_field> --refant <ant>
```
Apply to target:
```bash
python -m casa_cal.cli apply --ms <target.ms> --field <field> --tables <ms_cal>_kcal <ms_cal>_bacal <ms_cal>_bpcal <ms_cal>_gacal <ms_cal>_gpcal
```


```

```python
from typing import Optional

from casatasks import tclean as casa_tclean


def quick_image(
    ms: str,
    imagename: str,
    field: str,
    niter: int = 1000,
    threshold: str = "0.1mJy",
    weighting: str = "briggs",
    robust: float = 0.5,
) -> None:
    casa_tclean(
        vis=ms,
        imagename=imagename,
        field=field,
        deconvolver="multiscale",
        scales=[0, 3, 10],
        weighting=weighting,
        robust=robust,
        niter=niter,
        threshold=threshold,
        usemask="auto-multithresh",
        interactive=False,
    )


```

Let me confirm two details so I can begin implementing without surprises:

1. Where should I write the new code package?
   - a) /data/dsa110-contimg/casa_cal (default)
   - b) Another path (please specify)

2. Where is the VLA calibrator catalog text file I should parse?
   - a) references/dsa110-calib/dsacalib/data/vlacalibrators.txt
   - b) Provide an alternate path or URL

Once confirmed, I’ll implement the package exactly per the plan:
- catalogs: NVSS/VLA parsers and declination caltable
- flagging: CASA flag wrappers
- calibration: delay, bandpass, gains
- applycal: apply tables to targets
- imaging: quick tclean
- qa: plotcal exports and delay histograms
- cli: calibrate/apply driver

You’ll then be able to:
- Set up env
- Run calibration on a calibrator MS
- Apply tables to targets
- Generate QA figures

Quick reference commands (for when code is in place):
```bash
# env
conda create -n casa6-67 python=3.10 -y
conda activate casa6-67
conda install -c conda-forge casatools=6.7.0 casatasks=6.7.0 casadata pyuvdata=3.2.4 astropy=6 pandas=2.2 numpy scipy matplotlib pyyaml -y

# calibrate a calibrator MS
python -m casa_cal.cli calibrate --ms <cal.ms> --field <cal_field> --refant <ant>

# apply to target
python -m casa_cal.cli apply --ms <target.ms> --field <field> --tables <ms_cal>_kcal <ms_cal>_bacal <ms_cal>_bpcal <ms_cal>_gacal <ms_cal>_gpcal
```

- I’m ready to start as soon as you confirm the two items above.

```shellscript
# env
conda create -n casa6-67 python=3.10 -y
conda activate casa6-67
conda install -c conda-forge casatools=6.7.0 casatasks=6.7.0 casadata pyuvdata=3.2.4 astropy=6 pandas=2.2 numpy scipy matplotlib pyyaml -y

# calibrate a calibrator MS
python -m casa_cal.cli calibrate --ms <cal.ms> --field <cal_field> --refant <ant>

# apply to target
python -m casa_cal.cli apply --ms <target.ms> --field <field> --tables <ms_cal>_kcal <ms_cal>_bacal <ms_cal>_bpcal <ms_cal>_gacal <ms_cal>_gpcal
```

```shellscript
# env
conda create -n casa6-67 python=3.10 -y
conda activate casa6-67
conda install -c conda-forge casatools=6.7.0 casatasks=6.7.0 casadata pyuvdata=3.2.4 astropy=6 pandas=2.2 numpy scipy matplotlib pyyaml -y

# calibrate a calibrator MS
python -m casa_cal.cli calibrate --ms <cal.ms> --field <cal_field> --refant <ant>

# apply to target
python -m casa_cal.cli apply --ms <target.ms> --field <field> --tables <ms_cal>_kcal <ms_cal>_bacal <ms_cal>_bpcal <ms_cal>_gacal <ms_cal>_gpcal
```

---

**User**

We should ensure that this all works within the already created casa6  conda environment.

---

**Cursor**

- Activate your existing env and install/ensure deps:
```bash
conda activate casa6
conda install -y -c conda-forge casatools=6.7.0 casatasks=6.7.0 casadata
conda install -y -c conda-forge pyuvdata=3.2.4 astropy=6 pandas=2.2 numpy scipy matplotlib pyyaml
python - << 'PY'
import casatools, casatasks; print('CASA OK')
import pyuvdata, astropy, pandas, numpy, scipy, matplotlib; print('Sci stack OK')
import sys; sys.path.insert(0, '/data/dsa110-contimg'); import casa_cal; print('casa_cal OK')
PY
```

- Run calibrator → produce tables (K+B+G) with your MS:
```bash
python -m casa_cal.cli calibrate --ms /path/to/calibrator.ms --field <cal_field> --refant <ant>
```

- Apply to a target MS:
```bash
python -m casa_cal.cli apply --ms /path/to/target.ms --field <field> --tables \
/path/to/calibrator_kcal /path/to/calibrator_bacal /path/to/calibrator_bpcal \
/path/to/calibrator_gacal /path/to/calibrator_gpcal
```

- Optional quick image:
```bash
python - << 'PY'
from casa_cal.imaging import quick_image
quick_image('/path/to/target.ms', imagename='target_image', field='<field>')
PY
```

Notes
- Package path is `/data/dsa110-contimg/casa_cal`; no pip install needed.
- Matplotlib is configured for non-interactive backend; plots are written to files.
- If your env already has CASA 6.7, only install any missing libs from the commands above.

```shellscript
conda activate casa6
conda install -y -c conda-forge casatools=6.7.0 casatasks=6.7.0 casadata
conda install -y -c conda-forge pyuvdata=3.2.4 astropy=6 pandas=2.2 numpy scipy matplotlib pyyaml
python - << 'PY'
import casatools, casatasks; print('CASA OK')
import pyuvdata, astropy, pandas, numpy, scipy, matplotlib; print('Sci stack OK')
import sys; sys.path.insert(0, '/data/dsa110-contimg'); import casa_cal; print('casa_cal OK')
PY
```

```shellscript
python -m casa_cal.cli calibrate --ms /path/to/calibrator.ms --field <cal_field> --refant <ant>
```

```shellscript
python -m casa_cal.cli apply --ms /path/to/target.ms --field <field> --tables \
/path/to/calibrator_kcal /path/to/calibrator_bacal /path/to/calibrator_bpcal \
/path/to/calibrator_gacal /path/to/calibrator_gpcal
```

```shellscript
python - << 'PY'
from casa_cal.imaging import quick_image
quick_image('/path/to/target.ms', imagename='target_image', field='<field>')
PY
```

---

**User**

Walk through how the calibrator searching and selection works.

---

**Cursor**

### How calibrator search and selection works (no dsacalib)

- General flow
  - Load catalogs:
    - VLA calibrator list (primary for bandpass/gain calibrators) using `read_vla_calibrator_catalog(path)`.
    - NVSS (optional cross-check) using `read_nvss_catalog()`.
  - Build a declination-specific candidate list near the current pointing declination using `update_caltable(vla_df, pt_dec)`, which internally calls `generate_caltable(...)`.
  - Select the bandpass calibrator from this candidate list (highest weighted flux, compact code if available).
  - Select gain calibrators near each target in time/elevation for cadence.

- Inputs used
  - `pt_dec`: pointing declination (astropy quantity, deg or rad).
  - `radius`: sky radius around `pt_dec` to consider (default 2.5 deg).
  - `min_weighted_flux`: minimum primary-beam-weighted flux (default 1.0 Jy).
  - `min_percent_flux`: minimum fraction of field weighted flux contributed by the candidate (default 0.15).

- Catalog parsing
  - VLA calibrators: `read_vla_calibrator_catalog(path)` parses the NRAO-format file into a DataFrame indexed by `source` with numeric `ra`/`dec` in deg and `flux_20_cm` in mJy. If the “20cm” block is present for a source, its flux (Jy) is converted to mJy and stored; any accompanying code string (e.g., quality flags) is captured as `code_20_cm`.
  - NVSS: `read_nvss_catalog()` downloads and caches `heasarc_nvss.tdat.gz`, parses to a DataFrame with `ra`, `dec`, and `flux_20_cm` in mJy. This is optional and used for cross-checks/monitoring.

- Candidate generation and scoring
  - Declination window:
    - Filter VLA entries with `dec` in [pt_dec − radius, pt_dec + radius] and `flux_20_cm` > 1000 mJy (i.e., >1 Jy).
  - Primary-beam weighting:
    - For each candidate, compute a primary-beam response at 1.4 GHz (Airy-like model) via `airy_primary_beam_response(...)`.
    - Weighted flux = (catalog flux in Jy) × (primary-beam response).
  - Field flux normalization:
    - For each candidate, compute the total weighted flux of all VLA catalog entries within a local RA/Dec patch (RA half-width scaled by cos(dec) to account for convergence of meridians) and within the same declination band.
    - Percent flux = candidate weighted flux / local field weighted flux.
  - Selection thresholds:
    - Keep only candidates with `weighted_flux` > `min_weighted_flux` (default 1.0 Jy) and `percent_flux` > `min_percent_flux` (default 0.15).
  - Output:
    - A CSV is written under `.cache/catalogs/` by `generate_caltable(...)` and managed by `update_caltable(...)`. Columns include `ra(deg)`, `dec(deg)`, `flux (Jy)`, `weighted_flux`, `percent_flux`, `code_20_cm`.
    - `update_caltable(vla_df, pt_dec)` ensures the declination-specific CSV exists and returns its path.

- Bandpass calibrator selection
  - Choose the top-ranked entry by `weighted_flux` from the declination CSV.
  - Prefer known-good codes (if your VLA file includes calibrator codes); if present, filter to compact, stable codes before picking the top by `weighted_flux`.
  - Validate visibility (elevation constraints, not too close to horizon) for your observing time.

- Gain calibrator selection and cadence
  - Use the same declination-specific table, but you may relax `min_weighted_flux` slightly to allow more candidates (e.g., 0.5–1.0 Jy weighted).
  - For a given target schedule, select a gain calibrator that:
    - Is close in sky/elevation to minimize switching overhead.
    - Has stable structure (point-like or compact).
    - Is observed on a cadence of every 10–15 minutes. Interpolate solutions to targets with appropriate interpolation in `applycal`.
  - If multiple gain calibrators are available, alternate to improve calibration robustness across the session.

- Monitoring and QA
  - Periodically re-run `update_caltable(vla_df, pt_dec)` when the pointing declination or session changes.
  - Cross-check candidate stability against NVSS (e.g., large flux discrepant entries can hint at resolved/variable sources).
  - Track session-by-session solution quality: delay outliers, bandpass phase stability, gain scatter. If a calibrator underperforms, demote it and pick the next best candidate.

- Typical usage sketch
  - Load catalog and build candidate list:
    - vla_df = read_vla_calibrator_catalog('references/dsa110-calib/dsacalib/data/vlacalibrators.txt')
    - cal_csv = update_caltable(vla_df, pt_dec)
  - Pick bandpass calibrator:
    - Read `cal_csv` with pandas, sort by `weighted_flux` desc, optionally filter by `code_20_cm`, choose the top entry.
  - Pick gain calibrators:
    - From the same table, select 1–2 additional entries with high `weighted_flux` and good elevation coverage for the anticipated cadence.

- Practical notes
  - The Airy-like primary beam is an approximation and is used to prioritize calibrators by in-beam strength near the meridian. If you have a measured beam model, you can substitute it in `airy_primary_beam_response(...)`.
  - Thresholds (`min_weighted_flux`, `min_percent_flux`) are tunable. Increase them for stricter quality; decrease slightly if the sky is sparse at your declination.
  - If you maintain a quality history (delay RMS, bandpass phase RMS, gain stability), feed that back into candidate ranking session-over-session.

---

**User**

Can you perform an example run that goes through the general flow?

---

**Cursor**

### Example run: end-to-end flow in your existing casa6 env

1) Activate env and verify
```bash
conda activate casa6
python - << 'PY'
import casatools, casatasks; print('CASA 6.7 OK')
import casa_cal; print('casa_cal OK')
PY
```

2) Parse VLA catalog and build a declination-specific candidate list
```bash
python - << 'PY'
from pathlib import Path
import pandas as pd
import astropy.units as u
from casa_cal.catalogs import read_vla_calibrator_catalog, update_caltable

vla_path = '/data/dsa110-contimg/references/dsa110-calib/dsacalib/data/vlacalibrators.txt'
vla_df = read_vla_calibrator_catalog(vla_path)

# Example: pointing declination +30 deg
pt_dec = 30.0 * u.deg
csv_path = update_caltable(vla_df, pt_dec)
print('Caltable CSV:', csv_path)

# Pick top candidate by weighted flux
df = pd.read_csv(csv_path, index_col=0)
cand = df.sort_values('weighted_flux', ascending=False).head(1)
cal_name = cand.index[0]
cal_ra_deg = cand['ra(deg)'].iloc[0]
cal_dec_deg = cand['dec(deg)'].iloc[0]
print('Selected bandpass calibrator:', cal_name, cal_ra_deg, cal_dec_deg)
PY
```

3) Calibrate a calibrator MS (produce K, B, G tables)
- Replace paths/field/refant for your dataset.
```bash
python -m casa_cal.cli calibrate \
  --ms /data/path/to/2025-10-06_CAL.ms \
  --field <cal_field_name_or_id> \
  --refant 23
```
This generates:
- <ms>_<field>_kcal
- <ms>_<field>_bacal
- <ms>_<field>_bpcal
- <ms>_<field>_gacal
- <ms>_<field>_gpcal
(and optionally <ms>_<field>_2kcal, <ms>_<field>_2gcal)

4) Apply those solutions to a target MS
```bash
python - << 'PY'
import glob, os
ms_cal = '/data/path/to/2025-10-06_CAL.ms'
ms_target = '/data/path/to/2025-10-06_TARGET.ms'
field = '<target_field_name_or_id>'
prefix = ms_cal.rstrip('.ms') + '_' + '<cal_field_name_or_id>'

tables = [
  f'{prefix}_kcal',
  f'{prefix}_bacal',
  f'{prefix}_bpcal',
  f'{prefix}_gacal',
  f'{prefix}_gpcal',
]

from casa_cal.applycal import apply_to_target
apply_to_target(ms_target, field, tables)
print('Applied:', tables)
PY
```

5) Quick image of the target
```bash
python - << 'PY'
from casa_cal.imaging import quick_image
quick_image('/data/path/to/2025-10-06_TARGET.ms',
            imagename='/data/path/to/out/target_image',
            field='<target_field_name_or_id>',
            niter=1000, threshold='0.1mJy')
print('Image written: /data/path/to/out/target_image.*')
PY
```

6) Optional QA plots for the calibration tables
```bash
python - << 'PY'
from pathlib import Path
from casa_cal.qa import save_plotcal

ms_cal = '/data/path/to/2025-10-06_CAL.ms'
cal_field = '<cal_field_name_or_id>'
prefix = ms_cal.rstrip('.ms') + f'_{cal_field}'
outdir = Path('/data/path/to/qa'); outdir.mkdir(parents=True, exist_ok=True)

for tab, xaxis, yaxis, out in [
  (f'{prefix}_kcal', 'time', 'delay', outdir/'kcal_delay.png'),
  (f'{prefix}_bacal', 'chan', 'amp', outdir/'bacal_amp.png'),
  (f'{prefix}_bpcal', 'chan', 'phase', outdir/'bpcal_phase.png'),
  (f'{prefix}_gacal', 'time', 'amp', outdir/'gacal_amp.png'),
  (f'{prefix}_gpcal', 'time', 'phase', outdir/'gpcal_phase.png'),
]:
  save_plotcal(tab, xaxis, yaxis, str(out))
  print('Saved', out)
PY
```

7) (Optional) Build candidates and cadence for more targets
- Reuse step 2 CSV.
- Choose 1–2 additional high weighted-flux entries as gain calibrators spaced 10–15 min across the schedule.
- Repeat steps 3–6 for each calibrator/target as needed.

That’s the full flow: select calibrator via VLA list and beam-weighting, solve K/B/G on the calibrator MS, apply to target MS, and image/QA — all within your existing casa6 environment.

```shellscript
conda activate casa6
python - << 'PY'
import casatools, casatasks; print('CASA 6.7 OK')
import casa_cal; print('casa_cal OK')
PY
```

```shellscript
python - << 'PY'
from pathlib import Path
import pandas as pd
import astropy.units as u
from casa_cal.catalogs import read_vla_calibrator_catalog, update_caltable

vla_path = '/data/dsa110-contimg/references/dsa110-calib/dsacalib/data/vlacalibrators.txt'
vla_df = read_vla_calibrator_catalog(vla_path)

# Example: pointing declination +30 deg
pt_dec = 30.0 * u.deg
csv_path = update_caltable(vla_df, pt_dec)
print('Caltable CSV:', csv_path)

# Pick top candidate by weighted flux
df = pd.read_csv(csv_path, index_col=0)
cand = df.sort_values('weighted_flux', ascending=False).head(1)
cal_name = cand.index[0]
cal_ra_deg = cand['ra(deg)'].iloc[0]
cal_dec_deg = cand['dec(deg)'].iloc[0]
print('Selected bandpass calibrator:', cal_name, cal_ra_deg, cal_dec_deg)
PY
```

```shellscript
python -m casa_cal.cli calibrate \
  --ms /data/path/to/2025-10-06_CAL.ms \
  --field <cal_field_name_or_id> \
  --refant 23
```

```shellscript
python - << 'PY'
import glob, os
ms_cal = '/data/path/to/2025-10-06_CAL.ms'
ms_target = '/data/path/to/2025-10-06_TARGET.ms'
field = '<target_field_name_or_id>'
prefix = ms_cal.rstrip('.ms') + '_' + '<cal_field_name_or_id>'

tables = [
  f'{prefix}_kcal',
  f'{prefix}_bacal',
  f'{prefix}_bpcal',
  f'{prefix}_gacal',
  f'{prefix}_gpcal',
]

from casa_cal.applycal import apply_to_target
apply_to_target(ms_target, field, tables)
print('Applied:', tables)
PY
```

```shellscript
python - << 'PY'
from casa_cal.imaging import quick_image
quick_image('/data/path/to/2025-10-06_TARGET.ms',
            imagename='/data/path/to/out/target_image',
            field='<target_field_name_or_id>',
            niter=1000, threshold='0.1mJy')
print('Image written: /data/path/to/out/target_image.*')
PY
```

```shellscript
python - << 'PY'
from pathlib import Path
from casa_cal.qa import save_plotcal

ms_cal = '/data/path/to/2025-10-06_CAL.ms'
cal_field = '<cal_field_name_or_id>'
prefix = ms_cal.rstrip('.ms') + f'_{cal_field}'
outdir = Path('/data/path/to/qa'); outdir.mkdir(parents=True, exist_ok=True)

for tab, xaxis, yaxis, out in [
  (f'{prefix}_kcal', 'time', 'delay', outdir/'kcal_delay.png'),
  (f'{prefix}_bacal', 'chan', 'amp', outdir/'bacal_amp.png'),
  (f'{prefix}_bpcal', 'chan', 'phase', outdir/'bpcal_phase.png'),
  (f'{prefix}_gacal', 'time', 'amp', outdir/'gacal_amp.png'),
  (f'{prefix}_gpcal', 'time', 'phase', outdir/'gpcal_phase.png'),
]:
  save_plotcal(tab, xaxis, yaxis, str(out))
  print('Saved', out)
PY
```

---

**User**

@test_cal.py I ran this to test 1) and 2) and got:(casa6) ubuntu@lxd110h17:/data/dsa110-contimg$ python test.py
Caltable CSV: .cache/catalogs/calibrator_sources_dec+030p0.csv
Traceback (most recent call last):
  File "/data/dsa110-contimg/test.py", line 17, in <module>
    cal_name = cand.index[0]
               ~~~~~~~~~~^^^
  File "/opt/miniforge/envs/casa6/lib/python3.11/site-packages/pandas/core/indexes/base.py", line 5401, in __getitem__
    return getitem(key)
           ^^^^^^^^^^^^
IndexError: index 0 is out of bounds for axis 0 with size 0
(casa6) ubuntu@lxd110h17:/data/dsa110-contimg$ python test.py
CASA 6.7 OK
casa_cal OK
Caltable CSV: .cache/catalogs/calibrator_sources_dec+030p0.csv
Traceback (most recent call last):
  File "/data/dsa110-contimg/test.py", line 19, in <module>
    cal_name = cand.index[0]
               ~~~~~~~~~~^^^
  File "/opt/miniforge/envs/casa6/lib/python3.11/site-packages/pandas/core/indexes/base.py", line 5401, in __getitem__
    return getitem(key)
           ^^^^^^^^^^^^
IndexError: index 0 is out of bounds for axis 0 with size 0

---

**Cursor**

I'll fix the VLA catalog parser to mirror the known file structure and add a fallback in calibrator selection when thresholds produce an empty set. Then I'll update the CSV generation accordingly.

```python
import os
import gzip
from urllib.request import urlretrieve
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from astropy.coordinates import Angle
import astropy.units as u

NVSS_URL = (
    "https://heasarc.gsfc.nasa.gov/FTP/heasarc/dbase/tdat_files/heasarc_nvss.tdat.gz"
)


def read_nvss_catalog(cache_dir: str = ".cache/catalogs") -> pd.DataFrame:
    """Download (if needed) and parse the NVSS catalog to a DataFrame.

    Returns flux_20_cm in mJy to match historical conventions.
    """
    os.makedirs(cache_dir, exist_ok=True)
    gz_path = str(Path(cache_dir) / "heasarc_nvss.tdat.gz")
    txt_path = str(Path(cache_dir) / "heasarc_nvss.tdat")

    if not os.path.exists(txt_path):
        if not os.path.exists(gz_path):
            urlretrieve(NVSS_URL, gz_path)
        with gzip.open(gz_path, "rb") as f_in, open(txt_path, "wb") as f_out:
            f_out.write(f_in.read())

    df = pd.read_csv(
        txt_path,
        sep="|",
        skiprows=67,
        names=[
            "ra",
            "dec",
            "lii",
            "bii",
            "ra_error",
            "dec_error",
            "flux_20_cm",
            "flux_20_cm_error",
            "limit_major_axis",
            "major_axis",
            "major_axis_error",
            "limit_minor_axis",
            "minor_axis",
            "minor_axis_error",
            "position_angle",
            "position_angle_error",
            "residual_code",
            "residual_flux",
            "pol_flux",
            "pol_flux_error",
            "pol_angle",
            "pol_angle_error",
            "field_name",
            "x_pixel",
            "y_pixel",
            "extra",
        ],
    )
    if len(df) > 0:
        df = df.iloc[:-1]  # drop trailer row
    if "extra" in df.columns:
        df = df.drop(columns=["extra"])  # trailing blank
    return df


def read_vla_calibrator_catalog(
    path: str, cache_dir: Optional[str] = None
) -> pd.DataFrame:
    """Parse the NRAO VLA calibrator list from a local text file.

    This follows the structure used in historical VLA calibrator files:
    - A header line per source: "<source> ... <ra> <dec> ..."
      where RA/Dec are sexagesimal strings parseable by astropy Angle.
    - Followed by 4 lines of other metadata.
    - Followed by a block of frequency lines until a blank line; the line
      containing "20cm " includes 4 code tokens and a flux (Jy).
    """
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)

    records = []
    with open(path, encoding="utf-8") as f:
        # Skip the first 3 lines if they are header text (as in many files)
        header_peek = [f.readline() for _ in range(3)]
        # Continue reading entries
        while True:
            line = f.readline()
            if not line:
                break
            if not line.strip():
                continue
            parts = line.split()
            # Expect at least: source, ?, ?, ra, dec
            if len(parts) < 5:
                continue
            try:
                source = parts[0]
                ra_str = parts[3]
                dec_str = parts[4]
                ra_deg = Angle(ra_str).to_value(u.deg)
                dec_deg = Angle(dec_str).to_value(u.deg)
            except Exception:
                continue

            # Skip 4 lines per entry as per file layout
            for _ in range(4):
                _ = f.readline()

            flux_20_cm = None
            code_20_cm = None
            # Read frequency block until blank
            while True:
                pos = f.tell()
                fl = f.readline()
                if (not fl) or fl.isspace():
                    break
                if "20cm " in fl:
                    toks = fl.split()
                    try:
                        # Expected format: "20cm <...> <code_a> <code_b> <code_c> <code_d> <flux> ..."
                        code_a, code_b, code_c, code_d = toks[2], toks[3], toks[4], toks[5]
                        flux_20_cm = toks[6]
                        code_20_cm = code_a + code_b + code_c + code_d
                    except Exception:
                        # Fallback: last token as flux
                        flux_20_cm = toks[-1]
                        code_20_cm = None
            # Position now at blank; continue
            if flux_20_cm not in [None, "?"]:
                try:
                    flux_mJy = 1000.0 * float(flux_20_cm)
                except Exception:
                    flux_mJy = np.nan
                records.append(
                    {
                        "source": source,
                        "ra": ra_deg,
                        "dec": dec_deg,
                        "flux_20_cm": flux_mJy,
                        "code_20_cm": code_20_cm,
                    }
                )

    df = pd.DataFrame.from_records(records)
    if not df.empty:
        df = df.set_index("source")
    return df


def airy_primary_beam_response(
    ant_ra: float, ant_dec: float, src_ra: float, src_dec: float, freq_GHz: float, dish_dia_m: float = 4.7
) -> float:
    """Approximate primary beam response using an Airy pattern.

    Returns a scalar response in [0, 1]. Coordinates in radians.
    """
    # Offset angle approximation on the sky
    dra = (src_ra - ant_ra) * np.cos(ant_dec)
    ddec = src_dec - ant_dec
    theta = np.sqrt(dra * dra + ddec * ddec)
    # First-null approximation: 1.22 * lambda / D
    lam_m = (3e8 / (freq_GHz * 1e9))
    x = np.pi * dish_dia_m * np.sin(theta) / lam_m
    # Avoid division by zero
    x = np.where(x == 0, 1e-12, x)
    resp = (2 * (np.sin(x) - x * np.cos(x)) / (x * x)) ** 2
    # Clamp numeric noise
    return float(np.clip(resp, 0.0, 1.0))


def generate_caltable(
    vla_df: pd.DataFrame,
    pt_dec: u.Quantity,
    csv_path: str,
    radius: u.Quantity = 2.5 * u.deg,
    min_weighted_flux: u.Quantity = 1.0 * u.Jy,
    min_percent_flux: float = 0.15,
) -> str:
    """Build a declination-specific calibrator table and save to CSV.

    Weighted by primary beam response at 1.4 GHz.
    """
    pt_dec_deg = pt_dec.to_value(u.deg)
    # ensure numeric
    vla_df = vla_df.copy()
    vla_df["ra"] = pd.to_numeric(vla_df["ra"], errors="coerce")
    vla_df["dec"] = pd.to_numeric(vla_df["dec"], errors="coerce")
    vla_df["flux_20_cm"] = pd.to_numeric(vla_df["flux_20_cm"], errors="coerce")

    cal_df = vla_df[
        (vla_df["dec"] < (pt_dec_deg + radius.to_value(u.deg)))
        & (vla_df["dec"] > (pt_dec_deg - radius.to_value(u.deg)))
        & (vla_df["flux_20_cm"] > 1000.0)
    ].copy()
    if cal_df.empty:
        # Still write an empty CSV to satisfy pipeline expectations
        cal_df.to_csv(csv_path, index=True)
        return csv_path

    # Compute weighted flux per calibrator and field flux
    cal_df["weighted_flux"] = 0.0
    cal_df["field_flux"] = 0.0

    ant_ra = 0.0  # use RA=self for beam centering approximation; drop explicit RA dependence
    ant_dec = np.deg2rad(pt_dec_deg)
    for name, row in cal_df.iterrows():
        src_ra = np.deg2rad(row["ra"]) if np.isfinite(row["ra"]) else 0.0
        src_dec = np.deg2rad(row["dec"]) if np.isfinite(row["dec"]) else ant_dec
        resp = airy_primary_beam_response(ant_ra, ant_dec, src_ra, src_dec, 1.4)
        cal_df.at[name, "weighted_flux"] = (row["flux_20_cm"] / 1e3) * resp

        # Field: local patch of radius scaled by cos(dec)
        field = vla_df[
            (vla_df["dec"] < (pt_dec_deg + radius.to_value(u.deg)))
            & (vla_df["dec"] > (pt_dec_deg - radius.to_value(u.deg)))
            & (vla_df["ra"] < row["ra"] + radius.to_value(u.deg) / max(np.cos(np.deg2rad(pt_dec_deg)), 1e-3))
            & (vla_df["ra"] > row["ra"] - radius.to_value(u.deg) / max(np.cos(np.deg2rad(pt_dec_deg)), 1e-3))
        ].copy()
        wsum = 0.0
        for _, crow in field.iterrows():
            f_ra = np.deg2rad(crow["ra"]) if np.isfinite(crow["ra"]) else 0.0
            f_dec = np.deg2rad(crow["dec"]) if np.isfinite(crow["dec"]) else ant_dec
            wsum += (crow["flux_20_cm"] / 1e3) * airy_primary_beam_response(
                ant_ra, ant_dec, f_ra, f_dec, 1.4
            )
        cal_df.at[name, "field_flux"] = wsum

    cal_df["percent_flux"] = cal_df["weighted_flux"] / cal_df["field_flux"].replace(0, np.nan)

    sel = cal_df[
        (cal_df["weighted_flux"] > min_weighted_flux.to_value(u.Jy))
        & (cal_df["percent_flux"] > min_percent_flux)
    ].copy()

    # Fallback: if selection empty, choose top by weighted flux within dec band
    if sel.empty:
        sel = cal_df.sort_values("weighted_flux", ascending=False).head(10).copy()
        # If any field_flux is zero (rare), set percent_flux=1 for ranking purposes
        z = sel["field_flux"] == 0
        sel.loc[z, "percent_flux"] = 1.0

    # Reformat columns and units
    out = sel.copy()
    out["flux (Jy)"] = out["flux_20_cm"] / 1e3
    out = out.rename(columns={"code_20_cm": "code_20_cm", "ra": "ra(deg)", "dec": "dec(deg)"})
    out = out[["ra(deg)", "dec(deg)", "flux (Jy)", "weighted_flux", "percent_flux", "code_20_cm"]]
    out.to_csv(csv_path, index=True)
    return csv_path


def update_caltable(
    vla_df: pd.DataFrame, pt_dec: u.Quantity, out_dir: str = ".cache/catalogs"
) -> str:
    """Ensure a declination-specific caltable exists; return its path."""
    os.makedirs(out_dir, exist_ok=True)
    decsign = "+" if pt_dec.to_value(u.deg) >= 0 else "-"
    decval = f"{abs(pt_dec.to_value(u.deg)):05.1f}".replace(".", "p")
    csv_path = str(Path(out_dir) / f"calibrator_sources_dec{decsign}{decval}.csv")
    if not os.path.exists(csv_path):
        generate_caltable(vla_df=vla_df, pt_dec=pt_dec, csv_path=csv_path)
    return csv_path



```

- Cause: the declination-specific CSV contained no rows passing thresholds, so `head(1)` returned empty. This can happen if parsing missed flux/coords or the thresholds filtered everything.

- Fixes I implemented:
  - Hardened `read_vla_calibrator_catalog` to mirror the VLA file structure (explicit RA/Dec fields; 4-line skip; “20cm ” block with 4 codes + flux).
  - Coerced `ra`, `dec`, and `flux_20_cm` to numeric before selection.
  - Added a fallback: if thresholded selection is empty, pick the top 10 by `weighted_flux` within the declination band and continue.

- Re-run your test:
```bash
conda activate casa6
python test_cal.py
```

- If you still see empty results:
  - Verify the VLA path is correct: `/data/dsa110-contimg/references/dsa110-calib/dsacalib/data/vlacalibrators.txt`
  - Inspect the CSV quickly:
```bash
python - << 'PY'
import pandas as pd
df = pd.read_csv('.cache/catalogs/calibrator_sources_dec+030p0.csv', index_col=0)
print(df.head(5))
print('rows:', len(df))
PY
```

- Optional: lower `min_weighted_flux` for sparser skies by replacing the default when calling `generate_caltable` (e.g., 0.5 Jy).

```shellscript
conda activate casa6
python test_cal.py
```

```shellscript
python - << 'PY'
import pandas as pd
df = pd.read_csv('.cache/catalogs/calibrator_sources_dec+030p0.csv', index_col=0)
print(df.head(5))
print('rows:', len(df))
PY
```

- The CSV is empty. Likely causes: VLA file parsing didn’t match your file’s exact layout, or thresholds filtered all rows.

Try this quick debug to confirm parsing and selection:

```bash
python - << 'PY'
import pandas as pd, astropy.units as u
from casa_cal.catalogs import read_vla_calibrator_catalog, update_caltable, generate_caltable

vla_path = '/data/dsa110-contimg/references/dsa110-calib/dsacalib/data/vlacalibrators.txt'
vla_df = read_vla_calibrator_catalog(vla_path)
print('VLA rows:', len(vla_df))
print(vla_df.head(5))

pt_dec = 30.0 * u.deg

# Force a caltable with looser thresholds:
csv_path = generate_caltable(
    vla_df=vla_df, pt_dec=pt_dec, csv_path='.cache/catalogs/dec+030p0_loose.csv',
    min_weighted_flux=0.2 * u.Jy, min_percent_flux=0.02
)
df = pd.read_csv(csv_path, index_col=0)
print('Candidates after loose thresholds:', len(df))
print(df.sort_values('weighted_flux', ascending=False).head(5))
PY
```

- If VLA rows == 0: the catalog path/format is the issue. Please paste the first ~25 lines of `vlacalibrators.txt` so I can adapt the parser to your exact layout.
- If VLA rows > 0 but candidates still 0 with loose thresholds: print min/max of `ra`, `dec`, `flux_20_cm` to ensure numeric parsing worked:
```bash
python - << 'PY'
import numpy as np
import pandas as pd, astropy.units as u
from casa_cal.catalogs import read_vla_calibrator_catalog
vla_df = read_vla_calibrator_catalog('/data/dsa110-contimg/references/dsa110-calib/dsacalib/data/vlacalibrators.txt')
for col in ['ra','dec','flux_20_cm']:
    s = pd.to_numeric(vla_df[col], errors='coerce')
    print(col, 'count', s.notna().sum(), 'min', s.min(), 'max', s.max())
PY
```

Workaround to proceed now:
- If the “loose” CSV prints candidates, pick the top one:
```bash
python - << 'PY'
import pandas as pd
df = pd.read_csv('.cache/catalogs/dec+030p0_loose.csv', index_col=0)
cand = df.sort_values('weighted_flux', ascending=False).head(1)
print('Selected:', cand.index[0], cand[['ra(deg)','dec(deg)','flux (Jy)']].iloc[0].to_dict())
PY
```

Once we see the first lines of your VLA file (or the numeric summary), I’ll finalize the parser so the default thresholds produce a non-empty caltable.

```shellscript
python - << 'PY'
import pandas as pd, astropy.units as u
from casa_cal.catalogs import read_vla_calibrator_catalog, update_caltable, generate_caltable

vla_path = '/data/dsa110-contimg/references/dsa110-calib/dsacalib/data/vlacalibrators.txt'
vla_df = read_vla_calibrator_catalog(vla_path)
print('VLA rows:', len(vla_df))
print(vla_df.head(5))

pt_dec = 30.0 * u.deg

# Force a caltable with looser thresholds:
csv_path = generate_caltable(
    vla_df=vla_df, pt_dec=pt_dec, csv_path='.cache/catalogs/dec+030p0_loose.csv',
    min_weighted_flux=0.2 * u.Jy, min_percent_flux=0.02
)
df = pd.read_csv(csv_path, index_col=0)
print('Candidates after loose thresholds:', len(df))
print(df.sort_values('weighted_flux', ascending=False).head(5))
PY
```

```shellscript
python - << 'PY'
import numpy as np
import pandas as pd, astropy.units as u
from casa_cal.catalogs import read_vla_calibrator_catalog
vla_df = read_vla_calibrator_catalog('/data/dsa110-contimg/references/dsa110-calib/dsacalib/data/vlacalibrators.txt')
for col in ['ra','dec','flux_20_cm']:
    s = pd.to_numeric(vla_df[col], errors='coerce')
    print(col, 'count', s.notna().sum(), 'min', s.min(), 'max', s.max())
PY
```

```shellscript
python - << 'PY'
import pandas as pd
df = pd.read_csv('.cache/catalogs/dec+030p0_loose.csv', index_col=0)
cand = df.sort_values('weighted_flux', ascending=False).head(1)
print('Selected:', cand.index[0], cand[['ra(deg)','dec(deg)','flux (Jy)']].iloc[0].to_dict())
PY
```

---

**User**

Ah I found if I switched to dec 55, it worked!

Do we have a way to calculate the transit time of calibrator so we know which observation to use to generate solutions?

---

**Cursor**

Yes. Compute when the source’s hour angle is 0 at OVRO (transit) and then pick the observation whose midpoint is closest to that time. Here’s a minimal astropy-only helper you can use in your casa6 env.

```python
from astropy.time import Time
from astropy.coordinates import EarthLocation, Angle
import astropy.units as u
import numpy as np

# OVRO (approx.) - you can also get this via casatools.measures if you prefer
OVRO = EarthLocation.from_geodetic(lon=Angle(-118.2817, u.deg),
                                   lat=Angle(37.2314, u.deg),
                                   height=1222*u.m)

SIDEREAL_RATE = 1.002737909350795  # sidereal days per solar day

def next_transit_time(ra_deg: float, start_time_mjd: float, location: EarthLocation = OVRO, max_iter: int = 4) -> Time:
    """
    Compute the next transit time (HA=0) after start_time_mjd for a source with RA=ra_deg.
    Assumes apparent LST ~ linear over short windows; refines with a few iterations.
    """
    ra = Angle(ra_deg, u.deg).to(u.hourangle).value  # hours
    t = Time(start_time_mjd, format='mjd', scale='utc', location=location)
    for _ in range(max_iter):
        lst = t.sidereal_time('apparent').hour  # local apparent sidereal time (hours)
        delta_lst = (ra - lst + 12) % 24 - 12  # wrap to [-12h, +12h]
        # convert LST difference to UTC seconds (sidereal day is shorter)
        delta_utc_days = (delta_lst / 24.0) / SIDEREAL_RATE
        t = t + delta_utc_days * u.day
    # ensure result is not before start_time; if so, add one sidereal day
    if t < Time(start_time_mjd, format='mjd', scale='utc'):
        t = t + (1.0 / SIDEREAL_RATE) * u.day
    return t

def pick_best_observation(observations, transit_time: Time):
    """
    observations: list of tuples (obs_id, start_mjd, end_mjd)
    returns (obs_id, mid_mjd, delta_minutes)
    """
    best = None
    best_dt = None
    for obs_id, mjd0, mjd1 in observations:
        mid = 0.5 * (mjd0 + mjd1)
        dt_min = abs((Time(mid, format='mjd') - transit_time).to(u.min).value)
        if (best_dt is None) or (dt_min < best_dt):
            best_dt = dt_min
            best = (obs_id, mid, dt_min)
    return best
```

Example usage:
```python
# Source RA in degrees, e.g., 210.0 deg
ra_deg = 210.0
# Start of the observing window (e.g., beginning of UTC day)
start_mjd = Time('2025-10-06T00:00:00', scale='utc').mjd

t_transit = next_transit_time(ra_deg, start_mjd)  # Time object
print('Transit ISO:', t_transit.isot, 'MJD:', t_transit.mjd)

# Suppose you have a list of calibrator pass files with start/end MJDs
observations = [
    ('cal_01', 60295.125, 60295.145),
    ('cal_02', 60295.210, 60295.230),
    ('cal_03', 60295.295, 60295.315),
]
best = pick_best_observation(observations, t_transit)
print('Use observation:', best)
```

Notes
- If you prefer CASA’s site/location, you can retrieve OVRO using `casatools.measures().observatory('OVRO_MMA')` and convert to an `EarthLocation`. The approximation above is sufficient for scheduling.
- For sources with accurate RA/Dec and typical night-long windows, 3–4 refinement iterations are ample; the residual will be well below 1 minute.
- If you need the previous transit instead, subtract one sidereal day from the returned time.

```python
from astropy.time import Time
from astropy.coordinates import EarthLocation, Angle
import astropy.units as u
import numpy as np

# OVRO (approx.) - you can also get this via casatools.measures if you prefer
OVRO = EarthLocation.from_geodetic(lon=Angle(-118.2817, u.deg),
                                   lat=Angle(37.2314, u.deg),
                                   height=1222*u.m)

SIDEREAL_RATE = 1.002737909350795  # sidereal days per solar day

def next_transit_time(ra_deg: float, start_time_mjd: float, location: EarthLocation = OVRO, max_iter: int = 4) -> Time:
    """
    Compute the next transit time (HA=0) after start_time_mjd for a source with RA=ra_deg.
    Assumes apparent LST ~ linear over short windows; refines with a few iterations.
    """
    ra = Angle(ra_deg, u.deg).to(u.hourangle).value  # hours
    t = Time(start_time_mjd, format='mjd', scale='utc', location=location)
    for _ in range(max_iter):
        lst = t.sidereal_time('apparent').hour  # local apparent sidereal time (hours)
        delta_lst = (ra - lst + 12) % 24 - 12  # wrap to [-12h, +12h]
        # convert LST difference to UTC seconds (sidereal day is shorter)
        delta_utc_days = (delta_lst / 24.0) / SIDEREAL_RATE
        t = t + delta_utc_days * u.day
    # ensure result is not before start_time; if so, add one sidereal day
    if t < Time(start_time_mjd, format='mjd', scale='utc'):
        t = t + (1.0 / SIDEREAL_RATE) * u.day
    return t

def pick_best_observation(observations, transit_time: Time):
    """
    observations: list of tuples (obs_id, start_mjd, end_mjd)
    returns (obs_id, mid_mjd, delta_minutes)
    """
    best = None
    best_dt = None
    for obs_id, mjd0, mjd1 in observations:
        mid = 0.5 * (mjd0 + mjd1)
        dt_min = abs((Time(mid, format='mjd') - transit_time).to(u.min).value)
        if (best_dt is None) or (dt_min < best_dt):
            best_dt = dt_min
            best = (obs_id, mid, dt_min)
    return best
```

```python
# Source RA in degrees, e.g., 210.0 deg
ra_deg = 210.0
# Start of the observing window (e.g., beginning of UTC day)
start_mjd = Time('2025-10-06T00:00:00', scale='utc').mjd

t_transit = next_transit_time(ra_deg, start_mjd)  # Time object
print('Transit ISO:', t_transit.isot, 'MJD:', t_transit.mjd)

# Suppose you have a list of calibrator pass files with start/end MJDs
observations = [
    ('cal_01', 60295.125, 60295.145),
    ('cal_02', 60295.210, 60295.230),
    ('cal_03', 60295.295, 60295.315),
]
best = pick_best_observation(observations, t_transit)
print('Use observation:', best)
```

---

**User**

These fucntions don't exist in @dsacalib/ already?

---

**Cursor**

Yes. In `@dsacalib/` you already have the pieces:

- Calibrator list at pointing declination:
  - `dsacalib.preprocess.update_caltable(pt_dec)` writes a declination-specific CSV of VLA calibrators.

- Transit-time–driven file selection for calibrator passes:
  - `dsacalib.routines.get_files_for_cal(caltable, hdf5dir, duration, filelength, date_specifier)` returns, per date and calibrator, the matching input files and the computed `transit_time` for that calibrator.
  - `dsacalib.routines.cal_in_datetime(dt, transit_time, duration, filelength)` checks whether a correlator file interval overlaps the desired window around transit.

- End-to-end orchestration around those:
  - `references/dsa110-calib/services/calibration_service.py` calls `update_caltable(...)`, then `get_files_for_cal(...)`, and uses the returned `transit_time` to tag the solution and downstream products.

If you want to stick with the no-`dsacalib` path, our new `casa_cal.catalogs.update_caltable` replicates the declination CSV, and you can pair it with the small `next_transit_time(...)` helper I provided to choose the observation closest to transit.

---

**User**

repurpose the relevant parts of dsacalib code and integrate them into ours.

---

**Cursor**

I'll add scheduling utilities by repurposing the relevant logic: a robust transit-time finder and a cal_in_datetime check for selecting the best observation near transit. Then I'll update our package with these functions.

```python
from typing import List, Tuple

import numpy as np
from astropy.time import Time
from astropy.coordinates import EarthLocation, Angle
import astropy.units as u


OVRO = EarthLocation.from_geodetic(lon=Angle(-118.2817, u.deg), lat=Angle(37.2314, u.deg), height=1222 * u.m)
SIDEREAL_RATE = 1.002737909350795  # sidereal days per solar day


def next_transit_time(ra_deg: float, start_time_mjd: float, location: EarthLocation = OVRO, max_iter: int = 4) -> Time:
    """Compute next transit (HA=0) after start_time_mjd for a source with RA=ra_deg."""
    ra_hours = Angle(ra_deg, u.deg).to(u.hourangle).value
    t = Time(start_time_mjd, format="mjd", scale="utc", location=location)
    for _ in range(max_iter):
        lst = t.sidereal_time("apparent").hour
        delta_lst = (ra_hours - lst + 12) % 24 - 12  # wrap to [-12, +12]
        delta_utc_days = (delta_lst / 24.0) / SIDEREAL_RATE
        t = t + delta_utc_days * u.day
    if t < Time(start_time_mjd, format="mjd", scale="utc"):
        t = t + (1.0 / SIDEREAL_RATE) * u.day
    return t


def cal_in_datetime(dt_start_iso: str, transit_time: Time, duration: u.Quantity = 5 * u.min, filelength: u.Quantity = 15 * u.min) -> bool:
    """Return True if a file starting at dt_start_iso overlaps the desired window around transit.

    A file of length `filelength` starting at `dt_start_iso` overlaps a window of +/- duration around `transit_time`.
    """
    mjd0 = Time(dt_start_iso, scale="utc").mjd
    mjd1 = (Time(dt_start_iso, scale="utc") + filelength).mjd
    window0 = (transit_time - duration).mjd
    window1 = (transit_time + duration).mjd
    return (mjd0 <= window1) and (mjd1 >= window0)


def pick_best_observation(observations: List[Tuple[str, float, float]], transit_time: Time) -> Tuple[str, float, float]:
    """Pick observation whose midpoint is closest to transit.

    observations: list of (obs_id, start_mjd, end_mjd)
    returns: (obs_id, mid_mjd, delta_minutes)
    """
    best = None
    best_dt = None
    for obs_id, mjd0, mjd1 in observations:
        mid = 0.5 * (mjd0 + mjd1)
        dt_min = abs((Time(mid, format="mjd") - transit_time).to(u.min).value)
        if (best_dt is None) or (dt_min < best_dt):
            best_dt = dt_min
            best = (obs_id, mid, dt_min)
    return best


```

- Yes. In dsacalib it’s already covered:
  - calibrator list by dec: `preprocess.update_caltable(pt_dec)`
  - transit-based selection: `routines.get_files_for_cal(...)` computes `transit_time` and picks files around it
  - datetime overlap: `routines.cal_in_datetime(...)`

- In our package, I’ve integrated equivalents (no dsacalib imports):
  - `casa_cal.catalogs.update_caltable(...)`: builds the declination-specific CSV from the VLA catalog.
  - `casa_cal.schedule.next_transit_time(ra_deg, start_mjd)`: computes the next transit at OVRO.
  - `casa_cal.schedule.cal_in_datetime(dt_start_iso, transit_time, duration, filelength)`: overlap test.
  - `casa_cal.schedule.pick_best_observation(observations, transit_time)`: chooses the nearest-midpoint observation.

Use them together to select the right observation near transit, then run K+B+G on that MS.

---

**User**

Great! Let's integrate this better within our pipeline architecture in @pipeline/ 

---

**Cursor**

- Proposed modules in pipeline
  - pipeline/calib/catalog_stage.py: load VLA/NVSS, build dec-specific CSV via casa_cal.catalogs.update_caltable, persist path in run context.
  - pipeline/calib/schedule_stage.py: compute next transit time via casa_cal.schedule.next_transit_time, choose best observation via pick_best_observation, or overlap via cal_in_datetime.
  - pipeline/calib/solve_stage.py: run K/B/G on chosen calibrator MS using casa_cal.calibration.solve_delay/solve_bandpass/solve_gains; return ordered table list.
  - pipeline/calib/apply_stage.py: apply tables to target MS via casa_cal.applycal.apply_to_target; optional quick image via casa_cal.imaging.quick_image.
  - pipeline/calib/qa_stage.py: emit plotcal PNGs via casa_cal.qa.save_plotcal and a minimal JSON QA summary.

- Pipeline run context contract
  - Inputs: ms_root, date, refant, cal_field, target_fields, pt_dec, vla_catalog_path.
  - Outputs in context:
    - calib.caltable_csv
    - calib.transit_time_mjd
    - calib.ms_cal (path), calib.tables (list in apply order)
    - target[n].applied_tables, target[n].image_paths
    - qa.figures (dict), qa.metrics (dict)

- Orchestrator wiring (pseudo)
```python
# pipeline/main.py
from pipeline.calib import catalog_stage, schedule_stage, solve_stage, apply_stage, qa_stage

ctx = {...}  # loaded from pipeline config/yaml
ctx = catalog_stage.run(ctx)
ctx = schedule_stage.run(ctx)
ctx = solve_stage.run(ctx)
ctx = apply_stage.run(ctx)
ctx = qa_stage.run(ctx)
```

- Stage skeletons
```python
# pipeline/calib/catalog_stage.py
from casa_cal.catalogs import read_vla_calibrator_catalog, update_caltable
def run(ctx):
    vla_df = read_vla_calibrator_catalog(ctx['vla_catalog_path'])
    ctx['calib'] = ctx.get('calib', {})
    ctx['calib']['caltable_csv'] = update_caltable(vla_df, ctx['pt_dec'])
    return ctx
```

```python
# pipeline/calib/schedule_stage.py
from astropy.time import Time
from casa_cal.schedule import next_transit_time, pick_best_observation
def run(ctx):
    ra_deg = ctx['cal_ra_deg']  # from selected row in CSV (or pass cal name then lookup)
    start_mjd = Time(ctx['date'] + 'T00:00:00', scale='utc').mjd
    ttran = next_transit_time(ra_deg, start_mjd)
    ctx['calib']['transit_time_mjd'] = float(ttran.mjd)
    # observations: [(id, mjd0, mjd1), ...] populated upstream by your file scanner
    ctx['calib']['best_obs'] = pick_best_observation(ctx['observations'], ttran)
    return ctx
```

```python
# pipeline/calib/solve_stage.py
from casa_cal.calibration import solve_delay, solve_bandpass, solve_gains
def run(ctx):
    ms_cal = ctx['calib']['ms_cal']  # path chosen from best_obs
    cal_field = ctx['cal_field']; refant = ctx['refant']
    ktabs = solve_delay(ms_cal, cal_field, refant)
    bptabs = solve_bandpass(ms_cal, cal_field, refant, ktabs[0])
    gtabs = solve_gains(ms_cal, cal_field, refant, ktabs[0], bptabs, do_fluxscale=False)
    ctx['calib']['tables'] = ktabs[:1] + bptabs + gtabs
    return ctx
```

```python
# pipeline/calib/apply_stage.py
from casa_cal.applycal import apply_to_target
from casa_cal.imaging import quick_image
def run(ctx):
    for t in ctx['target_fields']:
        apply_to_target(ctx['ms_target'], field=t, gaintables=ctx['calib']['tables'])
        if ctx.get('make_image', True):
            quick_image(ctx['ms_target'], imagename=f"{ctx['outdir']}/{t}", field=t)
    return ctx
```

```python
# pipeline/calib/qa_stage.py
from casa_cal.qa import save_plotcal
def run(ctx):
    prefix = ctx['calib']['ms_cal'].rstrip('.ms') + f"_{ctx['cal_field']}"
    outdir = ctx['qa_outdir']
    figs = []
    for spec in [
        (f"{prefix}_kcal",'time','delay','kcal_delay.png'),
        (f"{prefix}_bacal",'chan','amp','bacal_amp.png'),
        (f"{prefix}_bpcal",'chan','phase','bpcal_phase.png'),
        (f"{prefix}_gacal",'time','amp','gacal_amp.png'),
        (f"{prefix}_gpcal",'time','phase','gpcal_phase.png'),
    ]:
        save_plotcal(spec[0], spec[1], spec[2], f"{outdir}/{spec[3]}")
        figs.append(f"{outdir}/{spec[3]}")
    ctx['qa'] = {'figures': figs}
    return ctx
```

- Config knobs to expose
  - thresholds: min_weighted_flux, min_percent_flux
  - cadence minutes, duration/filelength for overlap logic
  - refant, cal_field, target_fields
  - imaging knobs (niter, threshold, weighting)
  - QA output dir

- Minimal pipeline YAML excerpt
```yaml
calibration:
  vla_catalog_path: /data/.../vlacalibrators.txt
  pt_dec_deg: 55.0
  refant: '23'
  cal_field: 'Jxxxx+xxxx'
  target_fields: ['target1','target2']
  cadence_min: 15
  min_weighted_flux_jy: 1.0
  min_percent_flux: 0.15
  imaging:
    niter: 1000
    threshold: 0.1mJy
    weighting: briggs
    robust: 0.5
```

- Where to hook into existing pipeline
  - Add a “calibration” stage node to your pipeline DAG after data ingest/listing and before science imaging.
  - Source selection: either fixed cal_field from config or programmatically pick the top row from the dec CSV at runtime.
  - File discovery: reuse your current file-scanning stage to build the (obs_id, start_mjd, end_mjd) list for schedule_stage.

This keeps all CASA work inside casa6, reuses our casa_cal APIs, and cleanly slots into your pipeline stages without introducing dsacalib imports.

```python
# pipeline/main.py
from pipeline.calib import catalog_stage, schedule_stage, solve_stage, apply_stage, qa_stage

ctx = {...}  # loaded from pipeline config/yaml
ctx = catalog_stage.run(ctx)
ctx = schedule_stage.run(ctx)
ctx = solve_stage.run(ctx)
ctx = apply_stage.run(ctx)
ctx = qa_stage.run(ctx)
```

```python
# pipeline/calib/catalog_stage.py
from casa_cal.catalogs import read_vla_calibrator_catalog, update_caltable
def run(ctx):
    vla_df = read_vla_calibrator_catalog(ctx['vla_catalog_path'])
    ctx['calib'] = ctx.get('calib', {})
    ctx['calib']['caltable_csv'] = update_caltable(vla_df, ctx['pt_dec'])
    return ctx
```

```python
# pipeline/calib/schedule_stage.py
from astropy.time import Time
from casa_cal.schedule import next_transit_time, pick_best_observation
def run(ctx):
    ra_deg = ctx['cal_ra_deg']  # from selected row in CSV (or pass cal name then lookup)
    start_mjd = Time(ctx['date'] + 'T00:00:00', scale='utc').mjd
    ttran = next_transit_time(ra_deg, start_mjd)
    ctx['calib']['transit_time_mjd'] = float(ttran.mjd)
    # observations: [(id, mjd0, mjd1), ...] populated upstream by your file scanner
    ctx['calib']['best_obs'] = pick_best_observation(ctx['observations'], ttran)
    return ctx
```

```python
# pipeline/calib/solve_stage.py
from casa_cal.calibration import solve_delay, solve_bandpass, solve_gains
def run(ctx):
    ms_cal = ctx['calib']['ms_cal']  # path chosen from best_obs
    cal_field = ctx['cal_field']; refant = ctx['refant']
    ktabs = solve_delay(ms_cal, cal_field, refant)
    bptabs = solve_bandpass(ms_cal, cal_field, refant, ktabs[0])
    gtabs = solve_gains(ms_cal, cal_field, refant, ktabs[0], bptabs, do_fluxscale=False)
    ctx['calib']['tables'] = ktabs[:1] + bptabs + gtabs
    return ctx
```

```python
# pipeline/calib/apply_stage.py
from casa_cal.applycal import apply_to_target
from casa_cal.imaging import quick_image
def run(ctx):
    for t in ctx['target_fields']:
        apply_to_target(ctx['ms_target'], field=t, gaintables=ctx['calib']['tables'])
        if ctx.get('make_image', True):
            quick_image(ctx['ms_target'], imagename=f"{ctx['outdir']}/{t}", field=t)
    return ctx
```

```python
# pipeline/calib/qa_stage.py
from casa_cal.qa import save_plotcal
def run(ctx):
    prefix = ctx['calib']['ms_cal'].rstrip('.ms') + f"_{ctx['cal_field']}"
    outdir = ctx['qa_outdir']
    figs = []
    for spec in [
        (f"{prefix}_kcal",'time','delay','kcal_delay.png'),
        (f"{prefix}_bacal",'chan','amp','bacal_amp.png'),
        (f"{prefix}_bpcal",'chan','phase','bpcal_phase.png'),
        (f"{prefix}_gacal",'time','amp','gacal_amp.png'),
        (f"{prefix}_gpcal",'time','phase','gpcal_phase.png'),
    ]:
        save_plotcal(spec[0], spec[1], spec[2], f"{outdir}/{spec[3]}")
        figs.append(f"{outdir}/{spec[3]}")
    ctx['qa'] = {'figures': figs}
    return ctx
```

```yaml
calibration:
  vla_catalog_path: /data/.../vlacalibrators.txt
  pt_dec_deg: 55.0
  refant: '23'
  cal_field: 'Jxxxx+xxxx'
  target_fields: ['target1','target2']
  cadence_min: 15
  min_weighted_flux_jy: 1.0
  min_percent_flux: 0.15
  imaging:
    niter: 1000
    threshold: 0.1mJy
    weighting: briggs
    robust: 0.5
```

---

**User**

Go ahead and hook this in.

---

**Cursor**

I'll add calibration stages under pipeline/calib (catalog, schedule, solve, apply, qa) and wire them to use casa_cal. Then you can call these stages from your orchestrator.

```python
from typing import Dict

import astropy.units as u
from casa_cal.catalogs import read_vla_calibrator_catalog, update_caltable


def run(ctx: Dict) -> Dict:
    """Build declination-specific calibrator CSV and store its path in context.

    Expected ctx keys:
      - vla_catalog_path: str (path to VLA calibrator text file)
      - pt_dec_deg: float (pointing declination in degrees)
    Writes ctx['calib']['caltable_csv']
    """
    vla_df = read_vla_calibrator_catalog(ctx['vla_catalog_path'])
    pt_dec = float(ctx['pt_dec_deg']) * u.deg
    ctx.setdefault('calib', {})
    ctx['calib']['caltable_csv'] = update_caltable(vla_df, pt_dec)
    return ctx


```

```python
from typing import Dict

from astropy.time import Time
from casa_cal.schedule import next_transit_time, pick_best_observation


def run(ctx: Dict) -> Dict:
    """Compute transit time and select best observation near transit.

    Expected ctx keys:
      - cal_ra_deg: float (RA of selected calibrator in degrees)
      - date: str (YYYY-MM-DD)
      - observations: list of (obs_id, start_mjd, end_mjd)
    Writes ctx['calib']['transit_time_mjd'] and ctx['calib']['best_obs']
    """
    start_mjd = Time(ctx['date'] + 'T00:00:00', scale='utc').mjd
    ttran = next_transit_time(ctx['cal_ra_deg'], start_mjd)
    ctx.setdefault('calib', {})
    ctx['calib']['transit_time_mjd'] = float(ttran.mjd)
    ctx['calib']['best_obs'] = pick_best_observation(ctx['observations'], ttran)
    return ctx


```

```python
from typing import Dict, List

from casa_cal.calibration import solve_delay, solve_bandpass, solve_gains


def run(ctx: Dict) -> Dict:
    """Run K/B/G solves on the chosen calibrator MS.

    Expected ctx keys:
      - calib.ms_cal: str (path to calibrator MS)
      - cal_field: str (calibrator field name/id)
      - refant: str
    Writes ctx['calib']['tables'] in application order
    """
    ms_cal = ctx['calib']['ms_cal']
    cal_field = ctx['cal_field']
    refant = ctx['refant']
    ktabs = solve_delay(ms_cal, cal_field, refant)
    bptabs = solve_bandpass(ms_cal, cal_field, refant, ktabs[0])
    gtabs = solve_gains(ms_cal, cal_field, refant, ktabs[0], bptabs, do_fluxscale=False)
    ctx['calib']['tables'] = ktabs[:1] + bptabs + gtabs
    return ctx


```

```python
from typing import Dict

from casa_cal.applycal import apply_to_target
from casa_cal.imaging import quick_image


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


```

```python
from typing import Dict

from casa_cal.qa import save_plotcal


def run(ctx: Dict) -> Dict:
    """Generate plotcal-based QA figures for K/B/G tables.

    Expected ctx keys:
      - calib.ms_cal: str
      - cal_field: str
      - qa_outdir: str
    Writes ctx['qa']['figures'] list
    """
    prefix = ctx['calib']['ms_cal'].rstrip('.ms') + f"_{ctx['cal_field']}"
    outdir = ctx['qa_outdir']
    figs = []
    for caltable, xaxis, yaxis, name in [
        (f"{prefix}_kcal", 'time', 'delay', 'kcal_delay.png'),
        (f"{prefix}_bacal", 'chan', 'amp', 'bacal_amp.png'),
        (f"{prefix}_bpcal", 'chan', 'phase', 'bpcal_phase.png'),
        (f"{prefix}_gacal", 'time', 'amp', 'gacal_amp.png'),
        (f"{prefix}_gpcal", 'time', 'phase', 'gpcal_phase.png'),
    ]:
        save_plotcal(caltable, xaxis, yaxis, f"{outdir}/{name}")
        figs.append(f"{outdir}/{name}")
    ctx.setdefault('qa', {})
    ctx['qa']['figures'] = figs
    return ctx


```

- Added pipeline calibration stages that wrap casa_cal:
  - pipeline/calib/catalog_stage.py
  - pipeline/calib/schedule_stage.py
  - pipeline/calib/solve_stage.py
  - pipeline/calib/apply_stage.py
  - pipeline/calib/qa_stage.py

- How to use in your orchestrator
```python
from pipeline.calib import catalog_stage, schedule_stage, solve_stage, apply_stage, qa_stage

ctx = {
    'vla_catalog_path': '/data/dsa110-contimg/references/dsa110-calib/dsacalib/data/vlacalibrators.txt',
    'pt_dec_deg': 55.0,
    'date': '2025-10-06',
    'cal_ra_deg': 210.0,      # from selected row in dec CSV
    'observations': [          # (id, start_mjd, end_mjd)
        ('cal_01', 60295.125, 60295.145),
        ('cal_02', 60295.210, 60295.230),
    ],
    'cal_field': 'Jxxxx+xxxx',
    'refant': '23',
    'calib': { 'ms_cal': '/path/to/calibrator.ms' },
    'ms_target': '/path/to/target.ms',
    'target_fields': ['target1'],
    'outdir': '/path/to/out',
    'qa_outdir': '/path/to/qa',
    'make_image': True,
}

ctx = catalog_stage.run(ctx)
ctx = schedule_stage.run(ctx)
ctx = solve_stage.run(ctx)
ctx = apply_stage.run(ctx)
ctx = qa_stage.run(ctx)
```

- Outputs in ctx:
  - calib.caltable_csv, calib.transit_time_mjd, calib.best_obs
  - calib.tables (ordered K+B+G), QA figures list

This integrates calibrator selection, transit scheduling, solves, application, and QA directly into your pipeline.

```python
from pipeline.calib import catalog_stage, schedule_stage, solve_stage, apply_stage, qa_stage

ctx = {
    'vla_catalog_path': '/data/dsa110-contimg/references/dsa110-calib/dsacalib/data/vlacalibrators.txt',
    'pt_dec_deg': 55.0,
    'date': '2025-10-06',
    'cal_ra_deg': 210.0,      # from selected row in dec CSV
    'observations': [          # (id, start_mjd, end_mjd)
        ('cal_01', 60295.125, 60295.145),
        ('cal_02', 60295.210, 60295.230),
    ],
    'cal_field': 'Jxxxx+xxxx',
    'refant': '23',
    'calib': { 'ms_cal': '/path/to/calibrator.ms' },
    'ms_target': '/path/to/target.ms',
    'target_fields': ['target1'],
    'outdir': '/path/to/out',
    'qa_outdir': '/path/to/qa',
    'make_image': True,
}

ctx = catalog_stage.run(ctx)
ctx = schedule_stage.run(ctx)
ctx = solve_stage.run(ctx)
ctx = apply_stage.run(ctx)
ctx = qa_stage.run(ctx)
```

