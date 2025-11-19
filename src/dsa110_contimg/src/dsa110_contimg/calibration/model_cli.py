#!/opt/miniforge/envs/casa6/bin/python
"""
CLI to inject a calibrator point-source model into an MS using a VLA CSV.

Example:
  python -m dsa110_contimg.calibration.model_cli inject \
    --ms /data/pipeline/raw_cal/0834+555_2025-10-03T15:15:57.ms \
    --catalog /data/dsa110-contimg/references/dsa110-contimg-main-legacy/data/catalogs/vla_calibrators_parsed.csv \
    --name 0834+555
"""

import argparse
from typing import Optional

import numpy as np

from .catalogs import read_vla_parsed_catalog_with_flux
from .model import write_point_model_with_ft


def cmd_inject(args: argparse.Namespace) -> int:
    df = read_vla_parsed_catalog_with_flux(args.catalog, band="20cm")
    name = args.name.strip()
    if name not in df.index:
        print(f"Calibrator '{name}' not found in catalog")
        return 2
    row = df.loc[name]
    ra_deg = float(row["ra_deg"])
    dec_deg = float(row["dec_deg"])
    flux_jy = float(row.get("flux_jy", np.nan))
    if not np.isfinite(flux_jy) or flux_jy <= 0:
        flux_jy = float(args.flux) if args.flux is not None else 8.0
    # Spectral index if present
    sidx: Optional[float] = None
    reffreq_hz: float = float(args.reffreq) if args.reffreq is not None else 1.4e9
    if "sidx" in row and np.isfinite(row["sidx"]):
        sidx = float(row["sidx"])
        if "sidx_f0_hz" in row and np.isfinite(row["sidx_f0_hz"]):
            reffreq_hz = float(row["sidx_f0_hz"])
    print(
        f"Writing MODEL_DATA for {name} @ ra={ra_deg:.6f} dec={dec_deg:.6f} flux={flux_jy:.3f} Jy"
    )
    try:
        write_point_model_with_ft(
            args.ms,
            ra_deg,
            dec_deg,
            flux_jy,
            reffreq_hz=reffreq_hz,
            spectral_index=sidx,
        )
    except Exception as e:
        print(f"Model write failed: {e}")
        return 3
    print("Done.")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Inject calibrator MODEL_DATA into an MS")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("inject", help="Inject a calibrator point model via CASA ft")
    sp.add_argument("--ms", required=True, help="Path to Measurement Set")
    sp.add_argument(
        "--catalog", required=True, help="VLA parsed CSV (with RA/Dec and FLUX_JY)"
    )
    sp.add_argument(
        "--name", required=True, help="Calibrator J2000 name, e.g. 0834+555"
    )
    sp.add_argument("--flux", type=float, help="Override flux (Jy) if missing in CSV")
    sp.add_argument(
        "--reffreq",
        type=float,
        help="Reference frequency (Hz) for the component (default 1.4e9)",
    )
    sp.set_defaults(func=cmd_inject)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
