## Build a CASA Voltage Pattern (VP) table from the DSA-110 H5 beam

This guide documents exactly how we generate a CASA VP table from the DSA-110 beam model HDF5, so anyone can reproduce it.

### Inputs
- H5 beam file (complex E-field Jones samples):
  - `freq_Hz` (nfreq)
  - `theta_pts` (ntheta), `phi_pts` (nphi)
  - `X_pol_Efields/ephi`, `X_pol_Efields/etheta` (nfreq, ntheta, nphi)
  - `Y-pol_Efields/ephi`, `Y-pol_Efields/etheta` (nfreq, ntheta, nphi)
- Optional: preferred frequency slice (Hz)
- Optional: telescope name (e.g., `DSA_110`)

### Mapping (E-Jones → feed Jones)
- Jxx = X.ephi
- Jxy = −X.etheta
- Jyx = Y.ephi
- Jyy = −Y.etheta

### Coordinate system (csys) used
- Direction: `AZEL` (Azimuth, Elevation)
- Units: degrees for direction axes
- Stokes axis: `XX, XY, YX, YY`
- Spectral axis: single channel (frequency dependence is ignored by VP image)
- Reference pixel: image center
- Reference value: (0°, 0°) boresight
- Increments: derived from grid spacing
- Note: `phi_pts` maps to Az; Elevation is computed from polar angle as `El = 90° − theta`

### Jones image shape
- CASA complex image with shape `(ny, nx, 4, 1)` ordered as `(YY index last)`:
  - pol axis order: `XX, XY, YX, YY`
  - one spectral channel

### Implementation
We expose a CLI that wraps the builder in `dsa110_contimg`:

```bash
python -m dsa110_contimg.beam.cli \
  --h5 /stage/dsa110-contimg/dsa110-beam-model/DSA110_beam_1.h5 \
  --out /stage/dsa110-contimg/vp/dsa110.vp \
  --telescope DSA_110 \
  --freq-hz 1.4e9
```

This writes:
- VP table: `/stage/dsa110-contimg/vp/dsa110.vp`
- Temp complex image used to create it: `/stage/dsa110-contimg/vp/dsa110_vp_tmp.im`

Under the hood (`vp_builder.py`):
- Converts angles to degrees; computes elevation from `theta`.
- Builds the 4-pol complex Jones cube and a stable `coordsys` via `casatools.coordsys.newcoordsys(...)`.
- Registers the complex image with `vpmanager.setpbimage(compleximage=..., antnames=['*'])` and saves `saveastable()`.

### Verifying the VP
```python
from casatools import vpmanager
vp = vpmanager()
# Optionally bind a default telescope for UI inspection
vp.setuserdefault(telescope='DSA_110')
# The VP table is referenced via tclean(vptable=...)
```

### Using the VP in imaging
- A-Projection (if available in your CASA build):
  - `tclean(gridder='awproject', vptable='/path/to/dsa110.vp', wbawp=True, cfcache=...)`
  - Note: some CASA builds attempt a built-in A-term for the telescope name first; if unrecognized, A-Projection may fail before using the VP.
- Alternative for Stokes I: `wproject` + scalar PB correction
  - Image with `gridder='wproject'`, `pbcor=False`.
  - Build scalar PB: `PB ≈ 0.5*(|Jxx|^2 + |Jyy|^2)` (same grid as image).
  - Divide image by PB where `PB >= pblimit` (e.g., 0.25); for MT‑MFS, use wideband PB correction.

### Notes
- The VP encodes full 4‑pol Jones; you can supply it even if you only form Stokes I.
- For reproducibility, the CLI defaults are stable (center boresight, single channel, AZEL csys).
