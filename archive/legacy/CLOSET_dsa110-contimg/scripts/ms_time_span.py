#!/usr/bin/env python3
import sys
from pathlib import Path

import numpy as np
from astropy.time import Time
from pyuvdata import UVData


def main() -> int:
    # Pick newest MS under data/ms
    ms_dir = Path('data/ms')
    ms_list = sorted(ms_dir.glob('*.ms'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not ms_list:
        print('No MS found in data/ms')
        return 2

    ms_path = str(ms_list[0])
    uv = UVData()
    uv.read_ms(ms_path, ignore_single_chan=True)

    tmin_jd = float(np.min(uv.time_array))
    tmax_jd = float(np.max(uv.time_array))
    span_sec = (tmax_jd - tmin_jd) * 86400.0

    print(f"MS: {ms_path}")
    print(f"Start (UTC): {Time(tmin_jd, format='jd').isot}")
    print(f"End   (UTC): {Time(tmax_jd, format='jd').isot}")
    print(f"Span: {span_sec:.2f} s ({span_sec/60.0:.2f} min)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


