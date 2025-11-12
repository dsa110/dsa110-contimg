## DSA-110 beam: off-axis diagnostics

This note summarizes how the off-axis diagnostics figure was generated from the DSA‑110 HDF5 beam model and how to interpret each panel.

Figure (PNG): `/scratch/dsa110-contimg/ms/central_cal_rebuild/dsa110_beam_offaxis_diagnostics.png`

### Inputs
- Beam model: `/scratch/dsa110-contimg/beam-model/DSA110_beam_1.h5`
  - Datasets: `X_pol_Efields/etheta`, `X_pol_Efields/ephi`, `Y-pol_Efields/etheta`, `Y-pol_Efields/ephi`, `theta_pts` (deg), `phi_pts` (deg), `freq_Hz`.
- Center (reference) frequency: nearest H5 frequency to the median of `freq_Hz`.

### Coordinate and feed mapping
- Local sky basis (IAU/IEEE): `e_phi` (azimuthal, E‑increasing), `e_theta` (toward decreasing elevation).
- DSA‑110 linear receptors at boresight:
  - X ↔ `e_phi` (Az)
  - Y ↔ `-e_theta` (El)
- Receiving Jones uses the complex conjugate of the transmit E‑fields from the H5 model.

### Computations
All radial curves are averaged over `phi` and masked where the center‑frequency primary beam (PB) falls below 0.3 to avoid divisions near nulls.

- Primary beam (panel 1):
  - Per frequency: `PB(f,θ,φ) = (|X_etheta|^2 + |X_ephi|^2 + |Y_etheta|^2 + |Y_ephi|^2)/2`.
  - Normalize each frequency by its boresight value (θ≈0, averaged over φ).
  - Plot the φ‑average at the reference frequency; annotate PB=0.8 and PB=0.5 radii.

- Frequency variation (panel 2):
  - For each θ: `var_rel(θ) = max_f |PB̄(f,θ) − PB̄(f0,θ)| / PB̄(f0,θ)`, where `PB̄` is the φ‑average and `f0` is the reference frequency.
  - Annotate the angles where the variation exceeds 5% and 10%.

- Cross‑hand leakage (panel 3): Mueller‑based estimate for an unpolarized sky.
  - Build 2×2 receiving Jones at the reference frequency:
    - `J_xx = conj(X_ephi)`, `J_xy = −conj(X_etheta)`, `J_yx = conj(Y_ephi)`, `J_yy = −conj(Y_etheta)`.
  - Form `K = J · J^H` per pixel; leakage is `|K_xy| / sqrt(K_xx K_yy)`.
  - Radially average over φ and annotate where leakage exceeds 1%, 3%, 5%.

### Results (approximate)
- PB radii: PB≈0.8 at ~1.1°, PB≈0.5 at ~1.8°.
- Frequency dependence: ≥5% by ~0.9°, ≥10% by ~1.2°.
- Leakage: ~1.4% near boresight, rising to ~4–5% by ~2.2° (within the PB≥0.3 mask).

### Caveats
- Single‑frequency Jones was used for leakage (nearest to median `freq_Hz`); true wideband A‑projection requires a frequency‑dependent VP/antenna response table.
- The X/Y ↔ (`e_phi`, `−e_theta`) mapping is based on public DSA‑110 documentation; if probe labeling differs, swap X/Y in the Jones construction.
- This analysis uses array‑average patterns (no per‑antenna variation) and does not include parallactic‑angle rotation or pointing errors.


