# Pipeline Visuals

This page illustrates the streaming continuum imaging pipeline from ingest to products, plus decision points and fast-path options for speed.

## End-to-end Flow

```mermaid
flowchart TB
  Ingest[Ingest watcher] --> Group[Group subbands by time window]
  Group --> Convert[Convert UVH5 to MS - strategy orchestrator]
  Convert --> CalSel{Calibrator?}
  CalSel -->|yes| Cal[Calibrate: K, BP, G]
  CalSel -->|no| Apply[Apply latest caltables]
  Cal --> Reg[Register caltables]
  Reg --> Apply
  Apply --> Image[tclean image]
  Image --> Index[Record in products DB: ms_index, images, qa_artifacts]
  Index --> API[API/QA views]
```

Notes:
- Conversion uses a strategy pattern and can stage to tmpfs for speed.
- Calibration can run a "fast" path (subset + phase-only + uvrange) for quick-look.
- Imaging can run a "quick" mode (smaller imsize, fewer iterations) and skip FITS export.

## Conversion: Writer Selection and Staging

```mermaid
flowchart LR
  Auto[--writer auto] --> N{n_subbands <= 2?}
  N -->|yes| Mono[pyuvdata monolithic write]
  N -->|no| Par[direct-subband: parallel per-subband writes]
  Par --> Stage{--stage-to-tmpfs?}
  Stage -->|yes| Tmp[dev-shm staging]
  Stage -->|no| Disk[SSD NVMe scratch]
  Tmp --> Concat[CASA concat to full-band MS]
  Disk --> Concat
  Mono --> MS[Final full-band MS]
  Concat --> MS
```

- Auto is faster because it avoids concat overhead for very small N and exploits parallelism + RAM for larger N.
- tmpfs staging reduces filesystem latency for part writes and final concat.

## Calibration: Fast Path

```mermaid
flowchart LR
  MSIn[Input MS] --> Fast{--fast?}
  Fast -->|yes| Subset[mstransform subset (timebin/chanbin)]
  Fast -->|no| Full[use full MS]
  Subset --> K[solve_delay (K)]
  Full --> K
  K --> BP[solve_bandpass (BP) uvrange?]
  BP --> G[solve_gains (G): phase-only if fast]
  G --> Tabs[Caltables]
  Tabs --> Reg[Register + apply]
```

- Typical fast knobs: `--timebin 30s`, `--chanbin 4`, `--uvrange >1klambda`, phase-only gains.

## Imaging: Quick-look Options

```mermaid
flowchart LR
  CMS[Calibrated MS] --> Tclean[tclean]
  Quick{--quick?} -->|yes| Small[imsize <= 512, niter <= 300, robust ~ 0]
  Quick -->|no| Def[use requested defaults]
  Small --> Tclean
  Def --> Tclean
  Tclean --> Fits{--skip-fits?}
  Fits -->|yes| Done[Stop after CASA images]
  Fits -->|no| FITS[Export FITS]
```

- Quick-look is for speed and operator QA; omit `--quick` and `--skip-fits` for full-quality products.
