#!/usr/bin/env python3
import argparse
from core.calibration.skymodel_builder import SkyModelBuilder


def main():
    p = argparse.ArgumentParser(description='Build CASA component list (.cl) for a calibrator point source.')
    p.add_argument('--name', type=str, required=True, help='Source name')
    p.add_argument('--ra', type=float, required=True, help='RA deg (ICRS)')
    p.add_argument('--dec', type=float, required=True, help='Dec deg (ICRS)')
    p.add_argument('--flux', type=float, required=True, help='Flux (Jy) at reference frequency')
    p.add_argument('--ref-freq', type=float, default=1.4e9, help='Reference frequency in Hz')
    p.add_argument('--out', type=str, default=None, help='Output base name (defaults to source name)')
    args = p.parse_args()

    builder = SkyModelBuilder()
    sm = builder.build_point_sources(
        names=[args.name],
        ras_deg=[args.ra],
        decs_deg=[args.dec],
        fluxes_jy=[args.flux],
        ref_freq_hz=args.ref_freq,
    )
    out_base = args.out or args.name
    path = builder.write_casa_component_list(sm, out_base)
    print(path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
